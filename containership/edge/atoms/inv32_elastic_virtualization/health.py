"""Health, readiness, stall watchdog, quarantine/freeze and emergency controls (WS 8, 10).

Liveness answers "is the process able to make progress" (event loop / locks not wedged).
Readiness answers "may this controller accept *new mutations*" and is the AND of every check below.
Readiness is never true while audit integrity has failed or ownership is stale.

Degraded modes (WS 10):
    NORMAL        all operations
    READ_ONLY     reads + audit only (config mode=read_only, or audit export down beyond tolerance)
    FROZEN_WRITE  no new mutations (lease lost, provider circuit open, unknown outcome pending, emergency)
    TELEMETRY_DOWN / EXPORT_DOWN / FREE_PAGE_DOWN  informational; control continues
"""
from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
from typing import Any, Callable, Mapping

from . import errors as E

QUARANTINE_SCOPES = ("guest", "host", "tenant", "global")


@dataclass
class InFlight:
    operation_id: str
    kind: str
    guest: str
    started: float
    deadline: float
    stall_after: float
    phase: str = "prepared"
    last_progress: float = 0.0
    provider_request_id: str | None = None


class Watchdog:
    """Tracks every in-flight mutation; flags stalls independently of client timeouts."""

    def __init__(self, *, clock=time.monotonic, on_incident: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._clock = clock
        self._ops: dict[str, InFlight] = {}
        self._lock = threading.Lock()
        self._flagged: set[str] = set()
        self._on_incident = on_incident or (lambda e: None)

    def start(self, op: str, kind: str, guest: str, *, deadline: float, stall_after_s: float) -> None:
        now = self._clock()
        with self._lock:
            self._ops[op] = InFlight(op, kind, guest, now, deadline, stall_after_s, last_progress=now)

    def progress(self, op: str, phase: str, provider_request_id: str | None = None) -> None:
        with self._lock:
            f = self._ops.get(op)
            if f:
                f.phase, f.last_progress = phase, self._clock()
                if provider_request_id:
                    f.provider_request_id = provider_request_id

    def finish(self, op: str) -> None:
        with self._lock:
            self._ops.pop(op, None)
            self._flagged.discard(op)

    def scan(self) -> list[dict[str, Any]]:
        """Idempotent: each stalled op produces exactly one incident signal."""
        now = self._clock()
        out = []
        with self._lock:
            for f in self._ops.values():
                stalled = now - f.last_progress > f.stall_after or now > f.deadline
                if stalled and f.operation_id not in self._flagged:
                    self._flagged.add(f.operation_id)
                    cause = "provider_slow" if f.phase == "provider_requested" else "local_stall"
                    sig = {"signal": "stall", "operation_id": f.operation_id, "kind": f.kind, "phase": f.phase,
                           "cause": cause, "provider_request_id": f.provider_request_id,
                           "age_s": round(now - f.started, 3)}
                    out.append(sig)
        for s in out:
            self._on_incident(s)
        return out

    def count(self) -> int:
        return len(self._ops)


class QuarantineManager:
    """Per-guest/host/tenant freeze and global emergency disable, persisted in the durable store."""

    def __init__(self, store, *, audit: Callable[[Mapping[str, Any]], Any], clock=time.time) -> None:
        self._store = store
        self._audit = audit
        self._clock = clock

    @staticmethod
    def key(scope: str, ident: str | None) -> str:
        if scope not in QUARANTINE_SCOPES:
            raise E.ValidationFailed("unknown quarantine scope", scope=scope)
        return "global" if scope == "global" else f"{scope}:{ident}"

    def set(self, scope: str, ident: str | None, *, principal: str, reason: str, ticket: str, owner: str,
            ttl_s: float | None, auto_expire_safe: bool = False) -> dict[str, Any]:
        if not reason.strip() or not ticket.strip() or not owner.strip():
            raise E.ValidationFailed("quarantine requires reason, ticket and owner")
        if ttl_s is not None and ttl_s <= 0:
            raise E.ValidationFailed("ttl must be positive")
        k = self.key(scope, ident)
        data = {"scope": scope, "ident": ident, "principal": principal, "reason": reason, "ticket": ticket,
                "owner": owner, "set_at": self._clock(),
                "expires_at": (self._clock() + ttl_s) if ttl_s else None, "auto_expire": bool(auto_expire_safe)}
        self._store.set_quarantine(k, data)
        self._audit({"kind": "quarantine_set", **{f"q_{k2}": v for k2, v in data.items()}})
        return data

    def clear(self, scope: str, ident: str | None, *, principal: str, reason: str) -> None:
        k = self.key(scope, ident)
        self._store.clear_quarantine(k)
        self._audit({"kind": "quarantine_clear", "q_scope": scope, "q_ident": ident, "principal": principal,
                     "reason": reason})

    def active(self) -> dict[str, dict[str, Any]]:
        now = self._clock()
        out = {}
        for k, d in list(self._store.quarantine.items()):
            if d.get("expires_at") and d["expires_at"] <= now:
                if d.get("auto_expire"):
                    self._store.clear_quarantine(k)
                    self._audit({"kind": "quarantine_expired", "q_key": k})
                    continue
                # expired but not declared safe to auto-clear: stays until manual clear
            out[k] = d
        return out

    def check(self, *, host: str, tenant: str, guest: str) -> None:
        act = self.active()
        for k in ("global", f"host:{host}", f"tenant:{tenant}", f"guest:{guest}"):
            if k in act:
                cls = E.EmergencyDisabled if k == "global" else E.Quarantined
                raise cls("mutation blocked by quarantine", scope=k.split(":")[0], ticket=act[k].get("ticket"))


@dataclass
class HealthReport:
    live: bool
    ready: bool
    mode: str
    checks: dict[str, bool] = field(default_factory=dict)
    degraded: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "PK_HEALTH/1", "live": self.live, "ready": self.ready, "mode": self.mode,
                "checks": dict(self.checks), "degraded": list(self.degraded)}
