"""GAP-06 - Device identity and attestation.

The security primitives are importable without ``pk_core``. Framework-bound
symbols are loaded lazily so the core trust logic remains independently
unit-testable.
"""
from __future__ import annotations

from .attestation import (
    CHALLENGE_TTL,
    LEVELS,
    VERDICT_TTL,
    AttestationFailed,
    Attestor,
    Challenge,
    ChallengeCapacityExceeded,
    ChallengeExpired,
    ClockRollback,
    Evidence,
    IdentityBindingFailed,
    InvalidEvidence,
    ReplayDetected,
    UnknownNode,
    UnissuedChallenge,
    Verdict,
)

__version__ = "5.0.0"

__all__ = [
    "__version__",
    "LEVELS",
    "VERDICT_TTL",
    "CHALLENGE_TTL",
    "Attestor",
    "Challenge",
    "Evidence",
    "Verdict",
    "AttestationFailed",
    "ReplayDetected",
    "UnissuedChallenge",
    "ChallengeExpired",
    "UnknownNode",
    "IdentityBindingFailed",
    "InvalidEvidence",
    "ClockRollback",
    "ChallengeCapacityExceeded",
    "COMPONENT",
    "DeviceIdentityAndAttestationComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]


def __getattr__(name: str):
    if name in {"COMPONENT", "DeviceIdentityAndAttestationComponent"}:
        from .component import COMPONENT, DeviceIdentityAndAttestationComponent
        return {"COMPONENT": COMPONENT, "DeviceIdentityAndAttestationComponent": DeviceIdentityAndAttestationComponent}[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    raise AttributeError(name)
