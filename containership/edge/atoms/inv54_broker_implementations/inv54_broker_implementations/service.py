"""BrokerService: the production-profile façade that composes the reference brokers with
identity, capability checks, tenant isolation, quotas, admission control, bounded
backlogs, lifecycle, audit, telemetry, health and degraded modes.

Isolation model (component 39): every tenant gets its *own* broker instances; there is no
shared structure through which one tenant's data or offsets can be reached by another.
"""
from __future__ import annotations

import json
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable

from . import __version__
from .brokers import PartitionedLog
from .errors import (BACKLOG_FULL, INVALID_ARGUMENT, NOT_FOUND, OFFSET_OUT_OF_RANGE, BrokerError, Outcome, Result,
                     classify)
from .lifecycle import Lifecycle, State
from .quota import QuotaManager, QuotaSpec, saturation
from .resilience import AdmissionController, Deadline, IdempotencyCache
from .security import Authorizer, AuditLog, HmacAuthenticator, Principal, check_name
from .telemetry import Decision, DecisionLog, Metrics, StructuredLogger, TraceContext, build_lineage


@dataclass
class _Subscriber:
    backlog: deque
    limit: int
    delivered: int = 0
    dropped: int = 0
    last_progress: float = 0.0


@dataclass
class _Tenant:
    subscribers: dict[str, dict[str, _Subscriber]] = field(default_factory=dict)  # topic -> name -> sub
    logs: dict[str, PartitionedLog] = field(default_factory=dict)                 # stream -> log
    last_poll: dict[tuple[str, str, int], float] = field(default_factory=dict)


