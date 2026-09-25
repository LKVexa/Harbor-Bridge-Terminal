"""Governed runtime around the bare :class:`Future` (C017, C024, C028, C042,
C046, C052, C054, C059, C067, C071, C072, C076).

The runtime hands out *capabilities*, never raw futures:

* ``ResolverCap`` may resolve / resolve_error / abandon -- never take;
* ``ReceiverCap`` may take / wait / cancel -- never resolve;
* ``ObserverCap`` may inspect state -- never mutate or consume;
* ``AdminCap`` (one per runtime, held by the operator) may disable/enable.

Capabilities carry a 128-bit random token checked in constant time, are bound to
one tenant and one future, and cannot be upgraded.  Dropping the last reference
to a ``ResolverCap`` of a pending future abandons it (writer-drop detection).

Constraint precedence (C019, ``POLICY_VERSION``):
    1 disabled/quarantine  2 authentication  3 authorization  4 version
    5 resource limits      6 state machine   7 argument validity
Security and isolation are always evaluated before capacity or performance.
"""
from __future__ import annotations

import collections
import hmac
import itertools
import os
import secrets
import threading
import time
import weakref
from dataclasses import dataclass
from typing import Any, Mapping

from . import future as _f
from .config import ConfigStore
from .errors import ErrorRecord, FutureError, Rejected, from_exception
from .future import Future
from .telemetry import AuditChain, DecisionLog, Metrics, StructuredLog, TraceContext

__all__ = ["Runtime", "ResolverCap", "ReceiverCap", "ObserverCap", "AdminCap", "POLICY_VERSION"]

POLICY_VERSION = "INV18-PREC/1"
COMPONENT_ID = "INV-18"
TOMBSTONES = 16384
HEALTHY, READY, DEGRADED, FAILED = "HEALTHY", "READY", "DEGRADED", "FAILED"


@dataclass(frozen=True, eq=False)
class _Cap:
    future_id: str
    tenant: str
    token: str
    kind: str

    def __repr__(self) -> str:  # never print tokens (C075)
        return f"{type(self).__name__}({self.future_id!r}, tenant={self.tenant!r})"


class ResolverCap(_Cap):
    pass


class ReceiverCap(_Cap):
    pass


class ObserverCap(_Cap):
    pass


@dataclass(frozen=True, eq=False)
class AdminCap:
    runtime_id: str
    token: str

    def __repr__(self) -> str:
        return f"AdminCap({self.runtime_id!r})"


class _Entry:
    __slots__ = ("future", "tenant", "tokens", "created", "resolved_at", "trace", "epoch")

    def __init__(self, fut, tenant, tokens, created, trace, epoch):
        self.future, self.tenant, self.tokens = fut, tenant, tokens
        self.created, self.resolved_at, self.trace, self.epoch = created, None, trace, epoch


