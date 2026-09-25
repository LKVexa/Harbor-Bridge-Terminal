"""INV-58 - Existing service-mesh layer.

The existing service-mesh layer is already doing mTLS, retries and routing for
current workloads, and the new runtime has to coexist with it rather than
duplicate it.  The sharpest hazard is retry multiplication: three app attempts
through a mesh that also performs three attempts is nine attempts against a
struggling service.  This element owns the division of labour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .mesh_logic import (
    BypassDetector,
    RoutePolicyRegistry,
    Unmappable,
    effective_attempts,
    map_identity,
    reconcile,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ExistingServiceMeshLayerComponent(Component):
    """Master-applied component for INV-58."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        naive = effective_attempts(3, 3)
        r = reconcile("orders->payments", 3, 3, budget=3)
        total = effective_attempts(r["app"], r["mesh"])
        _verify(
            naive == 9
            and total == 3
            and r["owner"] == "app"
            and not (r["app"] > 1 and r["mesh"] > 1),
            "retry reconciliation did not enforce single-layer ownership and budget",
        )
        registry = RoutePolicyRegistry()
        migrated = registry.migrate_route("orders->payments", 3, 3, budget=3)
        _verify(
            migrated["revision"] == 1 and registry.get("orders->payments")["mesh"] == 1,
            "route migration registry did not activate the reconciled policy atomically",
        )
        findings[0] = self.satisfied(
            items[0],
            f"Left alone, 3 app attempts through 3 mesh attempts is {naive} attempts per call; "
            f"reconciliation gives retry ownership to exactly one layer and reduces the call to "
            f"{total} attempts, inside its budget. Route migration is copy-on-write and revisioned.",
            *self._evidence("mesh_logic.py::reconcile", "mesh_logic.py::RoutePolicyRegistry"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        _verify(
            map_identity("spiffe://estate.local/ns/shop/sa/orders", "estate.local")
            == "runtime:ns/shop/sa/orders",
            "valid estate SPIFFE identity failed to map",
        )
        foreign = False
        try:
            map_identity("spiffe://evil.example/ns/shop/sa/orders", "estate.local")
        except Unmappable:
            foreign = True
        else:
            _verify(False, "foreign SPIFFE trust domain was accepted")

        ambiguous = False
        try:
            map_identity("spiffe://estate.local/ns/shop/../admin", "estate.local")
        except Unmappable:
            ambiguous = True
        else:
            _verify(False, "ambiguous SPIFFE path was accepted")

        det = BypassDetector({"payments"}, max_flags=2)
        _verify(
            foreign
            and ambiguous
            and det.observe("legacy-cron", "payments", mtls=False)
            and not det.observe("orders", "payments", True),
            "identity/bypass security checks failed",
        )
        findings[0] = self.satisfied(
            items[0],
            "Mesh certificate identities fail closed unless they are unambiguous SPIFFE IDs in the "
            "configured trust domain; plaintext traffic to a meshed service is flagged in a bounded, "
            "thread-safe evidence buffer.",
            *self._evidence("mesh_logic.py::map_identity", "mesh_logic.py::BypassDetector"),
        )
        return findings


COMPONENT = ExistingServiceMeshLayerComponent