class BrokerService:
    def __init__(self, *, authenticator: HmacAuthenticator, authorizer: Authorizer, audit: AuditLog,
                 limits: dict[str, Any] | None = None, quotas: QuotaManager | None = None,
                 clock: Callable[[], float] = time.monotonic, logger: StructuredLogger | None = None,
                 metrics: Metrics | None = None) -> None:
        lim = {"partitions": 4, "max_message_bytes": 1_048_576, "max_subscribers_per_tenant": 1000,
               "max_backlog_per_subscriber": 10_000, "max_log_records_per_partition": 1_000_000,
               "max_inflight": 1024, "overflow_policy": "reject"}
        lim.update(limits or {})
        self.limits = lim
        self.authn, self.authz, self.audit = authenticator, authorizer, audit
        self.quotas = quotas or QuotaManager(QuotaSpec())
        self.clock = clock
        self.metrics = metrics or Metrics()
        self.log = logger or StructuredLogger()
        self.decisions = DecisionLog()
        self.admission = AdmissionController(lim["max_inflight"])
        self.idem = IdempotencyCache()
        self.lifecycle = Lifecycle(self._on_transition)
        self.degraded_reasons: set[str] = set()
        self.quarantined_tenants: set[str] = set()
        self.dependencies: dict[str, Callable[[], bool]] = {}
        self._tenants: dict[str, _Tenant] = {}
        self._lock = RLock()
        self.config_digest = "unset"

    # ------------------------------------------------------------------ lifecycle
    def _on_transition(self, frm: State, to: State, reason: str) -> None:
        self.metrics.inc("lifecycle_transitions", to=to.value)
        self.log.log("INFO", "lifecycle.transition", from_state=frm.value, to_state=to.value, reason=reason)
        self.audit.record("system", "*", "lifecycle", to.value, "allow", reason)

    def start(self, config_digest: str = "unset") -> None:
        self.config_digest = config_digest
        self.lifecycle.transition(State.CONFIGURED, "config applied")
        self.lifecycle.transition(State.STARTING, "start requested")
        self.lifecycle.transition(State.READY if self._deps_ok() else State.DEGRADED, "start complete")

    def drain(self) -> None:
        self.lifecycle.transition(State.DRAINING, "drain requested")

    def stop(self) -> None:
        if self.lifecycle.state is not State.DRAINING:
            self.drain()
        self.lifecycle.transition(State.STOPPED, "stopped")

    def _deps_ok(self) -> bool:
        ok = True
        for name, probe in self.dependencies.items():
            try:
                good = bool(probe())
            except Exception:
                good = False
            if not good:
                self.degraded_reasons.add(f"dependency:{name}")
                ok = False
            else:
                self.degraded_reasons.discard(f"dependency:{name}")
        return ok

    def reevaluate(self) -> State:
        s = self.lifecycle.state
        ok = self._deps_ok()
        if s is State.READY and not ok:
            self.lifecycle.transition(State.DEGRADED, ",".join(sorted(self.degraded_reasons)))
        elif s is State.DEGRADED and ok:
            self.lifecycle.transition(State.READY, "dependencies recovered")
        return self.lifecycle.state

    # ------------------------------------------------------------------ quarantine (58)
    def quarantine_tenant(self, token: str, tenant: str, reason: str) -> None:
        p = self._auth(token, "admin", tenant, "*", "quarantine")
        self.quarantined_tenants.add(tenant)
        self.audit.record(p.subject, tenant, "quarantine", tenant, "allow", reason)

    def release_tenant(self, token: str, tenant: str, reason: str) -> None:
        p = self._auth(token, "admin", tenant, "*", "release")
        self.quarantined_tenants.discard(tenant)
        self.audit.record(p.subject, tenant, "release", tenant, "allow", reason)

    # ------------------------------------------------------------------ security glue
    def _auth(self, token: str, action: str, tenant: str, resource: str, op: str,
              request_id: str | None = None) -> Principal:
        rid = request_id or secrets.token_hex(8)
        try:
            p = self.authn.authenticate(token)
            why = self.authz.check(p, action, tenant, resource)
        except BrokerError as e:
            self.metrics.inc("authz_denied", action=action, code=e.code.code)
            self.audit.record("unknown", tenant, action, resource, "deny", e.code.code)
            self.decisions.add(Decision(self.clock(), rid, op, tenant, "deny", [e.code.code, e.message]))
            raise
        self.audit.record(p.subject, tenant, action, resource, "allow", why)
        self.decisions.add(Decision(self.clock(), rid, op, tenant, "allow", [why], {"resource": resource}))
        return p

    def _tenant(self, t: str) -> _Tenant:
        with self._lock:
            return self._tenants.setdefault(t, _Tenant())

    def _admit_write(self, tenant: str) -> None:
        self.lifecycle.require_writable()
        if tenant in self.quarantined_tenants:
            from .errors import QUARANTINED
            raise BrokerError(QUARANTINED, "tenant quarantined", tenant=tenant)

    @staticmethod
    def _size(msg: Any) -> int:
        try:
            return len(json.dumps(msg, separators=(",", ":")).encode())
        except Exception as exc:
            raise BrokerError(INVALID_ARGUMENT, "message must be JSON-serialisable") from exc

    # ------------------------------------------------------------------ fan-out API
    def subscribe(self, token: str, tenant: str, topic: str, name: str) -> None:
        check_name(topic, "topic"), check_name(name, "subscriber")
        self._auth(token, "subscribe", tenant, topic, "subscribe")
        t = self._tenant(tenant)
        with self._lock:
            total = sum(len(s) for s in t.subscribers.values())
            subs = t.subscribers.setdefault(topic, {})
            if name not in subs and total >= self.limits["max_subscribers_per_tenant"]:
                raise BrokerError(BACKLOG_FULL, "subscriber ceiling reached", tenant=tenant)
            subs.setdefault(name, _Subscriber(deque(), self.limits["max_backlog_per_subscriber"],
                                              last_progress=self.clock()))

    def publish(self, token: str, tenant: str, topic: str, msg: Any, *, idempotency_key: str | None = None,
                deadline: Deadline | None = None, priority: int = 5, trace: TraceContext | None = None) -> Result:
        check_name(topic, "topic")
        p = self._auth(token, "publish", tenant, topic, "publish")
        self._admit_write(tenant)
        if deadline:
            deadline.check()
        size = self._size(msg)
        if size > self.limits["max_message_bytes"]:
            raise BrokerError(INVALID_ARGUMENT, "message exceeds max_message_bytes", size=size)
        ikey = f"{tenant}/{topic}/{idempotency_key}" if idempotency_key else None

        def do() -> Result:
            self.admission.acquire(priority)
            try:
                self.quotas.charge(tenant, p.workload, size)
                return self._fanout(tenant, topic, msg)
            finally:
                self.admission.release()

        t0 = time.perf_counter()
        res, dup = self.idem.get_or_run(ikey, do)
        self.metrics.observe("publish_latency_s", time.perf_counter() - t0, op="fanout")
        self.metrics.inc("published", tenant=tenant, duplicate=str(dup))
        self.log.log("INFO", "publish", trace=trace, tenant=tenant, topic=topic, size=size,
                     outcome=res.outcome.value, duplicate=dup)
        return res

    def _fanout(self, tenant: str, topic: str, msg: Any) -> Result:
        import copy
        t = self._tenant(tenant)
        with self._lock:
            subs = t.subscribers.get(topic, {})
            copies = {n: copy.deepcopy(msg) for n in subs}  # prepared before any mutation
            policy = self.limits["overflow_policy"]
            full = [n for n, s in subs.items() if len(s.backlog) >= s.limit]
            if full and policy == "reject":
                # all-or-nothing: completeness invariant preserved by refusing the whole publish
                self.metrics.inc("backlog_rejects", tenant=tenant)
                raise BrokerError(BACKLOG_FULL, subscribers=",".join(full[:10]))
            res = Result(Outcome.SUCCESS)
            for n, s in subs.items():
                if len(s.backlog) >= s.limit:  # drop_oldest: explicit, counted, reported as DEGRADED
                    s.backlog.popleft()
                    s.dropped += 1
                    res.outcome, res.mode = Outcome.DEGRADED, "drop_oldest"
                    res.failed[n] = {"dropped_oldest": 1}
                s.backlog.append(copies[n])
                res.delivered.append(n)
            if self.lifecycle.state is State.DEGRADED and res.outcome is Outcome.SUCCESS:
                res.outcome, res.mode = Outcome.DEGRADED, ",".join(sorted(self.degraded_reasons))
            return res

    def receive(self, token: str, tenant: str, topic: str, name: str, limit: int = 100) -> list[Any]:
        self._auth(token, "consume", tenant, topic, "receive")
        self.lifecycle.require_readable()
        sub = self._tenant(tenant).subscribers.get(topic, {}).get(name)
        if sub is None:
            raise BrokerError(NOT_FOUND, "no such subscriber", topic=topic, subscriber=name)
        with self._lock:
            out = [sub.backlog.popleft() for _ in range(min(limit, len(sub.backlog)))]
            if out:
                sub.delivered += len(out)
                sub.last_progress = self.clock()
            return out

    # ------------------------------------------------------------------ log API
    def _stream(self, tenant: str, stream: str) -> PartitionedLog:
        t = self._tenant(tenant)
        with self._lock:
            if stream not in t.logs:
                t.logs[stream] = PartitionedLog(self.limits["partitions"])
            return t.logs[stream]

    def append(self, token: str, tenant: str, stream: str, key: str, msg: Any, *,
               idempotency_key: str | None = None, priority: int = 5) -> tuple[int, int]:
        check_name(stream, "stream")
        p = self._auth(token, "publish", tenant, stream, "append")
        self._admit_write(tenant)
        size = self._size(msg)
        if size > self.limits["max_message_bytes"]:
            raise BrokerError(INVALID_ARGUMENT, "message exceeds max_message_bytes", size=size)
        log = self._stream(tenant, stream)
        ikey = f"{tenant}/{stream}/{idempotency_key}" if idempotency_key else None

        def do() -> tuple[int, int]:
            self.admission.acquire(priority)
            try:
                part = log.partition_for(key)
                if log.end_offset(part) >= self.limits["max_log_records_per_partition"]:
                    raise BrokerError(BACKLOG_FULL, "partition at record ceiling", partition=part)
                self.quotas.charge(tenant, p.workload, size)
                return log.append(key, msg)
            finally:
                self.admission.release()

        t0 = time.perf_counter()
        res, _ = self.idem.get_or_run(ikey, do)
        self.metrics.observe("append_latency_s", time.perf_counter() - t0)
        self.metrics.inc("appended", tenant=tenant, partition=str(res[0]))
        return res

    def poll(self, token: str, tenant: str, stream: str, consumer: str, partition: int, limit: int = 100):
        check_name(consumer, "consumer")
        self._auth(token, "consume", tenant, stream, "poll")
        self.lifecycle.require_readable()
        log = self._stream(tenant, stream)
        try:
            batch = log.poll(consumer, partition, limit)
        except Exception as exc:
            raise classify(exc) from exc
        self._tenant(tenant).last_poll[(stream, consumer, partition)] = self.clock()
        self.metrics.set("consumer_lag", log.end_offset(partition) - log.committed_offset(consumer, partition),
                         tenant=tenant, consumer=consumer)
        return batch

    def seek(self, token: str, tenant: str, stream: str, consumer: str, partition: int, offset: int) -> None:
        self._auth(token, "seek", tenant, stream, "seek")
        log = self._stream(tenant, stream)
        try:
            log.seek(consumer, partition, offset)
        except IndexError as exc:
            raise BrokerError(OFFSET_OUT_OF_RANGE, str(exc)) from exc
        except Exception as exc:
            raise classify(exc) from exc
        self.metrics.inc("replays", tenant=tenant)

    # ------------------------------------------------------------------ health (52, 72)
    def stalls(self, stall_after_s: float) -> list[dict[str, Any]]:
        """Consumers with backlog whose position has not advanced within ``stall_after_s``."""
        now = self.clock()
        out = []
        for tname, t in self._tenants.items():
            for topic, subs in t.subscribers.items():
                for n, s in subs.items():
                    if s.backlog and now - s.last_progress > stall_after_s:
                        out.append({"tenant": tname, "topic": topic, "subscriber": n, "backlog": len(s.backlog),
                                    "idle_s": round(now - s.last_progress, 3)})
            for (stream, consumer, part), ts in t.last_poll.items():
                log = t.logs[stream]
                lag = log.end_offset(part) - log.committed_offset(consumer, part)
                if lag and now - ts > stall_after_s:
                    out.append({"tenant": tname, "stream": stream, "consumer": consumer, "partition": part,
                                "lag": lag, "idle_s": round(now - ts, 3)})
        return out

    def health(self, stall_after_s: float = 60.0) -> dict[str, Any]:
        self.reevaluate() if self.lifecycle.state in (State.READY, State.DEGRADED) else None
        backlog = max((len(s.backlog) for t in self._tenants.values() for subs in t.subscribers.values()
                       for s in subs.values()), default=0)
        sat = saturation(self.admission.inflight, self.admission.max_inflight, backlog,
                         self.limits["max_backlog_per_subscriber"])
        stalls = self.stalls(stall_after_s)
        state = self.lifecycle.state
        return {
            "schema": "inv54.health/1",
            "live": state not in (State.FAILED, State.STOPPED),
            "ready": state in (State.READY, State.DEGRADED) and sat["state"] != "saturated",
            "state": state.value,
            "version": __version__,
            "config_digest": self.config_digest,
            "degraded_reasons": sorted(self.degraded_reasons),
            "dependencies": {k: (f"dependency:{k}" not in self.degraded_reasons) for k in self.dependencies},
            "saturation": sat,
            "stalls": stalls,
            "quarantined_tenants": sorted(self.quarantined_tenants),
            "admission_shed": self.admission.shed_count,
            "audit_head": self.audit.head,
            "lineage": build_lineage(),
        }


