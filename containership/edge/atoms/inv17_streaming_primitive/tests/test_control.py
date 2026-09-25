"""C016/C027/C093 versions, C017/C028 quotas+fairness, C052 health, C054 shedding/breaker,
C057 crash semantics, C059 quarantine/disable."""
import unittest

from _pkg import control as C, security as X, stream as S, open_stream, registry


class VersionTest(unittest.TestCase):
    def test_negotiate(self):
        self.assertEqual(C.negotiate("PK_STREAM", [1, 2, 3]), 1)
        for bad in ([2], [], [True]):
            with self.assertRaises(C.VersionUnsupported): C.negotiate("PK_STREAM", bad)
        with self.assertRaises(C.VersionUnsupported): C.negotiate("PK_NOPE", [1])

    def test_open_refuses_unsupported_version(self):
        r = registry()
        tok = r.authority.issue("s", "t", "w", ["open"])
        with self.assertRaises(C.VersionUnsupported):
            r.open(int, tenant="t", workload="w", token=tok, stream_id="s", versions={"PK_STREAM": [2]})
        self.assertEqual(r.streams(), [])


class QuotaFairnessTest(unittest.TestCase):
    def test_stream_quota(self):
        r = registry(quotas={"t1": C.TenantQuota(max_streams=2)})
        open_stream(r, "a"); open_stream(r, "b")
        with self.assertRaises(C.QuotaExceeded): open_stream(r, "c")
        open_stream(r, "d", tenant="t2")  # other tenants unaffected
        self.assertEqual(r.audit.events[-2].kind, "quota.denied")

    def test_buffered_quota_and_global_shedding(self):
        r = registry(quotas={"t1": C.TenantQuota(max_buffered=2)}, global_buffer_budget=3)
        s, tok = open_stream(r, "a"); s.grant(5)
        r.write("a", 1, tenant="t1", workload="w1", token=tok); r.write("a", 2, tenant="t1", workload="w1", token=tok)
        with self.assertRaises(C.QuotaExceeded): r.write("a", 3, tenant="t1", workload="w1", token=tok)
        s2, tok2 = open_stream(r, "b", tenant="t2"); s2.grant(5)
        r.write("b", 1, tenant="t2", workload="w1", token=tok2)
        with self.assertRaises(C.LoadShed): r.write("b", 2, tenant="t2", workload="w1", token=tok2)
        self.assertEqual(r.shed_count, 2)

    def test_breaker_opens_and_recovers(self):
        now = [0.0]
        r = registry(global_buffer_budget=1, clock=lambda: now[0])
        s, tok = open_stream(r, "a"); s.grant(10)
        r.write("a", 1, tenant="t1", workload="w1", token=tok)
        for _ in range(5):
            with self.assertRaises(C.LoadShed): r.write("a", 1, tenant="t1", workload="w1", token=tok)
        self.assertEqual(r.breaker.state, "open")
        with self.assertRaises(C.CircuitOpen): open_stream(r, "b")
        self.assertEqual(r.health().status, "degraded")
        now[0] += 6
        s.read()
        open_stream(r, "b")  # half-open lets a probe through
        r.write("a", 2, tenant="t1", workload="w1", token=tok)
        self.assertEqual(r.breaker.state, "closed")

    def test_fair_scheduler_no_starvation(self):
        f = C.FairCreditScheduler({"big": 9, "small": 1})
        g = f.allocate(10, {"big": 1000, "small": 1000})
        self.assertEqual(sum(g.values()), 10)
        self.assertGreaterEqual(g["small"], 1)
        self.assertGreater(g["big"], g["small"])
        self.assertEqual(f.allocate(5, {"a": 2, "b": 0}), {"a": 2, "b": 0})
        with self.assertRaises(ValueError): f.allocate(-1, {})

    def test_registry_rebalance(self):
        r = registry(quotas={"heavy": C.TenantQuota(weight=4), "light": C.TenantQuota(weight=1)})
        for i in range(4):
            open_stream(r, f"h{i}", tenant="heavy")
        open_stream(r, "l0", tenant="light")
        g = r.rebalance(10)
        self.assertEqual(sum(g.values()), 10)
        self.assertGreaterEqual(g.get("l0", 0), 1)
        light = sum(v for k, v in g.items() if k.startswith("l"))
        self.assertLess(light, 10)

    def test_quota_validation(self):
        with self.assertRaises(ValueError): C.TenantQuota(max_streams=0)


