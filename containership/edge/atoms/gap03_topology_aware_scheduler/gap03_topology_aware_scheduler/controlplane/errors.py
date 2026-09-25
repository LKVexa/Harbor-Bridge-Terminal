"""MC-014 - Service-level failure codes and RPC error model (GAP03-ERR/1).

One boundary (:func:`to_external`) maps every internal exception to a stable
external code.  Class names and stack traces never leave that boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

ERROR_NAMESPACE = "GAP03-ERR/1"
MAX_CAUSE_DEPTH = 4
MAX_DETAIL_CHARS = 256


@dataclass(frozen=True)
class ErrorCode:
    code: str
    category: str
    http_status: int
    grpc_status: str
    retryable: bool
    retry_after_s: int | None
    severity: str
    owner: str
    template: str
    stability: str = "stable"


_C = ErrorCode
CODES: dict[str, ErrorCode] = {c.code: c for c in (
    _C("INVALID_ARGUMENT", "validation", 400, "INVALID_ARGUMENT", False, None, "info", "wire", "request rejected: {reason}"),
    _C("UNSUPPORTED_VERSION", "validation", 400, "FAILED_PRECONDITION", False, None, "warn", "wire", "unsupported schema/protocol version"),
    _C("PAYLOAD_TOO_LARGE", "validation", 413, "RESOURCE_EXHAUSTED", False, None, "warn", "wire", "payload exceeds bounds"),
    _C("UNAUTHENTICATED", "authn", 401, "UNAUTHENTICATED", False, None, "security", "identity", "caller identity could not be verified"),
    _C("PERMISSION_DENIED", "authz", 403, "PERMISSION_DENIED", False, None, "security", "authz", "operation not permitted"),
    _C("REPLAY_DETECTED", "authn", 409, "ALREADY_EXISTS", False, None, "security", "identity", "request replay rejected"),
    _C("FAIRNESS_DENIED", "policy", 429, "RESOURCE_EXHAUSTED", False, None, "info", "fairshare", "claim denied by fair-share policy: {reason}"),
    _C("NO_CAPACITY", "capacity", 503, "RESOURCE_EXHAUSTED", True, 5, "info", "fairshare", "no capacity available"),
    _C("NO_FEASIBLE_CANDIDATE", "capacity", 422, "FAILED_PRECONDITION", False, None, "info", "scoring", "no feasible candidate"),
    _C("NOT_IN_TOPOLOGY", "validation", 404, "NOT_FOUND", False, None, "info", "topology", "node is not in the declared topology"),
    _C("STALE_STATE", "conflict", 409, "ABORTED", True, 0, "info", "state", "state changed since decision; re-score"),
    _C("CONFLICT", "conflict", 409, "ABORTED", False, None, "warn", "state", "conflicting mutation"),
    _C("FENCED", "coordination", 409, "FAILED_PRECONDITION", False, None, "warn", "coordination", "write carries a superseded fencing token"),
    _C("NOT_LEADER", "coordination", 503, "UNAVAILABLE", True, 1, "info", "coordination", "this replica does not hold the lease"),
    _C("DEPENDENCY_UNAVAILABLE", "dependency", 503, "UNAVAILABLE", True, 2, "error", "degraded", "a required dependency is unavailable"),
    _C("DEADLINE_EXCEEDED", "dependency", 504, "DEADLINE_EXCEEDED", True, 1, "warn", "retry", "deadline exceeded"),
    _C("OVERLOADED", "overload", 429, "RESOURCE_EXHAUSTED", True, 1, "warn", "admission", "scheduler overloaded; retry later"),
    _C("FROZEN", "control", 503, "UNAVAILABLE", False, None, "warn", "controls", "operation blocked by an active freeze/quarantine control"),
    _C("INTEGRITY_FAILURE", "integrity", 500, "DATA_LOSS", False, None, "security", "store", "integrity verification failed"),
    _C("INTERNAL", "internal", 500, "INTERNAL", False, None, "error", "scheduler", "internal error"),
)}
# alias rules: granular reason -> stable top-level code
ALIASES = {"RESERVATION_OVERSUBSCRIBED": "FAIRNESS_DENIED", "PROTECTED_RESERVATION": "FAIRNESS_DENIED",
           "CAPACITY_EXHAUSTED": "NO_CAPACITY"}


class SchedulerError(Exception):
    """Internal exception carrying a stable code; the only type the boundary trusts."""

    def __init__(self, code: str, reason: str = "", *, cause: "SchedulerError | None" = None, detail: dict | None = None):
        code = ALIASES.get(code, code)
        if code not in CODES:
            raise ValueError(f"unknown error code {code!r}")
        self.code = code
        self.reason = reason
        self.cause = cause
        self.detail = dict(detail or {})
        super().__init__(f"{code}: {reason}")


_PATHISH = re.compile(r"(/[\w.\-]+){2,}|[A-Za-z]:\\[^\s]+")
_SECRETISH = re.compile(r"(?i)(secret|token|password|key)=\S+")


def safe_text(text: str) -> str:
    text = _PATHISH.sub("<path>", str(text))
    text = _SECRETISH.sub(r"\1=<redacted>", text)
    text = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in text)
    return text[:MAX_DETAIL_CHARS]


def classify(exc: BaseException) -> SchedulerError:
    """Map any internal exception to a SchedulerError (the single mapping point)."""
    if isinstance(exc, SchedulerError):
        return exc
    from .. import scheduler as s
    if isinstance(exc, s.StaleFairShare):
        return SchedulerError("STALE_STATE", "fair-share state changed")
    if isinstance(exc, s.ReservationOversubscribed):
        return SchedulerError("RESERVATION_OVERSUBSCRIBED", "reservations exceed capacity")
    if isinstance(exc, s.ShareViolation):
        msg = str(exc)
        if "capacity_exhausted" in msg:
            return SchedulerError("NO_CAPACITY", "capacity_exhausted")
        return SchedulerError("FAIRNESS_DENIED", "protected_reservation")
    if isinstance(exc, s.NotInTopology):
        return SchedulerError("NOT_IN_TOPOLOGY", "unknown node")
    if isinstance(exc, s.TopologyConflict):
        return SchedulerError("CONFLICT", "topology rewrite requires explicit replace")
    if isinstance(exc, TimeoutError):
        return SchedulerError("DEADLINE_EXCEEDED", "timeout")
    if isinstance(exc, (ValueError, TypeError)):
        return SchedulerError("INVALID_ARGUMENT", safe_text(str(exc)))
    return SchedulerError("INTERNAL", "unexpected failure")


def to_external(exc: BaseException, *, correlation_id: str = "") -> dict:
    """Render an external error payload (bounded, redacted, versioned)."""
    err = classify(exc)
    spec = CODES[err.code]
    causes, cur, depth = [], err.cause, 0
    while cur is not None and depth < MAX_CAUSE_DEPTH:
        causes.append(cur.code)
        cur, depth = cur.cause, depth + 1
    reason = safe_text(err.reason)
    return {
        "namespace": ERROR_NAMESPACE,
        "code": err.code,
        "category": spec.category,
        "message": safe_text(spec.template.format(reason=reason) if "{reason}" in spec.template else spec.template),
        "reason": reason,
        "retryable": spec.retryable,
        "retry_after_s": spec.retry_after_s,
        "http_status": spec.http_status,
        "grpc_status": spec.grpc_status,
        "cause_chain": causes,
        "correlation_id": safe_text(correlation_id)[:64],
    }


def is_retryable(exc: BaseException) -> bool:
    return CODES[classify(exc).code].retryable


def catalog() -> list[dict]:
    return [c.__dict__.copy() for c in sorted(CODES.values(), key=lambda c: c.code)] + [
        {"alias": a, "maps_to": t} for a, t in sorted(ALIASES.items())]
