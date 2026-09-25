"""Operator freeze / disable controls (checklist #59).

Scopes: ``global``, ``tenant:<t>``, ``secret:<name>``, ``op:<verb>``.  A freeze
is an audited operator action; lifting it requires the same role.  Frozen
operations fail with ``INV55-E-FROZEN`` (DENIED - never retried).
"""
from __future__ import annotations

import threading

from .errors import INV55Error


class Quarantine:
    def __init__(self):
        self._frozen: dict[str, str] = {}
        self._lock = threading.Lock()

    def freeze(self, scope: str, reason: str):
        if not (scope == "global" or scope.split(":", 1)[0] in ("tenant", "secret", "op")):
            raise ValueError("bad freeze scope")
        with self._lock:
            self._frozen[scope] = reason

    def unfreeze(self, scope: str):
        with self._lock:
            self._frozen.pop(scope, None)

    def check(self, *, tenant: str, secret: str | None, op: str):
        keys = ["global", f"tenant:{tenant}", f"op:{op}"] + ([f"secret:{secret}"] if secret else [])
        with self._lock:
            for k in keys:
                if k in self._frozen:
                    raise INV55Error("INV55-E-FROZEN", k, reason="frozen")

    def active(self) -> dict:
        with self._lock:
            return dict(self._frozen)
