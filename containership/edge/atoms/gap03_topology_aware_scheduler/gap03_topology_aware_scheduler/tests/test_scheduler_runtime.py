"""Runtime unit tests for GAP-03; stdlib-only and independent of pk_core."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = PKG_DIR / "scheduler.py"
spec = importlib.util.spec_from_file_location("gap03_scheduler_runtime", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
if spec.loader is None:
    raise RuntimeError(f"cannot load runtime module: {MODULE_PATH}")
spec.loader.exec_module(mod)

FairShare = mod.FairShare
NotInTopology = mod.NotInTopology
ReservationOversubscribed = mod.ReservationOversubscribed
ShareViolation = mod.ShareViolation
StaleFairShare = mod.StaleFairShare
Topology = mod.Topology
TopologyConflict = mod.TopologyConflict
rank = mod.rank
score_candidates = mod.score_candidates


class TopologyTests(unittest.TestCase):
    def setUp(self):
        self.topo = Topology()
        self.topo.place("a", "eu", "dub", "r1")
        self.topo.place("b", "eu", "dub", "r1")
        self.topo.place("c", "eu", "dub", "r2")
        self.topo.place("d", "eu", "ams", "r1")
        self.topo.place("e", "us", "iad", "r1")

    def test_cost_is_strictly_monotone(self):
        self.assertEqual(self.topo.cost("a", "a"), 0)
        self.assertLess(self.topo.cost("a", "b"), self.topo.cost("a", "c"))
        self.assertLess(self.topo.cost("a", "c"), self.topo.cost("a", "d"))
        self.assertLess(self.topo.cost("a", "d"), self.topo.cost("a", "e"))

    def test_unknown_same_node_is_rejected(self):
        with self.assertRaises(NotInTopology):
            self.topo.cost("rogue", "rogue")

    def test_conflicting_rewrite_requires_explicit_replace(self):
        generation = self.topo.generation
        with self.assertRaises(TopologyConflict):
            self.topo.place("a", "us", "sea", "r9")
        self.assertEqual(self.topo.generation, generation)
        self.topo.place("a", "us", "sea", "r9", replace=True)
        self.assertEqual(self.topo.path("a"), ("us", "sea", "r9"))
        self.assertEqual(self.topo.generation, generation + 1)

    def test_labels_are_canonical(self):
        for bad in ("", " a", "a ", "a\n"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                Topology().place(bad, "eu", "dub", "r1")
        with self.assertRaises(ValueError):
            Topology().place("a", "eu/west", "dub", "r1")

    def test_spread_is_strict_even_against_same_node_locality(self):
        # Old soft penalty selected 'a' (same node) ahead of a cross-region
        # candidate.  Requested spreading now always prefers an unused site.
        self.assertEqual(rank(self.topo, "a", ["a", "e"], spread_from=["a"]), ["e", "a"])

    def test_duplicate_candidates_are_rejected(self):
        with self.assertRaises(ValueError):
            rank(self.topo, "a", ["b", "b"])

    def test_external_topology_corruption_fails_closed(self):
        self.topo.nodes["rogue"] = ("eu", "bad/site", "r1")
        with self.assertRaises(ValueError):
            self.topo.snapshot()


class FairShareTests(unittest.TestCase):
    def test_protects_other_tenant_reservation(self):
        share = FairShare(reserved={"t1": 4, "t2": 4}, capacity=10)
        share.claim("t1", 6)
        with self.assertRaises(ShareViolation):
            share.claim("t1", 1)
        self.assertEqual(share.held("t1"), 6)
        share.claim("t2", 4)
        self.assertEqual(share.total_used(), 10)

    def test_physical_capacity_is_enforced_inside_own_reservation(self):
        share = FairShare(reserved={"t1": 10}, capacity=5)
        with self.assertRaises(ReservationOversubscribed):
            share.claim("t1", 1)
        self.assertEqual(share.total_used(), 0)

    def test_capacity_exhaustion_without_reservations(self):
        share = FairShare(capacity=2)
        share.claim("t1", 2)
        with self.assertRaises(ShareViolation):
            share.claim("t1", 1)

    def test_release_cannot_underflow(self):
        share = FairShare(capacity=2)
        share.claim("t1", 2)
        self.assertEqual(share.release("t1"), 1)
        with self.assertRaises(ValueError):
            share.release("t1", 2)

    def test_invalid_ledger_values_are_rejected(self):
        for kwargs in (
            {"capacity": -1},
            {"capacity": True},
            {"reserved": {"t": -1}, "capacity": 1},
            {"used": {"t": 2}, "capacity": 1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                FairShare(**kwargs)



    def test_allowed_claim_preserves_every_other_unmet_reservation(self):
        tenants = ("a", "b")
        for capacity in range(1, 6):
            for reserved_a in range(capacity + 1):
                for reserved_b in range(capacity - reserved_a + 1):
                    reserved = {"a": reserved_a, "b": reserved_b}
                    for used_a in range(capacity + 1):
                        for used_b in range(capacity - used_a + 1):
                            used = {"a": used_a, "b": used_b}
                            share = FairShare(reserved=reserved, used=used, capacity=capacity)
                            for tenant in tenants:
                                for slots in range(1, capacity + 1):
                                    verdict = share.verdict(tenant, slots)
                                    if not verdict.allowed:
                                        continue
                                    after = dict(used)
                                    after[tenant] = after.get(tenant, 0) + slots
                                    free_after = capacity - sum(after.values())
                                    other_unmet = sum(
                                        max(0, reservation - after.get(other, 0))
                                        for other, reservation in reserved.items()
                                        if other != tenant
                                    )
                                    self.assertGreaterEqual(
                                        free_after,
                                        other_unmet,
                                        (capacity, reserved, used, tenant, slots, verdict),
                                    )

    def test_stale_score_token_is_rejected_at_claim(self):
        share = FairShare(reserved={"t": 2}, capacity=3)
        verdict = share.verdict("t", 1)
        share.claim("other", 1)
        with self.assertRaises(StaleFairShare):
            share.claim("t", 1, expected_state_token=verdict.state_token)

    def test_external_ledger_corruption_fails_closed(self):
        share = FairShare(capacity=2)
        share.used["t"] = -1
        with self.assertRaises(ValueError):
            share.verdict("t", 1)

    def test_claims_are_atomic_with_threads(self):
        share = FairShare(capacity=25)
        successes = 0
        success_lock = threading.Lock()

        def worker():
            nonlocal successes
            try:
                share.claim("t", 1)
            except ShareViolation:
                return
            with success_lock:
                successes += 1

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(successes, 25)
        self.assertEqual(share.total_used(), 25)


class ScoringTests(unittest.TestCase):
    def test_scoring_reports_fairness_without_claiming(self):
        topo = Topology()
        topo.place("a", "eu", "dub", "r1")
        topo.place("b", "eu", "ams", "r1")
        share = FairShare(reserved={"t": 1}, capacity=1)
        result = score_candidates(topo, "a", ["b"], fair_share=share, tenant="t")
        self.assertTrue(result.fairness.allowed)
        self.assertEqual(result.fairness.reason, "within_reservation")
        self.assertEqual(result.ranked_nodes(), ["b"])
        self.assertEqual(share.total_used(), 0)
        share.claim("t", 1, expected_state_token=result.fairness.state_token)
        self.assertEqual(share.total_used(), 1)


if __name__ == "__main__":
    unittest.main()
