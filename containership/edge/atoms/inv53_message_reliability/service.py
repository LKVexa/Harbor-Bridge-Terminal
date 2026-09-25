"""INV-53 broker service layer (components 8, 33, 35, 39-43, 46, 49, 53, 60, 65).

``Broker.handle(request)`` is the only data-path entry point.  Order of checks
(normative, docs/spec/CONSTRAINT_PRECEDENCE.md):

1. schema / version validation            -> E_VALIDATION / E_PROTOCOL_VERSION
2. authentication (secure default: on)    -> E_UNAUTHENTICATED / E_SECURITY_DEPENDENCY
3. authorization (capability grant)       -> E_FORBIDDEN
4. emergency disable / freeze / drain     -> E_FROZEN / E_DRAINING
5. circuit breaker (storage)              -> E_CIRCUIT_OPEN
6. tenant quota (token bucket)            -> E_QUOTA
7. load shedding (ready-depth watermark)  -> E_SHED  (puts only; consumers keep draining)
8. the queue operation itself             -> OK / E_CAPACITY / E_LEASE_STALE / ...

Safety beats availability: every security-dependency failure refuses; every
refusal happens before any state change and carries a decision reason.
"""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping

from . import protocol
from .config import validate as validate_config, digest as config_digest
from .durable import CorruptStoreError, DurableQueue, EpochFencedError, OwnershipError, StorageError
from .errors import Outcome
from .observability import Metrics, StructuredLogger, child_span, decision_event, parse_traceparent, traceparent
from .reliability import DuplicateMessageError, QueueCapacityError, ReliabilityError
from .security import (AuditLog, AuthenticationError, AuthorizationError, Authenticator, Authorizer,
                       SecurityDependencyError)

OP_ACTION = {"put": "produce", "receive": "consume", "ack": "consume", "nack": "consume", "extend": "consume",
             "redrive": "redrive", "health": "consume", "explain": "read_dlq"}
WRITE_OPS = {"put", "receive", "ack", "nack", "extend", "redrive"}


def backoff(attempt: int, *, base: float = 0.1, cap: float = 30.0, rng: Callable[[], float] = random.random) -> float:
    """Full-jitter exponential backoff (component 40): uniform in [0, min(cap, base*2^attempt)]."""
    if attempt < 0:
        raise ValueError("attempt must be >= 0")
    return rng() * min(cap, base * (2 ** min(attempt, 32)))


@dataclass
class TokenBucket:
    rate: float
    burst: int
    tokens: float = -1.0
    stamp: float | None = None

    def peek(self, now: float) -> bool:
        """Would ``take`` succeed?  Changes nothing."""
        if self.stamp is None:
            return self.burst >= 1
        elapsed = max(0.0, now - self.stamp)
        return min(float(self.burst), self.tokens + elapsed * self.rate) >= 1.0

    def take(self, now: float) -> bool:
        if self.stamp is None:
            self.tokens, self.stamp = float(self.burst), now
        elapsed = max(0.0, now - self.stamp)          # a clock going backwards grants nothing
        self.tokens = min(float(self.burst), self.tokens + elapsed * self.rate)
        self.stamp = max(self.stamp, now)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


@dataclass
class Breaker:
    threshold: int
    reset: float
    failures: int = 0
    opened_at: float | None = None
    half_open_probe: bool = False

    def allow(self, now: float) -> bool:
        if self.opened_at is None:
            return True
        if now - self.opened_at >= self.reset and not self.half_open_probe:
            self.half_open_probe = True
            return True
        return False

    def success(self) -> None:
        self.failures, self.opened_at, self.half_open_probe = 0, None, False

    def failure(self, now: float) -> None:
        self.failures += 1
        self.half_open_probe = False
        if self.failures >= self.threshold or self.opened_at is not None:
            self.opened_at = now

    @property
    def state(self) -> str:
        return "closed" if self.opened_at is None else ("half_open" if self.half_open_probe else "open")


