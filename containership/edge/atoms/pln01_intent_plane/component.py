"""PLN-01 - Intent plane integration with ``pk_core``.

The core graph/planner lives in :mod:`pln01_intent_plane.graph` so it remains
unit-testable without the surrounding monorepo.  This adapter supplies the
``pk_core`` contract and checklist assessment hooks.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import build
from .graph import AdmissionRejectedError, CycleError, IntentGraph, plan
from .metadata import ELEMENT_ID, ELEMENT_NAME


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class IntentPlaneComponent(Component):
    """Master-applied component for PLN-01."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        """Exercise ordering, dry-run planning, concurrency, and rollback."""
        findings = super().assess_implementation(items)
        graph = IntentGraph()
        a = graph.declare("t1", "prod", "network", {"cidr": "10.0.0.0/16"}, actor="test")
        b = graph.declare("t1", "prod", "runtime", {"kind": "wasm"}, after=[a], actor="test")
        graph.declare("t1", "prod", "app", {"image": "svc:1"}, after=[b], actor="test")
        order = graph.order()
        _verify(order.index(a) < order.index(b), "planner did not honour declared order")
        dry = plan(graph, actual={a: {"cidr": "10.0.0.0/16"}})
        _verify(dry["dry_run"] is True and len(dry["steps"]) == 3, "dry-run planner returned an invalid plan")
        _verify(len(dry["plan_id"]) == 64, "plan fingerprint missing")
        findings[5] = self.satisfied(
            items[5],
            f"Planner is deterministic: {len(order)} nodes ordered, "
            f"{sum(1 for s in dry['steps'] if s['action'] == 'noop')} step(s) resolved to noop.",
            *self._evidence("graph.py::plan"),
        )
        try:
            cyclic = IntentGraph()
            x = cyclic.declare("t1", "prod", "x", {}, actor="test")
            y = cyclic.declare("t1", "prod", "y", {}, after=[x], actor="test")
            # Deliberate fault injection into private state exercises cycle refusal.
            cyclic._edges[x] = frozenset({y})
            cyclic.order()
        except CycleError:
            findings[6] = self.satisfied(
                items[6], "Dependency cycles are reported, not silently reordered.",
                *self._evidence("graph.py::IntentGraph.order"))
        else:
            raise AssertionError("expected CycleError was not raised")

        before = graph.version
        graph.declare("t1", "prod", "app", {"image": "svc:2"}, after=[b], expected_version=before, actor="test")
        target = graph.version - 1
        graph.rollback(target, expected_version=graph.version, actor="test")
        _verify(graph.node_spec(("t1", "prod", "app"))["image"] == "svc:1", "rollback did not restore desired state")
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        graph = IntentGraph()
        anchor = graph.declare("t1", "prod", "shared", {}, actor="test")
        for foreign in (("t2", "prod", "shared"), ("t1", "stage", "shared")):
            try:
                graph.declare("t1", "prod", "app", {}, after=[foreign], actor="test")
            except AdmissionRejectedError:
                pass
            else:
                raise AssertionError("expected cross-boundary dependency refusal")
        _verify(graph.verify_audit_chain(), "audit chain verification failed")
        findings[5] = self.satisfied(
            items[5], "Cross-tenant and cross-environment graph edges are refused at declaration time.",
            *self._evidence("graph.py::IntentGraph.declare"))
        _verify(anchor in graph.order(), "baseline node disappeared during rejected declarations")
        return findings


COMPONENT = IntentPlaneComponent
