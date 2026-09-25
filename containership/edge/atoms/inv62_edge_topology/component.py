"""INV-62 - Edge topology conformance adapter.

The executable topology engine lives in :mod:`.topology`; this module binds it
to the external ``pk_core`` checklist/conformance framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import build
from .metadata import ELEMENT_ID, ELEMENT_NAME
from .topology import Topology


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class EdgeTopologyComponent(Component):
    """Conformance component for INV-62."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _estate(self) -> Topology:
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

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        topology = self._estate()
        node, latency_ms = topology.nearest("s1-d1", "gpu")
        _verify(
            (node, latency_ms) == ("s1-d2", 5.0),
            "nearest-capable resolution did not choose the 5 ms on-site GPU",
        )
        _verify(
            topology.nodes["s1-d1"].parent == "s1-gw",
            "device parent hierarchy was not retained",
        )
        findings[0] = self.satisfied(
            items[0],
            "Resolution uses the validated hierarchy and measured live-link latency: a GPU request from "
            "s1-d1 resolves to the on-site s1-d2 (5 ms), not the cloud path (82 ms).",
            *self._evidence("topology.py::Topology.add", "topology.py::Topology.nearest"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        topology = self._estate()
        _verify(not topology.partitioned("s1", cloud="cloud"), "healthy site was reported partitioned")
        topology.set_link_state("r1", "s1-gw", False)
        node, _ = topology.nearest("s1-d1", "control")
        _verify(node is None, "routing crossed a down uplink")
        _verify(topology.partitioned("s1", cloud="cloud"), "uplink loss was not detected as a partition")
        _verify(topology.elect("s1") == "s1-gw", "ineligible node won coordinator election")
        _verify(topology.nearest("s1-d1", "gpu")[0] == "s1-d2", "on-site routing failed in partition")
        findings[0] = self.satisfied(
            items[0],
            "When the site uplink goes down, no route crosses it, designated-cloud reachability reports "
            "the partition, an eligible site-local coordinator is elected deterministically, and on-site "
            "capabilities continue to resolve.",
            *self._evidence(
                "topology.py::Topology.partitioned",
                "topology.py::Topology.elect",
                "topology.py::Topology.set_link_state",
            ),
        )
        return findings


COMPONENT = EdgeTopologyComponent
