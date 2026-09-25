"""GovernedRuntime: the integrated INV-69 service layer (v4.3.0).

Composes the unchanged safety kernel (``runtime.Agent``) with configuration
generations, deployment profiles, trust gating, authorization (INV-59),
durable execution + fencing (INV-57), sandbox tiers (INV-70/71), retry,
admission/backpressure, lifecycle state machines, precedence resolution,
telemetry, lineage, a hash-chained PK_AGENT_RUN_EVENT/1 stream and explain
records.  Nothing here weakens a kernel decision: the kernel runs first and
its refusal is final.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any
import hashlib
import json
import secrets
import threading
import time

from .compat import COMPONENT_VERSION, handshake
from .config import ConfigStore, EffectiveConfig
from .context import Admission, CallContext
from .errors import AgentError, code_for_reason, translate
from .health import Watchdog, build_status
from .lifecycle import InvocationState, Lifecycle, RunState
from .precedence import PRECEDENCE_POLICY, Constraint, resolve as resolve_constraints
from .retry import RetryPolicy, call_with_retry
from .runtime import TOOLS, Agent, _arg_shape, _canonical_bytes
from .sandbox import (AuthorizationAdapter, DurableExecutionAdapter, SandboxAdapter, TIER_STRENGTH,
                      idempotency_key, select_failover_target)
from .telemetry import Lineage, Telemetry, TopologyAdapter
from .trust import Connectivity, TrustMonitor

RUN_EVENT_SCHEMA = "PK_AGENT_RUN_EVENT/1"


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass
class Run:
    run_id: str
    tenant: str
    principal: str
    agent: Agent
    lifecycle: Lifecycle
    fence: int
    ctx: CallContext
    invocations: dict[str, Lifecycle] = field(default_factory=dict)
    admitted: bool = False


class GovernedRuntime:
    def __init__(self, *, config: ConfigStore, authz: AuthorizationAdapter, durable: DurableExecutionAdapter,
                 fast: SandboxAdapter | None, heavy: SandboxAdapter, node: str = "node-0", executor_id: str | None = None,
                 trust: TrustMonitor | None = None, telemetry: Telemetry | None = None,
                 topology: TopologyAdapter | None = None, release: Mapping[str, str] | None = None,
                 trust_domain: str = "td-default", sleep=time.sleep, clock=time.time):
        self.config = config
        eff = config.active.config
        self.node, self.executor_id = node, executor_id or f"{node}:{secrets.token_hex(4)}"
        self.authz, self.durable, self.fast, self.heavy = authz, durable, fast, heavy
        self.trust = trust or TrustMonitor(max_queue=eff.get("offline.max_queue"))
        self.telemetry = telemetry or Telemetry(sample_rate=eff.get("telemetry.trace_sample_rate"),
                                                zone=eff.get("residency.zone"))
        self.topology = topology or TopologyAdapter()
        self.release = dict(release or {})
        self.trust_domain = trust_domain
        self._sleep, self._clock = sleep, clock
        self._lock = threading.RLock()
        self.runs: dict[str, Run] = {}
        self.events: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []
        self._head = "0" * 64
        self._base_seq, self._base_head = 0, "0" * 64   # after archive_events(): first retained seq / its prev_hash
        self.contained = False
        self.forced_heavy = False
        self.audit_export_overflow = 0
        self.admission = Admission(eff.get("concurrency.max_active"), eff.get("concurrency.max_waiting"),
                                   eff.get("concurrency.reserved_critical"))
        self.watchdog = Watchdog(warning_s=eff.get("health.stall_warning_s"), critical_s=eff.get("health.stall_critical_s"),
                                 queue_warn_s=eff.get("health.queue_age_warning_s"),
                                 queue_crit_s=eff.get("health.queue_age_critical_s"))
        self.peers: dict[str, dict] = {}
        self._handshake_all()

    # ------------------------------------------------------------------ infrastructure
    @property
    def eff(self) -> EffectiveConfig:
        return self.config.active.config

    def _handshake_all(self) -> None:
        for p, req in ((self.authz, frozenset({"error_codes.v1"})), (self.durable, frozenset({"fencing_tokens", "idempotency_keys"})),
                       (self.heavy, frozenset({"idempotency_keys"}))) + (((self.fast, frozenset({"idempotency_keys"})),) if self.fast else ()):
            self.peers[p.component] = handshake(p.hello(), required=req)

    def lineage(self) -> Lineage:
        # C066: cached per (config generation, topology snapshot, staleness bucket); recomputed when any changes
        snap = getattr(self.topology, "_snap", None)
        key = (self.config.active.number, id(snap), snap and snap.get("version"),
               int(self._clock() // 60))
        if getattr(self, "_lineage_key", None) != key:
            rel = dict(self.release, config_generation=str(self.config.active.number))
            self._lineage_cache = self.topology.lineage(self.node, release=rel)
            self._lineage_key = key
        return self._lineage_cache

    def _event(self, kind: str, ctx: CallContext | None, **fields) -> dict[str, Any]:
        with self._lock:
            ev = {
                "schema": RUN_EVENT_SCHEMA, "seq": self._base_seq + len(self.events), "kind": kind, "at": self._clock(),
                "executor": self.executor_id, "correlation_id": ctx.correlation_id if ctx else None,
                "trace_id": ctx.trace.trace_id if ctx else None, "span_id": ctx.trace.span_id if ctx else None,
                "config_digest": self.eff.digest, "config_generation": self.config.active.number,
                "profile": self.eff.profile["context"], "precedence_policy": PRECEDENCE_POLICY["version"],
                "lineage": self.lineage().as_labels(), **fields, "prev_hash": self._head,
            }
            ev["event_hash"] = _digest(ev)
            self._head = ev["event_hash"]
            self.events.append(ev)
            self.watchdog.audit_progress()
        try:
            self.telemetry.record("audit", ev)
        except OverflowError:
            # The chain above is the authoritative audit record; the export buffer is a copy.  Never fail
            # *after* work happened: new work is refused up-front by _check_audit_backpressure instead.
            self.audit_export_overflow += 1
        return ev

    def _check_audit_backpressure(self, ctx: CallContext) -> None:
        if self.telemetry.buffer_full("audit"):
            raise AgentError("AGT-CAP-003", "audit export backlog full; flush or archive before new work",
                             correlation_id=ctx.correlation_id)

    def verify_events(self) -> bool:
        prev = self._base_head
        for i, ev in enumerate(self.events):
            body = {k: v for k, v in ev.items() if k != "event_hash"}
            if ev["seq"] != self._base_seq + i or ev["prev_hash"] != prev or _digest(body) != ev["event_hash"]:
                return False
            prev = ev["event_hash"]
        return prev == self._head

    @property
    def head(self) -> str:
        return self._head

    def archive(self, sink) -> dict:
        """Bounded retention (C067/C088 soak finding): hand finished runs' transcripts and all current events to
        ``sink(kind, record)`` (an append-only store), then drop them from memory.  The chain continues from the
        archived head, so ``verify_events`` still proves continuity of what remains.  If the sink raises, nothing
        is dropped."""
        with self._lock:
            finished = [r for r in self.runs.values() if r.lifecycle.terminal]
            events = list(self.events)
            for r in finished:
                sink("transcript", r.agent.export_transcript())
            for ev in events:
                sink("run_event", ev)
            for r in finished:
                del self.runs[r.run_id]
            if events:
                self._base_seq = events[-1]["seq"] + 1
                self._base_head = events[-1]["event_hash"]
                del self.events[:len(events)]
            self.decisions.clear()
            hashes = {e["event_hash"] for e in events}
            self.telemetry.drop_exported("audit", lambda r: r.get("event_hash") in hashes)
            return {"archived_runs": len(finished), "archived_events": len(events), "base_seq": self._base_seq,
                    "base_head": self._base_head}

    def _get(self, run_id: str) -> Run:
        run = self.runs.get(run_id)
        if run is None:
            raise AgentError("AGT-LCY-001", "unknown run", details={"run_id": run_id})
        return run

    def _retry_policy(self) -> RetryPolicy:
        e = self.eff
        return RetryPolicy(e.get("retry.max_attempts"), e.get("retry.base_delay"), e.get("retry.max_delay"))

    # ------------------------------------------------------------------ run lifecycle
    def start_run(self, run_id: str, *, principal: str, allow: frozenset[str], ctx: CallContext,
                  priority: str = "normal") -> dict:
        if self.contained:
            raise AgentError("AGT-POL-001", "containment active: new runs disabled", correlation_id=ctx.correlation_id)
        with self._lock:
            if run_id in self.runs:
                raise AgentError("AGT-LCY-002", details={"run_id": run_id})
        self.trust.gate("admission")
        self._check_audit_backpressure(ctx)
        lc = Lifecycle("run", run_id, policy_version=PRECEDENCE_POLICY["version"])
        self.admission.acquire(ctx, priority)
        try:
            fence = call_with_retry("durable.acquire", lambda c: self.durable.acquire(c, run_id, self.executor_id,
                                    self.eff.get("residency.zone")), ctx, policy=self._retry_policy(), sleep=self._sleep).value
            e = self.eff
            agent = Agent(f"{run_id}", allow, max_steps=e.get("budgets.max_steps"), max_cost=e.get("budgets.max_cost"),
                          max_transcript_events=e.get("budgets.max_transcript_events"))
        except BaseException:
            self.admission.release()
            raise
        lc.transition(RunState.ADMITTED, actor=principal, reason="admitted", request_id=f"{run_id}:admit")
        lc.transition(RunState.RUNNING, actor=self.executor_id, reason="started", request_id=f"{run_id}:start")
        run = Run(run_id, ctx.tenant, principal, agent, lc, fence, ctx, admitted=True)
        with self._lock:
            self.runs[run_id] = run
        self.watchdog.heartbeat(run_id)
        self.telemetry.inc("runs_started", tenant=ctx.tenant)
        self._event("run_started", ctx, run_id=run_id, tenant=ctx.tenant, principal=principal, fence=fence,
                    allow=sorted(allow), code=None,
                    peers={k: {"version": v["peer_version"], "support": v["support_state"],
                               "capabilities": v["agreed_capabilities"]} for k, v in self.peers.items()})
        return {"run_id": run_id, "state": lc.state.value, "fence": fence}

    def _end(self, run: Run, state: RunState, reason: str, code: str | None) -> dict:
        if run.lifecycle.state is not state:
            if state is RunState.CANCELLED and run.lifecycle.state is not RunState.CANCELLING:
                run.lifecycle.transition(RunState.CANCELLING, actor=run.principal, reason=reason,
                                         request_id=f"{run.run_id}:cancelling")
            run.lifecycle.transition(state, actor=self.executor_id, reason=reason, request_id=f"{run.run_id}:{state.value}")
        if run.admitted:
            run.admitted = False
            self.admission.release()
        self.watchdog.done(run.run_id)
        self._event("run_ended", run.ctx, run_id=run.run_id, state=state.value, code=code, reason=reason,
                    kernel_head=run.agent.transcript_head, cost_used=run.agent.cost_used, attempts=run.agent.attempts)
        return {"run_id": run.run_id, "state": state.value, "code": code}

    def finish_run(self, run_id: str) -> dict:
        run = self._get(run_id)
        return self._end(run, RunState.SUCCEEDED, "completed", None)

    def cancel_run(self, run_id: str, reason: str = "caller cancelled") -> dict:
        run = self._get(run_id)
        run.ctx.cancel.cancel(reason)
        return self._end(run, RunState.CANCELLED, reason, "AGT-CAN-001")

    # ------------------------------------------------------------------ approval
    def approve(self, run_id: str, tool: str, arg: Any, approver: str, ctx: CallContext) -> dict:
        run = self._get(run_id)
        try:
            self.trust.gate("approval")
            self.trust.network_op("approval.grant")
            run.agent.approve(tool, arg, approver)
        except BaseException as exc:
            err = translate(exc, ctx.correlation_id)
            self.telemetry.inc("approval_refusals", code=err.code)
            self._event("approval_refused", ctx, run_id=run_id, tool=str(tool)[:64], approver=str(approver)[:64],
                        code=err.code)
            raise err
        self.telemetry.inc("approvals")
        self._event("approval_recorded", ctx, run_id=run_id, tool=tool, approver=approver, code=None,
                    kernel_head=run.agent.transcript_head)
        return {"run_id": run_id, "approved": True}

    # ------------------------------------------------------------------ sandbox selection (C019 + C045 + C056)
    def _select_tier(self, tool: str, *, generated: bool, ctx: CallContext) -> dict:
        spec = TOOLS[tool]
        e = self.eff
        required = "heavy" if (spec.risk == "high" or generated or self.forced_heavy) else e.get("sandbox.low_risk_tier")
        fast_ok = self.fast is not None and "fast_sandbox" not in self.trust.blocked_capabilities()
        candidates = [{"tier": "fast"}, {"tier": "heavy"}] if fast_ok else [{"tier": "heavy"}]
        constraints = [
            Constraint("tier >= required by risk class", "security",
                       lambda c: TIER_STRENGTH[c["tier"]] >= TIER_STRENGTH[required]),
            Constraint("prefer cheaper tier", "cost", lambda c: True),
        ]
        d = resolve_constraints(candidates, constraints, scope=f"tenant:{ctx.tenant}")
        rec = d.to_dict()
        rec.update({"decision_point": "sandbox_selection", "tool": tool, "risk": spec.risk, "required_tier": required,
                    "fast_available": fast_ok, "generated_code": generated, "forced_heavy": self.forced_heavy,
                    "correlation_id": ctx.correlation_id})
        self.decisions.append(rec)
        return rec

    # ------------------------------------------------------------------ invoke
    def invoke(self, run_id: str, tool: str, arg: Any, ctx: CallContext, *, generated: bool = False) -> dict:
        run = self._get(run_id)
        t0 = time.perf_counter()
        inv_id = f"{run_id}:{run.agent.attempts}:{secrets.token_hex(3)}"
        side = bool(isinstance(tool, str) and tool in TOOLS and TOOLS[tool].side_effect)
        inv = Lifecycle("invocation", inv_id, policy_version=PRECEDENCE_POLICY["version"], side_effect=side)
        run.invocations[inv_id] = inv
        base = {"run_id": run_id, "invocation": inv_id, "tool": tool if isinstance(tool, str) else "<invalid>"}
        self.watchdog.heartbeat(run_id)
        try:
            ctx.check()
            if run.lifecycle.terminal:
                raise AgentError("AGT-LCY-001", "run is terminal", details={"state": run.lifecycle.state.value})
            self.trust.gate("tool_execution")
            self._check_audit_backpressure(ctx)
            if side:
                self.trust.network_op("tool.side_effect")
            # ---- INV-59 authorization (retryable, idempotent)
            az = call_with_retry("authorization.check",
                                 lambda c: self.authz.authorize(c, run.principal, str(tool), run.tenant),
                                 ctx, policy=self._retry_policy(), sleep=self._sleep).value
            if not isinstance(az, Mapping) or az.get("decision") not in ("allow", "deny"):
                raise AgentError("AGT-DEP-002", "malformed authorization response")
            self.decisions.append({"decision_point": "authorization", "run_id": run_id, "tool": base["tool"],
                                   "decision": az["decision"], "policy_version": az.get("policy_version", "unknown"),
                                   "correlation_id": ctx.correlation_id})
            if az["decision"] != "allow":
                inv.transition(InvocationState.DENIED, actor="INV-59", reason="authorization denied", request_id=inv_id + ":deny")
                raise AgentError("AGT-AUTHZ-002", correlation_id=ctx.correlation_id)
            inv.transition(InvocationState.AUTHORIZED, actor="INV-59", reason="authorized", request_id=inv_id + ":authz")
            # ---- kernel policy (allowlist, budgets, one-use approval)
            k = run.agent.step(tool, arg)
            code = code_for_reason(k["reason"])
            if k["outcome"] == "pending":
                inv.transition(InvocationState.PENDING_APPROVAL, actor="kernel", reason=k["reason"], request_id=inv_id + ":pend")
                if run.lifecycle.state is RunState.RUNNING:
                    run.lifecycle.transition(RunState.AWAITING_APPROVAL, actor="kernel", reason="approval needed",
                                             request_id=f"{run_id}:await:{k['step']}")
                return self._result(run, ctx, base, "pending", code, k, t0)
            if k["outcome"] == "refused":
                inv.transition(InvocationState.DENIED, actor="kernel", reason=k["reason"], request_id=inv_id + ":kdeny")
                return self._result(run, ctx, base, "refused", code, k, t0)
            if run.lifecycle.state is RunState.AWAITING_APPROVAL:
                run.lifecycle.transition(RunState.RUNNING, actor="kernel", reason="approval consumed",
                                         request_id=f"{run_id}:resume:{k['step']}")
            if side:  # approval was consumed by the kernel: record the gate on the invocation machine
                inv.transition(InvocationState.PENDING_APPROVAL, actor="kernel", reason="approval present", request_id=inv_id + ":p")
                inv.transition(InvocationState.AUTHORIZED, actor="kernel", reason="approval consumed", request_id=inv_id + ":a2")
            # ---- sandbox selection + dispatch
            sel = self._select_tier(tool, generated=generated, ctx=ctx)
            tier = sel["chosen"]["tier"]
            sandbox = self.heavy if tier == "heavy" else self.fast
            arg_ref = hashlib.sha256(_canonical_bytes(arg)).hexdigest()
            ikey = idempotency_key(run_id, k["step"], tool, arg_ref)
            prior = self.durable.committed(ikey)
            if prior is not None:
                inv.transition(InvocationState.DISPATCHED, actor=self.executor_id, reason="already committed", request_id=inv_id + ":d")
                inv.transition(InvocationState.COMPLETED, actor=self.executor_id, reason="replay suppressed", request_id=inv_id + ":c")
                return self._result(run, ctx, base, "ran", None, k, t0, tier=tier, value=prior.get("result"), deduplicated=True)
            self.durable.check_fence(run_id, run.fence)   # fenced BEFORE any side effect (split-brain guard)
            call_with_retry("sandbox.launch", lambda c: sandbox.launch(c), ctx, policy=self._retry_policy(), sleep=self._sleep)
            inv.transition(InvocationState.DISPATCHED, actor=self.executor_id, reason=f"dispatched to {tier}", request_id=inv_id + ":d")
            op = "tool.execute.side_effect" if side else "tool.execute.readonly"
            try:
                out = call_with_retry(op, lambda c: sandbox.execute(c, tool, arg, ikey), ctx,
                                      policy=self._retry_policy(), idempotency_key=ikey, sleep=self._sleep).value
            except AgentError as exc:
                if exc.code == "AGT-SBX-001" and (exc.details.get("effect") == "indeterminate" or exc.cause and
                                                  exc.cause.details.get("effect") == "indeterminate"):
                    inv.transition(InvocationState.INDETERMINATE, actor=self.executor_id, reason="lost after dispatch",
                                   request_id=inv_id + ":x")
                else:
                    inv.transition(InvocationState.TIMED_OUT if exc.code == "AGT-TMO-001" else InvocationState.FAILED,
                                   actor=self.executor_id, reason=exc.code, request_id=inv_id + ":f")
                raise
            if not isinstance(out, Mapping) or "result" not in out:
                inv.transition(InvocationState.FAILED, actor=self.executor_id, reason="malformed sandbox response",
                               request_id=inv_id + ":m")
                raise AgentError("AGT-DEP-002", "malformed sandbox response")
            self.durable.record_effect(ctx, run_id, run.fence, ikey, {"result": out["result"], "tier": tier})
            self.durable.checkpoint(ctx, run_id, run.fence, k["step"],
                                    {"attempts": run.agent.attempts, "cost_used": run.agent.cost_used,
                                     "kernel_head": run.agent.transcript_head})
            inv.transition(InvocationState.COMPLETED, actor=self.executor_id, reason="completed", request_id=inv_id + ":c")
            return self._result(run, ctx, base, "ran", None, k, t0, tier=tier, value=out["result"],
                                deduplicated=bool(out.get("deduplicated")), ikey=ikey)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            err = translate(exc, ctx.correlation_id)
            self.telemetry.inc("refusals" if err.spec.category in ("authorization", "policy", "approval", "capacity")
                               else "failures", code=err.code, tenant=run.tenant)
            self._event("invocation_failed", ctx, **base, code=err.code, category=err.spec.category,
                        retryable=err.retryable, invocation_state=inv.state.value,
                        details_digest=_digest(err.to_dict()["details"]))
            self.telemetry.observe("invoke_latency_s", time.perf_counter() - t0, outcome="error")
            raise err

    def _result(self, run: Run, ctx: CallContext, base: dict, outcome: str, code: str | None, k: dict, t0: float,
                **extra) -> dict:
        elapsed = time.perf_counter() - t0
        self.telemetry.inc("steps", tenant=run.tenant, outcome=outcome)
        if code:
            self.telemetry.inc("refusals" if outcome == "refused" else "pending", code=code, tenant=run.tenant)
        if code == "AGT-CAP-001":
            self.telemetry.inc("budget_stops", tenant=run.tenant)
        self.telemetry.observe("invoke_latency_s", elapsed, outcome=outcome)
        ev_extra = {kk: v for kk, v in extra.items() if kk in ("tier", "deduplicated", "ikey")}
        self._event("invocation", ctx, **base, outcome=outcome, code=code, kernel_step=k.get("step"),
                    kernel_reason=k.get("reason"), kernel_head=run.agent.transcript_head,
                    arg_shape=_arg_shape(k.get("arg")), **ev_extra)
        res = {**base, "outcome": outcome, "code": code, "reason": k.get("reason"),
               "correlation_id": ctx.correlation_id, "trace_id": ctx.trace.trace_id}
        res.update({kk: v for kk, v in extra.items() if kk != "ikey"})
        return res

    # ------------------------------------------------------------------ failover / resume (C055)
    def adopt(self, run_id: str, *, principal: str, allow: frozenset[str], ctx: CallContext, source_executor: str) -> dict:
        """Take over a run from another executor: new fence, restore counters from the durable checkpoint,
        approvals are NOT carried over (re-approval required), committed effects are never replayed."""
        cp = self.durable.load(run_id)
        fence = self.durable.acquire(ctx, run_id, self.executor_id, self.eff.get("residency.zone"))
        e = self.eff
        agent = Agent(run_id, allow, max_steps=e.get("budgets.max_steps"), max_cost=e.get("budgets.max_cost"),
                      max_transcript_events=e.get("budgets.max_transcript_events"))
        if cp:
            agent._attempts, agent._cost_used = int(cp.state["attempts"]), int(cp.state["cost_used"])
        lc = Lifecycle("run", run_id, policy_version=PRECEDENCE_POLICY["version"])
        lc.transition(RunState.ADMITTED, actor=principal, reason="adopted", request_id=f"{run_id}:admit")
        lc.transition(RunState.RUNNING, actor=self.executor_id, reason="resumed after failover", request_id=f"{run_id}:start")
        rctx = CallContext(ctx.deadline, ctx.cancel, ctx.trace.linked_root(), ctx.correlation_id, ctx.tenant, ctx.baggage)
        self.admission.acquire(rctx)
        run = Run(run_id, ctx.tenant, principal, agent, lc, fence, rctx, admitted=True)
        with self._lock:
            self.runs[run_id] = run
        self._event("failover_adopted", rctx, run_id=run_id, source_executor=source_executor, fence=fence,
                    checkpoint_seq=cp.seq if cp else None, restored_attempts=agent.attempts,
                    restored_cost=agent.cost_used, links=list(rctx.trace.links), code=None)
        return {"run_id": run_id, "fence": fence, "restored_attempts": agent.attempts}

    def plan_failover(self, candidates: list[Mapping[str, Any]], required_tier: str = "heavy") -> Mapping[str, Any]:
        t = select_failover_target(candidates, zone=self.eff.get("residency.zone"),
                                   allowed_zones=list(self.eff.get("residency.allowed_failover_zones")),
                                   trust_domain=self.trust_domain, required_tier=required_tier)
        self.decisions.append({"decision_point": "failover_target", "chosen": dict(t),
                               "zone": self.eff.get("residency.zone")})
        self._event("failover_planned", None, target=t.get("id"), code=None)
        return t

    # ------------------------------------------------------------------ operator containment (C097)
    def contain(self, action: str, *, operator: str, reason: str) -> dict:
        actions = {"disable_new_runs", "force_heavy_sandbox", "release_containment"}
        if action not in actions:
            raise AgentError("AGT-VAL-001", "unknown containment action")
        if not operator or not reason:
            raise AgentError("AGT-VAL-001", "containment requires operator and reason")
        if action == "disable_new_runs":
            self.contained = True
        elif action == "force_heavy_sandbox":
            self.forced_heavy = True
        else:
            self.contained = self.forced_heavy = False
        self._event("containment", None, action=action, operator=operator, reason=reason, code=None)
        return {"contained": self.contained, "forced_heavy": self.forced_heavy}

    # ------------------------------------------------------------------ status (C071)
    def status(self, audience: str = "operator") -> dict:
        adm = self.admission.stats()
        findings = self.watchdog.evaluate(adm["oldest_wait_s"])
        sealed = sum(1 for r in self.runs.values() if r.agent._sealed)
        if self.telemetry.buffer_full("audit"):
            findings = findings + [{"code": "HLT-AUDIT-STALL", "action": "reject_new_work",
                                    "overflowed": self.audit_export_overflow}]
        return build_status(version=COMPONENT_VERSION, build_id=self.release.get("artifact_digest", "unknown"),
                            config=self.eff, trust_snapshot=self.trust.snapshot(), admission=adm, findings=findings,
                            contained=self.contained, sealed_agents=sealed, telemetry_ids=self.telemetry.policy_ids(),
                            lineage=self.lineage().as_labels(), audience=audience,
                            trust_probe=self.trust.would_pass, peers=self.peers)

    def set_offline(self, offline: bool):
        return self.trust.set_connectivity(Connectivity.OFFLINE if offline else Connectivity.ONLINE)