@dataclass
class _QueueCtl:
    q: DurableQueue
    breaker: Breaker
    last_progress: float
    frozen: str | None = None
    ops: dict[str, int] = field(default_factory=dict)


class Broker:
    def __init__(self, root: str | os.PathLike, *, config: Mapping[str, Any] | None = None,
                 authenticator: Authenticator | None = None, authorizer: Authorizer | None = None,
                 audit: AuditLog | None = None, metrics: Metrics | None = None,
                 logger: StructuredLogger | None = None, clock: Callable[[], float] = time.time,
                 max_queues_per_tenant: int = 64, fault: Callable[[str, str], None] | None = None) -> None:
        self.cfg = validate_config(config or {})
        self.cfg_digest = config_digest(self.cfg)
        if self.cfg["require_authentication"] and authenticator is None:
            raise ValueError("require_authentication is on (secure default) but no authenticator was supplied")
        if self.cfg["audit_required"] and audit is None:
            raise ValueError("audit_required is on (secure default) but no audit log was supplied")
        self.root = Path(root)
        self.authn, self.authz = authenticator, authorizer or Authorizer()
        self.audit, self.metrics = audit, metrics or Metrics()
        self.log = logger or StructuredLogger(open(os.devnull, "w"))
        self.clock = clock
        self.max_queues = max_queues_per_tenant
        self._fault = fault
        self._queues: dict[tuple[str, str], _QueueCtl] = {}
        self._buckets: dict[str, TokenBucket] = {}
        self._frozen_tenants: dict[str, str] = {}
        self.disabled: str | None = None
        self.draining = False
        self._lock = RLock()

    # --------------------------------------------------------------- plumbing
    def _audit(self, event: str, **fields: Any) -> None:
        if self.audit is None:
            return
        self.audit.append(event, **fields)          # raises SecurityDependencyError -> fail closed

    def _ctl(self, tenant: str, queue: str, *, create: bool) -> _QueueCtl | None:
        key = (tenant, queue)
        ctl = self._queues.get(key)
        if ctl is None:
            # A store persisted by an earlier process must be reopened for every op, not only put:
            # otherwise a restarted broker would answer OK_EMPTY while messages sit on disk.
            exists = (self.root / "tenants" / tenant / queue / "journal.jsonl").exists()
            if not (create or exists):
                return None
            if sum(1 for t, _ in self._queues if t == tenant) >= self.max_queues:
                raise QueueCapacityError(f"tenant {tenant!r} queue limit reached ({self.max_queues})")
            ctl = _QueueCtl(self._open(tenant, queue),
                            Breaker(self.cfg["breaker_failure_threshold"], self.cfg["breaker_reset_seconds"]),
                            last_progress=self.clock())
            self._queues[key] = ctl
        return ctl

    def _open(self, tenant: str, queue: str) -> DurableQueue:
        c = self.cfg
        return DurableQueue(self.root / "tenants" / tenant / queue, visibility=c["visibility_seconds"],
                            max_attempts=c["max_attempts"], max_ready=c["max_ready"],
                            max_in_flight=c["max_in_flight"], max_dead_letters=c["max_dead_letters"],
                            max_message_bytes=c["max_message_bytes"], fsync=c["fsync"], fault=self._fault)

    def _refuse(self, code: str, reason: str, op: str, tenant: str = "-", **data: Any) -> dict:
        self.metrics.inc("inv53_refusals_total", op=op, code=code)
        ev = decision_event(op, code, reason, tenant=tenant)
        self.log.log("warning", "refused", **ev)
        out = Outcome(code, reason, data)
        if out.retryable:
            data.setdefault("retry_after", round(backoff(1), 3))
        return protocol.response(out.to_dict())

    # ------------------------------------------------------------------ admin
    def freeze(self, tenant: str, queue: str | None = None, *, reason: str, actor: str) -> None:
        with self._lock:
            self._audit("freeze", tenant=tenant, queue=queue or "*", reason=reason, actor=actor)
            if queue is None:
                self._frozen_tenants[tenant] = reason
            else:
                self._ctl(tenant, queue, create=True).frozen = reason

    def unfreeze(self, tenant: str, queue: str | None = None, *, actor: str) -> None:
        with self._lock:
            self._audit("unfreeze", tenant=tenant, queue=queue or "*", actor=actor)
            if queue is None:
                self._frozen_tenants.pop(tenant, None)
            elif (tenant, queue) in self._queues:
                self._queues[(tenant, queue)].frozen = None

    def emergency_disable(self, *, reason: str, actor: str) -> None:
        with self._lock:
            self._audit("emergency_disable", reason=reason, actor=actor)
            self.disabled = reason

    def emergency_enable(self, *, actor: str) -> None:
        with self._lock:
            self._audit("emergency_enable", actor=actor)
            self.disabled = None

    def drain(self, *, actor: str) -> dict[str, Any]:
        """Stop admitting puts; consumers keep settling.  Returns remaining work."""
        with self._lock:
            self._audit("drain", actor=actor)
            self.draining = True
            return {f"{t}/{q}": c.q.snapshot() for (t, q), c in self._queues.items()}

    def shutdown(self, *, actor: str) -> None:
        with self._lock:
            self.draining = True
            self._audit("shutdown", actor=actor)
            for c in self._queues.values():
                c.q.close()
            self._queues.clear()

    # ----------------------------------------------------------------- health
    def mode(self) -> str:
        if self.disabled:
            return "DISABLED"
        if self.draining:
            return "DRAINING"
        if any(c.breaker.state != "closed" for c in self._queues.values()):
            return "DEGRADED_STORAGE"
        if any(self._shedding(c) for c in self._queues.values()):
            return "DEGRADED_SHEDDING"
        return "NORMAL"

    def _shedding(self, c: _QueueCtl) -> bool:
        return c.q.snapshot()["ready"] >= self.cfg["shed_ready_ratio"] * self.cfg["max_ready"]

    def health(self, *, now: float | None = None, tenant: str | None = None) -> dict[str, Any]:
        """Operator view of every queue; with ``tenant`` (the wire op) only that tenant's queues."""
        now = self.clock() if now is None else now
        with self._lock:
            queues = {}
            for (t, q), c in self._queues.items():
                if tenant is not None and t != tenant:
                    continue
                s = c.q.snapshot()
                stalled = s["ready"] > 0 and now - c.last_progress > self.cfg["stall_seconds"]
                queues[f"{t}/{q}"] = {**s, "breaker": c.breaker.state, "frozen": bool(c.frozen), "stalled": stalled}
                for k in ("ready", "in_flight", "dead_lettered"):
                    self.metrics.set(f"inv53_{k}", s[k], tenant=t, queue=q)
            mode = self.mode()
            ready = mode in ("NORMAL", "DEGRADED_SHEDDING") and not any(v["stalled"] for v in queues.values())
            out = {"live": True, "ready": ready, "mode": mode, "queues": queues}
            if tenant is None:        # deployment-wide facts are for operators, not tenants
                out.update({"config_digest": self.cfg_digest, "audit_head": self.audit.head() if self.audit else None})
            return out

    # -------------------------------------------------------------- data path
    def handle(self, request: Any) -> dict[str, Any]:
        t0 = time.perf_counter()
        op = request.get("op", "?") if isinstance(request, Mapping) else "?"
        try:
            return self._handle(request)
        except SecurityDependencyError as exc:
            return self._refuse("E_SECURITY_DEPENDENCY", str(exc), op)
        except Exception as exc:  # never leak a traceback across the boundary
            self.log.log("error", "internal_error", op=op, error=type(exc).__name__)
            return self._refuse("E_INTERNAL", type(exc).__name__, op)
        finally:
            if op in protocol.OPS:
                self.metrics.observe("inv53_op_seconds", time.perf_counter() - t0, op=op)

    def _handle(self, request: Any) -> dict[str, Any]:
        try:
            req = protocol.validate_request(request)
        except protocol.ProtocolError as exc:
            return self._refuse(exc.code, str(exc), "?")
        op, tenant, queue = req["op"], req["tenant"], req["queue"]
        trace = child_span(parse_traceparent(req.get("traceparent")))
        wall = self.clock()

        principal = "anonymous"
        if self.cfg["require_authentication"] or "auth" in req:
            try:
                principal = self.authn.authenticate(req, now=wall)
            except AuthenticationError as exc:
                self._audit("authn_denied", op=op, tenant=tenant, queue=queue, reason=str(exc))
                return self._refuse("E_UNAUTHENTICATED", "authentication failed", op, tenant)
        try:
            self.authz.check(principal, tenant, queue, OP_ACTION[op])
        except AuthorizationError:
            self._audit("authz_denied", principal=principal, op=op, tenant=tenant, queue=queue)
            return self._refuse("E_FORBIDDEN", "not permitted", op, tenant)

        with self._lock:
            # Every refusal below is decided before any state is created or consumed.
            if self.disabled:
                return self._refuse("E_FROZEN", f"emergency disabled: {self.disabled}", op, tenant)
            if tenant in self._frozen_tenants:
                return self._refuse("E_FROZEN", "tenant frozen", op, tenant)
            if op == "health":
                return protocol.response(Outcome("OK").to_dict(), health=self.health(tenant=tenant))
            if op == "put" and self.draining:
                return self._refuse("E_DRAINING", "draining; not admitting new work", op, tenant)
            try:
                ctl = self._ctl(tenant, queue, create=False)
            except CorruptStoreError as exc:
                return self._refuse("E_CORRUPT", str(exc), op, tenant)
            except OwnershipError as exc:
                return self._refuse("E_EPOCH_FENCED", str(exc), op, tenant)
            if ctl is None:
                if op == "explain":
                    return protocol.response(Outcome("OK").to_dict(), explain={"id": req["id"], "state": "unknown_or_settled"})
                if op != "put":
                    return protocol.response(Outcome("OK_EMPTY" if op == "receive" else "E_LEASE_STALE",
                                                     "no such queue").to_dict())
                if sum(1 for t, _ in self._queues if t == tenant) >= self.max_queues:
                    return self._refuse("E_CAPACITY", f"tenant queue limit reached ({self.max_queues})", op, tenant)
            else:
                if ctl.frozen:
                    return self._refuse("E_FROZEN", "queue frozen", op, tenant)
                if op == "explain":
                    return protocol.response(Outcome("OK").to_dict(), explain=ctl.q.explain(req["id"]))
                if op == "put" and self._shedding(ctl):
                    return self._refuse("E_SHED", "ready depth above shed watermark", op, tenant)
            bucket = self._buckets.setdefault(tenant, TokenBucket(self.cfg["tenant_rate_per_second"], self.cfg["tenant_burst"]))
            if not bucket.peek(wall):
                return self._refuse("E_QUOTA", "tenant rate limit", op, tenant)
            if ctl is not None and op in WRITE_OPS and not ctl.breaker.allow(wall):
                return self._refuse("E_CIRCUIT_OPEN", "storage breaker open", op, tenant)
            bucket.take(wall)
            if ctl is None:
                try:
                    ctl = self._ctl(tenant, queue, create=True)
                except (CorruptStoreError, OwnershipError, QueueCapacityError) as exc:
                    return self._refuse("E_INTERNAL", type(exc).__name__, op, tenant)
            try:
                out = self._op(ctl, req, trace)
            except (StorageError, EpochFencedError) as exc:
                ctl.breaker.failure(wall)
                self._recover(tenant, queue, ctl)
                code = "E_EPOCH_FENCED" if isinstance(exc, EpochFencedError) else "E_STORAGE"
                return self._refuse(code, str(exc), op, tenant)
            except CorruptStoreError as exc:
                ctl.frozen = "corrupt"
                return self._refuse("E_CORRUPT", str(exc), op, tenant)
            except QueueCapacityError as exc:
                return self._refuse("E_CAPACITY", str(exc), op, tenant)
            except DuplicateMessageError as exc:
                return self._refuse("E_DUPLICATE_ACTIVE", str(exc), op, tenant)
            except ReliabilityError as exc:
                return self._refuse("E_INTERNAL", str(exc), op, tenant)
            if op in WRITE_OPS:
                ctl.breaker.success()
            ctl.ops[op] = ctl.ops.get(op, 0) + 1
            self.metrics.inc("inv53_ops_total", op=op, tenant=tenant, code=out["outcome"]["code"])
            self.log.log("info", "op", trace=trace, op=op, tenant=tenant, queue=queue,
                         code=out["outcome"]["code"], principal=principal)
            return out

    def _recover(self, tenant: str, queue: str, ctl: _QueueCtl) -> None:
        """After a write failure the queue fail-stopped; reopen it so replay decides the truth."""
        try:
            ctl.q.close()
        except Exception:
            pass
        try:
            ctl.q = self._open(tenant, queue)
        except Exception as exc:
            ctl.frozen = f"recovery failed: {type(exc).__name__}"

    def _op(self, ctl: _QueueCtl, req: dict, trace: dict) -> dict:
        op, q = req["op"], ctl.q
        # Lease time is the broker's clock.  A client-supplied ``now`` is accepted for wire
        # compatibility but never trusted: it would let a caller expire someone else's lease.
        now = self.clock()
        if op == "put":
            msg = dict(req["message"])
            if req.get("traceparent"):
                headers = dict(msg.get("headers") or {})
                headers.setdefault("traceparent", traceparent(trace))
                msg["headers"] = headers
            new = q.put(msg)
            return protocol.response(Outcome("OK" if new else "OK_DUPLICATE").to_dict())
        if op == "receive":
            d = q.receive(now=now)
            if d is None:
                return protocol.response(Outcome("OK_EMPTY").to_dict())
            return protocol.response(Outcome("OK").to_dict(), delivery={"message": d.message, "lease": d.lease_id,
                                                                         "deadline": d.deadline, "attempt": d.attempt})
        if op == "ack":
            ok = q.ack(req["id"], req["lease"], now=now)
            if ok:
                ctl.last_progress = now
            return protocol.response(Outcome("OK" if ok else "E_LEASE_STALE", "" if ok else "lease not current").to_dict())
        if op == "nack":
            ok = q.nack(req["id"], lease_id=req["lease"], now=now, requeue=req.get("requeue", True),
                        reason=req.get("reason", "negative_acknowledgement"))
            if ok:
                ctl.last_progress = now
            return protocol.response(Outcome("OK" if ok else "E_LEASE_STALE").to_dict())
        if op == "extend":
            if req["extension"] > self.cfg["max_lease_extension_seconds"]:
                raise QueueCapacityError("extension exceeds max_lease_extension_seconds")
            d = q.extend_visibility(req["id"], lease_id=req["lease"], now=now, extension=req["extension"])
            if d is None:
                return protocol.response(Outcome("E_LEASE_STALE").to_dict())
            return protocol.response(Outcome("OK", data={"deadline": d.deadline}).to_dict())
        if op == "redrive":
            self._audit("redrive", tenant=req["tenant"], queue=req["queue"], id=req["id"])
            ok = q.redrive(req["id"], now=now)
            return protocol.response(Outcome("OK" if ok else "E_VALIDATION", "" if ok else "no such dead letter").to_dict())
        raise ReliabilityError(f"unhandled op {op}")
