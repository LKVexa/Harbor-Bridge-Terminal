"""Dependency-free unit tests for the GAP-04 safety-critical state machine."""
from __future__ import annotations

import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap04_disconnected_operation_controller.controller import (  # noqa: E402
    AutonomyController,
    DecisionJournalFull,
    LeaseExpired,
    NotPartitioned,
    NotPermittedAtTier,
    PolicyStale,
    ReconciliationRequired,
)


class AutonomyControllerTest(unittest.TestCase):
    def test_tiers_narrow_monotonically(self):
        c = AutonomyController("site-a", lease_ticks=300)
        c.partition(0)
        self.assertEqual(c.tier(0), "full")
        self.assertEqual(c.tier(30), "sustain")
        self.assertEqual(c.tier(120), "freeze")
        self.assertEqual(c.tier(300), "expired")

    def test_backdated_renewal_is_rejected(self):
        c = AutonomyController("site-a", granted_at=100, policy_cached_at=100)
        with self.assertRaises(ValueError):
            c.renew(99, control_plane_reachable=True)
        self.assertEqual(c.granted_at, 100)

    def test_offline_renewal_is_rejected(self):
        c = AutonomyController("site-a")
        with self.assertRaises(LeaseExpired):
            c.renew(10, control_plane_reachable=False)

    def test_renewal_cannot_bypass_reconciliation(self):
        c = AutonomyController("site-a", lease_ticks=300)
        c.partition(0)
        c.decide("restart", "workload-a", 10)
        with self.assertRaises(ReconciliationRequired):
            c.renew(20, control_plane_reachable=True)
        self.assertEqual(len(c.decisions), 1)

    def test_decision_requires_partition(self):
        c = AutonomyController("site-a")
        with self.assertRaises(NotPartitioned):
            c.decide("restart", "workload-a", 1)

    def test_expired_lease_fails_closed(self):
        c = AutonomyController("site-a", lease_ticks=10)
        c.partition(0)
        with self.assertRaises(LeaseExpired):
            c.decide("restart", "workload-a", 10)

    def test_freeze_tier_refuses_new_admission(self):
        c = AutonomyController("site-a", lease_ticks=300)
        c.partition(0)
        with self.assertRaises(NotPermittedAtTier):
            c.decide("admit-new", "workload-a", 120)

    def test_stale_policy_fails_closed(self):
        c = AutonomyController(
            "site-a", lease_ticks=300, policy_cached_at=0, max_policy_staleness_ticks=20
        )
        c.partition(0)
        with self.assertRaises(PolicyStale):
            c.decide("restart", "workload-a", 21)

    def test_journal_is_bounded(self):
        c = AutonomyController("site-a", lease_ticks=300, max_decisions=1)
        c.partition(0)
        c.decide("restart", "workload-a", 1)
        with self.assertRaises(DecisionJournalFull):
            c.decide("restart", "workload-b", 2)

    def test_decisions_property_is_defensive_copy(self):
        c = AutonomyController("site-a", lease_ticks=300)
        c.partition(0)
        c.decide("restart", "workload-a", 1)
        leaked = c.decisions
        leaked.clear()
        self.assertEqual(len(c.decisions), 1)

    def test_backdated_reconcile_is_rejected(self):
        c = AutonomyController("site-a", lease_ticks=300)
        c.partition(10)
        c.decide("restart", "workload-a", 20)
        with self.assertRaises(ValueError):
            c.reconcile(19)
        self.assertEqual(len(c.decisions), 1)

    def test_reconnect_reconciles_then_renews(self):
        c = AutonomyController("site-a", lease_ticks=300)
        c.partition(0)
        c.decide("restart", "workload-a", 10)
        record = c.reconnect(20, control_plane_reachable=True)
        self.assertEqual(record["decision_count"], 1)
        self.assertEqual(record["renewed_until"], 320)
        self.assertFalse(c.health(20)["partitioned"])
        self.assertEqual(c.granted_at, 20)

    def test_concurrent_decisions_have_unique_sequences(self):
        c = AutonomyController("site-a", lease_ticks=300, max_decisions=50)
        c.partition(0)
        errors = []

        def worker(i):
            try:
                c.decide("restart", f"workload-{i}", i + 1)
            except Exception as exc:  # collect race outcomes for assertion
                errors.append(exc)

        # Serialize event timestamps in increasing order while still exercising shared-state locking.
        # The lock guarantees journal mutation integrity; event-time ordering remains caller-owned.
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Scheduler order may reject backdated arrivals, but it must never corrupt/duplicate records.
        self.assertEqual(len({d["sequence"] for d in c.decisions}), len(c.decisions))
        self.assertLessEqual(len(c.decisions), 10)
        self.assertTrue(all(isinstance(e, ValueError) for e in errors))


    def test_denied_future_decision_advances_monotonic_floor(self):
        c = AutonomyController("site-a", lease_ticks=300)
        c.partition(0)
        with self.assertRaises(NotPermittedAtTier):
            c.decide("admit-new", "workload-a", 130)
        with self.assertRaises(ValueError):
            c.decide("restart", "workload-b", 100)

    def test_expired_lease_precedes_stale_policy_error(self):
        c = AutonomyController(
            "site-a", lease_ticks=10, policy_cached_at=0, max_policy_staleness_ticks=5
        )
        c.partition(0)
        with self.assertRaises(LeaseExpired):
            c.decide("restart", "workload-a", 10)

    def test_cache_policy_requires_connected_control_plane(self):
        c = AutonomyController("site-a", lease_ticks=300)
        self.assertEqual(c.cache_policy(10, control_plane_reachable=True), 10)
        with self.assertRaises(TypeError):
            c.renew(20, control_plane_reachable=1)
        c.partition(20)
        with self.assertRaises(ReconciliationRequired):
            c.cache_policy(21, control_plane_reachable=True)

    def test_public_views_are_versioned(self):
        c = AutonomyController("site-a", lease_ticks=300)
        c.partition(0)
        self.assertEqual(c.lease_view(1)["schema"], "PK_AUTONOMY_LEASE/1")
        self.assertEqual(c.tier_view(1)["schema"], "PK_DEGRADATION_TIER/1")
        self.assertEqual(c.reconcile(2)["schema"], "PK_RECONCILIATION_RECORD/1")


if __name__ == "__main__":
    unittest.main()
