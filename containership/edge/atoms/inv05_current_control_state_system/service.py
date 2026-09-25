"""INV-05 control-state service facade.

Request pipeline (identical for every transport):

    admission (serving state / freeze / quarantine / break-glass)
      -> rate limit + concurrency gate          (MC-020-06, MC-021-04)
      -> authorization (deny by default)        (MC-023-03)
      -> deadline / cancellation check          (MC-026)
      -> namespace mapping (server-side)        (MC-021-02)
      -> engine operation                       (store.py)
      -> metrics, trace span, structured log, explain record, audit (MC-032..038)

Authentication happens in the transport (mTLS peer cert or bearer token) and
yields a :class:`Principal`; nothing below the transport trusts client-supplied
identity or key prefixes.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from . import __version__
from .audit import AuditLog
from .errors import (
    Cancelled, DeadlineExceeded, FailedClosed, Frozen, InvalidArgument, LeaseNotFound, PermissionDenied,
    StateError, Unavailable,
)
from .limits import ConcurrencyGate, Limits, TokenBucket
from .observability import ExplainStore, Metrics, NullStream, StructuredLogger, Tracer
from .schema import CAPABILITIES, PROTOCOL, PROTOCOL_MAJOR, PROTOCOL_MINOR, check_message, negotiate, parse_compare, parse_op
from .security import CLUSTER, Authorizer, Namespace, Principal
from .store import ControlStore, Delete, Put, Range, TxnResult
from .watch import WatchHub, Watcher

BUILD_INFO = {"version": __version__, "commit": os.environ.get("INV05_BUILD_COMMIT", "unknown"),
              "schema": f"{PROTOCOL}/{PROTOCOL_MAJOR}.{PROTOCOL_MINOR}", "event_schema": "cstate.event/1",
              "backend": "inv05-local-mvcc/1"}

# MC-026-01/04: deadline classes and retry classification per operation
OP_CLASSES: dict[str, dict[str, Any]] = {
    "range":    {"default_ms": 5000, "max_ms": 30000, "retry": "idempotent"},
    "txn":      {"default_ms": 5000, "max_ms": 30000, "retry": "token-idempotent (request_id) else conditional"},
    "compact":  {"default_ms": 30000, "max_ms": 120000, "retry": "idempotent"},
    "lease_grant": {"default_ms": 5000, "max_ms": 10000, "retry": "non-retryable (creates a new lease)"},
    "lease_keepalive": {"default_ms": 2000, "max_ms": 5000, "retry": "idempotent"},
    "lease_revoke": {"default_ms": 5000, "max_ms": 10000, "retry": "idempotent (LEASE_NOT_FOUND on repeat)"},
    "watch":    {"default_ms": 0, "max_ms": 0, "retry": "resume from resume_revision"},
    "admin":    {"default_ms": 10000, "max_ms": 60000, "retry": "idempotent"},
}


class CancelToken:
    def __init__(self) -> None:
        self._ev = threading.Event()

    def cancel(self) -> None:
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()


@dataclass
class Controls:
    """Operator controls (MC-031).  All changes are audited."""
    freeze_reads: str = ""
    freeze_writes: str = ""
    freeze_admin: str = ""
    freeze_watches: str = ""
    quarantined: str = ""
    maintenance: str = ""
    break_glass: str = ""
    draining: bool = False

    def active(self) -> dict[str, str]:
        return {k: v for k, v in self.__dict__.items() if v}


@dataclass
class RequestContext:
    principal: Principal
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    deadline: float = 0.0            # absolute monotonic; 0 == class default
    traceparent: str | None = None
    cancel: CancelToken | None = None
    attempt: int = 1


class ControlStateService:
    def __init__(self, store: ControlStore, *, audit: AuditLog, authorizer: Authorizer | None = None,
                 metrics: Metrics | None = None, logger: StructuredLogger | None = None,
                 tracer: Tracer | None = None, config_hash: str = "", site_epoch: int = 1,
                 durable: Any = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.store = store
        self.durable = durable
        self.limits: Limits = store.limits
        self.audit = audit
        self.metrics = metrics or Metrics()
        self.log = logger or StructuredLogger(NullStream())
        self.tracer = tracer or Tracer(0.0)
        self.explain = ExplainStore()
        self.authz = authorizer or Authorizer()
        self.authz.on_decision = self._on_decision
        self.hub = WatchHub(store)
        self.controls = Controls()
        self.config_hash = config_hash
        self.site_epoch = site_epoch
        self.role = "primary"
        self.clock = clock
        self.bootstrapped = False
        self._rate = TokenBucket(self.limits.rate_per_identity_rps, self.limits.burst_per_identity, clock)
        self._gate = ConcurrencyGate(self.limits.max_inflight_requests)
        self._heartbeat = clock()
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None
        self.compactor: Any = None

    # ------------------------------------------------------------------ helpers
    def _on_decision(self, d: Any) -> None:
        if not d.allowed:
            self.metrics.inc("cstate_authz_denials_total", action=d.action)
            self.audit.record("authz", d.action, actor=d.subject_hash, target=d.namespace, outcome="denied",
                              policy_version=d.policy_version, reason=d.reason)
            self.log.log("WARN", "CS2001", "authorization denied", action=d.action, subject=d.subject_hash,
                         policy_version=d.policy_version)

    def _ns(self, ctx: RequestContext, target: Namespace | None) -> Namespace:
        return target or ctx.principal.namespace

    def _deadline(self, ctx: RequestContext, op: str, deadline_ms: int | None = None) -> float:
        cls = OP_CLASSES[op]
        if deadline_ms is not None:
            if deadline_ms <= 0:
                raise InvalidArgument("deadline_ms must be positive", field="deadline_ms")
            deadline_ms = min(deadline_ms, cls["max_ms"])
        ms = deadline_ms or cls["default_ms"]
        d = self.clock() + ms / 1000.0 if ms else 0.0
        if ctx.deadline:
            d = min(d, ctx.deadline) if d else ctx.deadline
        return d

    def _check_live(self, ctx: RequestContext, deadline: float) -> None:
        if ctx.cancel and ctx.cancel.cancelled:
            raise Cancelled("request cancelled by caller")
        if deadline and self.clock() > deadline:
            raise DeadlineExceeded("deadline exceeded before execution")

    def _admit(self, kind: str) -> None:
        c = self.controls
        is_admin = kind.startswith("admin")
        if self.store.failed and not is_admin:
            raise FailedClosed(f"store failed closed: {self.store.failed_reason}", reason="failed")
        if c.break_glass and not is_admin:
            raise Frozen("service emergency-disabled", reason="break_glass")
        if c.quarantined and not is_admin:
            raise Frozen("node quarantined", reason="quarantine")
        if c.draining and kind in ("write", "watch", "read"):
            from .errors import Draining
            raise Draining("node draining")
        reason = {"read": c.freeze_reads, "write": c.freeze_writes or c.maintenance, "admin": c.freeze_admin,
                  "watch": c.freeze_watches}.get(kind, "")
        if reason:
            raise Frozen(f"{kind} admission frozen: {reason}", reason=reason[:64])
        if kind == "write" and self.role != "primary":
            raise Unavailable("this site is a read-only replica", reason="replica")

    @contextmanager
    def _request(self, ctx: RequestContext, op: str, kind: str, action: str,
                 target: Namespace | None = None, key: str = "") -> Iterator[Any]:
        t0 = time.perf_counter()
        result = "ok"
        with self.tracer.span(f"cstate.{op}", ctx.traceparent, op=op, attempt=ctx.attempt) as sp:
            try:
                self._admit(kind)
                self._rate.take(ctx.principal.subject)
                with self._gate:
                    self.metrics.set("cstate_inflight_requests", self._gate.inflight)
                    with self.tracer.span("cstate.authz", op=op):
                        decision = self.authz.require(ctx.principal, action, target, key)
                    sp.set(policy_version=decision.policy_version)
                    yield sp
            except StateError as exc:
                result = exc.spec.category
                sp.set(code=exc.code)
                self.log.log("INFO", "CS1101", "request failed", op=op, code=exc.code,
                             request_id=ctx.request_id, subject=ctx.principal.subject_hash)
                raise
            except Exception:
                result = "internal"
                self.log.log("ERROR", "CS1101", "internal error", op=op, request_id=ctx.request_id)
                raise
            finally:
                dt = time.perf_counter() - t0
                self.metrics.inc("cstate_requests_total", op=op, result=result)
                self.metrics.observe("cstate_request_duration_seconds", dt, op=op)
                if ctx.attempt > 1:
                    self.metrics.inc("cstate_retries_total", op=op)
                sp.set(result=result)

    # ------------------------------------------------------------------ namespacing
    @staticmethod
    def _map_key(ns: Namespace, key: str) -> str:
        if not isinstance(key, str):
            raise InvalidArgument("key must be a string", field="key")
        return ns.prefix + key

    def _map_op(self, ns: Namespace, op: Any) -> Any:
        if isinstance(op, Put):
            if not op.key:
                raise InvalidArgument("put.key must be non-empty", field="put.key")
            return Put(self._map_key(ns, op.key), op.value, op.lease)
        if isinstance(op, Delete):
            if not op.key and not op.prefix:
                raise InvalidArgument("delete.key required", field="delete.key")
            return Delete(self._map_key(ns, op.key), op.prefix)
        if isinstance(op, Range):
            return Range(self._map_key(ns, op.key), self._map_key(ns, op.range_end) if op.range_end else "",
                         op.prefix or not op.key and not op.range_end, op.revision, op.limit, op.page_token)
        return op

    @staticmethod
    def _strip(ns: Namespace, d: dict[str, Any]) -> dict[str, Any]:
        if "key" in d and isinstance(d["key"], str) and d["key"].startswith(ns.prefix):
            d = dict(d)
            d["key"] = d["key"][len(ns.prefix):]
        return d

    def _strip_range(self, ns: Namespace, r: dict[str, Any]) -> dict[str, Any]:
        r = dict(r)
        r["kvs"] = [self._strip(ns, kv) for kv in r["kvs"]]
        return r

    def _check_lease_owner(self, ctx: RequestContext, lease_id: int) -> None:
        if not lease_id:
            return
        lease = self.store.lease_get(lease_id)
        if lease.owner != ctx.principal.subject:
            raise PermissionDenied("lease owned by another identity", reason="lease_owner")

    # ------------------------------------------------------------------ data plane
    def txn(self, ctx: RequestContext, body: dict[str, Any], target: Namespace | None = None) -> dict[str, Any]:
        msg = check_message("txn", body)
        compares = [parse_compare(c) for c in msg.get("compare", [])]
        success = [parse_op(o) for o in msg.get("success", [])]
        failure = [parse_op(o) for o in msg.get("failure", [])]
        writes = any(isinstance(o, (Put, Delete)) for o in success + failure)
        action = "write" if writes else "read"
        if any(isinstance(o, Delete) for o in success + failure):
            action = "delete" if not any(isinstance(o, Put) for o in success + failure) else "write"
        ns = self._ns(ctx, target)
        with self._request(ctx, "txn", "write" if writes else "read", action, target) as sp:
            deadline = self._deadline(ctx, "txn", msg.get("deadline_ms"))
            for o in success + failure:
                if isinstance(o, Put):
                    self._check_lease_owner(ctx, o.lease)
            mcmp = []
            for c in compares:
                if c.target == "FENCE":
                    self._check_lease_owner(ctx, int(c.key[6:]) if c.key[6:].isdigit() else 0)
                    mcmp.append(c)
                else:
                    mcmp.append(type(c)(self._map_key(ns, c.key), c.target, c.op, c.operand))
            self._check_live(ctx, deadline)
            with self.tracer.span("cstate.txn.evaluate", op="txn"):
                res: TxnResult = self.store.txn(mcmp, [self._map_op(ns, o) for o in success],
                                                [self._map_op(ns, o) for o in failure],
                                                request_id=(f"{ctx.principal.subject}|{msg['request_id']}"
                                                            if msg.get("request_id") else ""),
                                                txn_id=ctx.request_id, actor=ctx.principal.subject_hash)
            out = res.to_dict()
            out["responses"] = [({"range": self._strip_range(ns, r["range"])} if "range" in r else r)
                                for r in out["responses"]]
            sp.set(revision=res.revision, branch="success" if res.succeeded else "failure")
            if not res.succeeded:
                self.metrics.inc("cstate_txn_conflicts_total")
            self.explain.add({"request_id": ctx.request_id, "op": "txn", "subject": ctx.principal.subject_hash,
                              "namespace": ns.label(), "read_revision": res.revision - (1 if writes and res.succeeded else 0),
                              "result_revision": res.revision,
                              "predicates": [{"key": c.key, "target": c.target, "op": c.op, "held": h}
                                             for c, h in zip(compares, res.compare_results)],
                              "branch": "success" if res.succeeded else "failure",
                              "policy_version": self.authz.policy.version, "config_sha256": self.config_hash,
                              "build": BUILD_INFO["version"], "outcome": "committed" if writes else "read"})
            if writes and res.revision:
                self.audit.record("mutation", "txn", actor=ctx.principal.subject_hash, target=ns.label(),
                                  outcome="success" if res.succeeded else "compare_failed",
                                  request_id=ctx.request_id, revision=res.revision)
            return out

    def range(self, ctx: RequestContext, body: dict[str, Any], target: Namespace | None = None) -> dict[str, Any]:
        msg = check_message("range", body)
        ns = self._ns(ctx, target)
        with self._request(ctx, "range", "read", "read", target) as sp:
            deadline = self._deadline(ctx, "range", msg.get("deadline_ms"))
            self._check_live(ctx, deadline)
            r = self._map_op(ns, Range(msg["key"], msg.get("range_end", ""), msg.get("prefix", False),
                                       msg.get("revision", 0), msg.get("limit", 0), msg.get("page_token", "")))
            res = self.store.range(r).to_dict()
            sp.set(revision=res["revision"])
            return self._strip_range(ns, res)

    def watch(self, ctx: RequestContext, body: dict[str, Any], target: Namespace | None = None) -> Watcher:
        msg = check_message("watch", body)
        ns = self._ns(ctx, target)
        kinds = msg.get("kinds")
        if kinds and not set(kinds) <= {"CREATE", "UPDATE", "DELETE", "EXPIRE"}:
            raise InvalidArgument("unknown event kind", field="kinds")
        with self._request(ctx, "watch", "watch", "watch", target):
            return self.hub.create(prefix=ns.prefix + msg.get("prefix", ""),
                                   start_revision=msg.get("start_revision", 0), owner=ctx.principal.subject,
                                   kinds=set(kinds) if kinds else None, with_prev=msg.get("prev_value", False),
                                   transform=lambda d: self._strip(ns, d))

    def compact(self, ctx: RequestContext, body: dict[str, Any]) -> dict[str, Any]:
        msg = check_message("compact", body)
        with self._request(ctx, "compact", "admin", "compact", CLUSTER):
            with self.tracer.span("cstate.compaction", op="compact", revision=msg["revision"]):
                dropped = self.store.compact(msg["revision"])
            self.audit.record("compaction", "compact", actor=ctx.principal.subject_hash, request_id=ctx.request_id,
                              revision=msg["revision"], dropped=dropped, operator_override=True)
            self.log.log("INFO", "CS1300", "compaction completed", revision=msg["revision"], dropped=dropped)
            return {"compact_revision": self.store.compact_revision, "dropped": dropped}

    def lease_grant(self, ctx: RequestContext, body: dict[str, Any]) -> dict[str, Any]:
        msg = check_message("lease_grant", body)
        with self._request(ctx, "lease_grant", "write", "lease"):
            l = self.store.lease_grant(msg["ttl"], owner=ctx.principal.subject)
            self.audit.record("lease", "grant", actor=ctx.principal.subject_hash, target=str(l.id),
                              request_id=ctx.request_id, ttl=l.ttl)
            return {"id": l.id, "ttl": l.ttl, "fence": l.fence, "remaining_s": l.ttl}

    def lease_keepalive(self, ctx: RequestContext, body: dict[str, Any]) -> dict[str, Any]:
        msg = check_message("lease_keepalive", body)
        with self._request(ctx, "lease_keepalive", "write", "lease"):
            self._check_lease_owner(ctx, msg["id"])
            l = self.store.lease_keepalive(msg["id"])
            return {"id": l.id, "ttl": l.ttl, "fence": l.fence, "remaining_s": round(l.remaining(self.store.clock()), 3)}

    def lease_revoke(self, ctx: RequestContext, body: dict[str, Any]) -> dict[str, Any]:
        msg = check_message("lease_revoke", body)
        with self._request(ctx, "lease_revoke", "write", "lease"):
            self._check_lease_owner(ctx, msg["id"])
            n = self.store.lease_revoke(msg["id"])
            self.audit.record("lease", "revoke", actor=ctx.principal.subject_hash, target=str(msg["id"]),
                              request_id=ctx.request_id, deleted=n)
            return {"id": msg["id"], "deleted": n}

    def hello(self, body: dict[str, Any]) -> dict[str, Any]:
        return negotiate(body)

    # ------------------------------------------------------------------ admin (MC-031)
    def _admin(self, ctx: RequestContext, action: str, what: str, **detail: Any) -> None:
        self.metrics.inc("cstate_admin_ops_total", action=action)
        self.audit.record("admin", what, actor=ctx.principal.subject_hash, request_id=ctx.request_id, **detail)
        self.log.log("WARN", "CS2002", "admin action", action=what, subject=ctx.principal.subject_hash,
                     **{k: v for k, v in detail.items() if isinstance(v, (str, int, bool))})

    def freeze(self, ctx: RequestContext, scope: str, reason: str) -> dict[str, str]:
        if scope not in ("reads", "writes", "admin", "watches"):
            raise InvalidArgument("scope must be reads|writes|admin|watches", field="scope")
        if not reason:
            raise InvalidArgument("reason required", field="reason")
        with self._request(ctx, "admin", "admin" if scope != "admin" else "admin_unfreezable", "admin.freeze"):
            setattr(self.controls, f"freeze_{scope}", reason[:200])
            self._admin(ctx, "admin.freeze", f"freeze.{scope}", reason=reason)
            return self.controls.active()

    def unfreeze(self, ctx: RequestContext, scope: str) -> dict[str, str]:
        with self._request(ctx, "admin", "admin_unfreezable", "admin.freeze"):
            setattr(self.controls, f"freeze_{scope}", "")
            self._admin(ctx, "admin.freeze", f"unfreeze.{scope}")
            return self.controls.active()

    def drain(self, ctx: RequestContext, grace_s: float = 5.0) -> dict[str, Any]:
        with self._request(ctx, "admin", "admin", "admin.drain"):
            self.controls.draining = True
            n = self.hub.drain(min(grace_s, 60.0))
            self._admin(ctx, "admin.drain", "drain", watches=n)
            return {"drained_watches": n}

    def quarantine(self, ctx: RequestContext, reason: str) -> dict[str, str]:
        """Stop serving without destroying state or evidence (MC-031-04)."""
        with self._request(ctx, "admin", "admin", "admin.quarantine"):
            self.controls.quarantined = reason[:200] or "quarantined"
            self.hub.drain(1.0)
            self.hub.draining = False
            self._admin(ctx, "admin.quarantine", "quarantine", reason=reason)
            return self.controls.active()

    def maintenance(self, ctx: RequestContext, enter: bool, reason: str = "") -> dict[str, Any]:
        with self._request(ctx, "admin", "admin", "admin.maintenance"):
            if enter:
                self.controls.maintenance = reason[:200] or "maintenance"
            else:
                problems = self.store.check_invariants()
                if problems or self.store.failed:  # explicit exit criteria (MC-031-05)
                    raise Unavailable("maintenance exit criteria not met", reason="invariants")
                self.controls.maintenance = ""
            self._admin(ctx, "admin.maintenance", "maintenance.enter" if enter else "maintenance.exit", reason=reason)
            return {"controls": self.controls.active()}

    def break_glass(self, ctx: RequestContext, disable: bool, reason: str) -> dict[str, Any]:
        """Emergency disable of the whole data plane (MC-031-06)."""
        if not reason:
            raise InvalidArgument("reason required", field="reason")
        with self._request(ctx, "admin", "admin_unfreezable", "admin.break_glass"):
            self.controls.break_glass = reason[:200] if disable else ""
            self._admin(ctx, "admin.break_glass", "break_glass.disable" if disable else "break_glass.enable",
                        reason=reason)
            self.log.log("CRITICAL", "CS2004", "break-glass control used", disable=disable,
                         subject=ctx.principal.subject_hash)
            return {"controls": self.controls.active()}

    def set_policy(self, ctx: RequestContext, policy_dict: dict[str, Any]) -> str:
        from .security import Policy
        with self._request(ctx, "admin", "admin", "admin.policy"):
            v = self.authz.rollout(Policy.from_dict(policy_dict))
            self.audit.record("policy", "rollout", actor=ctx.principal.subject_hash, target=v)
            self.log.log("WARN", "CS2005", "policy rolled out", version=v)
            return v

    def rollback_policy(self, ctx: RequestContext) -> str:
        with self._request(ctx, "admin", "admin", "admin.policy"):
            v = self.authz.rollback()
            self.audit.record("policy", "rollback", actor=ctx.principal.subject_hash, target=v)
            return v

    def set_log_level(self, ctx: RequestContext, level: str) -> None:
        with self._request(ctx, "admin", "admin", "admin.loglevel"):
            self.log.set_level(level, actor=ctx.principal.subject_hash)
            self.audit.record("config", "log_level", actor=ctx.principal.subject_hash, target=level)

    def get_explanation(self, ctx: RequestContext, request_id: str) -> dict[str, Any] | None:
        with self._request(ctx, "admin", "admin", "admin.explain"):
            return self.explain.get(request_id)

    def read_audit(self, ctx: RequestContext) -> list[dict[str, Any]]:
        with self._request(ctx, "admin", "admin", "admin.audit_read"):
            return self.audit.entries()

    # ------------------------------------------------------------------ health (MC-030)
    def liveness(self) -> dict[str, Any]:
        """Shallow but stall-aware: fails if the store lock cannot be taken or the ticker stalled."""
        got = self.store.lock.acquire(timeout=2.0)
        if got:
            self.store.lock.release()
        stalled = self._ticker is not None and self.clock() - self._heartbeat > 10.0
        ok = got and not stalled
        return {"status": "ok" if ok else "stalled", "lock_acquirable": got, "ticker_stalled": stalled}

    def readiness(self) -> dict[str, Any]:
        reasons = []
        if not self.bootstrapped:
            reasons.append("not_bootstrapped")
        if self.store.failed:
            reasons.append("store_failed")
        for k in ("quarantined", "break_glass", "draining"):
            if getattr(self.controls, k):
                reasons.append(k)
        degraded = [k for k in ("freeze_reads", "freeze_writes", "freeze_watches", "maintenance")
                    if getattr(self.controls, k)]
        if self.role != "primary":
            degraded.append("replica_read_only")
        state = "failed" if self.store.failed else ("not_ready" if reasons else ("degraded" if degraded else "ready"))
        for s in ("ready", "degraded", "not_ready", "failed"):
            self.metrics.set("cstate_state", 1.0 if s == state else 0.0, state=s)
        return {"status": state, "reasons": reasons, "degraded": degraded}

    def version(self) -> dict[str, Any]:
        return {**BUILD_INFO, "capabilities": list(CAPABILITIES), "config_sha256": self.config_hash}

    def diagnostics(self, ctx: RequestContext) -> dict[str, Any]:
        with self._request(ctx, "admin", "admin", "admin.diagnostics"):
            return {"revision": self.store.revision, "compact_revision": self.store.compact_revision,
                    "history": self.store.history_size, "keys": self.store.key_count,
                    "leases": len(self.store.leases()), "watch": self.hub.stats(),
                    "controls": self.controls.active(), "counters": dict(self.store.counters),
                    "role": self.role, "site_epoch": self.site_epoch,
                    "recovery": self.durable.report.to_dict() if self.durable else None,
                    "failed_reason": self.store.failed_reason}

    def refresh_gauges(self) -> None:
        s = self.store
        self.metrics.set("cstate_revision", s.revision)
        self.metrics.set("cstate_compact_revision", s.compact_revision)
        self.metrics.set("cstate_compaction_lag_revisions", s.revision - s.compact_revision)
        self.metrics.set("cstate_history_events", s.history_size)
        self.metrics.set("cstate_keys", s.key_count)
        self.metrics.set("cstate_leases_active", len(s.leases()))
        with self.metrics._lock:
            self.metrics._values["cstate_compacted_refusals_total"][()] = float(s.counters["compacted_refusals"])
            self.metrics._values["cstate_leases_expired_total"][()] = float(s.counters["leases_expired"])
            self.metrics._values["cstate_watch_slow_consumer_cancels_total"][()] = float(
                self.hub.counters["slow_consumer_cancels"])
        st = self.hub.stats()
        self.metrics.set("cstate_watches_active", st["active"])
        self.metrics.set("cstate_watch_backlog_events", st["backlog_total"])
        if self.durable:
            self.metrics.set("cstate_wal_bytes", self.durable.wal.bytes_written)
        self.metrics.sample_process()

    # ------------------------------------------------------------------ background
    def start(self, interval_s: float = 0.5, checkpoint_every: int = 50_000) -> None:
        def loop() -> None:
            while not self._stop.wait(interval_s):
                self._heartbeat = self.clock()
                try:
                    n = self.store.tick()
                    if n:
                        self.log.log("INFO", "CS1400", "leases expired", count=n)
                    if self.compactor:
                        self.compactor.run_once()
                    if self.durable and self.durable.wal.appends >= checkpoint_every:
                        self.durable.checkpoint()
                    self.refresh_gauges()
                except StateError:
                    pass
                except Exception:
                    self.log.log("ERROR", "CS3000", "background loop error")
        self._heartbeat = self.clock()
        self._ticker = threading.Thread(target=loop, name="inv05-ticker", daemon=True)
        self._ticker.start()

    def stop(self) -> None:
        self._stop.set()
        if self._ticker:
            self._ticker.join(timeout=5)
        if self.durable:
            self.durable.close()
        self.log.log("INFO", "CS1002", "service stopped")
