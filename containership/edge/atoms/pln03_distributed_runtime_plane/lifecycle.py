"""Runtime/adapter lifecycle state machine and quarantine controls (MC-006, MC-042)."""
from __future__ import annotations

from enum import Enum
from threading import RLock
from typing import Callable

from .runtime import RuntimePlaneError


class State(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    DRAINING = "draining"
    FROZEN = "frozen"          # operator freeze: reads allowed, writes refused
    QUARANTINED = "quarantined"  # isolated: all calls refused
    STOPPED = "stopped"
    FAILED = "failed"


LEGAL: dict[State, frozenset[State]] = {
    State.CREATED: frozenset({State.STARTING, State.STOPPED}),
    State.STARTING: frozenset({State.READY, State.FAILED, State.STOPPED}),
    State.READY: frozenset({State.DEGRADED, State.DRAINING, State.FROZEN, State.QUARANTINED, State.FAILED}),
    State.DEGRADED: frozenset({State.READY, State.DRAINING, State.FROZEN, State.QUARANTINED, State.FAILED}),
    State.FROZEN: frozenset({State.READY, State.DRAINING, State.QUARANTINED}),
    State.QUARANTINED: frozenset({State.DRAINING, State.STOPPED}),
    State.DRAINING: frozenset({State.STOPPED}),
    State.FAILED: frozenset({State.STARTING, State.STOPPED}),
    State.STOPPED: frozenset(),
}

SERVES_READS = {State.READY, State.DEGRADED, State.FROZEN}
SERVES_WRITES = {State.READY, State.DEGRADED}


class LifecycleRefused(RuntimePlaneError):
    code = "PK_LIFECYCLE_REFUSED"


class Quarantined(RuntimePlaneError):
    code = "PK_QUARANTINED"


class Lifecycle:
    def __init__(self, name: str, on_transition: Callable[[str, State, State, str, str], None] | None = None):
        self.name = name
        self._state = State.CREATED
        self._lock = RLock()
        self._on_transition = on_transition
        self.history: list[tuple[State, State, str, str]] = []

    @property
    def state(self) -> State:
        return self._state

    def transition(self, target: State, *, actor: str, reason: str) -> None:
        if not actor or not reason:
            raise LifecycleRefused("transitions require an actor and a reason")
        with self._lock:
            src = self._state
            if target not in LEGAL[src]:
                raise LifecycleRefused(f"illegal transition {src.value} -> {target.value}",
                                       component=self.name, src=src.value, dst=target.value)
            self._state = target
            self.history.append((src, target, actor, reason))
        if self._on_transition:
            self._on_transition(self.name, src, target, actor, reason)

    def require(self, write: bool) -> None:
        s = self._state
        if s is State.QUARANTINED:
            raise Quarantined(f"{self.name} is quarantined", component=self.name)
        allowed = SERVES_WRITES if write else SERVES_READS
        if s not in allowed:
            raise LifecycleRefused(f"{self.name} is {s.value}; {'write' if write else 'read'} refused",
                                   component=self.name, state=s.value)
