"""MC-016 - Safe degraded-mode / failover policy (GAP03-DEGRADED/1).

A declarative dependency x operation matrix decides fail-open / fail-closed.
Mutating commits are blocked whenever ownership, authoritative state, identity
or integrity cannot be proven; read-only explain stays available.  Operator
overrides are scoped, time-limited, require break-glass authorization and an
explicit risk acknowledgement, and are audited.
"""
from __future__ import annotations

import time

from .errors import SchedulerError

OPS = ("score", "commit", "topology_mutate", "explain", "health")
# dependency: {op: "closed"|"open"|"stale_ok"}, max stale TTL seconds
MATRIX = {
    "identity":      ({"score": "open", "commit": "closed", "topology_mutate": "closed", "explain": "closed", "health": "open"}, 0),
    "topology_store": ({"score": "stale_ok", "commit": "closed", "topology_mutate": "closed", "explain": "open", "health": "open"}, 60),
    "ledger":        ({"score": "stale_ok", "commit": "closed", "topology_mutate": "open", "explain": "open", "health": "open"}, 30),
    "entitlement":   ({"score": "stale_ok", "commit": "stale_ok", "topology_mutate": "open", "explain": "open", "health": "open"}, 300),
    "coordination":  ({"score": "open", "commit": "closed", "topology_mutate": "closed", "explain": "open", "health": "open"}, 0),
    "audit":         ({"score": "open", "commit": "closed", "topology_mutate": "closed", "explain": "open", "health": "open"}, 0),
    "gap02":         ({"score": "stale_ok", "commit": "stale_ok", "topology_mutate": "open", "explain": "open", "health": "open"}, 300),
    "gap14":         ({"score": "open", "commit": "open", "topology_mutate": "open", "explain": "open", "health": "open"}, 900),
    "pln05":         ({"score": "open", "commit": "open", "topology_mutate": "open", "explain": "open", "health": "open"}, 1800),
    "sch01":         ({"score": "open", "commit": "closed", "topology_mutate": "open", "explain": "open", "health": "open"}, 0),
    "time":          ({"score": "open", "commit": "closed", "topology_mutate": "closed", "explain": "open", "health": "open"}, 0),
}
RECOVERY_ORDER = ("time", "identity", "coordination", "audit", "topology_store", "ledger", "entitlement", "sch01",
                  "gap02", "gap14", "pln05")


