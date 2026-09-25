"""MC-018 / MC-019 / MC-003: retry timing safety, breaker, admission, lifecycle FSM, fencing."""
from __future__ import annotations

import random
import unittest

from _support import Clock, errors, resilience as R

ME = errors.MeshError


class RetrySafetyTest(unittest.TestCase):
    def test_classification(self):
        self.assertTrue(R.retry_safe("GET"))
        self.assertFalse(R.retry_safe("POST"))
        self.assertTrue(R.retry_safe("POST", idempotency_key="k"))
        self.assertFalse(R.retry_safe("GET", outcome="response_received_5xx_after_write"))

    def test_backoff_is_bounded_and_jittered(self):
        p = R.BackoffPolicy(base_delay_ms=100, max_delay_ms=400, max_elapsed_ms=700)
        for seed in range(200):
            d = p.delays(10, random.Random(seed))
            self.assertLessEqual(sum(d), 0.7 + 1e-9)
            self.assertTrue(all(0 <= x <= 0.4 for x in d))
            self.assertLessEqual(len(d), 9)
        self.assertEqual(p.delays(1), [])
        self.assertNotEqual(p.delays(5, random.Random(1)), p.delays(5, random.Random(2)))

    def _flaky(self, fails):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] <= fails:
                raise ConnectionError("x")
            return "ok"
        return fn, calls

    def test_attempts_are_never_exceeded(self):
        fn, calls = self._flaky(10)
        with self.assertRaises(ME) as cm:
            R.execute_with_retry(fn, attempts=3, method="GET", backoff=R.BackoffPolicy(1, 1, 100), deadline_s=5)
        self.assertEqual(calls["n"], 3)
        self.assertEqual(cm.exception.code, "E_DEPENDENCY_UNAVAILABLE")

    def test_success_after_retry(self):
        fn, calls = self._flaky(2)
        self.assertEqual(R.execute_with_retry(fn, attempts=3, method="GET", backoff=R.BackoffPolicy(1, 1, 100)), "ok")

    def test_non_idempotent_gets_one_attempt(self):
        fn, calls = self._flaky(1)
        with self.assertRaises(ME):
            R.execute_with_retry(fn, attempts=5, method="POST", backoff=R.BackoffPolicy(1, 1, 100))
        self.assertEqual(calls["n"], 1)

    def test_deadline_and_cancellation(self):
        clock = Clock(0.0)
        def fn():
            clock.advance(0.6)
            raise ConnectionError()
        with self.assertRaises(ME) as cm:
            R.execute_with_retry(fn, attempts=5, method="GET", deadline_s=1.0, clock=clock,
                                 backoff=R.BackoffPolicy(1, 1, 100))
        self.assertEqual(cm.exception.code, "E_DEADLINE_EXCEEDED")
        tok = R.CancelToken()
        tok.cancel()
        with self.assertRaises(ME) as cm:
            R.execute_with_retry(lambda: 1, attempts=2, method="GET", cancel=tok)
        self.assertEqual(cm.exception.code, "E_CANCELLED")

    def test_invalid_attempts(self):
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ME):
                R.execute_with_retry(lambda: 1, attempts=bad, method="GET")


class BreakerTest(unittest.TestCase):
    def test_transitions(self):
        c = Clock(0.0)
        b = R.CircuitBreaker(failure_threshold=2, reset_timeout_s=10, clock=c)
        b.record(False)
        self.assertEqual(b.state, "closed")
        b.record(False)
        self.assertEqual(b.state, "open")
        self.assertFalse(b.allow())
        c.advance(10)
        self.assertEqual(b.state, "half_open")
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())  # half-open probe limit
        b.record(False)
        self.assertEqual(b.state, "open")
        c.advance(10)
        b.allow()
        b.record(True)
        self.assertEqual(b.state, "closed")

    def test_breaker_stops_retry_storm(self):
        c = Clock(0.0)
        b = R.CircuitBreaker(failure_threshold=2, reset_timeout_s=60, clock=c)
        calls = {"n": 0}
        def fn():
            calls["n"] += 1
            raise ConnectionError()
        for _ in range(5):
            with self.assertRaises(ME):
                R.execute_with_retry(fn, attempts=3, method="GET", breaker=b, backoff=R.BackoffPolicy(1, 1, 50))
        self.assertEqual(calls["n"], 2)


class AdmissionTest(unittest.TestCase):
    def test_inflight_ceiling_and_fair_share(self):
        c = Clock(0.0)
        a = R.AdmissionController(rate_per_s=1e6, burst=1000, max_inflight=10, tenant_share=0.5, clock=c)
        got = sum(a.try_acquire("noisy") for _ in range(20))
        self.assertEqual(got, 5)  # one tenant cannot take more than its share
        self.assertEqual(sum(a.try_acquire("quiet") for _ in range(5)), 5)
        self.assertFalse(a.try_acquire("third"))  # global ceiling
        a.release("noisy")
        self.assertTrue(a.try_acquire("third"))
        self.assertEqual(a.saturation(), 1.0)
        with self.assertRaises(RuntimeError):
            a.release("never")

    def test_rate_limit_refills(self):
        c = Clock(0.0)
        a = R.AdmissionController(rate_per_s=10, burst=2, max_inflight=100, tenant_share=1.0, clock=c)
        results = []
        for _ in range(3):
            ok = a.try_acquire("t")
            results.append(ok)
            if ok:
                a.release("t")
        self.assertEqual(results, [True, True, False])
        c.advance(0.1)
        self.assertTrue(a.try_acquire("t"))


class LifecycleTest(unittest.TestCase):
    def test_legal_and_illegal(self):
        seen = []
        lc = R.Lifecycle(lambda o, n, r: seen.append((o, n)))
        for s in ("bootstrapping", "ready", "degraded", "ready", "frozen", "ready", "draining", "stopped"):
            lc.to(s, "t")
        self.assertEqual(len(seen), 8)
        with self.assertRaises(ME):
            lc.to("ready", "resurrect")

    def test_every_state_is_reachable_and_declared(self):
        self.assertEqual(set(R.LEGAL_TRANSITIONS), set(R.LIFECYCLE_STATES))
        self.assertEqual(set(R.STATE_ACCEPTS), set(R.LIFECYCLE_STATES))
        reach, frontier = {"created"}, ["created"]
        while frontier:
            for n in R.LEGAL_TRANSITIONS[frontier.pop()]:
                if n not in reach:
                    reach.add(n)
                    frontier.append(n)
        self.assertEqual(reach, set(R.LIFECYCLE_STATES))


class FencingTest(unittest.TestCase):
    def test_monotonic(self):
        f = R.FencingGuard()
        f.check_and_advance("s", 3)
        f.check_and_advance("s", 3)
        with self.assertRaises(ME):
            f.check_and_advance("s", 2)
        f.restore({"s": 1})
        with self.assertRaises(ME):
            f.check_and_advance("s", 2)


if __name__ == "__main__":
    unittest.main()
