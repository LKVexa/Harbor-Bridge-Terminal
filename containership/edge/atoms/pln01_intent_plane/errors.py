"""Stable, versioned, machine-readable error codes for PLN-01 (MC-013).

Every public failure maps to exactly one code in ``ERROR_CODES``.  Codes are
append-only: a released code is never renumbered, re-purposed, or removed
(see docs/COMPATIBILITY.md).  ``to_error(exc)`` produces a
``PK_ERROR/1`` document that is safe to return over RPC: the message passes
through diagnostic redaction and never includes spec values.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_SCHEMA = "PK_ERROR/1"


@dataclass(frozen=True)
class ErrorCode:
    code: str
    http_status: int
    retryable: bool
    terminal: bool
    summary: str


ERROR_CODES: dict[str, ErrorCode] = {c.code: c for c in (
    ErrorCode("PLN01-E0001", 400, False, True, "Request or declaration failed validation"),
    ErrorCode("PLN01-E0002", 409, False, True, "Dependency cycle detected"),
    ErrorCode("PLN01-E0003", 409, True, False, "Stale graph version (optimistic concurrency conflict)"),
    ErrorCode("PLN01-E0004", 409, False, True, "Node has dependents; retract without cascade refused"),
    ErrorCode("PLN01-E0005", 403, False, True, "Admission rejected by boundary rule or policy"),
    ErrorCode("PLN01-E0006", 409, False, True, "Replayed mutation request_id"),
    ErrorCode("PLN01-E0007", 410, False, True, "Requested graph version aged out of retained history"),
    ErrorCode("PLN01-E0008", 401, False, True, "Authentication failed"),
    ErrorCode("PLN01-E0009", 403, False, True, "Principal lacks required capability"),
    ErrorCode("PLN01-E0010", 503, True, False, "Trust/identity dependency unavailable (fail-closed)"),
    ErrorCode("PLN01-E0011", 429, True, False, "Tenant quota or rate limit exceeded"),
    ErrorCode("PLN01-E0012", 503, True, False, "Overloaded: load shed or concurrency bulkhead full"),
    ErrorCode("PLN01-E0013", 504, True, False, "Deadline exceeded"),
    ErrorCode("PLN01-E0014", 499, False, True, "Operation cancelled by caller"),
    ErrorCode("PLN01-E0015", 503, True, False, "Circuit open for downstream dependency"),
    ErrorCode("PLN01-E0016", 423, False, False, "Scope quarantined, frozen, or disabled"),
    ErrorCode("PLN01-E0017", 422, False, True, "Secret material detected in declaration"),
    ErrorCode("PLN01-E0018", 422, False, True, "Artifact digest/signature/provenance verification failed"),
    ErrorCode("PLN01-E0019", 409, True, False, "Lease not held or fencing token stale"),
    ErrorCode("PLN01-E0020", 500, False, True, "Durable store corruption or integrity failure"),
    ErrorCode("PLN01-E0021", 400, False, True, "Configuration invalid"),
    ErrorCode("PLN01-E0022", 409, False, True, "Transaction aborted; no change applied"),
    ErrorCode("PLN01-E0023", 422, False, True, "Unsupported schema or protocol version"),
    ErrorCode("PLN01-E9999", 500, False, True, "Internal error"),
)}


class PlaneError(RuntimeError):
    """Base for service-layer failures that carry an explicit code."""

    code = "PLN01-E9999"

    def __init__(self, message: str = "", **details: Any) -> None:
        super().__init__(message or ERROR_CODES[self.code].summary)
        self.details = details


def _mk(name: str, code: str, *bases: type) -> type:
    return type(name, (PlaneError, *bases), {"code": code, "__doc__": ERROR_CODES[code].summary})


AuthenticationError = _mk("AuthenticationError", "PLN01-E0008", PermissionError)
AuthorizationError = _mk("AuthorizationError", "PLN01-E0009", PermissionError)
TrustUnavailableError = _mk("TrustUnavailableError", "PLN01-E0010")
QuotaExceededError = _mk("QuotaExceededError", "PLN01-E0011")
OverloadedError = _mk("OverloadedError", "PLN01-E0012")
DeadlineExceededError = _mk("DeadlineExceededError", "PLN01-E0013", TimeoutError)
CancelledError = _mk("CancelledError", "PLN01-E0014")
CircuitOpenError = _mk("CircuitOpenError", "PLN01-E0015")
ScopeFrozenError = _mk("ScopeFrozenError", "PLN01-E0016")
SecretDetectedError = _mk("SecretDetectedError", "PLN01-E0017", ValueError)
ArtifactVerificationError = _mk("ArtifactVerificationError", "PLN01-E0018")
LeaseError = _mk("LeaseError", "PLN01-E0019")
StoreIntegrityError = _mk("StoreIntegrityError", "PLN01-E0020")
ConfigError = _mk("ConfigError", "PLN01-E0021", ValueError)
TransactionAbortedError = _mk("TransactionAbortedError", "PLN01-E0022")
UnsupportedSchemaError = _mk("UnsupportedSchemaError", "PLN01-E0023", ValueError)

_GRAPH_MAP = {
    "ValidationError": "PLN01-E0001",
    "CycleError": "PLN01-E0002",
    "VersionConflictError": "PLN01-E0003",
    "DependencyInUseError": "PLN01-E0004",
    "AdmissionRejectedError": "PLN01-E0005",
    "ReplayError": "PLN01-E0006",
    "HistoryUnavailableError": "PLN01-E0007",
}


def code_for(exc: BaseException) -> str:
    if isinstance(exc, PlaneError):
        return exc.code
    for cls in type(exc).__mro__:
        if cls.__name__ in _GRAPH_MAP:
            return _GRAPH_MAP[cls.__name__]
    return "PLN01-E9999"


def to_error(exc: BaseException, *, trace_id: str | None = None) -> dict[str, Any]:
    """Render an exception as a redacted ``PK_ERROR/1`` document."""
    from .secret_guard import redact_text

    code = code_for(exc)
    meta = ERROR_CODES[code]
    message = meta.summary if code == "PLN01-E9999" else redact_text(str(exc))[:512]
    doc: dict[str, Any] = {
        "schema": ERROR_SCHEMA,
        "code": code,
        "http_status": meta.http_status,
        "retryable": meta.retryable,
        "terminal": meta.terminal,
        "message": message,
    }
    if trace_id:
        doc["trace_id"] = trace_id
    return doc
