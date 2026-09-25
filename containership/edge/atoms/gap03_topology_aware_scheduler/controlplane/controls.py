"""MC-017 - Emergency freeze / quarantine / disable controls (GAP03-CTL/1).

Scopes: global, tenant, region, site, node, workload_class, txn.
Modes: freeze-new (block new placements), drain (block new, allow in-flight
until deadline), quarantine (block placements onto scope), disable-commit
(block commits; scoring/explain allowed), hard-stop (block everything except
health/explain/release/rollback).  Persisted durably; expiry is enforced on
read; CLI/API is idempotent (control_id) with optimistic concurrency.
"""
from __future__ import annotations

import time

from .durable import DurableStore
from .errors import SchedulerError

SCOPES = ("global", "tenant", "region", "site", "node", "workload_class", "txn")
MODES = {
    "freeze-new": {"placement.commit", "placement.score_new"},
    "drain": {"placement.commit"},
    "quarantine": {"placement.commit"},
    "disable-commit": {"placement.commit", "topology.mutate"},
    "hard-stop": {"placement.commit", "placement.score_new", "topology.mutate", "score"},
}
ALWAYS_ALLOWED = {"health", "explain", "release", "rollback", "reconcile"}
HIGH_BLAST = {("global", "hard-stop"), ("global", "disable-commit"), ("region", "hard-stop")}
MAX_TTL_S = 7 * 86400


class ControlStore(DurableStore):
    KIND = "controls"

    def initial_state(self):
        return {"generation": 0, "controls": {}}

    def apply(self, state, op):
        if op["expected_generation"] != state["generation"]:
            raise SchedulerError("STALE_STATE", "controls changed concurrently")
        cid = op["control_id"]
        if op["type"] == "create":
            if cid in state["controls"]:
                return state["generation"]  # idempotent
            state["controls"][cid] = op["control"]
        elif op["type"] == "extend":
            c = state["controls"].get(cid)
            if c is None:
                raise SchedulerError("INVALID_ARGUMENT", "unknown control")
            c["expires_at"] = op["expires_at"]
        elif op["type"] == "exempt":
            c = state["controls"].get(cid)
            if c is None:
                raise SchedulerError("INVALID_ARGUMENT", "unknown control")
            c.setdefault("exemptions", []).append(op["exemption"])
        elif op["type"] == "clear":
            if cid not in state["controls"]:
                return state["generation"]
            state["controls"][cid]["cleared"] = True
        else:
            raise SchedulerError("INVALID_ARGUMENT", "unknown op")
        state["generation"] += 1
        return state["generation"]


