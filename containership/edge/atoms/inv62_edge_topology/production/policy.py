"""Constraint-precedence and policy-aware resolution/failover with durable
decision-reason records (MC-010, MC-045, MC-066, MC-067).

Precedence (earliest wins; a later layer can never re-admit a candidate an
earlier layer rejected):

    security > tenant_isolation > residency > availability > slo > cost
"""
from __future__ import annotations

import itertools
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from ..topology import TIER_PARENT, Link, Topology
from .config import PRECEDENCE

if PRECEDENCE[0] != "security":  # pragma: no cover - import-time invariant
    raise RuntimeError("security must take precedence over every other constraint")

TIER_COST = {tier: i for i, tier in enumerate(reversed(list(TIER_PARENT)))}  # device 0 .. cloud 3


@dataclass
class Decision:
    decision_id: str
    tenant: str
    operation: str
    inputs: dict[str, Any]
    graph_revision: int
    config_generation: int | None
    release: str
    considered: list[dict[str, Any]]
    selected: str | None
    latency_ms: float | None
    outcome: str
    mode: str
    at: float

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class DecisionLog:
    """Bounded in-memory decision store; every record is also written to the
    structured log so retention is governed by telemetry policy."""

    def __init__(self, capacity: int = 10_000):
        self._items: OrderedDict[str, Decision] = OrderedDict()
        self._cap = capacity
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def new_id(self) -> str:
        return f"dec-{int(time.time())}-{next(self._ids):08d}"

    def put(self, d: Decision) -> None:
        with self._lock:
            self._items[d.decision_id] = d
            while len(self._items) > self._cap:
                self._items.popitem(last=False)

    def get(self, decision_id: str) -> Decision | None:
        return self._items.get(decision_id)

    def __len__(self) -> int:
        return len(self._items)


@dataclass
class ResolveRequest:
    origin: str
    capability: str
    residency: list[str] | None = None
    max_latency_ms: float | None = None
    exclude: list[str] = field(default_factory=list)
    same_site_only: bool = False
    prefer: str = "latency"


@dataclass
class ResolveResult:
    node: str | None
    latency_ms: float | None
    considered: list[dict[str, Any]]
    stale_used: bool


def resolve(topo: Topology, req: ResolveRequest, *, quarantined: set[str], now: float, stale_after_s: float,
            stale_behaviour: str, residency_required: bool, allow_cross_site_failover: bool,
            limit: int = 16) -> ResolveResult:
    """Walk nodes in latency order and apply the precedence layers to each
    capable node.  For ``prefer=latency`` the walk stops at the first
    survivor (it is provably the best), so cost is proportional to the part
    of the graph closer than the answer, not to graph size."""
    origin = topo.nodes[req.origin]

    def fresh(link: Link) -> bool:
        return link.measured_at is None or now - link.measured_at <= stale_after_s

    link_ok = fresh if stale_behaviour == "exclude" else None
    allowed_res: set[str] | None = None
    if req.residency:
        allowed_res = set(req.residency)
    elif residency_required and origin.residency is not None:
        allowed_res = {origin.residency}

    considered: list[dict[str, Any]] = []
    survivors: list[tuple[float, str]] = []
    excluded = set(req.exclude)
    for d, name in topo.iter_by_distance(req.origin, link_ok=link_ok):
        if req.max_latency_ms is not None and d > req.max_latency_ms and req.prefer == "latency":
            # every remaining node is farther: record one representative and stop
            if req.capability in topo.nodes[name].caps and len(considered) < limit:
                considered.append({"node": name, "latency_ms": d, "verdict": "rejected", "layer": "slo",
                                   "reason": f"latency {d}ms exceeds {req.max_latency_ms}ms"})
            break
        node = topo.nodes[name]
        if req.capability not in node.caps:
            continue
        verdict: tuple[str, str] | None = None
        if name in quarantined:
            verdict = ("security", "node quarantined")
        elif name in excluded:
            verdict = ("security", "excluded by caller")
        elif allowed_res is not None and node.residency not in allowed_res:
            verdict = ("residency", f"residency {node.residency!r} not in {sorted(allowed_res)!r}")
        elif (req.same_site_only or not allow_cross_site_failover) and node.site is not None \
                and origin.site is not None and node.site != origin.site:
            verdict = ("residency" if req.same_site_only else "availability",
                       "other site; same_site_only" if req.same_site_only else "cross-site failover disabled by policy")
        elif req.max_latency_ms is not None and d > req.max_latency_ms:
            verdict = ("slo", f"latency {d}ms exceeds {req.max_latency_ms}ms")
        rec: dict[str, Any] = {"node": name, "latency_ms": d}
        if verdict:
            rec.update({"verdict": "rejected", "layer": verdict[0], "reason": verdict[1]})
        else:
            rec.update({"verdict": "eligible"})
            survivors.append((d, name))
        if len(considered) < limit:
            considered.append(rec)
        if survivors and req.prefer == "latency":
            break
    if req.prefer == "cost":
        survivors.sort(key=lambda t: (TIER_COST[topo.nodes[t[1]].tier], t[0], t[1]))
    selected = survivors[0] if survivors else None
    stale_used = False
    if selected and stale_behaviour != "exclude":
        fresh_d = topo.distance(req.origin, selected[1], link_ok=fresh)
        stale_used = fresh_d is None or fresh_d > selected[0]
    for rec in considered:
        if selected and rec["node"] == selected[1]:
            rec["verdict"] = "selected"
            if stale_used:
                rec["note"] = "path uses stale latency data"
        elif rec["verdict"] == "eligible":
            rec.update({"verdict": "rejected", "layer": "rank", "reason": "outranked by selected candidate"})
    return ResolveResult(selected[1] if selected else None, selected[0] if selected else None, considered, stale_used)


def explain(decision: Decision) -> str:
    """Operator-readable explanation (MC-067)."""
    lines = [
        f"decision {decision.decision_id} ({decision.operation}) tenant={decision.tenant} mode={decision.mode}",
        f"  graph revision {decision.graph_revision}, config generation {decision.config_generation}, release {decision.release}",
        f"  inputs: {decision.inputs}",
        f"  outcome: {decision.outcome}; selected={decision.selected} latency_ms={decision.latency_ms}",
        f"  precedence: {' > '.join(PRECEDENCE)}",
    ]
    if not decision.considered:
        lines.append("  no reachable node advertised the capability over live links")
    for rec in decision.considered:
        why = f" [{rec.get('layer')}] {rec.get('reason')}" if rec["verdict"] == "rejected" else ""
        note = f" ({rec['note']})" if "note" in rec else ""
        lines.append(f"  - {rec['node']:<24} {rec['latency_ms']:>9.3f} ms  {rec['verdict']}{why}{note}")
    return "\n".join(lines)
