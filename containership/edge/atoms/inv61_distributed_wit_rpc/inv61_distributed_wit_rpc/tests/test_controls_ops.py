"""M07, M10-M17, M19, M20, M25 - controls and operational subsystems."""
import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rpc import Endpoint, make_frame  # noqa: E402
from wrpc import controls as C, ops as O  # noqa: E402


class AuthorizerTest(unittest.TestCase):
    def test_default_deny_grant_and_deny_precedence(self):
        a = C.Authorizer([C.Grant("t1", "svc-*", "pk:kv/*", "get")], [C.Grant("t1", "svc-bad", "*", "*")])
        self.assertEqual(a.decide("t1", "svc-a", "pk:kv/store", "get", 0)[2], "granted")
        self.assertEqual(a.decide("t1", "svc-a", "pk:kv/store", "put", 0)[2], "default-deny")
        self.assertEqual(a.decide("t1", "svc-bad", "pk:kv/store", "get", 0)[2], "explicit-deny")

    def test_no_cross_tenant_glob_and_expiry_and_revoke(self):
        a = C.Authorizer([C.Grant("t1", "*", "*", "*", not_after=100)])
        self.assertFalse(a.decide("t2", "x", "i", "f", 0)[0])
        self.assertTrue(a.decide("t1", "x", "i", "f", 99)[0])
        self.assertFalse(a.decide("t1", "x", "i", "f", 100)[0])
        self.assertEqual(a.revoke(lambda g: g.tenant == "t1"), 1)
        self.assertFalse(a.decide("t1", "x", "i", "f", 0)[0])


