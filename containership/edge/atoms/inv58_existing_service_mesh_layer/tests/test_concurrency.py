"""MC-029: concurrency / race tests with repeated scheduling."""
from __future__ import annotations

import sys
import threading
import unittest

from _support import CTRL_A, CTRL_B, NODE, errors, make_service, mesh, operator, publisher, base_config

ROUNDS = 5


class ConcurrencyTest(unittest.TestCase):
    def setUp(self):
        self._si = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)  # force aggressive preemption

    def tearDown(self):
        sys.setswitchinterval(self._si)

    def _run(self, targets):
        errs = []

        def wrap(fn):
            def inner():
                try:
                    fn()
                except Exception as e:  # pragma: no cover
                    errs.append(repr(e))
            return inner
        ts = [threading.Thread(target=wrap(t)) for t in targets]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
            self.assertFalse(t.is_alive(), "deadlock")
        return errs

    def test_registry_no_lost_update_and_monotonic_revision(self):
        for _ in range(ROUNDS):
            reg = mesh.RoutePolicyRegistry(max_routes=10_000)
            revs = []
            lock = threading.Lock()

            def writer(w):
                def run():
                    for i in range(100):
                        r = reg.migrate_route(f"w{w}-r{i}", 2, 1)
                        with lock:
                            revs.append(r["revision"])
                return run

            def reader():
                last = 0
                for _ in range(300):
                    rev, snap = reg.snapshot()
                    self.assertGreaterEqual(rev, last)
                    self.assertGreaterEqual(rev, len(snap))
                    last = rev
            errs = self._run([writer(w) for w in range(8)] + [reader for _ in range(3)])
            self.assertEqual(errs, [])
            self.assertEqual(sorted(revs), list(range(1, 801)))
            self.assertEqual(len(reg.snapshot()[1]), 800)

    def test_service_concurrent_tenants_and_admission_accounting(self):
        for _ in range(ROUNDS):
            svc, clock, _ = make_service(cfg=base_config(admission={"rate_per_s": 1e6, "burst": 10**6}))

            def tenant_worker(cred, tenant, w):
                def run():
                    for i in range(50):
                        svc.migrate_route(cred, tenant, f"r{w}-{i}", 2, 1, fence=0, idempotency_key=f"{tenant}-{w}-{i:05d}")
                        svc.reconcile(cred, tenant, f"r{w}-{i}", 3, 3)
                        svc.report_flow(NODE, tenant, "x", "payments", bool(i % 2))
                return run
            errs = self._run([tenant_worker(CTRL_A, "alpha", w) for w in range(4)] +
                             [tenant_worker(CTRL_B, "beta", w) for w in range(4)])
            self.assertEqual(errs, [])
            self.assertEqual(svc._admission._inflight, 0)
            self.assertEqual(len(svc._registries["alpha"].snapshot()[1]), 200)
            self.assertEqual(len(svc._registries["beta"].snapshot()[1]), 200)
            self.assertEqual(svc.audit.verify(), (True, "ok"))

    def test_idempotency_key_race_executes_once(self):
        for _ in range(ROUNDS):
            svc, clock, _ = make_service()
            results = []

            def run():
                try:
                    results.append(svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 1, fence=1, idempotency_key="race-00001")["revision"])
                except errors.MeshError as e:
                    results.append(e.code)
            self._run([run] * 8)
            self.assertEqual(svc._registries["alpha"].revision, 1, results)   # executed exactly once
            self.assertTrue(all(r in (1, "E_CONFLICT") for r in results), results)

    def test_config_swap_during_traffic(self):
        svc, clock, _ = make_service()

        def traffic():
            for i in range(200):
                r = svc.reconcile(CTRL_A, "alpha", "a->b", 5, 1)
                self.assertIn(r["effective_attempts"], (2, 3))

        def flipper():
            for i in range(20):
                svc.activate_config(publisher(clock), base_config(version=f"v{i}", default_budget=2 if i % 2 else 3))
        errs = self._run([traffic, traffic, flipper])
        self.assertEqual(errs, [])

    def test_freeze_races_with_mutation(self):
        svc, clock, _ = make_service()
        outcomes = []

        def mut():
            for i in range(100):
                try:
                    svc.migrate_route(CTRL_A, "alpha", f"m{i}", 2, 1, fence=0, idempotency_key=f"frz-{i:06d}")
                    outcomes.append("ok")
                except errors.MeshError as e:
                    outcomes.append(e.code)

        def frz():
            svc.freeze(operator(clock), True, reason="race")
        self._run([mut, frz])
        self.assertTrue(set(outcomes) <= {"ok", "E_FROZEN"})
        n = len(svc._registries["alpha"].snapshot()[1])
        self.assertEqual(n, outcomes.count("ok"))


if __name__ == "__main__":
    unittest.main()
