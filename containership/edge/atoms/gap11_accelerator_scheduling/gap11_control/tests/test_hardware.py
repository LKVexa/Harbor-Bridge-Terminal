"""P0-06 inventory, P0-07 partition topology, P0-08 scrub executor, P1-19 thermal,
P1-20 health/RAS — 'hardware template' checks .01-.10 (simulated providers only)."""
from __future__ import annotations

import unittest

from support import Stack, covers
from gap11_control.common import ControlError, ManualClock
from gap11_control.hardware import (HealthMonitor, InventoryAdapter, PartitionProfile, PartitionTopology,
                                    PermanentProviderError, ScrubExecutor, SimScrubBackend, ThermalAdmission,
                                    TransientProviderError, normalize, with_retry)

NV = {"uuid": "GPU-1111-2222-3333-4444-5555aaaabbbb", "memory_total_bytes": 80 * 1024 ** 3, "arch": "hopper",
      "caps": ["fp8", "nvlink"], "pci_bus_id": "0000:17:00.0", "numa_node": 0, "nvlink_domain": "nvl-a",
      "driver": "550.54", "vbios": "96.00.61", "mig": [{"profile": "3g.40gb", "memory_mib": 40960}, {"profile": "3g.40gb-b", "memory_mib": 40960}]}
AMD = {"serial": "SN00112233AABB", "vram_mib": 196608, "gfx": "GFX942", "bdf": "0000:c1:00.0", "driver_version": "6.7", "fw": "2.1"}


class Provider:
    def __init__(self, vendor, items, *, transient=0, permanent=False, clock=None):
        self.vendor, self.items, self.transient, self.permanent = vendor, items, transient, permanent

    def list_devices(self):
        if self.permanent:
            raise TransientProviderError("down")
        if self.transient:
            self.transient -= 1
            raise TransientProviderError("busy")
        return [dict(i) for i in self.items]


class InventoryTests(unittest.TestCase):
    @covers("GAP11-P0-06.01", "GAP11-P0-06.02")
    def test_vendor_payloads_normalise_to_one_canonical_model(self):
        nv = normalize("simnv", NV, "node-1")
        amd = normalize("simamd", AMD, "node-1")
        self.assertEqual(set(nv) , set(amd))
        self.assertEqual((nv["memory_gb"], amd["memory_gb"]), (80, 192))            # bytes vs MiB normalised
        self.assertEqual(amd["generation"], "cdna3")                                 # vendor enum mapped
        self.assertEqual([p["memory_gb"] for p in nv["partitions"]], [40, 40])
        self.assertEqual(normalize("simnv", {**NV, "xid_errors": [79]}, "n")["health"], "failed")
        with self.assertRaises(ControlError):
            normalize("unknownvendor", {}, "n")
        with self.assertRaises(ControlError):
            normalize("simnpu", {"id": "n0", "gen": "v1", "mem_gb": 0, "drv": "1", "fw": "1"}, "n")   # malformed

    @covers("GAP11-P0-06.03", "GAP11-P0-06.05", "GAP11-P1-21.10")
    def test_stable_identity_survives_pci_renumbering_and_replacement_is_distinguished(self):
        clock = ManualClock()
        p = Provider("simnv", [NV])
        inv = InventoryAdapter([p], node="node-1", clock=clock)
        first = inv.collect()
        self.assertEqual(first["evidence"]["added"], [NV["uuid"]])
        p.items = [{**NV, "pci_bus_id": "0000:18:00.0"}]                            # renumbered after reboot
        second = inv.collect()
        self.assertEqual(second["evidence"]["renumbered_only"], [NV["uuid"]])
        self.assertEqual(second["evidence"]["added"], [])
        p.items = [{**NV, "uuid": "GPU-9999-new-board-at-same-slot"}]                # replacement, same slot
        third = inv.collect()
        self.assertEqual(third["evidence"]["removed"], [NV["uuid"]])
        self.assertEqual(third["evidence"]["added"], ["GPU-9999-new-board-at-same-slot"])

    @covers("GAP11-P0-06.06", "GAP11-P0-06.10")
    def test_bounded_retry_and_failed_provider_is_unknown_not_removed(self):
        clock = ManualClock()
        good = Provider("simnv", [NV], transient=2)
        inv = InventoryAdapter([good, Provider("simamd", [AMD])], node="n", clock=clock)
        self.assertEqual(len(inv.collect()["devices"]), 2)                            # 2 transient failures retried
        dead = Provider("simamd", [AMD], permanent=True)
        inv.providers = [Provider("simnv", [NV]), dead]
        rep = inv.collect()
        self.assertEqual(rep["evidence"]["removed"], [])                              # outage != removal
        self.assertEqual(rep["evidence"]["provider_errors"], [{"vendor": "simamd", "code": "DEADLINE_EXCEEDED"}])
        calls = {"n": 0}
        def always():
            calls["n"] += 1
            raise TransientProviderError("x")
        t0 = clock.monotonic()
        with self.assertRaises(ControlError):
            with_retry(always, deadline=t0 + 0.3, clock=clock, attempts=10, base_delay=0.05)
        self.assertLessEqual(clock.monotonic(), t0 + 0.3)                             # never overruns deadline
        with self.assertRaises(PermanentProviderError):                               # non-retryable class
            with_retry(lambda: (_ for _ in ()).throw(PermanentProviderError("no")), deadline=t0 + 9, clock=clock)

    @covers("GAP11-P0-06.09")
    def test_inventory_evidence_is_structured(self):
        inv = InventoryAdapter([Provider("simnv", [NV])], node="node-7", clock=ManualClock())
        ev = inv.collect()["evidence"]
        for k in ("schema", "node", "ts", "devices", "added", "removed", "changed", "provider_errors"):
            self.assertIn(k, ev)


