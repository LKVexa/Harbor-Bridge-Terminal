"""GAP-14 decision service: the estate-integrated decision path.

Order of operations for ``decide`` (every step fail-closed):

 1. readiness (active signed config)            P0-11, P1-17
 2. admission: payload size, concurrency        P1-21
 3. authenticate + authorize (scope, tenant)    P0-07
 4. strict request validation, tenant binding   P0-08, C03
 5. anti-replay on request_id                   C01
 6. deadline + cancellation                     P1-13
 7. verified inputs: GAP-03 topology, SCH-01 placement, GAP-05 convergence,
    GAP-13 verdicts for each candidate site     P0-02..05, P1-14..16
 8. plan: hard constraints then objective       engine semantics + P2-28..36
 9. shadow / canary evaluation                  P2-38
10. provenance envelope, signed                 P0-09
11. audit append (no audit -> no decision)      P0-10
12. metrics, structured log, trace              P1-18, P1-19
"""
from __future__ import annotations

import collections
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from . import __version__
from .adapters import (AdapterContext, DataPlaneHandoff, PlacementAdapter, PolicyAdapter, ReplicationAdapter,
                       TopologyAdapter, WorkloadRequirements)
from .audit import AuditSink
from .config import ConfigManager
from .engine import CostModelError, GravityDecisionError, NoLegalOption
from .errors import G14Error, REGISTRY
from .identity import Authenticator, Principal, WorkloadIdentity
from .modeling import CalibrationTracker, CanaryRouter
from .observability import Registry, StructuredLogger, TraceContext, standard_metrics
from .planner import PlanInputs, Route, Stage, WorkloadProfile, optimize_dag, plan
from .resilience import AdmissionController, CircuitBreaker, Deadline, FreshnessPolicy, RetryPolicy
from .trust import KeyRing, ReplayGuard, canonical_json, digest, exact_fields, ident, number

REQUEST_SCHEMA = "PK_GRAVITY_DECISION_REQUEST/1"
DECISION_SCHEMA = "PK_GRAVITY_DECISION/2"
SIMULATION_SCHEMA = "PK_GRAVITY_SIMULATION/1"
SERVICE_ISSUER = "gap14-data-gravity"


@dataclass(frozen=True)
class DecisionRequest:
    request_id: str
    identity: WorkloadIdentity
    dataset: str
    dataset_tenant: str
    data_site: str
    size_gb: float
    classification: str
    compute_site: str
    requirements: WorkloadRequirements
    profile: WorkloadProfile | None

    @classmethod
    def parse(cls, raw: Any) -> "DecisionRequest":
        exact_fields(raw, "request", ["schema", "request_id", "workload", "dataset", "compute_site"], ["requirements", "profile"])
        if raw["schema"] != REQUEST_SCHEMA:
            raise G14Error("G14_INVALID_REQUEST", "unsupported request schema", details={"field": "schema"})
        d = exact_fields(raw["dataset"], "dataset", ["name", "tenant_id", "site", "size_gb", "classification"])
        return cls(ident(raw["request_id"], "request_id"), WorkloadIdentity.parse(raw["workload"]),
                   ident(d["name"], "dataset.name"), ident(d["tenant_id"], "dataset.tenant_id"),
                   ident(d["site"], "dataset.site"), number(d["size_gb"], "dataset.size_gb"),
                   ident(d["classification"], "dataset.classification"), ident(raw["compute_site"], "compute_site"),
                   WorkloadRequirements.parse(raw.get("requirements")), WorkloadProfile.parse(raw.get("profile")))

    def public(self) -> dict[str, Any]:
        return {"request_id": self.request_id, "compute_site": self.compute_site,
                "dataset": {"name": self.dataset, "site": self.data_site, "size_gb": self.size_gb,
                            "classification": self.classification}}


