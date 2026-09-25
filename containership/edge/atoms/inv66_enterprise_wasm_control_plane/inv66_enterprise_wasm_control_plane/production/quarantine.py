"""Freeze / quarantine / emergency-disable controls (MC-042; C059, C092).

* ``freeze(scope)`` — any holder of ``quarantine`` at that scope; takes effect
  immediately for new admissions beneath the scope (``ECP_QUARANTINED``).
* ``release(scope)`` — needs ``dual_authorization.quarantine_release`` distinct
  approvers (default 2) who each hold ``quarantine``; the freezer alone cannot
  unfreeze.  Releasing is deliberately harder than freezing.
* ``emergency_disable`` — freeze of the organisation root: a kill switch.

All three are journaled (``quarantine.*``) before taking effect and rebuilt on
replay, so a restart never silently lifts a freeze.
"""
from __future__ import annotations

import threading
from typing import Any

from .errors import EcpError


class QuarantineController:
    def __init__(self) -> None:
        self.frozen: dict[tuple[str, ...], dict[str, Any]] = {}
        self.release_votes: dict[tuple[str, ...], set[str]] = {}
        self._lock = threading.Lock()

    def apply_record(self, kind: str, body: dict[str, Any]) -> None:
        scope = tuple(body["scope"].split("/"))
        with self._lock:
            if kind == "quarantine.freeze":
                self.frozen[scope] = {"by": body["by"], "reason": body.get("reason", ""), "seq": body.get("seq")}
                self.release_votes.pop(scope, None)
            elif kind == "quarantine.release_vote":
                self.release_votes.setdefault(scope, set()).add(body["by"])
            elif kind == "quarantine.release":
                self.frozen.pop(scope, None)
                self.release_votes.pop(scope, None)

    def blocking(self, target: tuple[str, ...]) -> tuple[str, ...] | None:
        with self._lock:
            for i in range(1, len(target) + 1):
                if target[:i] in self.frozen:
                    return target[:i]
        return None

    def check(self, target: tuple[str, ...]) -> None:
        b = self.blocking(target)
        if b is not None:
            raise EcpError("ECP_QUARANTINED", "scope is frozen", scope="/".join(b))

    def votes(self, scope: tuple[str, ...]) -> set[str]:
        with self._lock:
            return set(self.release_votes.get(scope, set()))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"/".join(k): dict(v) for k, v in self.frozen.items()}
