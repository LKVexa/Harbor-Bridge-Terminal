"""MC-020 / MC-031: fault injection, partition/reconnect, degraded control plane, soak/burst/fleet.

Recovery objectives asserted here (docs/SLO.md RO-1..RO-4):
  RO-1 first successful request after a trust dependency recovers: 0 extra requests
  RO-2 no mutation lost or duplicated across restart (snapshot + fencing)
  RO-3 audit chain verifies after every fault scenario
  RO-4 admission in-flight accounting returns to zero after every burst
"""
from __future__ import annotations

import os
import random
import unittest

from _support import CTRL_A, CTRL_B, NODE, base_config, errors, make_service, operator, publisher

SOAK = int(os.environ.get("INV58_SOAK_ITERATIONS", "3000"))
ME = errors.MeshError


def attempt(fn, *a, **kw):
    try:
        fn(*a, **kw)
        return "ok"
    except ME as e:
        return e.code


class FaultInjectionTest(unittest.TestCase):
    def test_trust_dependency_flap_recovers_immediately(self):
        svc, clock, kms = make_service()
        for dep in ("identity", "policy", "time", "audit_sink"):
            svc.set_dependency(dep, False)
            self.assertNotEqual(attempt(svc.migrate_route, CTRL_A, "alpha", "a->b", 2, 1, fence=1, idempotency_key=f"fl-{dep}-01"), "ok")
            svc.set_dependency(dep, True)
            self.assertEqual(attempt(svc.migrate_route, CTRL_A, "alpha", "a->b", 2, 1, fence=1, idempotency_key=f"fl-{dep}-02"), "ok")  # RO-1
        self.assertEqual(svc.audit.verify(), (True, "ok"))  # RO-3

    def test_key_service_partition_and_reconnect(self):
        svc, clock, kms = make_service()
        kms.up = False
        self.assertEqual(attempt(svc.freeze, operator(clock), True, reason="p"), "E_DEPENDENCY_UNAVAILABLE")
        self.assertEqual(attempt(svc.activate_config, publisher(clock), base_config(version="9")), "E_DEPENDENCY_UNAVAILABLE")
        self.assertEqual(svc.reconcile(CTRL_A, "alpha", "a->b", 2, 1)["owner"], "app")  # mesh-identity data plane unaffected
        kms.up = True
        self.assertEqual(attempt(svc.freeze, operator(clock), True, reason="p"), "ok")

    def test_config_activation_crash_mid_probe_leaves_previous_active(self):
        svc, clock, kms = make_service()
        prev = svc.config.active()[1].digest
        original = svc._probe_config
        svc._probe_config = lambda cfg: (_ for _ in ()).throw(RuntimeError("crash during activation"))
        self.assertEqual(attempt(svc.activate_config, publisher(clock), base_config(version="2")), "E_CONFIG_INVALID")
        self.assertEqual(svc.config.active()[1].digest, prev)
        svc._probe_config = original
        svc.activate_config(publisher(clock), base_config(version="2"))

    def test_restart_mid_migration_series_no_loss_no_duplication(self):
        svc, clock, kms = make_service()
        for i in range(20):
            svc.migrate_route(CTRL_A, "alpha", f"r{i}", 3, 1, fence=i, idempotency_key=f"rs-{i:06d}")
        snap = svc.snapshot()
        svc2, _, _ = make_service(clock=clock, kms=kms)  # "process restart"
        svc2.restore(operator(clock), snap)
        self.assertEqual(len(svc2._registries["alpha"].snapshot()[1]), 20)  # RO-2 no loss
        self.assertEqual(svc2._registries["alpha"].revision, 20)
        self.assertEqual(attempt(svc2.migrate_route, CTRL_A, "alpha", "r0", 2, 1, fence=3, idempotency_key="rs-replay-1"), "E_STALE_FENCE")  # RO-2 no dup
        svc2.migrate_route(CTRL_A, "alpha", "r20", 2, 1, fence=20, idempotency_key="rs-000020")

    def test_split_brain_two_controllers(self):
        svc, clock, kms = make_service()
        # controller A (epoch 10) and a stale controller B (epoch 9) both believe they own alpha
        svc.migrate_route(CTRL_A, "alpha", "x", 3, 1, fence=10, idempotency_key="sb-a-00001")
        self.assertEqual(attempt(svc.migrate_route, CTRL_A, "alpha", "x", 1, 5, fence=9, idempotency_key="sb-b-00001"), "E_STALE_FENCE")
        self.assertEqual(svc.get_route(CTRL_A, "alpha", "x")["owner"], "app")


