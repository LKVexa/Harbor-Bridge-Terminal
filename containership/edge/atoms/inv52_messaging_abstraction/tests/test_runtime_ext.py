"""4.3.0 runtime behaviour: limits, idempotency, lifecycle, decisions, tracing, health."""
import threading
import unittest

from _support import env, pkg  # noqa: F401
from inv52_messaging_abstraction import runtime as rt


def bus(**kw):
    b = rt.PubSub(**kw)
    b.allow("t", "a")
    return b


class LimitsTest(unittest.TestCase):
    def test_payload_size_limit_rejects_and_records_terminal(self):
        b = bus(max_payload_bytes=300)
        b.subscribe("t", lambda m: True, [])
        with self.assertRaises(rt.ResourceLimitExceeded) as ctx:
            b.publish("a", "t", env(data={"x": "y" * 400}))
        self.assertFalse(ctx.exception.retryable)
        self.assertEqual(b.metrics()["oversize"], 1)
        self.assertEqual(b.decisions()[-1]["outcome"], rt.REJECTED_TERMINAL)

    def test_payload_at_limit_boundary_is_accepted(self):
        m = env(data={"x": ""})
        size = rt.payload_size(m)
        b = bus(max_payload_bytes=size)
        b.subscribe("t", lambda m: True, [])
        self.assertEqual(b.publish("a", "t", m), 1)
        b2 = bus(max_payload_bytes=size - 1)
        with self.assertRaises(rt.ResourceLimitExceeded):
            b2.publish("a", "t", m)

    def test_nesting_limit(self):
        deep = {}
        cur = deep
        for _ in range(50):
            cur["x"] = {}
            cur = cur["x"]
        b = bus(max_json_depth=8)
        with self.assertRaises(rt.ResourceLimitExceeded):
            b.publish("a", "t", env(data=deep))

    def test_topic_limit(self):
        b = rt.PubSub(max_topics=2)
        b.allow("x", "a")
        b.allow("y", "a")
        with self.assertRaises(rt.ResourceLimitExceeded):
            b.allow("z", "a")

    def test_invalid_new_knobs_fail_closed(self):
        for kw in ({"max_payload_bytes": 0}, {"dedup_window": -1}, {"predicate_view": "shared"},
                   {"admission": 5}, {"max_topics": True}):
            with self.assertRaises(rt.InvalidArgument, msg=kw):
                rt.PubSub(**kw)


class IdempotencyTest(unittest.TestCase):
    def test_duplicate_id_suppressed_within_window(self):
        b = bus(dedup_window=2)
        sink = []
        b.subscribe("t", lambda m: True, sink)
        m = env(message_id="m-1")
        self.assertEqual(b.publish("a", "t", m), 1)
        self.assertEqual(b.publish("a", "t", m), 0)
        self.assertEqual(len(sink), 1)
        self.assertEqual(len(b.dead_letter), 0)
        self.assertEqual(b.decisions()[-1]["outcome"], rt.DUPLICATE)

    def test_window_is_bounded(self):
        b = bus(dedup_window=2)
        sink = []
        b.subscribe("t", lambda m: True, sink)
        for i in ("1", "2", "3"):
            b.publish("a", "t", env(message_id=i))
        b.publish("a", "t", env(message_id="1"))  # evicted from window -> delivered again
        self.assertEqual(len(sink), 4)

    def test_default_keeps_420_semantics(self):
        b = bus()
        sink = []
        b.subscribe("t", lambda m: True, sink)
        m = env(message_id="same")
        b.publish("a", "t", m)
        b.publish("a", "t", m)
        self.assertEqual(len(sink), 2)


class TopicLifecycleTest(unittest.TestCase):
    def test_freeze_is_retryable_disable_is_terminal(self):
        b = bus()
        b.set_topic_state("t", rt.FROZEN)
        with self.assertRaises(rt.TopicUnavailable) as c1:
            b.publish("a", "t", env())
        self.assertTrue(c1.exception.retryable)
        b.set_topic_state("t", rt.DISABLED)
        with self.assertRaises(rt.TopicDisabled) as c2:
            b.publish("a", "t", env())
        self.assertFalse(c2.exception.retryable)

    def test_quarantine_holds_in_dead_letter_not_delivered(self):
        b = bus()
        sink = []
        b.subscribe("t", lambda m: True, sink)
        b.set_topic_state("t", rt.QUARANTINED, reason="suspected poison")
        self.assertEqual(b.publish("a", "t", env()), 0)
        self.assertEqual(sink, [])
        self.assertEqual(b.dead_letter[-1]["reason"], "quarantined")
        self.assertIn("t", b.health()["checks"]["quarantined_topics"])

    def test_illegal_transition(self):
        b = bus()
        b.set_topic_state("t", rt.DISABLED)
        with self.assertRaises(rt.InvalidTransition):
            b.set_topic_state("t", rt.FROZEN)
        b.set_topic_state("t", rt.ACTIVE)

    def test_every_declared_transition_is_legal_and_others_are_not(self):
        for src, dsts in rt.TOPIC_TRANSITIONS.items():
            for dst in rt.TOPIC_STATES:
                b = bus()
                b.topic_state["t"] = src
                if dst == src or dst in dsts:
                    b.set_topic_state("t", dst)
                else:
                    with self.assertRaises(rt.InvalidTransition):
                        b.set_topic_state("t", dst)


