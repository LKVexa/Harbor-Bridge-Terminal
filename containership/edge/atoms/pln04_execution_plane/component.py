"""PLN-04 - Execution plane certification adapter.

The dependency-free execution state machine lives in :mod:`.runtime`.  This
module maps exercised behaviour onto the external ``pk_core`` checklist without
claiming unrelated checklist items as evidence.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .runtime import (
    AdmissionConflict,
    AuditEvent,
    CapacityExceeded,
    ExecutionPlaneError,
    InstanceRecord,
    NoSufficientTier,
    Node,
    ResidentTierUnattested,
    TIERS,
    TRUST_CLASSES,
    admit,
    teardown,
)


def _verify(condition: object, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ExecutionPlaneComponent(Component):
    """Master-applied certification component for PLN-04."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)

        # C044 -- authenticate/attest nodes before trust is granted.  Do not
        # silently certify this when the hardware-rooted sibling is absent.
        gap06 = sibling("GAP-06")
        if gap06 is None:
            findings[3] = self.partial(
                items[3],
                "The local tier catalogue is fail-closed, but this package does not contain a hardware-rooted node attestor.",
                note="GAP-06 Device identity and attestation is not installed here",
            )
        else:
            try:
                attestor = gap06.Attestor("prod", accepted={"m-fw-1"})
                evidence = gap06.Evidence(
                    "n1", ("m-fw-1",), attestor.challenge("n1", 0), hardware_rooted=True
                )
                attestor.attest(evidence, now=0)
                _verify(
                    attestor.level_of("n1", 0) == "hardware",
                    "hardware attestation did not reach hardware trust",
                )
                drifted = gap06.Evidence(
                    "n1", ("m-fw-1", "m-rootkit"), "nonce-2", hardware_rooted=True
                )
                try:
                    attestor.attest(drifted, now=1)
                except gap06.AttestationFailed:
                    pass
                else:
                    raise AssertionError("drifted measurements were not rejected")
                _verify(
                    attestor.level_of("n1", 1) == "untrusted",
                    "failed attestation did not drop node trust",
                )
            except (AttributeError, TypeError) as exc:
                findings[3] = self.partial(
                    items[3],
                    "GAP-06 is installed but its exported attestation API is incompatible with this adapter.",
                    note=f"integration mismatch: {exc}",
                )
            else:
                findings[3] = self.satisfied(
                    items[3],
                    "Hardware-rooted node attestation is exercised through GAP-06 and drifted measurements are rejected.",
                    *self._evidence("component.py::assess_security"),
                    "GAP-06/Attestor",
                )

        # C046 -- tenant/workload isolation.
        node = Node({"process": True, "wasm": True})
        _verify(admit(node, "owned", "tenant-a", "trusted") == "process")
        try:
            admit(node, "owned", "tenant-b", "trusted")
        except PermissionError:
            pass
        else:
            raise AssertionError("cross-tenant workload takeover was accepted")
        try:
            admit(node, "hostile", "tenant-a", "hostile")
        except NoSufficientTier:
            pass
        else:
            raise AssertionError("hostile workload was downgraded below its required tier")
        findings[5] = self.satisfied(
            items[5],
            "Cross-tenant workload takeover is refused and hostile workloads are never downgraded below their required tier.",
            *self._evidence("runtime.py::admit"),
        )

        # C048 -- fail-safe behavior when attestation is unavailable.
        node = Node({"process": True, "microvm": True})
        admit(node, "resident", "tenant-a", "untrusted")
        affected = node.fail_attestation("microvm")
        _verify(affected == ("resident",), "resident workload was not quarantined")
        _verify(node.instance("resident").state == "quarantined")
        try:
            admit(node, "next", "tenant-a", "untrusted")
        except NoSufficientTier:
            pass
        else:
            raise AssertionError("new admission used an unattested tier")
        findings[7] = self.satisfied(
            items[7],
            "Attestation loss fails closed: residents are quarantined and new admissions cannot use the failed tier.",
            *self._evidence("runtime.py::Node.fail_attestation"),
        )

        # C049 -- tamper-evident audit events.
        _verify(node.verify_audit_chain(), "audit chain verification failed")
        _verify(len(node.audit_events()) >= 2, "security-sensitive operations were not audited")
        findings[8] = self.satisfied(
            items[8],
            "Admission, refusal, attestation and teardown operations emit SHA-256 hash-chained audit events.",
            *self._evidence("runtime.py::AuditEvent"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)

        # C054 -- admission control/load shedding.
        limited = Node({"process": True}, max_instances=1, per_tenant_limit=1)
        admit(limited, "w1", "t1", "trusted")
        try:
            admit(limited, "w2", "t1", "trusted")
        except CapacityExceeded:
            pass
        else:
            raise AssertionError("capacity ceiling did not reject excess admission")
        findings[3] = self.satisfied(
            items[3],
            "Bounded node and per-tenant ceilings reject excess admissions before resident state grows without limit.",
            *self._evidence("runtime.py::admit"),
        )

        # C056 -- degraded operation when a preferred tier is unavailable.
        node = Node({"process": True, "microvm": True})
        _verify(
            admit(node, "w-degraded", "t1", "third-party") == "microvm",
            "admission did not escalate to the next sufficient attested tier",
        )
        findings[5] = self.satisfied(
            items[5],
            "When a preferred floor tier is absent, admission can degrade upward to the next stronger attested tier without weakening isolation.",
            *self._evidence("runtime.py::admit"),
        )

        # C059 -- quarantine/freeze controls for unsafe execution.
        node.fail_attestation("microvm")
        _verify(node.instance("w-degraded").state == "quarantined")
        findings[8] = self.satisfied(
            items[8],
            "Tier attestation failure quarantines resident workloads and requires teardown/recreation before execution can resume.",
            *self._evidence("runtime.py::Node.fail_attestation"),
        )
        return findings


COMPONENT = ExecutionPlaneComponent

__all__ = [
    "AdmissionConflict",
    "AuditEvent",
    "CapacityExceeded",
    "COMPONENT",
    "ExecutionPlaneComponent",
    "ExecutionPlaneError",
    "InstanceRecord",
    "NoSufficientTier",
    "Node",
    "ResidentTierUnattested",
    "TIERS",
    "TRUST_CLASSES",
    "admit",
    "teardown",
]
