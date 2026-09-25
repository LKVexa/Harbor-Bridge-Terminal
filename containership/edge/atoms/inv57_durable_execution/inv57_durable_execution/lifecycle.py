"""Workflow lifecycle state machine (MC-05, SG-08).

States and permitted transitions are a closed table.  Every control is
idempotent: re-requesting the state a workflow is already in is a no-op that
returns ``changed=False`` rather than an error, so retried operator calls are
safe.  Terminal states admit no further transition.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import IllegalTransition

LIFECYCLE_SCHEMA = "INV57_LIFECYCLE/1"


class State(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    IN_DOUBT = "in_doubt"          # waiting on reconciliation of an activity
    CANCELLING = "cancelling"      # cooperative cancel requested
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"      # forced, non-cooperative
    TIMED_OUT = "timed_out"
    QUARANTINED = "quarantined"    # integrity failure; operator only


TERMINAL = frozenset({State.COMPLETED, State.FAILED, State.CANCELLED,
                      State.TERMINATED, State.TIMED_OUT})

# (from, control) -> to
_T: dict[tuple[State, str], State] = {
    (State.PENDING, "start"): State.RUNNING,
    (State.PENDING, "cancel"): State.CANCELLED,
    (State.PENDING, "terminate"): State.TERMINATED,
    (State.RUNNING, "suspend"): State.SUSPENDED,
    (State.RUNNING, "complete"): State.COMPLETED,
    (State.RUNNING, "fail"): State.FAILED,
    (State.RUNNING, "cancel"): State.CANCELLING,
    (State.RUNNING, "terminate"): State.TERMINATED,
    (State.RUNNING, "timeout"): State.TIMED_OUT,
    (State.RUNNING, "in_doubt"): State.IN_DOUBT,
    (State.RUNNING, "quarantine"): State.QUARANTINED,
    (State.SUSPENDED, "resume"): State.RUNNING,
    (State.SUSPENDED, "cancel"): State.CANCELLED,
    (State.SUSPENDED, "terminate"): State.TERMINATED,
    (State.SUSPENDED, "timeout"): State.TIMED_OUT,
    (State.IN_DOUBT, "reconcile"): State.RUNNING,
    (State.IN_DOUBT, "terminate"): State.TERMINATED,
    (State.IN_DOUBT, "quarantine"): State.QUARANTINED,
    (State.CANCELLING, "cancelled"): State.CANCELLED,
    (State.CANCELLING, "terminate"): State.TERMINATED,
    (State.QUARANTINED, "release"): State.SUSPENDED,
    (State.QUARANTINED, "terminate"): State.TERMINATED,
}

CONTROLS = frozenset(c for _, c in _T)
OPERATOR_ONLY = frozenset({"terminate", "release", "quarantine", "reconcile"})


@dataclass(frozen=True)
class Transition:
    control: str
    before: State
    after: State
    changed: bool
    reason: str


def transition(current: State, control: str, *, reason: str = "") -> Transition:
    if control not in CONTROLS:
        raise IllegalTransition(f"unknown lifecycle control {control!r}")
    target = _T.get((current, control))
    if target is None:
        # Idempotent re-request of the state already reached.
        for (src, ctl), dst in _T.items():
            if ctl == control and dst == current:
                return Transition(control, current, current, False, reason)
        raise IllegalTransition(f"{control!r} is not permitted from {current.value!r}")
    return Transition(control, current, target, True, reason)


def table() -> list[dict]:
    return [{"from": s.value, "control": c, "to": d.value} for (s, c), d in sorted(
        _T.items(), key=lambda kv: (kv[0][0].value, kv[0][1]))]
