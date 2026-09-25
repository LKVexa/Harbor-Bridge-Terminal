"""Standalone unit tests for INV-62 topology logic; requires only the stdlib."""
from __future__ import annotations

import math
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv62_edge_topology import (  # noqa: E402
    CapacityExceeded,
    NoCoordinatorCandidate,
    TopologyLimits,
    Topology,
    TopologyError,
    UnknownNode,
    UnknownSite,
)


def estate() -> Topology:
    topology = Topology()
    topology.add("cloud", "cloud", caps=["control", "gpu"])
    topology.add("r1", "region", parent="cloud")
    topology.add("s1-gw", "site", "s1", ["cache", "coordinator"], parent="r1")
    topology.add("s1-d1", "device", "s1", parent="s1-gw")
    topology.add("s1-d2", "device", "s1", ["gpu"], parent="s1-gw")
    topology.connect("cloud", "r1", 20)
    topology.connect("r1", "s1-gw", 60)
    topology.connect("s1-gw", "s1-d1", 2)
    topology.connect("s1-gw", "s1-d2", 3)
    return topology


class TopologyTest(unittest.TestCase):
    def test_hierarchy_is_retained(self):
        topology = estate()
        self.assertEqual(topology.nodes["r1"].parent, "cloud")
        self.assertEqual(topology.nodes["s1-gw"].parent, "r1")
        self.assertEqual(topology.nodes["s1-d1"].parent, "s1-gw")

    def test_parent_inference_is_only_unambiguous(self):
        topology = Topology()
        topology.add("cloud", "cloud")
        topology.add("r1", "region")
        topology.add("s1-gw", "site", "s1")
        topology.add("s1-d1", "device", "s1")
        self.assertEqual(topology.nodes["s1-d1"].parent, "s1-gw")
        topology.add("s1-gw-b", "site", "s1", parent="r1")
        with self.assertRaises(TopologyError):
            topology.add("s1-d2", "device", "s1")

    def test_invalid_hierarchy_is_rejected(self):
        topology = Topology()
        topology.add("cloud", "cloud")
        with self.assertRaises(TopologyError):
            topology.add("device", "device", "s1", parent="cloud")
        with self.assertRaises(UnknownNode):
            topology.add("r1", "region", parent="missing")
        with self.assertRaises(TopologyError):
            topology.add("x", "unknown")

    def test_nearest_prefers_lowest_live_latency(self):
        topology = estate()
        self.assertEqual(topology.nearest("s1-d1", "gpu"), ("s1-d2", 5.0))
        self.assertEqual(topology.distance("s1-d1", "cloud"), 82.0)

    def test_partition_detection_uses_designated_cloud(self):
        topology = estate()
        self.assertFalse(topology.partitioned("s1", cloud="cloud"))
        topology.set_link_state("r1", "s1-gw", False)
        self.assertTrue(topology.partitioned("s1", cloud="cloud"))
        self.assertEqual(topology.nearest("s1-d1", "control"), (None, None))
        self.assertEqual(topology.nearest("s1-d1", "gpu"), ("s1-d2", 5.0))

    def test_election_requires_explicit_eligibility(self):
        topology = estate()
        self.assertEqual(topology.elect("s1"), "s1-gw")
        no_candidate = Topology()
        no_candidate.add("cloud", "cloud")
        no_candidate.add("r1", "region")
        no_candidate.add("s1-gw", "site", "s1")
        with self.assertRaises(NoCoordinatorCandidate):
            no_candidate.elect("s1")

    def test_unknown_references_fail_closed(self):
        topology = estate()
        with self.assertRaises(UnknownNode):
            topology.nearest("missing", "gpu")
        with self.assertRaises(UnknownNode):
            topology.connect("cloud", "missing", 1)
        with self.assertRaises(UnknownSite):
            topology.partitioned("missing")
        with self.assertRaises(UnknownNode):
            topology.partitioned("s1", cloud="missing")
        with self.assertRaises(TopologyError):
            topology.set_link_state("cloud", "s1-gw", False)

    def test_link_validation_rejects_unsafe_values(self):
        topology = estate()
        for bad in (-1, math.inf, -math.inf, math.nan, True, "1"):
            with self.subTest(latency=bad):
                with self.assertRaises(TopologyError):
                    topology.connect("cloud", "r1", bad)
        with self.assertRaises(TopologyError):
            topology.connect("cloud", "cloud", 1)
        with self.assertRaises(TopologyError):
            topology.connect("cloud", "r1", 1, up=1)

    def test_duplicate_nodes_do_not_silently_mutate_state(self):
        topology = estate()
        with self.assertRaises(TopologyError):
            topology.add("cloud", "cloud")

    def test_snapshot_is_deterministic_and_serializable_shape(self):
        snapshot = estate().snapshot()
        self.assertEqual(snapshot["nodes"]["s1-d2"]["parent"], "s1-gw")
        self.assertEqual(snapshot["links"][0]["a"], "cloud")
        self.assertTrue(all(set(link) == {"a", "b", "latency_ms", "up"} for link in snapshot["links"]))

    def test_remove_refuses_parents_and_drops_links(self):
        topology = estate()
        with self.assertRaises(TopologyError):
            topology.remove("s1-gw")
        topology.remove("s1-d2")
        self.assertNotIn("s1-d2", topology.nodes)
        self.assertEqual(topology.nearest("s1-d1", "gpu"), ("cloud", 82.0))
        self.assertFalse(any("s1-d2" in pair for pair in topology.links))

    def test_snapshot_round_trip_is_lossless(self):
        topology = estate()
        topology.set_link_state("r1", "s1-gw", False, measured_at=5.0)
        again = Topology.from_snapshot(topology.snapshot())
        self.assertEqual(again.snapshot(), topology.snapshot())
        with self.assertRaises(TopologyError):
            Topology.from_snapshot({"nodes": {"x": {"tier": "moon"}}, "links": []})
        with self.assertRaises(TopologyError):
            Topology.from_snapshot({"nodes": {}, "links": [], "evil": 1})

    def test_resource_bounds_are_enforced(self):
        topology = Topology(limits=TopologyLimits(max_nodes=2, max_links=1, max_degree=1, max_caps_per_node=1))
        topology.add("cloud", "cloud", caps=["a"])
        topology.add("r1", "region")
        with self.assertRaises(CapacityExceeded):
            topology.add("r2", "region", parent="cloud")
        with self.assertRaises(CapacityExceeded):
            Topology(limits=TopologyLimits(max_caps_per_node=1)).add("c", "cloud", caps=["a", "b"])
        topology.connect("cloud", "r1", 1)
        topology.connect("cloud", "r1", 2)  # replacing an existing link is not growth
        with self.assertRaises(TopologyError):
            TopologyLimits(max_nodes=0)

    def test_identifier_grammar_rejects_injection(self):
        topology = Topology()
        for bad in ("a b", "x\n", "../etc", "a" * 129, "<script>", "n\x00"):
            with self.subTest(bad=bad):
                with self.assertRaises(TopologyError):
                    topology.add(bad, "cloud")

    def test_candidates_are_ordered_and_bounded(self):
        topology = estate()
        self.assertEqual(topology.candidates("s1-d1", "gpu"), [("s1-d2", 5.0), ("cloud", 82.0)])
        self.assertEqual(topology.candidates("s1-d1", "gpu", limit=1), [("s1-d2", 5.0)])

    def test_adjacency_index_tracks_links(self):
        topology = estate()
        topology.disconnect("s1-gw", "s1-d2")
        self.assertEqual(topology.nearest("s1-d1", "gpu"), ("cloud", 82.0))
        rev = topology.revision
        topology.connect("s1-gw", "s1-d2", 1)
        self.assertGreater(topology.revision, rev)
        self.assertEqual(topology.nearest("s1-d1", "gpu"), ("s1-d2", 3.0))

    def test_clone_is_independent(self):
        topology = estate()
        copy = topology.clone()
        copy.set_link_state("r1", "s1-gw", False)
        self.assertTrue(topology.links[frozenset(("r1", "s1-gw"))].up)
        self.assertFalse(topology.partitioned("s1"))


if __name__ == "__main__":
    unittest.main()
