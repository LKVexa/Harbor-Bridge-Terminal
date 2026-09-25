"""Concurrency/race suite (checklist #85, #58)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from helpers import Env
from inv55_secrets_integration.audit import verify_chain
from inv55_secrets_integration.service import ServiceLimits


class Races(unittest.TestCase):
    def test_parallel_resolve_use_rotate_keeps_invariants(self):
        e = Env(limits=ServiceLimits(max_leases_per_subject=100_000))
        e.svc.admission.max_in_flight = 10_000
        e.svc.admission.workload_burst = e.svc.admission.tenant_burst = 10**9
        e.svc.admission.workload_rate = e.svc.admission.tenant_rate = 10**9
        e.seed()
        cred = e.cred()
        admin = e.cred("admin")
        errors: list = []

        def worker(i: int) -> None:
            try:
                if i % 10 == 0:
                    r = e.svc.rotate({"protocol": "PK_SECRET_ROTATE/1", "credential": admin, "name": "db-password",
                                      "value": f"v-{i}", "idempotency_key": f"idem-race-{i:05d}"})
                    assert r["ok"], r
                    return
                r = e.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": cred, "name": "db-password"})
                assert r["ok"], r
                u = e.svc.use({"protocol": "PK_SECRET_RESOLVE/1", "credential": cred, "name": "db-password",
                               "lease_id": r["lease_id"]})
                assert u["ok"] and u["version"] == r["version"], (r, u)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        with ThreadPoolExecutor(16) as ex:
            list(ex.map(worker, range(800)))
        self.assertEqual(errors, [])
        ok, n, _ = verify_chain(e.sink.lines, b"audit-key")
        self.assertTrue(ok)
        self.assertEqual(n, len(e.sink.lines))
        self.assertEqual(e.svc.admission.in_flight, 0)
        # every rotation produced a distinct version: 1 seed + 80 rotations
        self.assertEqual(e.provider.metadata("acme/db-password")["current_version"], 81)

    def test_concurrent_idempotent_rotate_single_version(self):
        """Duplicate delivery of the same rotation from many threads writes at most... one version each key."""
        e = Env()
        e.seed()
        admin = e.cred("admin")
        barrier = threading.Barrier(8)
        results = []

        def go():
            barrier.wait()
            results.append(e.svc.rotate({"protocol": "PK_SECRET_ROTATE/1", "credential": admin,
                                         "name": "db-password", "value": "same", "idempotency_key": "idem-dup-0001",
                                         "expected_version": 1}))
        ts = [threading.Thread(target=go) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        ok = [r for r in results if r["ok"]]
        self.assertGreaterEqual(len(ok), 1)
        self.assertEqual({r["version"] for r in ok}, {2})
        self.assertEqual(e.provider.metadata("acme/db-password")["current_version"], 2,
                         "CAS on the provider prevents duplicate/split-brain writes")

    def test_duplicate_rotation_without_cas_writes_once(self):
        """Idempotency reservation: N concurrent duplicates (no expected_version) -> one provider write."""
        e = Env()
        e.svc.admission.workload_burst = e.svc.admission.tenant_burst = 10**9
        e.seed()
        admin = e.cred("admin")
        barrier = threading.Barrier(12)
        results = []

        def go():
            barrier.wait()
            results.append(e.svc.rotate({"protocol": "PK_SECRET_ROTATE/1", "credential": admin,
                                         "name": "db-password", "value": "once", "idempotency_key": "idem-once-001"}))
        ts = [threading.Thread(target=go) for _ in range(12)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertTrue(all(r["ok"] for r in results), results)
        self.assertEqual({r["version"] for r in results}, {2})
        self.assertEqual(sum(not r["replayed"] for r in results), 1)
        self.assertEqual(e.provider.metadata("acme/db-password")["current_version"], 2)

    def test_same_idempotency_key_different_payload_conflicts(self):
        e = Env()
        e.seed()
        admin = e.cred("admin")
        req = {"protocol": "PK_SECRET_ROTATE/1", "credential": admin, "name": "db-password",
               "idempotency_key": "idem-diff-001"}
        self.assertTrue(e.svc.rotate({**req, "value": "a"})["ok"])
        r = e.svc.rotate({**req, "value": "b"})
        self.assertEqual(r["error"]["code"], "INV55-E019-CONFLICT")

    def test_revoke_races_use(self):
        e = Env()
        e.svc.admission.workload_burst = e.svc.admission.tenant_burst = 10**9
        e.seed()
        for _ in range(50):
            r = e.resolve()
            out = []
            t1 = threading.Thread(target=lambda: out.append(e.use(r["lease_id"])))
            t2 = threading.Thread(target=lambda: e.svc.revoke({"protocol": "PK_SECRET_RESOLVE/1",
                                                               "credential": e.cred("admin"), "name": "db-password",
                                                               "lease_id": r["lease_id"]}))
            t1.start(); t2.start(); t1.join(); t2.join()
            self.assertFalse(e.use(r["lease_id"])["ok"], "after revoke completes, use must fail")


if __name__ == "__main__":
    unittest.main()
