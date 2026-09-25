"""Lifecycle state model + emergency-disable policy (components P1-14, P1-12).

States: ENABLED, DEPRECATED, DRAINING, DISABLED, MIGRATING, FAILED, QUARANTINED.
Only the transitions in ``TRANSITIONS`` are legal; everything else is refused with
``PK_POLL_ILLEGAL_TRANSITION`` and leaves the state unchanged.  The machine
artifact is ``schemas/pk_poll_lifecycle.json`` and is checked against this table
by the contract tests.

Admission rule per state (``admits_new_polls``):
  ENABLED, DEPRECATED, MIGRATING -> new legacy polls admitted (with deprecation)
  DRAINING -> new polls refused (PK_POLL_DRAINING); in-flight polls finish
  DISABLED, FAILED, QUARANTINED -> refused (PK_POLL_DISABLED / _FAILED / _QUARANTINED)
Emergency disable = transition to DRAINING, then DISABLED once in-flight == 0.
Rollback = DISABLED -> DEPRECATED (re-enable), recorded with actor and reason.
"""
from __future__ import annotations

import threading
import time

try:
    from .errors import Inv14Error
except ImportError:
    from errors import Inv14Error

STATES = ("ENABLED", "DEPRECATED", "DRAINING", "DISABLED", "MIGRATING", "FAILED", "QUARANTINED")
TRANSITIONS = {
    "ENABLED": {"DEPRECATED", "DRAINING", "FAILED", "QUARANTINED"},
    "DEPRECATED": {"MIGRATING", "DRAINING", "FAILED", "QUARANTINED"},
    "MIGRATING": {"DEPRECATED", "DRAINING", "FAILED", "QUARANTINED"},
    "DRAINING": {"DISABLED", "DEPRECATED", "FAILED", "QUARANTINED"},
    "DISABLED": {"DEPRECATED", "QUARANTINED"},
    "FAILED": {"DRAINING", "QUARANTINED", "DEPRECATED"},
    "QUARANTINED": {"DISABLED"},
}
ADMITTING = {"ENABLED", "DEPRECATED", "MIGRATING"}
REFUSAL_CODE = {"DRAINING": "PK_POLL_DRAINING", "DISABLED": "PK_POLL_DISABLED",
                "FAILED": "PK_POLL_FAILED_STATE", "QUARANTINED": "PK_POLL_QUARANTINED"}
MAX_HISTORY = 128


class LifecycleError(Inv14Error):
    default_code = "PK_POLL_ILLEGAL_TRANSITION"


class Lifecycle:
    def __init__(self, initial: str = "DEPRECATED", *, clock=time.time):
        if initial not in STATES:
            raise LifecycleError("unknown state", code="PK_POLL_UNKNOWN_STATE")
        self._cv = threading.Condition()
        self._state, self._clock = initial, clock
        self._in_flight = 0
        self._history = [{"to": initial, "actor": "init", "reason": "initial", "at": clock()}]

    @property
    def state(self) -> str:
        with self._cv:
            return self._state

    def transition(self, to: str, *, actor: str, reason: str) -> dict:
        if not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or not reason.strip():
            raise LifecycleError("actor and reason are required", code="PK_POLL_TRANSITION_UNATTRIBUTED")
        with self._cv:
            if to not in STATES:
                raise LifecycleError("unknown state", code="PK_POLL_UNKNOWN_STATE")
            if to == self._state:
                return {"from": to, "to": to, "idempotent": True}
            if to not in TRANSITIONS[self._state]:
                raise LifecycleError("illegal lifecycle transition",
                                     details={"from": self._state, "to": to})
            if to == "DISABLED" and self._in_flight:
                raise LifecycleError("cannot disable while polls are in flight; drain first",
                                     code="PK_POLL_DRAIN_INCOMPLETE", details={"in_flight": self._in_flight})
            rec = {"from": self._state, "to": to, "actor": actor[:64], "reason": reason[:256], "at": self._clock()}
            self._state = to
            self._history.append(rec)
            del self._history[:-MAX_HISTORY]
            self._cv.notify_all()
            return dict(rec)

    def enter(self) -> None:
        with self._cv:
            if self._state not in ADMITTING:
                raise LifecycleError("legacy polls are not admitted in state " + self._state,
                                     code=REFUSAL_CODE[self._state], details={"state": self._state})
            self._in_flight += 1

    def exit(self) -> None:
        with self._cv:
            if self._in_flight <= 0:
                raise LifecycleError("exit without enter", code="PK_POLL_LIFECYCLE_STATE")
            self._in_flight -= 1
            self._cv.notify_all()

    def in_flight(self) -> int:
        with self._cv:
            return self._in_flight

    def emergency_disable(self, *, actor: str, reason: str, drain_seconds: float = 60.0) -> dict:
        """Refuse new polls immediately, wait (bounded) for in-flight to drain, then disable."""
        if self.state not in ("DRAINING", "DISABLED"):
            self.transition("DRAINING", actor=actor, reason=reason)
        deadline = time.monotonic() + max(0.0, min(drain_seconds, 60.0))
        with self._cv:
            while self._in_flight and time.monotonic() < deadline:
                self._cv.wait(deadline - time.monotonic())
            drained = self._in_flight == 0
        if drained and self.state == "DRAINING":
            self.transition("DISABLED", actor=actor, reason=reason + " (drained)")
        return {"state": self.state, "drained": drained, "in_flight": self.in_flight()}

    def history(self) -> list:
        with self._cv:
            return [dict(h) for h in self._history]
