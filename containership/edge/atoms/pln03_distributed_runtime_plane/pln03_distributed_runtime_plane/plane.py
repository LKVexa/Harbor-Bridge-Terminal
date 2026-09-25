"""GovernedRuntime - the production-facing PLN-03 surface.

Composes the dependency-free reference ``DistributedRuntime`` with every
remediation control: lifecycle gating, capability-token enforcement, admission
and quotas, circuit breaking, deadlines/cancellation, bounded retry, degraded
store-and-forward, tamper-evident audit, metrics/logs/traces and config
provenance.  Order of checks follows the MC-010 precedence: security
(lifecycle/quarantine, token) -> residency (config validation) -> integrity
(fencing in adapters) -> SLO (admission, deadlines, retry) -> cost.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from .audit_log import AuditLog
from .config import DEFAULT, ConfigStore, Revision
from .durability import OfflineBuffer, ReadOnly
from .envelope import to_envelope
from .lifecycle import Lifecycle, State
from .resilience import Admission, CircuitBreaker, CircuitOpen, Deadline, RetryBudget, retry_call
from .runtime import Adapter, AdapterUnavailable, CapabilityDenied, DistributedRuntime, RuntimePlaneError
from .telemetry import Metrics, StructuredLog, Watchdog, health_report, parse_traceparent
from .tokens import TokenVerifier

T = TypeVar("T")
WRITE_OPS = {"state.write", "state.delete", "state.transact", "message.publish"}


@dataclass(frozen=True)
class PublishResult:
    accepted: bool
    outcome: str  # "success" | "degraded" (buffered locally, will reconcile)
    trace_id: str


class GovernedRuntime:
    def __init__(self, bindings: dict[str, Adapter], *, verifier: TokenVerifier, config: ConfigStore | None = None,
                 audit: AuditLog | None = None, owner: str | None = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        self.core = DistributedRuntime(bindings)
        self.bindings = dict(bindings)
        self.verifier = verifier
        self.audit = audit or AuditLog()
        self.metrics, self.log = Metrics(), StructuredLog()
        self.owner = owner
        self.sleep, self.clock = sleep, clock
        self.config = config or ConfigStore(on_change=self._config_changed)
        if config is not None:
            config.on_change = self._config_changed
        self.lifecycle = Lifecycle("pln03-runtime", on_transition=self._on_transition)
        self.quarantined_adapters: set[str] = set()
        if self.config._active is None:
            self.config.activate(DEFAULT, author="bootstrap", source="plane.DEFAULT", reason="secure defaults")
        else:
            self._config_changed(self.config.active, None)

    # -- configuration -------------------------------------------------------------------------
    def _config_changed(self, rev: Revision, prev: Revision | None) -> None:
        lim = rev.limits
        self.limits = lim
        self.admission = Admission(lim, self.clock)
        self.budget = RetryBudget(lim.retry_budget_ratio)
        self.breakers = {name: CircuitBreaker(lim.breaker_failure_threshold, lim.breaker_reset_s, self.clock)
                         for name in {a.name for a in self.bindings.values()}}
        self.buffer = getattr(self, "buffer", None) or OfflineBuffer(lim.max_offline_buffer_msgs,
                                                                     lim.max_offline_buffer_bytes)
        self.watchdog = Watchdog(lim.max_deadline_s, self.clock)
        if hasattr(self, "audit"):
            self.audit.emit("config.activate" if not rev.source.startswith("rollback:") else "config.rollback",
                            workload="operator", tenant=None, outcome="success", revision=rev.number,
                            digest=rev.digest, author=rev.author)

    def _on_transition(self, name: str, src: State, dst: State, actor: str, reason: str) -> None:
        self.audit.emit("lifecycle", workload=actor, tenant=None, outcome="success",
                        src=src.value, dst=dst.value, reason=reason)
        self.log.log("info", "lifecycle", src=src.value, dst=dst.value, actor=actor, reason=reason)

    # -- operator controls (MC-042, MC-049 emergency disable) ------------------------------------
    def start(self, actor: str = "operator") -> None:
        self.lifecycle.transition(State.STARTING, actor=actor, reason="start")
        self.lifecycle.transition(State.READY, actor=actor, reason="dependencies validated")

    def freeze(self, actor: str, reason: str) -> None:
        self.lifecycle.transition(State.FROZEN, actor=actor, reason=reason)

    def unfreeze(self, actor: str, reason: str) -> None:
        self.lifecycle.transition(State.READY, actor=actor, reason=reason)

    def emergency_disable(self, actor: str, reason: str) -> None:
        self.lifecycle.transition(State.QUARANTINED, actor=actor, reason=reason)
        self.audit.emit("quarantine", workload=actor, tenant=None, outcome="success", target="runtime", reason=reason)

    def quarantine_adapter(self, adapter_name: str, actor: str, reason: str) -> None:
        self.quarantined_adapters.add(adapter_name)
        self.audit.emit("quarantine", workload=actor, tenant=None, outcome="success", target=adapter_name,
                        reason=reason)

    def release_adapter(self, adapter_name: str, actor: str, reason: str) -> None:
        self.quarantined_adapters.discard(adapter_name)
        self.audit.emit("quarantine", workload=actor, tenant=None, outcome="released", target=adapter_name,
                        reason=reason)

    # -- the governed call path ------------------------------------------------------------------
    def _call(self, action: str, capability: str, workload: str, tenant: str, token: str | None,
              fn: Callable[[], T], *, deadline_s: float | None, traceparent: str | None, **meta) -> T:
        trace = parse_traceparent(traceparent)
        started = self.clock()
        try:
            self.lifecycle.require(write=action in WRITE_OPS)
            self.verifier.verify(token, workload=workload, tenant=tenant, capability=capability)
            adapter = self.bindings.get(f"{workload}:{capability}")
            if adapter is None:
                raise CapabilityDenied(f"{workload} is not bound to {capability!r}",
                                       workload=workload, capability=capability)
            if adapter.name in self.quarantined_adapters:
                from .lifecycle import Quarantined
                raise Quarantined("adapter quarantined", adapter=adapter.name)
            ds = min(deadline_s or self.limits.default_deadline_s, self.limits.max_deadline_s)
            deadline = Deadline(ds, self.clock)
            breaker = self.breakers[adapter.name]
            self.admission.acquire(tenant)
            wd = self.watchdog.start(action)
            try:
                def attempt() -> T:
                    breaker.before(adapter.name)
                    try:
                        r = fn()
                    except AdapterUnavailable:
                        breaker.record(False)
                        raise
                    breaker.record(True)
                    return r
                result = retry_call(attempt, limits=self.limits, deadline=deadline, budget=self.budget,
                                    sleep=self.sleep,
                                    on_retry=lambda n, e: self.metrics.inc("retries", capability=capability))
            finally:
                self.watchdog.stop(wd)
                self.admission.release(tenant)
        except RuntimePlaneError as exc:
            self._record(action, capability, workload, tenant, exc, trace, started, meta)
            raise
        except (PermissionError, ValueError, KeyError) as exc:
            self._record(action, capability, workload, tenant, exc, trace, started, meta)
            raise
        self._record(action, capability, workload, tenant, None, trace, started, meta)
        return result

    def _record(self, action, capability, workload, tenant, exc, trace, started, meta) -> None:
        code = getattr(exc, "code", "PK_OK") if exc else "PK_OK"
        outcome = to_envelope(exc)["outcome"] if exc else "success"
        self.metrics.inc("adapter_calls", capability=capability, outcome=outcome)
        self.metrics.observe(f"{capability}_latency_seconds", self.clock() - started)
        denied = code in {"PK_CAPABILITY_DENIED", "PK_TOKEN_INVALID", "PK_TOKEN_EXPIRED", "PK_QUARANTINED"}
        if denied:
            self.metrics.inc("capability_denials", capability=capability, code=code)
        self.audit.emit("deny" if denied else action, workload=workload, tenant=tenant,
                        outcome=outcome, code=code, trace_id=trace, capability=capability, **meta)
        if exc:
            self.log.log("warning", "call_failed", code=code, capability=capability, trace_id=trace,
                         workload=workload, tenant=tenant)

    # -- public API ------------------------------------------------------------------------------
    def state_get(self, workload, tenant, key, *, token, deadline_s=None, traceparent=None):
        return self._call("state.read", "state", workload, tenant, token,
                          lambda: self.core.state_get(workload, tenant, key),
                          deadline_s=deadline_s, traceparent=traceparent, key_len=len(key))

    def state_set(self, workload, tenant, key, value, *, token, deadline_s=None, traceparent=None):
        return self._call("state.write", "state", workload, tenant, token,
                          lambda: self.core.state_set(workload, tenant, key, value),
                          deadline_s=deadline_s, traceparent=traceparent, size=len(value) if isinstance(value, bytes) else -1)

    def state_delete(self, workload, tenant, key, *, token, deadline_s=None, traceparent=None):
        return self._call("state.delete", "state", workload, tenant, token,
                          lambda: self.core.state_delete(workload, tenant, key),
                          deadline_s=deadline_s, traceparent=traceparent)

    def state_transact(self, workload, tenant, operations, *, token, deadline_s=None, traceparent=None):
        ops = list(operations)
        return self._call("state.transact", "state", workload, tenant, token,
                          lambda: self.core.state_transact(workload, tenant, ops),
                          deadline_s=deadline_s, traceparent=traceparent, ops=len(ops))

    def publish(self, workload, tenant, topic, payload, idempotency_key, *, token, deadline_s=None,
                traceparent=None) -> PublishResult:
        trace = parse_traceparent(traceparent)
        tp = f"00-{trace}-{'0' * 15}1-01"
        try:
            ok = self._call("message.publish", "messaging", workload, tenant, token,
                            lambda: self.core.publish(workload, tenant, topic, payload, idempotency_key),
                            deadline_s=deadline_s, traceparent=tp, size=len(payload) if isinstance(payload, bytes) else -1)
            return PublishResult(bool(ok), "success", trace)
        except (AdapterUnavailable, CircuitOpen) as exc:
            cfg = self.config.active.config.get("degraded", {})
            if not cfg.get("allow_local_buffer"):
                raise
            self.buffer.put(workload, tenant, topic, payload, idempotency_key)  # may raise ReadOnly when full
            self.metrics.inc("degraded_buffered")
            self.log.log("warning", "publish_buffered", code=getattr(exc, "code", ""), trace_id=trace)
            return PublishResult(True, "degraded", trace)

    def reconcile(self) -> dict:
        """Replay the offline buffer after reconnect (MC-009).  Original idempotency keys are reused,
        so messages that did land before the partition are suppressed as duplicates."""
        report = self.buffer.drain(lambda w, t, tp, p, i: self.core.publish(w, t, tp, p, i))
        self.metrics.inc("duplicate_deliveries", report["deduplicated"])
        return report

    def subscribe(self, workload, tenant, topic, *, token, deadline_s=None, traceparent=None):
        return self._call("message.subscribe", "messaging", workload, tenant, token,
                          lambda: self.core.subscribe(workload, tenant, topic),
                          deadline_s=deadline_s, traceparent=traceparent)

    def secret_fetch(self, workload, tenant, reference, *, token, deadline_s=None, traceparent=None):
        return self._call("secret.access", "secrets", workload, tenant, token,
                          lambda: self.core.secret_fetch(workload, tenant, reference),
                          deadline_s=deadline_s, traceparent=traceparent, reference=reference)

    def invoke(self, workload, tenant, component, payload, *, token, deadline_s=None, traceparent=None):
        return self._call("invoke", "invoke", workload, tenant, token,
                          lambda: self.core.invoke(workload, tenant, component, payload),
                          deadline_s=deadline_s, traceparent=traceparent, target=component)

    def health(self) -> dict:
        return health_report(lifecycle_state=self.lifecycle.state.value,
                             adapters={a.name: a.available and a.name not in self.quarantined_adapters
                                       for a in self.bindings.values()},
                             breakers={n: b.state for n, b in self.breakers.items()},
                             stalled=self.watchdog.stalled(), config_digest=self.config.active.digest,
                             owner=self.owner)


__all__ = ["GovernedRuntime", "PublishResult", "ReadOnly"]
