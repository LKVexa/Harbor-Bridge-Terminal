"""Stable error taxonomy for the INV-04 runtime layer (components 22, 26, 33, 34).

Every runtime error carries a stable machine code, a retry classification and a
transport mapping.  Codes are part of the PK_ORCH_ERROR/1 contract; adding a
code is a minor contract change, renaming or removing one is breaking.
"""
from __future__ import annotations

from ..model import OrchestrationError


class RuntimeFault(OrchestrationError):
    """Base runtime error. ``retryable`` drives the retry classifier."""

    code = "ORCH_RUNTIME_ERROR"
    retryable = False

    def __init__(self, message: str, *, reason: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.reason = reason or self.code
        self.details = dict(details or {})

    def as_dict(self) -> dict:  # type: ignore[override]
        out: dict = {"code": self.code, "message": str(self)}
        if self.details:
            out["details"] = {k: v for k, v in sorted(self.details.items())}
        return out


class Conflict(RuntimeFault):
    code = "ORCH_CONFLICT"
    retryable = True


class StaleCache(RuntimeFault):
    code = "ORCH_STALE_CACHE"
    retryable = True


class NotFound(RuntimeFault):
    code = "ORCH_NOT_FOUND"


class AlreadyExists(RuntimeFault):
    code = "ORCH_ALREADY_EXISTS"


class Gone(RuntimeFault):
    """Watch window expired (HTTP 410 equivalent); caller must relist."""

    code = "ORCH_WATCH_EXPIRED"
    retryable = True


class NotLeader(RuntimeFault):
    code = "ORCH_NOT_LEADER"


class FencedOut(RuntimeFault):
    code = "ORCH_FENCED"


class DeadlineExceeded(RuntimeFault):
    code = "ORCH_DEADLINE_EXCEEDED"
    retryable = True


class Cancelled(RuntimeFault):
    code = "ORCH_CANCELLED"


class Throttled(RuntimeFault):
    code = "ORCH_THROTTLED"
    retryable = True


class CircuitOpen(RuntimeFault):
    code = "ORCH_CIRCUIT_OPEN"
    retryable = True


class DependencyUnavailable(RuntimeFault):
    code = "ORCH_DEPENDENCY_UNAVAILABLE"
    retryable = True


class EvictionBlocked(RuntimeFault):
    """The eviction subresource refused the request (HTTP 429 equivalent)."""

    code = "ORCH_EVICTION_BLOCKED"
    retryable = True


class DrainPolicyViolation(RuntimeFault):
    code = "ORCH_DRAIN_POLICY"


class SchemaViolation(RuntimeFault):
    code = "ORCH_SCHEMA_INVALID"


class Unauthenticated(RuntimeFault):
    code = "ORCH_UNAUTHENTICATED"


class Forbidden(RuntimeFault):
    code = "ORCH_FORBIDDEN"


class AdmissionDenied(RuntimeFault):
    code = "ORCH_ADMISSION_DENIED"


class QuotaExceeded(RuntimeFault):
    code = "ORCH_QUOTA_EXCEEDED"
    retryable = True


class IncompatibleProtocol(RuntimeFault):
    code = "ORCH_PROTOCOL_INCOMPATIBLE"


class IdempotencyMismatch(RuntimeFault):
    code = "ORCH_IDEMPOTENCY_MISMATCH"


class JournalCorrupt(RuntimeFault):
    code = "ORCH_JOURNAL_CORRUPT"


class HandoffGap(RuntimeFault):
    code = "ORCH_HANDOFF_GAP"


class OwnershipConflict(RuntimeFault):
    code = "ORCH_OWNERSHIP_CONFLICT"


class ConfigRejected(RuntimeFault):
    code = "ORCH_CONFIG_REJECTED"


# code -> (http status, grpc status name, kubernetes Status reason)
TRANSPORT_MAP: dict[str, tuple[int, str, str]] = {
    "ORCH_CONFIGURATION_INVALID": (422, "INVALID_ARGUMENT", "Invalid"),
    "ORCH_STATE_INTEGRITY": (409, "FAILED_PRECONDITION", "Conflict"),
    "ORCH_BUDGET_BREACH": (429, "FAILED_PRECONDITION", "TooManyRequests"),
    "ORCH_UNKNOWN_NODE": (404, "NOT_FOUND", "NotFound"),
    "ORCH_NO_CAPACITY": (409, "RESOURCE_EXHAUSTED", "Conflict"),
    "ORCH_RUNTIME_ERROR": (500, "INTERNAL", "InternalError"),
    "ORCH_CONFLICT": (409, "ABORTED", "Conflict"),
    "ORCH_STALE_CACHE": (409, "ABORTED", "Conflict"),
    "ORCH_NOT_FOUND": (404, "NOT_FOUND", "NotFound"),
    "ORCH_ALREADY_EXISTS": (409, "ALREADY_EXISTS", "AlreadyExists"),
    "ORCH_WATCH_EXPIRED": (410, "OUT_OF_RANGE", "Expired"),
    "ORCH_NOT_LEADER": (503, "UNAVAILABLE", "ServiceUnavailable"),
    "ORCH_FENCED": (409, "ABORTED", "Conflict"),
    "ORCH_DEADLINE_EXCEEDED": (504, "DEADLINE_EXCEEDED", "Timeout"),
    "ORCH_CANCELLED": (499, "CANCELLED", "Timeout"),
    "ORCH_THROTTLED": (429, "RESOURCE_EXHAUSTED", "TooManyRequests"),
    "ORCH_CIRCUIT_OPEN": (503, "UNAVAILABLE", "ServiceUnavailable"),
    "ORCH_DEPENDENCY_UNAVAILABLE": (503, "UNAVAILABLE", "ServiceUnavailable"),
    "ORCH_EVICTION_BLOCKED": (429, "FAILED_PRECONDITION", "TooManyRequests"),
    "ORCH_DRAIN_POLICY": (409, "FAILED_PRECONDITION", "Conflict"),
    "ORCH_SCHEMA_INVALID": (400, "INVALID_ARGUMENT", "BadRequest"),
    "ORCH_UNAUTHENTICATED": (401, "UNAUTHENTICATED", "Unauthorized"),
    "ORCH_FORBIDDEN": (403, "PERMISSION_DENIED", "Forbidden"),
    "ORCH_ADMISSION_DENIED": (403, "PERMISSION_DENIED", "Forbidden"),
    "ORCH_QUOTA_EXCEEDED": (429, "RESOURCE_EXHAUSTED", "TooManyRequests"),
    "ORCH_PROTOCOL_INCOMPATIBLE": (426, "FAILED_PRECONDITION", "BadRequest"),
    "ORCH_IDEMPOTENCY_MISMATCH": (422, "INVALID_ARGUMENT", "Invalid"),
    "ORCH_JOURNAL_CORRUPT": (500, "DATA_LOSS", "InternalError"),
    "ORCH_HANDOFF_GAP": (409, "OUT_OF_RANGE", "Conflict"),
    "ORCH_OWNERSHIP_CONFLICT": (409, "FAILED_PRECONDITION", "Conflict"),
    "ORCH_CONFIG_REJECTED": (422, "INVALID_ARGUMENT", "Invalid"),
}

ALL_CODES = tuple(sorted(TRANSPORT_MAP))


def is_retryable(exc: BaseException) -> bool:
    """Retry classifier: only explicitly retryable runtime faults and timeouts."""
    if isinstance(exc, RuntimeFault):
        return exc.retryable
    return isinstance(exc, (TimeoutError, ConnectionError))
