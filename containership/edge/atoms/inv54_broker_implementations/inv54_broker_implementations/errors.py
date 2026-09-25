"""Structured, machine-readable error model and failure-semantics taxonomy (components 05, 22).

Every failure the INV-54 runtime surfaces is a :class:`BrokerError` carrying a stable
code from the ``INV54-*`` namespace, an :class:`Outcome` class, a retryability flag and
secret-safe details.  Codes are append-only: a published code is never renamed or
re-purposed (see ``docs/VERSIONING.md``).  Provider adapters translate native errors into
this namespace so callers never branch on provider-specific exceptions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

ERROR_SCHEMA = "PK_BROKER_ERROR/1"


class Outcome(str, Enum):
    """Normative outcome classes (docs/FAILURE_SEMANTICS.md)."""

    SUCCESS = "success"            # every mandatory effect happened exactly as requested
    PARTIAL = "partial"            # some effects happened; the result enumerates which
    DEGRADED = "degraded"          # succeeded under a declared degraded mode
    RETRYABLE = "retryable"        # nothing durable happened; same request may be retried
    TERMINAL = "terminal"          # will not succeed on retry without a change of input/state


@dataclass(frozen=True)
class ErrorCode:
    code: str
    outcome: Outcome
    http_status: int
    summary: str

    @property
    def retryable(self) -> bool:
        return self.outcome is Outcome.RETRYABLE


_CODES: dict[str, ErrorCode] = {}


def _reg(code: str, outcome: Outcome, http: int, summary: str) -> ErrorCode:
    if code in _CODES:
        raise RuntimeError(f"duplicate error code {code}")
    ec = ErrorCode(code, outcome, http, summary)
    _CODES[code] = ec
    return ec


INVALID_ARGUMENT = _reg("INV54-E0001", Outcome.TERMINAL, 400, "request field failed validation")
UNAUTHENTICATED = _reg("INV54-E0101", Outcome.TERMINAL, 401, "caller identity not established")
PERMISSION_DENIED = _reg("INV54-E0102", Outcome.TERMINAL, 403, "capability not granted")
TENANT_VIOLATION = _reg("INV54-E0103", Outcome.TERMINAL, 403, "cross-tenant access refused")
REPLAYED_CREDENTIAL = _reg("INV54-E0104", Outcome.TERMINAL, 401, "credential nonce already used")
SECURITY_SERVICE_UNAVAILABLE = _reg("INV54-E0105", Outcome.RETRYABLE, 503, "security dependency unavailable; failing closed")
QUOTA_EXCEEDED = _reg("INV54-E0201", Outcome.RETRYABLE, 429, "tenant/workload quota exhausted")
OVERLOADED = _reg("INV54-E0202", Outcome.RETRYABLE, 503, "admission control shed the request")
CIRCUIT_OPEN = _reg("INV54-E0203", Outcome.RETRYABLE, 503, "circuit breaker open")
BACKLOG_FULL = _reg("INV54-E0204", Outcome.RETRYABLE, 429, "subscriber backlog full")
DEADLINE_EXCEEDED = _reg("INV54-E0301", Outcome.RETRYABLE, 504, "deadline exceeded before effect")
CANCELLED = _reg("INV54-E0302", Outcome.TERMINAL, 499, "request cancelled by caller")
OFFSET_OUT_OF_RANGE = _reg("INV54-E0401", Outcome.TERMINAL, 416, "offset outside retained range")
PARTITION_UNAVAILABLE = _reg("INV54-E0402", Outcome.RETRYABLE, 503, "partition unavailable")
NOT_FOUND = _reg("INV54-E0403", Outcome.TERMINAL, 404, "named resource does not exist")
FENCED = _reg("INV54-E0501", Outcome.TERMINAL, 409, "stale owner epoch; write fenced")
NOT_LEADER = _reg("INV54-E0502", Outcome.RETRYABLE, 421, "node is not the partition leader")
STORAGE_CORRUPTION = _reg("INV54-E0503", Outcome.TERMINAL, 500, "durable record failed integrity check")
STORAGE_IO = _reg("INV54-E0504", Outcome.RETRYABLE, 503, "durable storage I/O failure")
ILLEGAL_STATE = _reg("INV54-E0601", Outcome.TERMINAL, 409, "operation illegal in current lifecycle state")
QUARANTINED = _reg("INV54-E0602", Outcome.TERMINAL, 423, "resource quarantined/frozen")
CONFIG_INVALID = _reg("INV54-E0701", Outcome.TERMINAL, 422, "configuration rejected by validator")
CONFIG_CONFLICT = _reg("INV54-E0702", Outcome.RETRYABLE, 409, "configuration changed concurrently")
VERSION_UNSUPPORTED = _reg("INV54-E0801", Outcome.TERMINAL, 426, "no mutually supported protocol version")
PROVIDER_UNAVAILABLE = _reg("INV54-E0901", Outcome.RETRYABLE, 503, "provider endpoint unavailable")
PROVIDER_REJECTED = _reg("INV54-E0902", Outcome.TERMINAL, 502, "provider rejected the request")
PROVIDER_NOT_INSTALLED = _reg("INV54-E0903", Outcome.TERMINAL, 501, "provider client library not installed")
UNSUPPORTED_FEATURE = _reg("INV54-E0904", Outcome.TERMINAL, 501, "feature unsupported by this provider")
INTEGRITY_FAILURE = _reg("INV54-E1001", Outcome.TERMINAL, 500, "artifact/audit integrity verification failed")
INTERNAL = _reg("INV54-E9999", Outcome.TERMINAL, 500, "unclassified internal error")


def registry() -> dict[str, ErrorCode]:
    return dict(_CODES)


_SECRETISH = ("secret", "password", "token", "credential", "key", "authorization")


def _safe(details: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in details.items():
        if any(s in k.lower() for s in _SECRETISH):
            out[k] = "***REDACTED***"
        elif isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v if not isinstance(v, str) or len(v) <= 256 else v[:256] + "…"
        else:
            out[k] = repr(v)[:256]
    return out


class BrokerError(Exception):
    """A classified INV-54 failure.  ``str()`` never contains secret-named detail values."""

    def __init__(self, code: ErrorCode, message: str | None = None, **details: Any) -> None:
        self.code = code
        self.message = message or code.summary
        self.details = _safe(details)
        super().__init__(f"{code.code}: {self.message}")

    @property
    def outcome(self) -> Outcome:
        return self.code.outcome

    @property
    def retryable(self) -> bool:
        return self.code.retryable

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ERROR_SCHEMA,
            "code": self.code.code,
            "outcome": self.code.outcome.value,
            "retryable": self.code.retryable,
            "status": self.code.http_status,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass
class Result:
    """Outcome record for multi-effect operations (fan-out, batch publish)."""

    outcome: Outcome
    delivered: list[str] = field(default_factory=list)
    failed: dict[str, dict[str, Any]] = field(default_factory=dict)
    mode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"outcome": self.outcome.value, "delivered": list(self.delivered),
                "failed": dict(self.failed), "mode": self.mode}


def classify(exc: BaseException) -> BrokerError:
    """Map any exception to the stable namespace (built-ins from the reference brokers)."""
    if isinstance(exc, BrokerError):
        return exc
    if isinstance(exc, (TypeError, ValueError)):
        return BrokerError(INVALID_ARGUMENT, str(exc))
    if isinstance(exc, IndexError):
        return BrokerError(OFFSET_OUT_OF_RANGE, str(exc))
    if isinstance(exc, KeyError):
        return BrokerError(NOT_FOUND, str(exc))
    if isinstance(exc, TimeoutError):
        return BrokerError(DEADLINE_EXCEEDED, str(exc))
    if isinstance(exc, OSError):
        return BrokerError(STORAGE_IO, type(exc).__name__)
    return BrokerError(INTERNAL, type(exc).__name__)
