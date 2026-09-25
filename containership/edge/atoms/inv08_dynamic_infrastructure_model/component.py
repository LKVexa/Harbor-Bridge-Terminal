"""INV-08 - Dynamic infrastructure model adapter.

The executable behavior in this package is a bounded lease-backed elastic pool.
The wider 100-item production checklist is *not* proven by this module alone;
``pk_core`` supplies the conformance framework and production evidence must be
provided by the surrounding system.  Package-local gaps are tracked in
``MISSING_COMPONENTS.md``.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import build
from .metadata import ELEMENT_ID, ELEMENT_NAME
from .model import Pool


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class DynamicInfrastructureModelComponent(Component):
    """``pk_core`` adapter for INV-08."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = Pool(min_nodes=1, max_nodes=5)
        spike = p.tick(0, demand=1000)
        _verify(spike["size"] == 5, "check failed: spike['size'] == 5")
        busy = sorted(p.nodes)[:2]
        for node_id in busy:
            p.set_busy(node_id)
        calm = p.tick(20, demand=0)
        _verify(
            all(node_id in p.nodes for node_id in busy) and calm["size"] == 2,
            "busy nodes were reclaimed or calm size was incorrect",
        )
        findings[0] = self.satisfied(
            items[0],
            "A demand spike of 1000 units grows the pool only to its 5-node bound; "
            "when demand drops, idle nodes are reclaimed but the two nodes still "
            "running work keep renewed leases and stay.",
            *self._evidence("model.py::Pool.tick"),
        )
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        p = Pool(min_nodes=1, max_nodes=10)
        sizes = [p.tick(t, d)["size"] for t, d in enumerate([4, 16, 40, 8, 0, 0])]
        _verify(
            sizes == [1, 4, 10, 2, 1, 1],
            "check failed: demand-following size sequence changed",
        )
        findings[0] = self.satisfied(
            items[0],
            f"Pool size follows demand within bounds ({sizes}) and falls back to the "
            f"minimum when idle; accounting reports {p.node_hours} node-hours at the "
            "default one-hour tick interval.",
            *self._evidence("model.py::Pool.tick"),
        )
        return findings


COMPONENT = DynamicInfrastructureModelComponent
