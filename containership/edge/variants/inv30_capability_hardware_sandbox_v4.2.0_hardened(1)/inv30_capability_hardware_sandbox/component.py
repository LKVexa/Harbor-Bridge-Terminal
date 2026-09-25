"""INV-30 - Capability hardware sandbox.

The capability hardware sandbox is CHERI-shaped: pointers carry bounds and permissions the hardware itself checks, so a bug cannot be turned into an arbitrary write. It is the one tier where memory safety is enforced below the software stack -- and it exists on very little hardware, which this element states rather than glosses over.

The component answers all 100 requirements of the INV-30 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



from .core import (
    Amplification,
    BoundsViolation,
    Capability,
    Invalidated,
    PermissionViolation,
)


class CapabilityHardwareSandboxComponent(Component):
    """Master-applied component for INV-30."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        root = Capability(0x1000, 0x1000, frozenset({"read", "write"}))
        child = root.derive(base=0x1400, length=0x200, permissions={"read"})
        _verify(child.base == 0x1400 and child.permissions == frozenset({"read"}), "check failed: child.base == 5120 and child.permissions == frozenset({'read'})")
        _verify(child.check(address=0x1400, size=16, operation="read")["permitted"], "check failed: child.check(address=5120, size=16, operation='read')['permitted']")
        findings[5] = self.satisfied(
            items[5],
            f"Derivation narrows in both dimensions at once: [{hex(root.base)}, {hex(root.limit)}) with "
            f"read+write became [{hex(child.base)}, {hex(child.limit)}) with read only.",
            *self._evidence("component.py::Capability.derive"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        root = Capability(0x1000, 0x1000, frozenset({"read"}))
        proven = []
        try:
            root.derive(base=0x800, length=0x100)
        except Amplification:
            proven.append("bounds widening")
        try:
            root.derive(base=0x1000, length=0x10, permissions={"read", "write"})
        except Amplification:
            proven.append("permission amplification")
        try:
            root.check(address=0x2000, size=8, operation="read")
        except BoundsViolation:
            proven.append("out-of-bounds access")
        try:
            root.check(address=0x1000, size=8, operation="write")
        except PermissionViolation:
            proven.append("missing permission")
        _verify(len(proven) == 4, proven)
        findings[1] = self.satisfied(
            items[1],
            f"All four amplification paths are refused: {', '.join(proven)}. Authority is monotonically "
            "decreasing by construction, which is the whole point of the tier.",
            *self._evidence("component.py::Capability"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        cap = Capability(0x1000, 0x100, frozenset({"read"}))
        cap.invalidate()
        proven = []
        try:
            cap.check(address=0x1000, size=8, operation="read")
        except Invalidated:
            proven.append("access")
        try:
            cap.derive(base=0x1000, length=0x10)
        except Invalidated:
            proven.append("derivation")
        try:
            cap.valid = True
        except Invalidated:
            proven.append("resurrection")
        _verify(len(proven) == 3 and not cap.valid, 'check failed: len(proven) == 3')
        findings[6] = self.satisfied(
            items[6],
            "Invalidation is permanent and closes both access and derivation, so a freed capability cannot "
            "be resurrected into a use-after-free.",
            *self._evidence("component.py::Capability.invalidate"))
        gap02 = sibling("GAP-02")
        if gap02 is None:
            findings[0] = self.partial(
                items[0],
                "This element models the capability semantics but cannot tell whether the node has the "
                "hardware.",
                note="GAP-02 Hardware capability discovery is not installed here")
        else:
            report = gap02.CapabilityReport("n1")
            def no_cheri():
                raise gap02.ProbeUnavailable("no capability hardware on this node")
            _verify(gap02.probe(report, "cheri", no_cheri, 0) == gap02.UNPROBED, "check failed: gap02.probe(report, 'cheri', no_cheri, 0) == gap02.UNPROBED")
            view = report.for_consumer(now=1)
            _verify("cheri" not in view["present"] and "cheri" in view["unprobed"], "check failed: 'cheri' not in view['present'] and 'cheri' in view['unprobed']")
            gap02.probe(report, "cheri", lambda: True, 2)
            _verify("cheri" in report.for_consumer(now=3)["present"], "check failed: 'cheri' in report.for_consumer(now=3)['present']")
            findings[0] = self.satisfied(
                items[0],
                "Tier availability is decided by a real GAP-02 probe rather than assumed: an unprobeable "
                "node publishes capability hardware as unprobed and the tier is invisible to placement, "
                "while a node that probes positive makes it available.",
                *self._evidence("contract.py"), "GAP-02/CapabilityReport")
        return findings

COMPONENT = CapabilityHardwareSandboxComponent
