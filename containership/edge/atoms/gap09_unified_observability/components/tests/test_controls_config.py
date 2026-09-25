"""Components 09, 12, 13, 15, 36, 37, 39, 41, 42."""
import unittest

from fixtures import Clock, make_stack, sample, signed, tmpdir
from gap09_unified_observability.components.config import ConfigManager, validate, digest
from gap09_unified_observability.components.controls import (AdmissionController, CircuitBreaker, DecisionLog,
                                                             HealthModel, QuarantineRegistry, TenantCardinalityQuota,
                                                             TimeAuthority)
from gap09_unified_observability.components.errors import (ConfigRejected, DependencyUnavailable, Quarantined,
                                                           QuotaExceeded, Throttled, TimeUntrusted, Unauthorized)
from gap09_unified_observability.components.replication import FencedReplica, LeaseAuthority

BASE = dict(staleness_bound=60, max_batch_size=1000, replay_window=3600, max_clock_skew=5, tenant_rate=100.0,
            tenant_burst=200.0, reporter_rate=10.0, reporter_burst=20.0, tenant_series_limit=1000,
            retention_seconds=86400, allow_legacy_trust=False)


class TestTime(unittest.TestCase):
    def test_skew_and_confidence(self):
        c = Clock(1000, 990)
        t = TimeAuthority(c, max_skew=5, max_sync_age=60)
        self.assertEqual(t.check_reported(1005), 1000)            # exactly at skew bound
        with self.assertRaises(TimeUntrusted):
            t.check_reported(1006)
        c.synced = 939                                            # 61 s since sync
        with self.assertRaises(TimeUntrusted):
            t.now()
        t2 = TimeAuthority(lambda: (_ for _ in ()).throw(OSError()), max_skew=5, max_sync_age=60)
        with self.assertRaises(TimeUntrusted):
            t2.now()

    def test_ingest_refuses_when_time_untrusted(self):
        ingest, _, clock, _ = make_stack(tmpdir())
        clock.synced = 0
        with self.assertRaises(TimeUntrusted):
            ingest.submit(**signed([sample()]))


class TestAdmissionQuota(unittest.TestCase):
    def test_tenant_fairness_and_retry_after(self):
        a = AdmissionController(tenant_rate=1, tenant_burst=2, reporter_rate=100, reporter_burst=100, max_inflight=10)
        a.admit(tenant="noisy", reporter="r1", cost=2, now=0); a.release()
        with self.assertRaises(Throttled) as cm:
            a.admit(tenant="noisy", reporter="r1", cost=1, now=0)
        self.assertAlmostEqual(cm.exception.retry_after, 1.0)
        a.admit(tenant="quiet", reporter="r2", cost=2, now=0)    # other tenant unaffected
        a.release()
        a.admit(tenant="noisy", reporter="r1", cost=1, now=1.0)  # refilled after retry_after
        self.assertTrue(any(d["rule"] == "ADM-TENANT" for d in a.decisions.recent()))

    def test_global_shedding(self):
        a = AdmissionController(tenant_rate=100, tenant_burst=100, reporter_rate=100, reporter_burst=100, max_inflight=1)
        a.admit(tenant="t", reporter="r", cost=1, now=0)
        with self.assertRaises(Throttled):
            a.admit(tenant="t2", reporter="r2", cost=1, now=0)
        self.assertEqual(a.shed, 1)

    def test_per_tenant_series_quota(self):
        q = TenantCardinalityQuota(2, overrides={"big": 5})
        q.reserve("t1", ["a", "b"])
        q.reserve("t1", ["a"])                                   # existing key costs nothing
        with self.assertRaises(QuotaExceeded):
            q.reserve("t1", ["c"])
        q.reserve("t2", ["a", "b"])                              # t1 exhaustion does not affect t2
        q.reserve("big", list("abcde"))
        self.assertEqual(q.usage(), {"t1": 2, "t2": 2, "big": 5})

    def test_quota_enforced_before_commit_in_ingest(self):
        ingest, *_ = make_stack(tmpdir(), tenant_series=1)
        ingest.submit(**signed([sample("cpu")]))
        with self.assertRaises(QuotaExceeded):
            ingest.submit(**signed([sample("mem")], sid="s2"))
        self.assertEqual(len(ingest.store.latest), 1)


