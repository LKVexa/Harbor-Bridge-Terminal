"""INV-36 - Control transport component adapter.

Security-critical frame behavior lives in :mod:`.transport` so it is testable
without the external ``pk_core`` gate framework.  This module supplies the
estate-specific component adapter and a small set of executable evidence hooks.
"""
from __future__ import annotations

import hashlib

from .pkcore_adapter import require

ChecklistItem, Finding = require("checklist", "ChecklistItem", "Finding")
(Component,) = require("component", "Component")

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .transport import (
    AuthFailure,
    FrameTooLarge,
    OutOfOrder,
    Relay,
    Replay,
    Session,
    new_session_id,
)


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioral check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class ControlTransportComponent(Component):
    """pk_core adapter for INV-36."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _pair(self):
        # Synthetic evidence key only; production callers obtain this from an
        # authenticated establishment/attestation mechanism.
        shared = hashlib.sha256(b"INV-36 synthetic conformance shared secret").digest()
        session_id = new_session_id()
        return (
            Session("node-a", "node-b", shared, session_id=session_id),
            Session("node-b", "node-a", shared, session_id=session_id),
        )

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        a, b = self._pair()
        relay = Relay()
        msg = b"REVOKE lease-42"
        wire = relay.forward(a.seal(msg))
        _verify(b.open(wire) == msg, "round trip failed")
        _verify(all(msg not in frame for frame in relay.seen), "relay observed plaintext")

        tampered = bytearray(a.seal(b"GRANT lease-43"))
        tampered[-1] ^= 0x01
        refused = False
        try:
            b.open(tampered)
        except AuthFailure:
            refused = True
        _verify(refused and b.auth_failures == 1, "tamper was not refused")

        # Do not rewrite a checklist status here: these checks cover only a subset
        # of the broader security requirement.  Repository-level completeness is
        # reported by AUDIT_REPORT.md rather than inflated by executable smoke tests.
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        a, b = self._pair()
        first = a.seal(b"LEASE v1")
        second = a.seal(b"LEASE v2")

        out_of_order = False
        try:
            b.open(second)
        except OutOfOrder:
            out_of_order = True
        _verify(out_of_order and b.recv_seq == 0, "out-of-order frame advanced receive state")
        _verify(b.open(first) == b"LEASE v1", "first frame failed after reordering refusal")
        _verify(b.open(second) == b"LEASE v2", "second frame failed after sequence recovered")

        replayed = False
        try:
            b.open(first)
        except Replay:
            replayed = True

        oversized = False
        try:
            a.seal(b"x" * (64 * 1024 + 1))
        except FrameTooLarge:
            oversized = True
        _verify(replayed and oversized, "replay or size bound was not enforced")

        # As above, protocol-level fault checks are not equivalent to complete
        # process/node/site recovery certification.
        return findings


COMPONENT = ControlTransportComponent
