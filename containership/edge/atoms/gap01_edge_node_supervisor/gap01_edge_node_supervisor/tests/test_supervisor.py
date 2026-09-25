"""Dependency-free behavioral tests for the local supervisor runtime."""
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap01_edge_node_supervisor import (  # noqa: E402
    DrainIncomplete, IllegalTransition, NodeSupervisor,
)


class SupervisorBehaviorTest(unittest.TestCase):
    def ready(self):
        sup = NodeSupervisor("n1")
        sup.transition("ready")
        sup.report_health("runtime", 10)
        return sup

    def test_no_health_means_no_placement(self):
        sup = NodeSupervisor("n1")
        sup.transition("ready")
        self.assertFalse(sup.accepts_placement)

    def test_future_health_is_not_valid(self):
        sup = NodeSupervisor("n1", health={"runtime": 10}, clock=10)
        self.assertFalse(sup.healthy_at(9))

    def test_time_regression_rejected(self):
        sup = self.ready()
        with self.assertRaises(ValueError):
            sup.report_health("runtime", 9)
        with self.assertRaises(ValueError):
            sup.drain(now=9, deadline=20)

    def test_duplicate_workload_rejected(self):
        sup = self.ready()
        sup.admit("w", "trusted")
        with self.assertRaises(ValueError):
            sup.admit("w", "trusted")

    def test_cordon_blocks_placement(self):
        sup = self.ready()
        sup.transition("cordoned")
        with self.assertRaises(IllegalTransition):
            sup.admit("late", "trusted")

    def test_drain_is_trust_ordered_and_stops(self):
        sup = self.ready()
        sup.admit("trusted", "trusted")
        sup.admit("hostile", "hostile")
        sup.admit("third", "third-party")
        result = sup.drain(now=11, deadline=20)
        self.assertEqual(result["released"], ["hostile", "third", "trusted"])
        self.assertTrue(result["complete"])
        self.assertEqual(sup.state, "stopped")

    def test_deadline_escalation_is_idempotent(self):
        sup = self.ready()
        sup.admit("stuck", "trusted")
        a = sup.drain(now=21, deadline=20, stubborn={"stuck"})
        b = sup.drain(now=21, deadline=20, stubborn={"stuck"})
        self.assertIsNotNone(a["escalation"])
        self.assertIsNotNone(b["escalation"])
        self.assertEqual(len(sup.breaches), 1)

    def test_cannot_stop_with_residents(self):
        sup = self.ready()
        sup.admit("w", "trusted")
        with self.assertRaises(DrainIncomplete):
            sup.transition("stopped")

    def test_stopped_is_terminal(self):
        sup = NodeSupervisor("n1", state="stopped")
        with self.assertRaises(IllegalTransition):
            sup.transition("ready")


if __name__ == "__main__":
    unittest.main()