class DecisionAndExplainTest(unittest.TestCase):
    def test_every_route_has_a_reason(self):
        b = bus()
        b.subscribe("t", lambda m: False, [])
        b.subscribe("t", lambda m: 1 / 0, [])
        s = b.subscribe("t", lambda m: True, [])
        b.publish("a", "t", env(message_id="m-x"))
        ex = b.explain("m-x")
        self.assertEqual(ex["outcome"], rt.PARTIAL)
        reasons = [r["reason"] for r in ex["routes"]]
        self.assertEqual(reasons, ["predicate false", "predicate raised ZeroDivisionError", "delivered"])
        self.assertEqual(ex["routes"][2]["route"], s)
        self.assertEqual(ex["policy"]["allowed_publishers"], ["a"])

    def test_rejections_are_recorded(self):
        b = bus()
        with self.assertRaises(rt.TopicDenied):
            b.publish("m", "t", env("m", message_id="bad"))
        self.assertEqual(b.explain("bad")["reason"], "PK_MSG_TOPIC_DENIED")

    def test_decision_log_bounded(self):
        b = bus(max_decisions=3)
        for i in range(10):
            b.publish("a", "t", env(message_id=f"i{i}"))
        self.assertEqual(len(b.decisions()), 3)
        self.assertIsNone(b.explain("i0"))
        self.assertIsNotNone(b.explain("i9"))


class TraceTest(unittest.TestCase):
    TP = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

    def test_traceparent_propagates_to_subscriber_and_decision(self):
        b = bus()
        sink = []
        b.subscribe("t", lambda m: True, sink)
        b.publish("a", "t", env(traceparent=self.TP, message_id="tp"))
        self.assertEqual(sink[0]["traceparent"], self.TP)
        self.assertEqual(b.explain("tp")["traceparent"], self.TP)

    def test_malformed_traceparent_rejected(self):
        for bad in ("00-" + "0" * 32 + "-00f067aa0ba902b7-01", "garbage", 7):
            with self.assertRaises(rt.IncompleteEnvelope):
                rt.validate_envelope({"id": "1", "source": "a", "type": "t", "time": 0, "data": {},
                                      "traceparent": bad})


class HealthMetricsTest(unittest.TestCase):
    def test_health_degrades_on_backlog_and_stall(self):
        t = [0]
        b = bus(max_dead_letters=10, clock_ns=lambda: t[0])
        self.assertEqual(b.health()["status"], "ok")
        for _ in range(8):
            b.publish("a", "t", env())
        h = b.health()
        self.assertEqual(h["status"], "degraded")
        t[0] = 61 * 10 ** 9
        self.assertIn("no publish completed within stall window", b.health(stall_after_s=60)["problems"])

    def test_latency_histogram_and_outcomes(self):
        b = bus()
        b.subscribe("t", lambda m: True, [])
        for _ in range(5):
            b.publish("a", "t", env())
        m = b.metrics()
        self.assertEqual(m["latency"]["count"], 5)
        self.assertEqual(m["outcomes"][rt.DELIVERED], 5)
        self.assertIsNotNone(m["latency"]["p99_ns"])

    def test_observer_failure_never_breaks_publish(self):
        def boom(_e):
            raise RuntimeError
        b = bus(observer=boom)
        b.subscribe("t", lambda m: True, [])
        self.assertEqual(b.publish("a", "t", env()), 1)
        self.assertGreater(b.metrics()["observer_errors"], 0)

    def test_admission_hook_error_fails_closed(self):
        def broken(app, topic):
            raise KeyError("x")
        b = bus(admission=broken)
        with self.assertRaises(rt.Overloaded):
            b.publish("a", "t", env())


class CompatTest(unittest.TestCase):
    def test_unsubscribe(self):
        b = bus()
        sink = []
        sid = b.subscribe("t", lambda m: True, sink)
        self.assertTrue(b.unsubscribe(sid))
        self.assertFalse(b.unsubscribe(sid))
        b.publish("a", "t", env())
        self.assertEqual(sink, [])

    def test_routes_appended_directly_still_work(self):
        b = bus()
        sink = []
        b.routes.setdefault("t", []).append((lambda m: True, sink))
        self.assertEqual(b.publish("a", "t", env()), 1)
        self.assertEqual(b.decisions()[-1]["routes"][0]["route"], "route-0")

    def test_frozen_view_prevents_predicate_mutation(self):
        b = bus(predicate_view="frozen")
        sink = []

        def mutate(m):
            m["data"]["n"] = 99
            return True
        b.subscribe("t", mutate, [])
        b.subscribe("t", lambda m: True, sink)
        b.publish("a", "t", env())
        self.assertEqual(sink[0]["data"]["n"], 1)
        self.assertEqual(b.metrics()["route_errors"], 1)

    def test_concurrent_state_change_and_publish(self):
        b = bus()
        b.subscribe("t", lambda m: True, [])
        errors = []

        def pub():
            for _ in range(200):
                try:
                    b.publish("a", "t", env())
                except rt.TopicUnavailable:
                    pass
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

        def flip():
            for i in range(200):
                b.set_topic_state("t", rt.FROZEN if i % 2 == 0 else rt.ACTIVE)
        ts = [threading.Thread(target=pub) for _ in range(4)] + [threading.Thread(target=flip)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(errors, [])
        m = b.metrics()
        self.assertEqual(m["published"], m["outcomes"].get(rt.DELIVERED, 0))


if __name__ == "__main__":
    unittest.main()
