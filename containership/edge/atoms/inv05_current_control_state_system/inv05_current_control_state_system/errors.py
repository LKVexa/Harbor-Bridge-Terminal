"""Structured, transport-independent error model for INV-05 (MC-013).

Every error the service can surface to a caller is a :class:`StateError`
subclass carrying an immutable machine code from :data:`ERROR_CATALOG`.
Codes are never renamed or reused; new codes are appended only.  The
``to_wire`` form contains only *safe* details (allow-listed field names), so
stack traces, secrets, backend internals and other tenants' data never reach a
caller.  Transport mappings (HTTP status) are derived from the code, never the
other way around, so semantic identity survives any transport.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    category: str
    retryable: bool
    idempotency_sensitive: bool
    http_status: int
    description: str


# Immutable namespace.  APPEND ONLY.  tools/check_error_catalog.py pins this in CI.
ERROR_CATALOG: dict[str, ErrorSpec] = {spec.code: spec for spec in [
    ErrorSpec("CSTATE_INVALID_ARGUMENT", "input", False, False, 400, "Malformed or out-of-range request field"),
    ErrorSpec("CSTATE_UNSUPPORTED_PREDICATE", "input", False, False, 400, "Compare target/operator combination is not supported"),
    ErrorSpec("CSTATE_SCHEMA_VERSION", "input", False, False, 400, "Wire schema version not supported"),
    ErrorSpec("CSTATE_COMPACTED", "compaction", False, False, 410, "Requested revision was compacted; relist from a fresh snapshot"),
    ErrorSpec("CSTATE_FUTURE_REVISION", "input", True, False, 400, "Requested revision is newer than the store revision"),
    ErrorSpec("CSTATE_CONFLICT", "conflict", False, False, 409, "Idempotency key reused with a different request"),
    ErrorSpec("CSTATE_LEASE_NOT_FOUND", "conflict", False, False, 404, "Lease does not exist or has expired"),
    ErrorSpec("CSTATE_FENCED", "conflict", False, False, 409, "Stale fencing token or site epoch; caller no longer owns the resource"),
    ErrorSpec("CSTATE_UNAVAILABLE", "unavailable", True, True, 503, "Store or dependency unavailable"),
    ErrorSpec("CSTATE_FROZEN", "unavailable", True, False, 503, "Admission frozen by operator control"),
    ErrorSpec("CSTATE_FAILED", "unavailable", False, True, 503, "Store entered fail-closed state; operator recovery required"),
    ErrorSpec("CSTATE_TIMEOUT", "timeout", True, True, 504, "Deadline exceeded"),
    ErrorSpec("CSTATE_CANCELLED", "cancellation", False, True, 499, "Caller cancelled the operation"),
    ErrorSpec("CSTATE_QUOTA", "quota", True, False, 429, "Per-identity or per-tenant quota exceeded"),
    ErrorSpec("CSTATE_OVERLOADED", "overload", True, False, 429, "Server overloaded; retry after the indicated delay"),
    ErrorSpec("CSTATE_LIMIT", "input", False, False, 413, "Request exceeds a configured size/count limit"),
    ErrorSpec("CSTATE_UNAUTHENTICATED", "authn", False, False, 401, "Caller identity could not be established"),
    ErrorSpec("CSTATE_PERMISSION_DENIED", "authz", False, False, 403, "Caller is not authorised for this action"),
    ErrorSpec("CSTATE_INCOMPATIBLE_VERSION", "input", False, False, 426, "Protocol major version incompatible"),
    ErrorSpec("CSTATE_CORRUPTION", "internal", False, True, 500, "Persistent data failed integrity verification"),
    ErrorSpec("CSTATE_INTERNAL", "internal", False, True, 500, "Internal error (details withheld)"),
    ErrorSpec("CSTATE_SLOW_CONSUMER", "overload", True, False, 429, "Watch cancelled because the consumer fell behind"),
    ErrorSpec("CSTATE_DRAINING", "unavailable", True, False, 503, "Server draining; reconnect elsewhere"),
]}

#: Detail keys that may be returned to callers.  Everything else is dropped.
SAFE_DETAIL_KEYS = frozenset({
    "revision", "compact_revision", "current_revision", "retry_after_s", "limit",
    "limit_value", "field", "dependency", "supported", "reason", "resume_revision",
})


class StateError(Exception):
    """Base error.  ``code`` must exist in :data:`ERROR_CATALOG`."""

    code = "CSTATE_INTERNAL"

    def __init__(self, message: str = "", **details: Any) -> None:
        super().__init__(message or ERROR_CATALOG[self.code].description)
        self.message = message or ERROR_CATALOG[self.code].description
        self.details = details

    @property
    def spec(self) -> ErrorSpec:
        return ERROR_CATALOG[self.code]

    def to_wire(self) -> dict[str, Any]:
        spec = self.spec
        safe = {k: v for k, v in self.details.items()
                if k in SAFE_DETAIL_KEYS and isinstance(v, (int, float, str, bool, list))}
        msg = self.message if spec.category != "internal" else spec.description
        return {"code": spec.code, "category": spec.category, "retryable": spec.retryable,
                "message": msg[:512], "details": safe}


def _mk(name: str, code: str, base: type = StateError) -> type:
    return type(name, (base,), {"code": code, "__doc__": ERROR_CATALOG[code].description})


InvalidArgument = _mk("InvalidArgument", "CSTATE_INVALID_ARGUMENT")
UnsupportedPredicate = _mk("UnsupportedPredicate", "CSTATE_UNSUPPORTED_PREDICATE", InvalidArgument)
SchemaVersionError = _mk("SchemaVersionError", "CSTATE_SCHEMA_VERSION", InvalidArgument)
CompactedError = _mk("CompactedError", "CSTATE_COMPACTED")
FutureRevision = _mk("FutureRevision", "CSTATE_FUTURE_REVISION")
IdempotencyConflict = _mk("IdempotencyConflict", "CSTATE_CONFLICT")
LeaseNotFound = _mk("LeaseNotFound", "CSTATE_LEASE_NOT_FOUND")
Fenced = _mk("Fenced", "CSTATE_FENCED")
Unavailable = _mk("Unavailable", "CSTATE_UNAVAILABLE")
Frozen = _mk("Frozen", "CSTATE_FROZEN", Unavailable)
FailedClosed = _mk("FailedClosed", "CSTATE_FAILED", Unavailable)
DeadlineExceeded = _mk("DeadlineExceeded", "CSTATE_TIMEOUT")
Cancelled = _mk("Cancelled", "CSTATE_CANCELLED")
QuotaExceeded = _mk("QuotaExceeded", "CSTATE_QUOTA")
Overloaded = _mk("Overloaded", "CSTATE_OVERLOADED")
LimitExceeded = _mk("LimitExceeded", "CSTATE_LIMIT", InvalidArgument)
Unauthenticated = _mk("Unauthenticated", "CSTATE_UNAUTHENTICATED")
PermissionDenied = _mk("PermissionDenied", "CSTATE_PERMISSION_DENIED")
IncompatibleVersion = _mk("IncompatibleVersion", "CSTATE_INCOMPATIBLE_VERSION")
CorruptionError = _mk("CorruptionError", "CSTATE_CORRUPTION")
InternalError = _mk("InternalError", "CSTATE_INTERNAL")
SlowConsumer = _mk("SlowConsumer", "CSTATE_SLOW_CONSUMER")
Draining = _mk("Draining", "CSTATE_DRAINING", Unavailable)


def to_wire(exc: BaseException) -> dict[str, Any]:
    """Map any exception to a safe wire error; unknown exceptions become INTERNAL."""
    if isinstance(exc, StateError):
        return exc.to_wire()
    return InternalError().to_wire()


def from_wire(payload: dict[str, Any]) -> StateError:
    """Rebuild a typed error from its wire form (client side)."""
    code = payload.get("code", "CSTATE_INTERNAL")
    for cls in StateError.__subclasses__() + [c for s in StateError.__subclasses__() for c in s.__subclasses__()]:
        if getattr(cls, "code", None) == code:
            return cls(payload.get("message", ""), **payload.get("details", {}))
    return InternalError(payload.get("message", ""))
