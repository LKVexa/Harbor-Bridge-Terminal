"""Manifest lifecycle state machine (MC-008; C014-C015).

States and the only legal transitions::

    proposed ──► admitted ──► delivery_pending ──► delivered ──► rolled_back
        │            │               │                 │   └───► retired
        └► rejected  └► retired      └► rejected*      └► quarantined ──► delivered (release)
                                                                     └──► retired

``*`` delivery_pending → rejected only when the deployment manager refuses the
manifest permanently (non-retryable).  ``rejected`` and ``retired`` are terminal.
Every transition is journaled (``lifecycle.transition``) by the service before it
becomes visible; an illegal transition raises ``ECP_ILLEGAL_TRANSITION``.
"""
from __future__ import annotations

import threading
from typing import Any

from .errors import EcpError

STATES = ("proposed", "admitted", "rejected", "delivery_pending", "delivered", "rolled_back", "quarantined", "retired")
TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset({"admitted", "rejected"}),
    "admitted": frozenset({"delivery_pending", "retired"}),
    "delivery_pending": frozenset({"delivered", "rejected", "delivery_pending"}),
    "delivered": frozenset({"rolled_back", "quarantined", "retired"}),
    "quarantined": frozenset({"delivered", "retired"}),
    "rolled_back": frozenset({"retired", "delivery_pending"}),
    "rejected": frozenset(),
    "retired": frozenset(),
}
TERMINAL = frozenset(s for s, t in TRANSITIONS.items() if not t)


class Lifecycle:
    def __init__(self) -> None:
        self.state: dict[str, str] = {}
        self._lock = threading.Lock()

    def check(self, key: str, to_state: str) -> str:
        with self._lock:
            cur = self.state.get(key, "proposed" if to_state in ("admitted", "rejected") else None)
            if cur is None or to_state not in TRANSITIONS.get(cur, frozenset()):
                raise EcpError("ECP_ILLEGAL_TRANSITION", "illegal lifecycle transition", from_state=str(cur),
                               to_state=to_state)
            return cur

    def apply(self, key: str, to_state: str) -> None:
        with self._lock:
            self.state[key] = to_state

    def get(self, key: str) -> str | None:
        with self._lock:
            return self.state.get(key)

    def counts(self) -> dict[str, Any]:
        with self._lock:
            out: dict[str, int] = {}
            for s in self.state.values():
                out[s] = out.get(s, 0) + 1
            return out
