"""MC-14 - Wire-level structured error schema and stable error registry.

Every refusal the application plane can emit is registered here with a stable
code, a transport mapping, a retryability class and a redaction rule. The
public error document (``PK_ERROR/1``) is the only shape that may cross a
process boundary; Python exception text and internal details never do unless
the detail key is on the per-code allow-list.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

ERROR_SCHEMA = "PK_ERROR/1"


class PlaneError(Exception):
    """Base for non-resolver refusals raised by v4.3 plane components."""

    code = "INTERNAL"

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None, code: str | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    http_status: int
    grpc_status: str
    retryable: str  # "never" | "safe" | "after_backoff"
    category: str   # validation | policy | auth | dependency | integrity | capacity | internal | lifecycle
    public_details: tuple[str, ...] = ()


# Stable registry. Codes are append-only; removing or renumbering is a breaking change.
REGISTRY: dict[str, ErrorSpec] = {s.code: s for s in (
    ErrorSpec("INVALID_APPLICATION", 400, "INVALID_ARGUMENT", "never", "validation",
              ("field", "unsupported_fields", "limit", "actual", "component", "edge", "capability", "schema")),
    ErrorSpec("UNSATISFIED_CAPABILITY", 422, "FAILED_PRECONDITION", "never", "validation", ("component", "capability")),
    ErrorSpec("INCOMPATIBLE_INTERFACE", 422, "FAILED_PRECONDITION", "never", "validation",
              ("producer", "consumer", "interface", "exported_version", "imported_version", "reason")),
    ErrorSpec("REVISION_INTEGRITY_ERROR", 409, "DATA_LOSS", "never", "integrity", ()),
    ErrorSpec("RESOLUTION_ERROR", 422, "FAILED_PRECONDITION", "never", "validation", ()),
    ErrorSpec("UNSUPPORTED_VERSION", 400, "INVALID_ARGUMENT", "never", "validation", ("schema", "supported")),
    ErrorSpec("UNAUTHENTICATED", 401, "UNAUTHENTICATED", "never", "auth", ()),
    ErrorSpec("PERMISSION_DENIED", 403, "PERMISSION_DENIED", "never", "auth", ("capability", "reason")),
    ErrorSpec("POLICY_CONFLICT", 422, "FAILED_PRECONDITION", "never", "policy", ("capability", "constraint", "reason")),
    ErrorSpec("NO_ELIGIBLE_PROVIDER", 422, "FAILED_PRECONDITION", "never", "policy", ("capability", "rejected")),
    ErrorSpec("CATALOGUE_STALE", 503, "UNAVAILABLE", "after_backoff", "dependency", ("age_seconds", "max_age_seconds")),
    ErrorSpec("CATALOGUE_UNTRUSTED", 502, "FAILED_PRECONDITION", "never", "integrity", ("key_id",)),
    ErrorSpec("CATALOGUE_UNAVAILABLE", 503, "UNAVAILABLE", "after_backoff", "dependency", ()),
    ErrorSpec("ARTIFACT_UNTRUSTED", 422, "FAILED_PRECONDITION", "never", "integrity", ("artifact", "reason")),
    ErrorSpec("QUOTA_EXCEEDED", 429, "RESOURCE_EXHAUSTED", "after_backoff", "capacity", ("tenant", "limit")),
    ErrorSpec("OVERLOADED", 503, "UNAVAILABLE", "after_backoff", "capacity", ("reason",)),
    ErrorSpec("PAYLOAD_TOO_LARGE", 413, "INVALID_ARGUMENT", "never", "capacity", ("limit", "actual")),
    ErrorSpec("CIRCUIT_OPEN", 503, "UNAVAILABLE", "after_backoff", "dependency", ("dependency",)),
    ErrorSpec("DEADLINE_EXCEEDED", 504, "DEADLINE_EXCEEDED", "safe", "dependency", ()),
    ErrorSpec("CANCELLED", 499, "CANCELLED", "safe", "lifecycle", ()),
    ErrorSpec("IDEMPOTENCY_CONFLICT", 409, "ALREADY_EXISTS", "never", "lifecycle", ()),
    ErrorSpec("FENCED", 409, "ABORTED", "never", "lifecycle", ("held", "presented")),
    ErrorSpec("PLANE_FROZEN", 423, "FAILED_PRECONDITION", "after_backoff", "lifecycle", ("scope",)),
    ErrorSpec("PLANE_DISABLED", 503, "UNAVAILABLE", "never", "lifecycle", ("scope",)),
    ErrorSpec("REVISION_QUARANTINED", 423, "FAILED_PRECONDITION", "never", "lifecycle", ("revision",)),
    ErrorSpec("REVISION_NOT_FOUND", 404, "NOT_FOUND", "never", "lifecycle", ("revision",)),
    ErrorSpec("CONFIG_INVALID", 400, "INVALID_ARGUMENT", "never", "validation", ("field",)),
    ErrorSpec("SECRET_INLINE", 400, "INVALID_ARGUMENT", "never", "validation", ("field",)),
    ErrorSpec("SECRET_UNAVAILABLE", 503, "UNAVAILABLE", "after_backoff", "dependency", ("ref",)),
    ErrorSpec("AUDIT_CHAIN_BROKEN", 500, "DATA_LOSS", "never", "integrity", ("sequence",)),
    ErrorSpec("OAM_INVALID", 400, "INVALID_ARGUMENT", "never", "validation", ("field", "reason")),
    ErrorSpec("WIT_INVALID", 400, "INVALID_ARGUMENT", "never", "validation", ("line", "reason")),
    ErrorSpec("INTERNAL", 500, "INTERNAL", "never", "internal", ()),
)}


def to_public(error: BaseException, *, correlation_id: str | None = None) -> dict[str, Any]:
    """Render any exception as a redacted ``PK_ERROR/1`` document.

    Unknown exceptions become ``INTERNAL`` with no message leakage. Only detail
    keys on the code's allow-list are emitted, and values are reduced to
    bounded scalars / lists of scalars.
    """
    code = getattr(error, "code", None)
    spec = REGISTRY.get(code) if isinstance(code, str) else None
    if spec is None:
        spec = REGISTRY["INTERNAL"]
        message = "internal error"
        details: dict[str, Any] = {}
    else:
        message = str(error)[:512]
        raw = getattr(error, "details", {}) or {}
        details = {k: _scalarize(v) for k, v in raw.items() if k in spec.public_details}
    doc = {
        "schema": ERROR_SCHEMA,
        "code": spec.code,
        "category": spec.category,
        "retryable": spec.retryable,
        "http_status": spec.http_status,
        "grpc_status": spec.grpc_status,
        "message": message,
        "details": details,
    }
    if correlation_id is not None:
        doc["correlation_id"] = str(correlation_id)[:128]
    return doc


def _scalarize(value: Any) -> Any:
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, str):
        return value[:256]
    if isinstance(value, (list, tuple)):
        return [_scalarize(v) for v in list(value)[:32] if not isinstance(v, (dict, list, tuple))]
    return str(value)[:256]