class HealthTest(unittest.TestCase):
    def test_stall_ratio_and_duration(self):
        now = [0.0]
        r = registry(clock=lambda: now[0])
        self.assertEqual(r.health().status, "healthy")
        s, _ = open_stream(r)
        s.grant(1); s.write(1)
        for _ in range(10):
            with self.assertRaises(S.CreditExhausted): s.write(1)
        h = r.health()  # ratio 10/11 over min_attempts? no: 11 < 20 attempts
        self.assertIn(h.status, ("healthy", "degraded"))
        for _ in range(20):
            with self.assertRaises(S.CreditExhausted): s.write(1)
        self.assertEqual(r.health().status, "unhealthy")
        r2 = registry(clock=lambda: now[0])
        s2, _ = open_stream(r2)
        with self.assertRaises(S.CreditExhausted): s2.write(1)
        r2.health(); now[0] += 31
        h2 = r2.health()
        self.assertEqual(h2.status, "unhealthy")
        self.assertIn("credit stalled", h2.reasons[0])
        s2.grant(1)
        self.assertEqual(r2.health().status, "healthy")

    def test_buffer_fill_degraded(self):
        r = registry()
        s, _ = open_stream(r, config=S.StreamConfig(max_credit=10, max_buffer=10))
        s.grant(10)
        for i in range(9): s.write(i)
        self.assertEqual(r.health().status, "degraded")


class ControlTest(unittest.TestCase):
    def test_emergency_disable_and_enable(self):
        r = registry()
        s, tok = open_stream(r); s.grant(2); s.write(1)
        with self.assertRaises(X.AuthzDenied): r.emergency_disable("mallory", "x")
        r.emergency_disable("sre-oncall", "INC-1")
        self.assertEqual(r.health().status, "disabled")
        with self.assertRaises(C.ComponentDisabled): open_stream(r, "b")
        with self.assertRaises(C.ComponentDisabled): r.write("s1", 2, tenant="t1", workload="w1", token=tok)
        with self.assertRaises(S.StreamFrozen): s.write(2)
        self.assertEqual(s.read(), 1)  # drain allowed
        manual, _ = open_stream(registry(), "m")  # separate registry, unaffected
        r.enable("sre-oncall", "INC-1 resolved")
        s.write(2)
        kinds = [e.kind for e in r.audit.events]
        self.assertIn("control.disable", kinds); self.assertIn("control.enable", kinds)
        self.assertEqual(r.audit.verify(), [])

    def test_enable_does_not_lift_unrelated_freezes(self):
        r = registry()
        a, _ = open_stream(r, "a"); b, _ = open_stream(r, "b", tenant="t2")
        a.freeze("manual investigation")
        r.quarantine("sre-oncall", scope="tenant", value="t2", reason="abuse")
        r.emergency_disable("sre-oncall", "INC"); r.enable("sre-oncall", "done")
        self.assertTrue(a.frozen); self.assertTrue(b.frozen)
        r.release("sre-oncall", scope="tenant", value="t2")
        self.assertFalse(b.frozen); self.assertTrue(a.frozen)

    def test_quarantine_scope(self):
        r = registry()
        open_stream(r, "a", workload="bad"); open_stream(r, "b", workload="good")
        self.assertEqual(r.quarantine("sre-oncall", scope="workload", value="bad", reason="x"), 1)
        with self.assertRaises(C.ComponentDisabled): open_stream(r, "c", workload="bad")
        open_stream(r, "d", workload="good")
        with self.assertRaises(ValueError): r.quarantine("sre-oncall", scope="site", value="x", reason="x")


class CrashSemanticsTest(unittest.TestCase):
    def test_restart_loses_streams_explicitly(self):
        auth = X.CapabilityAuthority()
        r = C.StreamRegistry(authority=auth)
        tok = auth.issue("s", "t", "w", ["open", "write", "read"])
        r.open(int, tenant="t", workload="w", token=tok, stream_id="s")
        r2 = C.StreamRegistry(authority=auth)  # "process restart": fresh memory
        with self.assertRaises(C.StreamNotFound) as cm:
            r2.get("s", tenant="t", workload="w", token=tok, right="read")
        self.assertEqual(cm.exception.code, "PK_STREAM_NOT_FOUND")

    def test_duplicate_open_and_close(self):
        r = registry()
        open_stream(r, "a")
        tok = r.authority.issue("a", "t1", "w1", ["open"])
        with self.assertRaises(S.StreamError):
            r.open(int, tenant="t1", workload="w1", token=tok, stream_id="a")
        r.close("a"); self.assertEqual(r.streams(), [])


if __name__ == "__main__":
    unittest.main()
