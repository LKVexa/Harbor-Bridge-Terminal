"""MC-041 - Canary / staged deployment controller (GAP03-ROLLOUT/1).

Stages 1% -> 10% -> 50% -> 100% with bake times.  Promotion requires the
exit gate to be GO for the exact artifact digest, and every health/metric
criterion within budget at the end of the bake.  Any breach -> automatic
rollback to the previous digest (recorded).  The controller is pure logic
over injected ``observe()``/``shift()`` callables so it can be rehearsed.
"""
from __future__ import annotations

from .errors import SchedulerError

ENVIRONMENTS = ["dev", "integration", "shadow", "canary", "partial", "full"]
STAGES = [(1, 600), (10, 1800), (50, 3600), (100, 0)]  # production percentages after dev/integration/shadow pass
PRE_PROMOTION_GATES = ("unit_and_contract_tests", "security_scan", "migration_readiness", "benchmark_thresholds", "error_budget",
                       "no_open_p0_p1")
MAX_CANARY_FRACTION = 0.05
CRITERIA = {"error_ratio_max": 0.001, "p99_ms_max": 20.0, "fencing_rejections_max": 0, "readiness_min": 0.99,
            "audit_write_failures_max": 0}


COMPARE = {"fairness_denial_ratio": 0.02, "utilization": 0.10, "stale_conflict_ratio": 0.01, "drift_events": 2}


def evaluate(obs: dict, baseline: dict | None = None) -> list[str]:
    """Absolute criteria plus canary-vs-control deltas for fairness denials, utilisation, stale conflicts and drift."""
    bad = []
    if baseline:
        for sig, tol in COMPARE.items():
            if sig in obs and sig in baseline and obs[sig] - baseline[sig] > tol:
                bad.append(f"{sig}_vs_control")
    if obs["error_ratio"] > CRITERIA["error_ratio_max"] or (baseline and obs["error_ratio"] > 2 * baseline["error_ratio"] + 1e-4):
        bad.append("error_ratio")
    if obs["p99_ms"] > CRITERIA["p99_ms_max"]:
        bad.append("p99_ms")
    if obs["fencing_rejections"] > CRITERIA["fencing_rejections_max"]:
        bad.append("fencing_rejections")
    if obs["readiness"] < CRITERIA["readiness_min"]:
        bad.append("readiness")
    if obs["audit_write_failures"] > CRITERIA["audit_write_failures_max"]:
        bad.append("audit_write_failures")
    return bad


def run(*, candidate: str, previous: str, gate_result: dict, observe, shift, record, stages=STAGES, drain=None,
        meta: dict | None = None, clock=None, audit=None) -> dict:
    import time as _t
    clock = clock or _t.time
    if gate_result.get("decision") != "GO" or gate_result.get("artifact_digest") != candidate:
        raise SchedulerError("PERMISSION_DENIED", "exit gate is not GO for this exact artifact digest")
    meta = dict(meta or {})
    if audit is not None:  # release promotions are privileged changes (PG-006)
        _rec = record

        def record(ev, _rec=_rec):
            _rec(ev)
            audit.append(actor=str(meta.get("approver", "release-controller")), action=f"release.{ev['event']}",
                         target=candidate, result="ok", detail={k: v for k, v in ev.items() if k != "metrics"})
    history = []
    baseline = observe(previous, 0)
    started = clock()
    for pct, bake in stages:
        if drain is not None:
            drain(pct)  # fence/drain instances leaving service so in-flight txns are not orphaned
        shift(candidate, pct)
        obs = observe(candidate, pct)
        breaches = evaluate(obs, baseline)
        history.append({"pct": pct, "bake_s": bake, "obs": obs, "breaches": breaches})
        if breaches:
            shift(previous, 100)
            record({"event": "rollback", "from": candidate, "to": previous, "at_pct": pct, "breaches": breaches,
                    "start": started, "end": clock(), "metrics": obs, **meta})
            return {"result": "ROLLED_BACK", "history": history}
    record({"event": "promoted", "digest": candidate, "start": started, "end": clock(), "metrics": history[-1]["obs"], **meta})
    return {"result": "PROMOTED", "history": history}


def choose_cohort(tenants: list[dict], *, fraction: float = 0.01, max_fraction: float = MAX_CANARY_FRACTION,
                  exclusions: dict | None = None) -> dict:
    """Pick a canary cohort covering every (region, tenant_class) present, bounded by ``max_fraction``.
    tenants: [{"id", "region", "class"}]; exclusions: {id: rationale} (documented)."""
    exclusions = exclusions or {}
    pool = sorted((t for t in tenants if t["id"] not in exclusions), key=lambda t: t["id"])
    cap = max(1, int(len(tenants) * max_fraction))
    picked, seen = [], set()
    for t in pool:  # one per stratum first -> diversity
        k = (t["region"], t["class"])
        if k not in seen and len(picked) < cap:
            picked.append(t["id"])
            seen.add(k)
    want = max(len(picked), min(cap, int(len(tenants) * fraction)))
    for t in pool:
        if len(picked) >= want:
            break
        if t["id"] not in picked:
            picked.append(t["id"])
    strata = {(t["region"], t["class"]) for t in tenants if t["id"] not in exclusions}
    return {"cohort": picked, "strata_covered": len(seen), "strata_total": len(strata), "cap": cap,
            "exclusions": dict(sorted(exclusions.items()))}


def pre_promotion(results: dict) -> list[str]:
    return [g for g in PRE_PROMOTION_GATES if results.get(g) is not True]


class Controller:
    """Authorised pause/resume/abort around ``run``; every decision is recorded."""

    def __init__(self, *, record, authorized_roles=("release-manager",)):
        self.record, self.roles, self.state = record, set(authorized_roles), "idle"

    def _auth(self, principal):
        if not set(principal.get("roles", [])) & self.roles:
            raise SchedulerError("PERMISSION_DENIED", "rollout control requires release-manager")

    def pause(self, principal, reason):
        self._auth(principal)
        self.state = "paused"
        self.record({"event": "pause", "actor": principal["sub"], "reason": reason})

    def resume(self, principal):
        self._auth(principal)
        self.state = "running"
        self.record({"event": "resume", "actor": principal["sub"]})

    def abort(self, principal, reason, *, shift, previous):
        self._auth(principal)
        shift(previous, 100)
        self.state = "aborted"
        self.record({"event": "abort", "actor": principal["sub"], "reason": reason, "to": previous})
