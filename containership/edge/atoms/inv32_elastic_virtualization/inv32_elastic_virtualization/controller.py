"""ElasticController: the production mutation path (WS 1, 4-10, 12, 18).

Pipeline for every external request (each step is a trace span and fails closed)::

    decode+schema -> authenticate -> authorize(host,tenant,action) -> idempotency/unknown-outcome gate
    -> readiness/mode/quarantine -> admission (per-host/tenant/priority) -> per-guest serialization
    -> read live state (identity, tenant ownership, lifecycle, capability, expected-version CAS)
    -> policy (floor/ceiling/alignment/non-balloonable/boot-vCPU/reserve on hypervisor-confirmed capacity/quota)
    -> fence (lease epoch) -> journal PREPARED -> journal PROVIDER_REQUESTED -> provider call (bounded retry,
       circuit breaker, idempotency key, fencing token, expected version, incarnation, deadline)
    -> journal PROVIDER_CONFIRMED -> re-read + verify invariants -> re-fence -> STATE_COMMITTED
    -> audit append (durable, hash-chained) -> AUDIT_COMMITTED -> respond

A provider timeout is an UNKNOWN outcome: journalled, audited, the guest is blocked for mutation, and
only ``recover()``/``reconcile()`` against live hypervisor state can clear it.  Nothing is replayed blindly.
"""
from __future__ import annotations

from contextlib import ExitStack
import json
import math
import threading
import time
from typing import Any, Mapping
from uuid import uuid4

from . import errors as E
from . import __version__
from .adapters.base import MUTABLE_STATES, HypervisorAdapter, LiveGuest, ProviderStatus
from .authz import Authenticator, Policy, authorize
from .config import ConfigManager
from .fencing import GuestLocks, Ownership
from .health import HealthReport, QuarantineManager, Watchdog
from .model import (AUDIT_EVENT_SCHEMA, HOST_RESOURCES_SCHEMA, RESOURCE_ADJUSTMENT_SCHEMA, AuditIntegrityError,
                    FloorBreach, InvalidAdjustmentRecord, ReplayConflict, ReserveBreach, StaleAdjustment,
                    StateIntegrityError, UnknownGuest)
from .quota import QuotaPolicy
from .resilience import AdmissionController, CircuitBreaker, Priority, RetryBudget, RetryPolicy
from .store import TERMINAL_PHASES, DurableStore
from .telemetry import ExplainStore, MetricsRegistry, StructuredLogger, TraceContext, Tracer
from .validation import decode_request, validate

RESULT_SCHEMA = "PK_RESOURCE_ADJUSTMENT_RESULT/2"
_MODEL_ERRORS = (FloorBreach, ReserveBreach, StaleAdjustment, ReplayConflict, UnknownGuest, InvalidAdjustmentRecord,
                 StateIntegrityError, AuditIntegrityError)
ACTION_FOR_OP = {"memory_adjust": "memory.adjust", "vcpu_adjust": "vcpu.adjust",
                 "memory_revert": "adjustment.revert", "vcpu_revert": "adjustment.revert"}
PRIORITY = {"safety": Priority.SAFETY, "normal": Priority.NORMAL, "low": Priority.LOW}


