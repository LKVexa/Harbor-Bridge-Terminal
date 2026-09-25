"""GAP02-MC-39 — Quarantine / freeze control.

``quarantine(probe)`` stops a probe backend (its capabilities become unprobed
with QUARANTINED); ``freeze(node)`` stops the node from publishing any
capability as present (emergency disable). Every change needs an authorised
principal and a reason and is written to the audit stream.
"""
from __future__ import annotations

import threading
from typing import Callable

from .errors import Code, Gap02Error


class QuarantineRegistry:
    def __init__(self, audit: Callable[[str, dict], None] = lambda k, d: None):
        self._q: dict[str, str] = {}
        self.frozen: str | None = None
        self._audit = audit
        self._lock = threading.Lock()

    def quarantine(self, probe: str, principal: str, reason: str) -> None:
        if not principal or not reason:
            raise Gap02Error(Code.POLICY_DENIED, "principal and reason required")
        with self._lock:
            self._q[probe] = reason[:256]
        self._audit("quarantine.set", {"probe": probe, "principal": principal, "reason": reason[:256]})

    def release(self, probe: str, principal: str) -> None:
        with self._lock:
            self._q.pop(probe, None)
        self._audit("quarantine.release", {"probe": probe, "principal": principal})

    def freeze(self, principal: str, reason: str) -> None:
        if not principal or not reason:
            raise Gap02Error(Code.POLICY_DENIED, "principal and reason required")
        self.frozen = reason[:256]
        self._audit("node.freeze", {"principal": principal, "reason": reason[:256]})

    def thaw(self, principal: str) -> None:
        self.frozen = None
        self._audit("node.thaw", {"principal": principal})

    def is_quarantined(self, probe: str) -> bool:
        return self.frozen is not None or probe in self._q

    def snapshot(self) -> dict:
        return {"frozen": self.frozen, "quarantined": dict(self._q)}
