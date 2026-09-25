"""Integration with adjacent layers, fault injection, recovery, version negotiation, observability.

The Dapr tests run the real ``urllib`` transport against an in-process HTTP
server that implements the Dapr v1.0 publish endpoint and the subscriber
delivery contract.  It is an emulator, not ``daprd``: it proves the wire
mapping and status handling, not interoperability with a live sidecar.
"""
import http.server
import json
import pathlib
import random
import threading
import unittest

from _support import env
from inv52_messaging_abstraction import adapters as ad
from inv52_messaging_abstraction import observability as ob
from inv52_messaging_abstraction import runtime as rt
from inv52_messaging_abstraction import schemas as sc

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "conformance.json"


class _DaprEmulator(http.server.BaseHTTPRequestHandler):
    store: dict = {}
    script: list = []

    def log_message(self, *a):  # silence
        pass

    def do_POST(self):  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        parts = self.path.strip("/").split("/")
        if parts[:2] != ["v1.0", "publish"] or len(parts) != 4:
            self.send_response(404)
            self.end_headers()
            return
        if self.script:
            code = self.script.pop(0)
            self.send_response(code)
            self.end_headers()
            return
        if self.headers.get("Content-Type") != ad.CE_CONTENT_TYPE:
            self.send_response(400)
            self.end_headers()
            return
        ce = json.loads(body)
        self.store.setdefault((parts[2], parts[3]), []).append((ce, {k.lower(): v for k, v in self.headers.items()}))
        self.send_response(204)
        self.end_headers()


class DaprHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _DaprEmulator)
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        _DaprEmulator.store.clear()
        _DaprEmulator.script.clear()

    def adapter(self, **kw):
        return ad.DaprHttpAdapter(pubsub="order-events", base_url=self.url, timeout=2, sleep=lambda s: None,
                                  rng=random.Random(1), **kw)

    def test_publish_structured_cloudevent(self):
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        a = self.adapter(api_token=lambda: "tok-from-secret-store")
        a.publish("orders", env("shop", "order.placed", {"total": 5}, traceparent=tp))
        (ce, hdr), = _DaprEmulator.store[("order-events", "orders")]
        self.assertEqual((ce["specversion"], ce["source"], ce["type"], ce["data"]), ("1.0", "shop", "order.placed",
                                                                                     {"total": 5}))
        self.assertEqual(ce["traceparent"], tp)
        self.assertEqual(hdr.get("dapr-api-token"), "tok-from-secret-store")

    def test_retry_on_503_then_success_and_terminal_on_403(self):
        _DaprEmulator.script.extend([503, 503])
        a = self.adapter()
        a.publish("orders", env("shop"))
        self.assertEqual(a.attempts, 3)
        _DaprEmulator.script.append(403)
        a2 = self.adapter()
        with self.assertRaises(ad.BrokerRejected):
            a2.publish("orders", env("shop"))
        self.assertEqual(a2.attempts, 1)

    def test_sidecar_down_is_retryable_unavailable(self):
        a = ad.DaprHttpAdapter(pubsub="p", base_url="http://127.0.0.1:9", timeout=0.2, sleep=lambda s: None,
                               retry=__import__("inv52_messaging_abstraction.resilience", fromlist=["x"])
                               .RetryPolicy(max_attempts=2, base_delay=0.01, max_delay=0.01))
        with self.assertRaises(ad.BrokerUnavailable) as ctx:
            a.publish("orders", env("shop"))
        self.assertTrue(ctx.exception.retryable)
        self.assertEqual(a.attempts, 2)

    def test_inbound_delivery_status_mapping(self):
        bus = rt.PubSub()
        bus.allow("orders", "shop")
        sink = []
        bus.subscribe("orders", lambda m: True, sink)
        ce = ad.to_cloudevent(env("shop"), topic="orders", pubsub="p")
        self.assertEqual(ad.dapr_delivery_status(bus, app="shop", topic="orders", cloudevent=ce)["status"],
                         "SUCCESS")
        self.assertEqual(ad.dapr_delivery_status(bus, app="shop", topic="orders",
                                                 cloudevent={"specversion": "0.3"})["status"], "DROP")
        bus.set_topic_state("orders", rt.FROZEN)
        self.assertEqual(ad.dapr_delivery_status(bus, app="shop", topic="orders", cloudevent=ce)["status"], "RETRY")

    def test_cloudevent_round_trip_numeric_and_string_time(self):
        for t in (0, 1.5, "2026-09-22T00:00:00Z"):
            m = env(time=t)
            self.assertEqual(ad.from_cloudevent(ad.to_cloudevent(m, topic="x", pubsub="p")), m)


