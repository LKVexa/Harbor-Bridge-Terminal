"""Structured failure codes and outcome semantics for INV-63.

Covers INV-63-C014 (outcome semantics) and INV-63-C026 (structured failure
codes with machine-readable details).  Every error the service surfaces is a
:class:`DeploymentError` whose ``to_dict()`` form validates against the
``PK_DEPLOY_ERROR/1`` schema in :mod:`schemas`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Outcome(str, Enum):
    """INV-63-C014 outcome classes.

    SUCCESS   every requested action committed and the target converged.
    PARTIAL   some actions committed; remaining work is recorded and resumable.
    DEGRADED  request accepted while a non-critical dependency is unavailable;
              results are durable locally and resynchronised later.
    RETRYABLE nothing committed; the same request (same idempotency key) may be
              retried after ``retry_after_s``.
    TERMINAL  nothing committed; retrying the identical request cannot succeed.
    """

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    RETRYABLE = "RETRYABLE"
    TERMINAL = "TERMINAL"


class ErrorCode(str, Enum):
    # code value                        (retryable, outcome)
    INVALID_REQUEST = "INV63-E-INVALID-REQUEST"
    SCHEMA_VIOLATION = "INV63-E-SCHEMA"
    UNSUPPORTED_VERSION = "INV63-E-UNSUPPORTED-VERSION"
    PAYLOAD_TOO_LARGE = "INV63-E-PAYLOAD-TOO-LARGE"
    UNAUTHENTICATED = "INV63-E-UNAUTHENTICATED"
    FORBIDDEN = "INV63-E-FORBIDDEN"
    REPLAY_DETECTED = "INV63-E-REPLAY"
    TENANT_VIOLATION = "INV63-E-TENANT-ISOLATION"
    ARTIFACT_UNTRUSTED = "INV63-E-ARTIFACT-UNTRUSTED"
    INSUFFICIENT_CAPACITY = "INV63-E-INSUFFICIENT-CAPACITY"
    QUOTA_EXCEEDED = "INV63-E-QUOTA"
    OVERLOADED = "INV63-E-OVERLOADED"
    CIRCUIT_OPEN = "INV63-E-CIRCUIT-OPEN"
    DEADLINE_EXCEEDED = "INV63-E-DEADLINE"
    CANCELLED = "INV63-E-CANCELLED"
    DEPENDENCY_UNAVAILABLE = "INV63-E-DEPENDENCY-UNAVAILABLE"
    CONTROL_PLANE_OFFLINE = "INV63-E-CONTROL-PLANE-OFFLINE"
    STALE_EPOCH = "INV63-E-STALE-EPOCH"
    CONFLICT = "INV63-E-CONFLICT"
    ILLEGAL_TRANSITION = "INV63-E-ILLEGAL-TRANSITION"
    QUARANTINED = "INV63-E-QUARANTINED"
    FROZEN = "INV63-E-FROZEN"
    CONFIG_INVALID = "INV63-E-CONFIG-INVALID"
    SECRET_IN_CONFIG = "INV63-E-SECRET-IN-CONFIG"
    STATE_CORRUPT = "INV63-E-STATE-CORRUPT"
    ROLLOUT_FAILED = "INV63-E-ROLLOUT-FAILED"
    PRECONDITION_FAILED = "INV63-E-PRECONDITION"
    POLICY_REJECTED = "INV63-E-POLICY"
    INTERNAL = "INV63-E-INTERNAL"


_RETRYABLE = {
    ErrorCode.OVERLOADED, ErrorCode.CIRCUIT_OPEN, ErrorCode.DEADLINE_EXCEEDED,
    ErrorCode.DEPENDENCY_UNAVAILABLE, ErrorCode.CONTROL_PLANE_OFFLINE,
    ErrorCode.CONFLICT, ErrorCode.INSUFFICIENT_CAPACITY,
}

ERROR_CATALOG: dict[str, dict[str, Any]] = {
    code.value: {
        "retryable": code in _RETRYABLE,
        "outcome": (Outcome.RETRYABLE if code in _RETRYABLE else Outcome.TERMINAL).value,
    }
    for code in ErrorCode
}


@dataclass
class DeploymentError(Exception):
    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retry_after_s: float | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, f"{self.code.value}: {self.message}")

    @property
    def retryable(self) -> bool:
        return self.code in _RETRYABLE

    @property
    def outcome(self) -> Outcome:
        return Outcome.RETRYABLE if self.retryable else Outcome.TERMINAL

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema": "PK_DEPLOY_ERROR/1",
            "code": self.code.value,
            "message": self.message[:512],
            "retryable": self.retryable,
            "outcome": self.outcome.value,
            "details": self.details,
        }
        if self.retry_after_s is not None:
            out["retry_after_s"] = float(self.retry_after_s)
        return out


def classify(exc: BaseException) -> DeploymentError:
    """Map any exception to a structured error (fail closed to INTERNAL)."""
    if isinstance(exc, DeploymentError):
        return exc
    if isinstance(exc, LookupError):
        return DeploymentError(ErrorCode.PRECONDITION_FAILED, str(exc))
    if isinstance(exc, (ValueError, TypeError)):
        return DeploymentError(ErrorCode.INVALID_REQUEST, str(exc))
    if isinstance(exc, TimeoutError):
        return DeploymentError(ErrorCode.DEADLINE_EXCEEDED, str(exc))
    if isinstance(exc, (ConnectionError, OSError)):
        return DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE, str(exc))
    return DeploymentError(ErrorCode.INTERNAL, type(exc).__name__)
