"""C025 / C053 / C054 / C055 / C056 / C058 resilience tests."""
import importlib
import random
import threading
import unittest

import _path
r = importlib.import_module(_path.PKG + ".resilience")


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class DeadlineCancel(unittest.TestCase):
    def test_deadline(self):
        c = FakeClock()
        d = r.Deadline(1.0, clock=c)
        self.assertFalse(d.expired)
        c.t = 1.0
        self.assertTrue(d.expired)
        for bad in (0, -1, 301):
            with self.assertRaises(ValueError):
                r.Deadline(bad)

    def test_cancel(self):
        t = r.CancelToken()
        self.assertFalse(t.cancelled)
        t.cancel("user")
        self.assertTrue(t.cancelled)
        self.assertEqual(t.reason, "user")


class Idempotency(unittest.TestCase):
    def test_replay_conflict_inflight_ttl_eviction(self):
        c = FakeClock()
        cache = r.IdempotencyCache(capacity=2, ttl_s=10, clock=c)
        self.assertEqual(cache.begin("k", "f1"), ("new", None))
        self.assertEqual(cache.begin("k", "f1"), ("inflight", None))        # C058 duplicate
        self.assertEqual(cache.begin("k", "f2"), ("conflict", None))
        cache.finish("k", "f1", {"v": 1})
        self.assertEqual(cache.begin("k", "f1"), ("replay", {"v": 1}))
        self.assertEqual(cache.begin("k", "f2"), ("conflict", None))
        c.t = 11
        self.assertEqual(cache.begin("k", "f1"), ("new", None))
        cache.finish("k", "f1", 1)
        for k in ("a", "b"):
            cache.begin(k, "f")
            cache.finish(k, "f", 0)
        self.assertEqual(len(cache._d), 2)

    def test_non_cacheable_result_allows_reexecution(self):
        cache = r.IdempotencyCache()
        cache.begin("k", "f")
        cache.finish("k", "f", "boom", cacheable=False)
        self.assertEqual(cache.begin("k", "f"), ("new", None))

    def test_concurrent_duplicates_only_one_new(self):
        cache = r.IdempotencyCache()
        results = []
        def go():
            results.append(cache.begin("same", "f")[0])
        th = [threading.Thread(target=go) for _ in range(32)]
        [t.start() for t in th]
        [t.join() for t in th]
        self.assertEqual(results.count("new"), 1)


