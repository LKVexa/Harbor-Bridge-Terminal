"""Queue lifecycle, degraded modes, quarantine and controller fencing.

Covers INV-35-C015 (state machine), C055 (failover invariants), C056 (degraded
modes), C058 (stale-controller fencing) and C059 (runtime quarantine/freeze/
disable that acts on live queues rather than on registry membership).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
import time

from .errors import Inv35Error


class State(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    SERVING = "serving"
    DEGRADED = "degraded"
    DRAINING = "draining"
    FROZEN = "frozen"          # operator hold: no new admission, completions allowed
    QUARANTINED = "quarantined"  # security hold: no admission, no completion side effects
    DISABLED = "disabled"      # emergency disable: terminal until re-created
    STOPPED = "stopped"


class DegradedMode(str, Enum):
    NONE = "none"
    NO_SUPPRESSION = "no_notification_suppression"  # always notify; safe, slower
    REDUCED_DEPTH = "reduced_depth"                 # admission capped below QUEUE_DEPTH
    CONTROL_PLANE_UNREACHABLE = "control_plane_unreachable"  # keep serving with last-good config


#: Legal transitions. Anything absent is refused with INV35-E400.
TRANSITIONS: dict[State, frozenset[State]] = {
    State.CREATED: frozenset({State.STARTING, State.DISABLED}),
    State.STARTING: frozenset({State.SERVING, State.STOPPED, State.DISABLED, State.QUARANTINED}),
    State.SERVING: frozenset({State.DEGRADED, State.DRAINING, State.FROZEN, State.QUARANTINED, State.DISABLED}),
    State.DEGRADED: frozenset({State.SERVING, State.DRAINING, State.FROZEN, State.QUARANTINED, State.DISABLED}),
    State.DRAINING: frozenset({State.STOPPED, State.QUARANTINED, State.DISABLED}),
    State.FROZEN: frozenset({State.SERVING, State.DRAINING, State.QUARANTINED, State.DISABLED}),
    State.QUARANTINED: frozenset({State.DISABLED, State.STOPPED}),  # never straight back to serving
    State.DISABLED: frozenset(),
    State.STOPPED: frozenset(),
}

ADMITTING = frozenset({State.SERVING, State.DEGRADED})
COMPLETING = frozenset({State.SERVING, State.DEGRADED, State.DRAINING, State.FROZEN})


@dataclass
class Lifecycle:
    """Per-queue lifecycle with an append-only transition history."""

    queue: str
    state: State = State.CREATED
    degraded_mode: DegradedMode = DegradedMode.NONE
    controller_epoch: int = 0
    history: list[dict[str, object]] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, repr=False, compare=False)

    def transition(self, target: State, *, reason: str, actor: str, epoch: int | None = None,
                   mode: DegradedMode | None = None) -> dict[str, object]:
        if not reason or not actor:
            raise Inv35Error("INV35-E400", "transitions require a reason and an actor")
        with self._lock:
            self._check_epoch(epoch)
            if target not in TRANSITIONS[self.state]:
                raise Inv35Error("INV35-E400", f"{self.queue}: {self.state.value} -> {target.value} is illegal")
            if target is State.DEGRADED:
                if mode is None or mode is DegradedMode.NONE:
                    raise Inv35Error("INV35-E400", "entering DEGRADED requires a declared degraded mode")
                self.degraded_mode = mode
            elif target is State.SERVING:
                self.degraded_mode = DegradedMode.NONE
            record = {
                "queue": self.queue,
                "from": self.state.value,
                "to": target.value,
                "mode": self.degraded_mode.value,
                "reason": reason,
                "actor": actor,
                "epoch": self.controller_epoch,
                "at": time.time(),
            }
            self.state = target
            self.history.append(record)
            return record

    # -- controller fencing (C058) ------------------------------------------
    def claim(self, epoch: int, actor: str) -> None:
        """A controller takes ownership with a strictly increasing epoch."""
        with self._lock:
            if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch <= self.controller_epoch:
                raise Inv35Error("INV35-E307", f"epoch {epoch!r} <= current {self.controller_epoch}")
            self.controller_epoch = epoch
            self.history.append({"queue": self.queue, "claim": epoch, "actor": actor, "at": time.time()})

    def _check_epoch(self, epoch: int | None) -> None:
        if epoch is not None and epoch != self.controller_epoch:
            raise Inv35Error("INV35-E307", f"command epoch {epoch} != owner epoch {self.controller_epoch}")

    # -- admission gates -----------------------------------------------------
    def require_admitting(self) -> None:
        if self.state in ADMITTING:
            return
        if self.state is State.QUARANTINED:
            raise Inv35Error("INV35-E402", self.queue)
        if self.state in (State.DISABLED, State.STOPPED):
            raise Inv35Error("INV35-E403", self.queue)
        raise Inv35Error("INV35-E401", f"{self.queue} is {self.state.value}")

    def require_completing(self) -> None:
        if self.state in COMPLETING:
            return
        if self.state is State.QUARANTINED:
            raise Inv35Error("INV35-E402", self.queue)
        raise Inv35Error("INV35-E403" if self.state in (State.DISABLED, State.STOPPED) else "INV35-E401",
                         f"{self.queue} is {self.state.value}")


def state_machine_document() -> dict[str, object]:
    return {
        "schema": "INV35_LIFECYCLE/1",
        "states": [s.value for s in State],
        "degraded_modes": [m.value for m in DegradedMode],
        "transitions": {s.value: sorted(t.value for t in targets) for s, targets in TRANSITIONS.items()},
        "admitting": sorted(s.value for s in ADMITTING),
        "completing": sorted(s.value for s in COMPLETING),
    }
