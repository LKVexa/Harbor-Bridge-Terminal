"""MC-07, MC-10..MC-15, MC-26: governed placement path behaviour."""
from __future__ import annotations

import unittest

from _fx import Rig, m, sch
from sch01_workload_classification_and_runtime_placem.errors import SchedulerError


class DeploymentContextTest(unittest.TestCase):
    """MC-07 deployment-context semantics: freshness per context, disconnected sites, environment scoping."""

    def test_far_edge_tolerates_older_report_than_datacenter(self):
        r = Rig(); r.clock.t = 1000
        r.node("dc", context="datacenter", reported_at=1000 - 45)
        r.node("edge", context="far-edge", reported_at=1000 - 45)
        self.assertEqual(r.place()["node"], "edge")

    def test_disconnected_node_refused_unless_context_allows(self):
        r = Rig()
        r.node("dc", context="datacenter", connected=False)
        with self.assertRaises(SchedulerError) as e: r.place()
        self.assertIn("NODE_DISCONNECTED", e.exception.details["rejection_counts"])
        r.node("fe", context="far-edge", connected=False)
        self.assertEqual(r.place(name="w2")["node"], "fe")

    def test_environment_boundary(self):
        r = Rig(); r.node("staging1", environment="staging")
        with self.assertRaises(SchedulerError) as e: r.place()
        self.assertIn("ENVIRONMENT_MISMATCH", e.exception.details["rejection_counts"])

    def test_unknown_context_rejected(self):
        r = Rig()
        with self.assertRaises(ValueError): r.node("x", context="moon")


class QuotaFairShareTest(unittest.TestCase):
    """MC-10 quota and fair-share accounting with starvation guard."""

    def test_hard_quota(self):
        r = Rig(tenant_quota={"t1": 1}); r.node("n1")
        r.place(name="a")
        with self.assertRaises(SchedulerError) as e: r.place(name="b")
        self.assertEqual(e.exception.code, "QUOTA_EXCEEDED"); self.assertTrue(e.exception.spec.retryable)

    def test_release_returns_quota(self):
        r = Rig(tenant_quota={"t1": 1}); r.node("n1")
        a = r.place(name="a")
        r.s.transition(r.tok(), a["lease_id"], "RELEASED")
        self.assertEqual(r.place(name="b")["node"], "n1")

    def test_fair_share_cap_when_other_tenant_waits(self):
        r = Rig(tenant_quota={"t2": 0}, fair_share_max_fraction=0.5); r.node("n1", slots=4)
        with self.assertRaises(SchedulerError): r.place(name="x", tenant="t2")   # t2 now waiting
        r.place(name="a"); r.place(name="b")
        with self.assertRaises(SchedulerError) as e: r.place(name="c")
        self.assertIn("fair-share", str(e.exception))


class RuntimeSelectorTest(unittest.TestCase):
    """MC-11 concrete runtime/execution-target selection."""

    def test_runtime_named_in_placement(self):
        r = Rig(); r.node("n1", runtimes={"process": "runc", "wasm": "wasmtime"})
        self.assertEqual(r.place()["runtime"], "runc")

    def test_required_runtime_filters(self):
        r = Rig(); r.node("n1", runtimes={"process": "runc", "wasm": "wasmtime"})
        self.assertEqual(r.place(runtime="wasmtime")["tier"], "wasm")

    def test_tier_without_runtime_is_not_schedulable(self):
        r = Rig(); r.node("n1", tiers=("process",), runtimes={})
        with self.assertRaises(SchedulerError) as e: r.place()
        self.assertIn("NO_RUNTIME", e.exception.details["rejection_counts"])


class LatencyAwareTest(unittest.TestCase):
    """MC-12 latency class is consumed: interactive and batch place differently."""

    def setUp(self):
        self.r = Rig()
        self.r.node("near", slots=1, latency_ms={"lon": 3})
        self.r.node("far", slots=9, latency_ms={"lon": 80})

    def test_interactive_prefers_low_rtt_and_enforces_budget(self):
        out = self.r.place(latency_sensitive=True, origin_site="lon")
        self.assertEqual(out["node"], "near"); self.assertEqual(out["latency_class"], "interactive")
        with self.assertRaises(SchedulerError) as e:
            self.r.place(name="w2", latency_sensitive=True, origin_site="lon")
        self.assertIn("LATENCY_BUDGET", e.exception.details["rejection_counts"])

    def test_batch_ignores_latency_and_takes_most_free(self):
        self.assertEqual(self.r.place(origin_site="lon")["node"], "far")


