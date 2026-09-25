"""Deployment lifecycle state machine (INV-63-C015)."""
from __future__ import annotations

from enum import Enum

from .errors import DeploymentError, ErrorCode


class State(str, Enum):
    PENDING = "PENDING"            # desired state accepted, not yet validated against topology
    VALIDATED = "VALIDATED"        # admission + policy passed
    RECONCILING = "RECONCILING"    # diff being applied
    CONVERGED = "CONVERGED"        # actual == desired; reconcile is a no-op
    ROLLING_OUT = "ROLLING_OUT"    # bounded version change in progress
    DEGRADED = "DEGRADED"          # running below desired (capacity/offline); retried
    ROLLING_BACK = "ROLLING_BACK"  # automatic or operator rollback in progress
    FAILED = "FAILED"              # terminal failure; operator action required
    QUARANTINED = "QUARANTINED"    # unsafe behaviour isolated; no automated actions
    FROZEN = "FROZEN"              # operator freeze; no automated actions
    DELETED = "DELETED"            # desired count 0 and all instances stopped


S = State
TRANSITIONS: dict[State, frozenset[State]] = {
    S.PENDING: frozenset({S.VALIDATED, S.FAILED, S.DELETED}),
    S.VALIDATED: frozenset({S.RECONCILING, S.ROLLING_OUT, S.FAILED, S.FROZEN, S.QUARANTINED}),
    S.RECONCILING: frozenset({S.CONVERGED, S.DEGRADED, S.FAILED, S.QUARANTINED, S.FROZEN}),
    S.CONVERGED: frozenset({S.VALIDATED, S.RECONCILING, S.ROLLING_OUT, S.ROLLING_BACK, S.DEGRADED, S.FROZEN, S.QUARANTINED, S.DELETED}),
    S.ROLLING_OUT: frozenset({S.CONVERGED, S.ROLLING_BACK, S.DEGRADED, S.FAILED, S.FROZEN, S.QUARANTINED}),
    S.DEGRADED: frozenset({S.RECONCILING, S.CONVERGED, S.ROLLING_BACK, S.FAILED, S.FROZEN, S.QUARANTINED, S.VALIDATED}),
    S.ROLLING_BACK: frozenset({S.RECONCILING, S.CONVERGED, S.DEGRADED, S.FAILED, S.QUARANTINED}),
    S.FAILED: frozenset({S.VALIDATED, S.QUARANTINED, S.FROZEN, S.DELETED}),
    S.QUARANTINED: frozenset({S.FROZEN, S.VALIDATED}),   # release requires operator
    S.FROZEN: frozenset({S.VALIDATED, S.QUARANTINED}),
    S.DELETED: frozenset({S.PENDING, S.VALIDATED}),
}


def check_transition(src: State, dst: State) -> None:
    if dst not in TRANSITIONS[src]:
        raise DeploymentError(ErrorCode.ILLEGAL_TRANSITION, f"{src.value} -> {dst.value} is not a legal transition",
                              {"from": src.value, "to": dst.value})


class Lifecycle:
    """Per-(tenant, component) lifecycle tracker with transition history."""

    def __init__(self) -> None:
        self._state: dict[tuple[str, str], State] = {}
        self.history: list[tuple[str, str, str, str, str]] = []

    def get(self, tenant: str, component: str) -> State | None:
        return self._state.get((tenant, component))

    def move(self, tenant: str, component: str, dst: State, reason: str) -> State:
        key = (tenant, component)
        src = self._state.get(key)
        if src is None:
            if dst is not State.PENDING:
                raise DeploymentError(ErrorCode.ILLEGAL_TRANSITION, f"new workload must start in PENDING, not {dst.value}")
        elif src is not dst:
            check_transition(src, dst)
        self._state[key] = dst
        self.history.append((tenant, component, src.value if src else "-", dst.value, reason))
        return dst

    def restore(self, tenant: str, component: str, state: State) -> None:
        """Replay path: trust journaled states (already transition-checked at write)."""
        self._state[(tenant, component)] = state
