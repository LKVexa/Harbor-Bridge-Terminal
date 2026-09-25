"""INV-23 - Hardware virtualization primitive.

The hardware virtualization primitive is the floor everything above it stands on: the CPU's own trap-and-emulate machinery. It is either present and usable or it is not, and no amount of software above it can manufacture it, so this element reports it honestly and refuses to pretend nested virtualization is the same thing as bare metal.

The component answers all 100 requirements of the INV-23 checklist.  Bands
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


from .model import ABSENT, CLAIMED, PRESENT_DISABLED, USABLE, PrimitiveUnavailable, VirtPrimitive  # noqa: F401


class HardwareVirtualizationPrimitiveComponent(Component):
    """Master-applied component for INV-23."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        bare = VirtPrimitive("n1", cpuid_present=True, firmware_enabled=True, device_openable=True)
        _verify(
            bare.state() == USABLE and bare.report()["bare_metal"], "check failed: bare.state() == USABLE and bare.report()['bare_metal']"
        )
        disabled = VirtPrimitive("n2", cpuid_present=True, firmware_enabled=False)
        _verify(disabled.state() == PRESENT_DISABLED, "check failed: disabled.state() == PRESENT_DISABLED")
        _verify(VirtPrimitive("n3").state() == ABSENT, "check failed: VirtPrimitive('n3').state() == ABSENT")
        findings[5] = self.satisfied(
            items[5],
            "Detection is three-valued: usable, present-but-disabled and absent are distinct states, and "
            "only a device that actually opens reports usable.",
            *self._evidence("component.py::VirtPrimitive.state"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        p = VirtPrimitive("n1", cpuid_present=True, firmware_enabled=True, device_openable=True)
        p.claim("vmm-a")
        try:
            p.claim("vmm-b")
        except PrimitiveUnavailable:
            findings[5] = self.satisfied(
                items[5],
                "The virtualization device is exclusive: a second hypervisor cannot claim it, so two VMMs "
                "cannot believe they own the same CPU.",
                *self._evidence("component.py::VirtPrimitive.claim"),
            )
        else:
            raise AssertionError("expected PrimitiveUnavailable was not raised; the refusal this finding claims did not happen")
        nested = VirtPrimitive("n2", cpuid_present=True, firmware_enabled=True, device_openable=True, nesting_depth=2)
        _verify(not nested.report()["bare_metal"], "check failed: not nested.report()['bare_metal']")
        try:
            nested.claim("vmm", max_nesting=1)
        except PrimitiveUnavailable:
            findings[0] = self.satisfied(
                items[0],
                "A host already nested two levels deep cannot claim the primitive under a depth-1 policy, "
                "so a guest cannot present nested execution as bare-metal isolation.",
                *self._evidence("component.py::VirtPrimitive.claim"),
            )
        else:
            raise AssertionError("expected PrimitiveUnavailable was not raised; the refusal this finding claims did not happen")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        p = VirtPrimitive("n1", cpuid_present=True, firmware_enabled=True, device_openable=True)
        p.claim("vmm")
        p.firmware_enabled = False  # firmware downgrade between probes
        _verify(p.state() == PRESENT_DISABLED, "check failed: p.state() == PRESENT_DISABLED")
        findings[3] = self.satisfied(
            items[3],
            "A firmware downgrade flips the primitive back to present-disabled on the next probe rather "
            "than leaving a stale usable verdict behind.",
            *self._evidence("component.py::VirtPrimitive.state"),
        )
        return findings


COMPONENT = HardwareVirtualizationPrimitiveComponent
