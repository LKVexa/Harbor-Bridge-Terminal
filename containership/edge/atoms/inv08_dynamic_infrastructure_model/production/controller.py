"""Component 27 - desired-vs-observed reconciliation controller.

Contract ``PK_DYN_RECONCILE/1``
* Desired state = ``model.Pool.nodes`` after ``Pool.tick(now, demand)``
  (skipped while frozen).  Observed state = ``provider.list()``.
* Managed nodes = nodes whose most recent DONE create/delete op in the journal
  is a create.  Only managed nodes are ever deleted; observed nodes that are
  neither managed, pinned (INV-06) nor quarantined are *foreign* and are only
  reported (drift, OPERATOR_REQUIRED) - never deleted.
* Operations: create(node); delete(node) = drain then delete; drain-only for
  quarantined nodes.  Each op is journaled PENDING before the provider call
  and DONE/FAILED after; op ids are ``<kind>:<node>:<n>`` and the provider
  idempotency key is the op id, so a replay after a crash never duplicates.
* Every provider call carries the leader fencing epoch; the store fence is
  checked before each op (stale writer rejection at both boundaries).
* Kill switch -> no provider mutation (outcome BLOCKED).  Not leader ->
  RETRYABLE_FAILURE, no action.
* Conflict (provider says node exists but we did not create it) -> FAILED,
  reported, no retry.  Terminal create failure or a PENDING create older than
  ``op_timeout`` that the provider does not show -> rollback: the node is
  removed from the Pool (desired state reverts to observed reality) and the op
  is journaled ROLLED_BACK / TIMED_OUT.
* Convergence: after the round, desired == observed(managed) and no foreign
  nodes -> ``converged``; otherwise ``drift`` lists missing/unexpected/foreign.
"""
from __future__ import annotations

import random
from typing import Callable

from ..model import Pool
from .core import Inv08Error, Outcome
from .journal import Journal
from .leader import LEADER_KEY, LeaderElector
from .resilience import DEFAULT_POLICIES, RetryPolicy, call_with_retry