class OutboxChaosTest(unittest.TestCase):
    def test_offline_queue_reconnect_in_order_no_loss_no_dup(self):
        broker = ad.InMemoryBroker()
        box = ad.Outbox(broker, capacity=100)
        msgs = [env(data={"n": i}) for i in range(30)]
        for i, m in enumerate(msgs):
            if i == 10:
                broker.available = False  # connectivity lost mid-stream
            box.publish("t", m)
        self.assertEqual(len(broker.topics["t"]), 10)
        self.assertEqual(len(box.pending), 20)
        self.assertEqual(box.flush()["sent"], 0)  # still offline: nothing lost
        broker.available = True
        self.assertEqual(box.flush()["sent"], 20)
        self.assertEqual([m["data"]["n"] for m in broker.topics["t"]], list(range(30)))
        for m in msgs[:5]:  # at-least-once replay of already-sent messages is de-duplicated
            broker.publish("t", m)
        self.assertEqual(len(broker.topics["t"]), 30)
        self.assertEqual(broker.duplicates, 5)

    def test_capacity_is_backpressure_not_growth(self):
        broker = ad.InMemoryBroker()
        broker.available = False
        box = ad.Outbox(broker, capacity=3)
        for _ in range(3):
            box.publish("t", env())
        with self.assertRaises(rt.Overloaded):
            box.publish("t", env())
        self.assertEqual(len(box.pending), 3)

    def test_partition_of_one_topic_does_not_block_other_topics_directly(self):
        broker = ad.InMemoryBroker()
        broker.partitioned.add("a")
        with self.assertRaises(ad.BrokerUnavailable):
            broker.publish("a", env())
        broker.publish("b", env())
        self.assertEqual(len(broker.topics["b"]), 1)

    def test_expiry_bounds_offline_age(self):
        t = [0.0]
        broker = ad.InMemoryBroker()
        broker.available = False
        box = ad.Outbox(broker, capacity=10, max_age_s=5, clock=lambda: t[0])
        box.publish("t", env())
        t[0] = 10
        broker.available = True
        self.assertEqual(box.flush(), {"sent": 0, "pending": 0, "expired": 1, "rejected": 0})

    def test_recovery_objective_under_random_faults(self):
        """RPO 0 / no duplicates for 500 messages with 30% injected broker outages."""
        rng = random.Random(42)
        broker = ad.InMemoryBroker()
        box = ad.Outbox(broker, capacity=1000)
        for i in range(500):
            broker.available = rng.random() > 0.3
            box.publish("t", env(data={"n": i}))
            if rng.random() < 0.2:
                box.flush()
        broker.available = True
        box.flush()
        got = [m["data"]["n"] for m in broker.topics["t"]]
        self.assertEqual(got, list(range(500)))


class VersionTest(unittest.TestCase):
    def test_negotiation(self):
        self.assertEqual(sc.negotiate("PK_MSG_ENVELOPE", [1, 2, 3]), 1)
        with self.assertRaises(sc.VersionUnsupported):
            sc.negotiate("PK_MSG_ENVELOPE", [2])
        with self.assertRaises(sc.VersionUnsupported):
            sc.parse_contract_id("PK_MSG_ENVELOPE/2")

    def test_forward_compatible_unknown_optional_fields_accepted(self):
        m = dict(env(), futurefield={"x": 1})
        rt.validate_envelope(m)


