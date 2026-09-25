"""INV-04 - Current orchestration conformance adapter.

The executable orchestration model lives in :mod:`.model` and is intentionally
independent of ``pk_core``.  This module adapts it to the estate-level 100-item
conformance framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .model import BudgetBreach, Cluster


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class CurrentOrchestrationComponent(Component):
    """Master-applied component for INV-04."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        c = Cluster(["n1", "n2", "n3"], desired={"api": 3}, min_available={"api": 2})
        c.reconcile()
        moved = c.drain("n1")
        _verify(
            moved == 1 and len([p for p in c.pods if p[0] == "api"]) == 3,
            "drain did not reschedule the evicted replica",
        )

        tight = Cluster(["n1", "n2"], desired={"db": 2}, min_available={"db": 2})
        tight.reconcile()
        before = (list(tight.nodes), list(tight.pods))
        try:
            tight.drain("n1")
        except BudgetBreach:
            pass
        else:
            raise AssertionError("budget-breaching drain was not refused")
        _verify((tight.nodes, tight.pods) == before, "refused drain mutated cluster state")

        findings[0] = self.satisfied(
            items[0],
            "A budget-safe drain proceeds and reschedules the evicted replica; a drain that would "
            "violate min_available is refused atomically before node or pod state changes.",
            *self._evidence("model.py::Cluster.drain"),
        )
        return findings

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        c = Cluster(["a", "b"], desired={"web": 4})
        c.reconcile()
        c.pods.pop()
        c.desired["web"] = 2
        c.reconcile()
        _verify(len(c.pods) == 2 and c.reconcile() == 0, "reconcile did not converge idempotently")
        findings[0] = self.satisfied(
            items[0],
            "Running replicas are corrected toward desired state in both directions, and a converged "
            "cluster is idempotent. Reconciliation validates and plans before committing mutation.",
            *self._evidence("model.py::Cluster.reconcile"),
        )
        return findings


COMPONENT = CurrentOrchestrationComponent
