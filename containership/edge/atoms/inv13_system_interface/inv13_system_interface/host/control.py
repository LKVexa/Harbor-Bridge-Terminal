"""MC-027 -- rollback, quarantine, freeze and emergency-disable controls.

Every control action requires an authenticated operator identity (verified
by ``IdentityGate`` with role ``operator``) plus a reason, and is recorded in
the durable audit sink (who / what / why).  Quarantine and emergency-disable
take effect on the *next* check of every in-flight operation (``guard``), and
revoke the workload's descriptors so authority cannot be re-used.
"""
from __future__ import annotations

import threading
from typing import Any

from .errors import ErrorCode, Inv13Error


class ControlPlane:
    def __init__(self, *, identity, audit, descriptors, config=None) -> None:
        self.identity, self.audit, self.descriptors, self.config = identity, audit, descriptors, config
        self._quarantined: set[str] = set()
        self._disabled_caps: set[str] = set()
        self._frozen = False
        self._lock = threading.Lock()

    def _op(self, token: str, action: str, target: str, reason: str) -> dict[str, Any]:
        if not reason or len(reason) > 1024:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "reason required")
        claims = self.identity.verify(token, role="operator")
        self.audit.append(target, f"control.{action}", "applied", {"reason": reason, "action": action,
                                                                   "count": 1, "node": claims.get("sub")})
        return claims

    def quarantine(self, token: str, workload: str, reason: str) -> list[str]:
        self._op(token, "quarantine", workload, reason)
        with self._lock:
            self._quarantined.add(workload)
        revoked = []
        for d in self.descriptors.live():
            if d.workload == workload and d.parent is None:
                revoked += self.descriptors.revoke(d.id)
        return revoked

    def release(self, token: str, workload: str, reason: str) -> None:
        self._op(token, "release", workload, reason)
        with self._lock:
            self._quarantined.discard(workload)

    def emergency_disable(self, token: str, capability: str, reason: str) -> None:
        self._op(token, "emergency-disable", capability, reason)
        with self._lock:
            self._disabled_caps.add(capability)

    def freeze(self, token: str, reason: str) -> None:
        self._op(token, "freeze", "*", reason)
        self._frozen = True

    def unfreeze(self, token: str, reason: str) -> None:
        self._op(token, "unfreeze", "*", reason)
        self._frozen = False

    def rollback_config(self, token: str, reason: str) -> str:
        claims = self._op(token, "rollback", "config", reason)
        if self.config is None:
            raise Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE, "no config store")
        return self.config.rollback(actor=str(claims.get("sub")), reason=reason)

    def guard(self, workload: str, capability: str | None = None, *, mutation: bool = False) -> None:
        with self._lock:
            if workload in self._quarantined:
                raise Inv13Error(ErrorCode.QUARANTINED)
            if capability and capability in self._disabled_caps:
                raise Inv13Error(ErrorCode.CAP_NOT_GRANTED, "emergency-disabled")
            if mutation and self._frozen:
                raise Inv13Error(ErrorCode.FROZEN)