class Controller:
    def __init__(self, pool: Pool, provider, journal: Journal, elector: LeaderElector, *,
                 clock: Callable[[], float], site: str = "test-site", controls=None,
                 retry_policy: RetryPolicy | None = None, rng: random.Random | None = None,
                 sleep: Callable[[float], None] | None = None, op_timeout: float = 300.0,
                 pinned: set[str] | None = None, crash_hook: Callable[[str], None] | None = None,
                 breaker=None) -> None:
        self.pool, self.provider, self.journal, self.elector = pool, provider, journal, elector
        self.clock, self.site, self.controls = clock, site, controls
        self.policy = retry_policy or DEFAULT_POLICIES["provider"]
        self.rng = rng or random.Random(0)
        self.sleep = sleep or (lambda s: None)
        self.op_timeout = op_timeout
        self.pinned = set(pinned or ())
        self.crash_hook = crash_hook or (lambda point: None)
        self.breaker = breaker
        self.last_heartbeat: float | None = None
        self.rounds = 0

    # ------------------------------------------------------------ helpers
    @classmethod
    def recover(cls, pool_params: dict, provider, journal: Journal, elector: LeaderElector, **kw) -> "Controller":
        """Restart path: rebuild desired state from the journal's managed set
        intersected with what the provider actually reports."""
        tmp = cls(Pool(**pool_params), provider, journal, elector, **kw)
        observed = tmp._call(lambda: provider.list(), "list")
        now = tmp.clock()
        managed = tmp.managed() & set(observed)
        ttl = pool_params.get("lease_ttl", 10)
        nodes = {n: {"expires": now + ttl, "busy": False} for n in sorted(managed)}
        tmp.pool = Pool(**pool_params, nodes=nodes)
        return tmp

    def managed(self) -> set[str]:
        latest: dict[str, tuple[int, str]] = {}
        for op in self.journal.state.get("ops", {}).values():
            if op["status"] == "DONE" and op["kind"] in ("create", "delete"):
                if op["seq"] > latest.get(op["node_id"], (-1, ""))[0]:
                    latest[op["node_id"]] = (op["seq"], op["kind"])
        return {n for n, (_, k) in latest.items() if k == "create"}

    def _call(self, fn, dep: str):
        wrapped = fn
        return call_with_retry(wrapped, policy=self.policy, rng=self.rng, clock=self.clock,
                               sleep=self.sleep, dependency=f"provider:{dep}", breaker=self.breaker)

    def _op_id(self, kind: str, node: str) -> tuple[str, bool]:
        ops = self.journal.state.get("ops", {})
        prefix = f"{kind}:{node}:"
        mine = [k for k in ops if k.startswith(prefix)]
        for k in mine:
            if ops[k]["status"] == "PENDING":
                return k, True
        return f"{prefix}{len(mine) + 1}", False

    def _fence(self) -> int:
        lead = self.elector.require()
        self.elector.store.check_fence(LEADER_KEY, lead.epoch)
        return lead.epoch

    def _run(self, kind: str, node: str, report: dict) -> bool:
        fence = self._fence()
        op_id, resumed = self._op_id(kind, node)
        now = self.clock()
        if not resumed:
            self.journal.append(op_id, "PENDING", kind=kind, node_id=node, ts=now)
        self.crash_hook(f"{kind}:after_pending")
        try:
            if kind == "create":
                self._call(lambda: self.provider.create(node, {"site": self.site}, idempotency_key=op_id,
                                                        fence=fence), "create")
            elif kind == "drain":
                self._call(lambda: self.provider.drain(node, idempotency_key=op_id, fence=fence), "drain")
            elif kind == "delete":
                self._call(lambda: self.provider.drain(node, idempotency_key=op_id + "#drain",
                                                       fence=fence), "drain")
                self.crash_hook("delete:after_drain")
                self._call(lambda: self.provider.delete(node, idempotency_key=op_id, fence=fence), "delete")
        except Inv08Error as exc:
            self.journal.append(op_id, "FAILED", kind=kind, node_id=node, ts=self.clock(),
                                detail={"code": exc.code, "outcome": exc.outcome.value})
            report["failed"].append({"op": op_id, "code": exc.code})
            if exc.code == "INV08.PROVIDER.CONFLICT":
                report["conflicts"].append(node)
            if exc.code.startswith("INV08.FENCE"):
                raise
            if kind == "create" and not exc.retryable:
                self._rollback_create(node, op_id, report, "TERMINAL")
            return False
        self.crash_hook(f"{kind}:after_call")
        self.journal.append(op_id, "DONE", kind=kind, node_id=node, ts=self.clock())
        report["ops"].append(op_id)
        return True

    def _rollback_create(self, node: str, op_id: str, report: dict, why: str) -> None:
        self.pool.nodes.pop(node, None)
        self.journal.append(op_id, "ROLLED_BACK" if why == "TERMINAL" else "TIMED_OUT", kind="create",
                            node_id=node, ts=self.clock(), detail={"why": why})
        report["rolled_back"].append(node)

    def _resolve_pending(self, observed: dict, report: dict) -> None:
        now = self.clock()
        for op_id, op in sorted(self.journal.pending().items()):
            node, kind = op["node_id"], op["kind"]
            present = node in observed
            if kind == "create" and present:
                self.journal.append(op_id, "DONE", kind=kind, node_id=node, ts=now,
                                    detail={"recovered": True})
                report["recovered"].append(op_id)
            elif kind in ("delete",) and not present:
                self.journal.append(op_id, "DONE", kind=kind, node_id=node, ts=now,
                                    detail={"recovered": True})
                report["recovered"].append(op_id)
            elif kind == "drain" and present and observed[node]["state"] == "DRAINING":
                self.journal.append(op_id, "DONE", kind=kind, node_id=node, ts=now,
                                    detail={"recovered": True})
                report["recovered"].append(op_id)
            elif now - op["started"] > self.op_timeout:
                if kind == "create":
                    self._rollback_create(node, op_id, report, "TIMEOUT")
                else:
                    self.journal.append(op_id, "TIMED_OUT", kind=kind, node_id=node, ts=now)
                report["timed_out"].append(op_id)
            # else: left PENDING; re-issued below with the same idempotency key

    # ------------------------------------------------------------ main loop
    def reconcile(self, demand: float) -> dict:
        self.rounds += 1
        now = self.clock()
        self.last_heartbeat = now
        report: dict = {"round": self.rounds, "ts": now, "ops": [], "failed": [], "conflicts": [],
                        "rolled_back": [], "recovered": [], "timed_out": [], "frozen": False}
        if self.controls is not None and self.controls.is_killed():
            return dict(report, outcome=Outcome.BLOCKED.value, reason="kill switch engaged")
        try:
            lead = self.elector.try_acquire()
        except Inv08Error as exc:          # store outage/partition: cannot prove leadership
            self.elector.leadership = None
            return dict(report, outcome=Outcome.RETRYABLE_FAILURE.value, reason=exc.code)
        if lead is None:
            return dict(report, outcome=Outcome.RETRYABLE_FAILURE.value, reason="not leader")
        quarantined = set(self.controls.quarantined) if self.controls is not None else set()
        try:
            observed = self._call(lambda: self.provider.list(), "list")
            self._resolve_pending(observed, report)
            for n in quarantined | self.pinned:
                self.pool.nodes.pop(n, None)
            if self.controls is not None and self.controls.is_frozen(self.site):
                report["frozen"] = True
            else:
                self.pool.tick(now, demand)
            desired = set(self.pool.nodes)
            managed = self.managed()
            for node in sorted(desired - set(observed)):
                self._run("create", node, report)
            for node in sorted((set(observed) & managed) - desired - quarantined - self.pinned):
                self._run("delete", node, report)
            for node in sorted(quarantined & set(observed)):
                if observed[node]["state"] != "DRAINING":
                    self._run("drain", node, report)
            after = self._call(lambda: self.provider.list(), "list")
        except Inv08Error as exc:
            return dict(report, outcome=(Outcome.TERMINAL_FAILURE if exc.code.startswith("INV08.FENCE")
                                         else exc.outcome).value, reason=exc.code)
        managed = self.managed()
        desired = set(self.pool.nodes)
        drift = {
            "missing": sorted(desired - set(after)),
            "unexpected": sorted((set(after) & managed) - desired - quarantined - self.pinned),
            "foreign": sorted(set(after) - managed - quarantined - self.pinned),
        }
        converged = not any(drift.values())
        outcome = Outcome.SUCCESS if converged and not report["failed"] else (
            Outcome.OPERATOR_REQUIRED if drift["foreign"] or report["conflicts"] else Outcome.PARTIAL)
        return dict(report, outcome=outcome.value, converged=converged, drift=drift,
                    desired=sorted(desired), observed=sorted(after))
