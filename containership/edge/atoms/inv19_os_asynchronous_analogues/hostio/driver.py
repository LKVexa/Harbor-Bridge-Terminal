"""The INV-19 host asynchronous driver: one façade over every MC component.

Order of checks on every operation (security before allocation):
    authorize (MC-15) -> audit (MC-18, fail-closed) -> admission (MC-13)
    -> quota reserve (MC-21) -> op-table allocate -> native submit/register
    -> event -> canonical translation (MC-12) -> future/credit (MC-09/08)
    -> release quota, metrics, trace, log (MC-22)

Readiness backends perform the real syscall after readiness (``ReadinessIO``),
so component-visible outcomes are the same tag set ("value"/"error") on every
backend; readiness itself surfaces only as stream credit.

Health (MC-19): a stall (in-flight ops with no progress for ``health.stall_s``)
or repeated submit failures degrade the backend; ``recover()`` fails in-flight
ops exactly once with cause BACKEND_RECOVERY, reinitialises, and after
``health.max_recoveries`` quarantines the backend and fails over to the next
available one in priority order (admission is stopped during migration and a
minimum dwell prevents flapping).
"""
from __future__ import annotations

import ctypes
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from . import capabilities as capmod
from .audit import AuditLog, AuditUnavailable
from .config import ConfigStore
from .errors import CanonicalError, Code, canonical, translate, untranslatable_errors
from .integration import CreditPool, CreditStream, Future, WaitableSet
from .native_base import BackendClosed, BackendUnavailable, Interest
from .observability import DecisionLog, Logger, Metrics, TraceContext, Tracer
from .ops import OperationTable, OpState, TableFull
from .policy import Admission, CircuitBreaker, Overloaded, deadline_after, expired
from .readiness import Epoll, Kqueue, Portable, ReadinessIO
from .resources import Accountant, Limits, QuotaExceeded
from .security import Authority, Capability, KeyProvider, Unauthorized, pseudonym

RELEASE = "5.0.0"


