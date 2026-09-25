"""Operator emergency controls and degraded-mode policy (MC-030, MC-032).

``ControlPlane`` holds quarantine sets (tenant / node / instance), a global
admission freeze and the degraded mode.  Every change requires an operator
principal with the matching capability, is audited, and is consulted by the
admission controller before any side effect.
"""
from __future__ import annotations

import threading
from typing import Callable

from ..errors import Inv24Error

MODES = ("normal", "degraded", "offline")


class ControlPlane:
    def __init__(self, *, degraded_policy: str = "fail_closed",
                 audit: Callable[..., object] | None = None) -> None:
        if degraded_policy not in {"fail_closed", "serve_existing"}:
            raise Inv24Error("CONFIG_REJECTED", "unknown degraded policy")
        self.degraded_policy = degraded_policy
        self._lock = threading.Lock()
        self.quarantined: dict[str, set[str]] = {"tenant": set(), "node": set(), "instance": set()}
        self.frozen = False
        self.mode = "normal"
        self._audit = audit or (lambda *a, **k: None)

    def _authz(self, principal, cap: str) -> None:
        if principal is None:
            raise Inv24Error("UNAUTHENTICATED", "operator identity required")
        principal.require(cap)

    def quarantine(self, principal, scope: str, key: str, reason: str) -> None:
        self._authz(principal, "operator:quarantine")
        if scope not in self.quarantined:
            raise Inv24Error("CONFIG_REJECTED", f"unknown quarantine scope {scope}")
        with self._lock:
            self.quarantined[scope].add(key)
        self._audit("quarantine", principal.subject, "applied", scope=scope, key=key, reason=reason)

    def release(self, principal, scope: str, key: str, reason: str) -> None:
        self._authz(principal, "operator:quarantine")
        with self._lock:
            self.quarantined.get(scope, set()).discard(key)
        self._audit("quarantine_release", principal.subject, "applied", scope=scope, key=key, reason=reason)

    def freeze(self, principal, frozen: bool, reason: str) -> None:
        self._authz(principal, "operator:freeze")
        with self._lock:
            self.frozen = frozen
        self._audit("admission_freeze", principal.subject, "applied", frozen=frozen, reason=reason)

    def set_mode(self, mode: str, reason: str) -> None:
        if mode not in MODES:
            raise Inv24Error("CONFIG_REJECTED", f"unknown mode {mode}")
        with self._lock:
            self.mode = mode
        self._audit("mode_change", "system", "applied", mode=mode, reason=reason)

    def check_admission(self, *, tenant: str, node: str, instance: str) -> None:
        with self._lock:
            if self.frozen:
                raise Inv24Error("ADMISSION_FROZEN", "admission frozen by operator")
            if tenant in self.quarantined["tenant"] or node in self.quarantined["node"] \
                    or instance in self.quarantined["instance"]:
                raise Inv24Error("QUARANTINED", "tenant/node/instance quarantined")
            if self.mode != "normal":
                # new capacity is never created without the control plane
                raise Inv24Error("DEGRADED_REFUSED", f"no new admissions in {self.mode} mode")

    def may_keep_running(self, *, tenant: str, instance: str) -> bool:
        with self._lock:
            if tenant in self.quarantined["tenant"] or instance in self.quarantined["instance"]:
                return False
            return self.mode == "normal" or self.degraded_policy == "serve_existing"
