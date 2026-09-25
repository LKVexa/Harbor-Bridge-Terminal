"""Retry/backoff/jitter, deadlines, admission, circuit breaker, idempotency
(MC-015, MC-043, MC-044)."""
from __future__ import annotations

import random
import unittest

from support import FakeClock, TENANT, seeded

from inv62_edge_topology.production import errors
from inv62_edge_topology.production.resilience import (Admission, CircuitBreaker, Deadline, IdempotencyStore,
                                                        RetryPolicy, TokenBucket, retry_call)


class RetryTest(unittest.TestCase):
    def test_delays_bounded_jittered_and_budgeted(self):
        p = RetryPolicy(max_attempts=6, base_ms=10, cap_ms=40, budget_ms=100)
        for seed in range(200):
            d = p.delays(random.Random(seed))
            self.assertLessEqual(len(d), 5)
            self.assertLessEqual(sum(d), 100)
            self.assertTrue(all(0 <= x <= 40 for x in d))
        self.assertNotEqual(p.delays(random.Random(1)), p.delays(random.Random(2)))
        with self.assertRaises(ValueError):
            RetryPolicy(max_attempts=0)
        with self.assertRaises(ValueError):
            RetryPolicy(base_ms=50, cap_ms=10)

    def test_only_retryable_outcomes_retried(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise errors.TopoError(errors.OVERLOADED, "busy")
            return "ok"
        self.assertEqual(retry_call(flaky, RetryPolicy(), rng=random.Random(0), sleep=lambda s: None), "ok")
        calls.clear()

        def terminal():
            calls.append(1)
            raise errors.TopoError(errors.FORBIDDEN, "no")
        with self.assertRaises(errors.TopoError):
            retry_call(terminal, RetryPolicy(), sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_retry_gives_up_after_attempts(self):
        n = []

        def always():
            n.append(1)
            raise errors.TopoError(errors.OVERLOADED, "busy")
        with self.assertRaises(errors.TopoError):
            retry_call(always, RetryPolicy(max_attempts=3, base_ms=1, cap_ms=1, budget_ms=10), sleep=lambda s: None)
        self.assertLessEqual(len(n), 3)


class DeadlineTest(unittest.TestCase):
    def test_expiry_and_cancel(self):
        clk = FakeClock(0)
        d = Deadline(100, clk)
        d.check()
        clk.advance(0.2)
        with self.assertRaises(errors.TopoError) as cm:
            d.check()
        self.assertEqual(cm.exception.code, "TOPO.DEADLINE_EXCEEDED")
        d2 = Deadline(100, clk)
        d2.cancel()
        with self.assertRaises(errors.TopoError) as cm:
            d2.check()
        self.assertEqual(cm.exception.code, "TOPO.CANCELLED")

    def test_apply_aborts_before_commit_when_deadline_passes(self):
        svc, feed = seeded()
        rev = svc.tenants[TENANT].topo.revision
        orig = svc._apply_mutations

        def slow(ts, topo, muts):
            orig(ts, topo, muts)
            svc.clock.advance(10)  # the service mono clock is the fake clock
        svc._apply_mutations = slow
        feed.retry = RetryPolicy(max_attempts=1)
        with self.assertRaises(errors.TopoError) as cm:
            feed.call("PK_TOPO_GRAPH/1", "apply", {"mutations": [{"kind": "remove_node", "node": "s1-d2"}]},
                      idempotent=True, deadline_ms=50)
        self.assertEqual(cm.exception.code, "TOPO.DEADLINE_EXCEEDED")
        self.assertEqual(svc.tenants[TENANT].topo.revision, rev)
        self.assertIn("s1-d2", svc.tenants[TENANT].topo.nodes)


class AdmissionTest(unittest.TestCase):
    def test_bucket_refills_and_never_negative_on_clock_step(self):
        clk = FakeClock(100)
        b = TokenBucket(10, 2, clk)
        self.assertTrue(b.try_take() and b.try_take())
        self.assertFalse(b.try_take())
        clk.advance(-50)
        clk.advance(50.2)
        self.assertTrue(b.try_take())

    def test_in_flight_and_tenant_table_bounds(self):
        a = Admission(rate_per_s=1000, burst=1000, max_in_flight=2, max_tenants=2, clock=FakeClock())
        a.enter("t1")
        a.enter("t1")
        with self.assertRaises(errors.TopoError) as cm:
            a.enter("t2")
        self.assertEqual(cm.exception.code, "TOPO.OVERLOADED")
        a.leave()
        a.enter("t2")
        with self.assertRaises(errors.TopoError):
            a.enter("t3")
        self.assertEqual(a.shed, 2)


class BreakerTest(unittest.TestCase):
    def test_open_half_open_close(self):
        clk = FakeClock(0)
        cb = CircuitBreaker(threshold=2, cooldown_s=5, clock=clk)
        cb.before(); cb.failure()
        cb.before(); cb.failure()
        self.assertEqual(cb.state, "open")
        with self.assertRaises(errors.TopoError):
            cb.before()
        clk.advance(5)
        cb.before()
        self.assertEqual(cb.state, "half_open")
        with self.assertRaises(errors.TopoError):
            cb.before()  # only one probe
        cb.failure()
        self.assertEqual(cb.state, "open")
        clk.advance(5)
        cb.before(); cb.success()
        self.assertEqual(cb.state, "closed")


class IdempotencyTest(unittest.TestCase):
    def test_same_key_same_payload_returns_cached(self):
        clk = FakeClock(0)
        s = IdempotencyStore(ttl_s=10, capacity=2, clock=clk)
        fp = s.fingerprint({"a": 1})
        s.store("t", "key-00000001", fp, {"r": 1})
        self.assertEqual(s.lookup("t", "key-00000001", fp), {"r": 1})
        self.assertIsNone(s.lookup("other", "key-00000001", fp))
        with self.assertRaises(errors.TopoError):
            s.lookup("t", "key-00000001", s.fingerprint({"a": 2}))
        clk.advance(11)
        self.assertIsNone(s.lookup("t", "key-00000001", fp))

    def test_service_retry_with_same_key_applies_once(self):
        svc, feed = seeded()
        body = {"mutations": [{"kind": "add_node", "node": "s1-dx", "tier": "device", "site": "s1", "parent": "s1-gw"}]}
        import json
        from inv62_edge_topology.production import wire
        mk = lambda: {"protocol": "PK_TOPO_GRAPH/1", "op": "apply", "tenant": TENANT, "request_id": "req-idem0001",  # noqa: E731
                      "idempotency_key": "idem-00000001", "credential": svc.authn.issue("f", "topology-feed", [TENANT]),
                      "body": body}
        r1 = json.loads(svc.handle(wire.encode(mk())))
        r2 = json.loads(svc.handle(wire.encode(mk())))
        self.assertEqual(r1, r2)
        self.assertNotIn("error", r1)
        self.assertEqual(svc.metrics.get("inv62_idempotent_replays", family="PK_TOPO_GRAPH"), 1)


if __name__ == "__main__":
    unittest.main()
