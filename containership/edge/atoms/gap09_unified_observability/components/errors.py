"""Structured error taxonomy shared by the overlay (checks xx.06).

Codes distinguish malformed / unauthenticated / unauthorized / unverifiable /
revoked / expired / dependency-unavailable / internal states.  Messages never
carry secret material: callers pass identifiers only.
"""
from __future__ import annotations

from typing import Any

from ..runtime import SignalError


class Malformed(SignalError, ValueError):
    code = "malformed"


class Unauthenticated(SignalError, PermissionError):
    code = "unauthenticated"


class Unauthorized(SignalError, PermissionError):
    code = "unauthorized"


class Unverifiable(SignalError, PermissionError):
    code = "unverifiable"


class Revoked(SignalError, PermissionError):
    code = "revoked"


class Expired(SignalError, PermissionError):
    code = "expired"


class DependencyUnavailable(SignalError, RuntimeError):
    code = "dependency_unavailable"


class Throttled(SignalError, RuntimeError):
    code = "throttled"

    def __init__(self, message: str, *, retry_after: float, **details: Any) -> None:
        super().__init__(message, retry_after=retry_after, **details)
        self.retry_after = retry_after


class QuotaExceeded(SignalError, RuntimeError):
    code = "quota_exceeded"


class Quarantined(SignalError, PermissionError):
    code = "quarantined"


class Corrupted(SignalError, RuntimeError):
    code = "corrupted"


class ConfigRejected(SignalError, ValueError):
    code = "config_rejected"


class TimeUntrusted(SignalError, RuntimeError):
    code = "time_untrusted"


class InternalError(SignalError, RuntimeError):
    code = "internal_error"


ALL_CODES = tuple(
    c.code
    for c in (
        Malformed, Unauthenticated, Unauthorized, Unverifiable, Revoked, Expired,
        DependencyUnavailable, Throttled, QuotaExceeded, Quarantined, Corrupted,
        ConfigRejected, TimeUntrusted, InternalError,
    )
)
