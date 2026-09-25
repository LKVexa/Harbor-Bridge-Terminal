"""Retry/backoff/jitter, circuit breaker, admission, freeze/quarantine (items 31, 32, 35)."""
import random
import unittest

import _support as S

R, PE = S.resilience, S.lifecycle.PlaneError


class Resilience(unittest.TestCase):
    def test_backoff_bounded_and_jittered(self):
        b = R.Backoff(0.1, 2.0, 6, random.Random(1))
        ds = [b.delay(a) for a in range(1, 7)]
        self.assertTrue(all(0 <= d <= 2.0 for d in ds))
        self.assertGreater(len(set(ds)), 1)
        with self.assertRaises(PE):
            b.delay(7)
        with self.assertRaises(ValueError):
            b.delay(0)

    def test_retry_budget_caps_storms(self):
        rb = R.RetryBudget(ratio=0.1, min_tokens=2)
        self.assertTrue(rb.try_retry())
        self.assertTrue(rb.try_retry())
        self.assertFalse(rb.try_retry())
        for _ in range(10):
            rb.on_request()
        self.assertTrue(rb.try_retry())

    def test_circuit_breaker_open_halfopen_close(self):
        c = S.Clock()
        cb = R.CircuitBreaker(2, 10, c)
        boom = lambda: (_ for _ in ()).throw(RuntimeError("x"))  # noqa: E731
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                cb.call(boom)
        with self.assertRaises(PE) as ctx:
            cb.call(lambda: 1)
        self.assertEqual(ctx.exception.code, "INV67_CIRCUIT_OPEN")
        c.tick(11)
        self.assertEqual(cb.call(lambda: 5), 5)
        self.assertEqual(cb.state, cb.CLOSED)

    def test_halfopen_failure_reopens(self):
        c = S.Clock()
        cb = R.CircuitBreaker(1, 5, c)
        with self.assertRaises(RuntimeError):
            cb.call(lambda: 1 / 0 if False else (_ for _ in ()).throw(RuntimeError()))
        c.tick(6)
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError()))
        self.assertEqual(cb.state, cb.OPEN)

    def test_admission_fairness_and_shedding(self):
        c = S.Clock()
        a = R.Admission(3, {"big": 2}, 1, 100, 100, c)
        a.acquire("big"); a.acquire("big")
        with self.assertRaises(PE) as e:
            a.acquire("big")
        self.assertEqual(e.exception.code, "INV67_QUOTA_EXCEEDED")
        a.acquire("small")
        with self.assertRaises(PE) as e:
            a.acquire("other")
        self.assertEqual(e.exception.code, "INV67_OVERLOADED")
        a.release("big")
        a.acquire("other")
        self.assertEqual(a.shed, 2)
        with self.assertRaises(RuntimeError):
            a.release("nobody")

    def test_unknown_tenant_gets_default_not_unlimited(self):
        a = R.Admission(100, {}, 1, 100, 100, S.Clock())
        a.acquire("x")
        with self.assertRaises(PE):
            a.acquire("x")

    def test_rate_limit(self):
        c = S.Clock()
        a = R.Admission(100, {}, 100, 1.0, 2.0, c)
        a.acquire("t"); a.acquire("t")
        with self.assertRaises(PE):
            a.acquire("t")
        c.tick(1.0)
        a.acquire("t")

    def test_switchboard(self):
        sw = R.Switchboard()
        sw.check_launch("ns/a", "ns")
        with self.assertRaises(ValueError):
            sw.freeze("")
        sw.freeze("incident 42")
        with self.assertRaises(PE) as e:
            sw.check_launch("ns/a", "ns")
        self.assertTrue(e.exception.retryable)
        sw.unfreeze()
        sw.quarantine("ns:ns", "compromised")
        with self.assertRaises(PE) as e:
            sw.check_launch("ns/a", "ns")
        self.assertFalse(e.exception.retryable)
        sw.release("ns:ns")
        sw.check_launch("ns/a", "ns")


if __name__ == "__main__":
    unittest.main()