class OfflineBuffer:
    """Client-side store-and-forward for intermittent links (component 9).

    Bounded; each entry carries an idempotency key so a flush that is retried after a
    partial send cannot duplicate effects on the broker (at-least-once transport,
    effectively-once effect).  Overflow is explicit: ``reject`` or ``drop_oldest`` + counter.
    """

    def __init__(self, capacity: int = 10_000, policy: str = "reject") -> None:
        if policy not in ("reject", "drop_oldest"):
            raise BrokerError(INVALID_ARGUMENT, "policy must be reject|drop_oldest")
        self.capacity, self.policy = capacity, policy
        self.q: deque[tuple[str, dict[str, Any]]] = deque()
        self.dropped = 0

    def put(self, idem_key: str, request: dict[str, Any]) -> None:
        if len(self.q) >= self.capacity:
            if self.policy == "reject":
                raise BrokerError(BACKLOG_FULL, "offline buffer full")
            self.q.popleft()
            self.dropped += 1
        self.q.append((idem_key, request))

    def flush(self, send: Callable[[str, dict[str, Any]], Any]) -> int:
        sent = 0
        while self.q:
            key, req = self.q[0]
            try:
                send(key, req)
            except BrokerError as e:
                if e.retryable:
                    break  # link still down: keep order, stop
                self.q.popleft()  # terminal: drop and surface via counter
                self.dropped += 1
                continue
            self.q.popleft()
            sent += 1
        return sent
