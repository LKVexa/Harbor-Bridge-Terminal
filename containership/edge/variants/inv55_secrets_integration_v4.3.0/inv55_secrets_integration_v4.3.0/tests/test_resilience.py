"""Retry/backoff, circuit breaker, admission, deadlines, fault injection (#20, #53, #54, #56, #60, #88)."""
from __future__ import annotations

import random
import unittest

from helpers import SECRET, Clock, Env
from inv55_secrets_integration.errors import ErrorCode, Inv55Error
from inv55_secrets_integration.providers.base import (InMemoryProvider, ProviderDenied, ProviderUnavailable)
from inv55_secrets_integration.resilience import (AdmissionController, CircuitBreaker, CircuitOpen, Deadline,
                                                  RetryPolicy, TokenBucket)
from inv55_secrets_integration.service import ServiceLimits, State


class FaultyProvider(InMemoryProvider):
    """Fault-injection wrapper: scripted failures, latency, and flapping."""

    def __init__(self, clock=None, **kw):
        super().__init__(**kw)
        self.script: list[str] = []
        self.clock = clock
        self.calls = 0

    def read(self, name, version=None):
        self.calls += 1
        if self.script:
            f = self.script.pop(0)
            if f == "unavailable":
                raise ProviderUnavailable("injected")
            if f == "denied":
                raise ProviderDenied("injected")
            if f.startswith("slow:"):
                self.clock.advance(float(f[5:]))
        return super().read(name, version)


class RetryTests(unittest.TestCase):
    def test_backoff_bounded_with_jitter(self):
        rp = RetryPolicy(max_attempts=10, base_s=0.1, cap_s=1.0, rng=random.Random(1))
        for a in range(10):
            d = rp.backoff(a)
            self.assertTrue(0 <= d <= min(1.0, 0.1 * 2 ** a))

    def test_retries_only_retryable(self):
        n = [0]

        def f():
            n[0] += 1
            raise ProviderDenied("x")
        with self.assertRaises(ProviderDenied):
            RetryPolicy(max_attempts=5).run(f)
        self.assertEqual(n[0], 1)

    def test_gives_up_after_max_attempts(self):
        n = [0]

        def f():
            n[0] += 1
            raise ProviderUnavailable("x")
        with self.assertRaises(ProviderUnavailable):
            RetryPolicy(max_attempts=3).run(f)
        self.assertEqual(n[0], 3)

    def test_invalid_attempts(self):
        with self.assertRaises(ValueError):
            RetryPolicy(max_attempts=0)

    def test_deadline_and_cancel(self):
        c = Clock()
        d = Deadline.after(1, c)
        c.advance(2)
        with self.assertRaises(Inv55Error) as cm:
            d.check()
        self.assertIs(cm.exception.code, ErrorCode.DEADLINE_EXCEEDED)
        d2 = Deadline.after(10, c)
        d2.cancelled.set()
        with self.assertRaises(Inv55Error) as cm:
            d2.check()
        self.assertIs(cm.exception.code, ErrorCode.CANCELLED)


class BreakerTests(unittest.TestCase):
    def test_open_halfopen_close(self):
        c = Clock()
        b = CircuitBreaker(c, failure_threshold=2, cooldown_s=5)

        def bad():
            raise ProviderUnavailable("x")
        for _ in range(2):
            with self.assertRaises(ProviderUnavailable):
                b.call(bad)
        self.assertEqual(b.state, "open")
        with self.assertRaises(CircuitOpen):
            b.call(lambda: 1)
        c.advance(5)
        self.assertEqual(b.call(lambda: 1), 1)
        self.assertEqual(b.state, "closed")

    def test_halfopen_failure_reopens(self):
        c = Clock()
        b = CircuitBreaker(c, failure_threshold=1, cooldown_s=1)
        with self.assertRaises(ProviderUnavailable):
            b.call(lambda: (_ for _ in ()).throw(ProviderUnavailable("x")))
        c.advance(1)
        with self.assertRaises(ProviderUnavailable):
            b.call(lambda: (_ for _ in ()).throw(ProviderUnavailable("x")))
        self.assertEqual(b.state, "open")


