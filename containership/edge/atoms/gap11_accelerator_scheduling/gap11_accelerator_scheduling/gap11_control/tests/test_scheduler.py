"""P0-14 quotas/fairness, P1-17 topology/gang, P1-18 fragmentation, P1-22 preemption,
P1-23 constraint engine — 'scheduler template' .01-.10."""
from __future__ import annotations

import random
import unittest

from support import GPU0, GPU1, GPU2, Stack, covers
from gap11_control.common import ControlError, ManualClock
from gap11_control.scheduler import (ConstraintEngine, FairQueue, QuotaBook, choose_victims, fragmentation,
                                     gang_candidates, place_partition)

T = lambda c, *n: tuple(f"GAP11-{c}.{i:02d}" for i in n)
SCHED = ("P0-14", "P1-17", "P1-18", "P1-22", "P1-23")


def engine():
    return ConstraintEngine(
        hard={"security": lambda r, d: d.get("security_tenant") in (None, r["tenant"]),
              "health": lambda r, d: d.get("health", "ok") == "ok",
              "thermal": lambda r, d: d.get("thermal_ok", True),
              "residency": lambda r, d: d.get("region", "eu") == r.get("region", "eu"),
              "features": lambda r, d: set(r.get("features", [])) <= set(d["features"])},
        soft={"cost": lambda r, d: d["memory_gb"] - r.get("memory_gb", 0),
              "locality": lambda r, d: 0 if d["topology"].get("fabric") == r.get("fabric") else 1})


class ConstraintTests(unittest.TestCase):
    @covers(*T("P1-23", 1, 2, 3, 9), *T("P0-14", 2, 3, 9), *T("P1-17", 9))
    def test_hard_constraints_never_traded_for_score(self):
        devs = [{**GPU1, "security_tenant": "t9"}, {**GPU2, "health": "failed"}, {**GPU0}]
        d = engine().decide({"tenant": "t1", "memory_gb": 70}, devs)
        # gpu0 is too small for a *soft* reason only; gpu1/gpu2 are hard-rejected
        self.assertEqual(d.device, "gpu0")
        rej = {r["device"]: r.get("rejected_by") for r in d.reasons}
        self.assertEqual(rej["gpu1"], "security")
        self.assertEqual(rej["gpu2"], "health")
        # precedence: a device failing both security and health reports the higher class
        d2 = engine().decide({"tenant": "t1"}, [{**GPU1, "security_tenant": "t9", "health": "failed"}])
        self.assertEqual((d2.device, d2.reasons[0]["rejected_by"]), (None, "security"))
        with self.assertRaises(ControlError):
            ConstraintEngine(hard={"vibes": lambda r, d: True})

    @covers(*T("P1-23", 4), *T("P0-14", 4), *T("P1-18", 4), *T("P1-17", 4))
    def test_decisions_independent_of_input_order(self):
        rng = random.Random(7)
        devs = [{**GPU1, "device": f"g{i}"} for i in range(12)]
        base = engine().decide({"tenant": "t1", "memory_gb": 10}, devs)
        for _ in range(50):
            rng.shuffle(devs)
            self.assertEqual(engine().decide({"tenant": "t1", "memory_gb": 10}, devs).device, base.device)
        self.assertEqual(base.device, "g0")                                           # explicit id tiebreak