class Health(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    QUARANTINED = "quarantined"


def _make_backend(name: str, cfg) -> Any:
    try:
        return _open_backend(name, cfg)
    except OSError as exc:  # e.g. EMFILE/ENOMEM at start-up -> reason-coded, never a raw crash
        raise BackendUnavailable(name, translate(name, exc.errno).code, "open failed") from None


def _open_backend(name: str, cfg) -> Any:
    if name == "io_uring":
        from .iouring import IoUring
        return IoUring(cfg["ring.sq_entries"], cfg["ring.cq_entries"])
    if name == "iocp":
        from .iocp import Iocp
        return Iocp()
    if name == "epoll":
        return Epoll(cfg["quota.global_descriptors"], cfg["quota.max_event_batch"])
    if name == "kqueue":
        return Kqueue(cfg["quota.global_descriptors"], cfg["quota.max_event_batch"])
    return Portable(cfg["quota.global_descriptors"], cfg["quota.max_event_batch"])


@dataclass
class _Pending:
    fut: Future
    fd: int
    kind: str
    tenant: str
    workload: str
    reservation: Any
    buf_reservation: Any
    started: float
    trace: TraceContext
    data: bytes = b""
    nbytes: int = 0
    buf: Any = None


class AsyncHost:
    def __init__(self, *, config: ConfigStore | None = None, keys: KeyProvider | None = None,
                 caps: capmod.HostCapabilities | None = None, override: str = "",
                 diagnostic: bool = False, audit: AuditLog | None = None) -> None:
        self.config = config or ConfigStore()
        cfg = self.config.active
        self.keys = keys or KeyProvider()
        if self.keys.active is None:
            self.keys.create("inv19-cap-k1")
        self.authority = Authority(self.keys)
        self.metrics, self.logger, self.tracer, self.decisions = Metrics(), Logger(), Tracer(), DecisionLog()
        self.logger.config_digest = cfg.digest
        self.audit = audit or AuditLog(max_buffer=cfg["audit.max_buffer"],
                                       checkpoint_every=cfg["audit.checkpoint_every"],
                                       config_digest=cfg.digest)
        lim = lambda g, t, w: Limits(g, t, w)  # noqa: E731
        self.accountant = Accountant({
            "inflight_ops": lim(cfg["quota.max_inflight"], cfg["quota.per_tenant_descriptors"],
                                cfg["quota.per_workload_descriptors"]),
            "armed_descriptors": lim(cfg["quota.global_descriptors"], cfg["quota.per_tenant_descriptors"],
                                     cfg["quota.per_workload_descriptors"]),
            "io_buffer_bytes": lim(cfg["quota.buffer_bytes_global"], cfg["quota.buffer_bytes_per_tenant"],
                                   cfg["quota.buffer_bytes_per_workload"]),
            "stream_credits": lim(cfg["quota.global_descriptors"], cfg["quota.per_tenant_descriptors"],
                                  cfg["quota.per_workload_descriptors"]),
        })
        self.admission = Admission(cfg["quota.max_inflight"], cfg["quota.max_inflight"],
                                   cfg["quota.max_inflight"], cfg["quota.per_tenant_descriptors"])
        self.breaker = CircuitBreaker(cfg["breaker.failure_threshold"], cfg["breaker.open_s"])
        self.table = OperationTable(cfg["quota.max_inflight"])
        self.credit_pool = CreditPool(cfg["quota.global_descriptors"])
        self.waitables = WaitableSet(cfg["quota.global_descriptors"])
        self._lock = threading.RLock()
        self._pending: dict[int, _Pending] = {}
        self._fd_busy: dict[int, int] = {}
        self._streams: dict[int, tuple[CreditStream, str, str]] = {}
        self.caps = caps or capmod.detect()
        self.quarantined: set[str] = set()
        self.health = Health.HEALTHY
        self.recoveries = 0
        self.failovers: list[dict] = []
        self._last_progress = time.monotonic()
        self._last_switch = 0.0
        self.min_dwell_s = 1.0
        self.admitting = True
        self._override, self._diagnostic = override, diagnostic
        self._select_and_open(reason="bootstrap")

    # ------------------------------------------------------------------ selection
    def _select_and_open(self, reason: str) -> None:
        cfg = self.config.active
        disabled = list(cfg["backends.disabled"]) + sorted(self.quarantined)
        enabled = set(cfg["backends.enabled"]) | {"portable"}
        disabled += [b for b in capmod.PRIORITY if b not in enabled]
        try:
            sel = capmod.choose(self.caps, disabled=disabled,
                                override=self._override or cfg["backends.diagnostic_override"],
                                diagnostic=self._diagnostic)
        except capmod.SelectionError as exc:
            reasons = ";".join(f"{b}={i.get('reason')}" for b, i in self.caps.backends.items())
            raise BackendUnavailable("selection", "NO_USABLE_BACKEND", f"{exc} [{reasons}]") from None
        try:
            self.backend = _make_backend(sel.backend, cfg)
        except BackendUnavailable as exc:
            self.quarantined.add(sel.backend)
            self.decisions.record("backend-open-failed", sel.backend, {}, {"reason": exc.reason})
            if sel.backend == "portable":
                raise
            self._override = ""
            return self._select_and_open(reason=f"open-failed:{exc.reason}")
        self.selection = sel
        self.name, self.semantics = sel.backend, sel.semantics
        self.rio = ReadinessIO(self.name)
        for b in capmod.PRIORITY:
            self.metrics.set("inv19_backend_selected", 1.0 if b == self.name else 0.0,
                             backend=b, semantics=capmod.SEMANTICS[b])
        if sel.fallback:
            self.metrics.inc("inv19_fallback_engagements_total", reason=reason.split(":")[0][:40] or "bootstrap")
        self.decisions.record("backend-selection", sel.backend,
                              {"caps_digest": sel.caps_digest, "probe": sel.probe_version,
                               "trigger": reason}, {"selected_because": sel.reason, **sel.rejected})
        self.logger.log("backend_selected", backend=self.name, semantics=self.semantics, reason=sel.reason)
        self._set_health(Health.HEALTHY)

    def _set_health(self, h: Health) -> None:
        self.health = h
        for s in Health:
            self.metrics.set("inv19_backend_health", 1.0 if s is h else 0.0, backend=self.name, state=s.value)

    # ------------------------------------------------------------------ helpers
    def mint(self, tenant: str, workload: str, actions=("submit", "reap", "cancel", "arm", "inspect"),
             resource: str = "fd:*", ttl: float = 3600.0) -> Capability:
        return self.authority.mint(tenant, workload, actions, resource, ttl)

    def _authorize(self, cap: Any, action: str, fd: int | None = None, owner=None) -> Capability:
        try:
            c = self.authority.check(cap, action, fd=fd, owner=owner)
        except Unauthorized as exc:
            t = getattr(cap, "tenant", "?")
            w = getattr(cap, "workload", "?")
            try:
                self.audit.emit(action, "denied", actor="caller", tenant=pseudonym(str(t)),
                                workload=pseudonym(str(w)), resource=f"fd:{fd}", error=exc.reason)
            except AuditUnavailable:
                pass
            self.metrics.inc("inv19_errors_total", backend=self.name, code="UNAUTHORIZED")
            raise
        return c

    def _audit_ok(self, action: str, cap: Capability, resource: str, **extra: Any) -> None:
        self.audit.emit(action, "allowed", actor="caller", tenant=pseudonym(cap.tenant),
                        workload=pseudonym(cap.workload), resource=resource, **extra)

    # ------------------------------------------------------------------ operations
    def read(self, cap: Any, fd: int, nbytes: int, *, timeout: float | None = None,
             traceparent: str | None = None) -> Future:
        return self._submit(cap, "read", fd, nbytes=nbytes, timeout=timeout, traceparent=traceparent)

    def write(self, cap: Any, fd: int, data: bytes, *, timeout: float | None = None,
              traceparent: str | None = None) -> Future:
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes")
        return self._submit(cap, "write", fd, data=bytes(data), timeout=timeout, traceparent=traceparent)

    def _submit(self, cap: Any, kind: str, fd: int, *, nbytes: int = 0, data: bytes = b"",
                timeout: float | None, traceparent: str | None) -> Future:
        if isinstance(fd, bool) or not isinstance(fd, int) or fd < 0:
            raise ValueError("invalid descriptor")
        if kind == "read" and (isinstance(nbytes, bool) or not isinstance(nbytes, int) or not 0 < nbytes <= 1 << 24):
            raise ValueError("nbytes must be in (0, 16MiB]")
        c = self._authorize(cap, "submit", fd=fd)
        deadline = deadline_after(timeout if timeout is not None else self.config.active["timeout.default_s"])
        if not self.admitting:
            raise Overloaded("MIGRATING")
        if not self.breaker.allow():
            raise Overloaded("CIRCUIT_OPEN")
        self._audit_ok("submit", c, f"fd:{fd}", op=kind)
        self.admission.admit(c.tenant)
        res = bres = None
        try:
            res = self.accountant.reserve("inflight_ops", 1, tenant=c.tenant, workload=c.workload, backend=self.name)
            bres = self.accountant.reserve("io_buffer_bytes", max(1, nbytes if kind == "read" else len(data)),
                                           tenant=c.tenant, workload=c.workload, backend=self.name)
            ctx = TraceContext.parse(traceparent or "") if traceparent else None
            span = self.tracer.span("inv19.submit", ctx, op=kind, backend=self.name)
            with self._lock:
                if fd in self._fd_busy:
                    raise ValueError(f"descriptor {fd} already has an operation in flight")
                op = self.table.allocate(kind, c.tenant, c.workload, fd, deadline=deadline)
                fut = Future(op.op_id, corr={"trace_id": span.trace_id, "backend": self.name})
                p = _Pending(fut, fd, kind, c.tenant, c.workload, res, bres, time.monotonic(), span, data, nbytes)
                self._pending[op.op_id] = p
                self._fd_busy[fd] = op.op_id
                try:
                    self._native_submit(op.op_id, p)
                    self.table.transition(op.op_id, OpState.INFLIGHT)
                except (OSError, BackendClosed, ValueError, BlockingIOError) as exc:
                    err = translate(self.name, getattr(exc, "errno", None)) if isinstance(exc, OSError) \
                        else canonical(Code.INVALID_ARGUMENT, self.name)
                    self.breaker.failure()
                    self._finish(op.op_id, None, err, OpState.FAILED)
            self.metrics.inc("inv19_submit_total", backend=self.name, op=kind)
            return fut
        except BaseException:
            for r in (res, bres):
                if r is not None and not r.released:
                    self.accountant.release(r)
            self.admission.done(c.tenant)
            raise

    def _native_submit(self, op_id: int, p: _Pending) -> None:
        if self.semantics == "completion" and self.name == "io_uring":
            if p.kind == "read":
                p.buf = (ctypes.c_char * p.nbytes)()
                self.backend.submit("read", p.fd, op_id, buf=p.buf, length=p.nbytes, offset=-1)
            else:
                p.buf = (ctypes.c_char * max(1, len(p.data))).from_buffer_copy(p.data or b"\0")
                self.backend.submit("write", p.fd, op_id, buf=p.buf, length=len(p.data), offset=-1)
        elif self.semantics == "completion":  # pragma: no cover - iocp on Windows
            raise BackendUnavailable(self.name, "HANDLE_MODEL", "IOCP requires handle association")
        else:
            self.backend.register(p.fd, Interest.READ if p.kind == "read" else Interest.WRITE, owner=op_id)

    def _finish(self, op_id: int, value: Any, err: CanonicalError | None, state: OpState,
                cause: str | None = None) -> bool:
        with self._lock:
            p = self._pending.get(op_id)
            if p is None:
                return False
            if not self.table.transition(op_id, state, result=value, error=err):
                return False
            del self._pending[op_id]
            if self._fd_busy.get(p.fd) == op_id:
                del self._fd_busy[p.fd]
            if self.semantics == "readiness":
                try:
                    self.backend.unregister(p.fd)
                except Exception:
                    pass
            self.table.release(op_id)
        self.accountant.release(p.reservation)
        self.accountant.release(p.buf_reservation)
        self.admission.done(p.tenant)
        lat = time.monotonic() - p.started
        self.metrics.observe("inv19_reap_latency_seconds", lat, backend=self.name)
        self._last_progress = time.monotonic()
        if state is OpState.CANCELLED:
            p.fut.cancel(cause or "CALLER")
            self.metrics.inc("inv19_cancel_total", backend=self.name, outcome="cancelled")
        elif err is not None:
            if state is OpState.TIMED_OUT:
                self.metrics.inc("inv19_timeout_total", backend=self.name)
            self.metrics.inc("inv19_errors_total", backend=self.name, code=err.code)
            p.fut.resolve_error(err)
        else:
            self.breaker.success()
            p.fut.resolve_value(value)
        self.metrics.inc("inv19_reap_total", backend=self.name, kind="error" if err else "value")
        self.tracer.span("inv19.resolve", p.trace, state=state.value)
        return True

    def cancel(self, cap: Any, fut: Future, cause: str = "CALLER") -> bool:
        with self._lock:
            p = self._pending.get(fut.op_id)
            if p is None:
                return False
            owner = (p.tenant, p.workload)
        c = self._authorize(cap, "cancel", owner=owner)
        self._audit_ok("cancel", c, f"op:{fut.op_id & 0xFFFFFFFF}")
        if self.name == "io_uring":
            self.backend.cancel(fut.op_id)  # completion may still win; exactly-once via table
        return self._finish(fut.op_id, None, canonical(Code.CANCELLED, self.name), OpState.CANCELLED, cause)

    # ------------------------------------------------------------------ event pump
    def poll(self, timeout: float = 0.0) -> int:
        n = 0
        try:
            if self.semantics == "completion":
                for ev in self.backend.wait(timeout, self.config.active["quota.max_event_batch"]):
                    st = OpState.COMPLETED if ev.error is None else OpState.FAILED
                    p = self._pending.get(ev.op_id)
                    val = ev.result
                    if p is not None and p.kind == "read" and ev.error is None and p.buf is not None:
                        val = bytes(p.buf.raw[: ev.result])
                    n += self._finish(ev.op_id, val, ev.error, st)
            else:
                for ev in self.backend.wait(timeout):
                    op_id = self.backend.regs.owner(ev.fd)
                    if op_id is None:
                        continue
                    p = self._pending.get(op_id)
                    if p is None:
                        continue
                    kind, v = (self.rio.read(p.fd, p.nbytes) if p.kind == "read"
                               else self.rio.write(p.fd, p.data))
                    if kind == "retry":
                        continue  # readiness was only permission; stay armed
                    if kind == "error":
                        n += self._finish(op_id, None, v, OpState.FAILED)
                    else:
                        n += self._finish(op_id, v, None, OpState.COMPLETED)
        except BackendClosed:
            self._set_health(Health.UNHEALTHY)
        n += self._expire()
        self._check_health()
        self._publish_gauges()
        return n

    def _expire(self) -> int:
        n = 0
        now = time.monotonic()
        for op_id, p in list(self._pending.items()):
            op = self.table.lookup(op_id)
            if op is not None and expired(op.deadline, lambda: now):
                if self.name == "io_uring":
                    try:
                        self.backend.cancel(op_id)
                    except Exception:
                        pass
                n += self._finish(op_id, None, canonical(Code.TIMED_OUT, self.name), OpState.TIMED_OUT)
        return n

    def run_until(self, fut: Future, timeout: float = 5.0) -> tuple[str, Any]:
        end = time.monotonic() + timeout
        while not fut.done() and time.monotonic() < end:
            self.poll(0.005)
        return fut.result(0)

    # ------------------------------------------------------------------ streams (INV-17)
    def open_stream(self, cap: Any, fd: int) -> CreditStream:
        c = self._authorize(cap, "arm", fd=fd)
        self._audit_ok("arm", c, f"fd:{fd}")
        r = self.accountant.reserve("stream_credits", 1, tenant=c.tenant, workload=c.workload)
        s = CreditStream(fd, 1, self.credit_pool)
        self._streams[fd] = (s, c.tenant, c.workload)
        s._reservation = r  # type: ignore[attr-defined]
        return s

    def feed_readiness(self, ev) -> None:
        """Map one readiness event onto stream credit (never a completion)."""
        ent = self._streams.get(ev.fd)
        if ent is None:
            return
        s = ent[0]
        if ev.readable or ev.hup or ev.error:
            s.grant("read")   # error/hup: the next read attempt discovers the real outcome
        if ev.writable:
            s.grant("write")

    def close_stream(self, fd: int) -> None:
        ent = self._streams.pop(fd, None)
        if ent:
            ent[0].close()
            self.accountant.release(ent[0]._reservation)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ health / recovery
    def _check_health(self) -> None:
        stall = self.config.active["health.stall_s"]
        if self._pending and time.monotonic() - self._last_progress > stall and self.health is Health.HEALTHY:
            self._set_health(Health.DEGRADED)
            self.logger.log("backend_stall", "WARNING", backend=self.name)
        if self.breaker.state.value == "open" and self.health is not Health.UNHEALTHY:
            self._set_health(Health.UNHEALTHY)

    def recover(self, reason: str) -> dict:
        """Reinitialise (bounded), then quarantine + fail over."""
        with self._lock:
            self.admitting = False
            failed = 0
            for op_id in list(self._pending):
                failed += self._finish(op_id, None, canonical(Code.CANCELLED, self.name),
                                       OpState.CANCELLED, cause="BACKEND_RECOVERY")
            old = self.name
            try:
                self.backend.close()
            except Exception:
                pass
            self.recoveries += 1
            must_move = old in self.quarantined or self.recoveries > self.config.active["health.max_recoveries"]
            if must_move and old != "portable":
                # flapping guard: a quarantined backend stays out until an operator
                # lifts the quarantine (unquarantine), never automatically
                self.quarantined.add(old)
                self._override = ""
                self._select_and_open(reason=f"failover:{reason}")
                self._last_switch = time.monotonic()
                self.failovers.append({"from": old, "to": self.name, "reason": reason, "failed_ops": failed})
                self.recoveries = 0
            else:
                self.backend = _make_backend(old, self.config.active)
                self._set_health(Health.HEALTHY)
            self.admitting = True
            self.decisions.record("recovery", self.name, {"from": old}, {"reason": reason, "failed_ops": failed})
            return {"from": old, "to": self.name, "failed_ops": failed}

    def unquarantine(self, backend: str, actor: str = "operator") -> None:
        """Operator re-enable; takes effect at the next selection, never mid-flight."""
        self.quarantined.discard(backend)
        self.audit.emit("unquarantine", "applied", actor=actor, tenant="-", workload="-", resource=backend)

    def quarantine(self, backend: str, actor: str = "operator") -> None:
        if backend == "portable":
            raise ValueError("portable fallback cannot be quarantined")
        self.quarantined.add(backend)
        self.audit.emit("quarantine", "applied", actor=actor, tenant="-", workload="-", resource=backend)
        if backend == self.name:
            self.recover(f"quarantine:{actor}")

    # ------------------------------------------------------------------ status
    def _publish_gauges(self) -> None:
        for r, u in self.accountant.utilisation().items():
            self.metrics.set("inv19_quota_utilisation_ratio", u, resource=r)
        self.metrics.set("inv19_queue_depth", float(len(self._pending)), backend=self.name, queue="inflight")
        self.metrics.set("inv19_untranslatable_errors_total", float(untranslatable_errors.value), backend=self.name)

    def snapshot(self) -> dict:
        """C071 health/readiness/version/config/dependency/capability view (no secrets)."""
        return {"release": RELEASE, "backend": self.name, "semantics": self.semantics,
                "health": self.health.value, "fallback": self.selection.fallback,
                "selection_reason": self.selection.reason, "rejected": self.selection.rejected,
                "config": self.config.active.provenance(), "inflight": len(self._pending),
                "quarantined": sorted(self.quarantined), "failovers": len(self.failovers),
                "audit_head": self.audit.head, "untranslatable_errors": untranslatable_errors.value,
                "stale_completions": self.table.stale_completions, "lost_races": self.table.lost_races}

    def shutdown(self, timeout: float = 2.0) -> dict:
        self.admitting = False
        end = time.monotonic() + timeout
        while self._pending and time.monotonic() < end:
            self.poll(0.01)
        n = 0
        for op_id in list(self._pending):
            n += self._finish(op_id, None, canonical(Code.CANCELLED, self.name), OpState.CANCELLED, "SHUTDOWN")
        for fd in list(self._streams):
            self.close_stream(fd)
        try:
            self.backend.close()
        except Exception:
            pass
        self.waitables.close()
        return {"cancelled_at_shutdown": n, "accounting_at_baseline": self.accountant.at_baseline()}