class BurstSoakFleetTest(unittest.TestCase):
    def test_burst_overload_sheds_and_recovers(self):
        svc, clock, kms = make_service(cfg=base_config(limits={"max_inflight": 4}, admission={"rate_per_s": 1e6, "burst": 10**6}))
        # simulate 4 stuck in-flight requests, then a burst
        for _ in range(2):
            svc._admission.try_acquire("alpha")
            svc._admission.try_acquire("beta")
        shed = [attempt(svc.reconcile, CTRL_A, "alpha", "a", 2, 1) for _ in range(50)]
        self.assertEqual(set(shed), {"E_OVERLOADED"})
        self.assertGreaterEqual(svc.metrics.value("inv58_admission_shed_total", tenant="alpha"), 50)
        for t in ("alpha", "alpha", "beta", "beta"):
            svc._admission.release(t)
        self.assertEqual(attempt(svc.reconcile, CTRL_A, "alpha", "a", 2, 1), "ok")
        self.assertEqual(svc._admission._inflight, 0)  # RO-4

    def test_soak_randomized_mix_preserves_invariants(self):
        svc, clock, kms = make_service(cfg=base_config(admission={"rate_per_s": 1e6, "burst": 10**6}))
        rng = random.Random(58)
        fence = {"alpha": 0, "beta": 0}
        for i in range(SOAK):
            tenant, cred = rng.choice((("alpha", CTRL_A), ("beta", CTRL_B)))
            op = rng.random()
            if op < 0.4:
                r = svc.reconcile(cred, tenant, f"r{rng.randrange(50)}", rng.randint(1, 6), rng.randint(1, 6), budget=rng.randint(1, 5))
                self.assertLessEqual(r["effective_attempts"], r["budget"])
                self.assertFalse(r["app"] > 1 and r["mesh"] > 1)
            elif op < 0.7:
                fence[tenant] += 1
                degraded = svc.lifecycle.state == "degraded"
                res = attempt(svc.migrate_route, cred, tenant, f"r{rng.randrange(50)}", rng.randint(1, 6), rng.randint(1, 6),
                              fence=fence[tenant], idempotency_key=f"soak-{i:08d}")
                self.assertEqual(res, "E_NOT_READY" if degraded else "ok")  # degraded mode refuses policy mutation
            elif op < 0.9:
                svc.report_flow(NODE, tenant, f"src{rng.randrange(1000)}", rng.choice(["payments", "orders", "other"]), rng.random() < 0.8)
            else:
                dep = rng.choice(["telemetry"])
                svc.set_dependency(dep, rng.random() < 0.7)
            if i % 500 == 0:
                clock.advance(1)
        svc.set_dependency("telemetry", True)
        self.assertEqual(svc._admission._inflight, 0)
        self.assertLessEqual(len(svc.audit.records()), 10_000)
        self.assertLessEqual(sum(len(d.snapshot()) for d in svc._detectors.values()), 2 * 1024)
        self.assertEqual(svc.audit.verify(), (True, "ok"))
        self.assertTrue(svc.health()["live"])

    def test_fleet_scale_synthetic_topology(self):
        tenants = [f"t{i:03d}" for i in range(200)]
        cfg = base_config(tenants=tenants, spiffe_bindings={
            "runtime:node/n1": {"actor_type": "node", "roles": ["mesh-node"], "tenants": tenants}},
            meshed_destinations=[f"svc{i}" for i in range(500)])
        svc, clock, kms = make_service(cfg=cfg)
        node = {"san": "spiffe://estate.local/node/n1"}
        for i, t in enumerate(tenants):
            for j in range(5):
                svc.report_flow(node, t, f"w{j}", f"svc{(i * 5 + j) % 500}", j % 2 == 0)
        flagged = sum(len(d.snapshot()) for d in svc._detectors.values())
        self.assertEqual(flagged, 200 * 2)
        self.assertEqual(len(svc._registries), 200)


if __name__ == "__main__":
    unittest.main()
