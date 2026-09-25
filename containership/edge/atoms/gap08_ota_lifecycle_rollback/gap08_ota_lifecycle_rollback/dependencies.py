"""Dependency-unavailable fail-closed policy (component 15).

Every production dependency has an explicit mode per operation class:

=================  ===========  ===========  ============================
dependency         forward      rollback     notes
=================  ===========  ===========  ============================
state_store        required     required     no durable commit, no action
lease              required     required     no fence, no action
audit_sink         required     buffered     rollback events sealed on recovery
health             required     n/a          missing evidence = hold, never pass
artifact_verifier  required     n/a          deferred retries re-check validity
identity           required     required     acks must be authenticated
supervisor         required     required     unknown outcome -> reconcile
topology           required     n/a          unknown topology fails closed
time               required     required     clock skew beyond bound = unavailable
policy/authz       required     required     authorization cannot be skipped
compatibility      required     n/a          missing evidence fails closed
=================  ===========  ===========  ============================

``emergency_override`` can relax a *forward* requirement only with an
authorized, audited, time-boxed approval (see ``authz.ApprovalLedger``); it
can never relax state_store, lease, identity or authz.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum

from .common import Clock, SystemClock
from .errors import DependencyUnavailable, Unauthorized


class Mode(str, Enum):
    REQUIRED = "required"
    BUFFERED = "buffered"
    NOT_USED = "n/a"


class OpClass(str, Enum):
    FORWARD = "forward"    # create, admit, wave, deferred retry
    ROLLBACK = "rollback"  # rollback, quarantine, freeze, pause, cancel


POLICY: dict[str, dict[OpClass, Mode]] = {
    "state_store": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.REQUIRED},
    "lease": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.REQUIRED},
    "audit_sink": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.BUFFERED},
    "health": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.NOT_USED},
    "artifact_verifier": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.NOT_USED},
    "identity": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.REQUIRED},
    "supervisor": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.REQUIRED},
    "topology": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.NOT_USED},
    "time": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.REQUIRED},
    "authz": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.REQUIRED},
    "compatibility": {OpClass.FORWARD: Mode.REQUIRED, OpClass.ROLLBACK: Mode.NOT_USED},
}
NEVER_OVERRIDABLE = frozenset({"state_store", "lease", "identity", "authz"})


@dataclass
class DependencyHealth:
    clock: Clock = field(default_factory=SystemClock)
    stale_after_s: float = 30.0
    _last_ok: dict[str, float] = field(default_factory=dict)
    _down: set[str] = field(default_factory=set)
    _override: dict[str, float] = field(default_factory=dict)  # dep -> expiry
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def report(self, dep: str, ok: bool) -> None:
        if dep not in POLICY:
            raise KeyError(dep)
        with self._lock:
            if ok:
                self._down.discard(dep)
                self._last_ok[dep] = self.clock.monotonic()
            else:
                self._down.add(dep)

    def mark_all_ok(self) -> None:
        for dep in POLICY:
            self.report(dep, True)

    def is_available(self, dep: str) -> bool:
        with self._lock:
            if dep in self._down:
                return False
            last = self._last_ok.get(dep)
            return last is not None and self.clock.monotonic() - last <= self.stale_after_s

    def grant_override(self, dep: str, until_monotonic: float) -> None:
        if dep in NEVER_OVERRIDABLE:
            raise Unauthorized(f"dependency {dep} can never be overridden", resource=dep)
        with self._lock:
            self._override[dep] = until_monotonic

    def guard(self, op: OpClass) -> list[str]:
        """Raise if a REQUIRED dependency is down; return BUFFERED deps currently down."""
        buffered = []
        now = self.clock.monotonic()
        for dep, modes in POLICY.items():
            mode = modes[op]
            if mode is Mode.NOT_USED or self.is_available(dep):
                continue
            if mode is Mode.BUFFERED:
                buffered.append(dep)
                continue
            with self._lock:
                ov = self._override.get(dep)
            if op is OpClass.FORWARD and ov is not None and ov > now:
                continue
            raise DependencyUnavailable(f"required dependency {dep} unavailable for {op.value} operations",
                                        resource=dep)
        return buffered
