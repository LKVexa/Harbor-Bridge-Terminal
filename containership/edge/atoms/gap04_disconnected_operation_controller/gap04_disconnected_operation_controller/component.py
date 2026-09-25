"""GAP-04 conformance adapter for the disconnected-operation controller.

The safety-critical state machine lives in :mod:`controller` without a
``pk_core`` dependency. This module only maps that behavior into the Post-
Kubernetes conformance framework.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .controller import (
    PERMITTED,
    AutonomyController,
    LeaseExpired,
    NotPermittedAtTier,
    PolicyStale,
    ReconciliationRequired,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class DisconnectedOperationControllerComponent(Component):
    """Conformance adapter for GAP-04."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        c = AutonomyController("dub", granted_at=0, lease_ticks=300)
        c.partition(0)
        _verify(c.tier(0) == "full", "check failed: c.tier(0) == 'full'")
        _verify(c.tier(40) == "sustain", "check failed: c.tier(40) == 'sustain'")
        _verify(c.tier(130) == "freeze", "check failed: c.tier(130) == 'freeze'")
        c.decide("admit-new", "w1", 0)
        c.decide("admit-known", "w2", 40)
        c.decide("restart", "w3", 130)
        record = c.reconcile(140)
        _verify(record["decision_count"] == 3 and not c.decisions,
                "check failed: reconciliation must contain and clear all decisions")
        findings[5] = self.satisfied(
            items[5],
            f"Degradation is monotone with partition age (full -> sustain -> freeze) and all "
            f"{record['decision_count']} local decisions survive into the reconciliation record.",
            *self._evidence("controller.py::AutonomyController"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        c = AutonomyController("dub", granted_at=0, lease_ticks=60)
        c.partition(0)
        try:
            c.renew(30, control_plane_reachable=False)
        except LeaseExpired:
            findings[3] = self.satisfied(
                items[3],
                "A lease cannot be renewed without real control-plane contact, so a site cannot extend its "
                "own authority by staying partitioned.",
                *self._evidence("controller.py::AutonomyController.renew"))
        else:
            raise AssertionError("expected LeaseExpired was not raised")
        try:
            c.decide("admit-new", "w", 61)
        except LeaseExpired:
            findings[1] = self.satisfied(
                items[1],
                "Once the lease expires the site decides nothing at all; authority goes to zero rather than "
                "defaulting open.",
                *self._evidence("controller.py::AutonomyController.decide"))
        else:
            raise AssertionError("expected LeaseExpired was not raised")
        fresh = AutonomyController("ams", granted_at=0, lease_ticks=300)
        fresh.partition(0)
        try:
            fresh.decide("admit-new", "w", 130)
        except NotPermittedAtTier:
            findings[5] = self.satisfied(
                items[5],
                "Admitting new work is refused at the freeze tier, so a long partition narrows what the "
                "site may do instead of widening it.",
                *self._evidence("controller.py::PERMITTED"))
        else:
            raise AssertionError("expected NotPermittedAtTier was not raised")
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        c = AutonomyController("dub", granted_at=0, lease_ticks=300, policy_cached_at=0)
        c.partition(0)
        c.decide("restart", "w", 100)
        record = c.reconcile(110)
        _verify(record["max_policy_age"] == 100,
                "check failed: record['max_policy_age'] == 100")
        findings[7] = self.satisfied(
            items[7],
            "Each offline decision carries policy age, partition epoch, lease bounds, and a reason so the "
            "decision remains explainable after reconnect.",
            *self._evidence("controller.py::AutonomyController.decide"))
        return findings


COMPONENT = DisconnectedOperationControllerComponent
