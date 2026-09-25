"""Structured failure codes for INV-31 (checklist C026).

Every public failure maps to a stable, machine-readable code.  Error details
never carry scratch contents, secrets, or signing material.
"""
from __future__ import annotations

from typing import Any

from .runtime import (
    ConcurrencyExceeded,
    InstanceDestroyed,
    InstanceExpired,
    PoolCapacityExceeded,
)

ERROR_SCHEMA = "PK_INV31_ERROR/1"


class Inv31Error(RuntimeError):
    """Base class for boundary-level failures that carry a stable code."""

    code = "INV31-E-INTERNAL"
    retryable = False

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details = details


class AuthenticationFailed(Inv31Error):
    code = "INV31-E-AUTHN"


class AuthorizationDenied(Inv31Error):
    code = "INV31-E-AUTHZ"


class ReplayDetected(Inv31Error):
    code = "INV31-E-REPLAY"


class QuotaExceeded(Inv31Error):
    code = "INV31-E-QUOTA"
    retryable = True


class DeadlineExceeded(Inv31Error):
    code = "INV31-E-DEADLINE"


class Cancelled(Inv31Error):
    code = "INV31-E-CANCELLED"


class IdempotencyConflict(Inv31Error):
    code = "INV31-E-IDEMPOTENCY-CONFLICT"


class UnsupportedVersion(Inv31Error):
    code = "INV31-E-UNSUPPORTED-VERSION"


class DependencyUnavailable(Inv31Error):
    code = "INV31-E-DEPENDENCY-UNAVAILABLE"
    retryable = True


class ConfigurationRejected(Inv31Error):
    code = "INV31-E-CONFIG-REJECTED"


class Draining(Inv31Error):
    code = "INV31-E-DRAINING"
    retryable = True


class FrameworkUnavailable(Inv31Error):
    code = "INV31-E-PKCORE-UNAVAILABLE"


# Runtime (pk_core-free) exceptions mapped onto stable codes.
_RUNTIME_CODES: dict[type[BaseException], tuple[str, bool]] = {
    ConcurrencyExceeded: ("INV31-E-CONCURRENCY", True),
    PoolCapacityExceeded: ("INV31-E-POOL-CAPACITY", True),
    InstanceDestroyed: ("INV31-E-INSTANCE-DESTROYED", False),
    InstanceExpired: ("INV31-E-INSTANCE-EXPIRED", False),
    TypeError: ("INV31-E-INVALID-INPUT", False),
    ValueError: ("INV31-E-INVALID-INPUT", False),
}

CODES: tuple[str, ...] = tuple(sorted({
    *(c.code for c in (
        Inv31Error, AuthenticationFailed, AuthorizationDenied, ReplayDetected,
        QuotaExceeded, DeadlineExceeded, Cancelled, IdempotencyConflict,
        UnsupportedVersion, DependencyUnavailable, ConfigurationRejected,
        Draining, FrameworkUnavailable)),
    *(code for code, _ in _RUNTIME_CODES.values()),
}))

_SAFE_DETAIL_KEYS = frozenset({
    "tenant", "version", "limit", "requested", "supported", "dependency",
    "deadline", "now", "field", "idempotency_key", "capability", "quota",
})


def to_error(exc: BaseException) -> dict[str, Any]:
    """Render any exception as a PK_INV31_ERROR/1 record."""
    if isinstance(exc, Inv31Error):
        code, retryable = exc.code, exc.retryable
        details = {k: v for k, v in exc.details.items() if k in _SAFE_DETAIL_KEYS}
    else:
        code, retryable = "INV31-E-INTERNAL", False
        for kind, (mapped, retry) in _RUNTIME_CODES.items():
            if isinstance(exc, kind):
                code, retryable = mapped, retry
                break
        details = {}
    message = str(exc)
    if code == "INV31-E-INTERNAL":
        message = "internal error"  # never leak unexpected exception text
    return {
        "schema": ERROR_SCHEMA,
        "code": code,
        "retryable": retryable,
        "message": message[:512],
        "details": details,
    }
