"""MC-18 - unified public error contract (PK_SCHEDULER_ERROR/2).

Every failure that crosses the SCH-01 boundary is a :class:`SchedulerError` with a code
from :data:`CATALOG`.  Each catalog entry states retryability and the caller action, so a
client never has to parse a message.  ``ValueError``/``TypeError`` raised by the 4.2.0
engine are translated by :func:`from_exception` at the service boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

ERROR_SCHEMA = "PK_SCHEDULER_ERROR/2"


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    http: int
    retryable: bool
    category: str  # caller | policy | capacity | security | availability | internal
    action: str


CATALOG: dict[str, ErrorSpec] = {s.code: s for s in (
    ErrorSpec("INVALID_REQUEST", 400, False, "caller", "fix the request; see details.field"),
    ErrorSpec("SCHEMA_VIOLATION", 400, False, "caller", "payload does not satisfy the published schema"),
    ErrorSpec("UNSUPPORTED_VERSION", 400, False, "caller", "use a supported schema version (see compat policy)"),
    ErrorSpec("UNKNOWN_PROVENANCE", 422, False, "policy", "register the workload provenance with the policy owner"),
    ErrorSpec("NO_CANDIDATE", 409, True, "capacity", "retry after capacity changes; see rejection_counts"),
    ErrorSpec("DUPLICATE_LEASE", 409, False, "caller", "release the existing lease before re-placing"),
    ErrorSpec("QUOTA_EXCEEDED", 429, True, "capacity", "wait for tenant usage to fall or request a quota change"),
    ErrorSpec("UNAUTHENTICATED", 401, False, "security", "present a valid, unexpired, unreplayed credential"),
    ErrorSpec("FORBIDDEN", 403, False, "security", "caller lacks the capability for this operation/tenant"),
    ErrorSpec("ATTESTATION_FAILED", 422, False, "security", "node evidence did not verify; node is not schedulable"),
    ErrorSpec("POLICY_INVALID", 422, False, "policy", "policy bundle failed signature or validation"),
    ErrorSpec("CONFIG_INVALID", 422, False, "policy", "configuration failed validation; previous revision stays active"),
    ErrorSpec("DEADLINE_EXCEEDED", 504, True, "availability", "retry with the same idempotency key"),
    ErrorSpec("CANCELLED", 499, False, "caller", "request was cancelled by the caller"),
    ErrorSpec("OVERLOADED", 503, True, "availability", "back off (retry_after_ms) and retry with the same idempotency key"),
    ErrorSpec("CIRCUIT_OPEN", 503, True, "availability", "a dependency is failing; retry after retry_after_ms"),
    ErrorSpec("SCHEDULER_DISABLED", 503, True, "availability", "operator kill switch is engaged"),
    ErrorSpec("FROZEN", 503, True, "availability", "placements are frozen by an operator"),
    ErrorSpec("FENCED", 409, True, "availability", "this scheduler instance lost ownership; route to the current owner"),
    ErrorSpec("IDEMPOTENCY_CONFLICT", 409, False, "caller", "idempotency key reused with a different request body"),
    ErrorSpec("NOT_FOUND", 404, False, "caller", "unknown lease or object"),
    ErrorSpec("ILLEGAL_TRANSITION", 409, False, "caller", "lifecycle transition not permitted from current state"),
    ErrorSpec("SECRET_UNAVAILABLE", 503, True, "availability", "key provider unavailable; scheduler fails closed"),
    ErrorSpec("STATE_CORRUPT", 500, False, "internal", "journal integrity check failed; restore from backup"),
    ErrorSpec("INTERNAL", 500, False, "internal", "defect; report with trace_id"),
)}


class SchedulerError(Exception):
    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None,
                 retry_after_ms: int | None = None):
        if code not in CATALOG:
            code, message = "INTERNAL", f"uncatalogued error code {code!r}: {message}"
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})
        self.retry_after_ms = retry_after_ms

    @property
    def spec(self) -> ErrorSpec:
        return CATALOG[self.code]

    def as_dict(self) -> dict[str, Any]:
        out = {"schema": ERROR_SCHEMA, "code": self.code, "message": str(self),
               "retryable": self.spec.retryable, "category": self.spec.category,
               "action": self.spec.action, "details": self.details}
        if self.retry_after_ms is not None:
            out["retry_after_ms"] = self.retry_after_ms
        return out


def from_exception(exc: BaseException) -> SchedulerError:
    """Map any exception to the public contract without leaking internals."""
    from .engine import Unplaceable
    if isinstance(exc, SchedulerError):
        return exc
    if isinstance(exc, Unplaceable):
        return SchedulerError(exc.code if exc.code in CATALOG else "NO_CANDIDATE", str(exc), details=exc.details)
    if isinstance(exc, (ValueError, TypeError)):
        return SchedulerError("INVALID_REQUEST", str(exc))
    return SchedulerError("INTERNAL", "internal error")
