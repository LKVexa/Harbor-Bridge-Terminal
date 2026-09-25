"""Production service layer for INV-63.

``DeploymentService`` wraps the pure :class:`manager.Manager` with every
production control named in the remediation checklist: typed/versioned wire
contracts, authentication, capability authorization, tenant namespacing,
admission/backpressure, idempotency, deadlines, lifecycle state machine,
durable fenced journal with crash replay, make-before-break reconciliation
through a lattice adapter with bounded retry + circuit breaker, bounded
rollouts with canary + automatic rollback, offline/degraded mode with
resynchronisation, quarantine/freeze/emergency disable, precedence rules,
quotas, metrics/logs/traces/decision records and an explain view.

Every public behaviour is covered by tests tagged with INV-63 C-IDs.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Callable

from . import preflight, schema
from .adapter import LatticeAdapter
from .config import config_digest
from .errors import DeploymentError, ErrorCode, Outcome, classify
from .lifecycle import Lifecycle, State
from .manager import Manager
from .observability import (DecisionLog, Logger, Metrics, SpanContext, Tracer, classify_alert,
                            topology_digest)
from .resilience import Admission, CircuitBreaker, Controls, Deadline, HealthMonitor, RetryPolicy
from .security import ArtifactVerifier, Authorizer, OP_CAPABILITY, Principal, TokenAuthority, namespace
from .store import Journal

VERSION = "4.3.0"
PRECEDENCE = ("security", "residency", "consistency", "slo", "cost")  # INV-63-C019


class DeploymentService:
    def __init__(self, *, config: dict[str, Any], hosts: dict[str, str], adapter: LatticeAdapter,
                 journal: Journal, tokens: TokenAuthority, verifier: ArtifactVerifier | None = None,
                 node: str = "node-0", clock: Callable[[], float] = time.time,
                 mono: Callable[[], float] = time.monotonic, retry: RetryPolicy | None = None,
                 release: str | None = None,
                 artifact_fetcher: Callable[[str], bytes] | None = None):
        self.config = config
        self.hosts = dict(hosts)
        self.adapter = adapter
        self.journal = journal
        self.tokens = tokens
        self.verifier = verifier
        self.node = node
        self.clock, self.mono = clock, mono
        self.release = release or f"inv63-{VERSION}"
        self.artifact_fetcher = artifact_fetcher   # digest -> bytes; when set, content is re-hashed
        self.manager = Manager(self.hosts)
        self.lifecycle = Lifecycle()
        self.authz = Authorizer()
        self.controls = Controls()
        self.metrics = Metrics()
        self.log = Logger(node)
        self.tracer = Tracer()
        self.decisions = DecisionLog()
        self.health = HealthMonitor(config["stall_threshold_s"], clock=mono)
        self.retry = retry or RetryPolicy(max_attempts=config["retry_max_attempts"], sleep=lambda s: None)
        self.breaker = CircuitBreaker(config["circuit_failure_threshold"], 10.0, clock=mono)
        self.admission = Admission(config["max_inflight"], queue_depth=config["queue_depth"], clock=mono)
        self.desired: dict[str, dict[str, Any]] = {}     # ns -> desired body
        self.history: dict[str, list[dict[str, Any]]] = {}  # ns -> last 10 desired bodies (rollback targets)
        self.pending: list[dict[str, Any]] = []          # offline intents awaiting resync
        self.offline_since: float | None = None
        self._idem: OrderedDict[tuple[str, str], tuple[str, dict[str, Any]]] = OrderedDict()
        if config["require_encryption_at_rest"] and getattr(journal, "sealer", None) is None:
            raise DeploymentError(ErrorCode.CONFIG_INVALID,
                                  "require_encryption_at_rest is set but the journal has no Sealer attached")
        self._recover()

    # ================================================================ recovery (C057)
    def _recover(self) -> None:
        for rec in self.journal:
            d = rec.data
            if rec.kind == "snapshot":
                self._load_snapshot(d)
            elif rec.kind == "desired_set":
                self._set_desired_mem(d["ns"], d["body"])
            elif rec.kind == "lifecycle":
                t, c = d["ns"].split("/", 1)
                self.lifecycle.restore(t, c, State(d["to"]))
            elif rec.kind == "control":
                getattr(self.controls, d["set"]).discard(d["target"]) if d["op"] == "remove" else \
                    getattr(self.controls, d["set"]).add(d["target"])
            elif rec.kind == "host_quarantine":
                (self.controls.quarantined_hosts.add if d["on"] else self.controls.quarantined_hosts.discard)(d["host"])
            elif rec.kind == "emergency_disable":
                self.controls.global_disabled = d["on"]
            elif rec.kind == "offline_intent":
                self.pending.append(d)
            elif rec.kind == "resynced":
                self.pending = [p for p in self.pending if p["ns"] not in d["ns"]]
            elif rec.kind == "idempotency":
                self._idem[(d["sub"], d["key"])] = (d["digest"], {"outcome": d["outcome"], "replayed": True})
        if self.journal.epoch == 0:
            self.journal.acquire()
        self.log.log("info", "recovered", operation="recover", records=len(self.journal.records),
                     epoch=self.journal.epoch, torn_tail=self.journal.recovered_torn_tail)

    # ================================================================ helpers
    def _move(self, ns: str, dst: State, reason: str) -> None:
        tenant, comp = ns.split("/", 1)
        src = self.lifecycle.get(tenant, comp)
        if src is dst:
            return
        self.lifecycle.move(tenant, comp, dst, reason)
        self.journal.append("lifecycle", {"ns": ns, "from": src.value if src else None, "to": dst.value,
                                          "reason": reason})

    def _verify_artifact(self, body: dict[str, Any]) -> str:
        art = body.get("artifact") or {}
        blob = self.artifact_fetcher(art["digest"]) if (self.artifact_fetcher and art.get("digest")) else None
        return self.verifier.verify(body["component"], body["version"], body.get("artifact"), blob=blob)

    def _set_desired_mem(self, ns: str, body: dict[str, Any]) -> None:
        self.desired[ns] = body
        h = self.history.setdefault(ns, [])
        h.append(body)
        del h[:-10]

    def _to_degraded(self, ns: str, reason: str) -> None:
        if self.lifecycle.get(*ns.split("/", 1)) is State.VALIDATED:
            self._move(ns, State.RECONCILING, reason)
        self._move(ns, State.DEGRADED, reason)

    def _decide(self, ns: str, action: str, reason: str, trace: SpanContext, *, inputs=None, policies=None,
                constraints=None) -> None:
        tenant, comp = ns.split("/", 1)
        self.decisions.record(tenant=tenant, component=comp, action=action, reason=reason, inputs=inputs or {},
                              policies=policies or [], constraints=constraints or {}, trace_id=trace.trace_id,
                              release=self.release, topology_digest=topology_digest(self.hosts))
        self.metrics.inc("decisions", action=action)

    def _eligible(self, body: dict[str, Any]) -> list[str]:
        """Precedence: security (quarantine) > residency > SLO (spread) > cost."""
        hosts = [h for h in self.hosts if h not in self.controls.quarantined_hosts]
        residency = body.get("residency")
        if residency:
            labels = self.config.get("residency_labels", {})
            hosts = [h for h in hosts if labels.get(h) in residency]
        return sorted(hosts)

    def _observe(self) -> bool:
        """Refresh actual state from the lattice; False when offline."""
        try:
            actual = self.breaker.call(lambda: self.retry.run(self.adapter.list_instances, idempotent=True))
        except DeploymentError as exc:
            if exc.code in (ErrorCode.CONTROL_PLANE_OFFLINE, ErrorCode.CIRCUIT_OPEN,
                            ErrorCode.DEPENDENCY_UNAVAILABLE):
                if self.offline_since is None:
                    self.offline_since = self.mono()
                self.metrics.set("control_plane_up", 0)
                return False
            raise
        self.manager.actual = [a for a in actual if a[2] in self.hosts]
        self.offline_since = None
        self.metrics.set("control_plane_up", 1)
        return True

    # ================================================================ wire entry point
    def handle(self, raw: bytes) -> dict[str, Any]:
        t0 = self.mono()
        trace = SpanContext.parse(None, self.config["telemetry_sampling"])
        op, tenant, subject = "-", "-", "-"
        try:
            req = schema.parse_bytes(raw, "PK_DEPLOY_REQUEST/1")
            trace = SpanContext.parse(req.get("traceparent"), self.config["telemetry_sampling"])
            op = req["op"]
            if "accept_versions" in req:
                schema.negotiate("PK_DEPLOY_REQUEST", req["accept_versions"])
            deadline = Deadline(min(req.get("deadline_ms", self.config["request_timeout_ms"]),
                                    self.config["request_timeout_ms"]) / 1000.0, clock=self.mono)
            principal = self.tokens.verify(req["token"])
            subject = principal.subject
            body = req["body"]
            tenant = body.get("tenant", principal.tenant) if isinstance(body.get("tenant"), str) else principal.tenant
            self.authz.check(principal, OP_CAPABILITY[op], tenant)
            digest = hashlib.sha256(json.dumps([op, body], sort_keys=True).encode()).hexdigest()
            key = (principal.subject, req["idempotency_key"])
            if key in self._idem:
                prev_digest, prev = self._idem[key]
                if prev_digest != digest:
                    raise DeploymentError(ErrorCode.CONFLICT, "idempotency key reused with a different body")
                self.metrics.inc("idempotent_replays")
                return {"schema": "PK_DEPLOY_RESPONSE/1", **prev, "trace_id": trace.trace_id}
            self.admission.enter(tenant, body.get("priority", "standard"))
            span = self.tracer.span(f"inv63.{op}", trace, tenant=tenant, op=op)
            try:
                result = getattr(self, f"op_{op}")(principal, body, trace, deadline)
            except Exception as exc:
                self.tracer.finish(span, f"ERROR:{classify(exc).code.value}")
                raise
            finally:
                self.admission.leave()
            self.tracer.finish(span, "OK")
            outcome = result.pop("outcome", Outcome.SUCCESS.value)
            resp = {"schema": "PK_DEPLOY_RESPONSE/1", "outcome": outcome, "result": result,
                    "trace_id": trace.trace_id}
            if op not in ("explain",):
                self._idem[key] = (digest, {"outcome": outcome, "result": result})
                self.journal.append("idempotency", {"sub": principal.subject, "key": req["idempotency_key"],
                                                    "digest": digest, "outcome": outcome})
                while len(self._idem) > 10_000:
                    self._idem.popitem(last=False)
            self.metrics.inc("requests", op=op, outcome=outcome)
            return resp
        except Exception as exc:  # every failure leaves as a structured error
            err = classify(exc)
            self.metrics.inc("errors", op=op, code=err.code.value)
            self.metrics.inc("alerts", cls=classify_alert(err.code.value))
            self.log.log("warn", "request_failed", tenant=tenant, operation=op, trace_id=trace.trace_id,
                         code=err.code.value, subject=subject, message=err.message)
            return {"schema": "PK_DEPLOY_RESPONSE/1", "outcome": err.outcome.value, "error": err.to_dict(),
                    "trace_id": trace.trace_id}
        finally:
            self.metrics.observe("request_latency_ms", (self.mono() - t0) * 1000.0, op=op)

    # ================================================================ operations
    def op_set_desired(self, p: Principal, body: dict[str, Any], trace: SpanContext, dl: Deadline) -> dict:
        ref = body.get("schema", "")
        name, major = schema.parse_id(ref)
        if name != "PK_DEPLOY_DESIRED":
            raise DeploymentError(ErrorCode.SCHEMA_VIOLATION, "body must be PK_DEPLOY_DESIRED")
        schema.validate(body, ref)
        ns = namespace(body["tenant"], body["component"])
        self.controls.check(ns)
        policies = []
        if self.config["require_signed_artifacts"]:
            if major < 2:
                raise DeploymentError(ErrorCode.ARTIFACT_UNTRUSTED,
                                      "signed artifacts are required; PK_DEPLOY_DESIRED/1 carries no signature")
            if self.verifier is None:
                raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE, "artifact verifier unavailable: fail closed")
            self._verify_artifact(body)
            policies.append("signed-artifact")
        quota = self.config.get("tenant_quotas", {}).get(body["tenant"])
        if quota is not None:
            used = sum(d["count"] for n, d in self.desired.items() if n.startswith(body["tenant"] + "/") and n != ns)
            if used + body["count"] > quota["max_instances"]:
                raise DeploymentError(ErrorCode.QUOTA_EXCEEDED, "tenant instance quota exceeded",
                                      {"quota": quota["max_instances"], "requested": used + body["count"]})
            policies.append("tenant-quota")
        eligible = self._eligible(body)
        if body["count"] and not eligible:
            raise DeploymentError(ErrorCode.POLICY_REJECTED, "no host satisfies residency/security constraints",
                                  {"residency": body.get("residency")})
        if body.get("residency"):
            policies.append("residency")
        dl.check()
        if self.lifecycle.get(body["tenant"], body["component"]) in (None, State.DELETED):
            self._move(ns, State.PENDING, "desired state accepted")
        self.journal.append("desired_set", {"ns": ns, "body": body})
        self._set_desired_mem(ns, body)
        self._move(ns, State.VALIDATED, "admission, schema and policy checks passed")
        self._decide(ns, "accept_desired", f"desired {body['version']} x{body['count']} accepted",
                     trace, inputs={"count": body["count"], "version": body["version"]}, policies=policies,
                     constraints={"eligible_hosts": len(eligible)})
        return {"ns": ns, "state": State.VALIDATED.value}

    def op_reconcile(self, p: Principal, body: dict[str, Any], trace: SpanContext, dl: Deadline) -> dict:
        ns = namespace(body.get("tenant", p.tenant), body["component"])
        self.controls.check(ns)
        if ns not in self.desired:
            raise DeploymentError(ErrorCode.PRECONDITION_FAILED, f"no desired state for {ns}")
        return self.reconcile_ns(ns, trace, dl)

    def reconcile_ns(self, ns: str, trace: SpanContext | None = None, dl: Deadline | None = None) -> dict:
        trace = trace or SpanContext.parse(None)
        dl = dl or Deadline(self.config["request_timeout_ms"] / 1000, clock=self.mono)
        self.controls.check(ns)             # freeze/quarantine/emergency-disable gate every lattice action
        d = self.desired[ns]
        self.health.begin(ns)
        online = self._observe()
        spread = d.get("spread", True)
        eligible = self._eligible(d)
        if spread and len({self.hosts[h] for h in eligible}) < 2 and d["count"] > 1:
            spread_note = "spread relaxed: residency/security precede SLO spread"
        else:
            spread_note = None
        plan = self.manager.diff(ns, d["version"], d["count"], spread, eligible_hosts=eligible)
        self.manager.audit_events.clear()   # the fenced journal is the audit of record (bounded memory, C067)
        if not online:
            if self.offline_since is not None and self.mono() - self.offline_since > self.config["offline_autonomy_s"]:
                raise DeploymentError(ErrorCode.CONTROL_PLANE_OFFLINE, "offline beyond autonomy window",
                                      retry_after_s=self.config["reconcile_interval_s"])
            intent = {"ns": ns, "version": d["version"], "count": d["count"], "at": self.clock()}
            self.journal.append("offline_intent", intent)
            self.pending.append(intent)
            self._to_degraded(ns, "control plane offline; intent journaled")
            self._decide(ns, "defer_offline", "lattice unreachable; intent queued for resync", trace,
                         constraints={"offline_autonomy_s": self.config["offline_autonomy_s"]})
            return {"outcome": Outcome.DEGRADED.value, "ns": ns, "queued": True}
        if not plan["start"] and not plan["stop"]:
            self._move(ns, State.RECONCILING if self.lifecycle.get(*ns.split("/", 1)) in
                       (State.VALIDATED, State.DEGRADED) else State.CONVERGED, "no actions")
            self._move(ns, State.CONVERGED, "actual equals desired")
            if d["count"] == 0:
                self._move(ns, State.DELETED, "desired count 0 and no instances remain")
            self.health.progress(ns)
            self.metrics.inc("reconciles", result="noop")
            return {"outcome": Outcome.SUCCESS.value, "ns": ns, "started": 0, "stopped": 0}
        self._move(ns, State.RECONCILING, "diff non-empty")
        self._decide(ns, "reconcile", f"start {len(plan['start'])} stop {len(plan['stop'])} to reach desired",
                     trace, inputs={"desired": d["count"], "version": d["version"]},
                     policies=["spread" if spread else "pack"] + (["residency"] if d.get("residency") else []),
                     constraints={"eligible": eligible, "note": spread_note})
        started, stopped, failed = [], [], []
        # make-before-break: start new capacity first, then stop surplus/stale
        for inst in plan["start"]:
            dl.check()
            try:
                self.breaker.call(lambda i=inst: self.retry.run(lambda: self.adapter.start(i), idempotent=True,
                                                                deadline=dl))
                started.append(inst)
                self.journal.append("action_committed", {"ns": ns, "op": "start", "inst": list(inst)})
            except DeploymentError as exc:
                failed.append((inst, exc.code.value))
        for inst in plan["stop"]:
            dl.check()
            if failed and inst[1] == d["version"]:
                continue   # keep capacity when replacements failed
            self.breaker.call(lambda i=inst: self.retry.run(lambda: self.adapter.stop(i), idempotent=True,
                                                            deadline=dl))
            stopped.append(inst)
            self.journal.append("action_committed", {"ns": ns, "op": "stop", "inst": list(inst)})
        self._observe()
        self.metrics.inc("actions", len(started), kind="start")
        self.metrics.inc("actions", len(stopped), kind="stop")
        if failed:
            self._move(ns, State.DEGRADED, f"{len(failed)} starts failed")
            self.metrics.inc("reconciles", result="partial")
            return {"outcome": Outcome.PARTIAL.value, "ns": ns, "started": len(started), "stopped": len(stopped),
                    "failed": [{"inst": list(i), "code": c} for i, c in failed]}
        self._move(ns, State.CONVERGED, "all actions committed")
        if d["count"] == 0:
            self._move(ns, State.DELETED, "desired count 0 and no instances remain")
        self.health.progress(ns)
        self.metrics.inc("reconciles", result="applied")
        return {"outcome": Outcome.SUCCESS.value, "ns": ns, "started": len(started), "stopped": len(stopped)}

    def op_rollout(self, p: Principal, body: dict[str, Any], trace: SpanContext, dl: Deadline) -> dict:
        body = dict(body)
        body.setdefault("schema", "PK_DEPLOY_ROLLOUT/1")
        schema.validate(body, "PK_DEPLOY_ROLLOUT/1")
        ns = namespace(body["tenant"], body["component"])
        self.controls.check(ns)
        if ns not in self.desired:
            raise DeploymentError(ErrorCode.PRECONDITION_FAILED, f"no desired state for {ns}")
        if not self._observe():
            raise DeploymentError(ErrorCode.CONTROL_PLANE_OFFLINE, "rollouts are not started while offline",
                                  retry_after_s=self.config["reconcile_interval_s"])
        if self.config["require_signed_artifacts"]:
            if self.verifier is None:
                raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE, "artifact verifier unavailable: fail closed")
            self._verify_artifact(body)
        old_version = self.desired[ns]["version"]
        new, maxu, canary = body["version"], body["max_unavailable"], body.get("canary", 0)
        self._move(ns, State.ROLLING_OUT, f"{old_version} -> {new}")
        self._decide(ns, "rollout", f"bounded rollout {old_version}->{new} max_unavailable={maxu}", trace,
                     inputs={"from": old_version, "to": new}, constraints={"max_unavailable": maxu, "canary": canary})
        replaced: list[tuple] = []
        batches, worst = 0, 0
        first = True
        while True:
            dl.check()
            old = [a for a in self.manager.actual if a[0] == ns and a[1] != new]
            if not old:
                break
            size = canary if (first and canary) else maxu
            batch = old[:size]
            first = False
            worst = max(worst, len(batch))
            try:
                for inst in batch:
                    self.adapter.stop(inst)
                    ni = (ns, new, inst[2])
                    self.breaker.call(lambda i=ni: self.retry.run(lambda: self.adapter.start(i), idempotent=True,
                                                                  deadline=dl))
                    replaced.append((inst, ni))
                    if not self.adapter.healthy(ni):
                        raise DeploymentError(ErrorCode.ROLLOUT_FAILED, f"{ni} unhealthy after start")
            except DeploymentError as exc:
                self._move(ns, State.ROLLING_BACK, f"automatic rollback: {exc.code.value}")
                try:
                    self._rollback(ns, replaced, batch, new)
                except DeploymentError as rb_exc:
                    self._move(ns, State.FAILED, f"rollback incomplete: {rb_exc.code.value}")
                    self.metrics.inc("rollbacks", kind="failed")
                    raise DeploymentError(ErrorCode.ROLLOUT_FAILED, "rollout failed AND rollback incomplete; "
                                          "operator action required", {"cause": exc.code.value,
                                                                       "rollback_error": rb_exc.code.value,
                                                                       "state": State.FAILED.value}) from None
                self._observe()
                self._move(ns, State.CONVERGED if len([a for a in self.manager.actual if a[0] == ns])
                           >= self.desired[ns]["count"] else State.DEGRADED, "rollback complete")
                self._decide(ns, "auto_rollback", f"rollout to {new} failed ({exc.code.value}); restored {old_version}",
                             trace, inputs={"batch": batches + 1})
                self.metrics.inc("rollbacks", kind="automatic")
                raise DeploymentError(ErrorCode.ROLLOUT_FAILED, f"rollout to {new} failed and was rolled back",
                                      {"batch": batches + 1, "cause": exc.code.value, "restored": old_version}) from None
            batches += 1
            self._observe()
            self.journal.append("rollout_batch", {"ns": ns, "batch": batches, "to": new, "size": len(batch)})
            self.metrics.inc("rollout_batches")
        body_d = dict(self.desired[ns])
        body_d["version"] = new
        if "artifact" in body:
            body_d["artifact"] = body["artifact"]
        self.journal.append("desired_set", {"ns": ns, "body": body_d})
        self._set_desired_mem(ns, body_d)
        self._move(ns, State.CONVERGED, f"rollout to {new} complete")
        return {"ns": ns, "batches": batches, "worst_unavailable": worst}

    def _rollback(self, ns: str, replaced: list[tuple], batch: list[tuple], new: str) -> None:
        for old_inst, new_inst in reversed(replaced):
            try:
                self.adapter.stop(new_inst)
            except DeploymentError:
                pass
            self.adapter.start(old_inst)
        # restore any instance of the failing batch that was stopped but not replaced
        running = set(self.adapter.list_instances())
        for inst in batch:
            if inst not in running and inst not in [o for o, _ in replaced]:
                self.adapter.start(inst)
        self.journal.append("rollback", {"ns": ns, "restored": len(replaced), "abandoned": new})

    def op_rollback(self, p: Principal, body: dict[str, Any], trace: SpanContext, dl: Deadline) -> dict:
        """Operator-driven rollback to the previous desired version recorded in the journal."""
        ns = namespace(body["tenant"], body["component"])
        cur = self.desired.get(ns, {}).get("version")
        prior = [b for b in self.history.get(ns, []) if b["version"] != cur]
        if not prior:
            raise DeploymentError(ErrorCode.PRECONDITION_FAILED, "no previous version to roll back to")
        d = dict(prior[-1])
        d["count"] = self.desired[ns]["count"]
        target = d["version"]
        self.controls.check(ns)
        self._move(ns, State.ROLLING_BACK, f"operator rollback to {target}")
        self._decide(ns, "operator_rollback", f"operator {p.subject} rolled back to {target}", trace)
        self.journal.append("desired_set", {"ns": ns, "body": d})
        self._set_desired_mem(ns, d)
        self.metrics.inc("rollbacks", kind="operator")
        return self.reconcile_ns(ns, trace, dl) | {"rolled_back_to": target}

    def _control(self, p: Principal, body: dict, trace: SpanContext, which: str, op: str) -> dict:
        target = namespace(body["tenant"], body.get("component", "*"))
        getattr(self.controls, which).add(target) if op == "add" else getattr(self.controls, which).discard(target)
        self.journal.append("control", {"set": which, "op": op, "target": target, "by": p.subject})
        tenant, comp = target.split("/", 1)
        if comp != "*" and self.lifecycle.get(tenant, comp) is not None:
            if op == "add":
                self._move(target, State.QUARANTINED if which == "quarantined" else State.FROZEN, f"operator {p.subject}")
            else:
                self._move(target, State.VALIDATED, f"released by {p.subject}")
        self._decide(target if comp != "*" else f"{tenant}/*", f"{which}_{op}", f"operator {p.subject}: {body.get('reason', 'no reason given')}", trace)
        return {"target": target, which: op == "add"}

    def op_freeze(self, p, body, trace, dl):
        return self._control(p, body, trace, "frozen", "add")

    def op_unfreeze(self, p, body, trace, dl):
        return self._control(p, body, trace, "frozen", "remove")

    def op_quarantine(self, p, body, trace, dl):
        return self._control(p, body, trace, "quarantined", "add")

    def op_release_quarantine(self, p, body, trace, dl):
        return self._control(p, body, trace, "quarantined", "remove")

    def op_explain(self, p, body, trace, dl):
        return self.decisions.explain(body.get("tenant", p.tenant), body["component"])

    # ================================================================ snapshot / compaction (C057, C067)
    def snapshot(self) -> dict[str, Any]:
        return {
            "desired": self.desired,
            "history": self.history,
            "lifecycle": {f"{t}/{c}": st.value for (t, c), st in self.lifecycle._state.items()},
            "frozen": sorted(self.controls.frozen), "quarantined": sorted(self.controls.quarantined),
            "quarantined_hosts": sorted(self.controls.quarantined_hosts),
            "global_disabled": self.controls.global_disabled,
            "pending": self.pending,
            "idempotency": [[s, k, dg, v["outcome"]] for (s, k), (dg, v) in list(self._idem.items())[-10_000:]],
        }

    def _load_snapshot(self, snap: dict[str, Any]) -> None:
        self.desired = dict(snap["desired"])
        self.history = {k: list(v) for k, v in snap.get("history", {}).items()}
        for ns, st in snap["lifecycle"].items():
            t, c = ns.split("/", 1)
            self.lifecycle.restore(t, c, State(st))
        self.controls.frozen = set(snap["frozen"])
        self.controls.quarantined = set(snap["quarantined"])
        self.controls.quarantined_hosts = set(snap["quarantined_hosts"])
        self.controls.global_disabled = snap["global_disabled"]
        self.pending = list(snap["pending"])
        self._idem = OrderedDict(((s, k), (dg, {"outcome": o, "replayed": True})) for s, k, dg, o in snap["idempotency"])

    def compact(self) -> dict[str, Any]:
        """Replace the journal with one snapshot record chained to the old head."""
        return self.journal.compact(self.snapshot())

    # ================================================================ operator-only controls
    def _operator(self, principal: Principal, capability: str) -> str:
        if not isinstance(principal, Principal) or capability not in principal.capabilities or principal.tenant != "*":
            raise DeploymentError(ErrorCode.FORBIDDEN, f"{capability} requires a platform operator principal")
        return principal.subject

    def emergency_disable(self, on: bool, principal: Principal) -> None:
        actor = self._operator(principal, "control:freeze")
        self.controls.global_disabled = on
        self.journal.append("emergency_disable", {"on": on, "by": actor})
        self.log.log("crit" if on else "info", "emergency_disable", operation="emergency_disable", on=on, actor=actor)

    def quarantine_host(self, host: str, on: bool, principal: Principal) -> None:
        """Isolate a suspect node: no new placements; reconcile moves workloads off it."""
        actor = self._operator(principal, "control:quarantine")
        if host not in self.hosts:
            raise DeploymentError(ErrorCode.PRECONDITION_FAILED, f"unknown host {host}")
        (self.controls.quarantined_hosts.add if on else self.controls.quarantined_hosts.discard)(host)
        self.journal.append("host_quarantine", {"host": host, "on": on, "by": actor})

    def resync(self) -> dict[str, Any]:
        """Drain offline intents after connectivity returns (C018/C089)."""
        if not self._observe():
            return {"resynced": [], "pending": len(self.pending)}
        done = []
        for ns in sorted({p["ns"] for p in self.pending}):
            if ns in self.desired:
                r = self.reconcile_ns(ns)
                if r["outcome"] in (Outcome.SUCCESS.value,):
                    done.append(ns)
        if done:
            self.journal.append("resynced", {"ns": done})
            self.pending = [p for p in self.pending if p["ns"] not in done]
        return {"resynced": done, "pending": len(self.pending)}

    def tick(self) -> dict[str, Any]:
        """Periodic control loop: reconcile everything not frozen; report stalls."""
        results = {}
        if self.pending:
            self.resync()
        for ns in sorted(self.desired):
            try:
                self.controls.check(ns)
            except DeploymentError:
                continue
            try:
                results[ns] = self.reconcile_ns(ns)["outcome"]
            except DeploymentError as exc:
                results[ns] = exc.outcome.value
        stalled = self.health.stalled()
        self.metrics.set("stalled_workloads", len(stalled))
        return {"results": results, "stalled": stalled}

    # ================================================================ health (C071)
    def status(self, reference_time: float | None = None) -> dict[str, Any]:
        checks = preflight.run(hosts=self.hosts, state_dir=self.journal.dir, adapter=self.adapter,
                               reference_time=reference_time, clock=self.clock,
                               max_clock_skew_s=self.config["max_clock_skew_s"],
                               crypto_required=self.config["require_signed_artifacts"],
                               runtime_capabilities=(self.adapter.capabilities()
                                                     if hasattr(self.adapter, "capabilities") else None))
        leader = self.journal.epoch == self.journal.current_epoch()
        ready = preflight.ready(checks) and leader and not self.controls.global_disabled
        return {
            "schema": "INV63_STATUS/1", "version": VERSION, "release": self.release, "node": self.node,
            "live": True, "ready": ready, "leader": leader, "epoch": self.journal.epoch,
            "degraded": self.offline_since is not None or bool(self.pending),
            "config_digest": config_digest(self.config),
            "dependencies": {"lattice": "up" if self.adapter.ping() else "down", "journal": "ok",
                             "breaker": self.breaker.state},
            "capabilities": sorted({"desired/1", "desired/2", "diff/1", "rollout/1", "explain", "offline-mode",
                                    "canary", "auto-rollback"}),
            "controls": {"emergency_disabled": self.controls.global_disabled,
                         "frozen": sorted(self.controls.frozen), "quarantined": sorted(self.controls.quarantined)},
            "stalled": self.health.stalled(),
            "preflight": [c.to_dict() for c in checks],
        }