class QuotaFairnessTests(unittest.TestCase):
    @covers(*T("P0-14", 6), *T("P1-22", 6))
    def test_quota_secure_default_and_caps(self):
        q = QuotaBook({"t1": {"devices": 2, "memory_gb": 100}})
        q.check("t1", [], {"memory_gb": 50})
        with self.assertRaises(ControlError):
            q.check("t1", [{"tenant": "t1", "memory_gb": 60}], {"memory_gb": 50})
        with self.assertRaises(ControlError):
            q.check("t1", [{"tenant": "t1"}, {"tenant": "t1"}], {})
        with self.assertRaises(ControlError) as cm:
            q.check("stranger", [], {})                                               # no quota = no access
        self.assertEqual(cm.exception.code, "QUOTA_EXCEEDED")

    @covers(*T("P0-14", 6), *T("P1-23", 6), *T("P1-17", 6))
    def test_fair_queue_starvation_bound_and_backpressure(self):
        clock = ManualClock()
        q = FairQueue(capacity=50, clock=clock, aging_s=30)
        q.push("low-tenant", {"priority": "low"})
        served_low_at = None
        for i in range(40):                                                          # sustained high-priority flood
            q.push("hog", {"priority": "high"})
            clock.advance(2)
            it = q.pop()
            if it["tenant"] == "low-tenant":
                served_low_at = clock.monotonic() - 1000
                break
        self.assertIsNotNone(served_low_at)
        self.assertLessEqual(served_low_at, 2 * 30 + 2)                              # documented bound
        full = FairQueue(capacity=2, clock=clock)
        full.push("a", {}); full.push("a", {})
        with self.assertRaises(ControlError) as cm:
            full.push("b", {})
        self.assertEqual(cm.exception.code, "OVERLOADED")

    @covers(*T("P0-14", 6))
    def test_round_robin_between_equal_tenants(self):
        q = FairQueue(capacity=100, clock=ManualClock())
        for _ in range(10):
            q.push("a", {}); q.push("b", {})
        order = [q.pop()["tenant"] for _ in range(10)]
        self.assertLessEqual(abs(order.count("a") - order.count("b")), 1)


class TopologyGangTests(unittest.TestCase):
    @covers(*T("P1-17", 1, 3), *T("P0-14", 1))
    def test_gang_candidates_share_fabric_domain(self):
        devs = [GPU0, GPU1, GPU2, {**GPU2, "device": "gpu3"}]
        self.assertEqual(gang_candidates(devs, 2), [["gpu0", "gpu1"], ["gpu2", "gpu3"]])
        self.assertEqual(gang_candidates(devs, 3), [])

    @covers(*T("P1-17", 5), *T("P0-14", 5), *T("P1-18", 5), *T("P1-22", 5), *T("P1-23", 5))
    def test_gang_allocation_is_all_or_nothing(self):
        st = Stack()
        before = st.store.revision
        with self.assertRaises(ControlError):
            st.ctl.allocate_gang([{"tenant": "t1", "workload": f"r{i}", "memory_gb": 70} for i in range(3)],
                                 request_id=st.rid(), actor="t1")
        self.assertEqual(st.store.revision, before)                                  # nothing persisted
        self.assertEqual(st.ctl.leases(), {})
        g = st.ctl.allocate_gang([{"tenant": "t1", "workload": f"r{i}", "memory_gb": 70} for i in range(2)],
                                 request_id=st.rid(), actor="t1")
        self.assertEqual(sorted(m["device"] for m in g["members"]), ["gpu1", "gpu2"])
        self.assertEqual(len({st.store.get(f"lease/{m['lease_id']}")[0] for m in g["members"]}), 1)   # one revision


class FragmentationTests(unittest.TestCase):
    @covers(*T("P1-18", 1, 3, 7), *T("P0-14", 7))
    def test_fragmentation_metric_and_slice_placement(self):
        devs = [{**GPU0}, {**GPU1, "partitions": [{"name": "a", "memory_gb": 40}, {"name": "b", "memory_gb": 40}]}]
        leases = [{"device": "gpu1", "partition": "a", "memory_gb": 40, "tenant": "t"}]
        f = fragmentation(devs, leases, typical_gb=30)
        self.assertEqual(f["free_gb"], 24 + 40)
        self.assertEqual(f["unusable_gb"], 24)                                       # gpu0 whole, but < 30 GB
        # prefers the partially used device's slice, keeping whole devices whole
        devs2 = [{**GPU1, "device": "x", "partitions": [{"name": "a", "memory_gb": 40}, {"name": "b", "memory_gb": 40}]},
                 {**GPU1, "device": "y", "partitions": [{"name": "a", "memory_gb": 40}, {"name": "b", "memory_gb": 40}]}]
        self.assertEqual(place_partition(devs2, 30, [{"device": "y", "partition": "a"}]), ("y", "b"))
        self.assertEqual(place_partition(devs2, 30, []), ("x", "a"))
        self.assertIsNone(place_partition(devs2, 50, []))

    @covers(*T("P1-18", 2, 6, 9))
    def test_whole_device_lease_blocks_slices_and_vice_versa(self):
        devs = [{**GPU1, "device": "x", "partitions": [{"name": "a", "memory_gb": 40}]}]
        self.assertIsNone(place_partition(devs, 10, [{"device": "x", "partition": None}]))


