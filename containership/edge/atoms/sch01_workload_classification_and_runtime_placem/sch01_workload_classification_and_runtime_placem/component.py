"""pk_core conformance adapter for SCH-01.

The scheduler decision engine lives in :mod:`.engine` so its safety-critical logic can
be tested without the external conformance framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .engine import (
    FRESHNESS_BOUND,
    NodeReport,
    Unplaceable,
    Workload,
    candidates,
    classify,
    place,
)


def _verify(condition, message="behavioural check failed"):
    """Fail behavioural checks even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class WorkloadClassificationAndRuntimePlacementComponent(Component):
    """Master-applied conformance component for SCH-01."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        nodes = [
            NodeReport("n1", "eu", frozenset({"process", "wasm"}), free_slots=2),
            NodeReport("n2", "eu", frozenset({"process", "wasm", "microvm"}), free_slots=2),
        ]
        first = place(Workload("w1", "t1", "internal"), nodes)
        _verify(first["tier"] == "process", "did not choose the weakest sufficient tier")
        again = place(
            Workload("w1", "t1", "internal"),
            [
                NodeReport("n1", "eu", frozenset({"process", "wasm"}), free_slots=2),
                NodeReport("n2", "eu", frozenset({"process", "wasm", "microvm"}), free_slots=2),
            ],
        )
        _verify(again["node"] == first["node"], "placement is not deterministic for identical inputs")
        findings[5] = self.satisfied(
            items[5],
            f"Placement is deterministic and tier-minimal: {first['workload']} -> {first['node']} "
            f"({first['tier']}), {first['candidates_considered']} candidates considered.",
            *self._evidence("engine.py::place"),
        )
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        klass = classify(Workload("w", "t1", "public"))
        _verify(
            klass["trust_class"] == "untrusted" and klass["required_tier"] == "microvm",
            "public provenance did not map to untrusted/microvm",
        )
        findings[0] = self.satisfied(
            items[0],
            "Classification and placement are separate steps: classify() derives the trust class from "
            "provenance, place() binds a node, and neither may substitute for the other.",
            *self._evidence("engine.py::classify", "engine.py::place"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        weak = [NodeReport("n1", "eu", frozenset({"process", "wasm"}), free_slots=4)]
        try:
            place(Workload("hostile", "t1", "quarantined"), weak)
        except Unplaceable:
            findings[5] = self.satisfied(
                items[5],
                "A quarantined workload is refused rather than placed onto a node offering only weak tiers.",
                *self._evidence("engine.py::place"),
            )
        else:
            raise AssertionError("expected Unplaceable was not raised")

        occupied = [
            NodeReport(
                "n1", "eu", frozenset({"microvm"}), free_slots=4, occupants={"other": "t2"}
            )
        ]
        try:
            place(Workload("w", "t1", "public"), occupied)
        except Unplaceable:
            findings[1] = self.satisfied(
                items[1],
                "Cross-tenant co-location fails closed when occupancy metadata cannot prove a safe shared tier.",
                *self._evidence("engine.py::rejection_reasons"),
            )
        else:
            raise AssertionError("expected Unplaceable was not raised")

        klass = classify(Workload("w", "t1", "public", latency_sensitive=True))
        _verify(klass["trust_class"] == "untrusted", "public provenance did not remain untrusted")
        findings[0] = self.satisfied(
            items[0],
            "Trust class is derived from provenance, so a workload cannot self-declare its way to a weaker tier.",
            *self._evidence("engine.py::classify"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        stale = [NodeReport("n1", "eu", frozenset({"process"}), free_slots=4, reported_at=0)]
        try:
            place(Workload("w", "t1", "internal"), stale, now=FRESHNESS_BOUND + 1)
        except Unplaceable:
            findings[0] = self.satisfied(
                items[0],
                f"Nodes whose report is older than {FRESHNESS_BOUND} ticks are excluded rather than trusted.",
                *self._evidence("engine.py::rejection_reasons"),
            )
        else:
            raise AssertionError("expected Unplaceable was not raised")

        hot = [NodeReport("n1", "eu", frozenset({"process"}), free_slots=4, thermally_excluded=True)]
        try:
            place(Workload("w", "t1", "internal"), hot)
        except Unplaceable:
            findings[2] = self.satisfied(
                items[2],
                "A fully thermally-excluded candidate set produces a named refusal, not a forced placement.",
                *self._evidence("engine.py::rejection_reasons"),
            )
        else:
            raise AssertionError("expected Unplaceable was not raised")

        inv33 = sibling("INV-33")
        if inv33 is None:
            findings[4] = self.partial(
                items[4],
                "Placement leases carry an expiry but this package does not own execution-side reclamation.",
                note="INV-33 Virtualization controller is not installed here",
            )
        else:
            nodes = [NodeReport("n1", "eu", frozenset({"process"}), free_slots=2)]
            placement = place(Workload("w1", "t1", "internal"), nodes, now=0, lease_ticks=10)
            controller = inv33.VirtualizationController(placement["node"])
            controller.grant(placement["workload"], placement["tenant"], now=0, ticks=10)
            controller.start(placement["workload"], now=1)
            renewed = controller.renew(placement["workload"], now=5, ticks=10)
            _verify(renewed.expires_at == 15, "lease renewal produced the wrong expiry")
            report = controller.reconcile(actual={placement["workload"], "stowaway"}, now=30)
            _verify(report["reclaimed_expired"] == ["w1"], "expired lease was not reclaimed")
            _verify(report["reclaimed_orphans"] == ["stowaway"], "orphan was not reclaimed")
            _verify(report["orphans_remaining"] == 0, "orphans remain after reconciliation")
            findings[4] = self.satisfied(
                items[4],
                "The placement lease is honoured end to end by the INV-33 controller, including renewal "
                "and reconciliation of expired or orphaned execution.",
                *self._evidence("engine.py::place"),
                "INV-33/VirtualizationController.reconcile",
            )

        gap03 = sibling("GAP-03")
        if gap03 is None:
            findings[7] = self.partial(
                items[7],
                "The local scorer has no cross-decision fair-share ledger.",
                note="GAP-03 Topology-aware scheduler is not installed here",
            )
        else:
            share = gap03.FairShare(reserved={"t1": 4, "t2": 4}, capacity=10)
            share.claim("t1", 4)
            _verify(share.starved() == ["t2"], "starvation state not reported")
            try:
                share.claim("t1", 4)
                crowded_out = True
            except gap03.ShareViolation:
                crowded_out = False
            _verify(not crowded_out, "a noisy tenant consumed another tenant's reservation")
            share.claim("t2", 4)
            _verify(share.starved() == [], "starvation state did not clear")
            findings[7] = self.satisfied(
                items[7],
                "The GAP-03 fair-share guard prevents a tenant past its reservation from consuming another's.",
                *self._evidence("engine.py::place"),
                "GAP-03/FairShare",
            )
        return findings


# Correct public name plus a compatibility alias for 4.1.x callers.
WorkloadClassificationAndRuntimePlacemenComponent = WorkloadClassificationAndRuntimePlacementComponent
COMPONENT = WorkloadClassificationAndRuntimePlacementComponent
