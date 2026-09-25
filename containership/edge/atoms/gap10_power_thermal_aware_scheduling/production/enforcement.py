"""Components 02, 03, 07 - downstream scheduler enforcement adapter,
elasticity-plane enforcement adapter, and explicit fail-closed consumer
behaviour when GAP-10 is absent or unhealthy.

The adapters are written against small protocols (``SchedulerBackend``,
``ElasticityBackend``) so the same code drives the in-repo reference backends
(used by the tests and the end-to-end harness) and the real SCH-01 / PLN-05
integrations, which must implement the same methods.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from math import floor
from typing import Protocol

from .errors import ErrorCode, Gap10Error

DECISION_SCHEMA = "PK_POWER_CEILING/1"


# ------------------------------------------------------------ 07 consumer guard
@dataclass(frozen=True)
class FailClosedContract:
    """What a consumer MUST assume when GAP-10 output is missing/unhealthy.

    ``absent_fraction`` must not exceed the critical ceiling; the default (0.0)
    means *no new admission* on a node without a valid GAP-10 decision."""
    max_decision_age_s: float = 15.0
    absent_fraction: float = 0.0
    critical_fraction: float = 0.25

    def __post_init__(self):
        if not 0.0 <= self.absent_fraction <= self.critical_fraction:
            raise ValueError("absent_fraction must be within [0, critical_fraction]")


@dataclass
class CeilingView:
    """Consumer-side cache of GAP-10 decisions with fail-closed reads."""
    contract: FailClosedContract = field(default_factory=FailClosedContract)
    decisions: dict[str, dict] = field(default_factory=dict)
    gap10_healthy: bool = True
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def publish(self, decision: dict) -> None:
        if decision.get("schema") != DECISION_SCHEMA:
            raise Gap10Error(ErrorCode.TELEMETRY_UNSUPPORTED_VERSION, f"unsupported decision {decision.get('schema')}")
        for k in ("node", "decision_id", "ceiling", "ceiling_fraction", "excluded", "issued_at", "fencing_token"):
            if k not in decision:
                raise Gap10Error(ErrorCode.TELEMETRY_MALFORMED, f"decision missing {k}")
        with self._lock:
            cur = self.decisions.get(decision["node"])
            if cur and decision["fencing_token"] < cur["fencing_token"]:
                raise Gap10Error(ErrorCode.FENCING_TOKEN_STALE, "decision from a fenced-out controller")
            if cur and decision["fencing_token"] == cur["fencing_token"] and decision["issued_at"] < cur["issued_at"]:
                return  # out-of-order duplicate: idempotent drop
            self.decisions[decision["node"]] = dict(decision)

    def effective(self, node: str, full_capacity: int, now: float) -> dict:
        """Always returns a bounded ceiling; never 'unlimited'."""
        with self._lock:
            d = self.decisions.get(node)
        reason = None
        if not self.gap10_healthy:
            reason = "GAP-10 unhealthy"
        elif d is None:
            reason = "no GAP-10 decision for node"
        elif now - d["issued_at"] > self.contract.max_decision_age_s:
            reason = f"GAP-10 decision stale ({now - d['issued_at']:.1f}s)"
        if reason is not None:
            fraction = self.contract.absent_fraction
            if d is not None:
                fraction = min(fraction, d["ceiling_fraction"])
            return {"node": node, "ceiling": floor(full_capacity * fraction), "excluded": fraction == 0.0,
                    "decision_id": None if d is None else d["decision_id"], "fail_closed": True, "reason": reason}
        return {"node": node, "ceiling": min(d["ceiling"], floor(full_capacity * d["ceiling_fraction"])),
                "excluded": bool(d["excluded"]), "decision_id": d["decision_id"], "fail_closed": False, "reason": "live"}


# ------------------------------------------------------------ 02 scheduler adapter
class SchedulerBackend(Protocol):
    def allocated(self, node: str) -> int: ...
    def commit(self, node: str, workload: str, units: int, decision_id: str) -> None: ...
    def set_limit(self, node: str, limit: int, decision_id: str) -> None: ...
    def applied_limit(self, node: str) -> tuple[int, str | None]: ...
    def drain(self, node: str, units: int, reason: str) -> list[str]: ...


@dataclass
class ReferenceScheduler:
    """In-memory reference backend: enforces the limit on its own commit path so
    even a direct/manual commit cannot exceed the applied ceiling."""
    capacity: dict[str, int] = field(default_factory=dict)
    limits: dict[str, tuple[int, str | None]] = field(default_factory=dict)
    placements: dict[str, list[tuple[str, int, str]]] = field(default_factory=dict)
    available: bool = True
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _up(self):
        if not self.available:
            raise Gap10Error(ErrorCode.DOWNSTREAM_UNAVAILABLE, "scheduler unavailable")

    def allocated(self, node):
        return sum(u for _, u, _ in self.placements.get(node, []))

    def commit(self, node, workload, units, decision_id):
        self._up()
        with self._lock:
            limit, _ = self.limits.get(node, (0, None))  # no limit applied -> zero (fail-closed)
            if self.allocated(node) + units > limit:
                raise Gap10Error(ErrorCode.ADMISSION_DENIED, f"{node}: {self.allocated(node)}+{units} > {limit}")
            self.placements.setdefault(node, []).append((workload, units, decision_id))

    def manual_place(self, node, workload, units):
        """Operator/manual placement path - goes through the same limit check."""
        self.commit(node, workload, units, "manual")

    def set_limit(self, node, limit, decision_id):
        self._up()
        with self._lock:
            self.limits[node] = (limit, decision_id)

    def applied_limit(self, node):
        return self.limits.get(node, (0, None))

    def drain(self, node, units, reason):
        evicted = []
        with self._lock:
            pl = self.placements.get(node, [])
            while pl and units > 0:
                w, u, _ = pl.pop()  # newest first
                evicted.append(w)
                units -= u
        return evicted


@dataclass
class SchedulerEnforcementAdapter:
    backend: SchedulerBackend
    view: CeilingView
    capacity: dict[str, int]
    overcommit_action: str = "drain"   # drain | no-new-admission
    metrics: object = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @staticmethod
    def to_units(fraction: float, full: int) -> int:
        """Fractional ceilings are floored - never rounded up."""
        return floor(full * fraction + 1e-12)

    def apply(self, node: str, now: float) -> dict:
        eff = self.view.effective(node, self.capacity[node], now)
        limit = 0 if eff["excluded"] else eff["ceiling"]
        self.backend.set_limit(node, limit, eff["decision_id"] or "fail-closed")
        evicted = []
        over = self.backend.allocated(node) - limit
        if over > 0 and self.overcommit_action == "drain":
            evicted = self.backend.drain(node, over, eff["reason"])
        return {"node": node, "limit": limit, "evicted": evicted, **eff}

    def admit(self, node: str, workload: str, units: int, now: float, consulted_decision_id: str | None = None) -> str:
        """Admission bound to the decision it consulted; revalidated under lock
        immediately before commit (no TOCTOU)."""
        with self._lock:
            eff = self.view.effective(node, self.capacity[node], now)
            if consulted_decision_id is not None and eff["decision_id"] != consulted_decision_id:
                raise Gap10Error(ErrorCode.CEILING_REVISION_MISMATCH,
                                 f"consulted {consulted_decision_id}, current {eff['decision_id']}")
            limit = 0 if eff["excluded"] else eff["ceiling"]
            applied, applied_id = self.backend.applied_limit(node)
            if applied > limit:  # ceiling fell since last apply: tighten first
                self.backend.set_limit(node, limit, eff["decision_id"] or "fail-closed")
            if self.backend.allocated(node) + units > limit:
                raise Gap10Error(ErrorCode.ADMISSION_DENIED, f"{node}: ceiling {limit}; {eff['reason']}")
            self.backend.commit(node, workload, units, eff["decision_id"] or "fail-closed")
            return eff["decision_id"] or "fail-closed"

    def divergence(self, node: str, now: float) -> dict | None:
        eff = self.view.effective(node, self.capacity[node], now)
        desired = 0 if eff["excluded"] else eff["ceiling"]
        applied, applied_id = self.backend.applied_limit(node)
        diverged = applied > desired or applied_id != (eff["decision_id"] or "fail-closed")
        if self.metrics is not None:
            self.metrics.set("gap10_enforcement_divergence", 1 if diverged else 0, {"node": node, "consumer": "scheduler"})
        if diverged:
            return {"node": node, "desired": desired, "applied": applied, "desired_id": eff["decision_id"], "applied_id": applied_id}
        return None


# ------------------------------------------------------------ 03 elasticity adapter
@dataclass
class ReferenceElasticity:
    """Autoscaler reference: target replicas per pool, capped by ``cap``."""
    targets: dict[str, int] = field(default_factory=dict)
    caps: dict[str, tuple[int, str]] = field(default_factory=dict)

    def set_cap(self, pool, cap, decision_id):
        self.caps[pool] = (cap, decision_id)
        if self.targets.get(pool, 0) > cap:
            self.targets[pool] = cap

    def request_scale(self, pool, desired):
        cap, _ = self.caps.get(pool, (0, None))
        self.targets[pool] = min(desired, cap)
        return self.targets[pool]


@dataclass
class ElasticityEnforcementAdapter:
    """Propagates the sum of node ceilings in a pool to the elasticity plane as
    a hard scale cap, with a cooldown so the autoscaler cannot refill capacity
    that was just thermally reduced until the ceiling has stayed up for
    ``refill_cooldown_s``."""
    backend: ReferenceElasticity
    view: CeilingView
    pools: dict[str, list[str]]
    capacity: dict[str, int]
    refill_cooldown_s: float = 120.0
    _last_cap: dict[str, int] = field(default_factory=dict)
    _raised_since: dict[str, float] = field(default_factory=dict)

    def apply(self, pool: str, now: float) -> int:
        cap, ids = 0, []
        for n in self.pools[pool]:
            e = self.view.effective(n, self.capacity[n], now)
            cap += 0 if e["excluded"] else e["ceiling"]
            ids.append(str(e["decision_id"]))
        prev = self._last_cap.get(pool)
        if prev is not None and cap > prev:
            since = self._raised_since.setdefault(pool, now)
            if now - since < self.refill_cooldown_s:
                cap = prev  # hold the lower cap during cooldown
            else:
                self._raised_since.pop(pool, None)
        else:
            self._raised_since.pop(pool, None)
        self._last_cap[pool] = cap
        self.backend.set_cap(pool, cap, "|".join(ids))
        return cap
