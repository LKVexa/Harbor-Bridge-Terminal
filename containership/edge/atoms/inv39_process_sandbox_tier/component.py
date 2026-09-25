"""INV-39 - Process sandbox tier master-applied component."""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .sandbox import (
    REQUIRED_NAMESPACES,
    ProfileInvalid,
    ProfileNotApplied,
    Sandbox,
    SandboxProfile,
)


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ProcessSandboxTierComponent(Component):
    """Master-applied component for INV-39."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        profile = SandboxProfile("svc", frozenset({"read", "write", "exit_group"}))
        box = Sandbox("p1", profile)
        applied = box.start(readback=box.requested_state())
        _verify(
            applied["residual_syscalls"] == 3 and applied["within_budget"],
            "applied syscall count or budget result is incorrect",
        )
        _verify(
            box.call("read") and not box.call("ptrace"),
            "default-deny behaviour is incorrect",
        )
        _verify(box.denials == ["ptrace"], "denial audit trail is incorrect")
        findings[5] = self.satisfied(
            items[5],
            f"The verified model is default-deny: {applied['residual_syscalls']} syscalls are allowed, "
            "and an unlisted call is refused and recorded. Production kernel enforcement remains a "
            "separate backend responsibility.",
            *self._evidence("sandbox.py::Sandbox"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        proven = []
        try:
            profile = SandboxProfile(
                "bad", frozenset({"read"}), capabilities=frozenset({"cap_sys_admin"})
            )
            Sandbox("p1", profile).start(readback=Sandbox("tmp", profile).requested_state())
        except ProfileInvalid:
            proven.append("forbidden capability")
        try:
            profile = SandboxProfile(
                "bad2", frozenset({"read"}), namespaces=frozenset({"pid", "mount"})
            )
            Sandbox("p2", profile).start(readback=Sandbox("tmp2", profile).requested_state())
        except ProfileInvalid:
            proven.append("omitted namespace")
        _verify(len(proven) == 2, "both unsafe profile classes must be refused")
        findings[2] = self.satisfied(
            items[2],
            f"Profile validation refuses both {' and '.join(proven)} before verified start.",
            *self._evidence("sandbox.py::SandboxProfile.validate"),
        )

        profile = SandboxProfile("svc", frozenset({"read"}))
        try:
            Sandbox("p3", profile).start(
                readback={
                    "syscalls": {"read", "ptrace"},
                    "capabilities": set(),
                    "namespaces": REQUIRED_NAMESPACES,
                }
            )
        except ProfileNotApplied:
            findings[7] = self.satisfied(
                items[7],
                "Applied state is verified by explicit external read-back; missing or mismatched read-back "
                "fails closed instead of being replaced by requested state.",
                *self._evidence("sandbox.py::Sandbox.start"),
            )
        else:
            raise AssertionError("expected ProfileNotApplied was not raised")

        findings[9] = self.satisfied(
            items[9],
            "The applied record states that this tier shares the host kernel and that an allowed-syscall "
            "kernel bug can defeat the tier.",
            *self._evidence("sandbox.py::Sandbox.start"),
        )
        return findings

    def assess_architecture(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_architecture(items)
        findings[7] = self.satisfied(
            items[7],
            "Running untrusted or hostile code is an explicit non-goal of this tier; PLN-04 admits those "
            "classes to microVM or full virtualization instead.",
            *self._evidence("contract.py"),
        )
        return findings


COMPONENT = ProcessSandboxTierComponent
