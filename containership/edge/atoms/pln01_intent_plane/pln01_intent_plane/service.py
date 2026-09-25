"""PLN-01 service facade: the production request path.

Every mutation passes, in order:  schema validation -> authentication (fail
closed) -> capability authorization -> safety controls (disable/freeze/
quarantine) -> lease/fencing check -> tenant quota -> bulkhead + deadline ->
secret rejection -> constraint precedence -> artifact verification -> graph
admission (boundary rules + external policy) -> write-ahead durable commit ->
durable sealed audit -> metrics/logs/trace.

Responses are ``{"ok": True, ...}`` or ``{"ok": False, "error": PK_ERROR/1}``.
The plane still never executes plan steps.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import __version__
from .config import ActiveConfig, build_config
from .controls import Bulkhead, Deadline, SafetyControls, TenantQuotas
from .errors import (AuthenticationError, TransactionAbortedError, code_for, to_error)
from .graph import IntentGraph, ValidationError, plan as build_plan
from .metadata import SCHEMA_ACTUAL_STATE, SCHEMA_DECLARATION, SCHEMA_GRAPH
from .precedence import resolve as resolve_constraints
from .secret_guard import classify, reject_secrets
from .store import DurableStore, FileLease
from .telemetry import Health, Metrics, StructuredLogger, TraceContext
from .trust import ArtifactPolicy, Authenticator, Principal, authorize
from .validation import validate


class IntentPlaneService:
    def __init__(
        self,
        *,
        config: ActiveConfig | None = None,
        authenticator: Authenticator | None = None,
        artifact_policy: ArtifactPolicy | None = None,
        admission_policy: Callable | None = None,
        store: DurableStore | None = None,
        lease: FileLease | None = None,
        clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
        log_sink: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config or build_config(author="bootstrap")
        self.authenticator = authenticator
        self.artifact_policy = artifact_policy
        self.store, self.lease = store, lease
        self._clock, self._mono = clock, monotonic
        lim = dict(self.config.values["limits"])
        if store is not None:
            self.graph = store.open_graph(admission_policy=admission_policy, **lim)
        else:
            self.graph = IntentGraph(admission_policy=admission_policy, **lim)
        q, t = self.config.values["quotas"], self.config.values["timeouts"]
        self.quotas = TenantQuotas(rate=q["tenant_rate_per_second"], burst=q["tenant_burst"],
                                   max_nodes=q["tenant_max_nodes"], clock=monotonic)
        self.bulkhead = Bulkhead(q["max_concurrent_requests"], q["max_queue_depth"])
        self.controls = SafetyControls(clock=clock)
        self.metrics = Metrics()
        self.log = StructuredLogger(sink=log_sink, level=self.config.values["telemetry"]["log_level"])
        self.health = Health(clock=monotonic)
        self.health.register_dependency("identity", required=bool(self.config.values["security"]["require_authentication"]))
        self.health.register_dependency("durable_store", required=store is not None)
        self.health.register_dependency("policy_engine", required=False)
        self.health.register_dependency("observability", required=False)
        self.reports: dict[str, dict[str, Any]] = {}          # site -> latest report
        self.decisions: dict[tuple, list[dict[str, Any]]] = {}  # node -> explanation records
        self.released_plans: dict[str, dict[str, Any]] = {}
        self.health.ready_flag = True
        if self.authenticator is not None:
            self.health.report_dependency("identity", "up")
        if store is not None:
            self.health.report_dependency("durable_store", "up")

    # ----------------------------------------------------------- plumbing
    def _principal(self, credential: str | None) -> Principal:
        if not self.config.values["security"]["require_authentication"]:
            return Principal("anonymous-dev", "human", (("intent:admin", "*"),))
        if self.authenticator is None:
            raise AuthenticationError("authentication required but no authenticator configured")
        if credential is None:
            raise AuthenticationError("missing credential")
        try:
            return self.authenticator.authenticate(credential)
        except Exception as exc:
            if code_for(exc) == "PLN01-E0010":
                self.health.report_dependency("identity", "down", "authenticator unavailable")
            raise

    def _tenant_nodes(self, tenant: str) -> int:
        return self.graph.tenant_node_count(tenant)

    def _run(self, op: str, fn: Callable[[TraceContext], dict[str, Any]], traceparent: str | None,
             deadline_s: float | None) -> dict[str, Any]:
        trace = TraceContext.parse(traceparent).child()
        started = self._mono()
        deadline = Deadline(deadline_s or self.config.values["timeouts"]["request_deadline_seconds"], clock=self._mono)
        try:
            result = self.bulkhead.run(lambda: fn(trace), deadline)
            outcome, body = "ok", dict(result, ok=True)
        except Exception as exc:  # noqa: BLE001 - converted to PK_ERROR/1
            outcome = code_for(exc)
            body = {"ok": False, "error": to_error(exc, trace_id=trace.trace_id)}
            self.log.log("WARNING" if outcome != "PLN01-E9999" else "ERROR", f"{op}.failed", trace,
                         code=outcome, message=body["error"]["message"])
        elapsed = self._mono() - started
        self.metrics.inc("pln01_requests_total", op=op, outcome=outcome)
        self.metrics.observe("pln01_request_seconds", elapsed, op=op)
        self.metrics.set("graph_version", self.graph.version)
        self.metrics.set("pln01_bulkhead_saturation", self.bulkhead.saturation)
        self.health.heartbeat()
        body["traceparent"] = trace.header()
        return body

    def _audit(self, principal: Principal, operation: str, targets: Sequence, outcome: str, reason: str,
               trace: TraceContext) -> None:
        event = {"actor": principal.subject, "operation": operation, "targets": [list(t) for t in targets],
                 "outcome": outcome, "reason": reason, "graph_version": self.graph.version,
                 "trace_id": trace.trace_id, "config_digest": self.config.digest, "at": self._clock()}
        if self.store is not None:
            self.store.append_audit(event)
        for t in targets:
            self.decisions.setdefault(tuple(t), []).append(event)
            del self.decisions[tuple(t)][:-50]

    def _fence(self) -> None:
        if self.lease is not None:
            token = self.lease.check()
            if self.store is not None:
                self.store.fencing_token = token

    # ------------------------------------------------------------- declare
    def submit(self, request: Mapping[str, Any], *, credential: str | None = None,
               traceparent: str | None = None, deadline_s: float | None = None) -> dict[str, Any]:
        """Handle one ``PK_DECLARATION/1`` request."""
        def work(trace: TraceContext) -> dict[str, Any]:
            validate(request, SCHEMA_DECLARATION)
            principal = self._principal(credential)
            return self._apply(request, principal, trace)
        return self._run(str(request.get("operation", "declare")) if isinstance(request, Mapping) else "declare",
                         work, traceparent, deadline_s)

    def _apply(self, request: Mapping[str, Any], principal: Principal, trace: TraceContext) -> dict[str, Any]:
        tenant, environment, name = request["node"]
        op = request["operation"]
        cap = "intent:declare" if op == "declare" else "intent:retract"
        try:
            authorize(principal, cap, tenant, environment)
            self.controls.check_mutation(tenant, environment)
            self._fence()
            adding = 0 if self.graph.contains(tuple(request["node"])) else 1
            self.quotas.admit(tenant, self._tenant_nodes(tenant), adding if op == "declare" else 0)
            if op == "retract":
                removed = self.graph.retract(tuple(request["node"]), cascade=bool(request.get("cascade")),
                                             expected_version=request.get("expected_version"),
                                             request_id=request["request_id"], actor=principal.subject)
                self._audit(principal, "retract", removed or [request["node"]], "admitted", "retracted", trace)
                self.metrics.inc("declaration_admission", result="admitted", reason="retract")
                return {"removed": [list(k) for k in removed], "graph_version": self.graph.version}
            spec = dict(request.get("spec", {}))
            if self.config.values["security"]["reject_secrets"]:
                reject_secrets(spec)
            resolution = resolve_constraints(spec.get("constraints", [])) if "constraints" in spec else {}
            artifacts = request.get("artifacts", [])
            if artifacts and self.config.values["security"]["require_artifact_verification"]:
                if self.artifact_policy is None:
                    from .errors import ArtifactVerificationError
                    raise ArtifactVerificationError("artifact verification required but no policy configured")
                for art in artifacts:
                    self.artifact_policy.verify(art)
            if artifacts:
                spec["artifacts"] = [{"name": a["name"], "digest": a["digest"]} for a in artifacts]
            if "site" in request:
                spec.setdefault("site", request["site"])
            key = self.graph.declare(tenant, environment, name, spec,
                                     after=[tuple(d) for d in request.get("after", [])],
                                     expected_version=request.get("expected_version"),
                                     request_id=request["request_id"], actor=principal.subject)
        except Exception as exc:
            self.metrics.inc("declaration_admission", result="rejected", reason=code_for(exc))
            self._audit(principal, op, [request["node"]], "rejected", code_for(exc), trace)
            raise
        self.metrics.inc("declaration_admission", result="admitted", reason="ok")
        self._audit(principal, "declare", [key], "admitted", "validated and committed", trace)
        if resolution:
            self.decisions.setdefault(key, []).append({"constraint_resolution": resolution})
        if self.store is not None:
            self.store.maybe_snapshot()
        self.log.log("INFO", "declare.admitted", trace, node=list(key), graph_version=self.graph.version,
                     classification=classify(spec))
        return {"node": list(key), "graph_version": self.graph.version}

    # --------------------------------------------------------- transaction
    def transaction(self, requests: Sequence[Mapping[str, Any]], *, credential: str | None = None,
                    traceparent: str | None = None, deadline_s: float | None = None,
                    expected_version: int | None = None) -> dict[str, Any]:
        """All-or-nothing multi-declaration activation (MC-017)."""
        def work(trace: TraceContext) -> dict[str, Any]:
            if not requests or len(requests) > 1000:
                raise ValidationError("transaction must contain 1..1000 requests")
            for r in requests:
                validate(r, SCHEMA_DECLARATION)
            principal = self._principal(credential)
            with self.graph._lock:
                start = self.graph.version
                if expected_version is not None and expected_version != start:
                    from .graph import VersionConflictError
                    raise VersionConflictError(f"stale graph version {expected_version}; current {start}")
                for r in requests:
                    authorize(principal, "intent:transaction", r["node"][0], r["node"][1])
                applied = []
                try:
                    for r in requests:
                        applied.append(self._apply(r, principal, trace))
                except Exception as exc:
                    if self.graph.version != start:
                        self.graph.rollback(start, actor=principal.subject)
                    self._audit(principal, "transaction", [r["node"] for r in requests], "aborted", code_for(exc), trace)
                    raise TransactionAbortedError(
                        f"transaction aborted at step {len(applied) + 1}: {code_for(exc)}; restored version {start}",
                        cause=code_for(exc)) from exc
            return {"applied": applied, "from_version": start, "graph_version": self.graph.version}
        return self._run("transaction", work, traceparent, deadline_s)

    # -------------------------------------------------------------- report
    def report(self, document: Mapping[str, Any], *, credential: str | None = None,
               traceparent: str | None = None) -> dict[str, Any]:
        """Ingest ``PK_ACTUAL_STATE/1`` (MC-004 staleness/ordering semantics)."""
        def work(trace: TraceContext) -> dict[str, Any]:
            validate(document, SCHEMA_ACTUAL_STATE)
            principal = self._principal(credential)
            if principal.kind not in ("reporter", "service") and not principal.allows("intent:admin", "*", "*"):
                raise AuthenticationError("only reporter/service principals may report actual state")
            for n in document["nodes"]:
                authorize(principal, "intent:report", n["node"][0], n["node"][1])
            site = document["site"]
            prev = self.reports.get(site)
            seq = document.get("sequence", 0)
            if prev and (seq < prev["sequence"] or document["observed_at"] < prev["observed_at"]):
                return {"accepted": False, "reason": "out-of-order report ignored", "site": site}
            if document["observed_at"] > self._clock() + 300:
                raise ValidationError("report observed_at is in the future beyond skew allowance")
            self.reports[site] = {"sequence": seq, "observed_at": document["observed_at"], "reporter": principal.subject,
                                  "nodes": {tuple(n["node"]): n["spec"] for n in document["nodes"]}}
            self.health.report_dependency("observability", "up")
            return {"accepted": True, "site": site, "nodes": len(document["nodes"])}
        return self._run("report", work, traceparent, None)

    def site_status(self) -> dict[str, dict[str, Any]]:
        now = self._clock()
        out = {}
        for site, rep in sorted(self.reports.items()):
            age = now - rep["observed_at"]
            limit = self.config.staleness_for(site)
            out[site] = {"context": self.config.context_for(site), "age_seconds": round(age, 3),
                         "staleness_limit": limit, "state": "connected" if age <= limit else "disconnected"}
        return out

    # ---------------------------------------------------------------- plan
    def plan(self, *, credential: str | None = None, tenant: str | None = None, environment: str | None = None,
             release: bool = False, traceparent: str | None = None) -> dict[str, Any]:
        def work(trace: TraceContext) -> dict[str, Any]:
            principal = self._principal(credential)
            authorize(principal, "intent:plan", tenant or "*", environment or "*") if tenant else \
                authorize(principal, "intent:admin", "*", "*")
            status = self.site_status()
            actual: dict[tuple, Any] = {}
            for rep in self.reports.values():
                actual.update(rep["nodes"])
            started = self._mono()
            result = build_plan(self.graph, actual)
            self.metrics.observe("plan_emission_seconds", self._mono() - started)
            snap = self.graph.snapshot(result["graph_version"])
            site_of = {tuple(n["node"]): n["spec"].get("site") for n in snap["nodes"]}
            stale_sites = {s for s, v in status.items() if v["state"] == "disconnected"}
            steps = []
            for step in result["steps"]:
                k = tuple(step["node"])
                if tenant and (k[0] != tenant or (environment and k[1] != environment)):
                    continue
                if self.controls.is_quarantined(k[0], k[1]):
                    step = dict(step, held="quarantined")
                elif site_of.get(k) in stale_sites:
                    step = dict(step, held="site-disconnected")
                steps.append(step)
            drift = [d for d in result["drift"] if not tenant or d[0] == tenant]
            self.metrics.set("drift_open", len(drift))
            out = dict(result, steps=steps, drift=drift, stale_sites=sorted(stale_sites),
                       lineage={"component_version": __version__, "config_digest": self.config.digest})
            if release:
                if self.controls.disabled is not None:
                    from .errors import ScopeFrozenError
                    raise ScopeFrozenError("plan release disabled")
                self.released_plans[result["plan_id"]] = {"graph_version": result["graph_version"], "at": self._clock()}
                out["released"] = True
            return out
        return self._run("plan", work, traceparent, None)

    def verify_release(self, plan_id: str) -> None:
        """Downstream check: refuse replay of a released plan against a newer graph."""
        from .graph import VersionConflictError
        rec = self.released_plans.get(plan_id)
        if rec is None:
            raise ValidationError("unknown plan_id")
        if rec["graph_version"] != self.graph.version:
            raise VersionConflictError("plan was released against an older graph version; replan required")

    # ------------------------------------------------------------- reads
    def graph_view(self, *, credential: str | None = None, version: int | None = None) -> dict[str, Any]:
        def work(trace: TraceContext) -> dict[str, Any]:
            self._principal(credential)
            snap = self.graph.snapshot(version)
            validate(snap, SCHEMA_GRAPH)
            return {"graph": snap}
        return self._run("graph", work, None, None)

    def explain(self, node: Sequence[str]) -> dict[str, Any]:
        """Decision explanation and release lineage for one node (MC-036)."""
        key = tuple(node)
        try:
            spec = self.graph.node_spec(key)
        except KeyError:
            spec = None
        return {"node": list(key), "present": spec is not None,
                "decisions": [dict(d) for d in self.decisions.get(key, [])],
                "graph_version": self.graph.version,
                "lineage": {"component_version": __version__, "config": self.config.provenance()}}

    def rollback(self, target_version: int, *, credential: str | None = None, request_id: str) -> dict[str, Any]:
        def work(trace: TraceContext) -> dict[str, Any]:
            principal = self._principal(credential)
            authorize(principal, "intent:rollback", "*", "*")
            if self.controls.disabled is not None:
                from .errors import ScopeFrozenError
                raise ScopeFrozenError("mutations disabled")
            self._fence()
            v = self.graph.rollback(target_version, request_id=request_id, actor=principal.subject)
            self._audit(principal, "rollback", [], "admitted", f"restored {target_version}", trace)
            return {"graph_version": v}
        return self._run("rollback", work, None, None)
