"""GAP-14 - Data-gravity manager.

The data-gravity manager decides whether the computation moves to the data or the data moves to the computation. It costs both directions honestly against residency and egress, and it will recommend neither rather than propose a move that residency forbids.

The component answers all 100 requirements of the GAP-14 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .engine import (
    COMPUTE_MOVE_COST,
    EGRESS_PER_GB,
    CostModelError,
    Dataset,
    GravityDecisionError,
    GravityManager,
    NoLegalOption,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class DataGravityManagerComponent(Component):
    """Master-applied component for GAP-14."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        g = GravityManager(residency={"dub": {"public"}, "ams": {"public"}},
                           distance={("dub", "ams"): 1.0, ("ams", "dub"): 1.0},
                           compute_sites=frozenset({"dub", "ams"}))
        big = Dataset("lake", "dub", size_gb=500, classification="public")
        small = Dataset("lookup", "dub", size_gb=2, classification="public")
        _verify(g.recommend(big, "ams")["direction"] == "move-compute", "check failed: g.recommend(big, 'ams')['direction'] == 'move-compute'")
        _verify(g.recommend(small, "ams")["direction"] == "move-data", "check failed: g.recommend(small, 'ams')['direction'] == 'move-data'")
        findings[5] = self.satisfied(
            items[5],
            "The cost model inverts at the expected scale: a 500GB dataset pulls the compute to it, a 2GB "
            "dataset moves to the compute.",
            *self._evidence("component.py::GravityManager.recommend"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        g = GravityManager(residency={"dub": {"pii", "public"}, "ams": {"public"}},
                           distance={("dub", "ams"): 1.0, ("ams", "dub"): 1.0},
                           compute_sites=frozenset({"dub", "ams"}))
        pii = Dataset("customers", "dub", size_gb=1, classification="pii")
        result = g.recommend(pii, "ams")
        _verify(result["direction"] == "move-compute", "cheap illegal move-data was chosen")
        _verify(any("may not hold pii" in e for e in result["eliminated"]), "check failed: any(('may not hold pii' in e for e in result['eliminated']))")
        findings[5] = self.satisfied(
            items[5],
            "A 1GB PII dataset is not moved to a non-PII site even though moving it is far cheaper: "
            "residency eliminates the option before cost is compared.",
            *self._evidence("component.py::GravityManager.recommend"))
        pinned = GravityManager(residency={"dub": {"pii"}, "ams": {"public"}},
                                compute_sites=frozenset({"ams"}))
        try:
            pinned.recommend(Dataset("pinned", "dub", 1, "pii"), "ams")
        except NoLegalOption:
            findings[8] = self.satisfied(
                items[8],
                "When residency forbids both directions the answer is a refusal, not the least-bad move.",
                *self._evidence("component.py::GravityManager.recommend"))
        else:
            raise AssertionError('expected NoLegalOption was not raised; the refusal this finding claims did not happen')
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        g = GravityManager(residency={"dub": {"public"}, "ams": {"public"}},
                           compute_sites=frozenset({"ams"}))
        unconverged = Dataset("live", "dub", size_gb=1, classification="public", converged=False)
        try:
            g.recommend(unconverged, "ams")
        except NoLegalOption as exc:
            _verify("unresolved replication conflicts" in str(exc), "check failed: 'unresolved replication conflicts' in str(exc)")
            findings[3] = self.satisfied(
                items[3],
                "A dataset with open replication conflicts is not moved; GAP-05 convergence is a "
                "precondition, so a move cannot silently pick a conflict winner.",
                *self._evidence("component.py::GravityManager.recommend"))
        else:
            raise AssertionError('expected NoLegalOption was not raised; the refusal this finding claims did not happen')
        same = g.recommend(Dataset("d", "ams", 1, "public"), "ams")
        _verify(same["direction"] == "none" and same["cost"] == 0.0, "check failed: same['direction'] == 'none' and same['cost'] == 0.0")
        findings[4] = self.satisfied(
            items[4],
            "Recommending a move for already co-located data is a no-op rather than a wasted transfer, so "
            "repeated calls are idempotent.",
            *self._evidence("component.py::GravityManager.recommend"))
        return findings

COMPONENT = DataGravityManagerComponent
