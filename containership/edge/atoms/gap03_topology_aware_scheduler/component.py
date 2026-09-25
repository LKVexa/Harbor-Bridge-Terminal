"""GAP-03 - Topology-aware scheduler.

The topology-aware scheduler supplies what a flat scheduler cannot: locality cost and fair share. It scores candidates by how far they are from the data and the caller, and it refuses to let one tenant's demand crowd out another's floor.

The conformance adapter emits findings for all 100 GAP-03 checklist controls.
Selected bands are overridden below so important claims are backed by exercised
runtime behaviour.  A complete finding set is not, by itself, production
certification; external evidence gaps are tracked in MISSING_COMPONENTS.md.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)


from .scheduler import (
    FairShare,
    NotInTopology,
    ReservationOversubscribed,
    ShareViolation,
    Topology,
    rank,
    score_candidates,
)


class TopologyAwareSchedulerComponent(Component):
    """Master-applied component for GAP-03."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        topo = Topology()
        topo.place("a", "eu", "dub", "r1")
        topo.place("b", "eu", "dub", "r2")
        topo.place("c", "eu", "ams", "r1")
        topo.place("d", "us", "iad", "r1")
        _verify(topo.cost("a", "a") == 0 < topo.cost("a", "b") < topo.cost("a", "c") < topo.cost("a", "d"), "check failed: topo.cost('a', 'a') == 0 < topo.cost('a', 'b') < topo.cost('a', 'c') < topo.cost('a', 'd')")
        order = rank(topo, "a", ["d", "c", "b"])
        _verify(order == ["b", "c", "d"], f"ranking is not locality-ordered: {order}")
        _verify(rank(topo, "a", ["d", "c", "b"]) == order, "ranking is not deterministic")
        strict_spread = rank(topo, "a", ["a", "d"], spread_from=["a"])
        _verify(strict_spread == ["d", "a"], f"strict failure-domain spreading failed: {strict_spread}")
        share = FairShare(reserved={"t1": 1}, capacity=2)
        scored = score_candidates(topo, "a", ["b", "c"], fair_share=share, tenant="t1")
        _verify(scored.fairness.allowed, "score did not return an allowed fairness verdict")
        _verify(scored.ranked_nodes() == ["b", "c"], f"unexpected scored order: {scored.ranked_nodes()}")
        findings[5] = self.satisfied(
            items[5],
            f"Locality cost is monotone and deterministic ({order}); requested spreading is strict "
            f"({strict_spread}); scoring returns the fair-share verdict alongside candidate scores.",
            *self._evidence("scheduler.py::TopologySnapshot.cost", "scheduler.py::rank", "scheduler.py::score_candidates"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[1] = self.satisfied(
            items[1],
            "This element supplies cost and a fairness verdict only; SCH-01 keeps the placement decision, "
            "so hard-constraint filtering is never traded away for a better locality score.",
            *self._evidence("contract.py", "scheduler.py::rank", "scheduler.py::score_candidates"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        topo = Topology()
        topo.place("a", "eu", "dub", "r1")
        try:
            topo.cost("a", "rogue")
        except NotInTopology:
            findings[6] = self.satisfied(
                items[6],
                "A node absent from the declared topology cannot be scored, so a forged node cannot pull "
                "work toward itself.",
                *self._evidence("scheduler.py::TopologySnapshot.path"))
        else:
            raise AssertionError('expected NotInTopology was not raised; the refusal this finding claims did not happen')
        share = FairShare(reserved={"t1": 4, "t2": 4}, capacity=10)
        share.claim("t1", 4)
        try:
            share.claim("t1", 4)
        except ShareViolation:
            findings[5] = self.satisfied(
                items[5],
                "A tenant past its own reservation cannot claim capacity reserved for another tenant.",
                *self._evidence("scheduler.py::FairShare.claim"))
        else:
            raise AssertionError('expected ShareViolation was not raised; the refusal this finding claims did not happen')
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        share = FairShare(reserved={"t1": 4, "t2": 4}, capacity=10)
        share.claim("t1", 4)
        _verify(share.starved() == ["t2"], "starvation went undetected")
        share.claim("t2", 4)
        _verify(share.starved() == [], 'check failed: share.starved() == []')
        findings[7] = self.satisfied(
            items[7],
            "Starvation is detected as a first-class state: a tenant below its reservation is reported "
            "before its demand is served.",
            *self._evidence("scheduler.py::FairShare.starved"))
        oversubscribed = FairShare(reserved={"t1": 4, "t2": 4}, capacity=7)
        try:
            oversubscribed.claim("t1", 1)
        except ReservationOversubscribed:
            pass
        else:
            raise AssertionError("oversubscribed reservations must fail closed")
        topo = Topology()
        topo.place("a", "eu", "dub", "r1")
        topo.place("b", "eu", "ams", "r1")
        topo.place("c", "eu", "dub", "r2")
        spread = rank(topo, "a", ["c", "b"], spread_from=["a"])
        _verify(spread[0] == "b", "anti-affinity did not penalise the shared failure domain")
        findings[6] = self.satisfied(
            items[6],
            "Requested anti-affinity strictly ranks unused site failure domains ahead of used ones, "
            "bounding blast radius across sites.",
            *self._evidence("scheduler.py::rank"))
        return findings

COMPONENT = TopologyAwareSchedulerComponent
