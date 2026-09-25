"""Durable expansion service core: submit -> journal -> fenced reconcile -> observe.

SPDX-License-Identifier: NOASSERTION

Covers MC-013/019/020/021/022/024/025/026/028/029/038.  The 5.0.0
``CpuExpansionController`` remains the single source of the expansion
policy: every submit rebuilds it from the durable document, applies the
request, and persists the resulting state with a compare-and-swap.

Safety rules enforced here:
* observed_vcpus only moves through a verified guest observation;
* an UNKNOWN adapter outcome is never retried blindly — the next pass
  re-reads live hypervisor state first;
* every adapter call carries the current lease's fence token;
* restart recovery rebuilds pending work from the journal only.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
import uuid
from dataclasses import replace
from typing import Any, Callable

from ..expansion import CpuExpansionController, ExpansionError, StaleGeneration, VmCpuState, IdempotencyConflict
from .adapters.base import AdapterError, EnsureRequest, Outcome
from .audit import AuditChain
from .observation import ObservationRejected, ObservationVerifier, classify_stall
from .policy import DEFAULT_EVALUATORS, evaluate
from .resilience import CircuitBreaker, CircuitOpen, DependencyHealth, RetryBudget, RetryPolicy
from .security import QuotaService
from .store import CasConflict, FileStateStore, LeaseHeld
from .telemetry import Metrics, StructuredLogger

TERMINAL = ("done", "failed", "abandoned", "superseded")


class DegradedMode(ExpansionError):
    code = "DEGRADED_MODE"
    retryable = True


class PolicyDenied(ExpansionError):
    code = "POLICY_DENIED"


def _params_hash(target: int, expected: int | None) -> str:
    return hashlib.sha256(json.dumps([target, expected]).encode()).hexdigest()[:16]


def state_from_doc(doc: dict) -> VmCpuState:
    return VmCpuState(**doc["cpu"])


def state_to_cpu(s: VmCpuState) -> dict:
    d = s.as_dict()
    return {k: d[k] for k in ("vm_id", "observed_vcpus", "desired_vcpus", "max_vcpus", "host_capacity_vcpus",
                              "acpi_hotplug_supported", "guest_hotplug_supported", "expansion_enabled",
                              "generation")}


class ExpansionService:
    def __init__(self, store: FileStateStore, adapter, verifier: ObservationVerifier, audit: AuditChain,
                 *, owner: str, quota: QuotaService | None = None, health: DependencyHealth | None = None,
                 metrics: Metrics | None = None, logger: StructuredLogger | None = None,
                 precedence: list[str] | None = None, lease_ttl_s: float = 15.0,
                 retry: RetryPolicy | None = None, seed: int = 0,
                 clock: Callable[[], float] = time.time) -> None:
        self.store, self.adapter, self.verifier, self.audit = store, adapter, verifier, audit
        self.owner, self.quota = owner, quota
        self.health = health or DependencyHealth()
        self.metrics = metrics or Metrics()
        self.log = logger or StructuredLogger("inv34.reconciler")
        self.precedence = precedence or ["security", "residency", "capacity", "slo", "cost"]
        self.lease_ttl = lease_ttl_s
        self.retry = retry or RetryPolicy()
        self.budget = RetryBudget(self.retry.budget_ratio)
        self.breaker = CircuitBreaker("hypervisor_adapter")
        self.rng = random.Random(seed)
        self.clock = clock
        self.policy_ctx: dict[str, dict[str, Any]] = {}      # vm_id -> extra policy inputs
        self.last_decision: dict[str, dict] = {}

    # ------------------------------------------------------------------ submit
    def submit(self, vm_id: str, request_id: str, target: int, expected_generation: int | None = None,
               *, actor: str = "", trace_id: str = "", config_digest: str = "") -> dict:
        # Validate before touching durable state (fuzz found an unhashable request_id here).
        from .validation import require_identifier, require_int
        require_identifier(vm_id, "vm_id")
        require_identifier(request_id, "request_id")
        require_int(target, "target_vcpus", minimum=1, maximum=65_536)
        if expected_generation is not None:
            require_int(expected_generation, "expected_generation", minimum=0)
        ok, bad = self.health.expansion_allowed()
        for _ in range(8):  # CAS retry loop against concurrent writers
            doc = self.store.load(vm_id)
            if doc is None:
                raise ExpansionError("unknown VM", vm_id=vm_id)
            ph = _params_hash(target, expected_generation)
            prior = doc["idempotency"].get(request_id)
            if prior is not None:           # durable idempotency survives restart (MC-020)
                if prior["params"] != ph:
                    raise IdempotencyConflict("request_id reused with different parameters", request_id=request_id)
                self.metrics.inc("inv34_requests_total", outcome="replay")
                return prior["result"]
            state = state_from_doc(doc)
            if target > state.desired_vcpus and not ok:
                self.metrics.inc("inv34_requests_total", outcome="degraded")
                raise DegradedMode("mandatory dependency unhealthy; new expansion refused", unhealthy=bad)
            ctrl = CpuExpansionController(state)
            result = ctrl.request_expansion(request_id, target, expected_generation=expected_generation)
            new_state = ctrl.snapshot()
            op_id = None
            if result.status == "accepted":
                ctx = {"add_vcpus": result.added_vcpus,
                       "host_free_vcpus": state.host_capacity_vcpus - state.desired_vcpus,
                       **self.policy_ctx.get(vm_id, {})}
                decision = evaluate(self.precedence, DEFAULT_EVALUATORS, ctx)
                self.last_decision[vm_id] = {"request_id": request_id, "inputs": ctx, **decision.as_dict()}
                if not decision.allowed:
                    self.audit.append("request.rejected", vm_id=vm_id, request_id=request_id,
                                      code="POLICY_DENIED", constraint=decision.deciding)
                    raise PolicyDenied(f"denied by {decision.deciding}", trace=decision.as_dict()["trace"])
                if self.quota is not None:
                    self.quota.reserve(vm_id, target)
                op_id = f"op-{uuid.uuid4().hex[:20]}"
            payload = {**result.as_dict(), "operation_id": op_id, "trace_id": trace_id}

            def mutate(d: dict, _s=new_state, _op=op_id, _p=payload, _ph=ph) -> None:
                d["cpu"] = state_to_cpu(_s)
                d["idempotency"][request_id] = {"params": _ph, "result": _p}
                d["idempotency_order"].append(request_id)
                if _op:
                    for e in d["journal"]:
                        if e["state"] not in TERMINAL:
                            e["state"] = "superseded"
                    d["journal"].append({"op_id": _op, "request_id": request_id, "target": target,
                                         "generation": _s.generation, "state": "pending", "attempts": 0,
                                         "next_attempt_at": 0.0, "accepted_at": self.clock(),
                                         "actor": actor, "trace_id": trace_id, "config_digest": config_digest,
                                         "last_progress_at": self.clock(), "history": []})
            try:
                self.store.update(vm_id, doc["revision"], mutate)
            except CasConflict:
                continue
            self.audit.append("request.accepted" if op_id else "request.received", vm_id=vm_id,
                              request_id=request_id, actor=actor, target=target, operation_id=op_id,
                              generation=new_state.generation, trace_id=trace_id, config_digest=config_digest)
            self.metrics.inc("inv34_requests_total", outcome=result.status)
            return payload
        raise StaleGeneration("could not commit after repeated concurrent updates")

    # --------------------------------------------------------------- reconcile
    def reconcile_once(self, vm_id: str) -> dict:
        try:
            fence, doc = self.store.acquire_lease(vm_id, self.owner, self.lease_ttl)
        except LeaseHeld as exc:
            return {"vm_id": vm_id, "action": "skipped", "reason": str(exc)}
        self.audit.append("lease.acquired", vm_id=vm_id, owner=self.owner, fence=fence)
        live_entries = [e for e in doc["journal"] if e["state"] not in TERMINAL]
        if not live_entries:
            return {"vm_id": vm_id, "action": "idle"}
        entry = live_entries[-1]
        now = self.clock()
        if entry["next_attempt_at"] > now:
            return {"vm_id": vm_id, "action": "backoff", "until": entry["next_attempt_at"]}
        try:
            self.breaker.before_call()
        except CircuitOpen as exc:
            self.health.set("hypervisor_adapter", "down")
            return {"vm_id": vm_id, "action": "circuit_open", "reason": str(exc)}
        # Always read live state first: this is what makes UNKNOWN safe to resolve.
        try:
            live = self.adapter.read_live(vm_id)
        except AdapterError as exc:
            self._breaker_record(False)
            return self._schedule_retry(vm_id, doc, entry, fence, exc.code.value)
        if live.present_vcpus >= entry["target"]:
            self._breaker_record(True)
            return self._finish(vm_id, doc, entry, fence, "presented", live.present_vcpus, "live>=target")
        if entry["state"] == "ambiguous":
            entry_note = "ambiguous outcome resolved by live read: action not applied; re-issuing once"
            self.audit.append("reconcile.ambiguous", vm_id=vm_id, operation_id=entry["op_id"], note=entry_note)
        if entry["attempts"] > 0 and not self.budget.try_spend():
            return {"vm_id": vm_id, "action": "retry_budget_exhausted"}
        if entry["attempts"] == 0:
            self.budget.on_first_attempt()
        req = EnsureRequest(vm_id, entry["target"], entry["generation"], entry["op_id"], fence,
                            time.monotonic() + 30.0, entry.get("trace_id", ""), entry["request_id"])
        self.audit.append("adapter.action", vm_id=vm_id, operation_id=entry["op_id"], fence=fence,
                          target=entry["target"])
        t0 = time.monotonic()
        try:
            res = self.adapter.ensure_vcpus(req)
        except AdapterError as exc:
            self._breaker_record(False)
            self.metrics.inc("inv34_adapter_calls_total", outcome="error", code=exc.code.value)
            if not exc.retryable:
                return self._finish(vm_id, doc, entry, fence, "failed", None, exc.code.value)
            return self._schedule_retry(vm_id, doc, entry, fence, exc.code.value)
        self.metrics.observe("inv34_adapter_call_seconds", time.monotonic() - t0)
        self.metrics.inc("inv34_adapter_calls_total", outcome=res.outcome.value)
        self.audit.append("adapter.outcome", vm_id=vm_id, operation_id=entry["op_id"], outcome=res.outcome.value,
                          backend_operation_id=res.backend_operation_id, error_code=res.error_code)
        self._breaker_record(res.outcome not in (Outcome.UNKNOWN,) and not (res.outcome == Outcome.FAILED and res.retryable))
        if res.outcome in (Outcome.ACKNOWLEDGED, Outcome.NOOP):
            return self._finish(vm_id, doc, entry, fence, "presented", res.present_after, res.outcome.value)
        if res.outcome == Outcome.UNKNOWN:
            return self._mark(vm_id, doc, entry, fence, "ambiguous", res.error_code or "unknown", backoff=True)
        if res.outcome in (Outcome.PARTIAL, Outcome.SUBMITTED):
            return self._mark(vm_id, doc, entry, fence, "in_progress", res.outcome.value, backoff=True)
        if res.retryable:
            return self._schedule_retry(vm_id, doc, entry, fence, res.error_code or "failed")
        return self._finish(vm_id, doc, entry, fence, "failed", None, res.error_code or "failed")

    def _breaker_record(self, ok: bool) -> None:
        """Keep dependency health in step with the breaker, so degraded mode also ENDS
        when the hypervisor recovers (defect found by tools/perf.py: health stayed 'down')."""
        self.breaker.record(ok)
        self.health.set("hypervisor_adapter", "healthy" if self.breaker.state == "closed" else "down")

    def _commit_entry(self, vm_id: str, fence: int, op_id: str, fn) -> dict:
        for _ in range(8):
            doc = self.store.load(vm_id)
            self.store.check_lease(doc, self.owner, fence)       # lost lease -> LeaseLost, nothing written
            try:
                return self.store.update(vm_id, doc["revision"],
                                         lambda d: fn(next(e for e in d["journal"] if e["op_id"] == op_id), d))
            except CasConflict:
                continue
        raise CasConflict("could not commit journal entry")

    def _schedule_retry(self, vm_id, doc, entry, fence, reason) -> dict:
        attempts = entry["attempts"] + 1
        if attempts >= self.retry.max_attempts:
            return self._finish(vm_id, doc, entry, fence, "failed", None, f"retries exhausted: {reason}")
        delay = self.retry.backoff(attempts, self.rng)

        def fn(e, d):
            e["attempts"], e["next_attempt_at"] = attempts, self.clock() + delay
            e["history"].append({"at": self.clock(), "event": "retry", "reason": reason})
        self._commit_entry(vm_id, fence, entry["op_id"], fn)
        return {"vm_id": vm_id, "action": "retry_scheduled", "delay_s": delay, "reason": reason}

    def _mark(self, vm_id, doc, entry, fence, state, reason, backoff=False) -> dict:
        delay = self.retry.backoff(entry["attempts"] + 1, self.rng) if backoff else 0.0

        def fn(e, d):
            e["state"], e["attempts"] = state, e["attempts"] + 1
            e["next_attempt_at"] = self.clock() + delay
            e["history"].append({"at": self.clock(), "event": state, "reason": reason})
        self._commit_entry(vm_id, fence, entry["op_id"], fn)
        return {"vm_id": vm_id, "action": state, "reason": reason}

    def _finish(self, vm_id, doc, entry, fence, how, present, reason) -> dict:
        state = "done" if how == "presented" else "failed"

        def fn(e, d):
            e["state"] = state
            e["history"].append({"at": self.clock(), "event": how, "reason": reason, "present": present})
            d.pop("needs_reconcile", None)
        self._commit_entry(vm_id, fence, entry["op_id"], fn)
        # "done" here means the hypervisor presented the vCPUs.  Convergence is still
        # only reported when the guest observation reaches desired (status.converged).
        return {"vm_id": vm_id, "action": how, "present": present, "reason": reason}

    # ------------------------------------------------------------- observation
    def observe(self, report: dict) -> dict:
        try:
            obs = self.verifier.verify(report)
        except ObservationRejected as exc:
            self.audit.append("observation.rejected", vm_id=str(report.get("vm_id"))[:128], code=exc.code)
            self.metrics.inc("inv34_observations_total", outcome=exc.code)
            raise
        for _ in range(8):
            doc = self.store.load(obs.vm_id)
            ctrl = CpuExpansionController(state_from_doc(doc))
            before = ctrl.snapshot().observed_vcpus
            new = ctrl.record_observation(obs.online_vcpus)

            def mutate(d, _n=new):
                d["cpu"] = state_to_cpu(_n)
                d.setdefault("observation", {})
                d["observation"].update({"last_at": obs.observed_at, "source": obs.source_id,
                                         "sequence": obs.sequence})
                if _n.observed_vcpus > before:
                    for e in d["journal"]:
                        if e["state"] not in ("failed", "abandoned"):
                            e["last_progress_at"] = self.clock()
            try:
                self.store.update(obs.vm_id, doc["revision"], mutate)
                break
            except CasConflict:
                continue
        self.audit.append("observation.accepted", vm_id=obs.vm_id, source=obs.source_id, sequence=obs.sequence,
                          online=obs.online_vcpus)
        self.metrics.inc("inv34_observations_total", outcome="accepted")
        return new.as_dict()

    # ------------------------------------------------------------------ status
    def status(self, vm_id: str) -> dict:
        doc = self.store.load(vm_id)
        s = state_from_doc(doc)
        pend = [e for e in doc["journal"] if e["state"] not in TERMINAL]
        obs_at = (doc.get("observation") or {}).get("last_at")
        accepted = max([e["accepted_at"] for e in doc["journal"]] or [self.clock()])
        progress = max([e.get("last_progress_at", 0) for e in doc["journal"]] or [0])
        stall = classify_stall(s.desired_vcpus, s.observed_vcpus, accepted, progress, obs_at, self.clock())
        return {**s.as_dict(), "revision": doc["revision"], "pending_operations": len(pend),
                "needs_reconcile": bool(doc.get("needs_reconcile")), "convergence": stall.__dict__,
                "lease": doc.get("lease")}

    def set_enabled(self, vm_id: str, enabled: bool, actor: str) -> dict:
        """Quarantine/freeze control (MC-027). Freezing never removes CPUs."""
        for _ in range(8):
            doc = self.store.load(vm_id)
            try:
                d = self.store.update(vm_id, doc["revision"],
                                      lambda x: x["cpu"].update(expansion_enabled=enabled))
                self.audit.append("ops.enable" if enabled else "ops.disable", vm_id=vm_id, actor=actor)
                return d["cpu"]
            except CasConflict:
                continue
        raise CasConflict("could not toggle")

    def recover(self) -> dict:
        """Startup recovery (MC-026): rebuild pending work from journals; nothing is
        re-issued without the live read in ``reconcile_once``."""
        summary = {"vms": 0, "pending": 0, "ambiguous": 0, "needs_reconcile": 0}
        seqs = {}
        for vm_id in self.store.vm_ids():
            doc = self.store.load(vm_id)
            summary["vms"] += 1
            for e in doc["journal"]:
                if e["state"] not in TERMINAL:
                    summary["pending"] += 1
                if e["state"] == "ambiguous":
                    summary["ambiguous"] += 1
            if doc.get("needs_reconcile"):
                summary["needs_reconcile"] += 1
            o = doc.get("observation")
            if o:
                seqs[(vm_id, o["source"])] = o["sequence"]
        self.verifier.restore_sequences(seqs)   # replay protection survives restart
        return summary
