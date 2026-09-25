"""INV-66 - Enterprise Wasm control plane.

The enterprise Wasm control plane sits above many lattices and many teams. It adds what a single lattice lacks: who may deploy where, which registries and signers are acceptable, and a record of every change. Guardrails are enforced at admission, so a manifest that pulls from an unapproved registry never reaches a deployment manager.

The component answers all 100 requirements of the INV-66 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .control_plane import ControlPlane  # 4.2.0 local engine: behavioural fixture only (DEP-01)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)


class EnterpriseWasmControlPlaneComponent(Component):
    """Master-applied component for INV-66."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _cp(self):
        # The pk_core bands exercise the 4.2.0 decision engine as a fixture.  The production path is
        # production.service.ControlPlaneService (authenticated principals, signatures, journal).
        return ControlPlane(roles={("dev", "staging"): "deployer", ("ops", "prod"): "deployer"},
                            registries=frozenset({"registry.estate.local"}),
                            signers=frozenset({"release-signer"}))

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        cp = self._cp()
        good = {"components": [{"name": "api", "image": "registry.estate.local/api:1", "signer": "release-signer"}]}
        evil = {"components": [{"name": "api", "image": "ghcr.evil.example/api:1", "signer": "someone"}]}
        _verify(cp.admit("ops", "prod", good)["admitted"], "check failed: cp.admit('ops', 'prod', good)['admitted']")
        _verify(not cp.admit("dev", "prod", good)["admitted"], "check failed: not cp.admit('dev', 'prod', good)['admitted']")
        d = cp.admit("ops", "prod", evil)
        _verify(not d["admitted"] and len(d["reasons"]) == 2 and list(cp.forwarded) == [good], "check failed: not d['admitted'] and len(d['reasons']) == 2 and (list(cp.forwarded) == [good])")
        findings[0] = self.satisfied(
            items[0],
            "Admission enforces role per lattice and approved registries and signers: a developer cannot "
            "deploy to prod, a manifest from an unapproved registry with an unknown signer is refused "
            "with both reasons, and only the admitted manifest is forwarded.",
            *self._evidence("control_plane.py::ControlPlane.admit"))
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        cp = self._cp()
        m = {"components": [{"name": "a", "image": "registry.estate.local/a:1", "signer": "release-signer"}]}
        cp.admit("ops", "prod", m)
        cp.admit("dev", "prod", m)
        ok = cp.verify_audit()
        tampered = cp.export_audit()
        tampered[1]["entry"]["admitted"] = True          # rewrite exported history
        _verify(ok and not cp.verify_audit(tampered), 'check failed: ok and (not cp.verify_audit(tampered))')
        findings[0] = self.satisfied(
            items[0],
            "Every admission and refusal is appended to a hash-chained audit log; rewriting a refusal "
            "into an admission after the fact breaks the chain and is detected.",
            *self._evidence("control_plane.py::ControlPlane._record", "control_plane.py::ControlPlane.verify_audit"))
        return findings

COMPONENT = EnterpriseWasmControlPlaneComponent
