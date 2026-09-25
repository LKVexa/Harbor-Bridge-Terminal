"""INV-06 - Traditional IaC master-applied component adapter.

The package-local state engine lives in :mod:`state`; this module binds that
engine to ``pk_core`` and exercises representative checklist behaviours.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .state import IacState, InvalidPlan, InvalidState, ProtectedResource, StalePlan


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class TraditionalIacComponent(Component):
    """Master-applied component for INV-06."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        s = IacState()
        s.apply(s.plan({"vpc": "10.0/16", "db": "large"}))
        alice = s.plan({"vpc": "10.0/16", "db": "xlarge"})
        bob = s.plan({"vpc": "10.1/16", "db": "large"})
        s.apply(alice)
        stale = False
        try:
            s.apply(bob)
        except StalePlan:
            stale = True
        _verify(stale and s.resources["db"] == "xlarge", "stale plan safety check failed")
        findings[0] = self.satisfied(
            items[0],
            "Two plans computed against the same serial cannot both apply: once Alice's lands, Bob's "
            "stale plan is refused instead of silently reverting her database change.",
            *self._evidence("state.py::IacState.apply"),
        )

        s.protect("db")
        protected = False
        try:
            s.plan({"vpc": "10.0/16"})
        except ProtectedResource:
            protected = True
        _verify(protected and "db" in s.resources, "protected resource safety check failed")
        findings[1] = self.satisfied(
            items[1],
            "A plan that would destroy a protected resource is refused, and protection changes advance "
            "the state serial so older plans are invalidated.",
            *self._evidence("state.py::IacState.protect", "state.py::IacState.plan"),
        )
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        s = IacState()
        s.apply(s.plan({"sg": "443", "vm": "small"}))
        d = s.drift({"sg": "443,22", "vm": "small", "bucket": "tmp"})
        _verify(set(d) == {"sg", "bucket"}, "drift detection check failed")
        _verify(s.verify_audit_chain(), "audit chain verification failed")
        findings[0] = self.satisfied(
            items[0],
            "Drift is reported by comparing real resources with state, while the in-memory audit chain "
            "records the scan without including resource values.",
            *self._evidence("state.py::IacState.drift", "state.py::IacState.verify_audit_chain"),
        )
        return findings


COMPONENT = TraditionalIacComponent

__all__ = [
    "COMPONENT",
    "TraditionalIacComponent",
    "IacState",
    "StalePlan",
    "ProtectedResource",
    "InvalidPlan",
    "InvalidState",
]
