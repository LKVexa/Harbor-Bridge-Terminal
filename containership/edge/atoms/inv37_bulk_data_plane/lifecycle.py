"""Transfer lifecycle state machine (INV-37-C015).

The transition table is the single source of truth; SEMANTICS.md is generated
from ``TRANSITIONS`` by ``tools/render_semantics.py`` and tests assert every
(state, event) pair not in the table is refused with ``illegal_transition``.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .errors import IllegalTransition


class Lifecycle(str, Enum):
    CREATED = "created"
    VALIDATING = "validating"
    READY = "ready"
    RECEIVING = "receiving"
    DISCONNECTED = "disconnected"
    COMPLETE_UNVERIFIED = "complete_unverified"
    VERIFIED = "verified"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    QUARANTINED = "quarantined"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    CLOSING = "closing"
    CLOSED = "closed"


class Event(str, Enum):
    VALIDATE = "validate"
    VALIDATED = "validated"
    REJECT = "reject"
    CHUNK = "chunk"
    ALL_CHUNKS = "all_chunks"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"
    VERIFY_OK = "verify_ok"
    VERIFY_FAIL = "verify_fail"
    RETRYABLE_ERROR = "retryable_error"
    RETRY = "retry"
    TERMINAL_ERROR = "terminal_error"
    QUARANTINE = "quarantine"
    RELEASE = "release"
    CANCEL = "cancel"
    CANCEL_DONE = "cancel_done"
    CLOSE = "close"
    CLOSE_DONE = "close_done"


L, E = Lifecycle, Event
_ACTIVE = (L.READY, L.RECEIVING, L.DISCONNECTED, L.COMPLETE_UNVERIFIED, L.FAILED_RETRYABLE)

TRANSITIONS: dict[tuple[Lifecycle, Event], Lifecycle] = {
    (L.CREATED, E.VALIDATE): L.VALIDATING,
    (L.VALIDATING, E.VALIDATED): L.READY,
    (L.VALIDATING, E.REJECT): L.FAILED_TERMINAL,
    (L.READY, E.CHUNK): L.RECEIVING,
    (L.READY, E.ALL_CHUNKS): L.COMPLETE_UNVERIFIED,   # zero-length objects
    (L.RECEIVING, E.CHUNK): L.RECEIVING,
    (L.RECEIVING, E.ALL_CHUNKS): L.COMPLETE_UNVERIFIED,
    (L.RECEIVING, E.DISCONNECT): L.DISCONNECTED,
    (L.READY, E.DISCONNECT): L.DISCONNECTED,
    (L.DISCONNECTED, E.RECONNECT): L.RECEIVING,
    (L.RECEIVING, E.RETRYABLE_ERROR): L.FAILED_RETRYABLE,
    (L.FAILED_RETRYABLE, E.RETRY): L.RECEIVING,
    (L.COMPLETE_UNVERIFIED, E.VERIFY_OK): L.VERIFIED,
    (L.COMPLETE_UNVERIFIED, E.VERIFY_FAIL): L.QUARANTINED,
    (L.QUARANTINED, E.RELEASE): L.FAILED_TERMINAL,
    (L.VERIFIED, E.CLOSE): L.CLOSING,
    (L.FAILED_TERMINAL, E.CLOSE): L.CLOSING,
    (L.CANCELLED, E.CLOSE): L.CLOSING,
    (L.QUARANTINED, E.CLOSE): L.CLOSING,
    (L.CLOSING, E.CLOSE_DONE): L.CLOSED,
    (L.CANCELLING, E.CANCEL_DONE): L.CANCELLED,
}
for _s in _ACTIVE + (L.CREATED, L.VALIDATING):
    TRANSITIONS[(_s, E.CANCEL)] = L.CANCELLING
    TRANSITIONS[(_s, E.TERMINAL_ERROR)] = L.FAILED_TERMINAL
for _s in _ACTIVE + (L.VERIFIED,):
    TRANSITIONS[(_s, E.QUARANTINE)] = L.QUARANTINED

TERMINAL = frozenset({L.CLOSED})
# Idempotent repeats: repeating these events in the resulting state is a no-op.
IDEMPOTENT: dict[Event, frozenset[Lifecycle]] = {
    E.CANCEL: frozenset({L.CANCELLING, L.CANCELLED}),
    E.CLOSE: frozenset({L.CLOSING, L.CLOSED}),
    E.QUARANTINE: frozenset({L.QUARANTINED}),
    E.VERIFY_OK: frozenset({L.VERIFIED}),
}


@dataclass
class StateMachine:
    state: Lifecycle = L.CREATED
    last_event: Event | None = None
    last_reason: str = "created"
    changed_at: float = field(default_factory=time.time)
    history: list[tuple[str, str, str, str]] = field(default_factory=list)
    on_transition: Callable[[Lifecycle, Event, Lifecycle, str], None] | None = None
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def fire(self, event: Event, reason: str = "") -> Lifecycle:
        with self._lock:
            if event in IDEMPOTENT and self.state in IDEMPOTENT[event]:
                return self.state
            target = TRANSITIONS.get((self.state, event))
            if target is None:
                raise IllegalTransition(
                    "illegal lifecycle transition", state=self.state.value, event=event.value
                )
            prior = self.state
            self.state = target
            self.last_event = event
            self.last_reason = reason or event.value
            self.changed_at = time.time()
            self.history.append((prior.value, event.value, target.value, self.last_reason))
            if len(self.history) > 64:
                del self.history[:-64]
            cb = self.on_transition
        if cb:
            cb(prior, event, target, reason)
        return target

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self.state.value,
                "last_event": self.last_event.value if self.last_event else None,
                "last_reason": self.last_reason,
                "changed_at": self.changed_at,
            }


def transition_table() -> list[dict[str, str]]:
    return [
        {"from": s.value, "event": e.value, "to": t.value}
        for (s, e), t in sorted(TRANSITIONS.items(), key=lambda kv: (kv[0][0].value, kv[0][1].value))
    ]
