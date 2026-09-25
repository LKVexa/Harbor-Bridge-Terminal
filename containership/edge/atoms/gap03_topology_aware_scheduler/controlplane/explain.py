"""MC-022 - Operator explain API / view (GAP03-EXPLAIN/1).

Immutable decision records (content-addressed inputs, no secrets), stored
append-only; authorization-scoped query (tenants see their own records,
operators all), bounded time range + pagination, audited and rate-limited
access; a non-mutating replay tool re-scores from the recorded snapshot and
flags divergence caused by a code/config/scoring-version change.
"""
from __future__ import annotations

import time

from .. import scheduler as sch
from . import canonical
from .admission import TokenBucket
from .durable import DurableStore
from .errors import SchedulerError

SCHEMA = "GAP03-EXPLAIN/1"
RETENTION_DAYS = 90
MAX_RANGE_S = 7 * 86400


class ExplainStore(DurableStore):
    KIND = "explain"
    SNAPSHOT_EVERY = 10**12

    def initial_state(self):
        return {"records": {}, "order": []}

    def apply(self, state, op):
        rec = op["record"]
        if rec["txn"] in state["records"]:
            return rec["txn"]  # immutable: first write wins
        state["records"][rec["txn"]] = rec
        state["order"].append(rec["txn"])
        return rec["txn"]


class Explain:
    def __init__(self, store: ExplainStore, *, audit=None, clock=time.time, rate=20.0, metrics=None):
        self.store, self.audit, self.clock, self.metrics = store, audit, clock, metrics
        self.buckets: dict[str, TokenBucket] = {}
        self.rate = rate

    def record(self, *, txn, tenant, workload, inputs, scored, fairness, snapshot_nodes=None, infeasible=None,
               components=None, sources=None):
        rec = {"schema": SCHEMA, "txn": txn, "tenant": tenant, "workload_ref": workload.get("id"),
               "ts": int(self.clock()), "inputs": inputs,
               "candidates": [{"node": c.node, "rank_score": c.rank_score, "locality_cost": c.locality_cost,
                               "spread_penalty": c.spread_penalty, "failure_domain": c.failure_domain} for c in scored],
               "tie_break": "ascending (rank_score, node id); node ids compared by code point",
               "hard_filter": dict(sorted((infeasible or {}).items())),
               "soft_components": components or {},
               "sources": sources or {},
               "fairness": {"allowed": fairness.allowed, "reason": fairness.reason, "reserved": fairness.reserved_slots,
                            "held": fairness.held_slots, "capacity": fairness.capacity, "free": fairness.free_capacity,
                            "protected_for_others": fairness.protected_for_other_tenants,
                            "surplus": fairness.surplus_available, "state_token": fairness.state_token},
               "snapshot_ref": canonical.digest(snapshot_nodes) if snapshot_nodes is not None else None,
               "snapshot": snapshot_nodes}
        self.store.submit({"type": "record", "record": rec})
        return rec

    def query(self, principal: dict, *, txn=None, workload=None, since=None, until=None, page_token=0, page_size=50):
        sub = principal.get("sub", "?")
        bucket = self.buckets.setdefault(sub, TokenBucket(self.rate, self.rate))
        if bucket.take():
            raise SchedulerError("OVERLOADED", "explain query rate")
        perms, own = principal.get("perms", set()), principal.get("tenant")
        if "explain.read" not in perms and not own:
            raise SchedulerError("PERMISSION_DENIED", "explain.read required")
        now = self.clock()
        until = until or now
        since = since if since is not None else until - 86400
        if until - since > MAX_RANGE_S or until < since:
            raise SchedulerError("INVALID_ARGUMENT", "time range too wide")
        out, nxt = [], None
        order = self.store.state["order"]
        for i in range(page_token, len(order)):
            r = self.store.state["records"][order[i]]
            if txn and r["txn"] != txn:
                continue
            if workload and r["workload_ref"] != workload:
                continue
            if not since <= r["ts"] <= until:
                continue
            if "explain.read" not in perms and r["tenant"] != own:
                continue
            if len(out) >= min(page_size, 200):
                nxt = i
                break
            out.append(r)
        if self.metrics:
            self.metrics.inc("gap03_explain_queries_total", result="ok")
        if self.audit:
            self.audit.append(actor=sub, action="explain.query", target=str(txn or workload or "range"), result="ok",
                              detail={"returned": len(out)})
        return {"records": out, "next_page_token": nxt}

    def retention_plan(self, *, now: float, retention_days: int = RETENTION_DAYS, holds: set[str] | frozenset = frozenset()) -> dict:
        """Records older than the retention window become eligible for archive (never those under incident hold)."""
        cutoff = now - retention_days * 86400
        old = [t for t in self.store.state["order"] if self.store.state["records"][t]["ts"] < cutoff]
        return {"retention_days": retention_days, "eligible_for_archive": [t for t in old if t not in holds],
                "held": sorted(set(old) & set(holds)), "privacy": "records hold pseudonymous refs + content digests only"}

    def replay(self, txn: str, *, scoring_version: str) -> dict:
        """Re-run a historical decision in non-mutating mode; report divergence."""
        r = self.store.state["records"].get(txn)
        if r is None:
            raise SchedulerError("INVALID_ARGUMENT", "unknown txn")
        if r["snapshot"] is None:
            return {"txn": txn, "replayable": False, "reason": "snapshot not captured"}
        from types import MappingProxyType
        snap = sch.TopologySnapshot(MappingProxyType({k: tuple(v) for k, v in r["snapshot"].items()}),
                                    r["inputs"]["topology_generation"])
        anchor = r["sources"].get("anchor")
        scored = sch._score_snapshot(snap, anchor, [c["node"] for c in r["candidates"]],
                                     spread_from=r["sources"].get("spread_from", []))
        now = [c.node for c in scored]
        then = [c["node"] for c in r["candidates"]]
        version_changed = scoring_version != r["inputs"]["scoring_version"]
        return {"txn": txn, "replayable": True, "identical": now == then, "then": then, "now": now,
                "version_changed": version_changed,
                "divergence_cause": None if now == then else ("scoring_version" if version_changed else "nondeterminism")}
