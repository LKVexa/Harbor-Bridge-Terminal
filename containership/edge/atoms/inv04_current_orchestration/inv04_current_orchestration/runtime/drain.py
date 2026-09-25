"""Drain transaction coordinator with crash recovery (components 7, 8, 9, 21, 22).

Phases (journaled write-ahead, one record per transition):

    requested -> preflight_ok -> cordoned -> evicting -> verifying -> completed
         \\-> rejected                \\-> aborted -> uncordoned        (before any eviction)
                                           \\-> failed_cordoned               (after >=1 eviction)

Irreversibility: cordon is reversible; the first successful eviction is the
point of no return.  Before it, any failure rolls back by uncordoning.  After
it, the coordinator never uncordons automatically (the node's workloads are
already moving) — it stops in ``failed_cordoned`` with a stable reason for the
operator runbook.

Recovery: ``recover()`` replays the journal, and for every non-terminal
operation resumes from its last durable phase.  Evictions are keyed by pod UID,
so a replayed eviction of an already-evicted pod is a no-op ("already_gone")
and a replacement pod with a new UID is never touched.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .api import ClusterAPI
from .errors import NotFound, RuntimeFault
from .journal import Journal
from .objects import PodSpec
from .policy import classify_for_drain, may_evict_from, node_state, pdb_status, selects, stateful_order
from .resilience import Backoff, Context, retry_call
from .scheduling import plan_drain_capacity

TERMINAL = frozenset({"completed", "rejected", "uncordoned", "failed_cordoned"})


@dataclass
class DrainOptions:
    delete_emptydir_data: bool = False
    force_unmanaged: bool = False
    ignore_daemonsets: bool = True
    eviction_attempts: int = 6
    verify_timeout: float = 30.0
    heartbeat_grace: float = 40.0
    dry_run: bool = False


@dataclass
class DrainResult:
    op_id: str
    node: str
    phase: str
    reason: str = ""
    evicted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"op_id": self.op_id, "node": self.node, "phase": self.phase, "reason": self.reason,
                "evicted": sorted(self.evicted), "skipped": sorted(self.skipped), "blocked": sorted(self.blocked)}


class DrainCoordinator:
    def __init__(self, api: ClusterAPI, journal: Journal, *, fencing_token: Callable[[], int] = lambda: 0,
                 clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
                 backoff: Backoff | None = None, on_transition: Callable[[str, str, str], None] | None = None,
                 settle: Callable[[], object] | None = None):
        self.api, self.journal = api, journal
        self.fencing_token, self.clock, self.sleep = fencing_token, clock, sleep
        self.backoff = backoff or Backoff(base=0.05, cap=2.0)
        self.on_transition = on_transition or (lambda op, phase, reason: None)
        self.settle: Callable[[], object] = settle or (lambda: None)

    # ------------------------------------------------------------ journaling
    def _mark(self, op_id: str, node: str, phase: str, reason: str = "", **data) -> None:
        self.journal.append(op_id, "drain", phase, {"node": node, "reason": reason, **data})
        self.on_transition(op_id, phase, reason)

    # ------------------------------------------------------------------ API
    def drain(self, node: str, *, op_id: str, options: DrainOptions | None = None, ctx: Context | None = None) -> DrainResult:
        opts = options or DrainOptions()
        ctx = ctx or Context(timeout=300.0)
        last = self.journal.last_phase(op_id)
        if last in TERMINAL:
            return self._result_from_journal(op_id)  # idempotent replay
        if last is None:
            self._mark(op_id, node, "requested", options=opts.__dict__)
        return self._run(op_id, node, opts, ctx)

    def recover(self, *, options: DrainOptions | None = None) -> list[DrainResult]:
        out = []
        for op_id in self.journal.open_operations(TERMINAL):
            entries = self.journal.for_op(op_id)
            if entries[0].kind != "drain":
                continue
            node = entries[0].data["node"]
            opts = options or DrainOptions(**{k: v for k, v in entries[0].data.get("options", {}).items()
                                              if k in DrainOptions.__dataclass_fields__})
            self._mark(op_id, node, "recovering", from_phase=entries[-1].phase)
            out.append(self._run(op_id, node, opts, Context(timeout=300.0)))
        return out

    # ------------------------------------------------------------- internals
    def _phases(self, op_id: str) -> list[str]:
        return [e.phase for e in self.journal.for_op(op_id)]

    def _result_from_journal(self, op_id: str) -> DrainResult:
        es = self.journal.for_op(op_id)
        res = DrainResult(op_id, es[0].data["node"], es[-1].phase, es[-1].data.get("reason", ""))
        for e in es:
            if e.phase == "evicted":
                res.evicted.append(e.data["pod"])
        return res

    def _run(self, op_id: str, node: str, opts: DrainOptions, ctx: Context) -> DrainResult:
        res = DrainResult(op_id, node, "requested")
        phases = self._phases(op_id)
        evicted_uids = {e.data["uid"] for e in self.journal.for_op(op_id) if e.phase == "evicted"}
        res.evicted = [e.data["pod"] for e in self.journal.for_op(op_id) if e.phase == "evicted"]
        try:
            ctx.check("drain")
            nd = self.api.get_node(node)
        except NotFound:
            if evicted_uids:
                self._mark(op_id, node, "completed", "node_deleted")
                res.phase, res.reason = "completed", "node_deleted"
                return res
            self._mark(op_id, node, "rejected", "unknown_node")
            res.phase, res.reason = "rejected", "unknown_node"
            return res

        state = node_state(nd, self.clock(), heartbeat_grace=opts.heartbeat_grace)
        if not may_evict_from(state):
            return self._abort(op_id, node, res, f"node_{state}", evicted_uids)

        nodes, _ = self.api.list_nodes()
        pods, _ = self.api.list_pods()
        pdbs = self.api.list_pdbs()
        on_node = [p for p in pods if p.node == node]
        decisions = {p.meta.uid: classify_for_drain(p, delete_emptydir_data=opts.delete_emptydir_data,
                                                    force_unmanaged=opts.force_unmanaged,
                                                    ignore_daemonsets=opts.ignore_daemonsets) for p in on_node}
        res.skipped = sorted(d.pod for d in decisions.values() if d.action == "skip")
        res.blocked = sorted(f"{d.pod}:{d.reason}" for d in decisions.values() if d.action == "block")
        victims = stateful_order([p for p in on_node if decisions[p.meta.uid].action == "evict"])

        if "preflight_ok" not in phases:
            if res.blocked:
                self._mark(op_id, node, "rejected", "drain_policy", blocked=res.blocked)
                res.phase, res.reason = "rejected", "drain_policy"
                return res
            # Budget preflight (parity with model.Cluster.drain): for every budget that
            # selects a victim, the healthy pods *off* this node must already satisfy
            # desiredHealthy.  Evictions then proceed one at a time and retry on 429
            # while replacements become ready, exactly like the Eviction API.
            victim_uids = {v.meta.uid for v in victims}
            for pdb in pdbs:
                if not any(selects(pdb, v) for v in victims if v.phase not in ("Succeeded", "Failed")):
                    continue
                st = pdb_status(pdb, pods)
                off_node = sum(1 for p in pods if selects(pdb, p) and p.meta.uid not in victim_uids
                               and p.phase == "Running" and p.ready and p.meta.deletion_timestamp is None)
                if off_node < st.desired_healthy:
                    self._mark(op_id, node, "rejected", "budget_breach", pdb=pdb.meta.key,
                               remaining=off_node, desired_healthy=st.desired_healthy)
                    res.phase, res.reason = "rejected", "budget_breach"
                    return res
            live = [v for v in victims if v.phase not in ("Succeeded", "Failed") and v.meta.owner_kind not in ("Job",)]
            _, failures = plan_drain_capacity(live, [n for n in nodes if n.name != node], pods, node)
            if failures:
                self._mark(op_id, node, "rejected", "no_capacity", unplaceable=[f.pod for f in failures])
                res.phase, res.reason = "rejected", "no_capacity"
                return res
            if opts.dry_run:
                self._mark(op_id, node, "completed", "dry_run", would_evict=[v.meta.key for v in victims])
                res.phase, res.reason = "completed", "dry_run"
                return res
            self._mark(op_id, node, "preflight_ok", victims=[v.meta.key for v in victims])

        if "cordoned" not in phases:
            try:
                def cordon():
                    cur = self.api.get_node(node)
                    return self.api.set_unschedulable(node, True, expected_rv=cur.meta.resource_version, uid=nd.meta.uid)
                retry_call(cordon, ctx=ctx, attempts=5, backoff=self.backoff, sleep=self.sleep)
            except RuntimeFault as exc:
                return self._abort(op_id, node, res, f"cordon_failed:{exc.code}", evicted_uids)
            self._mark(op_id, node, "cordoned")

        if "evicting" not in self._phases(op_id):
            self._mark(op_id, node, "evicting")
        for v in victims:
            if v.meta.uid in evicted_uids:
                continue
            try:
                def evict_one(v: PodSpec = v) -> str:
                    return self.api.evict(v.meta.key, uid=v.meta.uid, fencing_token=self.fencing_token())

                def on_retry(_n: int, _e: BaseException) -> None:
                    self.settle()

                outcome = retry_call(evict_one, ctx=ctx, attempts=opts.eviction_attempts, backoff=self.backoff,
                                     sleep=self.sleep, on_retry=on_retry)
            except RuntimeFault as exc:
                return self._abort(op_id, node, res, f"eviction_failed:{exc.reason}", evicted_uids)
            self._mark(op_id, node, "evicted", pod=v.meta.key, uid=v.meta.uid, outcome=outcome)
            evicted_uids.add(v.meta.uid)
            res.evicted.append(v.meta.key)
            self.settle()

        self._mark(op_id, node, "verifying")
        deadline = self.clock() + opts.verify_timeout
        while True:
            self.settle()
            pods, _ = self.api.list_pods()
            remaining = [p for p in pods if p.node == node and p.meta.uid in evicted_uids]
            if not remaining:
                break
            if self.clock() >= deadline:
                self._mark(op_id, node, "failed_cordoned", "verify_timeout", remaining=[p.meta.key for p in remaining])
                res.phase, res.reason = "failed_cordoned", "verify_timeout"
                return res
            self.sleep(0.05)
        self._mark(op_id, node, "completed", "drained")
        res.phase, res.reason = "completed", "drained"
        return res

    def _abort(self, op_id: str, node: str, res: DrainResult, reason: str, evicted_uids: set[str]) -> DrainResult:
        self._mark(op_id, node, "aborted", reason)
        if evicted_uids:
            self._mark(op_id, node, "failed_cordoned", reason)
            res.phase, res.reason = "failed_cordoned", reason
            return res
        if "cordoned" in self._phases(op_id):
            try:
                cur = self.api.get_node(node)
                self.api.set_unschedulable(node, False, expected_rv=cur.meta.resource_version, uid=cur.meta.uid)
            except RuntimeFault as exc:
                self._mark(op_id, node, "failed_cordoned", f"{reason};uncordon_failed:{exc.code}")
                res.phase, res.reason = "failed_cordoned", reason
                return res
        self._mark(op_id, node, "uncordoned", reason)
        res.phase, res.reason = "uncordoned", reason
        return res
