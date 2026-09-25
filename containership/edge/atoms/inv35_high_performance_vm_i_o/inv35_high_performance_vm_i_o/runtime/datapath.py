"""Hardened datapath facade: the single entry point production-shaped callers use.

It composes the unchanged ``io_model`` safety core with authentication,
capabilities, tenant isolation, quotas, deadlines, idempotency, lifecycle,
quarantine, telemetry, audit and crash-recovery journalling.  Ordering on the
submit path is deliberate and tested (tests/security, tests/contracts):

  lifecycle gate -> capability -> tenant binding -> deadline/cancel -> breaker
  -> idempotency replay -> descriptor validation (io_model) -> quota -> commit

Nothing guest-controlled is trusted before io_model validation, and no counter
(queue, quota, idempotency, journal) moves unless every earlier stage passed.

Traffic separation (the INV-35 source function, "separate orchestration and
bulk-data channels"): control operations (register, lifecycle, configure,
quarantine) are methods on :class:`ControlPlane`; bulk operations (submit,
complete) are methods on :class:`Datapath`.  They share state but require
disjoint capability actions, so a bulk-data credential cannot drive the control
plane and vice versa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
from threading import RLock
from typing import Any, Mapping

from ..io_model import MemoryRegion, VirtQueue, DescriptorInvalid, QueueFull
from .config import ConfigStore, build as build_config
from .errors import Inv35Error, classify_model_error
from .health import StallDetector, negotiate, status_document
from .lifecycle import DegradedMode, Lifecycle, State
from .policy import CancelToken, CircuitBreaker, Deadline, IdempotencyCache, QuotaManager
from .security import AuditLog, Authority, KeyRing
from .telemetry import Metrics, StructuredLog, TraceContext, decision, explain

BULK_ACTIONS = frozenset({"submit", "complete"})
CONTROL_ACTIONS = frozenset({"register_memory", "lifecycle", "configure", "quarantine", "read_status"})


@dataclass
class _Queue:
    tenant: str
    vq: VirtQueue
    life: Lifecycle
    reservations: list[int] = field(default_factory=list)  # descriptor counts, FIFO (journal mirror)


class Runtime:
    """Shared state for both planes. One instance per host process."""

    def __init__(self, *, keyring: KeyRing | None = None, config: ConfigStore | None = None,
                 clock=time.monotonic, version: str = "4.3.0") -> None:
        self.version = version
        self.keyring = keyring or KeyRing()
        if keyring is None:
            self.keyring.rotate("k1")
        self.authority = Authority(self.keyring)
        self.audit = AuditLog(self.keyring)
        self.config = config or ConfigStore()
        self.metrics = Metrics()
        self.log = StructuredLog()
        self.decisions: list[dict[str, Any]] = []
        self.clock = clock
        self.queues: dict[str, _Queue] = {}
        self.journal: list[dict[str, Any]] = []
        self.idem = IdempotencyCache()
        self._lock = RLock()
        self.control_plane_reachable = True
        self._rebuild_policy()

    # -- policy objects derived from the active configuration -----------------
    def _rebuild_policy(self) -> None:
        c = self.config.active.values
        self.quota = QuotaManager(host_descriptor_capacity=c["host_descriptor_capacity"], tenant_share=c["tenant_share"],
                                  rate=c["submit_rate_per_s"], burst=c["submit_burst"], clock=self.clock)
        self.breaker = CircuitBreaker(c["breaker_threshold"], c["breaker_cooldown_s"], clock=self.clock)
        self.stalls = StallDetector(c["stall_threshold_s"], clock=self.clock)
        for q in self.queues.values():
            self.quota.used[q.tenant] = self.quota.used.get(q.tenant, 0) + q.vq.in_flight_descriptors

    def _decide(self, action: str, outcome: str, code: str, rule: str, trace: TraceContext | None, **inputs: Any) -> None:
        rec = decision(action, outcome, code, inputs=inputs, rule=rule, trace=trace)
        self.decisions.append(rec)
        del self.decisions[:-4096]
        self.metrics.inc("decisions", action=action, outcome=outcome, code=code)
        self.log.emit("warn" if outcome != "success" else "info", f"{action}.{outcome}", trace=trace, code=code, **inputs)

    def _auth(self, token: object, action: str, tenant: str, queue: str, trace: TraceContext | None) -> None:
        if not self.config.active.values["require_capability"]:  # cannot be relaxed by overrides; defensive
            raise Inv35Error("INV35-E500", "require_capability must be true")
        try:
            self.authority.authorize(token, action=action, tenant=tenant, queue=queue,
                                     single_use=self.config.active.values["single_use_capabilities"])
        except Inv35Error as exc:
            self.audit.append("authz.refused", action=action, tenant=tenant, queue=queue, code=exc.code)
            self.metrics.inc("security_refusals", code=exc.code)
            self._decide(action, "refused", exc.code, "capability", trace, tenant=tenant, queue=queue)
            raise

    def status(self) -> dict[str, Any]:
        with self._lock:
            queues = {n: {"tenant": q.tenant, "state": q.life.state.value, "mode": q.life.degraded_mode.value,
                          "in_flight_descriptors": q.vq.in_flight_descriptors, "pending": q.vq.pending,
                          "depth_limit": q.vq.depth_limit} for n, q in self.queues.items()}
            stalls = [self.stalls.check(n, q.vq.pending) for n, q in self.queues.items()]
            for s in stalls:
                self.metrics.set("stalled", 1.0 if s["stalled"] else 0.0, queue=s["queue"])
            for n, q in self.queues.items():
                for m in DegradedMode:
                    self.metrics.set("queue_mode", 1.0 if m is q.life.degraded_mode else 0.0, queue=n, mode=m.value)
            doc = status_document(
                version=self.version, config_digest=self.config.active.digest,
                config_generation=self.config.active.generation, queues=queues,
                dependencies={"key_service": "ok" if self.keyring.available else "unavailable",
                              "time_service": "ok" if self.authority.time_trusted else "untrusted",
                              "control_plane": "reachable" if self.control_plane_reachable else "unreachable",
                              "pk_core": _pk_core_state()},
                capabilities=["descriptor_validation", "tenant_quota", "idempotent_submit", "quarantine",
                              "config_rollback", "audit_chain", "trace_context"],
                saturation=self.quota.saturation(), stalls=stalls)
            self.metrics.set("ready", 1.0 if doc["ready"] else 0.0)
            return doc

    # -- intermittent / offline control plane (C018, C089) -------------------
    def control_plane_lost(self, elapsed_s: float) -> list[dict[str, Any]]:
        """Apply the configured offline policy once the grace period has elapsed.

        The bulk datapath never depends on control-plane reachability for safety:
        descriptor validation uses only locally registered regions.  Within the
        grace period queues keep serving on last-good config (DEGRADED/
        control_plane_unreachable); beyond it the policy decides.
        """
        c = self.config.active.values
        self.control_plane_reachable = False
        changes = []
        with self._lock:
            for name, q in self.queues.items():
                if q.life.state not in (State.SERVING, State.DEGRADED):
                    continue
                if elapsed_s <= c["offline_grace_s"] or c["offline_policy"] == "serve_last_good":
                    if q.life.state is State.SERVING:
                        changes.append(q.life.transition(State.DEGRADED, reason="control plane unreachable",
                                                         actor="runtime", mode=DegradedMode.CONTROL_PLANE_UNREACHABLE))
                elif c["offline_policy"] == "freeze":
                    changes.append(q.life.transition(State.FROZEN, reason="offline grace exceeded", actor="runtime"))
                else:
                    changes.append(q.life.transition(State.QUARANTINED, reason="offline grace exceeded", actor="runtime"))
            for rec in changes:
                self.journal.append({"op": "lifecycle", "queue": rec["queue"], "to": rec["to"], "mode": rec["mode"],
                                     "epoch": rec["epoch"]})
                self.audit.append("offline.policy", queue=rec["queue"], to=rec["to"])
        return changes

    def control_plane_restored(self) -> list[dict[str, Any]]:
        self.control_plane_reachable = True
        out = []
        with self._lock:
            for q in self.queues.values():
                if q.life.state is State.DEGRADED and q.life.degraded_mode is DegradedMode.CONTROL_PLANE_UNREACHABLE:
                    out.append(q.life.transition(State.SERVING, reason="control plane restored", actor="runtime"))
        return out

    def explain(self, queue: str | None = None) -> str:
        return explain(self.decisions, queue=queue)

    # -- crash consistency (C057) -------------------------------------------
    def snapshot_journal(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(e) for e in self.journal]

    @classmethod
    def recover(cls, journal: list[dict[str, Any]], *, keyring: KeyRing, regions: dict[str, tuple[MemoryRegion, ...]]) -> "Runtime":
        """Rebuild queue ownership and reservations after a restart.

        Replays register/submit/complete/lifecycle records in order.  A queue that
        was QUARANTINED or DISABLED before the crash comes back in the same state;
        a queue that was SERVING comes back FROZEN so an operator (or the owning
        controller at a higher epoch) must explicitly resume it.
        """
        rt = cls(keyring=keyring)
        for e in journal:
            kind = e["op"]
            if kind == "register":
                vq = VirtQueue(e["queue"], regions[e["queue"]], depth_limit=e["depth_limit"], chain_limit=e["chain_limit"],
                               byte_limit=e["byte_limit"])
                rt.queues[e["queue"]] = _Queue(e["tenant"], vq, Lifecycle(e["queue"]))
            elif kind == "submit":
                q = rt.queues[e["queue"]]
                with q.vq._lock:
                    q.vq.in_flight += 1
                    q.vq.pending += 1
                    q.vq.in_flight_descriptors += e["descriptors"]
                    q.vq._submitted_sizes.append(e["descriptors"])
                q.reservations.append(e["descriptors"])
                rt.quota.used[q.tenant] = rt.quota.used.get(q.tenant, 0) + e["descriptors"]
                if e.get("idem"):
                    rt.idem.put(q.tenant, e["idem"], e["result"])
            elif kind == "complete":
                q = rt.queues[e["queue"]]
                q.vq.complete(guest_wants_notification=True)
                rt.quota.release(q.tenant, q.reservations.pop(0))
            elif kind == "lifecycle":
                q = rt.queues[e["queue"]]
                q.life.state = State(e["to"])
                q.life.degraded_mode = DegradedMode(e["mode"])
                q.life.controller_epoch = e["epoch"]
        for q in rt.queues.values():
            if q.life.state in (State.SERVING, State.DEGRADED, State.STARTING):
                q.life.state = State.FROZEN
                q.life.history.append({"queue": q.vq.name, "from": "recovered", "to": "frozen",
                                       "reason": "restart recovery", "actor": "runtime", "at": time.time()})
        rt.journal = [dict(e) for e in journal]
        rt.audit.append("runtime.recovered", records=len(journal), queues=sorted(rt.queues))
        return rt


def _pk_core_state() -> str:
    import importlib.util
    return "available" if importlib.util.find_spec("pk_core") else "unavailable"


class ControlPlane:
    """Orchestration channel: queue registration, lifecycle, config, quarantine."""

    def __init__(self, rt: Runtime) -> None:
        self.rt = rt

    def negotiate(self, offer: dict[str, list[int]]) -> dict[str, int]:
        return negotiate(offer)

    def register_queue(self, token: str, *, tenant: str, queue: str, regions: tuple[MemoryRegion, ...],
                       epoch: int = 1, actor: str = "controller") -> dict[str, Any]:
        rt = self.rt
        rt._auth(token, "register_memory", tenant, queue, None)
        c = rt.config.active.values
        with rt._lock:
            if queue in rt.queues:
                owner = rt.queues[queue].tenant
                raise Inv35Error("INV35-E305" if owner != tenant else "INV35-E400", f"queue {queue} already registered")
            if sum(1 for q in rt.queues.values() if q.tenant == tenant) >= c["max_queues_per_tenant"]:
                raise Inv35Error("INV35-E201", f"{tenant} queue count limit")
            vq = VirtQueue(queue, tuple(regions), depth_limit=c["queue_depth"], chain_limit=c["max_chain"],
                           byte_limit=c["max_chain_bytes"])
            life = Lifecycle(queue)
            life.claim(epoch, actor)
            rt.queues[queue] = _Queue(tenant, vq, life)
            rt.journal.append({"op": "register", "queue": queue, "tenant": tenant, "depth_limit": vq.depth_limit,
                               "chain_limit": vq.chain_limit, "byte_limit": vq.byte_limit})
            for target, why in ((State.STARTING, "registered"), (State.SERVING, "regions validated")):
                rec = life.transition(target, reason=why, actor=actor, epoch=epoch)
                rt.journal.append({"op": "lifecycle", "queue": queue, "to": rec["to"], "mode": rec["mode"], "epoch": epoch})
            rt.audit.append("queue.registered", tenant=tenant, queue=queue,
                            regions=[(r.base, r.length) for r in regions], epoch=epoch)
            rt._decide("register", "success", "INV35-E000", "control.register", None, tenant=tenant, queue=queue)
            return {"queue": queue, "tenant": tenant, "state": life.state.value, "epoch": epoch}

    def transition(self, token: str, *, tenant: str, queue: str, target: State, reason: str, actor: str,
                   epoch: int, mode: DegradedMode | None = None) -> dict[str, Any]:
        rt = self.rt
        action = "quarantine" if target in (State.QUARANTINED, State.DISABLED) else "lifecycle"
        rt._auth(token, action, tenant, queue, None)
        with rt._lock:
            q = rt.queues.get(queue)
            if q is None or q.tenant != tenant:
                raise Inv35Error("INV35-E305", f"{queue} is not owned by {tenant}")
            rec = q.life.transition(target, reason=reason, actor=actor, epoch=epoch, mode=mode)
            rt.journal.append({"op": "lifecycle", "queue": queue, "to": rec["to"], "mode": rec["mode"], "epoch": epoch})
            rt.audit.append("queue.transition", **{k: v for k, v in rec.items() if k != "at"})
            rt._decide("lifecycle", "success", "INV35-E000", f"{rec['from']}->{rec['to']}", None, queue=queue, reason=reason)
            return rec

    def claim(self, token: str, *, tenant: str, queue: str, epoch: int, actor: str) -> None:
        self.rt._auth(token, "lifecycle", tenant, queue, None)
        with self.rt._lock:
            q = self.rt.queues[queue]
            q.life.claim(epoch, actor)
            self.rt.audit.append("queue.claimed", queue=queue, epoch=epoch, actor=actor)

    def apply_config(self, token: str, *, tenant: str, queue: str, environment: dict[str, Any] | None = None,
                     site: dict[str, Any] | None = None, profile: str = "datacenter", author: str = "operator"):
        rt = self.rt
        rt._auth(token, "configure", tenant, queue, None)
        values, prov = build_config(profile=profile, environment=environment, site=site, source="control-plane", author=author)
        with rt._lock:
            snap = rt.config.apply(values, prov)
            rt._rebuild_policy()
            rt.audit.append("config.applied", generation=snap.generation, digest=snap.digest, author=author)
            return snap

    def rollback_config(self, token: str, *, tenant: str, queue: str, to_generation: int | None = None):
        rt = self.rt
        rt._auth(token, "configure", tenant, queue, None)
        with rt._lock:
            snap = rt.config.rollback(to_generation=to_generation)
            rt._rebuild_policy()
            rt.audit.append("config.rolled_back", generation=snap.generation, digest=snap.digest)
            return snap

    def status(self, token: str, *, tenant: str, queue: str) -> dict[str, Any]:
        self.rt._auth(token, "read_status", tenant, queue, None)
        return self.rt.status()


class Datapath:
    """Bulk-data channel: submit and complete only."""

    def __init__(self, rt: Runtime) -> None:
        self.rt = rt

    def submit(self, token: str, *, tenant: str, queue: str, chain: Mapping[object, object], head: object,
               idempotency_key: str | None = None, deadline: Deadline | None = None,
               cancel: CancelToken | None = None, traceparent: str | None = None) -> dict[str, Any]:
        rt = self.rt
        trace = TraceContext.parse(traceparent).child()
        started = time.perf_counter()
        q = rt.queues.get(queue)
        if q is None:
            raise Inv35Error("INV35-E403", f"unknown queue {queue}")
        q.life.require_admitting()
        rt._auth(token, "submit", tenant, queue, trace)
        if q.tenant != tenant:
            rt.audit.append("isolation.refused", tenant=tenant, queue=queue)
            raise Inv35Error("INV35-E305", f"{queue} belongs to another tenant")
        if cancel is not None and cancel.cancelled:
            raise Inv35Error("INV35-E204")
        if deadline is not None:
            deadline.check(rt.clock)
        rt.breaker.before()
        if idempotency_key is not None:
            prior = rt.idem.get(tenant, idempotency_key)
            if prior is not None:
                rt.metrics.inc("idempotent_replays", queue=queue)
                return {**prior, "replayed": True}
        with rt._lock:
            try:
                result = q.vq.submit(chain, head)
            except (DescriptorInvalid, QueueFull) as exc:
                code = classify_model_error(exc)
                outcome = "refused"
                rt.metrics.inc("descriptors_validated", outcome="refused", code=code)
                if code == "INV35-E105":
                    rt.metrics.inc("bounds_violations", queue=queue)
                if code in ("INV35-E102", "INV35-E103"):
                    rt.metrics.inc("chain_violations", queue=queue)
                if code.startswith("INV35-E1"):
                    rt.audit.append("descriptor.refused", tenant=tenant, queue=queue, code=code)
                rt._decide("submit", outcome, code, "io_model.validate", trace, tenant=tenant, queue=queue)
                raise Inv35Error(code, str(exc), queue=queue) from exc
            try:
                rt.quota.admit(tenant, result["descriptor_count"])
            except Inv35Error as exc:
                _unreserve_last(q.vq, result["descriptor_count"])
                rt._decide("submit", "refused", exc.code, "quota", trace, tenant=tenant, queue=queue)
                raise
            q.reservations.append(result["descriptor_count"])
            degraded = q.life.state is State.DEGRADED
            result = {**result, "code": "INV35-E001" if degraded else "INV35-E000",
                      "trace_id": trace.trace_id, "idempotency_key": idempotency_key}
            rt.journal.append({"op": "submit", "queue": queue, "descriptors": result["descriptor_count"],
                               "idem": idempotency_key, "result": result})
            if idempotency_key is not None:
                rt.idem.put(tenant, idempotency_key, result)
            rt.metrics.inc("descriptors_validated", result["descriptor_count"], outcome="accepted", code="INV35-E000")
            rt.metrics.set("queue_depth", q.vq.in_flight_descriptors, queue=queue)
            rt.metrics.set("saturation", rt.quota.saturation())
        rt.metrics.observe_us("submit_latency_us", (time.perf_counter() - started) * 1e6, queue=queue)
        return result

    def complete(self, token: str, *, tenant: str, queue: str, guest_wants_notification: bool,
                 traceparent: str | None = None) -> dict[str, Any]:
        rt = self.rt
        trace = TraceContext.parse(traceparent).child()
        q = rt.queues.get(queue)
        if q is None:
            raise Inv35Error("INV35-E403", f"unknown queue {queue}")
        q.life.require_completing()
        rt._auth(token, "complete", tenant, queue, trace)
        if q.tenant != tenant:
            raise Inv35Error("INV35-E305", f"{queue} belongs to another tenant")
        with rt._lock:
            force_notify = (not rt.config.active.values["notification_suppression"]
                            or q.life.degraded_mode is DegradedMode.NO_SUPPRESSION)
            try:
                result = q.vq.complete(guest_wants_notification=guest_wants_notification or force_notify)
            except RuntimeError as exc:
                raise Inv35Error("INV35-E205", str(exc)) from exc
            released = q.reservations.pop(0)
            rt.quota.release(tenant, released)
            rt.journal.append({"op": "complete", "queue": queue})
            rt.stalls.progress(queue)
            if not result["notified"]:
                rt.metrics.inc("suppressed_notifications", queue=queue)
            rt.metrics.set("queue_depth", q.vq.in_flight_descriptors, queue=queue)
            rt.breaker.record(True)
            return {**result, "trace_id": trace.trace_id}


def _unreserve_last(vq: VirtQueue, count: int) -> None:
    """Roll back the reservation io_model just made (quota refused after validation)."""
    with vq._lock:
        vq._submitted_sizes.pop()
        vq.in_flight -= 1
        vq.pending -= 1
        vq.in_flight_descriptors -= count