class ElasticController:
    def __init__(self, *, host: str, controller_id: str, adapter: HypervisorAdapter, store: DurableStore,
                 ownership: Ownership, authenticator: Authenticator, policy: Policy, config: ConfigManager,
                 quotas: QuotaPolicy | None = None, clock=time.time, mono=time.monotonic, sleep=time.sleep,
                 rng=None) -> None:
        self.host, self.controller_id = host, controller_id
        self.adapter, self.store, self.ownership = adapter, store, ownership
        self.authn, self.policy, self.config = authenticator, policy, config
        self.quotas = quotas or QuotaPolicy()
        self._clock, self._mono, self._sleep = clock, mono, sleep
        cfg = config.active
        self.metrics = MetricsRegistry()
        self.tracer = Tracer()
        self.log = StructuredLogger("inv32")
        self.explainer = ExplainStore()
        self.watchdog = Watchdog(clock=mono, on_incident=self._incident)
        self.quarantine = QuarantineManager(store, audit=self._audit_control, clock=clock)
        self.admission = AdmissionController(max_host=cfg["max_inflight_per_host"], max_tenant=cfg["max_inflight_per_tenant"],
                                             safety_slots=cfg["safety_reserved_slots"],
                                             tenant_rate_per_s=cfg["tenant_rate_per_s"], tenant_burst=cfg["tenant_burst"],
                                             clock=mono)
        self.provider_circuit = CircuitBreaker("provider", failure_threshold=cfg["circuit_failure_threshold"],
                                               reset_s=cfg["circuit_reset_s"], clock=mono, rng=rng,
                                               on_change=self._circuit_changed)
        self._retry_budget = RetryBudget(ratio=cfg["retry_budget_ratio"], clock=mono)
        self._rng = rng
        self.locks = GuestLocks()
        self._cancelled: set[str] = set()
        self._draining = False
        self._caps = adapter.capabilities()
        config.add_validator(self.config_state_validator)
        self._incidents: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        # Growth reservations: op_id -> (tenant, delta_mib, delta_vcpus).  Concurrent grows on *different* guests
        # are admitted against capacity net of in-flight reservations, so two individually-safe grows can never
        # jointly cross the host reserve or a tenant cap (check-then-act race closed).
        self._reservations: dict[str, tuple[str, int, int]] = {}
        self.full_verify_every = 1024
        self._mutations_since_full_verify = 0

    # ================================================================ helpers
    def _audit_control(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.store.append_audit({"schema": RESOURCE_ADJUSTMENT_SCHEMA, "host": self.host,
                                        "controller": self.controller_id, "epoch": self.ownership.epoch,
                                        "config_digest": self.config.active.digest, **payload})

    def _incident(self, signal: dict[str, Any]) -> None:
        self._incidents.append(signal)
        self.log.log("ERROR", "incident signal", host=self.host, operation_id=signal.get("operation_id"),
                     outcome="unknown_outcome" if signal.get("signal") == "unknown_outcome" else "stall",
                     **{k: v for k, v in signal.items() if k != "operation_id"})

    def _circuit_changed(self, name: str, old: str, new: str) -> None:
        if new == "open":
            self.metrics.inc("inv32_circuit_open_total", dependency=name)
        self.log.log("WARNING", f"circuit {name} {old}->{new}", host=self.host)

    def registration(self, guest: str) -> dict[str, Any] | None:
        return self.store.guest_state(guest)

    def register_guest(self, guest: str, *, tenant: str, floor_mib: int, ceiling_mib: int, vcpu_max: int) -> None:
        """Declare policy bounds for a guest the hypervisor already runs (called by INV-33 on placement)."""
        live = self.adapter.get_guest(guest)
        if live.tenant != tenant:
            raise E.IdentityMismatch("tenant does not own guest at provider")
        if not 0 <= floor_mib <= live.memory_mib <= ceiling_mib or not 1 <= live.vcpus <= vcpu_max:
            raise E.ValidationFailed("declared bounds do not contain live state")
        self.store.put_guest_state(guest, tenant=tenant, floor_mib=floor_mib, ceiling_mib=ceiling_mib,
                                   vcpu_max=vcpu_max, incarnation=live.incarnation, memory_mib=live.memory_mib,
                                   vcpus=live.vcpus, epoch=self.ownership.epoch)
        self._audit_control({"kind": "guest_add", "operation_id": uuid4().hex, "guest": guest, "tenant": tenant,
                             "applied_mib": live.memory_mib, "applied_vcpus": live.vcpus,
                             "reason": "guest registered with declared bounds"})

    def config_state_validator(self, values: Mapping[str, Any]) -> None:
        """ConfigManager validator: a new config may not make live state illegal or exceed provider capability."""
        cap = self.adapter.host_capacity()
        reserve = max(values["host_reserve_min_mib"], math.ceil(cap.usable_mib * values["host_reserve_fraction"]))
        allocated = sum(g.memory_mib for g in self.adapter.list_guests())
        if allocated > cap.usable_mib - reserve:
            raise E.ConfigInvalid("new reserve would make current allocation illegal; migrate (reclaim) first",
                                  allocated_mib=allocated, allocatable_mib=cap.usable_mib - reserve)
        caps = self.adapter.capabilities()
        if values["feature_memory_hot_unplug"] and not caps.memory_hot_unplug:
            raise E.ConfigInvalid("feature_memory_hot_unplug enabled but provider lacks the capability")
        if values["feature_free_page_reporting"] and not caps.free_page_reporting:
            raise E.ConfigInvalid("feature_free_page_reporting enabled but provider lacks the capability")

    def reserve_mib(self, usable_mib: int) -> int:
        cfg = self.config.active
        return max(cfg["host_reserve_min_mib"], math.ceil(usable_mib * cfg["host_reserve_fraction"]))

    def _usage(self, guests: list[LiveGuest]) -> dict[str, tuple[int, int]]:
        u: dict[str, tuple[int, int]] = {}
        for g in guests:
            m, c = u.get(g.tenant, (0, 0))
            u[g.tenant] = (m + g.memory_mib, c + g.vcpus)
        return u

    def _check_caps(self) -> None:
        caps = self.adapter.capabilities()
        if caps.generation != self._caps.generation or caps.provider_version != self._caps.provider_version:
            self._audit_control({"kind": "reconciled", "operation_id": uuid4().hex,
                                 "reason": "provider capabilities changed; cache invalidated",
                                 "caps_generation": caps.generation, "provider_version": caps.provider_version})
            self._caps = caps

    # ================================================================ public API
    def handle(self, raw: bytes | str | Mapping[str, Any], token: str | None, *,
               traceparent: str | None = None) -> dict[str, Any]:
        """Process one external adjustment request; always returns a PK_RESOURCE_ADJUSTMENT_RESULT/2."""
        ctx = TraceContext.parse(traceparent)
        t0 = self._mono()
        op_id, op_kind = None, "invalid"
        try:
            with self.tracer.span("decode", ctx):
                req = decode_request(json.dumps(dict(raw)) if isinstance(raw, Mapping) else raw)
            op_id, op_kind = req["operation_id"], req["op"]
            result = self._handle(req, token, ctx)
        except E.ControlError as exc:
            result = self._fail(op_id, op_kind, exc, ctx)
        except _MODEL_ERRORS as exc:
            result = self._fail(op_id, op_kind, exc, ctx)
        except Exception as exc:  # noqa: BLE001 - never leak internals; envelope says internal_error
            self.log.log("ERROR", "internal error", host=self.host, operation_id=op_id, trace_id=ctx.trace_id,
                         exc_type=type(exc).__name__)
            result = self._fail(op_id, op_kind, exc, ctx)
        self.metrics.observe("inv32_end_to_end_latency_seconds", self._mono() - t0, operation=op_kind[:32])
        self.metrics.inc("inv32_requests_total", operation=op_kind[:32], outcome=result["outcome"])
        validate("result", result)  # every response validated before publication
        return result

    def _fail(self, op_id: str | None, op_kind: str, exc: BaseException, ctx: TraceContext) -> dict[str, Any]:
        env = E.error_envelope(exc, trace_id=ctx.trace_id)
        self.metrics.inc("inv32_refusals_total", reason=env["code"])
        self.log.log("NOTICE" if env["category"] in ("validation", "policy", "overload") else "WARNING",
                     "request rejected", host=self.host, operation_id=op_id, trace_id=ctx.trace_id,
                     outcome=env["outcome"], code=env["code"], epoch=self.ownership.epoch,
                     config_digest=self.config.active.digest)
        return {"schema": RESULT_SCHEMA, "operation_id": (op_id or "")[:128], "outcome": env["outcome"],
                "replayed": False, "error": env, "trace_id": ctx.trace_id}

    def _handle(self, req: dict[str, Any], token: str | None, ctx: TraceContext) -> dict[str, Any]:
        op_id, op = req["operation_id"], req["op"]
        action = ACTION_FOR_OP[op]
        with self.tracer.span("authorize", ctx) as sp:
            principal = self.authn.authenticate(token)
            if req["host"] != self.host:
                # Identical failure to "not authorized": wrong-host requests leak nothing.
                raise E.AuthorizationDenied("not authorized", reason="host_out_of_scope")
            try:
                decision = authorize(self.policy, principal, action, host=self.host, tenant=req["tenant"])
            except E.AuthorizationDenied as exc:
                self._audit_control({"kind": "rejected", "operation_id": op_id, "guest": req["guest"],
                                     "tenant": req["tenant"], "code": exc.code, "principal": principal.id,
                                     "action": action, "authz_decision_id": exc.details.get("decision_id"),
                                     "authz_policy_version": self.policy.version})
                raise
            sp.set(outcome="allow")

        fingerprint = {k: req.get(k) for k in ("op", "guest", "tenant", "target_mib", "target_vcpus",
                                                "record_event_hash", "honoured")}
        prior = self.store.ops.get(op_id)
        if prior is not None and (prior.get("phase") == "failed" or prior.get("verdict") in ("not_applied",)):
            # Definitively not applied (no provider side effect): safe to execute under the same ID.
            if prior.get("fingerprint") not in (None, fingerprint):
                raise _replay_conflict(op_id)
            prior = None
        if prior is not None:
            if prior.get("fingerprint") != fingerprint:
                raise _replay_conflict(op_id)
            if prior.get("phase") in TERMINAL_PHASES and "result" in prior:
                res = dict(prior["result"])
                res["replayed"] = True
                res["trace_id"] = ctx.trace_id
                return res
            raise E.UnknownOutcomeBlocked("operation outcome unknown; reconcile before retrying",
                                          operation_id=op_id, phase=prior.get("phase"))

        priority = PRIORITY[req.get("priority", "safety" if op.endswith("revert") else "normal")]
        if priority is Priority.SAFETY and not op.endswith("revert"):
            priority = Priority.NORMAL  # callers cannot self-promote ordinary adjustments into safety capacity
        self._require_ready_for_mutation()
        self.quarantine.check(host=self.host, tenant=req["tenant"], guest=req["guest"])
        if self._draining:
            raise E.ShuttingDown("controller draining")

        cfg = self.config.active
        deadline = self._mono() + min(req.get("deadline_ms", cfg["operation_timeout_s"] * 1000) / 1000.0,
                                      cfg["operation_timeout_s"])
        with ExitStack() as stack:
            qstart = self._mono()
            stack.enter_context(self.admission.admit(req["tenant"], priority))
            self.metrics.observe("inv32_queue_wait_seconds", self._mono() - qstart, priority=priority.name.lower())
            stack.enter_context(self.locks.hold(req["guest"]))
            self.metrics.set("inv32_inflight_operations", self.admission.inflight())
            try:
                return self._mutate(req, op, principal, decision, fingerprint, deadline, ctx, priority)
            finally:
                with self._lock:
                    self._reservations.pop(req["operation_id"], None)

    # ---------------------------------------------------------------- mutation core
    def _mutate(self, req, op, principal, decision, fingerprint, deadline, ctx, priority) -> dict[str, Any]:
        op_id, guest_id = req["operation_id"], req["guest"]
        # Checked under the per-guest lock, so only genuinely unreconciled (not merely in-flight) ops block.
        for other in self.store.incomplete_ops().values():
            if other.get("guest") == guest_id and other.get("phase") in ("unknown", "provider_requested",
                                                                          "provider_confirmed", "state_committed"):
                raise E.UnknownOutcomeBlocked("guest has an unreconciled operation", guest=guest_id)
        t_decide = self._mono()
        with self.tracer.span("state_read", ctx):
            self._check_caps()
            try:
                live = self.provider_call(lambda: self.adapter.get_guest(guest_id), deadline)
            except E.IdentityMismatch:
                raise E.AuthorizationDenied("not authorized") from None  # no existence oracle
            reg = self.registration(guest_id)
            if live.tenant != req["tenant"] or reg is None or reg.get("tenant") != req["tenant"]:
                raise E.AuthorizationDenied("not authorized")
            if reg.get("incarnation") != live.incarnation:
                raise E.IdentityMismatch("guest identity changed since registration (identifier reuse)")
            if "expected_version" in req and req["expected_version"] != live.state_version:
                raise E.StaleExpectedState("guest changed since caller's read", expected=req["expected_version"],
                                           actual=live.state_version)
            cap = self.adapter.host_capacity()
            if not cap.trusted or cap.usable_mib <= 0:
                raise E.CapacityUntrusted("host capacity cannot be trusted; failing closed")
            all_guests = self.adapter.list_guests()

        with self.tracer.span("decision", ctx) as dsp:
            plan = self._plan(req, op, live, reg, cap, all_guests)
            dsp.set(operation=plan["primitive"])
        self.metrics.observe("inv32_decision_latency_seconds", self._mono() - t_decide, operation=op)

        explain = {"operation_id": op_id, "request": {k: req.get(k) for k in fingerprint},
                   "live_state_version": live.state_version, "live_memory_mib": live.memory_mib,
                   "live_vcpus": live.vcpus, "floor_mib": reg["floor_mib"], "ceiling_mib": reg["ceiling_mib"],
                   "vcpu_max": reg["vcpu_max"], "host_usable_mib": cap.usable_mib, "host_reserve_mib": plan["reserve_mib"],
                   "host_free_mib": plan["free_mib"], "policy_version": decision.policy_version,
                   "authz_decision_id": decision.decision_id, "capabilities_generation": self._caps.generation,
                   "provider_version": self._caps.provider_version, "epoch": self.ownership.epoch,
                   "config_digest": self.config.active.digest, "config_revision": self.config.active.meta.revision,
                   "release": __version__, "plan": plan, "controlling_rule": plan["rule"]}

        if plan["noop"]:
            ev = self._commit(req, op, principal, decision, live, plan, live, None, "success", ctx, fingerprint, noop=True)
            explain["outcome"] = "success"
            self.explainer.record(op_id, explain)
            return ev

        with self.tracer.span("fence", ctx):
            fence = self.ownership.validate()
        if op_id in self._cancelled:
            raise E.Cancelled("cancelled before provider mutation")

        self.store.op_phase(op_id, "prepared", fingerprint=fingerprint, guest=guest_id, created=self._clock(),
                            epoch=fence, controller=self.controller_id, expected_version=live.state_version,
                            incarnation=live.incarnation, from_value=plan["from"], target=plan["target"],
                            primitive=plan["primitive"], principal=principal.id)
        stall = {"memory_grow": "stall_memory_grow_s", "memory_reclaim": "stall_memory_reclaim_s"}.get(
            plan["primitive"], "stall_vcpu_s")
        self.watchdog.start(op_id, plan["primitive"], guest_id, deadline=deadline,
                            stall_after_s=self.config.active[stall])
        try:
            self.store.op_phase(op_id, "provider_requested")
            self.watchdog.progress(op_id, "provider_requested")
            t_prov = self._mono()
            with self.tracer.span("provider_mutation", ctx) as psp:
                setter = self.adapter.set_memory if plan["kind"] == "memory" else self.adapter.set_vcpus
                try:
                    result = self.provider_call(
                        lambda: setter(guest_id, plan["target"], expected_version=live.state_version,
                                       incarnation=live.incarnation, idempotency_key=op_id,
                                       fencing_token=fence, deadline=deadline),
                        deadline, idempotent=True)
                except E.ProviderTimeout as exc:
                    # Adapter contract: ProviderTimeout == request sent, outcome unknown.
                    # DeadlineExceeded/others == not applied (handled below as failed).
                    self.store.op_phase(op_id, "unknown", code=exc.code)
                    self._audit_control({"kind": "rejected", "operation_id": op_id, "guest": guest_id,
                                         "tenant": req["tenant"], "code": "unknown_outcome", "principal": principal.id,
                                         "reason": "provider did not confirm; guest blocked until reconciled"})
                    self._incident({"signal": "unknown_outcome", "operation_id": op_id})
                    raise E.UnknownOutcomeBlocked("provider outcome unknown; reconciliation required",
                                                  operation_id=op_id) from None
                except E.ControlError as exc:
                    self.store.op_phase(op_id, "failed", code=exc.code)
                    raise
                psp.set(outcome=result.status.value)
            self.metrics.observe("inv32_provider_latency_seconds", self._mono() - t_prov, operation=op)
            self.store.op_phase(op_id, "provider_confirmed", provider_request_id=result.request_id,
                                applied=result.applied, status=result.status.value)
            self.watchdog.progress(op_id, "provider_confirmed", result.request_id)

            with self.tracer.span("verification", ctx):
                after = self.adapter.get_guest(guest_id)
                observed = after.memory_mib if plan["kind"] == "memory" else after.vcpus
                if after.incarnation != live.incarnation or observed != result.applied:
                    self._quarantine_auto(guest_id, "post-mutation state disagrees with provider confirmation")
                    self.store.op_phase(op_id, "unknown", code="provider_invariant_violation")
                    raise E.ProviderInvariantViolation("provider confirmation does not match live state")
                self._verify_invariants(guest_id, after, reg, plan)
            outcome = "success"
            if result.status is ProviderStatus.REFUSED:
                outcome = "rejected"
                self.metrics.inc("inv32_refusals_total", reason="guest_refused")
            elif result.status is ProviderStatus.PARTIAL:
                outcome = "partial_success"
                if plan["kind"] == "vcpu":  # vCPU is all-or-nothing: compensate to the original count
                    comp = self.adapter.set_vcpus(guest_id, plan["from"], expected_version=result.state_version,
                                                  incarnation=live.incarnation, idempotency_key=op_id + ":comp",
                                                  fencing_token=fence, deadline=deadline)
                    after = self.adapter.get_guest(guest_id)
                    outcome = "rolled_back" if comp.applied == plan["from"] == after.vcpus else "unknown_outcome"
            with self.tracer.span("commit", ctx):
                self.ownership.validate()  # an old controller may not commit after takeover
                ev = self._commit(req, op, principal, decision, live, plan, after, result, outcome, ctx, fingerprint)
        finally:
            self.watchdog.finish(op_id)
        explain["outcome"] = ev["outcome"]
        explain["provider_request_id"] = result.request_id
        self.explainer.record(op_id, explain)
        return ev

    def _plan(self, req, op, live: LiveGuest, reg, cap, all_guests) -> dict[str, Any]:
        reserve = self.reserve_mib(cap.usable_mib)
        allocated = sum(g.memory_mib for g in all_guests)
        free = cap.usable_mib - reserve - allocated
        if free < 0:
            raise E.CapacityUntrusted("live allocations already cross the reserve; failing closed", free_mib=free)
        plan: dict[str, Any] = {"reserve_mib": reserve, "free_mib": free, "rule": "within_bounds", "noop": False}
        if op in ("memory_revert", "vcpu_revert"):
            ev = self._trusted_event(req["record_event_hash"], guest=req["guest"])
            kind = "memory" if op == "memory_revert" else "vcpu"
            if ev.get("kind") != kind:
                raise E.ValidationFailed("record kind does not match revert operation")
            if ev.get("epoch") != self.ownership.epoch:
                raise StaleAdjustment("rollback record belongs to another ownership epoch; reconcile first")
            current = live.memory_mib if kind == "memory" else live.vcpus
            applied = ev["applied_mib"] if kind == "memory" else ev["applied_vcpus"]
            if current != applied:
                raise StaleAdjustment("state changed after the recorded adjustment; refusing stale rollback",
                                      current=current, recorded=applied)
            target = ev["reversible_to"]
            plan["rule"] = "validated_rollback"
        elif op == "memory_adjust":
            kind, target = "memory", req["target_mib"]
        else:
            kind, target = "vcpu", req["target_vcpus"]
        plan["kind"] = kind
        if kind == "memory":
            cur = live.memory_mib
            if target < reg["floor_mib"]:
                raise FloorBreach("target below working-set floor", target_mib=target, floor_mib=reg["floor_mib"])
            if target > reg["ceiling_mib"]:
                target, plan["rule"] = reg["ceiling_mib"], "clamped_to_ceiling"
            blk = max(1, self._caps.memory_block_mib)
            aligned = (target // blk) * blk if target >= cur else -(-target // blk) * blk
            if aligned < reg["floor_mib"] or aligned > reg["ceiling_mib"]:
                aligned = target if target in (reg["floor_mib"], reg["ceiling_mib"]) else aligned
                if not reg["floor_mib"] <= aligned <= reg["ceiling_mib"]:
                    raise E.ValidationFailed("no block-aligned target inside guest bounds", block_mib=blk)
            if aligned != target:
                plan["rule"] = "aligned_to_block"
            target = aligned
            if target < live.non_balloonable_mib:
                raise FloorBreach("target below non-balloonable (pinned/DMA) memory",
                                  non_balloonable_mib=live.non_balloonable_mib)
            delta = target - cur
            primitive = "memory_grow" if delta > 0 else "memory_reclaim"
            if delta > free:
                raise ReserveBreach("growth would cross the host reserve", delta_mib=delta, free_mib=free)
            dv = 0
        else:
            cur = live.vcpus
            if not 1 <= target <= reg["vcpu_max"]:
                raise E.ValidationFailed("vCPU target outside declared bounds", vcpu_max=reg["vcpu_max"])
            if target < live.min_boot_vcpus:
                raise E.ValidationFailed("removal would detach a vCPU required by the guest", min=live.min_boot_vcpus)
            delta, dv = 0, target - cur
            primitive = "vcpu_add" if dv > 0 else "vcpu_remove"
        if live.lifecycle not in MUTABLE_STATES[primitive]:
            raise E.GuestStateIncompatible("guest lifecycle state forbids this mutation", state=live.lifecycle.value)
        if (delta or dv) and not self._caps.supports(primitive):
            raise E.CapabilityUnsupported("provider lacks capability", primitive=primitive)
        with self._lock:
            pending_mib = sum(max(0, d) for _, d, _ in self._reservations.values())
            if delta > 0 and delta > free - pending_mib:
                raise ReserveBreach("growth would cross the host reserve once in-flight growth lands",
                                    delta_mib=delta, free_mib=free - pending_mib)
            usage = self._usage(all_guests)
            for t, dm, dc in self._reservations.values():
                m, c = usage.get(t, (0, 0))
                usage[t] = (m + max(0, dm), c + max(0, dc))
            self.quotas.check_growth(tenant=req["tenant"], delta_mib=delta, delta_vcpus=dv,
                                     usage=usage, allocatable_mib=cap.usable_mib - reserve)
            if (delta > 0 or dv > 0) and not target == cur:
                self._reservations[req["operation_id"]] = (req["tenant"], delta, dv)
        plan.update({"from": cur, "target": target, "primitive": primitive, "noop": target == cur})
        return plan

    def _verify_invariants(self, guest_id: str, after: LiveGuest, reg, plan) -> None:
        cap = self.adapter.host_capacity()
        allocated = sum(g.memory_mib for g in self.adapter.list_guests())
        problems = []
        if not reg["floor_mib"] <= after.memory_mib <= reg["ceiling_mib"]:
            problems.append("guest memory outside floor/ceiling")
        if not 1 <= after.vcpus <= reg["vcpu_max"]:
            problems.append("guest vCPUs outside bounds")
        if allocated > cap.usable_mib - self.reserve_mib(cap.usable_mib):
            problems.append("host reserve crossed")
        if problems:
            self._quarantine_auto(guest_id, "; ".join(problems))
            raise E.ProviderInvariantViolation("provider result violates invariants", problems="; ".join(problems))

    def _quarantine_auto(self, guest: str, reason: str) -> None:
        self.quarantine.set("guest", guest, principal=f"controller:inv32/{self.controller_id}", reason=reason,
                            ticket="AUTO", owner="oncall", ttl_s=None)

    def _trusted_event(self, event_hash: str, *, guest: str) -> dict[str, Any]:
        if not self.store.verify_recent():
            raise E.StoreIntegrityError("audit chain failed verification")
        for ev in reversed(self.store.audit_events):
            if ev["event_hash"] == event_hash:
                if ev.get("guest") != guest or ev.get("host") != self.host:
                    raise E.ValidationFailed("record belongs to another guest or host")
                if ev.get("kind") not in ("memory", "vcpu") or ev.get("outcome") not in ("success", "partial_success"):
                    raise E.ValidationFailed("record is not a reversible applied adjustment")
                return ev
        raise E.ValidationFailed("record not present in this host's authenticated audit history")

    def _commit(self, req, op, principal, decision, before: LiveGuest, plan, after: LiveGuest, result, outcome,
                ctx, fingerprint, noop: bool = False) -> dict[str, Any]:
        op_id, kind = req["operation_id"], plan["kind"]
        self.store.put_guest_state(req["guest"], memory_mib=after.memory_mib, vcpus=after.vcpus,
                                   provider_version=after.state_version, epoch=self.ownership.epoch)
        if not noop:
            self.store.op_phase(op_id, "state_committed")
        payload: dict[str, Any] = {
            "kind": kind if op.endswith("adjust") else f"{kind}_revert", "operation_id": op_id,
            "guest": req["guest"], "tenant": req["tenant"], "outcome": outcome,
            "provider_request_id": result.request_id if result else None,
            "provider_status": result.status.value if result else "noop",
            "rule": plan["rule"], "trace_id": ctx.trace_id, **decision.audit_fields(),
            "reason": (req.get("reason") or "")[:256],
        }
        if kind == "memory":
            payload.update({"from_mib": before.memory_mib, "target_mib": plan["target"], "applied_mib": after.memory_mib,
                            "reversible_to": before.memory_mib})
            if op == "memory_adjust":
                payload["requested_mib"] = req["target_mib"]
        else:
            payload.update({"from_vcpus": before.vcpus, "applied_vcpus": after.vcpus, "reversible_to": before.vcpus})
            if op == "vcpu_adjust":
                payload["requested_vcpus"] = req["target_vcpus"]
        if op.endswith("revert"):
            payload["reverted_event_hash"] = req["record_event_hash"]
        with self.tracer.span("audit_append", ctx):
            ev = self._audit_control(payload)
        validate("audit_event", ev)  # every published event is schema-checked
        response = {"schema": RESULT_SCHEMA, "operation_id": op_id, "outcome": outcome, "replayed": False,
                    "event": ev, "provider_request_id": payload["provider_request_id"], "trace_id": ctx.trace_id}
        self.store.op_phase(op_id, "audit_committed", event_hash=ev["event_hash"], result=response,
                            fingerprint=fingerprint, guest=req["guest"], created=self._clock())
        self.log.log("INFO", "adjustment committed", host=self.host, tenant=req["tenant"], guest=req["guest"],
                     operation_id=op_id, trace_id=ctx.trace_id, epoch=self.ownership.epoch,
                     config_digest=self.config.active.digest, outcome=outcome, audit_sequence=ev["sequence"],
                     audit_hash=ev["event_hash"])
        return response

    def provider_call(self, fn, deadline: float, *, idempotent: bool = True):
        cfg = self.config.active
        policy = RetryPolicy(max_attempts=cfg["retry_max_attempts"], base_delay_s=cfg["retry_base_delay_s"],
                             max_delay_s=cfg["retry_max_delay_s"], budget=self._retry_budget, sleep=self._sleep,
                             clock=self._mono, metrics=self.metrics, rng=self._rng)

        def guarded():
            with self.provider_circuit.guard(counts=lambda e: getattr(e, "category", None) in
                                             (E.Category.DEPENDENCY, E.Category.TIMEOUT)
                                             and not isinstance(e, E.ProviderRejected)):
                return fn()
        return policy.run(guarded, deadline=deadline, idempotent=idempotent)

    # ================================================================ operator controls
    def set_quarantine(self, token: str, scope: str, ident: str | None, *, reason: str, ticket: str, owner: str,
                       ttl_s: float | None = None, auto_expire_safe: bool = False) -> dict[str, Any]:
        p = self.authn.authenticate(token)
        action = "emergency.disable" if scope == "global" else "quarantine.set"
        authorize(self.policy, p, action, host=self.host, tenant=ident if scope == "tenant" else None)
        return self.quarantine.set(scope, ident, principal=p.id, reason=reason, ticket=ticket, owner=owner,
                                   ttl_s=ttl_s, auto_expire_safe=auto_expire_safe)

    def clear_quarantine(self, token: str, scope: str, ident: str | None, *, reason: str) -> None:
        p = self.authn.authenticate(token)
        action = "emergency.disable" if scope == "global" else "quarantine.set"
        authorize(self.policy, p, action, host=self.host, tenant=ident if scope == "tenant" else None)
        self.quarantine.clear(scope, ident, principal=p.id, reason=reason)

    def cancel(self, operation_id: str) -> None:
        self._cancelled.add(operation_id)

    def explain(self, token: str, operation_id: str) -> dict[str, Any] | None:
        p = self.authn.authenticate(token)
        authorize(self.policy, p, "explain.read", host=self.host, tenant=None)
        return self.explainer.explain(operation_id)

    def drain(self, timeout_s: float = 5.0) -> bool:
        self._draining = True
        end = self._mono() + timeout_s
        while self.admission.inflight() and self._mono() < end:
            self._sleep(0.01)
        self.adapter.drain()
        return self.admission.inflight() == 0

    # ================================================================ recovery / reconciliation
    def recover(self) -> list[dict[str, Any]]:
        """Reconcile every incomplete journalled operation against live state.  Never replays a mutation."""
        report = []
        t0 = self._mono()
        for op_id, rec in sorted(self.store.incomplete_ops().items()):
            phase = rec.get("phase")
            guest = str(rec.get("guest"))
            try:
                live = self.adapter.get_guest(guest)
            except E.ControlError:
                report.append({"operation_id": op_id, "result": "blocked", "why": "guest unreadable"})
                continue
            kind = "memory" if str(rec.get("primitive", "")).startswith("memory") else "vcpu"
            observed = live.memory_mib if kind == "memory" else live.vcpus
            if phase == "prepared":
                self.store.op_phase(op_id, "failed", code="crashed_before_provider_call", verdict="not_applied")
                report.append({"operation_id": op_id, "result": "not_applied"})
                continue
            if live.incarnation != rec.get("incarnation"):
                verdict = "ambiguous"
            elif observed == rec.get("target") and live.state_version > rec.get("expected_version", -1):
                verdict = "applied"
            elif observed == rec.get("from_value") and live.state_version == rec.get("expected_version"):
                verdict = "not_applied"
            elif observed == rec.get("from_value"):
                verdict = "not_applied_or_reverted"
            else:
                verdict = "ambiguous"
            if verdict == "ambiguous":
                self._quarantine_auto(guest, f"reconciliation of {op_id} ambiguous")
                report.append({"operation_id": op_id, "result": "ambiguous_quarantined"})
                continue
            self.store.put_guest_state(guest, memory_mib=live.memory_mib, vcpus=live.vcpus,
                                       provider_version=live.state_version, epoch=self.ownership.epoch)
            ev = self._audit_control({"kind": "reconciled", "operation_id": op_id, "guest": guest,
                                      "verdict": verdict, "observed": observed, "prior_phase": phase})
            result = {"schema": RESULT_SCHEMA, "operation_id": op_id,
                      "outcome": "success" if verdict == "applied" else "terminal_failure",
                      "replayed": False, "event": ev, "provider_request_id": rec.get("provider_request_id")}
            self.store.op_phase(op_id, "reconciled", verdict=verdict, result=result)
            report.append({"operation_id": op_id, "result": verdict})
        self.metrics.observe("inv32_reconcile_latency_seconds", self._mono() - t0)
        return report

    # ================================================================ health / inventory
    def health(self) -> HealthReport:
        checks: dict[str, bool] = {}
        checks["audit_integrity"] = self.store.verify()
        try:
            self.ownership.validate()
            checks["ownership"] = True
        except E.ControlError:
            checks["ownership"] = False
        try:
            checks["provider"] = bool(self.adapter.health().get("ok"))
        except Exception:  # noqa: BLE001
            checks["provider"] = False
        checks["provider_circuit"] = self.provider_circuit.state != CircuitBreaker.OPEN
        checks["policy"] = self.policy.available
        checks["config"] = self.config.active is not None
        checks["no_unknown_outcomes"] = not any(v.get("phase") == "unknown" for v in self.store.incomplete_ops().values())
        checks["not_draining"] = not self._draining
        mode = self.config.active["mode"]
        emergency = "global" in self.quarantine.active() or self.config.active["emergency_disable"]
        if emergency:
            mode = "frozen_write"
        degraded = []
        if not self.config.active["telemetry_enabled"]:
            degraded.append("TELEMETRY_DOWN")
        ready = all(checks.values()) and mode == "normal"
        return HealthReport(live=True, ready=ready, mode=mode, checks=checks, degraded=degraded)

    def _require_ready_for_mutation(self) -> None:
        cfg = self.config.active
        if cfg["emergency_disable"]:
            raise E.EmergencyDisabled("mutations disabled by emergency configuration")
        if cfg["mode"] != "normal":
            raise E.NotReady("controller mode forbids mutation", mode=cfg["mode"])
        self._mutations_since_full_verify += 1
        full = self._mutations_since_full_verify >= self.full_verify_every
        if not (self.store.verify() if full else self.store.verify_recent()):
            raise E.StoreIntegrityError("audit integrity failed; mutations blocked")
        if full:
            self._mutations_since_full_verify = 0
        if not self.policy.available:
            raise E.PolicyUnavailable("policy service unavailable; failing closed")

    def inventory(self) -> dict[str, Any]:
        from .validation import SCHEMA_FILES
        c = self.config.active
        caps = self._caps
        return {"schema": "PK_INV32_INVENTORY/1", "component": "INV-32", "version": __version__,
                "schemas": sorted(SCHEMA_FILES.values()) + [AUDIT_EVENT_SCHEMA, HOST_RESOURCES_SCHEMA],
                "config_revision": c.meta.revision, "config_digest": c.digest,
                "provider": caps.provider, "provider_version": caps.provider_version,
                "capabilities": {k: v for k, v in caps.__dict__.items() if isinstance(v, (bool, int, str))},
                "controller_id": self.controller_id, "epoch": self.ownership.epoch,
                "circuit": self.provider_circuit.snapshot(),
                "feature_gates": {k: c[k] for k in c.values if k.startswith("feature_")}}

    def host_snapshot(self) -> dict[str, Any]:
        cap = self.adapter.host_capacity()
        guests = self.adapter.list_guests()
        reserve = self.reserve_mib(cap.usable_mib)
        allocated = sum(g.memory_mib for g in guests)
        snap: dict[str, Any] = {"schema": HOST_RESOURCES_SCHEMA, "host": self.host, "total_mib": cap.usable_mib,
                "reserve_mib": reserve, "allocated_mib": allocated, "free_mib": cap.usable_mib - reserve - allocated,
                "guest_count": len(guests), "audit_head": self.store.audit_head}
        validate("host", snap)
        self.metrics.set("inv32_guest_count", len(guests))
        self.metrics.set("inv32_memory_mib", allocated, kind="allocated")
        self.metrics.set("inv32_memory_mib", snap["free_mib"], kind="free")
        self.metrics.set("inv32_memory_mib", reserve, kind="reserved")
        self.metrics.set("inv32_lease_age_seconds", self.ownership.age_s())
        return snap


def _replay_conflict(op_id: str) -> Exception:
    return ReplayConflict("operation_id reused for a different request", operation_id=op_id)
