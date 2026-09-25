"""Machine-readable error and outcome model (MC-006, MC-016).

Codes are stable, namespaced strings.  They are part of the public contract:
removing or re-purposing a code is a breaking change (see COMPATIBILITY.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Outcome(str, Enum):
    """Outcome taxonomy for every PK_TOPO_* operation."""

    SUCCESS = "success"                # full answer, all constraints honoured
    PARTIAL = "partial"                # answer returned, some requested facets missing
    DEGRADED = "degraded"              # answer produced under a declared degraded mode
    RETRYABLE = "retryable_failure"    # no answer; the same request may succeed later
    TERMINAL = "terminal_failure"      # no answer; retrying the same request cannot help


@dataclass(frozen=True)
class ErrorCode:
    code: str
    outcome: Outcome
    http_status: int
    description: str


_CODES: dict[str, ErrorCode] = {}


def _reg(code: str, outcome: Outcome, http: int, description: str) -> ErrorCode:
    ec = ErrorCode(code, outcome, http, description)
    if code in _CODES:
        raise RuntimeError(f"duplicate error code {code}")
    _CODES[code] = ec
    return ec


T = Outcome.TERMINAL
R = Outcome.RETRYABLE
INVALID_REQUEST = _reg("TOPO.INVALID_REQUEST", T, 400, "Payload failed schema or semantic validation")
UNSUPPORTED_VERSION = _reg("TOPO.UNSUPPORTED_VERSION", T, 426, "No mutually supported protocol version")
PAYLOAD_TOO_LARGE = _reg("TOPO.PAYLOAD_TOO_LARGE", T, 413, "Payload exceeds the interface byte/item limit")
UNAUTHENTICATED = _reg("TOPO.UNAUTHENTICATED", T, 401, "Credential missing, malformed, expired or not trusted")
REPLAYED = _reg("TOPO.REPLAYED", T, 401, "Credential nonce was already used")
FORBIDDEN = _reg("TOPO.FORBIDDEN", T, 403, "Principal lacks the capability for this operation/tenant")
UNKNOWN_NODE = _reg("TOPO.UNKNOWN_NODE", T, 404, "Referenced node does not exist in the tenant graph")
UNKNOWN_SITE = _reg("TOPO.UNKNOWN_SITE", T, 404, "Referenced site has no members")
CONFLICT = _reg("TOPO.CONFLICT", T, 409, "Expected revision does not match (compare-and-set failed)")
IDEMPOTENCY_MISMATCH = _reg("TOPO.IDEMPOTENCY_MISMATCH", T, 422, "Idempotency key reused with a different payload")
INVALID_TOPOLOGY = _reg("TOPO.INVALID_TOPOLOGY", T, 422, "Mutation would violate a topology invariant")
QUOTA_EXCEEDED = _reg("TOPO.QUOTA_EXCEEDED", T, 429, "Tenant graph quota exhausted")
NO_CAPABLE_NODE = _reg("TOPO.NO_CAPABLE_NODE", T, 404, "No reachable node satisfies capability and policy")
NO_COORDINATOR = _reg("TOPO.NO_COORDINATOR", T, 404, "Site has no coordinator-eligible node")
FROZEN = _reg("TOPO.FROZEN", R, 423, "Automated decisions are frozen by an operator")
QUARANTINED = _reg("TOPO.QUARANTINED", T, 423, "Target is quarantined")
RATE_LIMITED = _reg("TOPO.RATE_LIMITED", R, 429, "Admission control shed this request")
OVERLOADED = _reg("TOPO.OVERLOADED", R, 503, "Bounded queue full or circuit open")
DEADLINE_EXCEEDED = _reg("TOPO.DEADLINE_EXCEEDED", R, 504, "Deadline elapsed before completion")
CANCELLED = _reg("TOPO.CANCELLED", R, 499, "Caller cancelled the request")
DEPENDENCY_UNAVAILABLE = _reg("TOPO.DEPENDENCY_UNAVAILABLE", R, 503, "Identity/policy/key/time dependency unavailable; failing closed")
STALE_LEADER = _reg("TOPO.STALE_LEADER", T, 409, "Fencing token is older than the current term")
NOT_READY = _reg("TOPO.NOT_READY", R, 503, "Service has no active validated configuration")
INTERNAL = _reg("TOPO.INTERNAL", R, 500, "Unexpected defect; details withheld from caller")

del T, R


def registry() -> dict[str, ErrorCode]:
    return dict(_CODES)


@dataclass
class TopoError(Exception):
    """Serializable protocol error.  ``details`` must never contain secrets."""

    error: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retry_after_ms: int | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, f"{self.error.code}: {self.message}")

    @property
    def code(self) -> str:
        return self.error.code

    @property
    def outcome(self) -> Outcome:
        return self.error.outcome

    def to_wire(self, correlation_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "code": self.error.code,
            "outcome": self.error.outcome.value,
            "message": self.message,
            "retryable": self.error.outcome is Outcome.RETRYABLE,
            "details": self.details,
        }
        if self.retry_after_ms is not None:
            body["retry_after_ms"] = self.retry_after_ms
        if correlation_id is not None:
            body["correlation_id"] = correlation_id
        return body
