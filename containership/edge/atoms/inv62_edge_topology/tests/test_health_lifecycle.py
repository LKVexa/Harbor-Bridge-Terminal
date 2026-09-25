"""Link health thresholds/hysteresis/flap/staleness (MC-042) and lifecycle
state machines (MC-007, MC-046)."""
from __future__ import annotations

import unittest

import support  # noqa: F401

from inv62_edge_topology.production.health import HealthPolicy, LinkHealth
from inv62_edge_topology.production.lifecycle import (ALLOWED, COORDINATOR_TRANSITIONS, LINK_TRANSITIONS,
                                                       NODE_TRANSITIONS, SITE_TRANSITIONS, CoordinatorState,
                                                       IllegalTransition, LinkState, Machine, Mode, NodeState,
                                                       SiteState)


class LinkHealthTest(unittest.TestCase):
    def setUp(self):
        self.p = HealthPolicy(probe_interval_s=1, suspect_after_s=3, stale_after_s=10, down_after_failures=3,
                              up_after_successes=2, flap_window_s=60, max_flaps=4)

    def test_hysteresis(self):
        h = LinkHealth(self.p)
        self.assertEqual(h.probe(True, 0), LinkState.UP)
        self.assertEqual(h.probe(False, 1), LinkState.SUSPECT)
        self.assertTrue(h.routable())
        h.probe(False, 2)
        self.assertEqual(h.probe(False, 3), LinkState.DOWN)
        self.assertEqual(h.probe(True, 4), LinkState.DOWN)  # one good probe is not enough
        self.assertEqual(h.probe(True, 5), LinkState.UP)

    def test_flap_suppression_holds_link_down(self):
        h = LinkHealth(self.p)
        t = 0
        h.probe(True, t)
        for _ in range(3):
            for _ in range(3):
                t += 1; h.probe(False, t)
            for _ in range(2):
                t += 1; h.probe(True, t)
        self.assertEqual(h.state, LinkState.FLAPPING)
        self.assertFalse(h.routable())
        t += 1
        self.assertEqual(h.probe(True, t), LinkState.FLAPPING)
        self.assertEqual(h.probe(True, t + 61), LinkState.UP)

    def test_missed_probes_suspect_then_stale(self):
        h = LinkHealth(self.p)
        h.probe(True, 0)
        self.assertEqual(h.evaluate(3.5), LinkState.SUSPECT)
        self.assertEqual(h.evaluate(11), LinkState.STALE)
        self.assertFalse(h.routable())
        self.assertEqual(h.probe(True, 12), LinkState.UP)

    def test_policy_from_config_ignores_unknown(self):
        self.assertEqual(HealthPolicy.from_config({"max_flaps": 9, "zzz": 1}).max_flaps, 9)


class MachineTest(unittest.TestCase):
    def test_tables_are_closed_over_their_enums(self):
        for table, enum in ((NODE_TRANSITIONS, NodeState), (LINK_TRANSITIONS, LinkState),
                            (SITE_TRANSITIONS, SiteState), (COORDINATOR_TRANSITIONS, CoordinatorState)):
            self.assertEqual(set(table), set(enum))
            for targets in table.values():
                self.assertTrue(targets <= set(enum))

    def test_illegal_transitions_raise_and_history_is_bounded(self):
        m = Machine(NodeState.DISCOVERED, NODE_TRANSITIONS, max_history=3)
        m.to(NodeState.ACTIVE, "ok")
        with self.assertRaises(IllegalTransition):
            m.to(NodeState.RETIRED, "skip draining")
        self.assertFalse(m.to(NodeState.ACTIVE, "noop"))
        for _ in range(3):
            m.to(NodeState.QUARANTINED, "q"); m.to(NodeState.ACTIVE, "r")
        self.assertEqual(len(m.history), 3)
        r = Machine(NodeState.RETIRED, NODE_TRANSITIONS)
        for s in NodeState:
            if s is not NodeState.RETIRED:
                self.assertFalse(r.can(s))

    def test_partitioned_site_must_recover_before_connected(self):
        m = Machine(SiteState.CONNECTED, SITE_TRANSITIONS)
        m.to(SiteState.PARTITIONED, "uplink lost")
        with self.assertRaises(IllegalTransition):
            m.to(SiteState.CONNECTED, "jump")

    def test_mode_allowances(self):
        self.assertEqual(ALLOWED[Mode.NOT_READY], frozenset())
        self.assertNotIn("graph.apply", ALLOWED[Mode.FROZEN])
        self.assertNotIn("partition.acquire", ALLOWED[Mode.FROZEN])
        self.assertIn("nearest.resolve", ALLOWED[Mode.FROZEN])
        self.assertTrue(ALLOWED[Mode.FROZEN] < ALLOWED[Mode.NORMAL])


if __name__ == "__main__":
    unittest.main()
