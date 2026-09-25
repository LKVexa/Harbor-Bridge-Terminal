"""INV-45 - SFI mechanisms.

Software fault isolation is the fallback when hardware will not help: masking
memory accesses into a sandbox region and constraining indirect control-flow.
This component exercises a dependency-free reference model and binds it to the
external ``pk_core`` checklist framework.

The reference model is not a native-code rewriter or loader; production claims
that depend on those facilities require separate evidence.  See SECURITY.md and
MISSING_COMPONENTS.md.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .sfi_core import (
    Access,
    BranchOutsideTargets,
    ModuleNotVerified,
    SandboxRegion,
    SfiModule,
    UnmaskedAccess,
)


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class SfiMechanismsComponent(Component):
    """Master-applied component for INV-45."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        region = SandboxRegion(0x40000000, 0x10000)
        module = SfiModule(
            "svc",
            region,
            tuple(Access(i, True) for i in range(8)),
            frozenset({0, 16, 32}),
            overhead_percent=11.5,
        )
        report = module.verify()
        _verify(report["all_masked"] and report["accesses"] == 8)
        _verify(report["permitted_targets"] == 3)
        _verify(module.branch(16) == 16)
        # Do not overwrite a checklist item with unrelated evidence.  Earlier
        # versions incorrectly wrote this behavior into C036 (config provenance).
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        region = SandboxRegion(0x40000000, 0x10000)
        module = SfiModule("svc", region, (Access(0, True),), frozenset({0}))
        module.verify()

        for address in (0x0, 0xFFFFFFFF, 0x40000000 - 1, 0x7FFFFFFFFFFF, -1):
            result = module.access(address)
            _verify(result["inside_region"], result)

        broken = SfiModule(
            "bad", region, (Access(0, True), Access(4, False)), frozenset({0})
        )
        try:
            broken.verify()
        except UnmaskedAccess:
            pass
        else:
            raise AssertionError("expected UnmaskedAccess was not raised")

        try:
            module.branch(999)
        except BranchOutsideTargets:
            pass
        else:
            raise AssertionError("expected BranchOutsideTargets was not raised")

        # Replacing a security-sensitive policy after verification invalidates
        # the seal; execution cannot inherit a stale verification decision.
        module.indirect_targets = frozenset({0, 999})
        try:
            module.branch(999)
        except ModuleNotVerified:
            pass
        else:
            raise AssertionError("policy mutation did not invalidate verification")

        # C046 is the checklist item these behaviors actually support.  Earlier
        # versions also misfiled unmasked-access rejection under C047 (encryption)
        # and branch confinement under C043 (ambient authority).
        findings[5] = self.satisfied(
            items[5],
            "Reference-model isolation is fail-closed: addresses are confined by masking; "
            "unmasked manifests are rejected; indirect branches are allowlisted; and "
            "post-verification security-state changes invalidate the verification seal.",
            *self._evidence("sfi_core.py::SfiModule"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)

        try:
            SandboxRegion(0x1000, 0x3000)
        except ValueError:
            pass
        else:
            raise AssertionError("expected invalid region size to be refused")

        unverified = SfiModule(
            "svc", SandboxRegion(0x1000, 0x1000), (Access(0, True),), frozenset({0})
        )
        try:
            unverified.access(0x10)
        except ModuleNotVerified:
            pass
        else:
            raise AssertionError("expected unverified module access to fail closed")

        # Behavioral checks above are useful regression tests, but neither is
        # sufficient evidence for C051/C057.  Keep the framework's original
        # findings instead of overwriting those checklist items with unrelated text.
        return findings


COMPONENT = SfiMechanismsComponent

__all__ = [
    "Access",
    "BranchOutsideTargets",
    "ModuleNotVerified",
    "SandboxRegion",
    "SfiModule",
    "UnmaskedAccess",
    "SfiMechanismsComponent",
    "COMPONENT",
]
