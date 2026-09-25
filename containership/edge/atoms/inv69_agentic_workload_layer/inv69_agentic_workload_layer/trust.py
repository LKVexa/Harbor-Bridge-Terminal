"""Dependency health, trust-service freshness, connectivity state, offline queue
and degraded modes (C018, C048, C056).

``DEPENDENCY_MATRIX`` is the criticality matrix: for each dependency and each
operation phase it states the behaviour when the dependency is unavailable:

    closed    fail closed (refuse the operation)
    cache     permitted from last-known-good only within ``max_age_s``
    queue     permitted; effect deferred to a bounded local queue
    degrade   permitted with the named capability disabled
    allow     unaffected
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
import threading
import time

from .errors import AgentError

PHASES = ("startup", "admission", "in_flight", "approval", "tool_execution", "audit")

DEPENDENCY_MATRIX: Mapping[str, Mapping[str, Any]] = {
    # critical trust services
    "identity":    {"critical": True, "max_age_s": 300, "startup": "closed", "admission": "closed", "in_flight": "cache",
                    "approval": "closed", "tool_execution": "cache", "audit": "allow"},
    "attestation": {"critical": True, "max_age_s": 600, "startup": "closed", "admission": "cache", "in_flight": "cache",
                    "approval": "cache", "tool_execution": "closed", "audit": "allow"},
    "policy":      {"critical": True, "max_age_s": 300, "startup": "closed", "admission": "cache", "in_flight": "cache",
                    "approval": "closed", "tool_execution": "cache", "audit": "allow"},
    "keys":        {"critical": True, "max_age_s": 0, "startup": "closed", "admission": "closed", "in_flight": "closed",
                    "approval": "closed", "tool_execution": "closed", "audit": "closed"},
    "time":        {"critical": True, "max_age_s": 0, "startup": "closed", "admission": "allow", "in_flight": "allow",
                    "approval": "closed", "tool_execution": "allow", "audit": "allow"},
    "authorization": {"critical": True, "max_age_s": 60, "startup": "closed", "admission": "closed", "in_flight": "cache",
                      "approval": "closed", "tool_execution": "cache", "audit": "allow"},
    # non-critical
    "audit_export": {"critical": False, "max_age_s": None, "startup": "allow", "admission": "allow", "in_flight": "allow",
                     "approval": "allow", "tool_execution": "allow", "audit": "queue"},
    "telemetry":   {"critical": False, "max_age_s": None, "startup": "allow", "admission": "allow", "in_flight": "allow",
                    "approval": "allow", "tool_execution": "allow", "audit": "allow", "degrades": "telemetry_export"},
    "topology":    {"critical": False, "max_age_s": 3600, "startup": "allow", "admission": "allow", "in_flight": "allow",
                    "approval": "allow", "tool_execution": "allow", "audit": "allow", "degrades": "topology_labels"},
    "fast_sandbox": {"critical": False, "max_age_s": None, "startup": "allow", "admission": "allow", "in_flight": "allow",
                     "approval": "allow", "tool_execution": "degrade", "audit": "allow", "degrades": "fast_sandbox"},
    "durable_execution": {"critical": True, "max_age_s": None, "startup": "closed", "admission": "closed",
                          "in_flight": "closed", "approval": "allow", "tool_execution": "closed", "audit": "allow"},
}

NETWORK_OPS = {
    # C018 classification of network-dependent operations while offline
    "identity.verify": "cacheable", "policy.fetch": "cacheable", "approval.grant": "mandatory_online",
    "tool.side_effect": "mandatory_online", "tool.readonly_local": "locally_satisfiable",
    "audit.export": "queueable", "artifact.fetch": "prohibited_offline", "status.report": "queueable",
    "authorization.check": "cacheable",
}


class Health(str, Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class Connectivity(str, Enum):
    ONLINE = "online"
    INTERMITTENT = "intermittent"
    OFFLINE = "offline"


@dataclass
class DepState:
    name: str
    health: Health = Health.UNKNOWN
    last_good_at: float | None = None
    last_good_version: str | None = None
    last_change_at: float = 0.0
    reason: str = "no probe yet"


@dataclass
class DeferredOp:
    local_seq: int
    op: str
    payload_ref: str
    created_mono: float
    created_wall: float
    assumptions: Mapping[str, str] = field(default_factory=dict)   # e.g. policy_version at enqueue


class TrustMonitor:
    """Tracks dependency health/freshness and gates operations per DEPENDENCY_MATRIX."""

    def __init__(self, *, clock=time.time, max_queue: int = 0, events=None):
        self._clock = clock
        self._lock = threading.Lock()
        self.deps = {n: DepState(n) for n in DEPENDENCY_MATRIX}
        self.connectivity = Connectivity.ONLINE
        self.max_queue = max_queue
        self.queue: list[DeferredOp] = []
        self._seq = 0
        self.events: list[dict[str, Any]] = events if events is not None else []

    def _emit(self, kind: str, **kw):
        self.events.append({"schema": "PK_AGENT_DEGRADED_EVENT/1", "kind": kind, "at": self._clock(), **kw})

    def report(self, name: str, health: Health, *, version: str | None = None, reason: str = "") -> None:
        with self._lock:
            d = self.deps[name]
            now = self._clock()
            if health is Health.UP:
                d.last_good_at, d.last_good_version = now, version or d.last_good_version
            if health != d.health:
                d.last_change_at = now
                self._emit("dependency_health", dependency=name, old=d.health.value, new=health.value, reason=reason)
            d.health, d.reason = health, reason or health.value

    def set_connectivity(self, state: Connectivity) -> list[DeferredOp]:
        """Change connectivity; on reconnect returns the deferred ops to re-evaluate (never replays blindly)."""
        with self._lock:
            old, self.connectivity = self.connectivity, state
            if old != state:
                self._emit("connectivity", old=old.value, new=state.value)
            if state is Connectivity.ONLINE and old is not Connectivity.ONLINE:
                drained, self.queue = sorted(self.queue, key=lambda o: o.local_seq), []
                return drained
            return []

    def fresh(self, name: str) -> tuple[bool, str]:
        d = self.deps[name]
        spec = DEPENDENCY_MATRIX[name]
        if d.health is Health.UP:
            return True, "up"
        if d.last_good_at is None:
            return False, "never verified"
        max_age = spec["max_age_s"]
        age = self._clock() - d.last_good_at
        if max_age is None:
            return False, "no cache permitted"
        if age < 0:
            return False, "clock went backwards"
        return (age <= max_age), f"last-known-good age {age:.1f}s (max {max_age}s)"

    def gate(self, phase: str, deps: tuple[str, ...] | None = None) -> dict[str, Any]:
        """Return a decision record; raise AgentError when the phase must fail closed."""
        if phase not in PHASES:
            raise ValueError(phase)
        decision = {"phase": phase, "checks": [], "degraded": []}
        for name in deps or tuple(DEPENDENCY_MATRIX):
            spec = DEPENDENCY_MATRIX[name]
            mode = spec[phase]
            d = self.deps[name]
            if d.health is Health.UP or mode == "allow":
                decision["checks"].append({"dependency": name, "mode": mode, "result": "ok"})
                continue
            if mode == "cache":
                ok, why = self.fresh(name)
                decision["checks"].append({"dependency": name, "mode": mode, "result": "cache" if ok else "stale",
                                           "why": why, "version": d.last_good_version})
                if not ok:
                    self._emit("fail_closed", dependency=name, phase=phase, why=why)
                    raise AgentError("AGT-TRU-001" if spec["critical"] else "AGT-DEP-001",
                                     details={"dependency": name, "phase": phase, "why": why})
                continue
            if mode in ("degrade", "queue"):
                decision["degraded"].append(spec.get("degrades", name))
                decision["checks"].append({"dependency": name, "mode": mode, "result": mode})
                continue
            self._emit("fail_closed", dependency=name, phase=phase, why=d.reason)
            raise AgentError("AGT-TRU-001" if spec["critical"] else "AGT-DEP-002",
                             details={"dependency": name, "phase": phase, "health": d.health.value})
        return decision

    def would_pass(self, phase: str) -> tuple[bool, str]:
        """Side-effect-free readiness probe using the same matrix as ``gate`` (status must agree with admission)."""
        for name, spec in DEPENDENCY_MATRIX.items():
            mode, d = spec[phase], self.deps[name]
            if d.health is Health.UP or mode in ("allow", "degrade", "queue"):
                continue
            if mode == "cache" and self.fresh(name)[0]:
                continue
            return False, name
        return True, ""

    def network_op(self, op: str, *, payload_ref: str = "", assumptions: Mapping[str, str] | None = None) -> str:
        """Classify and admit a network-dependent op under the current connectivity."""
        cls = NETWORK_OPS.get(op)
        if cls is None:
            raise AgentError("AGT-VAL-001", "unclassified network operation", details={"op": op})
        if self.connectivity is Connectivity.ONLINE:
            return "online"
        if cls in ("mandatory_online", "prohibited_offline"):
            raise AgentError("AGT-DEP-002", "operation requires connectivity", details={"op": op, "class": cls})
        if cls == "locally_satisfiable":
            return "local"
        if cls == "cacheable":
            return "cache"
        with self._lock:  # queueable
            if len(self.queue) >= self.max_queue:
                raise AgentError("AGT-CAP-003", "offline queue full", details={"op": op, "max": self.max_queue})
            self._seq += 1
            self.queue.append(DeferredOp(self._seq, op, payload_ref, time.monotonic(), self._clock(),
                                         dict(assumptions or {})))
            return "queued"

    def blocked_capabilities(self) -> list[str]:
        out = []
        if self.connectivity is not Connectivity.ONLINE:
            out += sorted(o for o, c in NETWORK_OPS.items() if c in ("mandatory_online", "prohibited_offline"))
        for n, d in self.deps.items():
            if d.health is not Health.UP and "degrades" in DEPENDENCY_MATRIX[n]:
                out.append(DEPENDENCY_MATRIX[n]["degrades"])
        return sorted(set(out))

    def snapshot(self) -> dict[str, Any]:
        return {"connectivity": self.connectivity.value, "queued": len(self.queue), "max_queue": self.max_queue,
                "dependencies": {n: {"health": d.health.value, "reason": d.reason, "fresh": self.fresh(n)[0],
                                     "last_good_version": d.last_good_version} for n, d in self.deps.items()},
                "blocked_capabilities": self.blocked_capabilities()}


def reconcile(deferred: list[DeferredOp], current_assumptions: Mapping[str, str]) -> tuple[list[DeferredOp], list[DeferredOp]]:
    """Re-evaluate deferred ops after recovery: keep those whose assumptions still hold, discard the rest.
    Duplicate payload refs are suppressed (replay protection)."""
    keep, drop, seen = [], [], set()
    for op in sorted(deferred, key=lambda o: o.local_seq):
        if op.payload_ref and op.payload_ref in seen:
            drop.append(op)
            continue
        seen.add(op.payload_ref)
        if all(current_assumptions.get(k) == v for k, v in op.assumptions.items()):
            keep.append(op)
        else:
            drop.append(op)
    return keep, drop
