"""Explicit lifecycle state machines (checklist #7).

Transitions not listed are rejected with ``IllegalTransition``; every state
machine is data, so the table is also emitted into the requirements docs.
"""
from __future__ import annotations

LEASE = {
    "ISSUED": {"ACTIVE"},
    "ACTIVE": {"RENEWED", "EXPIRED", "REVOKED", "VERSION_RETIRED"},
    "RENEWED": {"ACTIVE"},
    "EXPIRED": set(), "REVOKED": set(), "VERSION_RETIRED": set(),
}
VERSION = {
    "STAGED": {"CURRENT", "DISCARDED"},
    "CURRENT": {"PREVIOUS"},
    "PREVIOUS": {"RETIRED"},
    "RETIRED": {"DESTROYED"},
    "DISCARDED": set(), "DESTROYED": set(),
}
PROVIDER = {
    "UNINITIALISED": {"CONNECTING"},
    "CONNECTING": {"HEALTHY", "UNAVAILABLE"},
    "HEALTHY": {"DEGRADED", "UNAVAILABLE", "QUARANTINED"},
    "DEGRADED": {"HEALTHY", "UNAVAILABLE", "QUARANTINED"},
    "UNAVAILABLE": {"CONNECTING", "QUARANTINED"},
    "QUARANTINED": {"CONNECTING"},
}
MACHINES = {"lease": LEASE, "version": VERSION, "provider": PROVIDER}


class IllegalTransition(ValueError):
    pass


class StateMachine:
    def __init__(self, table: dict[str, set[str]], initial: str):
        if initial not in table:
            raise IllegalTransition(f"unknown initial state {initial!r}")
        self.table, self.state, self.history = table, initial, [initial]

    def to(self, new: str) -> str:
        if new not in self.table.get(self.state, set()):
            raise IllegalTransition(f"{self.state} -> {new} is not permitted")
        self.state = new
        self.history.append(new)
        return new

    @property
    def terminal(self) -> bool:
        return not self.table[self.state]
