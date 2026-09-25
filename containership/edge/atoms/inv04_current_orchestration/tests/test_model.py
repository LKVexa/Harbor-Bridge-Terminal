"""Dependency-free safety tests for the INV-04 orchestration model."""
from __future__ import annotations

import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv04_current_orchestration import (  # noqa: E402
    BudgetBreach,
    Cluster,
    ConfigurationError,
    NoCapacity,
    StateIntegrityError,
    UnknownNode,
)


class ClusterModelTest(unittest.TestCase):
    def test_reconcile_converges_and_balances_deterministically(self):
        c = Cluster(["b", "a"], desired={"web": 4})
        self.assertEqual(c.reconcile(), 4)
        self.assertEqual(c.pods, [("web", "a"), ("web", "b"), ("web", "a"), ("web", "b")])
        self.assertEqual(c.reconcile(), 0)

    def test_invalid_desired_is_rejected_before_any_mutation(self):
        c = Cluster(["n1"], desired={"a": 1, "z": -1})
        before = (list(c.nodes), list(c.pods))
        with self.assertRaises(ConfigurationError):
            c.reconcile()
        self.assertEqual((c.nodes, c.pods), before)

    def test_boolean_replica_count_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            Cluster(["n1"], desired={"web": True}).reconcile()

    def test_budget_breach_is_atomic(self):
        c = Cluster(["n1", "n2"], desired={"db": 2}, min_available={"db": 2})
        c.reconcile()
        before = (list(c.nodes), list(c.pods))
        with self.assertRaises(BudgetBreach):
            c.drain("n1")
        self.assertEqual((c.nodes, c.pods), before)

    def test_no_capacity_drain_is_atomic(self):
        c = Cluster(["n1"], desired={"api": 1})
        c.reconcile()
        before = (list(c.nodes), list(c.pods))
        with self.assertRaises(NoCapacity):
            c.drain("n1")
        self.assertEqual((c.nodes, c.pods), before)

    def test_unknown_node_is_atomic(self):
        c = Cluster(["n1"], desired={"api": 1})
        c.reconcile()
        before = (list(c.nodes), list(c.pods))
        with self.assertRaises(UnknownNode):
            c.drain("missing")
        self.assertEqual((c.nodes, c.pods), before)

    def test_invalid_budget_configuration_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            Cluster(["n1"], desired={"api": 1}, min_available={"api": 2}).reconcile()
        with self.assertRaises(ConfigurationError):
            Cluster(["n1"], desired={}, min_available={"api": 0}).reconcile()

    def test_observed_pod_on_unknown_node_is_rejected(self):
        c = Cluster(["n1"], pods=[("api", "gone")], desired={"api": 1})
        with self.assertRaises(StateIntegrityError):
            c.inventory()

    def test_duplicate_nodes_are_rejected(self):
        with self.assertRaises(ConfigurationError):
            Cluster(["n1", "n1"], desired={}).reconcile()

    def test_unmanaged_running_workload_is_rejected(self):
        c = Cluster(["n1"], pods=[("orphan", "n1")], desired={})
        with self.assertRaises(StateIntegrityError):
            c.drain("n1")

    def test_inventory_is_deterministic(self):
        c = Cluster(["n1", "n2"], desired={"z": 1, "a": 2})
        c.reconcile()
        self.assertEqual(list(c.inventory()), ["a", "z"])
        self.assertEqual(c.inventory()["a"], sorted(c.inventory()["a"]))

    def test_failures_have_stable_machine_readable_codes(self):
        err = NoCapacity("no nodes")
        self.assertEqual(err.as_dict(), {"code": "ORCH_NO_CAPACITY", "message": "no nodes"})


if __name__ == "__main__":
    unittest.main()
