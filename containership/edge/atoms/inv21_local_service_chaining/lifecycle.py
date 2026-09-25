"""Explicit lifecycle state machine for the chainer (GAP-011, GAP-031).

States: initializing -> ready <-> degraded; any live state -> quarantined
(emergency disable: refuses every call, local and remote); quarantined ->
ready only through an explicit, attributed ``release``; any -> stopped
(terminal). Illegal transitions raise and leave state unchanged.
"""
from __future__ import annotations

import threading
import time

from .errors import NotReady, Quarantined, ValidationFailed

STATES = ("initializing", "ready", "degraded", "quarantined", "stopped")
TRANSITIONS = {
    "initializing": {"ready", "stopped", "quarantined"},
    "ready": {"degraded", "quarantined", "stopped"},
    "degraded": {"ready", "quarantined", "stopped"},
    "quarantined": {"ready", "stopped"},
    "stopped": set(),
}
SERVING = {"ready", "degraded"}
MAX_HISTORY = 64


class Lifecycle:
    def __init__(self, initial: str = "initializing") -> None:
        if initial not in STATES:
            raise ValidationFailed("unknown lifecycle state", state=initial)
        self._state = initial
        self._lock = threading.Lock()
        self.history: list = [(time.time(), None, initial, "init", "system")]

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def transition(self, to: str, *, reason: str, actor: str = "system") -> None:
        if to not in STATES:
            raise ValidationFailed("unknown lifecycle state", state=to)
        with self._lock:
            if to not in TRANSITIONS[self._state]:
                raise ValidationFailed(f"illegal transition {self._state}->{to}", state=self._state)
            self.history.append((time.time(), self._state, to, reason[:128], actor[:64]))
            del self.history[:-MAX_HISTORY]
            self._state = to

    def require_serving(self) -> None:
        s = self.state
        if s == "quarantined":
            raise Quarantined("chainer quarantined (emergency disable)", state=s)
        if s not in SERVING:
            raise NotReady("chainer not serving", state=s)
