"""MC-006 — enforced production lifecycle state machine.

    CREATED -> APPLYING -> VERIFYING -> READY -> RUNNING -> TERMINATING -> CLEANED
    any non-terminal state -> FAILED -> CLEANED
    READY/RUNNING -> QUARANTINED -> TERMINATING

Exec is only reachable from READY, and READY only from VERIFYING, so no workload
instruction can run before verification (pre-exec containment invariant).
Every transition is recorded with a reason (MC-080).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .errors import SandboxError

STATES = ("CREATED", "APPLYING", "VERIFYING", "READY", "RUNNING", "TERMINATING",
          "QUARANTINED", "FAILED", "CLEANED")
TRANSITIONS: dict[str, frozenset[str]] = {
    "CREATED": frozenset({"APPLYING", "FAILED"}),
    "APPLYING": frozenset({"VERIFYING", "FAILED"}),
    "VERIFYING": frozenset({"READY", "FAILED"}),
    "READY": frozenset({"RUNNING", "QUARANTINED", "FAILED", "TERMINATING"}),
    "RUNNING": frozenset({"TERMINATING", "QUARANTINED", "FAILED"}),
    "QUARANTINED": frozenset({"TERMINATING"}),
    "TERMINATING": frozenset({"CLEANED", "FAILED"}),
    "FAILED": frozenset({"CLEANED"}),
    "CLEANED": frozenset(),
}
MAX_HISTORY = 64


@dataclass
class Lifecycle:
    sandbox_id: str
    state: str = "CREATED"
    history: list[tuple[float, str, str, str]] = field(default_factory=list)

    def to(self, new: str, reason: str) -> None:
        if new not in TRANSITIONS.get(self.state, ()):
            raise SandboxError("E_STATE_TRANSITION", f"{self.sandbox_id}: {self.state} -> {new} is not permitted")
        if len(self.history) < MAX_HISTORY:
            self.history.append((time.time(), self.state, new, reason[:256]))
        self.state = new

    def require(self, *states: str) -> None:
        if self.state not in states:
            raise SandboxError("E_STATE_TRANSITION", f"{self.sandbox_id}: in {self.state}, need one of {states}")

    @property
    def terminal(self) -> bool:
        return self.state == "CLEANED"