class IdempotencyRetryTest(unittest.TestCase):
    def test_duplicate_returns_first_outcome_without_reexecution(self):
        calls = []
        c = C.IdempotencyCache()
        r1, dup1 = c.run(("t", "r"), lambda: (calls.append(1) or {"ok": 1}, True), now=0)
        r2, dup2 = c.run(("t", "r"), lambda: (calls.append(2) or {"ok": 2}, True), now=1)
        self.assertEqual((r1, r2, dup1, dup2, calls), ({"ok": 1}, {"ok": 1}, False, True, [1]))

    def test_concurrent_duplicates_execute_once(self):
        c, calls, gate = C.IdempotencyCache(), [], threading.Event()

        def slow():
            gate.wait(2)
            calls.append(1)
            return {"ok": "v"}, True
        out = []
        ts = [threading.Thread(target=lambda: out.append(c.run(("t", "same"), slow))) for _ in range(16)]
        [t.start() for t in ts]
        gate.set()
        [t.join() for t in ts]
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(o[0] == {"ok": "v"} for o in out))

    def test_ttl_expiry_and_tenant_scoping(self):
        c = C.IdempotencyCache(ttl_s=10)
        c.run(("t1", "r"), lambda: ({"ok": 1}, True), now=0)
        self.assertEqual(c.run(("t2", "r"), lambda: ({"ok": 2}, True), now=1)[0], {"ok": 2})
        self.assertEqual(c.run(("t1", "r"), lambda: ({"ok": 3}, True), now=11)[0], {"ok": 3})

    def test_journal_survives_restart_and_torn_tail(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "j.jsonl")
            j = O.Journal(p)
            c = C.IdempotencyCache(journal=j)
            c.run(("t", "r1"), lambda: ({"ok": 1}, True), now=0)
            with open(p, "a") as fh:
                fh.write('{"k": ["t", "r2"], "ts"')          # crash mid-write
            c2 = C.IdempotencyCache(journal=O.Journal(p))
            calls = []
            self.assertEqual(c2.run(("t", "r1"), lambda: (calls.append(1) or {"ok": 9}, True), now=1)[0], {"ok": 1})
            self.assertEqual(calls, [])
            with open(p, "w") as fh:
                fh.write("garbage\n" + json.dumps({"k": ["t", "x"], "ts": 0, "o": {}}) + "\n")
            with self.assertRaises(ValueError):
                O.Journal(p).replay()

    def test_transient_outcome_not_cached_so_retry_runs(self):
        """Regression (assessor defect 1): 'overloaded' used to be cached for the TTL."""
        c, calls = C.IdempotencyCache(), []
        r1, _ = c.run(("t", "r"), lambda: ({"error": "overloaded"}, False), now=0)
        r2, dup = c.run(("t", "r"), lambda: (calls.append(1) or {"ok": 1}, True), now=1)
        self.assertEqual((r1["error"], r2, dup, calls), ("overloaded", {"ok": 1}, False, [1]))

    def test_request_id_reuse_for_different_call_conflicts(self):
        """Regression (assessor defect 2): key ignored which call it answered."""
        c = C.IdempotencyCache()
        c.run(("t", "r"), lambda: ({"ok": "put-result"}, True), now=0, call_digest="put")
        self.assertEqual(c.run(("t", "r"), lambda: ({"ok": "x"}, True), now=1, call_digest="get")[0],
                         {"error": "idempotency-conflict"})

    def test_capacity_evicts_oldest_instead_of_refusing(self):
        """Regression (soak defect): a full cache used to answer every new id 'overloaded'."""
        c = C.IdempotencyCache(max_entries=3)
        for i in range(10):
            self.assertEqual(c.run(("t", str(i)), lambda i=i: ({"ok": i}, True), now=0)[0], {"ok": i})
        self.assertEqual((len(c._done), c.evictions), (3, 7))

    def test_retry_honours_retry_after_hint(self):
        slept = []
        seq = iter([{"error": "overloaded", "retry_after_ms": 400}, {"ok": 1}])
        C.RetryPolicy(base_s=0.0, budget_ratio=10).call(lambda a: next(seq), 1e18, True, sleep=slept.append)
        self.assertEqual(slept, [0.4])

    def test_retry_only_idempotent_retryable_and_within_deadline(self):
        seq = iter([{"error": "unavailable"}, {"error": "unavailable"}, {"ok": 1}])
        p = C.RetryPolicy(base_s=0.001, budget_ratio=10)
        self.assertEqual(p.call(lambda n: next(seq), deadline=1e18, idempotent=True, sleep=lambda s: None), {"ok": 1})
        n = []
        p.call(lambda a: n.append(a) or {"error": "unavailable"}, 1e18, idempotent=False, sleep=lambda s: None)
        self.assertEqual(n, [0])
        n = []
        p.call(lambda a: n.append(a) or {"error": "signature-mismatch"}, 1e18, True, sleep=lambda s: None)
        self.assertEqual(n, [0])
        r = C.RetryPolicy(base_s=10, budget_ratio=10).call(lambda a: {"error": "unavailable"}, deadline=0.5,
                                                           idempotent=True, clock=lambda: 0.0, sleep=lambda s: None)
        self.assertIn(r["error"], ("deadline-exceeded", "unavailable"))

    def test_retry_budget_caps_amplification(self):
        p = C.RetryPolicy(max_attempts=10, base_s=0, budget_ratio=0.1)
        attempts = []
        for _ in range(100):
            p.call(lambda a: attempts.append(a) or {"error": "unavailable"}, 1e18, True, sleep=lambda s: None)
        self.assertLessEqual(len(attempts), 100 * 1.1 + 2)

    def test_backoff_bounded(self):
        p = C.RetryPolicy(base_s=0.1, cap_s=1.0)
        self.assertTrue(all(0 <= p.backoff(a, rng=lambda: 1.0) <= 1.0 for a in range(20)))

    def test_cancel_token(self):
        t = C.CancelToken()
        self.assertFalse(t.cancelled)
        t.cancel("client-gone")
        self.assertTrue(t.cancelled)
        self.assertEqual(t.reason, "client-gone")