class AdmissionTests(unittest.TestCase):
    def test_global_shed(self):
        a = AdmissionController(Clock(), max_in_flight=2)
        a.admit()
        a.admit()
        with self.assertRaises(Inv55Error) as cm:
            a.admit()
        self.assertIs(cm.exception.code, ErrorCode.OVERLOADED)
        a.release()
        a.admit()

    def test_fairness_isolated_per_tenant(self):
        c = Clock()
        a = AdmissionController(c, tenant_rate=1, tenant_burst=2, workload_rate=1, workload_burst=2)
        a.charge("noisy", "w")
        a.charge("noisy", "w")
        with self.assertRaises(Inv55Error):
            a.charge("noisy", "w")
        a.charge("quiet", "w")       # unaffected by the noisy neighbour
        c.advance(1)
        a.charge("noisy", "w")       # refilled

    def test_bucket_refill_caps_at_burst(self):
        c = Clock()
        t = TokenBucket(10, 3, c)
        c.advance(100)
        self.assertEqual(sum(t.take() for _ in range(10)), 3)

    def test_tracked_key_bound(self):
        a = AdmissionController(Clock(), max_tracked_keys=4)
        a.charge("t1", "a")
        a.charge("t2", "a")
        with self.assertRaises(Inv55Error):
            a.charge("t3", "a")


class FaultInjection(unittest.TestCase):
    """Dependency outage behaviour through the full service (#46, #60, #88)."""

    def _env(self, **limits):
        c = Clock()
        p = FaultyProvider(clock=c)
        e = Env(provider=p, limits=ServiceLimits(**limits))
        e.clock = c
        e.svc._raw_clock = c
        e.authn.clock = c
        return e, p

    def test_transient_outage_retried(self):
        e, p = self._env()
        e.seed()
        p.script = ["unavailable", "unavailable"]
        self.assertTrue(e.resolve()["ok"])

    def test_hard_outage_fails_closed_without_cache(self):
        e, p = self._env(cache_ttl_s=0)
        e.seed()
        p.available = False
        r = e.resolve()
        self.assertEqual(r["error"]["code"], ErrorCode.PROVIDER_UNAVAILABLE.value.code)
        self.assertEqual(r["error"]["outcome"], "retryable")

    def test_partition_degraded_then_reconnect(self):
        e, p = self._env(cache_ttl_s=10, stale_grace_s=60)
        e.seed()
        self.assertTrue(e.resolve()["ok"])       # warm cache
        p.available = False
        e.clock.advance(20)                      # beyond cache ttl, within grace
        r = e.resolve()
        self.assertEqual(r["outcome"], "degraded")
        self.assertEqual(e.svc.state, State.DEGRADED)
        self.assertEqual(e.use(r["lease_id"])["value"], SECRET)
        e.clock.advance(100)                     # beyond grace -> deny
        self.assertFalse(e.resolve()["ok"])
        p.available = True
        for _ in range(3):                       # circuit cooldown then recovery
            e.clock.advance(6)
            r = e.resolve()
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["outcome"], "success")
        self.assertEqual(e.svc.state, State.READY)

    def test_offline_default_is_deny(self):
        e, p = self._env(cache_ttl_s=10)         # stale_grace_s default 0
        e.seed()
        e.resolve()
        p.available = False
        e.clock.advance(11)
        self.assertFalse(e.resolve()["ok"])

    def test_provider_denied_maps_to_denied_not_retry(self):
        e, p = self._env(cache_ttl_s=0)
        e.seed()
        p.script = ["denied"]
        r = e.resolve()
        self.assertEqual(r["error"]["code"], ErrorCode.DENIED.value.code)
        self.assertEqual(p.calls, 1)

    def test_circuit_opens_and_sheds_provider_load(self):
        e, p = self._env(cache_ttl_s=0)
        e.seed()
        p.available = False
        for _ in range(5):
            e.resolve()
        before = p.calls
        e.resolve()
        self.assertEqual(p.calls, before, "open circuit must not call the provider")

    def test_unexpected_exception_fails_closed(self):
        e, p = self._env(cache_ttl_s=0)
        e.seed()

        def boom(*a, **k):
            raise RuntimeError("password=" + SECRET)
        p.read = boom
        r = e.resolve()
        self.assertEqual(r["error"]["code"], ErrorCode.INTERNAL.value.code)
        self.assertNotIn(SECRET, e.all_diagnostics())


if __name__ == "__main__":
    unittest.main()