class DegradedPolicy:
    def __init__(self, *, clock=time.time, audit=None, metrics=None):
        self.clock, self.audit, self.metrics = clock, audit, metrics
        self.status = {d: {"up": True, "since": clock(), "last_good": clock(), "generation": None} for d in MATRIX}
        self.overrides: list[dict] = []
        self.reconciled = True

    def report(self, dep: str, up: bool, *, generation: int | None = None):
        if dep not in MATRIX:
            raise SchedulerError("INVALID_ARGUMENT", "unknown dependency")
        st = self.status[dep]
        now = self.clock()
        if up:
            st["last_good"] = now
            st["generation"] = generation if generation is not None else st["generation"]
            if not st["up"]:
                self.reconciled = False  # restoration requires reconciliation before clearing degraded
        if st["up"] != up:
            st["since"] = now
        st["up"] = up
        if self.metrics:
            self.metrics.set("gap03_dependency_up", 1 if up else 0, dependency=dep)

    def mark_reconciled(self):
        self.reconciled = True

    def stale_age(self, dep: str) -> float:
        return 0.0 if self.status[dep]["up"] else self.clock() - self.status[dep]["last_good"]

    def is_stale_generation(self, dep: str, used_generation: int | None) -> bool:
        """Stale-snapshot detection by generation provenance, not wall clock alone."""
        g = self.status[dep]["generation"]
        return g is not None and used_generation is not None and used_generation < g

    def decide(self, op: str, *, scope: dict | None = None) -> dict:
        if op not in OPS:
            raise SchedulerError("INVALID_ARGUMENT", "unknown op")
        now = self.clock()
        reasons = []
        for dep, (rules, ttl) in MATRIX.items():
            st = self.status[dep]
            if st["up"]:
                continue
            rule = rules[op]
            age = now - st["last_good"]
            if rule == "closed" or (rule == "stale_ok" and age > ttl):
                if self._overridden(dep, op, scope or {}):
                    reasons.append(f"{dep}:overridden")
                    continue
                return {"allowed": False, "reason": f"{dep}_unavailable", "stale_age_s": round(age, 1)}
            reasons.append(f"{dep}:{'stale' if rule == 'stale_ok' else 'degraded_open'}")
        if op in ("commit", "topology_mutate") and not self.reconciled:
            return {"allowed": False, "reason": "recovery_reconciliation_pending"}
        return {"allowed": True, "degraded": reasons}

    def require(self, op: str, *, scope: dict | None = None):
        d = self.decide(op, scope=scope)
        if not d["allowed"]:
            raise SchedulerError("DEPENDENCY_UNAVAILABLE", d["reason"])
        return d

    def _overridden(self, dep, op, scope):
        now = self.clock()
        for o in self.overrides:
            if o["dependency"] == dep and o["op"] == op and o["expires"] > now and all(scope.get(k) == v for k, v in o["scope"].items()):
                return True
        return False

    def override(self, *, principal: dict, dependency: str, op: str, scope: dict, duration_s: int, risk_ack: str) -> dict:
        if "degraded.override" not in principal.get("perms", set()):
            raise SchedulerError("PERMISSION_DENIED", "break-glass permission required")
        if not risk_ack or len(risk_ack) < 20:
            raise SchedulerError("INVALID_ARGUMENT", "explicit risk acknowledgement text required")
        if not 0 < duration_s <= 3600:
            raise SchedulerError("INVALID_ARGUMENT", "override duration must be 1..3600 s")
        if dependency in ("identity", "audit", "coordination") and op in ("commit", "topology_mutate"):
            raise SchedulerError("PERMISSION_DENIED", "integrity/ownership dependencies cannot be overridden for mutations")
        o = {"dependency": dependency, "op": op, "scope": dict(scope), "expires": self.clock() + duration_s,
             "actor": principal["sub"], "risk_ack": risk_ack}
        self.overrides.append(o)
        if self.audit:
            self.audit.append(actor=principal["sub"], action="degraded.override", target=f"{dependency}:{op}", result="ok",
                              reason=risk_ack, detail={"scope": scope, "duration_s": duration_s})
        return o

    def health(self) -> dict:
        return {d: {"up": s["up"], "stale_age_s": round(self.stale_age(d), 1)} for d, s in self.status.items()} | {
            "_reconciled": self.reconciled, "_recovery_order": list(RECOVERY_ORDER),
            "_active_overrides": len([o for o in self.overrides if o["expires"] > self.clock()])}


FAILOVER_PREREQUISITES = ("lease held by the surviving site's replica (MC-006)",
                          "topology + ledger + journal restored or reachable at the surviving site (MC-042)",
                          "entitlement snapshot generation >= last committed generation",
                          "recover_all() completed: no PREPARED/UNKNOWN transactions left",
                          "residency hard constraints re-evaluated for the surviving candidates")


def failover_candidates(snapshot, candidates, *, failed_sites: set[str], residency_regions: set[str] | None = None) -> dict:
    """Site/region failover filtering: drop candidates in failed failure domains; never violate hard residency;
    report which were removed and why (fairness/topology checks still run afterwards in the normal path)."""
    keep, removed = [], {}
    for c in candidates:
        region, site, _ = snapshot.path(c)
        if f"{region}/{site}" in failed_sites or region in failed_sites:
            removed[c] = "failed_domain"
        elif residency_regions is not None and region not in residency_regions:
            removed[c] = "residency"
        else:
            keep.append(c)
    return {"candidates": keep, "removed": dict(sorted(removed.items())), "prerequisites": list(FAILOVER_PREREQUISITES),
            "eligible": bool(keep)}
