"""INV-38-C014 — Outcome semantics for the kernel-bypass transport.

A closed, versioned set of operation outcomes and stable reason codes, with an
explicit mapping from the reference-model ``BypassError.code`` values in
``transport.py``.  This is a model-level contract: it defines the wire-stable
classification every adapter (reference or real RDMA backend) must honour.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Final

from .transport import (
    BypassError,
    CompletionRingFull,
    NotRegistered,
    OutOfBounds,
    RegionBusy,
    RegionLimitReached,
    RingFull,
)

OUTCOME_SCHEMA_VERSION: Final = "outcome/1"


class Outcome(str, enum.Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    DEGRADED = "DEGRADED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    REJECTED_POLICY = "REJECTED_POLICY"


class Retryability(str, enum.Enum):
    NOT_RETRYABLE = "NOT_RETRYABLE"
    SAFE = "SAFE"
    RETRY_WITH_IDEMPOTENCY_KEY = "RETRY_WITH_IDEMPOTENCY_KEY"
    RETRY_AFTER_RECONCILIATION = "RETRY_AFTER_RECONCILIATION"


@dataclass(frozen=True, slots=True)
class ReasonSpec:
    reason_code: str
    outcome: Outcome
    retryability: Retryability
    tenant_safe: bool  # may this reason code be surfaced to an untrusted tenant?
    description: str


# The canonical, closed reason table.  Adding a row is a backward-compatible
# change; removing or repurposing a row is a breaking change (see C022/C027).
REASONS: Final[dict[str, ReasonSpec]] = {
    r.reason_code: r
    for r in (
        ReasonSpec("PK_BYPASS_OK", Outcome.SUCCESS, Retryability.NOT_RETRYABLE, True,
                   "Operation completed on the bypass fast path."),
        ReasonSpec("PK_BYPASS_KERNEL_FALLBACK", Outcome.DEGRADED, Retryability.NOT_RETRYABLE, True,
                   "Bypass unavailable; served on the kernel path with sealing preserved."),
        ReasonSpec("PK_BYPASS_PARTIAL_BATCH", Outcome.PARTIAL_SUCCESS, Retryability.RETRY_WITH_IDEMPOTENCY_KEY, True,
                   "Some items in a batch succeeded; per-item results required."),
        ReasonSpec("PK_BYPASS_RING_FULL", Outcome.RETRYABLE_FAILURE, Retryability.SAFE, True,
                   "Submission ring has no free slots; safe to retry after drain."),
        ReasonSpec("PK_BYPASS_COMPLETION_RING_FULL", Outcome.RETRYABLE_FAILURE, Retryability.SAFE, True,
                   "Completion ring bound would be exceeded; poll then retry."),
        ReasonSpec("PK_BYPASS_REGION_BUSY", Outcome.RETRYABLE_FAILURE, Retryability.RETRY_AFTER_RECONCILIATION, True,
                   "Deregistration attempted while descriptors are in flight."),
        ReasonSpec("PK_BYPASS_REGION_LIMIT", Outcome.RETRYABLE_FAILURE, Retryability.RETRY_AFTER_RECONCILIATION, True,
                   "Registered-region ceiling reached; free a region and retry."),
        ReasonSpec("PK_BYPASS_OUT_OF_BOUNDS", Outcome.TERMINAL_FAILURE, Retryability.NOT_RETRYABLE, True,
                   "Descriptor/region outside its legal range; a safety invariant."),
        ReasonSpec("PK_BYPASS_NOT_REGISTERED", Outcome.TERMINAL_FAILURE, Retryability.NOT_RETRYABLE, True,
                   "Region key unknown or already deregistered (possibly stale key)."),
        ReasonSpec("PK_BYPASS_STALE_KEY", Outcome.TERMINAL_FAILURE, Retryability.NOT_RETRYABLE, True,
                   "Region key from a superseded generation/epoch was presented."),
        ReasonSpec("PK_BYPASS_AUTH_FAILED", Outcome.REJECTED_POLICY, Retryability.NOT_RETRYABLE, True,
                   "Caller/peer/provider identity could not be authenticated."),
        ReasonSpec("PK_BYPASS_UNAUTHORIZED", Outcome.REJECTED_POLICY, Retryability.NOT_RETRYABLE, True,
                   "Authenticated principal lacks the required capability/scope."),
        ReasonSpec("PK_BYPASS_POLICY_REJECTED", Outcome.REJECTED_POLICY, Retryability.NOT_RETRYABLE, True,
                   "A precedence/constraint policy rejected the operation."),
        ReasonSpec("PK_BYPASS_PROVIDER_RESET", Outcome.RETRYABLE_FAILURE, Retryability.RETRY_AFTER_RECONCILIATION, True,
                   "Provider/device reset; queue/registration state must be re-verified."),
        ReasonSpec("PK_BYPASS_TIMEOUT", Outcome.RETRYABLE_FAILURE, Retryability.RETRY_WITH_IDEMPOTENCY_KEY, True,
                   "Operation deadline elapsed before a completion was observed."),
        ReasonSpec("PK_BYPASS_UNAVAILABLE", Outcome.DEGRADED, Retryability.SAFE, True,
                   "Bypass path unavailable and fallback disabled by policy."),
    )
}

# C014-T02: every reference-model error code MUST map into the outcome model.
ERROR_CODE_TO_REASON: Final[dict[str, str]] = {
    OutOfBounds.code: "PK_BYPASS_OUT_OF_BOUNDS",
    NotRegistered.code: "PK_BYPASS_NOT_REGISTERED",
    RegionBusy.code: "PK_BYPASS_REGION_BUSY",
    RingFull.code: "PK_BYPASS_RING_FULL",
    CompletionRingFull.code: "PK_BYPASS_COMPLETION_RING_FULL",
    RegionLimitReached.code: "PK_BYPASS_REGION_LIMIT",
    BypassError.code: "PK_BYPASS_POLICY_REJECTED",  # generic base -> conservative terminal-ish
}


@dataclass(frozen=True, slots=True)
class OperationResult:
    """The external, wire-stable result of a single operation."""

    reason_code: str
    outcome: Outcome
    retryability: Retryability
    bytes_completed: int = 0
    detail: str = ""

    def to_public(self) -> dict:
        """Tenant-safe projection: never leak internal-only reasons."""
        spec = REASONS[self.reason_code]
        code = self.reason_code if spec.tenant_safe else "PK_BYPASS_INTERNAL"
        return {
            "schema": OUTCOME_SCHEMA_VERSION,
            "outcome": self.outcome.value,
            "reason_code": code,
            "retryable": self.retryability is not Retryability.NOT_RETRYABLE,
            "bytes_completed": self.bytes_completed,
        }


def classify_error(exc: BaseException) -> OperationResult:
    """Map a raised model error into a stable OperationResult (C014-T02/T05)."""
    code = getattr(exc, "code", None)
    reason = ERROR_CODE_TO_REASON.get(code or "", "PK_BYPASS_POLICY_REJECTED")
    spec = REASONS[reason]
    return OperationResult(reason, spec.outcome, spec.retryability, detail=str(exc))


def result_for(reason_code: str, *, bytes_completed: int = 0, detail: str = "") -> OperationResult:
    spec = REASONS[reason_code]
    return OperationResult(reason_code, spec.outcome, spec.retryability, bytes_completed, detail)
