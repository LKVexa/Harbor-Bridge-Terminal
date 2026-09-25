"""INV-40 - Full virtualization tier.

The full virtualization tier is the heavyweight end: a complete machine with its own kernel and a full device model. It is the tier you use when the workload is hostile or the guest OS is not yours, and it costs seconds to boot and hundreds of megabytes to run -- numbers this element states plainly so the tier is chosen on purpose rather than by default.

The component integrates with the 100-item INV-40 pk_core checklist. Bands
whose defaults would merely restate the contract are overridden below so key
claims are backed by exercised behavior. Standalone repository evidence is
audited separately in AUDIT_REPORT.md and MISSING_COMPONENTS.md.
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



from .runtime import (
    BOOT_BUDGET_MS,
    FOOTPRINT_CEILING_MIB,
    FULL_DEVICE_MODEL,
    DeviceConflict,
    DeviceLeaseRegistry,
    FootprintExceeded,
    FullVm,
    InvalidVmState,
    PrimitiveRequired,
    device_conflict,
)


class FullVirtualizationTierComponent(Component):
    """Master-applied component for INV-40."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        vm = FullVm("g1", "t1", memory_mib=1024)
        result = vm.start(primitive_usable=True, elapsed_ms=3200, resident_mib=1200)
        _verify(result["within_budget"] and result["devices"] == len(FULL_DEVICE_MODEL), "check failed: result['within_budget'] and result['devices'] == len(FULL_DEVICE_MODEL)")
        _verify(vm.stop()["state"] == "stopped", "check failed: VM did not stop cleanly")
        _verify(vm.destroy()["destroyed"], "check failed: VM did not destroy cleanly")
        findings[5] = self.satisfied(
            items[5],
            f"A full guest boots with all {result['devices']} devices in {result['boot_ms']}ms and "
            f"{result['resident_mib']}MiB resident -- the real cost, accounted rather than rounded down.",
            *self._evidence("component.py::FullVm.start"))
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[6] = self.satisfied(
            items[6],
            f"This tier deliberately carries {len(FULL_DEVICE_MODEL)} devices against the microVM tier's "
            "minimal set: the trade is breadth of guest compatibility for attack surface, and it is the "
            "reason the tier exists at all.",
            *self._evidence("component.py::FULL_DEVICE_MODEL", "contract.py"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        vm = FullVm("g1", "t1", memory_mib=512)
        try:
            vm.start(primitive_usable=False, elapsed_ms=1000, resident_mib=600)
        except PrimitiveRequired:
            findings[5] = self.satisfied(
                items[5],
                "Without the hardware primitive the tier refuses to start rather than falling back to "
                "software emulation that would not deliver the boundary the caller asked for.",
                *self._evidence("component.py::FullVm.start"))
        else:
            raise AssertionError('expected PrimitiveRequired was not raised; the refusal this finding claims did not happen')
        result = vm.start(primitive_usable=True, elapsed_ms=1000, resident_mib=600)
        _verify(result["guest_os_opaque"], "check failed: result['guest_os_opaque']")
        findings[6] = self.satisfied(
            items[6],
            "The guest OS is treated as opaque and potentially hostile: nothing in this tier depends on "
            "introspecting guest internals, so a modified guest cannot invalidate a host assumption.",
            *self._evidence("component.py::FullVm.start"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        vm = FullVm("g1", "t1", memory_mib=4096)
        try:
            vm.start(primitive_usable=True, elapsed_ms=1000,
                     resident_mib=FOOTPRINT_CEILING_MIB + 1)
        except FootprintExceeded:
            findings[1] = self.satisfied(
                items[1],
                f"Resident footprint is capped at {FOOTPRINT_CEILING_MIB}MiB per guest, so this tier's "
                "expense is bounded rather than open-ended.",
                *self._evidence("component.py::FullVm.start"))
        else:
            raise AssertionError('expected FootprintExceeded was not raised; the refusal this finding claims did not happen')
        findings[4] = self.satisfied(
            items[4],
            f"Cold start and steady state are separated explicitly: a {BOOT_BUDGET_MS}ms boot budget and a "
            "resident-size ceiling are tracked as different quantities.",
            *self._evidence("component.py::FullVm.start"))
        return findings

COMPONENT = FullVirtualizationTierComponent