class TopologyTest(unittest.TestCase):
    """MC-13 topology: zone anti-affinity is hard, preferred zone is soft (DEGRADED_SUCCESS)."""

    def test_anti_affinity_hard(self):
        r = Rig(); r.node("a", zone="z1"); r.node("b", zone="z2")
        self.assertEqual(r.place(anti_affinity_zone="z1")["node"], "b")

    def test_preferred_zone_soft(self):
        r = Rig(); r.node("a", zone="z1", slots=9); r.node("b", zone="z2", slots=1)
        self.assertEqual(r.place(preferred_zone="z2")["node"], "b")
        out = r.place(name="w2", preferred_zone="z2")
        self.assertEqual(out["result_class"], "DEGRADED_SUCCESS"); self.assertEqual(out["node"], "a")


class ResidencyDataPathTest(unittest.TestCase):
    """MC-14 residency jurisdiction and data-path affinity are hard constraints."""

    def test_residency(self):
        r = Rig(); r.node("us1", jurisdiction="US"); r.node("de1", jurisdiction="DE")
        self.assertEqual(r.place(residency={"DE", "FR"})["jurisdiction"], "DE")

    def test_residency_unsatisfiable_refuses(self):
        r = Rig(); r.node("us1", jurisdiction="US")
        with self.assertRaises(SchedulerError) as e: r.place(residency={"DE"})
        self.assertIn("RESIDENCY", e.exception.details["rejection_counts"])

    def test_dataset_locality(self):
        r = Rig(); r.node("a"); r.node("b", data_paths={"ds-7"})
        self.assertEqual(r.place(dataset="ds-7")["node"], "b")


class AcceleratorTest(unittest.TestCase):
    """MC-15 accelerator identity, quantity, exclusivity, health, NUMA locality, lease release."""

    def devs(self):
        return (m.Accelerator("g0", "gpu.a100", numa=0), m.Accelerator("g1", "gpu.a100", numa=1),
                m.Accelerator("g2", "gpu.a100", numa=1), m.Accelerator("g3", "gpu.a100", numa=0, healthy=False))

    def test_numa_local_pair_and_exclusive(self):
        r = Rig(); r.node("n1", accelerators=self.devs())
        a = r.place(accelerators={"gpu.a100": 2})
        self.assertEqual(a["devices"], ["g1", "g2"])
        b = r.place(name="w2", accelerators={"gpu.a100": 1})
        self.assertEqual(b["devices"], ["g0"])          # g3 unhealthy never allocated
        with self.assertRaises(SchedulerError): r.place(name="w3", accelerators={"gpu.a100": 1})
        r.s.transition(r.tok(), a["lease_id"], "RELEASED")
        self.assertEqual(len(r.place(name="w4", accelerators={"gpu.a100": 2})["devices"]), 2)


class OccupancyIsolationTest(unittest.TestCase):
    """MC-26 cross-tenant co-location allowed only with proven hardware isolation."""

    def test_cross_tenant_refused_on_process_tier(self):
        r = Rig(); r.node("n1", tiers=("process",))
        r.place(name="a", tenant="t1")
        with self.assertRaises(SchedulerError) as e: r.place(name="b", tenant="t2")
        self.assertIn("TENANT_ISOLATION", e.exception.details["rejection_counts"])

    def test_cross_tenant_allowed_when_both_microvm_attested(self):
        r = Rig(); r.node("n1", tiers=("microvm",))
        a = r.place(name="a", tenant="t1", prov="public")
        b = r.place(name="b", tenant="t2", prov="public")
        self.assertEqual((a["node"], b["node"]), ("n1", "n1"))
        occ = [l["occupant"] for l in r.s.leases.values()]
        self.assertNotEqual(occ[0].tier_instance, occ[1].tier_instance)

    def test_legacy_occupants_still_fail_closed(self):
        r = Rig(); spec = r.node("n1", report=False); spec.report.occupants["old"] = "t9"
        r.s.report_node(r.tok("n1", "node", (), ("node-agent",)), spec)
        with self.assertRaises(SchedulerError): r.place()


if __name__ == "__main__":
    unittest.main()