class Retry(unittest.TestCase):
    def test_backoff_bounded_full_jitter(self):
        p = r.RetryPolicy(rng=random.Random(1))
        for a in range(1, 10):
            d = p.backoff(a)
            self.assertTrue(0 <= d <= p.cap_s)

    def test_only_idempotent_retryable_reasons(self):
        p = r.RetryPolicy()
        self.assertTrue(p.retryable("overloaded: rate", True))
        self.assertFalse(p.retryable("overloaded: rate", False))
        for reason in ("out of fuel", "capability denied: x", "deadline exceeded", "unauthenticated"):
            self.assertFalse(p.retryable(reason, True))

    def test_attempt_cap_and_budget(self):
        calls = []
        p = r.RetryPolicy(max_attempts=3, rng=random.Random(0))
        out = p.call(lambda: calls.append(1) or {"trap": "overloaded"}, idempotent=True, sleep=lambda s: None)
        self.assertEqual(len(calls), 3)
        self.assertEqual(out["trap"], "overloaded")
        # retry budget: exhaust tokens, then no more retries
        p2 = r.RetryPolicy(max_attempts=5, rng=random.Random(0))
        p2._tokens = 0
        calls.clear()
        p2.call(lambda: calls.append(1) or {"trap": "overloaded"}, idempotent=True, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_deadline_stops_retry(self):
        c = FakeClock()
        d = r.Deadline(0.001, clock=c)
        c.t = 0.001
        calls = []
        r.RetryPolicy().call(lambda: calls.append(1) or {"trap": "overloaded"}, idempotent=True, deadline=d,
                             sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_bad_policy(self):
        with self.assertRaises(ValueError):
            r.RetryPolicy(max_attempts=0)


class AdmissionBreaker(unittest.TestCase):
    def test_concurrency_tenant_rate(self):
        c = FakeClock()
        a = r.Admission(max_concurrent=3, rate_per_s=1, burst=10, per_tenant_concurrent=2, clock=c)
        self.assertIsNone(a.try_acquire("t1"))
        self.assertIsNone(a.try_acquire("t1"))
        self.assertEqual(a.try_acquire("t1"), "overloaded: tenant quota")
        self.assertIsNone(a.try_acquire("t2"))
        self.assertEqual(a.try_acquire("t3"), "overloaded: concurrency")
        for t in ("t1", "t1", "t2"):
            a.release(t)
        a2 = r.Admission(max_concurrent=100, rate_per_s=1, burst=2, per_tenant_concurrent=100, clock=c)
        a2.try_acquire("x"); a2.try_acquire("x")
        self.assertEqual(a2.try_acquire("x"), "overloaded: rate")
        c.t += 1
        self.assertIsNone(a2.try_acquire("x"))

    def test_breaker_cycle(self):
        c = FakeClock()
        b = r.CircuitBreaker(threshold=2, cooldown_s=5, clock=c)
        b.record(False); b.record(False)
        self.assertFalse(b.allow())
        c.t = 5
        self.assertTrue(b.allow())      # half-open probe
        self.assertFalse(b.allow())     # only one probe
        b.record(False)
        self.assertEqual(b.state, "open")
        c.t = 10
        self.assertTrue(b.allow())
        b.record(True)
        self.assertEqual(b.state, "closed")


class Failover(unittest.TestCase):
    def test_never_violates_isolation_residency_consistency(self):
        sites = [r.Site("a", "us", frozenset({"t1"}), healthy=False, config_digest="d"),
                 r.Site("b", "eu", frozenset({"t1"}), config_digest="d"),
                 r.Site("c", "us", frozenset({"t2"}), config_digest="d"),
                 r.Site("d", "us", frozenset({"t1"}), config_digest="OTHER"),
                 r.Site("e", "us", frozenset({"t1"}), config_digest="d")]
        self.assertEqual(r.select_failover(sites, tenant="t1", residency={"us"}, config_digest="d").name, "e")
        self.assertIsNone(r.select_failover(sites, tenant="t1", residency={"us"}, config_digest="d", exclude={"e"}))
        self.assertIsNone(r.select_failover(sites, tenant="t9", residency={"us", "eu"}, config_digest="d"))


class Degraded(unittest.TestCase):
    def test_mode_precedence(self):
        base = dict(trust_ok=True, time_ok=True, audit_ok=True, control_plane_ok=True, overload=False, draining=False)
        self.assertEqual(r.derive_mode(**base), r.Mode.NORMAL)
        for k in ("trust_ok", "time_ok", "audit_ok"):
            self.assertEqual(r.derive_mode(**{**base, k: False, "draining": True, "overload": True}), r.Mode.HALT)
        self.assertEqual(r.derive_mode(**{**base, "draining": True, "control_plane_ok": False}), r.Mode.DRAIN)
        self.assertEqual(r.derive_mode(**{**base, "control_plane_ok": False, "overload": True}), r.Mode.READ_ONLY_CONTROL)
        self.assertEqual(r.derive_mode(**{**base, "overload": True}), r.Mode.REDUCED)
        for m in r.Mode:
            self.assertIn(m, r.DEGRADED_RULES)
        self.assertFalse(r.DEGRADED_RULES[r.Mode.HALT]["admit"])


class Fencing(unittest.TestCase):
    def test_stale_controller_rejected(self):
        lease = r.FencedLease()
        e1 = lease.acquire("ctl-a")
        e2 = lease.acquire("ctl-b")
        self.assertFalse(lease.check("ctl-a", e1))
        self.assertTrue(lease.check("ctl-b", e2))
        self.assertFalse(lease.check("ctl-b", e1))


if __name__ == "__main__":
    unittest.main()