class DecisionService:
    def __init__(self, *, keyring: KeyRing, signing_kid: str, config: ConfigManager, audit: AuditSink,
                 authenticator: Authenticator, transports: Mapping[str, Callable], clock,
                 logger: StructuredLogger | None = None, registry: Registry | None = None,
                 sleep: Callable[[float], None] | None = None):
        cfg = config.active
        self.keyring, self.signing_kid, self.config, self.audit = keyring, signing_kid, config, audit
        self.auth, self.clock = authenticator, clock
        self.registry = registry or Registry()
        self.m = standard_metrics(self.registry)
        self.log = logger or StructuredLogger(clock=clock.now)
        self.replay = ReplayGuard()
        k = cfg.knobs
        self.admission = AdmissionController(int(k["max_concurrent"]), int(k["max_payload_bytes"]), int(k["max_batch"]),
                                             max_per_tenant=int(k["max_per_tenant"]) or None)
        self.draining = False
        self._was_ready: bool | None = None
        self.ctx = AdapterContext(keyring=keyring, clock=clock,
                                  freshness=FreshnessPolicy(dict(cfg.ttls), k["clock_skew_s"]),
                                  retry=RetryPolicy(max_attempts=int(k["retry_max_attempts"])),
                                  timeout_cap_s=k["dependency_timeout_s"], sleep=sleep,
                                  on_event=lambda dep, outcome, s: self.m["dep_latency"].observe(s, dependency=dep, outcome=outcome if outcome in ("ok",) else "error"))
        br = lambda name: CircuitBreaker(name, int(k["breaker_failure_threshold"]), k["breaker_reset_s"], clock)
        self.policy = PolicyAdapter(transports["GAP-13"], self.ctx, breaker=br("GAP-13"))
        self.topology = TopologyAdapter(transports["GAP-03"], self.ctx, breaker=br("GAP-03"))
        self.replication = ReplicationAdapter(transports["GAP-05"], self.ctx, breaker=br("GAP-05"))
        self.placement = PlacementAdapter(transports["SCH-01"], self.ctx, breaker=br("SCH-01"))
        self.dataplane = DataPlaneHandoff(transports["PLN-06"], self.ctx, signing_kid=signing_kid)
        self.explain_cache_size = 2048  # bounded explain cache; audit log is the durable record
        self._records: collections.OrderedDict[str, dict[str, Any]] = collections.OrderedDict()
        self._rec_lock = threading.Lock()
        self.calibration = CalibrationTracker(f"cfg-{cfg.revision}",
                                              on_alarm=lambda dim: self.m["drift"].inc(dimension=dim if dim in ("money", "time", "carbon") else "other"))
        self._last_audit_ok = True
        self._applied_digest = cfg.digest
        self.m["build_info"].inc(version=__version__, config_revision=str(cfg.revision), mode=cfg.mode)
        if config.on_event is None:  # config activations/rollbacks/rejections go to the same audit chain
            def _cfg_event(event: str, payload: Mapping[str, Any]) -> None:
                self.m["config"].inc(result=event.split(".")[-1])
                self._audit(event, payload)
            config.on_event = _cfg_event

    def _sync_config(self, cfg) -> None:
        """Apply reloadable knobs from a newly activated revision (restart-bound ones are not touched)."""
        if cfg.digest == self._applied_digest:
            return
        k = cfg.knobs
        self.ctx.freshness = FreshnessPolicy(dict(cfg.ttls), k["clock_skew_s"])
        self.ctx.retry = RetryPolicy(max_attempts=int(k["retry_max_attempts"]))
        self.ctx.timeout_cap_s = k["dependency_timeout_s"]
        self.admission.max_payload_bytes, self.admission.max_batch = int(k["max_payload_bytes"]), int(k["max_batch"])
        self._applied_digest = cfg.digest
        self.m["build_info"].inc(version=__version__, config_revision=str(cfg.revision), mode=cfg.mode)
        self.log.log("info", "config.applied", revision=cfg.revision, digest=cfg.digest)

    # ------------------------------------------------------------ helpers
    def _audit(self, event: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            ref = self.audit.append(event, payload, self.clock.now())
        except G14Error:
            self._last_audit_ok = False
            self.m["audit"].inc(result="failed")
            raise
        self._last_audit_ok = True
        self.m["audit"].inc(result="ok")
        return ref

    def _authorize(self, token: Any, scope: str, tenant: str | None) -> Principal:
        principal = self.auth.authenticate(token, self.clock.now())
        principal.require(scope, tenant)
        return principal

    def _refuse(self, exc: GravityDecisionError, trace: TraceContext, mode: str, request_id: str | None) -> None:
        code = exc.code
        category = REGISTRY[code].category if code in REGISTRY else "internal"
        self.m["refusals"].inc(code=code, category=category)
        if code in ("G14_OVERLOADED", "G14_PAYLOAD_TOO_LARGE"):
            self.m["admission"].inc(code=code)
        self.m["recommendations"].inc(direction="none", outcome="refused", mode=mode)
        if code == "PK_GRAVITY_NO_LEGAL_OPTION":
            self.m["no_legal"].inc()
        self.log.log("warning", "decision.refused", trace=trace, code=code, category=category, request_id=request_id)
        if code not in ("G14_AUDIT_UNAVAILABLE",):
            try:
                self._audit("decision.refused", {"code": code, "request_id": request_id, "trace_id": trace.trace_id,
                                                 "details_digest": digest(exc.details) if exc.details else None})
            except G14Error:
                pass  # refusal already fail-closed; audit loss is surfaced by metrics/readiness

    def _remember(self, decision_id: str, record: dict[str, Any]) -> None:
        with self._rec_lock:
            self._records[decision_id] = record
            while len(self._records) > self.explain_cache_size:
                self._records.popitem(last=False)

    # ----------------------------------------------------------- decide
    def decide(self, raw_request: Mapping[str, Any], token: Any, *, traceparent: str | None = None,
               cancel=None) -> dict[str, Any]:
        trace = TraceContext.from_traceparent(traceparent)
        t0 = self.clock.monotonic()
        mode = "production"
        request_id = raw_request.get("request_id") if isinstance(raw_request, Mapping) else None
        try:
            if self.draining:
                raise G14Error("G14_NOT_READY", "instance draining")
            cfg = self.config.active
            self._sync_config(cfg)
            mode = cfg.mode
            try:
                size = len(canonical_json(raw_request))
            except (TypeError, ValueError):
                raise G14Error("G14_INVALID_REQUEST", "request is not JSON-serialisable")
            self.admission.check_payload(size)
            with self.admission:
                # authenticate before deserialising the request body (P0-07 A06); authorize after tenant is known
                principal = self.auth.authenticate(token, self.clock.now())
                req = DecisionRequest.parse(raw_request)
                principal.require("gravity:recommend", req.identity.tenant_id)
                if req.dataset_tenant != req.identity.tenant_id:
                    raise G14Error("G14_CROSS_TENANT", "dataset belongs to another tenant")
                self.replay.check_and_add(f"{req.identity.tenant_id}/{req.request_id}", self.clock.now())
                deadline = Deadline(cfg.knobs["decision_deadline_s"], self.clock, cancel)
                with self.admission.tenant_slot(req.identity.tenant_id):
                    result = self._decide(req, principal, cfg, deadline, trace, mode)
            elapsed = self.clock.monotonic() - t0
            self.m["latency"].observe(elapsed, mode=mode)
            return result
        except G14Error as exc:
            self._refuse(exc, trace, mode, request_id if isinstance(request_id, str) else None)
            raise
        except (NoLegalOption, CostModelError) as exc:
            self._refuse(exc, trace, mode, request_id if isinstance(request_id, str) else None)
            raise
        except GravityDecisionError:
            raise
        except Exception as exc:  # never leak an unclassified fault as a decision
            err = G14Error("G14_INTERNAL", "internal fault", details={"type": type(exc).__name__})
            self._refuse(err, trace, mode, request_id if isinstance(request_id, str) else None)
            raise err from exc

    def _gather(self, req: DecisionRequest, cfg, deadline: Deadline, mode: str, sites: list[str]):
        topo = self.topology.snapshot(sites, deadline, mode)
        deadline.check("topology")
        place = self.placement.snapshot(req.identity.tenant_id, sites, deadline, mode)
        deadline.check("placement")
        conv = self.replication.proof(req.identity.tenant_id, req.dataset, deadline, mode)
        deadline.check("convergence")
        verdicts = {}
        for site, op in ((req.data_site, "process"), (req.compute_site, "hold")):
            if site in verdicts:
                continue
            preq = PolicyAdapter.build_request(
                tenant_id=req.identity.tenant_id, workload_id=req.identity.workload_id, dataset=req.dataset,
                classification=req.classification, source_site=req.data_site, destination_site=site, operation=op,
                jurisdiction_tags=list(cfg.site_jurisdictions.get(site, ())), evaluated_at=self.clock.now())
            verdicts[site] = self.policy.evaluate(preq, deadline, mode)
            deadline.check("policy")
        return topo, place, conv, verdicts

    def _plan(self, req, cfg, topo, place, conv, verdicts, relocation_cost):
        routes = {k: Route(v["locality_multiplier"], v["egress_per_gb"], v["available"], v["bandwidth_gbps"], v["congestion"])
                  for k, v in topo.routes.items()}
        legal = lambda s: (True, "ok") if verdicts[s].allow else (False, f"{s} may not hold {req.classification} (policy {verdicts[s].policy_version}: {','.join(verdicts[s].rule_ids) or 'deny'})")
        return plan(PlanInputs(req.dataset, req.data_site, req.compute_site, req.size_gb, req.classification,
                               conv.converged, legal, routes, lambda s: place.compatible(s, req.requirements),
                               place.data_quota_ok, relocation_cost, dict(cfg.site_economics), req.profile))

    def _decide(self, req: DecisionRequest, principal: Principal, cfg, deadline: Deadline, trace: TraceContext,
                mode: str) -> dict[str, Any]:
        sites = sorted({req.data_site, req.compute_site})
        topo, place, conv, verdicts = self._gather(req, cfg, deadline, mode, sites)
        if req.data_site == req.compute_site:
            if not verdicts[req.data_site].allow:
                raise NoLegalOption(f"{req.dataset}: current location violates residency",
                                    details={"reason_code": "CURRENT_RESIDENCY_VIOLATION"})
            ok, why = place.compatible(req.data_site, req.requirements)
            if not ok:
                raise G14Error("G14_COMPUTE_INCOMPATIBLE", why)
            planned = {"best": {"direction": "none", "to": req.data_site, "cost": 0.0,
                                "cost_breakdown": {"kind": "none", "from": req.data_site, "to": req.data_site, "total": 0.0}},
                       "options": [], "eliminated": []}
            reason_code = "ALREADY_COLOCATED"
        else:
            planned = self._plan(req, cfg, topo, place, conv, verdicts, cfg.knobs["compute_relocation_cost"])
            reason_code = "CHEAPEST_LEGAL_OPTION"
        model_revision = f"cfg-{cfg.revision}"
        shadow_report = None
        if cfg.shadow_model and reason_code != "ALREADY_COLOCATED":
            try:
                sp = self._plan(req, cfg, topo, place, conv, verdicts, cfg.shadow_model["compute_relocation_cost"])
                diverged = sp["best"]["direction"] != planned["best"]["direction"]
                shadow_report = {"model_revision": cfg.shadow_model["revision"], "direction": sp["best"]["direction"],
                                 "cost": sp["best"]["cost"], "diverged": diverged}
                if diverged:
                    self.m["shadow_divergence"].inc(model="shadow")
                if cfg.canary_percent and CanaryRouter(cfg.canary_percent, cfg.digest.encode()).in_canary(
                        f"{req.identity.tenant_id}/{req.identity.workload_id}/{req.dataset}"):
                    planned, model_revision = sp, cfg.shadow_model["revision"]
                    shadow_report["canary"] = True
            except GravityDecisionError as exc:
                shadow_report = {"model_revision": cfg.shadow_model["revision"], "error": exc.code}
        best = planned["best"]
        obligations: dict[str, Any] = {}
        # obligations attach from every site the chosen option touches (data moves touch both ends)
        touched = {req.data_site} if best["direction"] in ("move-compute", "none") else {req.data_site, req.compute_site}
        for site in sorted(touched):
            if verdicts[site].allow:
                obligations.update(verdicts[site].obligations)
        now = self.clock.now()
        stale = sorted(kind for kind, age in (("topology_snapshot", topo.age_s), ("placement_snapshot", place.age_s),
                                              ("convergence_proof", conv.age_s))
                       if age > cfg.ttls[kind]) + sorted(f"policy_verdict:{s_}" for s_, v in verdicts.items()
                                                          if v.age_s > cfg.ttls["policy_verdict"])
        for src in stale:
            self.m["degraded"].inc(source=src.split(":")[0])
        inputs = {"topology": topo.ref(), "placement": place.ref(), "convergence": conv.ref(),
                  "policy": {s: v.ref() for s, v in sorted(verdicts.items())}, "config": cfg.ref(),
                  "request": req.public(), "identity": req.identity.as_dict()}
        provenance = {
            "decision_id": f"dec-{uuid.uuid4().hex}", "issued_at": now, "mode": mode,
            "engine": {"package": "gap14_data_gravity_manager", "version": __version__, "model_revision": model_revision},
            "identity": req.identity.as_dict(), "actor": {"subject": principal.subject, "token_id": principal.token_id},
            "request": req.public(), "inputs": inputs, "input_digest": digest(inputs), "obligations": obligations,
            "quality": {"status": "degraded" if stale else "fresh", "stale_sources": stale},
            "trace": {"trace_id": trace.trace_id, "span_id": trace.span_id}, "schema_versions": {
                "decision": DECISION_SCHEMA, "request": REQUEST_SCHEMA}}
        recommendation = {"direction": best["direction"], "to": best["to"], "cost": best["cost"],
                          "cost_breakdown": best["cost_breakdown"], "reason_code": reason_code,
                          "options": planned["options"], "eliminated": [f"{e['direction']}: {e['reason']}" for e in planned["eliminated"]],
                          "elimination_details": planned["eliminated"]}
        envelope = {"schema": DECISION_SCHEMA, "executable": mode == "production", "recommendation": recommendation,
                    "provenance": provenance}
        envelope["sig"] = self.keyring.sign(envelope, self.signing_kid)
        audit_ref = self._audit("decision.issued", {"decision_id": provenance["decision_id"], "input_digest": provenance["input_digest"],
                                                    "direction": best["direction"], "to": best["to"], "cost": best["cost"],
                                                    "reason_code": reason_code, "envelope_digest": digest(envelope),
                                                    "tenant_id": req.identity.tenant_id, "shadow": shadow_report})
        envelope_out = {**envelope, "audit": audit_ref}
        self._remember(provenance["decision_id"], {"envelope": envelope, "audit": audit_ref, "shadow": shadow_report,
                                                   "tenant_id": req.identity.tenant_id})
        self.m["recommendations"].inc(direction=best["direction"], outcome="recommended", mode=mode)
        self.m["cost"].observe(best["cost"], direction=best["direction"])
        for e in planned["eliminated"]:
            self.m["eliminated"].inc(direction=e["direction"], code=e["code"])
        self.log.log("info", "decision.issued", trace=trace, decision_id=provenance["decision_id"],
                     direction=best["direction"], reason_code=reason_code, tenant_id=req.identity.tenant_id,
                     dataset=req.dataset, audit_seq=audit_ref["seq"])
        return envelope_out

    # ---------------------------------------------------------- handoff
    def handoff(self, envelope: Mapping[str, Any], token: Any) -> dict[str, Any]:
        prov = envelope.get("provenance", {}) if isinstance(envelope, Mapping) else {}
        tenant = prov.get("identity", {}).get("tenant_id")
        self._authorize(token, "gravity:handoff", tenant)
        deadline = Deadline(max(self.config.active.knobs["decision_deadline_s"], 0.25), self.clock)
        env = {k: v for k, v in envelope.items() if k != "audit"}
        result = self.dataplane.submit(env, deadline)
        self._audit("handoff.accepted", {"decision_id": prov.get("decision_id"), **result})
        return result

    # ---------------------------------------------------------- explain
    def explain(self, decision_id: str, token: Any) -> dict[str, Any]:
        with self._rec_lock:
            rec = self._records.get(decision_id)
        try:
            principal = self.auth.authenticate(token, self.clock.now())
            if rec is None:
                principal.require("gravity:explain")
                raise G14Error("G14_INVALID_REQUEST", "unknown or expired decision id")
            principal.require("gravity:explain", rec["tenant_id"])
        except G14Error as exc:
            self.m["explain"].inc(outcome="denied" if exc.reason.category == "security" else "not-found")
            raise
        self.m["explain"].inc(outcome="ok")
        self._audit("explain.accessed", {"decision_id": decision_id, "actor": principal.subject})
        env = rec["envelope"]
        rec_ = env["recommendation"]
        return {"schema": "PK_GRAVITY_EXPLAIN/1", "decision_id": decision_id,
                "summary": f"{rec_['direction']} to {rec_['to']} ({rec_['reason_code']}), cost {rec_['cost']:.6g}",
                "chosen": {k: rec_[k] for k in ("direction", "to", "cost", "cost_breakdown")},
                "alternatives": rec_["options"], "eliminated": rec_["elimination_details"],
                "inputs": env["provenance"]["inputs"], "input_digest": env["provenance"]["input_digest"],
                "obligations": env["provenance"]["obligations"], "model_revision": env["provenance"]["engine"]["model_revision"],
                "shadow": rec["shadow"], "audit": rec["audit"]}

    # --------------------------------------------------------- simulate
    def simulate(self, scenario: Mapping[str, Any], token: Any) -> dict[str, Any]:
        """What-if (P2-39): caller-supplied hypothetical inputs, no dependency calls,
        never executable, audited as a simulation (not a decision)."""
        self.admission.check_payload(len(canonical_json(scenario)))
        exact_fields(scenario, "scenario", ["request", "residency", "routes", "compute_sites"],
                     ["converged", "compute_relocation_cost"])
        if len(scenario["routes"]) > 10_000 or len(scenario["residency"]) > 10_000:
            raise G14Error("G14_PAYLOAD_TOO_LARGE", "scenario too large")
        req = DecisionRequest.parse(scenario["request"])
        principal = self._authorize(token, "gravity:simulate", req.identity.tenant_id)
        if req.dataset_tenant != req.identity.tenant_id:
            raise G14Error("G14_CROSS_TENANT", "dataset belongs to another tenant")
        residency = {ident(s, "residency.site"): {ident(c, "residency.class") for c in cs} for s, cs in scenario["residency"].items()}
        routes = {}
        for r in scenario["routes"]:
            exact_fields(r, "scenario.route", ["from", "to", "locality_multiplier", "egress_per_gb"], ["available", "bandwidth_gbps", "congestion"])
            routes[(ident(r["from"], "route.from"), ident(r["to"], "route.to"))] = Route(
                number(r["locality_multiplier"], "route.locality_multiplier"), number(r["egress_per_gb"], "route.egress_per_gb"),
                bool(r.get("available", True)), number(r.get("bandwidth_gbps", 1.0), "route.bandwidth_gbps", minimum=1e-6),
                number(r.get("congestion", 0.0), "route.congestion", maximum=0.99))
        csites = {ident(s, "compute_site") for s in scenario["compute_sites"]}
        converged = scenario.get("converged", True)
        if not isinstance(converged, bool):
            raise G14Error("G14_INVALID_REQUEST", "converged must be bool")
        cost = number(scenario.get("compute_relocation_cost", self.config.active.knobs["compute_relocation_cost"]), "compute_relocation_cost")
        planned = plan(PlanInputs(req.dataset, req.data_site, req.compute_site, req.size_gb, req.classification, converged,
                                  lambda s: (req.classification in residency.get(s, ()), f"{s} may not hold {req.classification}"),
                                  routes, lambda s: (s in csites, f"no compute capacity at {s}"), lambda s, gb: (True, "ok"),
                                  cost, dict(self.config.active.site_economics), req.profile))
        sim_id = f"sim-{uuid.uuid4().hex}"
        out = {"schema": SIMULATION_SCHEMA, "executable": False, "simulation_id": sim_id,
               "notice": "SIMULATION ONLY - hypothetical inputs, not authorised for execution",
               "result": {"direction": planned["best"]["direction"], "to": planned["best"]["to"], "cost": planned["best"]["cost"],
                          "options": planned["options"], "eliminated": planned["eliminated"]},
               "scenario_digest": digest(scenario), "actor": principal.subject}
        self.m["simulations"].inc(outcome="ok")
        self._audit("simulation.run", {"simulation_id": sim_id, "scenario_digest": out["scenario_digest"], "actor": principal.subject})
        return out

    # -------------------------------------------------------------- DAG
    def plan_dag(self, raw: Mapping[str, Any], token: Any) -> dict[str, Any]:
        """Advisory multi-dataset/DAG placement (P2-31) over *verified* inputs.

        Non-executable: each resulting data movement still needs its own
        production decision (and therefore its own verdicts and audit record).
        """
        exact_fields(raw, "dag", ["workload", "datasets", "stages", "candidate_sites"])
        ident_ = WorkloadIdentity.parse(raw["workload"])
        principal = self._authorize(token, "gravity:recommend", ident_.tenant_id)
        cfg = self.config.active
        if not isinstance(raw["datasets"], list) or not isinstance(raw["stages"], list) or not isinstance(raw["candidate_sites"], list):
            raise G14Error("G14_INVALID_REQUEST", "dag lists malformed")
        self.admission.check_payload(len(canonical_json(raw)), len(raw["datasets"]) + len(raw["stages"]))
        datasets = {}
        for d in raw["datasets"]:
            exact_fields(d, "dag.dataset", ["name", "tenant_id", "site", "size_gb", "classification"])
            if d["tenant_id"] != ident_.tenant_id:
                raise G14Error("G14_CROSS_TENANT", "dag dataset belongs to another tenant")
            datasets[ident(d["name"], "dataset.name")] = {"site": ident(d["site"], "dataset.site"), "size_gb": number(d["size_gb"], "size_gb"),
                                                          "classification": ident(d["classification"], "classification")}
        stages = []
        for s in raw["stages"]:
            exact_fields(s, "dag.stage", ["name", "inputs"], ["output_gb"])
            stages.append(Stage(ident(s["name"], "stage.name"), tuple(ident(i, "stage.input") for i in s["inputs"]),
                                number(s.get("output_gb", 0.0), "stage.output_gb")))
        cands = sorted({ident(c, "candidate_site") for c in raw["candidate_sites"]})
        sites = sorted(set(cands) | {d["site"] for d in datasets.values()})
        deadline = Deadline(max(cfg.knobs["decision_deadline_s"] * 10, 0.5), self.clock)
        topo = self.topology.snapshot(sites, deadline)
        place = self.placement.snapshot(ident_.tenant_id, sites, deadline)
        conv = {n: self.replication.proof(ident_.tenant_id, n, deadline) for n in datasets}
        verdict_cache: dict[tuple[str, str], bool] = {}

        def allowed(cls: str, site: str) -> bool:
            key = (cls, site)
            if key not in verdict_cache:
                preq = PolicyAdapter.build_request(tenant_id=ident_.tenant_id, workload_id=ident_.workload_id, dataset="dag",
                                                   classification=cls, source_site=site, destination_site=site, operation="hold",
                                                   jurisdiction_tags=list(cfg.site_jurisdictions.get(site, ())), evaluated_at=self.clock.now())
                verdict_cache[key] = self.policy.evaluate(preq, deadline).allow
            return verdict_cache[key]

        def pair_cost(name: str, gb: float, cls: str, a: str, b: str) -> float | None:
            if not all(allowed(c, b) for c in cls.split("+")):
                return None
            if a == b:
                return 0.0
            if name in conv and not conv[name].converged:
                return None
            r = topo.routes.get((a, b))
            if r is None or not r["available"]:
                return None
            return gb * r["egress_per_gb"] * r["locality_multiplier"]

        def relocation(site: str) -> float:
            return 0.0 if place.compatible(site, WorkloadRequirements())[0] else float("inf")

        result = optimize_dag(stages, datasets, [c for c in cands if place.compatible(c, WorkloadRequirements())[0]],
                              pair_cost, relocation, max_assignments=int(cfg.knobs["max_batch"]) * 400)
        out = {"schema": "PK_GRAVITY_DAG_PLAN/1", "executable": False, **result,
               "inputs": {"topology": topo.ref(), "placement": place.ref()}, "actor": principal.subject}
        self._audit("dag.planned", {"digest": digest(out), "tenant_id": ident_.tenant_id})
        return out

    # ------------------------------------------------------ calibration
    def record_outcome(self, decision_id: str, observed: Mapping[str, float], token: Any) -> dict[str, Any]:
        """Feed observed execution outcome back (P2-37).  ``observed`` keys:
        money, transfer_hours, kg_co2.  Drift alarms raise telemetry and flip the
        calibration report to uncalibrated; they never change a live decision."""
        with self._rec_lock:
            rec = self._records.get(decision_id)
        if rec is None:
            raise G14Error("G14_INVALID_REQUEST", "unknown or expired decision id")
        self._authorize(token, "gravity:recommend", rec["tenant_id"])
        exact_fields(observed, "observed", [], ["money", "transfer_hours", "kg_co2"])
        bd = rec["envelope"]["recommendation"]["cost_breakdown"]
        predicted = {"money": bd.get("per_run_money", bd.get("total", 0.0)), "transfer_hours": bd.get("transfer_hours", 0.0),
                     "kg_co2": bd.get("per_run_kg_co2", 0.0)}
        dims = {"money": "money", "transfer_hours": "time", "kg_co2": "carbon"}
        alarms = {}
        for k, v in observed.items():
            alarms[k] = self.calibration.record(dims[k], predicted[k], number(v, f"observed.{k}"))
        self._audit("outcome.recorded", {"decision_id": decision_id, "observed": dict(observed), "alarms": alarms})
        return self.calibration.report()

    def _alive(self) -> bool:
        """Liveness = this process can still take its internal locks and run the canonical encoder.
        Deliberately independent of remote dependencies (no restart loops on dependency outages)."""
        if not self._rec_lock.acquire(timeout=0.1):
            return False
        try:
            return canonical_json({"probe": 1}) == b'{"probe":1}'
        finally:
            self._rec_lock.release()

    def drain(self) -> None:
        """Graceful shutdown: readiness goes false, new decisions are refused (G14_NOT_READY)."""
        self.draining = True
        self.log.log("info", "service.draining")

    # ----------------------------------------------------------- health
    def health(self) -> dict[str, Any]:
        """P1-17 probe contract: liveness is process-level; readiness is gated."""
        breakers = {a.dependency: a.breaker.state for a in (self.policy, self.topology, self.replication, self.placement)}
        breakers["PLN-06"] = self.dataplane.breaker.state
        checks = {"config": self.config.ready, "audit": self._last_audit_ok,
                  "decision_path": all(v != "open" for k, v in breakers.items() if k != "PLN-06"),
                  "not_draining": not self.draining}
        ready = all(checks.values())
        if ready != self._was_ready:
            self.m["readiness"].inc(to="ready" if ready else "not-ready")
            self._was_ready = ready
        return {"schema": "PK_HEALTH/1", "live": self._alive(), "ready": ready, "checks": checks, "dependencies": breakers,
                "config": self.config.active.ref() if self.config.ready else None, "version": __version__,
                "audit_head": self.audit.head, "inflight": self.admission.inflight,
                "reason_code": None if ready else "G14_NOT_READY"}
