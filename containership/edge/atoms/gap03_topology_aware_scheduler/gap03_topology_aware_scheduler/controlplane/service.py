"""Control-plane scoring facade: wires MC-015..MC-029 around the v4.2.0 core.

score() pipeline (each stage is a trace span):
  admission -> controls/degraded -> snapshot -> hard filter (GAP-02 predicates,
  hard residency) -> locality (+latency refinement) -> gravity -> demand ->
  composition -> fairness verdict (never cached) -> explain components.
"""
from __future__ import annotations

import time

from .. import scheduler as sch
from . import objectives
from .cache import ScoreCache
from .errors import SchedulerError, to_external
from .latency import LatencyEngine
from .objectives import normalise_locality


class ScoringService:
    def __init__(self, *, topology_snapshot, ledger, config, admission=None, controls=None, degraded=None, metrics=None,
                 tracer=None, logger=None, inventory=None, gravity=None, demand=None, latency: LatencyEngine | None = None,
                 cache: ScoreCache | None = None, clock=time.time):
        self.snap_fn, self.ledger, self.config = topology_snapshot, ledger, config
        self.admission, self.controls, self.degraded = admission, controls, degraded
        self.metrics, self.tracer, self.logger = metrics, tracer, logger
        self.inventory, self.gravity, self.demand, self.latency = inventory, gravity, demand, latency
        self.cache = cache or ScoreCache(metrics=metrics)
        self.clock = clock

    def _span(self, name, **kw):
        return self.tracer.start(name, **kw) if self.tracer else None

    def _end(self, span, **kw):
        if span is not None:
            self.tracer.end(span, **kw)

    def score(self, req: dict, *, headers: dict | None = None) -> dict:
        t0 = time.perf_counter()
        root = self._span("admission", headers=headers, txn=req.get("request_id"))
        release = None
        try:
            if self.admission:
                release = self.admission.admit(kind="score", tenant=req["tenant"], priority=req.get("priority", "production"),
                                               candidates=len(req["candidates"]))
            if self.controls:
                self.controls.check("score", scope={"tenant": req["tenant"]})
            if self.degraded:
                self.degraded.require("score")
            cfg = self.config.current
            ssp = self._span("snapshot")
            snap = self.snap_fn()
            self._end(ssp)
            if self.latency:
                self.latency.invalidate(snap.generation)
            now = self.clock()
            if len(req["candidates"]) > cfg.get("limits.max_candidates"):
                raise SchedulerError("PAYLOAD_TOO_LARGE", "candidate count exceeds configured limit")
            snap.path(req["anchor"])
            key = ScoreCache.key(topology_generation=snap.generation, config_generation=cfg.generation, schema_version="1.1",
                                 scoring_version=objectives.FORMULA_VERSION, anchor=req["anchor"],
                                 candidates=req["candidates"], spread_from=req.get("spread_from", []))
            self.cache.set_namespace(snap.generation, cfg.generation)
            deterministic = not (self.latency or self.gravity or self.demand or self.inventory)
            signals: dict = {}

            def compute():
                lsp = self._span("locality_score")
                try:
                    return self._compose(req, snap, cfg, now, signals)
                finally:
                    self._end(lsp)
            csp = self._span("cache")
            composed = self.cache.get_or_compute(key, compute) if deterministic else tuple(compute())
            self._end(csp)
            fsp = self._span("fairness")
            verdict, rev, ent_gen = self.ledger.verdict(req["tenant"], req.get("slots", 1))  # never cached
            self._end(fsp)
            if self.metrics:
                self.metrics.observe("gap03_candidate_set_size", len(req["candidates"]))
                self.metrics.observe("gap03_feasible_candidates", sum(1 for c in composed if c.feasible))
                if not verdict.allowed:
                    self.metrics.inc("gap03_fairness_denials_total", reason=verdict.reason)
                self.metrics.inc("gap03_requests_total", op="score", code="OK")
                self.metrics.observe("gap03_score_latency_ms", (time.perf_counter() - t0) * 1000, result="ok")
            if self.logger:
                self.logger.log("score.ok", request_id=req.get("request_id"), trace_id=root["trace_id"] if root else "",
                                candidate_count=len(req["candidates"]))
            self._end(root)
            sources = {"trace_id": root["trace_id"] if root else None}
            if self.inventory is not None:
                sources["gap02"] = self.inventory.snapshot_meta()
            if self.gravity is not None and req.get("dataset"):
                rec = self.gravity.anchors.get(req["dataset"])
                sources["gap14"] = {"revision": rec["revision"] if rec else None,
                                    "status": {n: s.get("gravity_status") for n, s in sorted(signals.items())}}
            if self.demand is not None:
                adv = self.demand.advisory(req["tenant"], now)
                sources["pln05"] = {"request_id": adv["request_id"], "revision": adv.get("revision"), "status": adv["status"]}
            if self.latency is not None:
                sources["latency"] = {n: s.get("latency") for n, s in sorted(signals.items())}
            return {"ok": True, "topology_generation": snap.generation, "config_generation": cfg.generation,
                    "ledger_revision": rev, "entitlement_generation": ent_gen, "formula": objectives.FORMULA_VERSION,
                    "sources": sources,
                    "fairness": {"allowed": verdict.allowed, "reason": verdict.reason, "state_token": verdict.state_token},
                    "ranked": [{"node": c.node, "total": c.total, "components": dict(c.components), "feasible": c.feasible,
                                "hard_failures": list(c.hard_failures)} for c in composed]}
        except Exception as exc:  # noqa: BLE001 - single boundary
            ext = to_external(exc, correlation_id=str(req.get("request_id", "")))
            if self.metrics:
                self.metrics.inc("gap03_requests_total", op="score", code=ext["code"])
            self._end(root, error_code=ext["code"])
            return {"ok": False, "error": ext}
        finally:
            if release:
                release()

    def _compose(self, req, snap, cfg, now, signals=None):
        signals = signals if signals is not None else {}
        anchor = req["anchor"]
        spread = {snap.domain(n) for n in req.get("spread_from", [])}
        reqs = req.get("requirements", {})

        def hard(n):
            fails = []
            if n not in snap.nodes:
                return ("not_in_topology",)
            if self.inventory is not None:  # nodes that cannot be resolved to fresh inventory are infeasible
                ok, why = self.inventory.feasible(n, reqs, now)
                if not ok:
                    fails.append(why)
            if self.gravity is not None and req.get("dataset") and not self.gravity.hard_residency_ok(req["dataset"], n, snap):
                fails.append("residency")
            return tuple(fails)

        def loc(n):
            if n not in snap.nodes:
                return 1000
            if self.latency is not None and cfg.get("features.latency_refinement"):
                rc = self.latency.refined_cost(snap, anchor, n)
                signals.setdefault(n, {})["latency"] = {k: rc.get(k) for k in ("status", "age_s", "confidence", "cost_milli")}
                return normalise_locality(rc["cost_milli"])
            return normalise_locality(snap.cost(anchor, n) * 1000)

        def grav(n):
            if self.gravity is None or not req.get("dataset") or n not in snap.nodes:
                return None
            c = self.gravity.contribution(req["dataset"], n, snap, now)
            signals.setdefault(n, {})["gravity_status"] = c["status"]
            return c["value"] if c["status"] == "fresh" else None

        def dem(n):
            if self.demand is None or n not in snap.nodes:
                return None
            adv = self.demand.advisory(req["tenant"], now)
            return 0 if adv["slots"] == 0 else (200 if snap.domain(n) in spread else 0)

        def spr(n):
            return 1000 if n in snap.nodes and snap.domain(n) in spread else 0

        w = {"locality": cfg.get("scoring.weight_locality"), "gravity": cfg.get("scoring.weight_gravity"),
             "demand": cfg.get("scoring.weight_demand"), "spread": 0}
        fsp = self._span("filter")
        try:
            return objectives.compose(req["candidates"], weights=w, locality=loc, gravity=grav, demand=dem, spread=spr, hard=hard)
        finally:
            self._end(fsp)
