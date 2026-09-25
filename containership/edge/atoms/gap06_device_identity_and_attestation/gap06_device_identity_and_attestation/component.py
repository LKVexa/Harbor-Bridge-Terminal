"""GAP-06 - Device identity and attestation framework integration."""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .attestation import (
    AttestationFailed,
    Attestor,
    Evidence,
    ReplayDetected,
    UnissuedChallenge,
    VERDICT_TTL,
)
from .contract import ELEMENT_ID, ELEMENT_NAME, build


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class DeviceIdentityAndAttestationComponent(Component):
    """Master-applied component for GAP-06."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        a = Attestor("prod", accepted={"m-fw-1", "m-kernel-1"}, measurement_set_version="prod-2026-09")
        a.enrol("n1", hardware_identity="root:n1")
        a.enrol("n2")
        ev = Evidence(
            "n1",
            ("m-fw-1", "m-kernel-1"),
            a.challenge("n1", 0),
            hardware_rooted=True,
            hardware_identity="root:n1",
        )
        verdict = a.attest(ev, now=0)
        _verify(
            verdict.level == "hardware" and a.level_of("n1", 0) == "hardware",
            "hardware-rooted enrolled node did not receive hardware trust",
        )
        soft = Evidence("n2", ("m-fw-1",), a.challenge("n2", 0), hardware_rooted=False)
        _verify(a.attest(soft, now=0).level == "software", "software-rooted node exceeded software trust")
        findings[5] = self.satisfied(
            items[5],
            "Attestation level follows enrolled identity state and evidence: a software-rooted node reaches "
            "software at best, while hardware trust additionally requires a matching enrolled hardware identity.",
            *self._evidence("attestation.py::Attestor.attest"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        a = Attestor("prod", accepted={"m-fw-1"}, measurement_set_version="prod-2026-09")
        a.enrol("n1", hardware_identity="root:n1")
        a.enrol("n2", hardware_identity="root:n2")
        ev = Evidence(
            "n1", ("m-fw-1",), a.challenge("n1", 0), hardware_rooted=True, hardware_identity="root:n1"
        )
        a.attest(ev, now=0)
        try:
            a.attest(ev, now=1)
        except ReplayDetected:
            findings[3] = self.satisfied(
                items[3],
                "Evidence reusing a spent nonce is refused, so a recorded healthy boot cannot be replayed.",
                *self._evidence("attestation.py::Attestor.attest"),
            )
        else:
            raise AssertionError("expected ReplayDetected was not raised")

        live = a.challenge("n1", 1)
        try:
            a.attest(
                Evidence("n2", ("m-fw-1",), live, hardware_rooted=True, hardware_identity="root:n2"),
                now=1,
            )
        except UnissuedChallenge:
            pass
        else:
            raise AssertionError("another node was able to answer n1's challenge")
        # Wrong-node presentation must not burn the legitimate node's challenge.
        a.attest(
            Evidence("n1", ("m-fw-1",), live, hardware_rooted=True, hardware_identity="root:n1"),
            now=1,
        )

        try:
            a.attest(Evidence("n1", ("m-fw-1",), "self-chosen", hardware_rooted=False), now=1)
        except UnissuedChallenge:
            pass
        else:
            raise AssertionError("evidence answering a never-issued nonce was accepted")
        _verify(a.level_of("n1", 1) == "hardware", "unissued evidence mutated an existing trust verdict")

        drift_nonce = a.challenge("n1", 2)
        drifted = Evidence("n1", ("m-fw-1", "m-rootkit"), drift_nonce, hardware_rooted=True, hardware_identity="root:n1")
        try:
            a.attest(drifted, now=2)
        except AttestationFailed:
            findings[4] = self.satisfied(
                items[4],
                "Measurements outside the accepted set quarantine the node immediately, even though its "
                "previous verdict had not expired.",
                *self._evidence("attestation.py::Attestor.attest"),
            )
        else:
            raise AssertionError("expected AttestationFailed was not raised")
        _verify(a.level_of("n1", 2) == "untrusted", "quarantine did not override the live verdict")
        _verify(a.level_of("never-seen", 2) == "untrusted", "unknown node did not evaluate as untrusted")
        findings[1] = self.satisfied(
            items[1],
            "A node with no verdict, and a quarantined node with a live one, both evaluate to untrusted: "
            "absence of evidence is never treated as trust.",
            *self._evidence("attestation.py::Attestor.level_of"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        a = Attestor("prod", accepted={"m-fw-1"}, measurement_set_version="prod-2026-09")
        a.enrol("n1", hardware_identity="root:n1")
        a.attest(
            Evidence(
                "n1", ("m-fw-1",), a.challenge("n1", 0), hardware_rooted=True, hardware_identity="root:n1"
            ),
            now=0,
        )
        _verify(a.level_of("n1", VERDICT_TTL - 1) == "hardware", "verdict expired early")
        _verify(a.level_of("n1", VERDICT_TTL) == "untrusted", "verdict outlived its expiry")
        findings[3] = self.satisfied(
            items[3],
            f"A verdict decays to untrusted exactly at its {VERDICT_TTL}-tick expiry, so a partitioned "
            "site loses trust rather than retaining it indefinitely.",
            *self._evidence("attestation.py::Verdict.level_at"),
        )
        return findings


COMPONENT = DeviceIdentityAndAttestationComponent
