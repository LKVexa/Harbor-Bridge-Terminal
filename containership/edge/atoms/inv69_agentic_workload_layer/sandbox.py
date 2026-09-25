"""Contract-faithful adapters for adjacent layers (C030, C083) and run fencing / failover (C055).

These are *adapters over the published contracts* of INV-59 (authorization),
INV-57 (durable execution), INV-70 (fast sandbox) and INV-71 (heavy sandbox).
They speak the same request/response shapes a real peer must speak, perform the
PK_AGENT_PEER/1 handshake, and can be driven into failure modes (deny, timeout,
malformed response, unavailability, version skew, crash) for integration and
fault-injection testing.  Real peer binaries are not in this archive; the
certification tier against them is an explicit blocker (see WAIVERS.json).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
import hashlib
import json
import threading
import time

from .compat import PROTOCOL
from .context import CallContext
from .errors import AgentError

TIER_STRENGTH = {"fast": 1, "heavy": 2}


class FaultPlan:
    """Scripted faults: op -> list of fault names consumed one per call ('ok', 'unavailable', 'timeout',
    'malformed', 'deny', 'crash_after_effect')."""

    def __init__(self, plan: Mapping[str, list[str]] | None = None):
        self._plan = {k: list(v) for k, v in (plan or {}).items()}
        self._lock = threading.Lock()

    def next(self, op: str) -> str:
        with self._lock:
            q = self._plan.get(op)
            return q.pop(0) if q else "ok"

    def add(self, op: str, *faults: str) -> None:
        with self._lock:
            self._plan.setdefault(op, []).extend(faults)


def _apply_fault(fault: str, ctx: CallContext):
    if fault == "unavailable":
        raise AgentError("AGT-DEP-001", correlation_id=ctx.correlation_id)
    if fault == "timeout":
        raise TimeoutError()
    if fault == "sandbox_unavailable":
        raise AgentError("AGT-SBX-001", correlation_id=ctx.correlation_id)


class Peer:
    component = "unknown"
    version = "0.0.0"
    capabilities: frozenset = frozenset()

    def hello(self) -> dict:
        return {"component": self.component, "version": self.version, "protocol": PROTOCOL,
                "capabilities": sorted(self.capabilities)}


class AuthorizationAdapter(Peer):
    """INV-59: authorize(principal, tool, tenant) -> {"decision": "allow"|"deny", "policy_version": str}."""
    component, version = "INV-59", "4.3.0"
    capabilities = frozenset({"step.v1", "error_codes.v1", "trace_context.w3c"})

    def __init__(self, policy: Mapping[str, set[str]], faults: FaultPlan | None = None, policy_version="authz-1"):
        self.policy, self.faults, self.policy_version = policy, faults or FaultPlan(), policy_version
        self.calls = 0

    def authorize(self, ctx: CallContext, principal: str, tool: str, tenant: str) -> dict:
        self.calls += 1
        ctx.check()
        fault = self.faults.next("authorize")
        _apply_fault(fault, ctx)
        if fault == "malformed":
            return {"decisoin": "allow"}  # deliberately malformed
        allow = tool in self.policy.get(principal, set())
        return {"decision": "allow" if allow else "deny", "policy_version": self.policy_version,
                "principal": principal, "tool": tool, "tenant": tenant}


@dataclass
class Checkpoint:
    run_id: str
    seq: int
    state: dict
    fence: int


class DurableExecutionAdapter(Peer):
    """INV-57: leases with fencing tokens, checkpoints, and an idempotency record store."""
    component, version = "INV-57", "4.3.0"
    capabilities = frozenset({"fencing_tokens", "idempotency_keys", "trace_context.w3c"})

    def __init__(self, faults: FaultPlan | None = None, clock=time.time):
        self.faults = faults or FaultPlan()
        self._clock = clock
        self._lock = threading.Lock()
        self.leases: dict[str, tuple[str, int, float, str]] = {}   # run -> (owner, fence, expiry, zone)
        self._fence_counter: dict[str, int] = {}
        self.checkpoints: dict[str, Checkpoint] = {}
        self.effects: dict[str, dict] = {}                          # idempotency_key -> committed result

    def acquire(self, ctx: CallContext, run_id: str, owner: str, zone: str, ttl: float = 30.0) -> int:
        _apply_fault(self.faults.next("acquire"), ctx)
        with self._lock:
            cur = self.leases.get(run_id)
            if cur and cur[0] != owner and cur[2] > self._clock():
                raise AgentError("AGT-INT-003", "run is leased by another executor", details={"run_id": run_id})
            fence = self._fence_counter.get(run_id, 0) + 1
            self._fence_counter[run_id] = fence
            self.leases[run_id] = (owner, fence, self._clock() + ttl, zone)
            return fence

    def _check_fence(self, run_id: str, fence: int) -> None:
        cur = self.leases.get(run_id)
        if not cur or cur[1] != fence:
            raise AgentError("AGT-INT-003", details={"run_id": run_id, "fence": fence,
                                                      "current": cur[1] if cur else None})

    def check_fence(self, run_id: str, fence: int) -> None:
        with self._lock:
            self._check_fence(run_id, fence)

    def checkpoint(self, ctx: CallContext, run_id: str, fence: int, seq: int, state: dict) -> None:
        _apply_fault(self.faults.next("checkpoint"), ctx)
        with self._lock:
            self._check_fence(run_id, fence)
            prev = self.checkpoints.get(run_id)
            if prev and seq <= prev.seq:
                return  # idempotent: duplicate/out-of-order checkpoint ignored
            self.checkpoints[run_id] = Checkpoint(run_id, seq, json.loads(json.dumps(state)), fence)

    def record_effect(self, ctx: CallContext, run_id: str, fence: int, key: str, result: dict) -> dict:
        with self._lock:
            self._check_fence(run_id, fence)
            if key in self.effects:
                return self.effects[key]
            self.effects[key] = dict(result)
            return self.effects[key]

    def committed(self, key: str) -> dict | None:
        with self._lock:
            return self.effects.get(key)

    def load(self, run_id: str) -> Checkpoint | None:
        with self._lock:
            return self.checkpoints.get(run_id)


class SandboxAdapter(Peer):
    """INV-70 (fast) / INV-71 (heavy): launch(tier) then execute(tool, arg_ref, idempotency_key)."""
    capabilities = frozenset({"idempotency_keys", "trace_context.w3c"})

    def __init__(self, tier: str, tools: Mapping[str, Callable[[Any], Any]], faults: FaultPlan | None = None,
                 security_profile: Mapping[str, Any] | None = None):
        if tier not in TIER_STRENGTH:
            raise ValueError(tier)
        self.tier = tier
        self.component = "INV-70" if tier == "fast" else "INV-71"
        self.version = "4.3.0"
        self.tools = dict(tools)
        self.faults = faults or FaultPlan()
        self.security_profile = dict(security_profile or {"isolation": "microvm" if tier == "heavy" else "wasm",
                                                          "network": "deny", "fs": "ephemeral"})
        self.executions: list[dict] = []
        self._seen_keys: dict[str, Any] = {}
        self._lock = threading.Lock()

    def launch(self, ctx: CallContext) -> str:
        _apply_fault(self.faults.next("launch"), ctx)
        return f"{self.tier}-{len(self.executions)}"

    def execute(self, ctx: CallContext, tool: str, arg: Any, idempotency_key: str | None) -> dict:
        ctx.check()
        fault = self.faults.next("execute")
        _apply_fault(fault, ctx)
        with self._lock:
            if idempotency_key and idempotency_key in self._seen_keys:
                return {"result": self._seen_keys[idempotency_key], "deduplicated": True, "tier": self.tier}
            fn = self.tools.get(tool)
            if fn is None:
                raise AgentError("AGT-SBX-001", "tool not provisioned in sandbox", details={"tool": tool})
            value = fn(arg)
            self.executions.append({"tool": tool, "key": idempotency_key, "tier": self.tier})
            if idempotency_key:
                self._seen_keys[idempotency_key] = value
        if fault == "crash_after_effect":
            raise AgentError("AGT-SBX-001", "sandbox lost after dispatch", details={"effect": "indeterminate"})
        if fault == "malformed":
            return {"reslt": value}
        return {"result": value, "deduplicated": False, "tier": self.tier}


def idempotency_key(run_id: str, step: int, tool: str, arg_ref: str) -> str:
    return hashlib.sha256(f"{run_id}|{step}|{tool}|{arg_ref}".encode()).hexdigest()


def select_failover_target(candidates: list[Mapping[str, Any]], *, zone: str, allowed_zones: list[str],
                           trust_domain: str, required_tier: str) -> Mapping[str, Any]:
    """Residency/trust/capability-preserving failover target selection (C055)."""
    ok_zones = {zone, *allowed_zones}
    rejected = []
    for c in candidates:
        why = None
        if c.get("zone") not in ok_zones:
            why = "residency"
        elif c.get("trust_domain") != trust_domain:
            why = "trust_domain"
        elif TIER_STRENGTH.get(c.get("max_tier", ""), 0) < TIER_STRENGTH[required_tier]:
            why = "sandbox_capability"
        elif not c.get("healthy", False):
            why = "unhealthy"
        if why is None:
            return c
        rejected.append({"target": c.get("id"), "why": why})
    raise AgentError("AGT-POL-001", "no failover target satisfies residency/trust/capability",
                     details={"rejected": rejected})