class PreemptionTests(unittest.TestCase):
    @covers(*T("P1-22", 1, 2, 3, 8), *T("P0-14", 8))
    def test_victim_eligibility(self):
        leases = [
            {"lease_id": "a", "priority": "low", "created_mono": 0},
            {"lease_id": "b", "priority": "low", "created_mono": 50},
            {"lease_id": "c", "priority": "normal", "created_mono": 0},
            {"lease_id": "d", "priority": "low", "created_mono": 0, "non_preemptible": True},
            {"lease_id": "e", "priority": "low", "created_mono": 95},
        ]
        v = choose_victims({"priority": "high"}, leases, now=100, min_runtime_s=30)
        self.assertEqual([x["lease_id"] for x in v], ["b"])                          # youngest eligible low
        self.assertEqual(choose_victims({"priority": "low"}, leases, now=100), [])  # never equal/higher
        self.assertEqual(choose_victims({"priority": "high"}, leases, now=100, need_devices=3, budget=2), [])

    @covers(*T("P1-22", 4, 7))
    def test_preemption_feature_gate_defaults_off(self):
        from gap11_control.config import ConfigManager
        self.assertFalse(ConfigManager().active["feature_gates"]["preemption"])


class AdversarialTests(unittest.TestCase):
    @covers(*T("P0-14", 10), *T("P1-17", 10), *T("P1-18", 10), *T("P1-22", 10), *T("P1-23", 10),
            "GAP11-P0-16.07", "GAP11-P2-35.07", "GAP11-P2-36.07")
    def test_randomised_contention_preserves_invariants(self):
        """Property test (stdlib, seeded): under random allocate/release/scrub/heartbeat with
        retries, (1) one owner per whole device, (2) no cross-tenant reuse before scrub,
        (3) capacity conserved, (4) idempotent retries never add leases."""
        rng = random.Random(20260922)
        st = Stack(devices=[GPU0, GPU1, GPU2, {**GPU2, "device": "gpu3"}])
        tenants = ["t1", "t2", "t3"]
        last_rid: dict[str, tuple] = {}
        for step in range(400):
            op = rng.random()
            try:
                if op < 0.45:
                    t = rng.choice(tenants)
                    req = {"tenant": t, "workload": f"w{step}", "memory_gb": rng.choice([0, 6, 12, 20, 70])}
                    if rng.random() < 0.3:
                        req["partition"] = rng.choice(["half", "quarter", "nope"])
                    rid = st.rid()
                    st.ctl.allocate(req, request_id=rid, actor=t)
                    last_rid[rid] = (req, len(st.ctl.leases()))
                    if rng.random() < 0.3:                                             # client retry
                        n = len(st.ctl.leases())
                        st.ctl.allocate(req, request_id=rid, actor=t)
                        self.assertEqual(len(st.ctl.leases()), n)
                elif op < 0.8 and st.ctl.leases():
                    lid = rng.choice(sorted(st.ctl.leases()))
                    st.ctl.release(lid, request_id=st.rid(), actor="x")
                else:
                    dev = rng.choice(["gpu0", "gpu1", "gpu2", "gpu3"])
                    st.ctl.scrub(dev, request_id=st.rid(), actor="op")
            except ControlError:
                pass
            leases = [l for _, (_, l) in st.ctl.leases().items()]
            for name, (_, d) in st.ctl.devices().items():
                mine = [l for l in leases if l["device"] == name]
                self.assertLessEqual(sum(1 for l in mine if l["partition"] is None), 1)
                if any(l["partition"] is None for l in mine):
                    self.assertEqual(len(mine), 1)
                self.assertLessEqual(len({l["tenant"] for l in mine}), 1)
                if mine:
                    self.assertEqual(d["security_tenant"], mine[0]["tenant"])
                    parts = [l["partition"] for l in mine if l["partition"]]
                    self.assertEqual(len(parts), len(set(parts)))
                    self.assertLessEqual(sum(l["memory_gb"] or 0 for l in mine), d["memory_gb"])
        self.assertTrue(st.store.verify()["consistent"])


if __name__ == "__main__":
    unittest.main()