class AdmissionBreakerLeaseTest(unittest.TestCase):
    def test_admission_bounds_and_per_tenant_fairness(self):
        a = C.Admission(max_inflight=2, max_queue=0, per_tenant=1)
        self.assertTrue(a.acquire("t1", 0))
        self.assertFalse(a.acquire("t1", 0))           # tenant cap
        self.assertTrue(a.acquire("t2", 0))
        self.assertFalse(a.acquire("t3", 0))           # global cap, no queue
        a.release("t1")
        self.assertTrue(a.acquire("t3", 0))

    def test_admission_queue_wakes_waiter(self):
        a = C.Admission(max_inflight=1, max_queue=1, per_tenant=5)
        a.acquire("t", 0)
        got = []
        th = threading.Thread(target=lambda: got.append(a.acquire("t", 2)))
        th.start()
        a.release("t")
        th.join()
        self.assertEqual(got, [True])

    def test_breaker_state_machine(self):
        now = [0.0]
        b = C.CircuitBreaker(threshold=2, cooldown_s=5, clock=lambda: now[0])
        b.record(False)
        self.assertTrue(b.allow())
        b.record(False)
        self.assertEqual(b.state, "open")
        self.assertFalse(b.allow())
        now[0] = 5
        self.assertTrue(b.allow())          # half-open probe
        self.assertFalse(b.allow())         # only one probe
        b.record(False)
        self.assertEqual(b.state, "open")
        now[0] = 10
        b.allow()
        b.record(True)
        self.assertEqual(b.state, "closed")

    def test_fencing_prevents_duplicate_owner_writes(self):
        now = [0.0]
        L = C.LeaseTable(clock=lambda: now[0])
        t1 = L.acquire("k", "A", 10)
        self.assertIsNone(L.acquire("k", "B", 10))
        now[0] = 11                          # A paused past expiry: failover to B
        t2 = L.acquire("k", "B", 10)
        self.assertGreater(t2, t1)
        self.assertFalse(L.check("k", t1))   # A wakes: its write is refused
        self.assertTrue(L.check("k", t2))
        L.freeze("k")
        self.assertFalse(L.check("k", t2))
        self.assertIsNone(L.acquire("k", "C", 10))
        L.thaw("k")
        self.assertTrue(L.check("k", t2))


