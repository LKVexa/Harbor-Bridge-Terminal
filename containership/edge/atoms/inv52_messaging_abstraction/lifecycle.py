"""Component lifecycle for INV-52 (C015, C040, C048, C057, C059, C092).

States::

    CREATED -> CONFIGURED -> READY <-> DEGRADED
                               |          |
                               v          v
                            DRAINING -> STOPPED
    any state except STOPPED -> DISABLED (emergency disable) -> CONFIGURED

Illegal transitions raise ``InvalidTransition``; every transition is appended
to a bounded history with the actor and reason.  ``Bootstrap`` is the
deterministic empty-node -> healthy path used by the day-0 runbook.
"""
from __future__ import annotations

import datetime as dt
import threading
from collections import deque
from typing import Any, Callable, Mapping

from .runtime import InvalidTransition, MessagingError

CREATED, CONFIGURED, READY, DEGRADED, DRAINING, STOPPED, DISABLED = (
    "CREATED", "CONFIGURED", "READY", "DEGRADED", "DRAINING", "STOPPED", "DISABLED")
STATES = (CREATED, CONFIGURED, READY, DEGRADED, DRAINING, STOPPED, DISABLED)
TRANSITIONS: dict[str, set[str]] = {
    CREATED: {CONFIGURED, DISABLED},
    CONFIGURED: {READY, DISABLED, STOPPED},
    READY: {DEGRADED, DRAINING, DISABLED},
    DEGRADED: {READY, DRAINING, DISABLED},
    DRAINING: {STOPPED, DISABLED},
    STOPPED: set(),
    DISABLED: {CONFIGURED, STOPPED},
}
ACCEPTS_PUBLISH = {READY, DEGRADED}


class NotServing(MessagingError, RuntimeError):
    code = "PK_MSG_NOT_SERVING"
    retryable = True


class Lifecycle:
    def __init__(self, *, history: int = 256, clock: Callable[[], dt.datetime] | None = None):
        self.state = CREATED
        self.history: deque[dict[str, Any]] = deque(maxlen=history)
        self._lock = threading.Lock()
        self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))

    def to(self, new: str, *, actor: str, reason: str) -> None:
        with self._lock:
            if new not in STATES or new not in TRANSITIONS[self.state]:
                raise InvalidTransition(f"{self.state} -> {new} is not legal", details={"from": self.state, "to": new})
            self.history.append({"from": self.state, "to": new, "actor": actor, "reason": reason[:200],
                                 "at": self.clock().isoformat()})
            self.state = new

    def require_serving(self) -> None:
        if self.state not in ACCEPTS_PUBLISH:
            raise NotServing(f"component is {self.state}", details={"state": self.state})


class ManagedBus:
    """A ``PubSub`` gated by the component lifecycle and a dependency view.

    ``dependencies`` maps a name to a probe returning True when healthy and a
    flag saying whether it is critical.  A failed critical dependency moves the
    component to DEGRADED and — for security dependencies (identity, key, time,
    policy) — refuses publishes: fail closed (C048).  A failed noncritical one
    (telemetry export) only degrades (C056).
    """

    def __init__(self, bus: Any, lifecycle: Lifecycle | None = None,
                 dependencies: Mapping[str, tuple[Callable[[], bool], str]] | None = None):
        self.bus = bus
        self.lifecycle = lifecycle or Lifecycle()
        self.dependencies = dict(dependencies or {})  # name -> (probe, "security"|"critical"|"noncritical")

    def probe(self) -> dict[str, Any]:
        status = {}
        for name, (fn, kind) in self.dependencies.items():
            try:
                ok = bool(fn())
            except Exception:  # noqa: BLE001
                ok = False
            status[name] = {"ok": ok, "kind": kind}
        bad = [n for n, s in status.items() if not s["ok"] and s["kind"] in ("security", "critical")]
        if self.lifecycle.state == READY and bad:
            self.lifecycle.to(DEGRADED, actor="probe", reason="dependency failed: " + ",".join(bad))
        elif self.lifecycle.state == DEGRADED and not bad:
            self.lifecycle.to(READY, actor="probe", reason="dependencies recovered")
        return status

    def publish(self, app: str, topic: str, msg: Any) -> int:
        self.lifecycle.require_serving()
        status = self.probe()
        blocked = [n for n, s in status.items() if not s["ok"] and s["kind"] == "security"]
        if blocked:
            from .security import TrustUnavailable
            raise TrustUnavailable("security dependency unavailable; publish refused",
                                   details={"dependencies": blocked})
        return self.bus.publish(app, topic, msg)

    def emergency_disable(self, *, actor: str, reason: str) -> None:
        self.lifecycle.to(DISABLED, actor=actor, reason=reason)

    def health(self) -> dict[str, Any]:
        h = self.bus.health()
        deps = self.probe()
        h["lifecycle"] = self.lifecycle.state
        h["dependencies"] = deps
        h["ready"] = self.lifecycle.state in ACCEPTS_PUBLISH and not any(
            not d["ok"] and d["kind"] == "security" for d in deps.values())
        if self.lifecycle.state not in ACCEPTS_PUBLISH:
            h["status"] = "unhealthy"
        elif self.lifecycle.state == DEGRADED and h["status"] == "ok":
            h["status"] = "degraded"
        return h


def bootstrap(config_layers: list[Mapping[str, Any]], *, author: str, dependencies=None,
              manager_kw: Mapping[str, Any] | None = None) -> tuple[ManagedBus, dict[str, Any]]:
    """Deterministic day-0 path: validate -> build -> probe -> READY (C040)."""
    from .config import ConfigManager

    life = Lifecycle()
    mgr = ConfigManager(**dict(manager_kw or {}))
    prov = mgr.activate(*config_layers, author=author, layer_names=[f"layer{i}" for i in range(len(config_layers))])
    life.to(CONFIGURED, actor=author, reason=f"config {prov['digest'][:12]}")
    managed = ManagedBus(mgr.bus, life, dependencies)
    managed.manager = mgr  # type: ignore[attr-defined]
    status = {n: s for n, s in managed.probe().items()}
    if any(not s["ok"] and s["kind"] in ("security", "critical") for s in status.values()):
        return managed, {"provenance": prov, "dependencies": status, "state": life.state}
    life.to(READY, actor=author, reason="bootstrap preflight passed")
    return managed, {"provenance": prov, "dependencies": status, "state": life.state}