class Runtime:
    """Process-local registry of governed futures.  Not durable by design (C057)."""

    def __init__(self, config: ConfigStore | Mapping[str, Any] | None = None, *, clock=time.monotonic,
                 log_sink=None, version: str | None = None):
        from . import __version__ as _v
        self.version = version or _v
        self.runtime_id = "rt-" + secrets.token_hex(6)
        self.epoch = int(time.time_ns())          # boot epoch; fences pre-restart peers
        self.audit = AuditChain()
        self.config = config if isinstance(config, ConfigStore) else ConfigStore(
            config, audit=lambda a, d: self.audit.append(a, **d))
        self.metrics = Metrics()
        c = self.config.values()
        self.log = StructuredLog(component=COMPONENT_ID, version=self.version, maxlen=c["telemetry_queue_max"],
                                 rate_per_s=c["log_rate_limit_per_s"], sink=log_sink, metrics=self.metrics)
        self.decisions = DecisionLog(c["max_diag_records"])
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[str, _Entry] = {}
        self._per_tenant: dict[str, int] = {}
        self._seq = itertools.count(1)
        # bounded tombstones: a still-valid capability of a released future gets the
        # state-machine answer (AlreadyTaken / AlreadyResolved), not PERMISSION_DENIED
        self._tombs: "collections.OrderedDict[str, tuple[str, dict, str]]" = collections.OrderedDict()
        self._disabled: dict[str, str] = {}      # scope -> mode ("drain"|"freeze")
        self._admin = AdminCap(self.runtime_id, secrets.token_hex(16))
        self._dependency_state: dict[str, str] = {"telemetry_sink": "ok", "pk_core": "not-required-at-runtime"}
        self.audit.append("runtime.start", target=self.runtime_id, epoch=self.epoch,
                          config_revision=self.config.active().revision_id)

    # ------------------------------------------------------------------ admin
    def admin_capability(self) -> AdminCap:
        """Issued once to the operator process; not transferable across runtimes."""
        return self._admin

    def _check_admin(self, cap: Any) -> None:
        if not isinstance(cap, AdminCap) or cap.runtime_id != self.runtime_id or \
                not hmac.compare_digest(cap.token, self._admin.token):
            self.audit.append("admin.denied", result="denied")
            self._decide("AUTHZ_REJECTED", "PERMISSION_DENIED")
            raise Rejected("administrative capability required", code="PERMISSION_DENIED")

    def disable(self, admin: AdminCap, *, scope: str = "component", mode: str = "drain", reason: str = "") -> None:
        """Emergency disable / quarantine (C059).

        ``drain``: refuse new futures, let existing ones resolve and be taken.
        ``freeze``: additionally refuse every mutation; reads and take of already
        resolved values stay allowed so receivers are not orphaned silently.
        """
        self._check_admin(admin)
        if mode not in ("drain", "freeze"):
            raise Rejected("mode must be drain or freeze", code="INVALID_ARGUMENT")
        if not (scope == "component" or scope.startswith("tenant:")):
            raise Rejected("scope must be 'component' or 'tenant:<id>'", code="INVALID_ARGUMENT")
        self._disabled[scope] = mode
        self.audit.append("component.disable", actor="admin", target=scope, mode=mode, reason=reason)
        self.log.emit("warning", "disable", code="COMPONENT_DISABLED", scope=scope, mode=mode)

    def enable(self, admin: AdminCap, *, scope: str = "component") -> None:
        self._check_admin(admin)
        self._disabled.pop(scope, None)
        self.audit.append("component.enable", actor="admin", target=scope)

    def _disabled_mode(self, tenant: str) -> str | None:
        return self._disabled.get("component") or self._disabled.get(f"tenant:{tenant}")

    # ------------------------------------------------------------------ helpers
    def _decide(self, reason: str, code: str | None, **state: Any) -> None:
        self.decisions.record(reason, code=code, config_revision=self.config.active().revision_id,
                              policy_version=POLICY_VERSION, **state)

    def _reject(self, code: str, message: str, reason: str, **state: Any) -> Rejected:
        self.metrics.inc("inv18_rejections_total", code=code)
        self._decide(reason, code, **state)
        self.log.emit("warning", "reject", code=code, config_revision=self.config.active().revision_id,
                      **{k: v for k, v in state.items() if k != "tenant"})
        return Rejected(message, code=code, details=state)

    def _validate_tenant(self, tenant: Any) -> str:
        lim = self.config.values()["max_id_len"]
        if not isinstance(tenant, str) or not tenant or len(tenant) > lim or not tenant.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise Rejected("tenant must be a non-empty [A-Za-z0-9._-] identifier within max_id_len",
                           code="INVALID_ARGUMENT")
        return tenant

    def _observer(self, fid: str):
        def obs(event: str, fut: Future) -> None:
            e = self._entries.get(fid)
            now = self._clock()
            if event == "resolve":
                self.metrics.inc("inv18_values_resolved_total")
            elif event == "resolve_error":
                self.metrics.inc("inv18_errors_resolved_total")
            elif event == "abandon":
                self.metrics.inc("inv18_abandonments_total", reason="writer_dropped")
                self._decide("ABANDON_TRANSITION", "FUTURE_ABANDONED", future_id=fid)
            elif event == "cancel":
                self.metrics.inc("inv18_cancellations_total")
                self._decide("CANCEL_TRANSITION", "FUTURE_CANCELLED", future_id=fid)
            if e is not None and event in ("resolve", "resolve_error", "abandon", "cancel"):
                e.resolved_at = now
                self.metrics.observe("inv18_resolution_latency_seconds", now - e.created)
            if event == "take":
                self.metrics.inc("inv18_takes_total")
                if e is not None and e.resolved_at is not None:
                    self.metrics.observe("inv18_receive_latency_seconds", now - e.resolved_at)
        return obs

    # ------------------------------------------------------------------ create
    def create(self, value_type: type, *, tenant: str = "default", trace: TraceContext | None = None
               ) -> tuple[ResolverCap, ReceiverCap]:
        """Admit and allocate one future; returns the writer and receiver capabilities."""
        tenant = self._validate_tenant(tenant)
        if not isinstance(value_type, type):
            raise TypeError("value_type must be a type")
        c = self.config.values()
        if self._disabled_mode(tenant):
            raise self._reject("COMPONENT_DISABLED", "component disabled", "DISABLED_REJECTED", tenant=tenant)
        with self._lock:
            if len(self._entries) >= c["max_outstanding"]:
                self.metrics.inc("inv18_limit_hits_total", limit="process")
                err = "process"
            elif self._per_tenant.get(tenant, 0) >= c["max_per_tenant"]:
                self.metrics.inc("inv18_limit_hits_total", limit="tenant")
                err = "tenant"
            else:
                err = None
                # OPT-1 (docs/PERFORMANCE.md): one urandom call supplies every random field
                rnd = os.urandom(76).hex()
                fid = f"f{next(self._seq):x}-{rnd[:8]}"
                tokens = {"resolver": rnd[8:40], "receiver": rnd[40:72], "observer": rnd[72:104]}
                span = TraceContext(trace.trace_id, rnd[136:152], trace.span_id, trace.flags) if trace \
                    else TraceContext(rnd[104:136], rnd[136:152])
                fut: Future = Future(value_type, observer=self._observer(fid))
                self._entries[fid] = _Entry(fut, tenant, tokens, self._clock(), span, self.epoch)
                self._per_tenant[tenant] = self._per_tenant.get(tenant, 0) + 1
                open_n = len(self._entries)
        if err:
            raise self._reject("RESOURCE_EXHAUSTED", f"{err} outstanding-future limit reached",
                               "OVERLOAD_REJECTED", limit=err, tenant=tenant)
        self.metrics.inc("inv18_futures_created_total", tenant_class="default" if tenant == "default" else "named")
        self.metrics.set("inv18_futures_open", open_n)
        rcap = ResolverCap(fid, tenant, tokens["resolver"], "resolver")
        weakref.finalize(rcap, Runtime._writer_dropped, weakref.ref(self), fid)
        return rcap, ReceiverCap(fid, tenant, tokens["receiver"], "receiver")

    @staticmethod
    def _writer_dropped(rt_ref, fid: str) -> None:
        rt = rt_ref()
        if rt is None:
            return
        e = rt._entries.get(fid)
        if e is not None:
            e.future.abandon()
            rt._maybe_release(fid)

    def observer(self, cap: _Cap) -> ObserverCap:
        """Derive a read-only capability from a resolver or receiver capability."""
        e = self._auth(cap, ("resolver", "receiver"))
        return ObserverCap(cap.future_id, cap.tenant, e.tokens["observer"], "observer")

    # ------------------------------------------------------------------ auth
    def _auth(self, cap: Any, kinds: tuple[str, ...]) -> _Entry:
        if not isinstance(cap, _Cap):
            raise self._reject("PERMISSION_DENIED", "a capability is required", "AUTHZ_REJECTED")
        e = self._entries.get(cap.future_id)
        if e is None:
            tomb = self._tombs.get(cap.future_id)
            if tomb is not None and cap.kind in kinds and tomb[0] == cap.tenant and \
                    hmac.compare_digest(tomb[1].get(cap.kind, ""), cap.token or ""):
                if cap.kind == "receiver":
                    self.metrics.inc("inv18_double_takes_total")
                    self.metrics.inc("inv18_rejections_total", code="FUTURE_ALREADY_TAKEN")
                    self._decide("TAKE_REJECTED", "FUTURE_ALREADY_TAKEN", future_id=cap.future_id)
                    raise _f.AlreadyTaken("future already taken by its receiver")
                if cap.kind == "resolver" and tomb[2] == _f.CANCELLED:
                    self.metrics.inc("inv18_rejections_total", code="FUTURE_CANCELLED")
                    self._decide("RESOLVE_REJECTED", "FUTURE_CANCELLED", future_id=cap.future_id)
                    raise _f.Cancelled("future cancelled by its receiver")
                if cap.kind == "resolver":
                    self.metrics.inc("inv18_double_resolutions_total")
                    self.metrics.inc("inv18_rejections_total", code="FUTURE_ALREADY_RESOLVED")
                    self._decide("RESOLVE_REJECTED", "FUTURE_ALREADY_RESOLVED", future_id=cap.future_id)
                    raise _f.AlreadyResolved("future already resolved and released")
            # unknown, released beyond the tombstone window, or foreign: do not reveal which
            raise self._reject("PERMISSION_DENIED", "capability not valid", "AUTHZ_REJECTED")
        if cap.kind not in kinds or e.tenant != cap.tenant or \
                not hmac.compare_digest(e.tokens.get(cap.kind, ""), cap.token or ""):
            self.audit.append("capability.denied", target=cap.future_id, result="denied", kind=cap.kind)
            raise self._reject("PERMISSION_DENIED", "capability not valid", "AUTHZ_REJECTED")
        return e

    def _tomb_valid(self, cap: Any, kind: str) -> bool:
        if not isinstance(cap, _Cap) or cap.kind != kind or cap.future_id in self._entries:
            return False
        tomb = self._tombs.get(cap.future_id)
        return tomb is not None and tomb[0] == cap.tenant and \
            hmac.compare_digest(tomb[1].get(kind, ""), cap.token or "")

    def _mutation_gate(self, e: _Entry) -> None:
        if self._disabled_mode(e.tenant) == "freeze":
            raise self._reject("COMPONENT_DISABLED", "component frozen", "DISABLED_REJECTED")

    def _run(self, e: _Entry, fid: str, fn, *args):
        try:
            return fn(*args)
        except Exception as exc:
            code = from_exception(exc).code
            self.log.emit("warning", getattr(fn, "__name__", "op"), code=code, future_id=fid, trace=e.trace,
                          config_revision=self.config.active().revision_id, tenant=e.tenant)
            self._classify(exc, fid)
            raise

    def _classify(self, exc: BaseException, fid: str) -> None:
        code = from_exception(exc).code
        self.metrics.inc("inv18_rejections_total", code=code)
        if isinstance(exc, _f.AlreadyResolved):
            self.metrics.inc("inv18_double_resolutions_total")
            self._decide("RESOLVE_REJECTED", code, future_id=fid)
        elif isinstance(exc, _f.AlreadyTaken):
            self.metrics.inc("inv18_double_takes_total")
            self._decide("TAKE_REJECTED", code, future_id=fid)
        elif isinstance(exc, (TypeError, ValueError, _f.Cancelled)):
            self._decide("RESOLVE_REJECTED", code, future_id=fid)

    # ------------------------------------------------------------------ writer ops
    def resolve(self, cap: ResolverCap, value: Any) -> None:
        e = self._auth(cap, ("resolver",))
        self._mutation_gate(e)
        self._run(e, cap.future_id, e.future.resolve, value)
        self._maybe_release(cap.future_id)

    def resolve_error(self, cap: ResolverCap, message: str) -> None:
        e = self._auth(cap, ("resolver",))
        self._mutation_gate(e)
        self._run(e, cap.future_id, e.future.resolve_error, message)
        self._maybe_release(cap.future_id)

    def abandon(self, cap: ResolverCap) -> bool:
        if self._tomb_valid(cap, "resolver"):
            return False          # abandoning a settled, released future is a harmless no-op
        e = self._auth(cap, ("resolver",))
        self._mutation_gate(e)
        done = e.future.abandon()
        self._maybe_release(cap.future_id)
        return done

    # ------------------------------------------------------------------ receiver ops
    def take(self, cap: ReceiverCap):
        e = self._auth(cap, ("receiver",))
        try:
            return self._run(e, cap.future_id, e.future.take)
        finally:
            self._maybe_release(cap.future_id)

    def wait(self, cap: ReceiverCap, timeout: float | None = None) -> bool:
        e = self._auth(cap, ("receiver",))
        return e.future.wait(timeout)

    def take_wait(self, cap: ReceiverCap, timeout: float):
        """Wait up to ``timeout`` (caller-owned deadline) then take; TIMEOUT leaves the future intact."""
        e = self._auth(cap, ("receiver",))
        if not e.future.wait(timeout):
            self.metrics.inc("inv18_rejections_total", code="TIMEOUT")
            raise Rejected("receiver deadline expired", code="TIMEOUT", details={"timeout_s": timeout})
        return self.take(cap)

    def cancel(self, cap: ReceiverCap) -> bool:
        if self._tomb_valid(cap, "receiver"):
            return False
        e = self._auth(cap, ("receiver",))
        self._mutation_gate(e)
        done = e.future.cancel()
        self._maybe_release(cap.future_id)
        return done

    def inspect(self, cap: _Cap) -> dict:
        tomb = self._tombs.get(getattr(cap, "future_id", None))
        if cap.__class__ in (ObserverCap, ResolverCap, ReceiverCap) and cap.future_id not in self._entries \
                and tomb is not None and tomb[0] == cap.tenant and \
                hmac.compare_digest(tomb[1].get(cap.kind, ""), cap.token or ""):
            return {"future_id": cap.future_id, "state": "RELEASED", "taken": True}
        e = self._auth(cap, ("observer", "resolver", "receiver"))
        f = e.future
        return {"future_id": cap.future_id, "state": f.state, "taken": f.taken,
                "age_s": round(self._clock() - e.created, 6), "trace_id": e.trace.trace_id,
                "value_type": f.value_type.__name__}

    # ------------------------------------------------------------------ reclamation
    def _maybe_release(self, fid: str) -> None:
        """Drop registry state once the future is terminal *and* consumed (C067)."""
        with self._lock:
            e = self._entries.get(fid)
            if e is None:
                return
            f = e.future
            if f.state in _f.TERMINAL_STATES and f.taken:
                del self._entries[fid]
                self._tombs[fid] = (e.tenant, e.tokens, f.state)
                if len(self._tombs) > TOMBSTONES:
                    self._tombs.popitem(last=False)
                n = self._per_tenant.get(e.tenant, 1) - 1
                if n:
                    self._per_tenant[e.tenant] = n
                else:
                    self._per_tenant.pop(e.tenant, None)
                open_n = len(self._entries)
            else:
                return
        self.metrics.set("inv18_futures_open", open_n)

    @property
    def outstanding(self) -> int:
        return len(self._entries)

    def tenant_outstanding(self, tenant: str) -> int:
        return self._per_tenant.get(tenant, 0)

    # ------------------------------------------------------------------ health (C052, C071)
    def set_dependency(self, name: str, state: str) -> None:
        if state not in ("ok", "degraded", "unavailable", "not-required-at-runtime"):
            raise ValueError("bad dependency state")
        self._dependency_state[name] = state

    def health(self) -> dict:
        c = self.config.values()
        now = self._clock()
        with self._lock:
            entries = list(self._entries.values())
        pending = [e for e in entries if e.future.state == _f.PENDING]
        stalled = sum(1 for e in pending if now - e.created > c["stall_threshold_s"])
        reasons: list[str] = []
        if self.metrics.counter("inv18_invariant_violations_total"):
            state = FAILED
            reasons.append("INVARIANT_VIOLATION")
        else:
            if self._disabled:
                reasons.append("DISABLED:" + ",".join(sorted(f"{k}={v}" for k, v in self._disabled.items())))
            if len(entries) > c["soft_outstanding"]:
                reasons.append("SOFT_LIMIT_EXCEEDED")
            # a stall only degrades when it is widespread, not a single slow producer (no flapping on spikes)
            if pending and stalled / len(pending) > c["stall_ratio_degraded"] and stalled >= 3:
                reasons.append("STALLED_FUTURES")
            if self.log.sink_failed:
                self._dependency_state["telemetry_sink"] = "unavailable"
                reasons.append("TELEMETRY_SINK_UNAVAILABLE")
            state = DEGRADED if reasons else HEALTHY
        ready = state != FAILED and "component" not in self._disabled
        ages = sorted(now - e.created for e in pending)
        return {"state": state, "ready": ready, "reasons": reasons, "outstanding": len(entries),
                "pending": len(pending), "stalled": stalled,
                "pending_age_p50_s": ages[len(ages) // 2] if ages else 0.0,
                "pending_age_max_s": ages[-1] if ages else 0.0,
                "dependencies": dict(self._dependency_state)}

    def record_invariant_violation(self, what: str) -> None:
        self.metrics.inc("inv18_invariant_violations_total")
        self.audit.append("invariant.violation", result="failed", what=what)
        self.log.emit("critical", "invariant", code="INTERNAL_INVARIANT", what=what)