class ConformanceFixtureTest(unittest.TestCase):
    def test_fixture_suite(self):
        fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
        for case in fx["cases"]:
            with self.subTest(case["id"]):
                b = rt.PubSub(**case.get("bus", {}))
                for t, apps in case.get("allow", {}).items():
                    b.allow(t, *apps)
                sinks = {}
                for r in case.get("routes", []):
                    sinks[r["name"]] = []
                    field, op, val = r["match"]
                    pred = {"ge": lambda m, f=field, v=val: m["data"][f] >= v,
                            "lt": lambda m, f=field, v=val: m["data"][f] < v,
                            "eq": lambda m, f=field, v=val: m["data"].get(f) == v}[op]
                    b.subscribe(r["topic"], pred, sinks[r["name"]])
                exp = case["expect"]
                if "error" in exp:
                    with self.assertRaises(rt.MessagingError) as ctx:
                        b.publish(case["app"], case["topic"], case["message"])
                    self.assertEqual(ctx.exception.code, exp["error"])
                else:
                    self.assertEqual(b.publish(case["app"], case["topic"], case["message"]), exp["delivered"])
                    for name, n in exp.get("sinks", {}).items():
                        self.assertEqual(len(sinks[name]), n)
                    if "dead_letter_reason" in exp:
                        self.assertEqual(b.dead_letter[-1]["reason"], exp["dead_letter_reason"])
                    self.assertEqual(b.decisions()[-1]["outcome"], exp["outcome"])


class ObservabilityTest(unittest.TestCase):
    def test_logs_carry_stable_ids_release_and_no_payload(self):
        log = ob.StructuredLogger(node="n1", workload="checkout", release="4.3.0+abc")
        b = rt.PubSub(observer=ob.Telemetry(log))
        b.allow("acme::orders", "a")
        b.publish("a", "acme::orders", env(data={"card": "4111"}, message_id="m1"))
        rec = [r for r in log.records if r.get("event") == "publish.decision"][-1]
        for f in ob.LOG_FIELDS:
            self.assertIn(f, rec)
        self.assertEqual((rec["tenant"], rec["release"], rec["component"]), ("acme", "4.3.0+abc", "INV-52"))
        self.assertNotIn("4111", json.dumps(rec))

    def test_sampling_never_drops_failures_or_policy(self):
        log = ob.StructuredLogger(node="n", workload="w", release="r", sample_rate=0.0)
        b = rt.PubSub(observer=ob.Telemetry(log))
        b.allow("t", "a")
        b.subscribe("t", lambda m: True, [])
        b.publish("a", "t", env())
        with self.assertRaises(rt.TopicDenied):
            b.publish("x", "t", env("x"))
        events = [r.get("outcome") or r.get("event") for r in log.records]
        self.assertIn("policy.allow", events)
        self.assertIn(rt.REJECTED_TERMINAL, events)
        self.assertNotIn(rt.DELIVERED, events)
        self.assertEqual(log.dropped_by_sampling, 2)  # subscription.add + the successful decision

    def test_prometheus_labels_are_bounded(self):
        b = rt.PubSub()
        b.allow("t", "a")
        for i in range(20):
            b.publish("a", "t", env(message_id=f"unique-{i}"))
        text = ob.prometheus_text(b.metrics(), node="n", release="r")
        self.assertNotIn("unique-", text)
        self.assertIn('inv52_dead_letter_reason_total{component="INV-52",node="n",release="r",reason="no route '
                      'matched"} 20', text)
        self.assertIn("inv52_publish_latency_seconds_count", text)

    def test_classifier_distinguishes_classes(self):
        z = {}
        cases = [
            ({"published": 100}, {}, "normal_load"),
            ({"published": 50, "shed": 50}, {}, "overload"),
            ({"published": 10, "denied": 90}, {}, "attack_suspected"),
            ({"published": 99, "denied": 1}, {}, "policy_rejection"),
            ({"published": 100, "sink_errors": 50}, {}, "dependency_failure"),
            ({"published": 100}, {"dependency_down": True}, "dependency_failure"),
            ({"published": 100, "route_errors": 40}, {}, "software_defect"),
            ({"published": 100, "route_errors": 2}, {}, "degradation"),
            ({"published": 50, "invalid": 50}, {}, "client_defect"),
        ]
        for after, kw, want in cases:
            self.assertEqual(ob.classify(z, after, **kw)["class"], want, after)
        self.assertEqual(ob.classify(z, z)["class"], "idle")

    def test_trace_helpers(self):
        p = ob.new_traceparent()
        c = ob.child_traceparent(p)
        self.assertTrue(rt.TRACEPARENT.match(p) and rt.TRACEPARENT.match(c))
        self.assertEqual(p.split("-")[1], c.split("-")[1])
        self.assertNotEqual(p, c)


if __name__ == "__main__":
    unittest.main()
