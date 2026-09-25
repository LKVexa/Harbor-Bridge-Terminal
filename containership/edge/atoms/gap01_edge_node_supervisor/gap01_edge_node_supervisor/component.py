"""GAP-01 - Edge Node Supervisor.

The edge node supervisor is the single local authority on a node: it owns the node's lifecycle state machine, drains workloads before the node stops accepting them, and keeps the node honest when the control plane is unreachable. Nothing else on the node may declare it healthy.

The component answers all 100 requirements of the GAP-01 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
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

from .supervisor import (
    DRAIN_ORDER, HEALTH_STALENESS_BOUND, TRANSITIONS,
    DrainIncomplete, IllegalTransition, NodeSupervisor,
)


class EdgeNodeSupervisorComponent(Component):
    """Master-applied component for GAP-01."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        sup = NodeSupervisor("n1")
        sup.transition("ready")
        sup.report_health("kubelet-equivalent", 0)
        sup.admit("a", "trusted")
        sup.admit("b", "untrusted")
        sup.admit("c", "third-party")
        _verify(sup.drain_order() == ["b", "c", "a"], "drain order ignored trust class")
        result = sup.drain(now=10, deadline=20)
        _verify(result["complete"] and sup.state == "stopped" and not sup.workloads, "check failed: result['complete'] and sup.state == 'stopped' and (not sup.workloads)")
        findings[5] = self.satisfied(
            items[5],
            "Drain is deterministic and trust-ordered: untrusted released first, node reached stopped "
            "with zero residents.",
            *self._evidence("component.py::NodeSupervisor.drain"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        sup = NodeSupervisor("n1")
        sup.transition("ready")
        sup.transition("cordoned", reason="operator cordon")
        try:
            sup.admit("late", "trusted")
        except IllegalTransition:
            findings[5] = self.satisfied(
                items[5], "A cordoned node refuses admission outright rather than deferring to the scheduler.",
                *self._evidence("component.py::NodeSupervisor.admit"))
        else:
            raise AssertionError('expected IllegalTransition was not raised; the refusal this finding claims did not happen')
        fresh = NodeSupervisor("n2")
        fresh.transition("ready")
        _verify(not fresh.healthy_at(0), "a node with no health signals reported healthy")
        findings[7] = self.satisfied(
            items[7],
            "Health is affirmative evidence: a node with no reported signals is not healthy, so a silenced "
            "reporter cannot keep a node in service.",
            *self._evidence("component.py::NodeSupervisor.healthy_at"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        sup = NodeSupervisor("n1")
        sup.transition("ready")
        sup.report_health("s", 0)
        sup.admit("stuck", "trusted")
        result = sup.drain(now=10, deadline=5, stubborn={"stuck"})
        _verify(not result["complete"] and sup.state == "draining", "check failed: not result['complete'] and sup.state == 'draining'")
        findings[0] = self.satisfied(
            items[0],
            "A workload that refuses to drain holds the node in draining and records an escalation; "
            "the node never reports stopped while a resident remains.",
            *self._evidence("component.py::NodeSupervisor.drain"))
        try:
            NodeSupervisor("n3", state="stopped").transition("ready")
        except IllegalTransition:
            findings[6] = self.satisfied(
                items[6], "stopped is terminal: no transition out of it is accepted.",
                *self._evidence("component.py::TRANSITIONS"))
        else:
            raise AssertionError('expected IllegalTransition was not raised; the refusal this finding claims did not happen')
        _verify(not sup.healthy_at(HEALTH_STALENESS_BOUND + 1), 'check failed: not sup.healthy_at(HEALTH_STALENESS_BOUND + 1)')
        findings[8] = self.satisfied(
            items[8],
            f"A health signal older than {HEALTH_STALENESS_BOUND} ticks makes the node unhealthy, so "
            "staleness is visible rather than silently tolerated.",
            *self._evidence("component.py::NodeSupervisor.healthy_at"))
        return findings

COMPONENT = EdgeNodeSupervisorComponent