class Controls:
    def __init__(self, store: ControlStore, *, audit=None, clock=time.time, metrics=None):
        self.store, self.audit, self.clock, self.metrics = store, audit, clock, metrics

    def _authorize(self, principal, scope_kind, mode, approvers):
        perms = principal.get("perms", set())
        if "control.write" not in perms and "control.hard_stop" not in perms:
            raise SchedulerError("PERMISSION_DENIED", "control.write required")
        if mode == "hard-stop" and "control.hard_stop" not in perms:
            raise SchedulerError("PERMISSION_DENIED", "hard-stop requires break-glass")
        if (scope_kind, mode) in HIGH_BLAST and len({a for a in approvers if a != principal["sub"]}) < 1:
            raise SchedulerError("PERMISSION_DENIED", "dual approval required for high-blast-radius control")

    def create(self, principal: dict, *, control_id: str, scope_kind: str, scope_value: str, mode: str, reason: str,
               ticket: str, ttl_s: int, approvers: tuple[str, ...] = (), drain_deadline_s: int = 300) -> int:
        if scope_kind not in SCOPES or mode not in MODES:
            raise SchedulerError("INVALID_ARGUMENT", "unknown scope/mode")
        if not reason or not ticket:
            raise SchedulerError("INVALID_ARGUMENT", "reason and incident/change ticket required")
        if not 0 < ttl_s <= MAX_TTL_S:
            raise SchedulerError("INVALID_ARGUMENT", "ttl bounds")
        try:
            self._authorize(principal, scope_kind, mode, approvers)
        except SchedulerError:
            if self.audit:
                self.audit.append(actor=principal.get("sub", "?"), action="control.create", target=f"{scope_kind}:{scope_value}",
                                  result="denied", reason=reason)
            raise
        now = self.clock()
        ctl = {"scope": scope_kind, "value": scope_value, "mode": mode, "reason": reason, "ticket": ticket,
               "actor": principal["sub"], "created_at": now, "expires_at": now + ttl_s, "cleared": False,
               "drain_deadline": now + drain_deadline_s, "approvers": sorted(approvers)}
        g = self.store.submit({"type": "create", "control_id": control_id, "control": ctl,
                               "expected_generation": self.store.state["generation"]})
        if self.audit:
            self.audit.append(actor=principal["sub"], action="control.create", target=f"{scope_kind}:{scope_value}",
                              result="ok", reason=reason, generation=g, after=ctl)
        return g

    def extend(self, principal, control_id: str, ttl_s: int, expected_generation: int) -> int:
        self._authorize(principal, "tenant", "freeze-new", ())
        if not 0 < ttl_s <= MAX_TTL_S:
            raise SchedulerError("INVALID_ARGUMENT", "ttl bounds")
        return self.store.submit({"type": "extend", "control_id": control_id, "expires_at": self.clock() + ttl_s,
                                  "expected_generation": expected_generation})

    def clear(self, principal, control_id: str, expected_generation: int) -> int:
        self._authorize(principal, "tenant", "freeze-new", ())
        g = self.store.submit({"type": "clear", "control_id": control_id, "expected_generation": expected_generation})
        if self.audit:
            self.audit.append(actor=principal["sub"], action="control.clear", target=control_id, result="ok", generation=g)
        return g

    def exempt(self, principal: dict, *, control_id: str, scope: dict, ttl_s: int, reason: str, ticket: str) -> int:
        """Audited, break-glass, narrowly scoped, time-limited exception to one control (the only override path)."""
        if "control.hard_stop" not in principal.get("perms", set()):
            raise SchedulerError("PERMISSION_DENIED", "exemptions require break-glass")
        if not scope or not reason or not ticket:
            raise SchedulerError("INVALID_ARGUMENT", "exemption needs a non-empty scope, reason and ticket")
        if not 0 < ttl_s <= 3600:
            raise SchedulerError("INVALID_ARGUMENT", "exemption ttl must be 1..3600 s")
        c = self.store.state["controls"].get(control_id)
        if c is None:
            raise SchedulerError("INVALID_ARGUMENT", "unknown control")
        ex = {"scope": dict(scope), "expires_at": self.clock() + ttl_s, "actor": principal["sub"], "reason": reason, "ticket": ticket}
        g = self.store.submit({"type": "exempt", "control_id": control_id, "exemption": ex,
                               "expected_generation": self.store.state["generation"]})
        if self.audit:
            self.audit.append(actor=principal["sub"], action="control.exempt", target=control_id, result="ok", reason=reason,
                              generation=g, after=ex)
        return g

    def active(self) -> list[dict]:
        now = self.clock()
        return [dict(c, id=i) for i, c in sorted(self.store.state["controls"].items()) if not c["cleared"] and c["expires_at"] > now]

    def check(self, operation: str, *, scope: dict, inflight: bool = False) -> None:
        """Raise FROZEN if any active control blocks ``operation`` in ``scope``."""
        if operation in ALWAYS_ALLOWED:
            return
        now = self.clock()
        for c in self.active():
            if operation not in MODES[c["mode"]]:
                continue
            if c["scope"] != "global" and scope.get(c["scope"]) != c["value"]:
                continue
            if c["mode"] == "drain" and inflight and now < c["drain_deadline"]:
                continue
            if any(e["expires_at"] > now and all(scope.get(k) == v for k, v in e["scope"].items())
                   for e in c.get("exemptions", [])):
                continue
            if self.metrics:
                self.metrics.inc("gap03_control_blocks_total", mode=c["mode"])
            raise SchedulerError("FROZEN", f"{c['mode']} on {c['scope']}")

    def summary(self, *, privileged: bool) -> list[dict]:
        return [{"id": c["id"], "scope": c["scope"], "mode": c["mode"], "expires_at": int(c["expires_at"]),
                 **({"value": c["value"], "reason": c["reason"], "ticket": c["ticket"]} if privileged else {})}
                for c in self.active()]
