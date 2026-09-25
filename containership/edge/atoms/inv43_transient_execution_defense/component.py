"""INV-43 - Transient-execution defense.

Transient-execution defense is the tax every isolation boundary pays after Spectre. Mitigations are not free and not universal, so the honest position is a per-node record of which are active, what they cost, and which trust classes may not be co-located without them.

The registry adapter participates in the 100-item INV-43 checklist. Bands
with policy-model behaviour are overridden below so those findings are backed
by exercised code; broad production-readiness claims still require external
artifacts and are tracked in ``AUDIT_REPORT.md``.
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



from .defense import (
    ACTIVE, INACTIVE, UNKNOWN,
    REQUIRED_FOR_COTENANCY,
    MitigationMissing,
    MitigationState,
)


class TransientExecutionDefenseComponent(Component):
    """Master-applied component for INV-43."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        node = MitigationState("n1", smt_enabled=False)
        for name, cost in [("spectre_v2", 3.1), ("l1tf", 1.4), ("mds", 2.0), ("mmio_stale_data", 0.8)]:
            node.record(name, ACTIVE, cost)
        report = node.report()
        _verify(report["total_cost_percent"] == 7.3 and not report["inactive_or_unknown"], "check failed: report['total_cost_percent'] == 7.3 and (not report['inactive_or_unknown'])")
        _verify(node.may_cotenant("t1", "t2")["permitted"], "check failed: node.may_cotenant('t1', 't2')['permitted']")
        findings[5] = self.satisfied(
            items[5],
            f"Mitigation state is recorded with measured cost ({report['total_cost_percent']}% total "
            f"across {len(report['active'])} mitigations), so the tax is a number rather than a shrug.",
            *self._evidence("defense.py::MitigationState"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        node = MitigationState("n1", smt_enabled=False)
        node.record("spectre_v2", ACTIVE, 3.0)
        try:
            node.may_cotenant("t1", "t2")
        except MitigationMissing:
            findings[5] = self.satisfied(
                items[5],
                "A node missing any required mitigation refuses cross-tenant co-tenancy, so partial "
                "mitigation does not buy partial co-location.",
                *self._evidence("defense.py::MitigationState.may_cotenant"))
        else:
            raise AssertionError('expected MitigationMissing was not raised; the refusal this finding claims did not happen')
        full = MitigationState("n2", smt_enabled=True, core_scheduling=False)
        for name in REQUIRED_FOR_COTENANCY:
            full.record(name, ACTIVE, 1.0)
        try:
            full.may_cotenant("t1", "t2")
        except MitigationMissing:
            findings[0] = self.satisfied(
                items[0],
                "Even fully mitigated, SMT without core scheduling blocks cross-tenant co-tenancy, because "
                "siblings share microarchitectural state the mitigations do not cover.",
                *self._evidence("defense.py::MitigationState.may_cotenant"))
        else:
            raise AssertionError('expected MitigationMissing was not raised; the refusal this finding claims did not happen')
        _verify(full.status("some_future_class") == UNKNOWN, "check failed: full.status('some_future_class') == UNKNOWN")
        findings[9] = self.satisfied(
            items[9],
            "An unrecorded mitigation reads as unknown and is treated as inactive, so a new attack class "
            "is not assumed covered by the mitigations already in place.",
            *self._evidence("defense.py::MitigationState.status"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        node = MitigationState("n1")
        try:
            node.record("spectre_v2", ACTIVE, 0.0)
        except ValueError:
            findings[6] = self.satisfied(
                items[6],
                "A mitigation cannot be recorded active without a measured cost, so the performance tax is "
                "always exported alongside the protection.",
                *self._evidence("defense.py::MitigationState.record"))
        else:
            raise AssertionError('expected ValueError was not raised; the refusal this finding claims did not happen')
        return findings

COMPONENT = TransientExecutionDefenseComponent
