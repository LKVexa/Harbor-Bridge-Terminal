"""Machine-readable outcome and error taxonomy for INV-53 (components 05, 16).

Every public operation of the service layer returns an :class:`Outcome`.  The
taxonomy is versioned (``ERROR_TAXONOMY_VERSION``) and exported as JSON by
``python -m inv53_message_reliability errors`` so clients can bind to codes
instead of exception text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

ERROR_TAXONOMY_VERSION = "inv53.errors/1"


class Kind(str, Enum):
    SUCCESS = "success"
    DUPLICATE = "duplicate"            # idempotent replay: success, no new effect
    RETRYABLE = "retryable"            # caller may retry with backoff
    TERMINAL = "terminal"              # caller must not retry the same request
    REFUSED = "refused"                # policy/capacity refusal, retry after condition changes
    DEGRADED = "degraded"              # accepted under a declared degraded mode


@dataclass(frozen=True)
class Code:
    code: str
    kind: Kind
    retryable: bool
    description: str


CODES: dict[str, Code] = {c.code: c for c in [
    Code("OK", Kind.SUCCESS, False, "Operation completed."),
    Code("OK_DUPLICATE", Kind.DUPLICATE, False, "Idempotent replay of an already-applied request; no new effect."),
    Code("OK_EMPTY", Kind.SUCCESS, False, "Receive found no visible message."),
    Code("OK_DEGRADED", Kind.DEGRADED, False, "Accepted while a declared degraded mode is active."),
    Code("E_VALIDATION", Kind.TERMINAL, False, "Request failed schema or field validation."),
    Code("E_PROTOCOL_VERSION", Kind.TERMINAL, False, "No mutually supported protocol version."),
    Code("E_UNAUTHENTICATED", Kind.TERMINAL, False, "Caller identity could not be established."),
    Code("E_FORBIDDEN", Kind.TERMINAL, False, "Authenticated caller lacks the capability for this action/resource."),
    Code("E_DUPLICATE_ACTIVE", Kind.TERMINAL, False, "A different message with this id is already active."),
    Code("E_LEASE_STALE", Kind.TERMINAL, False, "Lease token missing, expired or superseded (fencing)."),
    Code("E_EPOCH_FENCED", Kind.TERMINAL, False, "Writer epoch is older than the store epoch; this node lost ownership."),
    Code("E_CAPACITY", Kind.REFUSED, True, "A hard capacity limit would be exceeded; nothing was changed."),
    Code("E_QUOTA", Kind.REFUSED, True, "Tenant quota or rate limit exceeded."),
    Code("E_SHED", Kind.REFUSED, True, "Admission control shed the request under overload."),
    Code("E_CIRCUIT_OPEN", Kind.REFUSED, True, "Circuit breaker open for a failing dependency."),
    Code("E_FROZEN", Kind.REFUSED, False, "Queue or tenant is frozen / quarantined / emergency-disabled."),
    Code("E_DRAINING", Kind.REFUSED, True, "Service is draining; new work is not admitted."),
    Code("E_SECURITY_DEPENDENCY", Kind.REFUSED, True, "A security dependency (key provider, audit sink) is unavailable; failing closed."),
    Code("E_STORAGE", Kind.RETRYABLE, True, "Durable write failed; outcome indeterminate. Store fail-stops; retry idempotently after recovery."),
    Code("E_CORRUPT", Kind.TERMINAL, False, "Durable state failed integrity verification; manual recovery required."),
    Code("E_INTERNAL", Kind.RETRYABLE, True, "Unexpected internal error; state unchanged."),
]}


@dataclass(frozen=True)
class Outcome:
    code: str
    reason: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.code not in CODES:
            raise ValueError(f"unknown outcome code {self.code!r}")

    @property
    def ok(self) -> bool:
        return CODES[self.code].kind in (Kind.SUCCESS, Kind.DUPLICATE, Kind.DEGRADED)

    @property
    def retryable(self) -> bool:
        return CODES[self.code].retryable

    def to_dict(self) -> dict[str, Any]:
        c = CODES[self.code]
        return {"code": c.code, "kind": c.kind.value, "retryable": c.retryable,
                "reason": self.reason, "data": self.data}


def taxonomy() -> dict[str, Any]:
    return {"schema": ERROR_TAXONOMY_VERSION,
            "codes": [{"code": c.code, "kind": c.kind.value, "retryable": c.retryable,
                       "description": c.description} for c in CODES.values()]}
