"""Stable, machine-readable error taxonomy for INV-55 (checklist #6, #21).

Every public failure maps to exactly one ``ErrorCode``.  The wire form produced by
``to_wire`` validates against ``schemas/error.schema.json``.  Error payloads never
carry secret values; ``detail`` strings are passed through ``redact_text`` before
leaving the process.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class Outcome(str, Enum):
    """Outcome/failure semantic model (docs/architecture/outcome-semantics.md)."""

    SUCCESS = "success"
    DEGRADED = "degraded"          # served from a still-valid cache while provider unavailable
    RETRYABLE = "retryable"        # caller may retry after retry_after_ms
    TERMINAL = "terminal"          # retrying the same request cannot succeed
    DENIED = "denied"              # security decision; never retry automatically


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    outcome: Outcome
    http_status: int
    retry_after_ms: int | None
    message: str


class ErrorCode(Enum):
    DENIED = ErrorSpec("INV55-E001-DENIED", Outcome.DENIED, 403, None,
                       "secret is unavailable or application is not authorized")
    UNAUTHENTICATED = ErrorSpec("INV55-E002-UNAUTHENTICATED", Outcome.DENIED, 401, None,
                                "caller identity could not be established")
    LEASE_EXPIRED = ErrorSpec("INV55-E003-LEASE-EXPIRED", Outcome.TERMINAL, 410, None,
                              "lease ended; resolve again")
    LEASE_REVOKED = ErrorSpec("INV55-E004-LEASE-REVOKED", Outcome.TERMINAL, 410, None,
                              "lease was revoked")
    CONTEXT_MISMATCH = ErrorSpec("INV55-E005-CONTEXT-MISMATCH", Outcome.DENIED, 403, None,
                                 "lease context does not match")
    VERSION_RETIRED = ErrorSpec("INV55-E006-VERSION-RETIRED", Outcome.TERMINAL, 410, None,
                                "secret version is retired")
    INVALID_REFERENCE = ErrorSpec("INV55-E007-INVALID-REFERENCE", Outcome.TERMINAL, 400, None,
                                  "malformed identifier or request")
    CLOCK_ROLLBACK = ErrorSpec("INV55-E008-CLOCK-ROLLBACK", Outcome.TERMINAL, 500, None,
                               "monotonic clock moved backwards; failing closed")
    PROVIDER_UNAVAILABLE = ErrorSpec("INV55-E009-PROVIDER-UNAVAILABLE", Outcome.RETRYABLE, 503, 1000,
                                     "secret provider unavailable")
    OVERLOADED = ErrorSpec("INV55-E010-OVERLOADED", Outcome.RETRYABLE, 429, 250,
                           "admission rejected; retry later")
    QUOTA_EXCEEDED = ErrorSpec("INV55-E011-QUOTA-EXCEEDED", Outcome.RETRYABLE, 429, 1000,
                               "tenant/workload quota exhausted")
    DEADLINE_EXCEEDED = ErrorSpec("INV55-E012-DEADLINE-EXCEEDED", Outcome.RETRYABLE, 504, 100,
                                  "request deadline exceeded")
    FROZEN = ErrorSpec("INV55-E013-FROZEN", Outcome.DENIED, 503, None,
                       "component is quarantined or frozen by operator")
    AUDIT_UNAVAILABLE = ErrorSpec("INV55-E014-AUDIT-UNAVAILABLE", Outcome.RETRYABLE, 503, 1000,
                                  "durable audit sink unavailable; failing closed")
    UNSUPPORTED_VERSION = ErrorSpec("INV55-E015-UNSUPPORTED-VERSION", Outcome.TERMINAL, 400, None,
                                    "protocol version not supported")
    LIMIT_EXCEEDED = ErrorSpec("INV55-E016-LIMIT-EXCEEDED", Outcome.TERMINAL, 413, None,
                               "request exceeds an interface limit")
    CAPACITY_EXHAUSTED = ErrorSpec("INV55-E017-CAPACITY", Outcome.RETRYABLE, 507, 5000,
                                   "storage capacity exhausted")
    CONFLICT = ErrorSpec("INV55-E019-CONFLICT", Outcome.TERMINAL, 409, None,
                         "expected_version does not match current version")
    CANCELLED = ErrorSpec("INV55-E018-CANCELLED", Outcome.TERMINAL, 499, None, "request cancelled")
    INTERNAL = ErrorSpec("INV55-E999-INTERNAL", Outcome.TERMINAL, 500, None, "internal error")


class Inv55Error(Exception):
    """Base class for typed public errors."""

    code: ErrorCode = ErrorCode.INTERNAL

    def __init__(self, detail: str | None = None, *, code: ErrorCode | None = None) -> None:
        if code is not None:
            self.code = code
        super().__init__(detail or self.code.value.message)

    def to_wire(self, request_id: str | None = None) -> dict:
        spec = self.code.value
        out = {
            "protocol": "PK_SECRET_ERROR/1",
            "code": spec.code,
            "outcome": spec.outcome.value,
            "http_status": spec.http_status,
            "message": spec.message,          # fixed text: never caller- or secret-derived
        }
        if spec.retry_after_ms is not None:
            out["retry_after_ms"] = spec.retry_after_ms
        if request_id is not None:
            out["request_id"] = request_id
        return out


def error(code: ErrorCode, detail: str | None = None) -> Inv55Error:
    return Inv55Error(detail, code=code)


_SECRETISH = re.compile(
    r"(?i)(hvs\.[A-Za-z0-9_-]{8,}|s\.[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"
    r"|(password|secret|token|api[_-]?key)\s*[=:]\s*\S+)"
)


def redact_text(text: str, known: tuple[str, ...] = ()) -> str:
    """Remove known secret values and credential-shaped substrings."""
    for value in known:
        if value:
            text = text.replace(value, "***")
    return _SECRETISH.sub("***", text)
