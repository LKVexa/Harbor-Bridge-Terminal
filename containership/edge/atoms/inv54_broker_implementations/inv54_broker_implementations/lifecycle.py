"""Broker/adapter lifecycle state machine (component 06) and quarantine control (58)."""
from __future__ import annotations

from enum import Enum
from threading import RLock
from typing import Callable

from .errors import ILLEGAL_STATE, QUARANTINED, BrokerError


class State(str, Enum):
    CREATED = "created"
    CONFIGURED = "configured"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    DRAINING = "draining"
    QUARANTINED = "quarantined"
    STOPPED = "stopped"
    FAILED = "failed"


# Legal transitions.  Anything not listed is illegal and raises INV54-E0601.
TRANSITIONS: dict[State, frozenset[State]] = {
    State.CREATED: frozenset({State.CONFIGURED, State.FAILED}),
    State.CONFIGURED: frozenset({State.CONFIGURED, State.STARTING, State.STOPPED, State.FAILED}),
    State.STARTING: frozenset({State.READY, State.DEGRADED, State.FAILED, State.STOPPED}),
    State.READY: frozenset({State.DEGRADED, State.DRAINING, State.QUARANTINED, State.FAILED}),
    State.DEGRADED: frozenset({State.READY, State.DRAINING, State.QUARANTINED, State.FAILED}),
    State.DRAINING: frozenset({State.STOPPED, State.FAILED}),
    State.QUARANTINED: frozenset({State.READY, State.DRAINING, State.STOPPED, State.FAILED}),
    State.STOPPED: frozenset({State.CONFIGURED}),
    State.FAILED: frozenset({State.STOPPED}),
}

ACCEPTS_WRITES = frozenset({State.READY, State.DEGRADED})
ACCEPTS_READS = frozenset({State.READY, State.DEGRADED, State.DRAINING, State.QUARANTINED})


class Lifecycle:
    def __init__(self, on_transition: Callable[[State, State, str], None] | None = None) -> None:
        self._state = State.CREATED
        self._lock = RLock()
        self._hook = on_transition
        self.history: list[tuple[str, str, str]] = []

    @property
    def state(self) -> State:
        return self._state

    def transition(self, to: State, reason: str) -> None:
        with self._lock:
            frm = self._state
            if to not in TRANSITIONS[frm]:
                raise BrokerError(ILLEGAL_STATE, f"illegal transition {frm.value}->{to.value}",
                                  from_state=frm.value, to_state=to.value)
            self._state = to
            if len(self.history) >= 256:
                del self.history[0]
            self.history.append((frm.value, to.value, reason))
        if self._hook:
            self._hook(frm, to, reason)

    def require_writable(self) -> None:
        s = self._state
        if s is State.QUARANTINED:
            raise BrokerError(QUARANTINED, "broker is quarantined; writes frozen")
        if s not in ACCEPTS_WRITES:
            raise BrokerError(ILLEGAL_STATE, f"writes not accepted in state {s.value}", state=s.value)

    def require_readable(self) -> None:
        if self._state not in ACCEPTS_READS:
            raise BrokerError(ILLEGAL_STATE, f"reads not accepted in state {self._state.value}",
                              state=self._state.value)