class PartitionTopologyTests(unittest.TestCase):
    def topo(self):
        return PartitionTopology(80, [PartitionProfile("2x40", (("a", 40), ("b", 40))),
                                      PartitionProfile("4x20", (("a", 20), ("b", 20), ("c", 20), ("d", 20))),
                                      PartitionProfile("7x10", tuple((f"s{i}", 10) for i in range(7)))])

    @covers("GAP11-P0-07.01", "GAP11-P0-07.02", "GAP11-P0-07.05")
    def test_alternative_layouts_are_mutually_exclusive_and_reconfigure_only_when_drained(self):
        t = self.topo()
        self.assertFalse(t.compatible("2x40", "4x20"))
        with self.assertRaises(ControlError):
            t.reconfigure("4x20", active_leases=1, drained=True)
        with self.assertRaises(ControlError):
            t.reconfigure("4x20", active_leases=0, drained=False)
        parts = t.reconfigure("4x20", active_leases=0, drained=True)
        self.assertEqual([p["memory_gb"] for p in parts], [20, 20, 20, 20])
        with self.assertRaises(ControlError):
            PartitionTopology(40, [PartitionProfile("bad", (("a", 30), ("b", 30)))])

    @covers("GAP11-P0-07.10", "GAP11-P1-18.07", "GAP11-P0-14.07")
    def test_profile_choice_minimises_residual_capacity(self):
        t = self.topo()
        self.assertEqual(t.best_profile([35, 35]), "2x40")
        self.assertEqual(t.best_profile([18, 18, 18]), "4x20")
        self.assertEqual(t.best_profile([10] * 7), "7x10")
        self.assertEqual(t.residual_after("2x40", [50]), 10 ** 9)                     # impossible

    @covers("GAP11-P0-07.03")
    def test_partition_names_survive_reconfigure_round_trip(self):
        t = self.topo()
        a = t.reconfigure("2x40", active_leases=0, drained=True)
        t.reconfigure("7x10", active_leases=0, drained=True)
        self.assertEqual(t.reconfigure("2x40", active_leases=0, drained=True), a)


class ScrubTests(unittest.TestCase):
    def dev(self):
        return {"device": "gpu0", "stable_id": "GPU-x"}

    @covers("GAP11-P0-08.01", "GAP11-P0-08.09", "GAP11-P0-08.10")
    def test_scrub_success_writes_evidence(self):
        clock = ManualClock()
        b = SimScrubBackend(clock=clock)
        b.load("gpu0", [7, 7, 7, 7])
        ev = ScrubExecutor(b, clock=clock).scrub(self.dev())
        self.assertTrue(ev["verified"])
        self.assertEqual(ev["steps"], ["reset", "zeroize", "verify"])
        for k in ("schema", "device", "stable_id", "started", "elapsed_s", "verify"):
            self.assertIn(k, ev)

    @covers("GAP11-P0-08.02", "GAP11-P0-08.06", "GAP11-P0-08.10")
    def test_partial_zeroize_timeout_and_permanent_fault_all_quarantine(self):
        clock = ManualClock()
        for backend, code in [(SimScrubBackend(fail="zeroize_partial"), "SCRUB_FAILED"),
                              (SimScrubBackend(fail="reset"), "SCRUB_FAILED"),
                              (SimScrubBackend(fail="health"), "SCRUB_FAILED"),
                              (SimScrubBackend(transient=99, clock=clock), "SCRUB_TIMEOUT"),
                              (SimScrubBackend(slow_s=3.0, clock=clock), "SCRUB_TIMEOUT")]:
            backend.load("gpu0", [7] * 8)
            ev = ScrubExecutor(backend, clock=clock, deadline_s=5.0).scrub(self.dev())
            self.assertFalse(ev["verified"], code)
            self.assertEqual(ev["code"], code)
        ok = SimScrubBackend(transient=2, clock=clock)
        ok.load("gpu0", [1] * 8)
        self.assertTrue(ScrubExecutor(ok, clock=clock, deadline_s=5.0).scrub(self.dev())["verified"])   # transient retried

    @covers("GAP11-P0-08.03", "GAP11-P0-08.05")
    def test_controller_quarantines_on_failed_scrub_and_blocks_cross_tenant_reuse(self):
        st = Stack(scrub_backend=SimScrubBackend(fail="zeroize_partial"))
        a = st.ctl.allocate({"tenant": "t1", "workload": "w", "memory_gb": 70}, request_id=st.rid(), actor="t1")
        with self.assertRaises(ControlError):
            st.ctl.scrub(a["device"], request_id=st.rid(), actor="op")                # leases active: illegal
        st.ctl.release(a["lease_id"], request_id=st.rid(), actor="t1")
        res = st.ctl.scrub(a["device"], request_id=st.rid(), actor="op")
        self.assertTrue(res["quarantined"])
        self.assertEqual(st.store.get(f"dev/{a['device']}")[1]["state"], "QUARANTINED")
        # t2 cannot land on it; with the other 80GB device taken it gets a refusal, never the dirty device
        st.ctl.allocate({"tenant": "t2", "workload": "x", "memory_gb": 70}, request_id=st.rid(), actor="t2")
        with self.assertRaises(ControlError):
            st.ctl.allocate({"tenant": "t2", "workload": "y", "memory_gb": 70}, request_id=st.rid(), actor="t2")
        # a successful re-scrub is the only way out
        st.backend.fail = None
        self.assertTrue(st.ctl.scrub(a["device"], request_id=st.rid(), actor="op")["completed"])
        self.assertEqual(st.store.get(f"dev/{a['device']}")[1]["security_tenant"], None)

    @covers("GAP11-P0-08.04")
    def test_no_scrub_executor_fails_closed(self):
        st = Stack()
        st.ctl.scrub_executor = None
        with self.assertRaises(ControlError) as cm:
            st.ctl.scrub("gpu2", request_id=st.rid(), actor="op")
        self.assertEqual(cm.exception.code, "DEPENDENCY_UNAVAILABLE")