class ConcurrencyTest(unittest.TestCase):
    """M25: counters and caches keep exact totals under contention."""

    def test_endpoint_stats_exact_under_threads(self):
        ep = Endpoint("kv", "1")
        ep.export("f", [], ["u8"], lambda: 1)
        fr = make_frame("kv", "1", "f", [], ["u8"], [], 1e18)
        N, T = 2000, 8

        def work():
            for _ in range(N):
                ep.handle(fr, 0)
        ts = [threading.Thread(target=work) for _ in range(T)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual((ep.stats.calls, ep.stats.succeeded), (N * T, N * T))

    def test_concurrent_export_duplicate_detected_once(self):
        ep = Endpoint("kv", "1")
        errors = []

        def exp():
            try:
                ep.export("same", [], [], lambda: 0)
            except ValueError:
                errors.append(1)
        ts = [threading.Thread(target=exp) for _ in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(errors), 15)

    def test_metrics_and_audit_under_threads(self):
        m, a = O.Metrics(), O.AuditLog()

        def work():
            for _ in range(500):
                m.inc("c", outcome="ok")
                a.append("e")
        ts = [threading.Thread(target=work) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(m.counters[("c", (("outcome", "ok"),))], 4000)
        self.assertEqual(O.AuditLog.verify(a.records), (True, "ok"))


class OpsTest(unittest.TestCase):
    def test_config_layers_provenance_validation_rollback(self):
        s = O.ConfigStore()
        d1 = s.activate(("file", {"max_inflight": 10}))
        self.assertEqual(s.provenance["sources"]["max_inflight"], "file")
        d2 = s.activate(("env", {"max_inflight": 20}))
        self.assertNotEqual(d1, d2)
        for bad in [{"nope": 1}, {"max_inflight": 0}, {"max_inflight": "10"}, {"log_level": "TRACE"},
                    {"psk_ref": "deadbeef" * 8}]:
            with self.assertRaises(O.ConfigError):
                s.activate(("bad", bad))
        self.assertEqual(s.active["max_inflight"], 20)         # failed activation changed nothing
        self.assertEqual(s.rollback(), d1)

    def test_secret_resolution_by_reference_only(self):
        os.environ["INV61_TEST_PSK"] = "ab" * 32
        self.assertEqual(O.resolve_secret("env:INV61_TEST_PSK"), bytes.fromhex("ab" * 32))
        with self.assertRaises(O.ConfigError):
            O.resolve_secret("env:INV61_MISSING_PSK")

    def test_audit_chain_detects_edit_delete_reorder_truncate(self):
        with tempfile.TemporaryDirectory() as d:
            a = O.AuditLog(os.path.join(d, "a.jsonl"))
            for i in range(5):
                a.append("authz", "t", "p", f"s{i}", "allow", "granted")
            head = a.head()
            recs = list(O.AuditLog(os.path.join(d, "a.jsonl")).records)     # reload from disk
            self.assertEqual(O.AuditLog.verify(recs, head), (True, "ok"))
            edited = [dict(r) for r in recs]
            edited[2]["decision"] = "deny"
            self.assertFalse(O.AuditLog.verify(edited)[0])
            self.assertFalse(O.AuditLog.verify(recs[:2] + recs[3:])[0])
            self.assertFalse(O.AuditLog.verify([recs[1], recs[0]] + recs[2:])[0])
            self.assertTrue(O.AuditLog.verify(recs[:4])[0])          # truncation alone passes the chain...
            self.assertFalse(O.AuditLog.verify(recs[:4], head)[0])   # ...and is caught by the external head

    def test_audit_memory_window_is_bounded_and_verifiable(self):
        a = O.AuditLog(max_memory_records=50)
        for i in range(500):
            a.append("e", subject=str(i))
        self.assertEqual(len(a.records), 50)
        self.assertEqual(a.head()[0], 500)
        self.assertEqual(O.AuditLog.verify(a.records, a.head(), window=True), (True, "ok"))
        w = list(a.records)
        w[10] = dict(w[10], reason="edited")
        self.assertFalse(O.AuditLog.verify(w, a.head(), window=True)[0])

    def test_metrics_exposition_and_cardinality_cap(self):
        m = O.Metrics(max_series=3)
        m.inc("inv61_calls_total", interface="a", outcome="ok")
        m.observe("inv61_handle_seconds", 0.0002)
        for i in range(10):
            m.inc("inv61_calls_total", interface=f"x{i}", outcome="ok")
        text = m.render()
        self.assertIn('inv61_calls_total{interface="a",outcome="ok"} 1', text)
        self.assertIn('inv61_handle_seconds_bucket{le="0.0005"} 1', text)
        self.assertIn("inv61_metric_series_dropped_total 9", text)
        with self.assertRaises(ValueError):
            m.inc("x", request_id="unbounded")

    def test_logger_redacts_truncates_filters_ratelimits(self):
        lines = []
        lg = O.JsonLogger(lines.append, "INFO", max_field=8, rate_per_s=3, clock=lambda: 100.0)
        lg.log("DEBUG", "hidden")
        lg.log("INFO", "call", psk="s3cr3t", args=[1, 2], note="0123456789abc", nested={"token": "t"})
        rec = json.loads(lines[0])
        self.assertEqual((rec["psk"], rec["args"], rec["nested"]["token"]), ("[REDACTED]",) * 3)
        self.assertTrue(rec["note"].endswith("[truncated]"))
        for _ in range(5):
            lg.log("INFO", "flood")
        self.assertEqual((len(lines), lg.suppressed), (3, 3))

    def test_traceparent(self):
        tp, span, sampled = O.child_traceparent(None, 1.0)
        tid = O.parse_traceparent(tp)[0]
        child, _, s2 = O.child_traceparent(tp, 0.0)
        self.assertEqual(O.parse_traceparent(child)[0], tid)           # trace id propagates
        self.assertTrue(s2)                                            # parent's sampled flag wins
        for bad in ["", "00-" + "0" * 32 + "-" + "1" * 16 + "-01", "zz", "01-" + "a" * 32 + "-" + "b" * 16 + "-01x"]:
            self.assertIsNone(O.parse_traceparent(bad))
        spans = []
        with O.Tracer(spans.append).span("x", tp, interface="i", psk="no"):
            pass
        self.assertEqual(spans[0]["attrs"], {"interface": "i"})

    def test_health_check_is_time_boxed(self):
        import time as _t
        h = O.Health(cache_s=0, check_timeout_s=0.1)
        h.register("hung", lambda: _t.sleep(5))
        t0 = _t.monotonic()
        r = h.ready()
        self.assertLess(_t.monotonic() - t0, 1.0)
        self.assertEqual(r["checks"]["hung"]["detail"], "timeout")

    def test_tracer_exporter_failure_never_fails_call(self):
        tp, _, _ = O.child_traceparent(None, 1.0)
        t = O.Tracer(lambda span: 1 / 0)
        with t.span("x", tp):
            pass
        self.assertEqual(t.export_failures, 1)

    def test_health_readiness(self):
        h = O.Health(cache_s=0)
        state = {"db": True}
        h.register("db", lambda: state["db"])
        h.register("opt", lambda: 1 / 0, critical=False)
        self.assertEqual(h.ready()["status"], "warn")
        state["db"] = False
        self.assertEqual(h.ready()["status"], "fail")
        state["db"] = True
        h.draining = True
        self.assertEqual(h.ready()["status"], "fail")
        self.assertEqual(h.live()["status"], "pass")


if __name__ == "__main__":
    unittest.main()
