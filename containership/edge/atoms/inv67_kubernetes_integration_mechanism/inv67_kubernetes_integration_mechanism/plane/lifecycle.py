"""Canonical lifecycle state machine and error taxonomy (checklist item 04).

Desired state (the WasmWorkload spec), observed Kubernetes state, downstream
runtime state and projected status are kept separate. The reconciler is the only
writer of ``status``; the runtime adapter is authoritative for runtime state; on
disagreement the projected phase becomes ``Unknown``/``Degraded`` rather than
guessing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class State(str, Enum):
    REQUESTED = "Requested"
    VALIDATING = "Validating"
    ADMITTED = "Admitted"
    QUEUED = "Queued"
    PLACED = "Placed"
    STARTING = "Starting"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    DELETING = "Deleting"
    DEGRADED = "Degraded"
    BLOCKED = "Blocked"
    UNKNOWN = "Unknown"


TERMINAL = frozenset({State.SUCCEEDED, State.FAILED, State.CANCELLED})

_T = {
    State.REQUESTED: {State.VALIDATING, State.DELETING},
    State.VALIDATING: {State.ADMITTED, State.BLOCKED, State.FAILED, State.DELETING},
    State.ADMITTED: {State.QUEUED, State.DELETING, State.BLOCKED},
    State.QUEUED: {State.PLACED, State.BLOCKED, State.DEGRADED, State.DELETING, State.FAILED},
    State.PLACED: {State.STARTING, State.FAILED, State.DELETING, State.UNKNOWN, State.DEGRADED},
    State.STARTING: {State.RUNNING, State.FAILED, State.DELETING, State.UNKNOWN, State.DEGRADED},
    State.RUNNING: {State.SUCCEEDED, State.FAILED, State.DELETING, State.UNKNOWN, State.DEGRADED},
    State.DEGRADED: {State.QUEUED, State.PLACED, State.STARTING, State.RUNNING, State.FAILED,
                     State.DELETING, State.UNKNOWN, State.BLOCKED},
    State.UNKNOWN: {State.PLACED, State.STARTING, State.RUNNING, State.SUCCEEDED, State.FAILED,
                    State.DELETING, State.DEGRADED},
    State.BLOCKED: {State.VALIDATING, State.DELETING},
    State.SUCCEEDED: {State.DELETING},
    State.FAILED: {State.DELETING, State.VALIDATING},  # VALIDATING only on a new generation
    State.CANCELLED: {State.DELETING},
    State.DELETING: {State.CANCELLED},
}


class IllegalTransition(Exception):
    code = "INV67_ILLEGAL_TRANSITION"


def legal(src: State, dst: State) -> bool:
    return src == dst or dst in _T.get(src, set())


def transition(src: State, dst: State) -> State:
    if not legal(src, dst):
        raise IllegalTransition(f"{src.value} -> {dst.value}")
    return dst


def transition_table() -> list[tuple[str, str, bool]]:
    """Every (src, dst) pair with its legality, for model-based tests and docs."""
    return [(a.value, b.value, legal(a, b)) for a in State for b in State]


# Pod phase projection from lifecycle state (PK_K8S_STATUS/1 enum).
POD_PHASE = {
    State.REQUESTED: "Pending", State.VALIDATING: "Pending", State.ADMITTED: "Pending",
    State.QUEUED: "Pending", State.PLACED: "Pending", State.STARTING: "Pending",
    State.RUNNING: "Running", State.SUCCEEDED: "Succeeded", State.FAILED: "Failed",
    State.CANCELLED: "Failed", State.DELETING: "Unknown", State.DEGRADED: "Unknown",
    State.BLOCKED: "Pending", State.UNKNOWN: "Unknown",
}


class Retry(str, Enum):
    RETRYABLE = "retryable"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class ErrorCode:
    code: str
    retry: Retry
    reason: str


ERRORS = {e.code: e for e in [
    ErrorCode("PK_K8S_UNSUPPORTED_FIELD", Retry.TERMINAL, "UnsupportedField"),
    ErrorCode("PK_K8S_INVALID_POD", Retry.TERMINAL, "InvalidSpec"),
    ErrorCode("INV67_UNAUTHORIZED", Retry.TERMINAL, "Unauthorized"),
    ErrorCode("INV67_INCOMPATIBLE", Retry.TERMINAL, "Incompatible"),
    ErrorCode("INV67_ARTIFACT_UNVERIFIED", Retry.TERMINAL, "ArtifactUnverified"),
    ErrorCode("INV67_QUOTA_EXCEEDED", Retry.RETRYABLE, "QuotaExceeded"),
    ErrorCode("INV67_DOWNSTREAM_UNAVAILABLE", Retry.RETRYABLE, "DownstreamUnavailable"),
    ErrorCode("INV67_CIRCUIT_OPEN", Retry.RETRYABLE, "CircuitOpen"),
    ErrorCode("INV67_OVERLOADED", Retry.RETRYABLE, "Overloaded"),
    ErrorCode("INV67_CONFLICT", Retry.RETRYABLE, "Conflict"),
    ErrorCode("INV67_FROZEN", Retry.RETRYABLE, "Frozen"),
    ErrorCode("INV67_QUARANTINED", Retry.TERMINAL, "Quarantined"),
    ErrorCode("INV67_NOT_LEADER", Retry.RETRYABLE, "NotLeader"),
    ErrorCode("INV67_RUNTIME_FAILED", Retry.TERMINAL, "RuntimeFailed"),
    ErrorCode("INV67_STALE_OBSERVATION", Retry.RETRYABLE, "StaleObservation"),
]}


class PlaneError(Exception):
    """Structured control-plane error with a stable code."""

    def __init__(self, code: str, message: str, **detail):
        if code not in ERRORS:
            raise ValueError(f"unregistered error code {code}")
        super().__init__(message)
        self.code, self.detail = code, detail

    @property
    def retryable(self) -> bool:
        return ERRORS[self.code].retry is Retry.RETRYABLE

    @property
    def reason(self) -> str:
        return ERRORS[self.code].reason

    def to_dict(self) -> dict:
        return {"code": self.code, "reason": self.reason, "message": str(self),
                "retryable": self.retryable, "detail": self.detail}


def attempt_id(uid: str, generation: int, attempt: int) -> str:
    """Stable id so retries and stale status are never mistaken for the current run."""
    return f"{uid}/g{generation}/a{attempt}"


def aggregate_units(unit_states: list[State]) -> State:
    """Partial-success semantics for multi-unit workloads."""
    if not unit_states:
        return State.UNKNOWN
    s = set(unit_states)
    if State.FAILED in s:
        return State.FAILED
    if State.UNKNOWN in s:
        return State.UNKNOWN
    if s == {State.SUCCEEDED}:
        return State.SUCCEEDED
    if State.RUNNING in s and s <= {State.RUNNING, State.SUCCEEDED}:
        return State.RUNNING
    if State.DEGRADED in s:
        return State.DEGRADED
    order = [State.STARTING, State.PLACED, State.QUEUED]
    for st in order:
        if st in s:
            return st
    return State.UNKNOWN
