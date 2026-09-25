"""Explicit provider and link lifecycle state machines (M11).

Illegal transitions raise; every transition is recorded (and audited by the
service).  ``revoked`` is terminal for a link generation: re-linking creates a
new generation with a higher config version.
"""
from __future__ import annotations

import threading

from ..errors.mapping import ProviderFault

PROVIDER_STATES = ("starting", "ready", "degraded", "draining", "disabled", "failed", "stopped")
PROVIDER_TRANSITIONS = {
    "starting": {"ready", "failed", "stopped"},
    "ready": {"degraded", "draining", "disabled", "failed", "stopped"},
    "degraded": {"ready", "draining", "disabled", "failed", "stopped"},
    "draining": {"stopped", "disabled", "ready"},
    "disabled": {"ready", "stopped"},
    "failed": {"starting", "stopped"},
    "stopped": {"starting"},
}
LINK_STATES = ("pending", "active", "suspended", "draining", "revoked")
LINK_TRANSITIONS = {
    "pending": {"active", "revoked"},
    "active": {"suspended", "draining", "revoked", "active"},  # active->active = config update
    "suspended": {"active", "revoked"},
    "draining": {"revoked", "active"},
    "revoked": set(),
}
SERVING_PROVIDER = {"ready", "degraded"}
SERVING_LINK = {"active"}


class StateMachine:
    def __init__(self, name: str, transitions: dict, initial: str):
        self.name, self._t, self.state = name, transitions, initial
        self.history: list[tuple[str, str, str]] = []
        self._lock = threading.Lock()

    def to(self, new: str, reason: str = "") -> str:
        with self._lock:
            if new not in self._t.get(self.state, set()):
                raise ProviderFault("PK_PROVIDER_INVALID_LINK", f"{self.name}: illegal transition {self.state} -> {new}")
            old, self.state = self.state, new
            self.history.append((old, new, reason[:128]))
            return old


def provider_machine() -> StateMachine:
    return StateMachine("provider", PROVIDER_TRANSITIONS, "starting")


def link_machine() -> StateMachine:
    return StateMachine("link", LINK_TRANSITIONS, "pending")