class TestConfig(unittest.TestCase):
    def test_validate_digest_activate_rollback(self):
        m = ConfigManager(BASE, author="ops")
        d1 = m.active_digest()
        m.apply({**BASE, "staleness_bound": 30}, author="ops", at=5, reason="tighten")
        self.assertNotEqual(m.active_digest(), d1)
        m.rollback(author="ops", at=6)
        self.assertEqual(m.active_digest(), d1)
        self.assertEqual(digest(BASE), d1)

    def test_rejections_leave_active_unchanged(self):
        m = ConfigManager(BASE, author="ops")
        d = m.active_digest()
        for bad in ({**BASE, "unknown": 1}, {**BASE, "allow_legacy_trust": True}, {**BASE, "staleness_bound": 0},
                    {**BASE, "staleness_bound": True}, {k: v for k, v in BASE.items() if k != "replay_window"},
                    {**BASE, "tenant_burst": 1.0}):
            with self.assertRaises(ConfigRejected):
                m.apply(bad, author="ops", at=1, reason="x")
        self.assertEqual(m.active_digest(), d)

    def test_overlays(self):
        merged = ConfigManager.merge(BASE, {"staleness_bound": 120}, {"max_clock_skew": 2})
        validate(merged)
        self.assertEqual((merged["staleness_bound"], merged["max_clock_skew"]), (120, 2))


class TestQuarantineBreakerHealth(unittest.TestCase):
    def test_quarantine_scoped(self):
        ingest, *_ = make_stack(tmpdir())
        ingest.quarantine.freeze("site", "s1", reason="compromise", actor="ops")
        with self.assertRaises(Quarantined):
            ingest.submit(**signed([sample()]))
        self.assertEqual(ingest.submit(**signed([sample(site="s2")], sid="s2")), 1)   # unrelated site continues
        ingest.quarantine.release("site", "s1", actor="ops")
        self.assertEqual(ingest.submit(**signed([sample(at=101)], sid="s3")), 1)

    def test_breaker(self):
        b = CircuitBreaker("trust", threshold=2, cooldown=10)
        def boom(): raise OSError()
        for _ in range(2):
            with self.assertRaises(OSError):
                b.call(boom, 0)
        with self.assertRaises(DependencyUnavailable):
            b.call(lambda: 1, 5)
        self.assertEqual(b.call(lambda: 1, 10), 1)              # half-open probe succeeds
        self.assertEqual(b.state, "closed")

    def test_health_degrades(self):
        up = {"v": True}
        h = HealthModel("5.1.0", lambda: "d" * 64, {"trust": lambda: up["v"]}, lambda: 0.1, ("submit", "query"))
        self.assertTrue(h.report()["ready"])
        up["v"] = False
        r = h.report()
        self.assertEqual((r["ready"], r["mode"], r["dependencies"]["trust"]), (False, "degraded", "down"))

    def test_decision_log_bounded(self):
        d = DecisionLog(capacity=3)
        for i in range(5):
            d.record(decision="drop", reason="r", subject={}, rule="R", at=i)
        self.assertEqual((len(d.recent()), d.total), (3, 5))


class TestFencing(unittest.TestCase):
    def test_split_brain_refused(self):
        la, rep = LeaseAuthority(ttl=10), FencedReplica()
        e1 = la.acquire("p", "node-a", 0)
        with self.assertRaises(Unauthorized):
            la.acquire("p", "node-b", 5)
        e2 = la.acquire("p", "node-b", 11)                      # a's lease expired
        rep.write("p", e2, "k", "from-b")
        with self.assertRaises(Unauthorized):
            rep.write("p", e1, "k", "from-a-zombie")
        self.assertEqual(rep.data[("p", "k")], "from-b")


if __name__ == "__main__":
    unittest.main()