class ThermalHealthTests(unittest.TestCase):
    @covers("GAP11-P1-19.01", "GAP11-P1-19.02", "GAP11-P1-19.05", "GAP11-P1-19.10")
    def test_thermal_admission_fails_closed_on_stale_or_hot(self):
        clock = ManualClock()
        th = ThermalAdmission(clock=clock)
        self.assertEqual(th.admissible("gpu0"), (False, "THERMAL_UNAVAILABLE"))       # no reading
        th.report("gpu0", temp_c=60, power_w=300)
        self.assertEqual(th.admissible("gpu0"), (True, "OK"))
        clock.advance(6)
        self.assertFalse(th.admissible("gpu0")[0])                                    # stale
        th.report("gpu0", temp_c=90, power_w=300)
        self.assertFalse(th.admissible("gpu0")[0])
        th.report("gpu0", temp_c=60, power_w=300, budget_ok=False)                    # GAP-10 budget revoked
        self.assertFalse(th.admissible("gpu0")[0])

    @covers("GAP11-P1-19.03", "GAP11-P1-19.06")
    def test_thermally_unavailable_device_cannot_be_leased(self):
        st = Stack()
        st.ctl.set_health("gpu1", thermal_ok=False, request_id=st.rid(), actor="gap10")
        st.ctl.set_health("gpu2", thermal_ok=False, request_id=st.rid(), actor="gap10")
        with self.assertRaises(ControlError) as cm:
            st.ctl.allocate({"tenant": "t1", "workload": "w", "memory_gb": 70}, request_id=st.rid(), actor="t1")
        self.assertEqual(cm.exception.code, "CAPACITY_EXHAUSTED")

    @covers("GAP11-P1-20.01", "GAP11-P1-20.02", "GAP11-P1-20.05", "GAP11-P1-20.10")
    def test_ras_classification_and_reset_storm(self):
        clock = ManualClock()
        hm = HealthMonitor(clock=clock, storm_threshold=3, storm_window_s=600)
        self.assertEqual(hm.observe("g", "ecc_uncorrectable"), "failed")
        self.assertEqual(hm.observe("g", "link_degraded"), "degraded")
        self.assertEqual(hm.observe("g", "reset"), "degraded")
        clock.advance(10); hm.observe("g", "reset")
        clock.advance(10)
        self.assertEqual(hm.observe("g", "reset"), "failed")                         # storm
        clock.advance(10_000)
        self.assertEqual(hm.observe("g", "reset"), "degraded")                        # window slid
        self.assertEqual(hm.observe("h", "ecc_correctable", 150), "failed")           # predictive threshold
        with self.assertRaises(ControlError):
            hm.observe("g", "cosmic_ray")

    @covers("GAP11-P1-20.03", "GAP11-P1-20.06")
    def test_failed_health_quarantines_and_excludes(self):
        st = Stack()
        st.ctl.set_health("gpu2", health="failed", request_id=st.rid(), actor="ras")
        d = st.store.get("dev/gpu2")[1]
        self.assertEqual((d["state"], d["quarantine_reason"]), ("QUARANTINED", "HARDWARE_FAULT"))
        with self.assertRaises(ControlError):
            st.ctl.set_health("gpu2", health="on_fire", request_id=st.rid(), actor="ras")


if __name__ == "__main__":
    unittest.main()
