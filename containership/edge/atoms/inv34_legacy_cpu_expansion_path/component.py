"""pk_core adapter for INV-34 - Legacy CPU expansion path."""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .expansion import (
    CpuExpansionController,
    ExpansionDisabled,
    HostCapacityExceeded,
    HotplugUnsupported,
    ShrinkNotSupported,
    StaleGeneration,
    VmCpuState,
)


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class LegacyCpuExpansionPathComponent(Component):
    """Master-applied component for conventional VM CPU expansion."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        contract = build()
        _verify(any("ACPI" in value for value in contract.interfaces.values()))
        findings[9] = self.satisfied(
            items[9],
            "The architecture decision is explicit: INV-34 is the conventional-VM CPU scaling path, "
            "using ACPI CPU hot-plug as the guest-visible mechanism; hypervisor-specific execution is an adapter boundary.",
            *self._evidence("contract.py", "expansion.py::VmCpuState"),
        )
        return findings

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        state = VmCpuState("vm-1", 2, 2, 8, 8)
        controller = CpuExpansionController(state)
        accepted = controller.request_expansion("req-1", 4, expected_generation=0)
        _verify(accepted.status == "accepted" and accepted.added_vcpus == 2)
        _verify(controller.snapshot().observed_vcpus == 2)
        _verify(controller.snapshot().desired_vcpus == 4)
        progressed = controller.record_observation(3)
        _verify(progressed.pending_vcpus == 1 and not progressed.converged)
        complete = controller.record_observation(4)
        _verify(complete.converged)
        findings[3] = self.satisfied(
            items[3],
            "Configuration and requests are validated before activation: malformed identifiers, invalid counts, stale generations, "
            "unsupported hot-plug, shrink requests, and capacity overrun fail closed.",
            *self._evidence("expansion.py::VmCpuState", "expansion.py::CpuExpansionController.request_expansion"),
        )
        findings[5] = self.satisfied(
            items[5],
            "Accepted desired CPU count and independently observed online CPU count are tracked separately, preventing an accepted "
            "control-plane request from being misreported as guest completion.",
            *self._evidence("expansion.py::VmCpuState", "expansion.py::CpuExpansionController.record_observation"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        disabled = CpuExpansionController(VmCpuState("vm-2", 2, 2, 8, 8, expansion_enabled=False))
        try:
            disabled.request_expansion("req-disabled", 4)
        except ExpansionDisabled:
            findings[1] = self.satisfied(
                items[1],
                "The reference controller includes an explicit administrative expansion kill switch and fails closed when it is disabled.",
                *self._evidence("expansion.py::ExpansionDisabled", "expansion.py::CpuExpansionController.request_expansion"),
            )
        else:
            raise AssertionError("disabled expansion unexpectedly succeeded")

        unsupported = CpuExpansionController(
            VmCpuState("vm-3", 2, 2, 8, 8, acpi_hotplug_supported=False)
        )
        try:
            unsupported.request_expansion("req-no-acpi", 4)
        except HotplugUnsupported:
            findings[5] = self.satisfied(
                items[5],
                "A VM cannot enter the expansion path unless both hypervisor ACPI hot-plug and guest CPU hot-plug support are declared.",
                *self._evidence("expansion.py::HotplugUnsupported"),
            )
        else:
            raise AssertionError("unsupported hot-plug unexpectedly succeeded")
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        controller = CpuExpansionController(VmCpuState("vm-4", 2, 2, 4, 3))
        try:
            controller.request_expansion("req-capacity", 4)
        except HostCapacityExceeded as exc:
            _verify(exc.retryable)
            findings[3] = self.satisfied(
                items[3],
                "Host-capacity exhaustion is rejected before state mutation and is machine-classified as retryable, preventing an unsafe "
                "partial desired-state update.",
                *self._evidence("expansion.py::HostCapacityExceeded"),
            )
        else:
            raise AssertionError("capacity overrun unexpectedly succeeded")

        try:
            CpuExpansionController(VmCpuState("vm-5", 2, 2, 8, 8)).request_expansion(
                "req-stale", 4, expected_generation=9
            )
        except StaleGeneration:
            findings[7] = self.satisfied(
                items[7],
                "Generation checks reject stale controllers before they can overwrite a newer desired state.",
                *self._evidence("expansion.py::StaleGeneration"),
            )
        else:
            raise AssertionError("stale generation unexpectedly succeeded")

        try:
            CpuExpansionController(VmCpuState("vm-6", 4, 4, 8, 8)).request_expansion("req-shrink", 2)
        except ShrinkNotSupported:
            findings[8] = self.satisfied(
                items[8],
                "The legacy path is monotonic: CPU hot-unplug is refused instead of silently entering a less portable failure mode.",
                *self._evidence("expansion.py::ShrinkNotSupported"),
            )
        else:
            raise AssertionError("hot-unplug unexpectedly succeeded")
        return findings


COMPONENT = LegacyCpuExpansionPathComponent
