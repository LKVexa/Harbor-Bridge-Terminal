"""Broker data path: contract, isolation, admission, degraded modes, observability, threat-derived
cases (components 8, 20-partial, 33, 35, 37, 39-43, 46, 49, 60-66, 70, 75)."""
from __future__ import annotations

import io
import json
import unittest

from _support import KEY_B, Clock, TmpDirCase, make_broker, signed
from inv53_message_reliability import security as S
from inv53_message_reliability.observability import CardinalityError, Metrics, parse_traceparent
from inv53_message_reliability.service import Breaker, Broker, TokenBucket, backoff


def code(resp):
    return resp["outcome"]["code"]


class BrokerTest(TmpDirCase):
    def setUp(self):
        super().setUp()
        self.b, self.clock = make_broker(self.tmp)

    def put(self, mid, tenant="acme", queue="q", principal="alice", kid="ka", **kw):
        key = KEY_B if kid == "kb" else None
        extra = {"key": key} if key else {}
        return self.b.handle(signed({"op": "put", "tenant": tenant, "queue": queue, "message": {"id": mid, **kw}},
                                    principal=principal, kid=kid, **extra))

    def recv(self, now=0, tenant="acme", queue="q", principal="alice", kid="ka"):
        extra = {"key": KEY_B} if kid == "kb" else {}
        return self.b.handle(signed({"op": "receive", "tenant": tenant, "queue": queue, "now": now},
                                    principal=principal, kid=kid, **extra))

    # ------------------------------------------------------------ contract
    def test_public_contract_roundtrip(self):
        self.assertEqual(code(self.put("m1", data=1)), "OK")
        self.assertEqual(code(self.put("m1", data=1)), "OK_DUPLICATE")
        self.assertEqual(code(self.put("m1", data=2)), "E_DUPLICATE_ACTIVE")
        r = self.recv()
        self.assertEqual(code(r), "OK")
        d = r["delivery"]
        self.assertEqual(d["message"]["data"], 1)
        ack = self.b.handle(signed({"op": "ack", "tenant": "acme", "queue": "q", "id": "m1", "lease": d["lease"], "now": 1}))
        self.assertEqual(code(ack), "OK")
        again = self.b.handle(signed({"op": "ack", "tenant": "acme", "queue": "q", "id": "m1", "lease": d["lease"], "now": 1}))
        self.assertEqual(code(again), "E_LEASE_STALE")
        self.assertEqual(code(self.recv()), "OK_EMPTY")

    def test_extend_nack_redrive_explain(self):
        self.put("m1")
        d = self.recv()["delivery"]
        ext = self.b.handle(signed({"op": "extend", "tenant": "acme", "queue": "q", "id": "m1", "lease": d["lease"],
                                    "now": 1, "extension": 10}))
        self.assertEqual(ext["outcome"]["data"]["deadline"], self.clock.t + 10)
        too_long = self.b.handle(signed({"op": "extend", "tenant": "acme", "queue": "q", "id": "m1", "lease": d["lease"],
                                         "now": 1, "extension": 10_000}))
        self.assertEqual(code(too_long), "E_CAPACITY")
        n = self.b.handle(signed({"op": "nack", "tenant": "acme", "queue": "q", "id": "m1", "lease": d["lease"], "now": 2,
                                  "requeue": False, "reason": "poison"}))
        self.assertEqual(code(n), "OK")
        ex = self.b.handle(signed({"op": "explain", "tenant": "acme", "queue": "q", "id": "m1"}))
        self.assertEqual(ex["explain"]["reason"], "poison")
        rd = self.b.handle(signed({"op": "redrive", "tenant": "acme", "queue": "q", "id": "m1", "now": 3}))
        self.assertEqual(code(rd), "OK")
        self.assertEqual(self.recv(now=4)["delivery"]["attempt"], 1)
        events = [json.loads(l)["event"] for l in (self.tmp / "audit.jsonl").read_text().splitlines()]
        self.assertIn("redrive", events)

    # ------------------------------------------- adversarial-review regressions
    def test_R4_health_over_the_wire_shows_only_the_callers_tenant(self):
        self.put("x", tenant="globex", queue="secret-q", principal="bob", kid="kb")
        self.put("a")
        h = self.b.handle(signed({"op": "health", "tenant": "acme", "queue": "q"}))["health"]
        self.assertEqual(sorted(h["queues"]), ["acme/q"])
        self.assertNotIn("audit_head", h)
        self.assertIn("globex/secret-q", self.b.health()["queues"], "the in-process operator view is complete")

    def test_R5_client_supplied_time_cannot_steal_a_lease(self):
        self.put("m")
        first = self.recv(now=100)["delivery"]
        stolen = self.recv(now=1e12)
        self.assertEqual(code(stolen), "OK_EMPTY", "a far-future client 'now' must not expire another lease")
        ack = self.b.handle(signed({"op": "ack", "tenant": "acme", "queue": "q", "id": "m", "lease": first["lease"],
                                    "now": 1e12}))
        self.assertEqual(code(ack), "OK")

    def test_R6_malformed_headers_are_a_validation_error(self):
        for bad in ("oops", {"traceparent": 5}, [1]):
            r = self.b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": "h", "headers": bad},
                                      "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}))
            self.assertEqual(code(r), "E_VALIDATION", bad)

    def test_R7_refusals_create_no_state(self):
        self.b.drain(actor="ops")
        self.assertEqual(code(self.put("n", queue="brand-new")), "E_DRAINING")
        self.assertNotIn(("acme", "brand-new"), self.b._queues)
        self.assertFalse((self.tmp / "broker" / "tenants" / "acme" / "brand-new").exists())
        b, clock = make_broker(self.tmp / "shed", config={"max_ready": 10, "max_in_flight": 10, "shed_ready_ratio": 0.2,
                                                          "tenant_burst": 3, "tenant_rate_per_second": 0.001})
        for i in range(2):
            b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": f"s{i}"}}))
        for i in range(5):   # shed refusals must not drain the tenant's quota
            self.assertEqual(code(b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": f"x{i}"}}))), "E_SHED")
        self.assertEqual(code(b.handle(signed({"op": "receive", "tenant": "acme", "queue": "q"}))), "OK")

    def test_R7_quota_refusal_does_not_strand_the_breaker_probe(self):
        br_state = {"fail": 0}

        def fault(point, op):
            if br_state["fail"] and point == "before_write":
                br_state["fail"] -= 1
                raise OSError("EIO")
        b, clock = make_broker(self.tmp / "bq", fault=fault, config={"breaker_failure_threshold": 1, "breaker_reset_seconds": 5,
                                                                     "tenant_burst": 2, "tenant_rate_per_second": 0.1})
        put = lambda i: code(b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": f"m{i}"}})))  # noqa: E731
        self.assertEqual(put(0), "OK")
        br_state["fail"] = 1
        self.assertEqual(put(1), "E_STORAGE")         # breaker opens; bucket is now empty
        clock.t += 5                                    # breaker would grant its one probe; bucket holds 0.5
        self.assertEqual(put(2), "E_QUOTA")             # refused by quota -- the probe must not be consumed
        clock.t += 10
        self.assertEqual(put(3), "OK", "the half-open probe is still available and closes the breaker")
        self.assertEqual(b.health()["mode"], "NORMAL")

    def test_R8_dot_names_refused(self):
        for bad in (".", "..", "a\\b", "c:"):
            r = self.b.handle(signed({"op": "receive", "tenant": bad, "queue": "q"}))
            self.assertEqual(code(r), "E_VALIDATION", bad)
            r = self.b.handle(signed({"op": "receive", "tenant": "acme", "queue": bad}))
            self.assertEqual(code(r), "E_VALIDATION", bad)

    # ------------------------------------------------------- threat-derived
    def test_T1_unauthenticated_is_refused_and_audited(self):
        r = self.b.handle({"v": "inv53.wire/1", "op": "put", "tenant": "acme", "queue": "q", "message": {"id": "x"}})
        self.assertEqual(code(r), "E_UNAUTHENTICATED")
        self.assertIn("authn_denied", (self.tmp / "audit.jsonl").read_text())

    def test_T2_cross_tenant_access_denied_even_with_same_queue_name(self):
        self.put("secret", tenant="acme", queue="shared")
        self.assertEqual(code(self.put("x", tenant="globex", queue="shared", principal="bob", kid="kb")), "OK")
        r = self.recv(tenant="globex", queue="shared", principal="bob", kid="kb")
        self.assertEqual(r["delivery"]["message"]["id"], "x", "globex sees only its own message")
        self.assertEqual(code(self.recv(tenant="acme", queue="shared", principal="bob", kid="kb")), "E_FORBIDDEN")
        self.assertEqual(code(self.put("y", tenant="globex", queue="q", principal="alice")), "E_FORBIDDEN")

    def test_T3_replayed_request_refused(self):
        req = signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": "r1"}})
        self.assertEqual(code(self.b.handle(req)), "OK")
        self.assertEqual(code(self.b.handle(req)), "E_UNAUTHENTICATED")

    def test_T4_stale_consumer_cannot_settle_redelivered_message(self):
        self.put("m")
        first = self.recv()["delivery"]
        self.clock.t += 31
        second = self.recv()["delivery"]
        stale = self.b.handle(signed({"op": "ack", "tenant": "acme", "queue": "q", "id": "m", "lease": first["lease"], "now": 31}))
        self.assertEqual(code(stale), "E_LEASE_STALE")
        self.assertEqual(second["attempt"], 2)

    def test_T5_path_traversal_names_refused(self):
        for bad in ("../etc", "a/b", " pad", ""):
            r = self.b.handle(signed({"op": "put", "tenant": bad, "queue": "q", "message": {"id": "x"}}))
            self.assertEqual(code(r), "E_VALIDATION", bad)
        self.assertFalse((self.tmp / "etc").exists())

    def test_T6_oversized_and_malformed_inputs(self):
        self.assertEqual(code(self.put("big", blob="x" * 300_000)), "E_CAPACITY")
        self.assertEqual(code(self.b.handle({"v": "inv53.wire/1", "op": "put"})), "E_VALIDATION")
        self.assertEqual(code(self.b.handle("not a dict")), "E_VALIDATION")
        self.assertEqual(code(self.b.handle({"v": "inv53.wire/9", "op": "put", "tenant": "a", "queue": "q"})),
                         "E_PROTOCOL_VERSION")

    def test_T7_audit_sink_outage_fails_closed(self):
        self.b.audit.path = self.tmp / "gone"
        (self.tmp / "gone").mkdir()
        r = self.b.handle({"v": "inv53.wire/1", "op": "put", "tenant": "acme", "queue": "q", "message": {"id": "x"}})
        self.assertEqual(code(r), "E_SECURITY_DEPENDENCY")

    def test_T8_logs_and_metrics_never_contain_payload_or_lease(self):
        self.put("m", payload={"ssn": "123-45-6789"})
        d = self.recv()["delivery"]
        logs = self.b._test_log.getvalue()
        self.assertNotIn("123-45-6789", logs)
        self.assertNotIn(d["lease"], logs)
        self.assertNotIn("123-45-6789", self.b.metrics.prometheus())
        audit = self.tmp / "audit.jsonl"
        self.assertNotIn(d["lease"], audit.read_text() if audit.exists() else "")

    def test_secure_defaults_require_authn_and_audit(self):
        with self.assertRaises(ValueError):
            Broker(self.tmp / "b2")
        with self.assertRaises(ValueError):
            Broker(self.tmp / "b3", authenticator=S.Authenticator(S.Keyring()))

    # --------------------------------------------------- control & degraded
    def test_freeze_emergency_disable_and_drain(self):
        self.put("m")
        self.b.freeze("acme", "q", reason="investigation", actor="ops")
        self.assertEqual(code(self.recv()), "E_FROZEN")
        self.b.unfreeze("acme", "q", actor="ops")
        self.assertEqual(code(self.recv()), "OK")
        self.b.freeze("acme", reason="tenant incident", actor="ops")
        self.assertEqual(code(self.put("n")), "E_FROZEN")
        self.b.unfreeze("acme", actor="ops")
        self.b.emergency_disable(reason="sev1", actor="ops")
        self.assertEqual(code(self.put("n")), "E_FROZEN")
        self.assertEqual(self.b.health()["mode"], "DISABLED")
        self.b.emergency_enable(actor="ops")
        remaining = self.b.drain(actor="ops")
        self.assertIn("acme/q", remaining)
        self.assertEqual(code(self.put("n2")), "E_DRAINING")
        self.clock.t += 100
        self.assertEqual(code(self.recv()), "OK", "consumers keep draining")
        text = (self.tmp / "audit.jsonl").read_text()
        for ev in ("freeze", "unfreeze", "emergency_disable", "emergency_enable", "drain"):
            self.assertIn(f'"event": "{ev}"', text)

    def test_quota_and_shedding(self):
        b, clock = make_broker(self.tmp / "q2", config={"tenant_burst": 3, "tenant_rate_per_second": 1.0})
        r = [code(b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": f"m{i}"}})))
             for i in range(5)]
        self.assertEqual(r, ["OK", "OK", "OK", "E_QUOTA", "E_QUOTA"])
        clock.t += 1
        self.assertEqual(code(b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": "z"}}))), "OK")
        b2, _ = make_broker(self.tmp / "q3", config={"max_ready": 10, "max_in_flight": 10, "shed_ready_ratio": 0.3})
        codes = [code(b2.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": f"s{i}"}})))
                 for i in range(5)]
        self.assertEqual(codes, ["OK", "OK", "OK", "E_SHED", "E_SHED"])
        self.assertEqual(b2.health()["mode"], "DEGRADED_SHEDDING")
        self.assertEqual(code(b2.handle(signed({"op": "receive", "tenant": "acme", "queue": "q", "now": 0}))), "OK")

    def test_storage_failure_opens_breaker_recovers_and_loses_nothing(self):
        state = {"fail": 0}

        def fault(point, op):
            if state["fail"] and point == "before_write" and op == "put":
                state["fail"] -= 1
                raise OSError("EIO")
        b, clock = make_broker(self.tmp / "s", fault=fault,
                               config={"breaker_failure_threshold": 2, "breaker_reset_seconds": 5})
        put = lambda i: code(b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": f"m{i}"}})))  # noqa: E731
        self.assertEqual(put(0), "OK")
        state["fail"] = 2
        self.assertEqual(put(1), "E_STORAGE")
        self.assertEqual(put(1), "E_STORAGE")
        self.assertEqual(put(1), "E_CIRCUIT_OPEN")
        self.assertEqual(b.health()["mode"], "DEGRADED_STORAGE")
        clock.t += 5
        self.assertEqual(put(1), "OK", "half-open probe succeeds and closes the breaker")
        self.assertEqual(b.health()["mode"], "NORMAL")
        self.assertEqual(b.health()["queues"]["acme/q"]["ready"], 2)

    def test_health_readiness_and_stall_detection(self):
        b, clock = make_broker(self.tmp / "h", config={"stall_seconds": 10})
        b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": "a"}}))
        h = b.health()
        self.assertTrue(h["live"] and h["ready"])
        clock.t += 11
        h = b.health()
        self.assertTrue(h["queues"]["acme/q"]["stalled"])
        self.assertFalse(h["ready"])

    def test_trace_context_propagates_to_consumer(self):
        tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        self.b.handle(signed({"op": "put", "tenant": "acme", "queue": "q", "message": {"id": "t"}, "traceparent": tp}))
        m = self.recv()["delivery"]["message"]
        ctx = parse_traceparent(m["headers"]["traceparent"])
        self.assertEqual(ctx["trace_id"], "0af7651916cd43dd8448eb211c80319c")
        self.assertNotEqual(ctx["span_id"], "b7ad6b7169203331")
        self.assertIn("0af7651916cd43dd8448eb211c80319c", self.b._test_log.getvalue())
        self.assertIsNone(parse_traceparent("00-" + "0" * 32 + "-b7ad6b7169203331-01"))

    def test_metrics_exposition_and_cardinality_cap(self):
        self.put("m")
        self.recv()
        self.b.health()
        text = self.b.metrics.prometheus(config_digest=self.b.cfg_digest)
        self.assertIn("inv53_build_info{", text)
        self.assertIn('inv53_ops_total{code="OK",op="put",tenant="acme"} 1', text)
        self.assertIn("inv53_op_seconds_bucket", text)
        m = Metrics(max_series=3)
        for i in range(10):
            m.inc("c", tenant=f"t{i}")
        self.assertEqual(m.dropped, 7)
        with self.assertRaises(CardinalityError):
            m.inc("c", message_id="m1")

    def test_internal_errors_do_not_leak(self):
        class Boom(S.Authorizer):
            def check(self, *a):
                raise RuntimeError("secret internal detail")
        self.b.authz = Boom()
        r = self.put("m")
        self.assertEqual(code(r), "E_INTERNAL")
        self.assertNotIn("secret internal detail", json.dumps(r))

    def test_graceful_shutdown_then_restart_preserves_state(self):
        self.put("a")
        self.put("b")
        d = self.recv()["delivery"]
        self.b.shutdown(actor="ops")
        b2, _ = make_broker(self.tmp)
        r = b2.handle(signed({"op": "ack", "tenant": "acme", "queue": "q", "id": "a", "lease": d["lease"], "now": 1}))
        self.assertEqual(code(r), "OK", "a lease granted before shutdown is honoured by the restarted broker")
        r = b2.handle(signed({"op": "receive", "tenant": "acme", "queue": "q", "now": 2}))
        self.assertEqual(r["delivery"]["message"]["id"], "b", "persisted work is visible without a new put")
        self.assertEqual(code(b2.handle(signed({"op": "receive", "tenant": "globex", "queue": "q", "now": 2},
                                               principal="bob", kid="kb", key=KEY_B))), "OK_EMPTY")


class OpenFailureTest(TmpDirCase):
    def test_queue_count_limit_and_unopenable_stores_are_typed_refusals(self):
        b, _ = make_broker(self.tmp)
        b.max_queues = 2
        codes = [code(b.handle(signed({"op": "put", "tenant": "acme", "queue": f"q{i}", "message": {"id": "m"}})))
                 for i in range(3)]
        self.assertEqual(codes, ["OK", "OK", "E_CAPACITY"])
        # a store corrupted on disk before the broker opens it
        store = self.tmp / "broker" / "tenants" / "acme" / "bad"
        from inv53_message_reliability.durable import DurableQueue
        with DurableQueue(store) as q:
            q.put({"id": "x"}); q.put({"id": "y"})
        lines = (store / "journal.jsonl").read_bytes().split(b"\n")
        lines[1] = lines[1].replace(b'"x"', b'"z"')
        (store / "journal.jsonl").write_bytes(b"\n".join(lines))
        b.max_queues = 10
        r = b.handle(signed({"op": "receive", "tenant": "acme", "queue": "bad", "now": 0}))
        self.assertEqual(code(r), "E_CORRUPT")
        # a store owned by another live writer
        other = DurableQueue(self.tmp / "broker" / "tenants" / "acme" / "held")
        other.put({"id": "h"})
        r = b.handle(signed({"op": "receive", "tenant": "acme", "queue": "held", "now": 0}))
        self.assertEqual(code(r), "E_EPOCH_FENCED")
        other.close()


class PolicyUnitTest(unittest.TestCase):
    def test_backoff_full_jitter_bounds(self):
        self.assertEqual(backoff(3, base=0.1, cap=30, rng=lambda: 1.0), 0.8)
        self.assertEqual(backoff(100, base=0.1, cap=30, rng=lambda: 1.0), 30)
        self.assertEqual(backoff(5, rng=lambda: 0.0), 0.0)
        with self.assertRaises(ValueError):
            backoff(-1)

    def test_token_bucket_clock_regression_grants_nothing(self):
        tb = TokenBucket(rate=1, burst=1)
        self.assertTrue(tb.take(100))
        self.assertFalse(tb.take(50))
        self.assertFalse(tb.take(100.5))
        self.assertTrue(tb.take(101))

    def test_breaker_half_open_single_probe(self):
        br = Breaker(threshold=1, reset=5)
        br.failure(0)
        self.assertFalse(br.allow(1))
        self.assertTrue(br.allow(5))
        self.assertFalse(br.allow(5), "only one probe while half-open")
        br.failure(6)
        self.assertEqual(br.state, "open")
        self.assertTrue(br.allow(11))
        br.success()
        self.assertEqual(br.state, "closed")


if __name__ == "__main__":
    unittest.main()
