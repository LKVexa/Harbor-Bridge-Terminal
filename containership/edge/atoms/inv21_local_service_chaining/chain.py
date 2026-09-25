"""INV-21 chainer: the single public call path (PK_LOCAL_CHAIN/1).

Two entry styles share one decision core:

* ``invoke(callee, request, ctx)`` / ``ainvoke(...)`` -- production API. The
  caller identity is an authenticated :class:`CallContext`; handlers placed with
  ``abi="hop"`` receive ``(hop, request)`` and continue the chain with
  ``hop.call`` / ``await hop.acall``, which derive the child context. Sync and
  async handlers/transports are both supported (INV-16).
* ``call(callee, tenant, request, path=, trace_id=)`` -- the 4.x compatibility
  API with caller-supplied strings. Refused with ``PK_CHAIN_UNAUTHENTICATED``
  in ``production`` mode.

Order of checks per hop (each refusal is audited, counted and explained):
lifecycle -> liveness (principal expiry, cancel, deadline) -> cycle -> depth ->
admission -> residency + tenant isolation -> per-hop capability decision ->
dispatch (local handler, or breaker + retry + remote transport).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import inspect
import secrets
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field, replace
from threading import RLock
from time import perf_counter_ns
from typing import Any, Callable, Deque, Optional

from .admission import AdmissionController, CircuitBreaker, RetryPolicy
from .audit import AuditLog
from .config import ChainConfig
from .context import CallContext, IdentityVerifier, Principal, check_id
from .errors import (CapabilityRefused, ChainCycle, ChainError, ChainTooDeep, CrossTenantChain,
                     DeadlineExceeded, ProviderUnavailable, TransportUnavailable, Unauthenticated,
                     ValidationFailed, normalize)
from .lifecycle import Lifecycle
from .policy import (CapabilityRequest, CompatLocalProvider, GuardedProvider, new_correlation_id)
from .residency import Placement, Residency
from .telemetry import DecisionEvent, DecisionLedger, Metrics

DEFAULT_MAX_DEPTH = 4
DEFAULT_MAX_TELEMETRY_EVENTS = 1024
COMPAT_ISSUER = "compat-unauthenticated"

CapabilityChecker = Callable[[str, str, Any, tuple, str], bool]
RemoteDispatch = Callable[[str, str, Any, tuple, str], Any]


@dataclass(frozen=True)
class Hop:
    """Handle given to ``abi="hop"`` handlers to continue the chain."""

    chainer: "Chainer"
    ctx: CallContext
    callee: str
    root_id: Optional[str] = None

    def call(self, callee: str, request: Any, *, operation: Optional[str] = None):
        return self.chainer.invoke(callee, request, self._next(operation))

    async def acall(self, callee: str, request: Any, *, operation: Optional[str] = None):
        return await self.chainer.ainvoke(callee, request, self._next(operation))

    def _next(self, operation):
        c = replace(self.ctx, path=self.ctx.path + (self.callee,), root_id=self.root_id,
                    operation=operation or self.ctx.operation)
        return self.chainer._seal_child(c)


class _RootScope:
    """Admission + active-root registration for one root call (cheaper than a generator CM)."""

    __slots__ = ("ch", "tenant", "root", "_adm")

    def __init__(self, ch, tenant, root):
        self.ch, self.tenant, self.root, self._adm = ch, tenant, root, None

    def __enter__(self):
        if self.ch.admission is not None:
            self._adm = self.ch.admission.admit(self.tenant)
            self._adm.__enter__()
        self.ch._active_roots.add(self.root)
        return self

    def __exit__(self, *exc):
        self.ch._active_roots.discard(self.root)
        if self._adm is not None:
            self._adm.__exit__(*exc)
        return False


@dataclass
class Chainer:
    residency: Residency
    max_depth: int = DEFAULT_MAX_DEPTH
    capability_checker: Optional[CapabilityChecker] = None
    remote_dispatch: Optional[RemoteDispatch] = None
    max_telemetry_events: int = DEFAULT_MAX_TELEMETRY_EVENTS
    # 4.3 production collaborators -------------------------------------------------
    config: Optional[ChainConfig] = None
    policy: Optional[GuardedProvider] = None
    transport: Any = None
    audit: Optional[AuditLog] = None
    admission: Optional[AdmissionController] = None
    breaker: Optional[CircuitBreaker] = None
    retry: Optional[RetryPolicy] = None
    lifecycle: Optional[Lifecycle] = None
    metrics: Optional[Metrics] = None
    trusted_issuers: frozenset = frozenset()
    verifier: Optional[IdentityVerifier] = None
    config_revision: Optional[int] = None
    # compat counters ---------------------------------------------------------------
    hops_local: int = 0
    hops_remote: int = 0
    cycles_refused: int = 0
    depth_exceeded: int = 0
    capability_refused: int = 0
    cross_tenant_refused: int = 0
    _trace: Deque = field(init=False, repr=False)
    _ledger: DecisionLedger = field(init=False, repr=False)
    _metrics_lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _seal_key: bytes = field(default_factory=lambda: secrets.token_bytes(32), init=False, repr=False)
    _active_roots: set = field(default_factory=set, init=False, repr=False)
    _vcache: OrderedDict = field(default_factory=OrderedDict, init=False, repr=False)

    def __post_init__(self) -> None:
        cfg = self.config
        if cfg is not None:
            self.max_depth = cfg.max_depth
            self.max_telemetry_events = cfg.max_telemetry_events
        if not isinstance(self.max_depth, int) or isinstance(self.max_depth, bool) or not 1 <= self.max_depth <= 64:
            raise ValueError("max_depth must be an integer within [1, 64]")
        if self.capability_checker is not None and not callable(self.capability_checker):
            raise TypeError("capability_checker must be callable")
        if self.remote_dispatch is not None and not callable(self.remote_dispatch):
            raise TypeError("remote_dispatch must be callable")
        if self.policy is not None and not isinstance(self.policy, GuardedProvider):
            self.policy = GuardedProvider(self.policy)
        self._ledger = DecisionLedger(max_events=self.max_telemetry_events,
                                      sample_rate=cfg.telemetry_sample_rate if cfg else 1.0)
        self._trace = deque(maxlen=self.max_telemetry_events)
        self.metrics = self.metrics or Metrics()
        self.lifecycle = self.lifecycle or Lifecycle("ready")
        if cfg is not None:
            self.admission = self.admission or AdmissionController(
                max_in_flight=cfg.max_in_flight, max_in_flight_per_tenant=cfg.max_in_flight_per_tenant,
                tenant_rate=cfg.tenant_rate)
            self.breaker = self.breaker or CircuitBreaker(failure_threshold=cfg.breaker_failure_threshold,
                                                          reset_after_s=cfg.breaker_reset_s)
            self.retry = self.retry or RetryPolicy(max_attempts=cfg.retry_max_attempts)
        if self.production:
            self._check_production_wiring()

    # -- configuration --------------------------------------------------------------
    @property
    def production(self) -> bool:
        return self.config is not None and self.config.mode == "production"

    def _check_production_wiring(self) -> None:
        problems = self._wiring_problems()
        if problems:
            raise ValidationFailed("production mode requires: " + ", ".join(problems), field="wiring")

    def _wiring_problems(self) -> list:
        problems = []
        if self.verifier is None:
            problems.append("identity verifier")
        if self.policy is None or not self.policy.authoritative:
            problems.append("authoritative capability provider")
        if self.capability_checker is not None:
            problems.append("legacy capability_checker must not be set")
        if self.transport is None:
            problems.append("remote transport adapter")
        if self.audit is None:
            problems.append("audit log")
        if not self.trusted_issuers:
            problems.append("trusted identity issuers")
        if self.residency.default_lease_s is None and (self.config is None or self.config.residency_lease_s is None):
            problems.append("residency lease")
        return problems

    def apply_config(self, cfg: ChainConfig) -> None:
        """Applier for ConfigStore.activate (atomic: validate everything first)."""
        if cfg.mode == "production":
            prev = self.config
            self.config = cfg
            try:
                problems = self._wiring_problems()
            finally:
                self.config = prev
            if problems:
                raise ValidationFailed("cannot activate production config; missing: " + ", ".join(problems),
                                       field="wiring")
        self.config = cfg
        if self.admission is None or (self.admission.max_in_flight, self.admission.max_per_tenant,
                                      self.admission.tenant_rate) != (cfg.max_in_flight, cfg.max_in_flight_per_tenant,
                                                                      cfg.tenant_rate):
            self.admission = AdmissionController(max_in_flight=cfg.max_in_flight,
                                                 max_in_flight_per_tenant=cfg.max_in_flight_per_tenant,
                                                 tenant_rate=cfg.tenant_rate)
        if self.breaker is None:
            self.breaker = CircuitBreaker(failure_threshold=cfg.breaker_failure_threshold,
                                          reset_after_s=cfg.breaker_reset_s)
        self.max_depth = cfg.max_depth
        if cfg.residency_lease_s is not None:
            self.residency.default_lease_s = cfg.residency_lease_s
        if self.policy is not None:
            self.policy.timeout_s = cfg.policy_timeout_s
            self.policy.cache_ttl_s = cfg.policy_cache_ttl_s
        self.retry = RetryPolicy(max_attempts=cfg.retry_max_attempts)

    def bind(self, store) -> None:
        """Wire this chainer to a ConfigStore: atomic apply + revision/provenance tagging."""
        store.on_activate(self.apply_config)

        def committed(rev):
            self.config_revision = rev.revision
            if self.audit is not None:
                self.audit.append("config_activated", revision=rev.revision, author=rev.author,
                                  source=rev.source, digest=rev.digest)
        store.on_committed(committed)
        self.config_revision = store.current.revision

    # -- observability ----------------------------------------------------------------
    @property
    def trace(self) -> list:
        with self._metrics_lock:
            return list(self._trace)

    @property
    def decisions(self) -> list:
        return self._ledger.events()

    def explain(self, trace_id: str) -> list:
        return self._ledger.explain(trace_id)

    def _bump(self, attr: str) -> None:
        with self._metrics_lock:
            setattr(self, attr, getattr(self, attr) + 1)

    def _record(self, ctx: CallContext, callee: str, route: str, reason: str, started: int,
                code: Optional[str] = None, policy_revision: Optional[int] = None) -> None:
        dur = max(0, perf_counter_ns() - started)
        ev = DecisionEvent(callee, ctx.tenant, ctx.trace_id, route, reason, ctx.depth, dur, code,
                           self._ledger.redact(ctx.principal.subject), time.time(),
                           self.config_revision, policy_revision)
        self._ledger.record(ev)
        if route != "local":  # local hops are counted by hops_local
            self.metrics.inc("decisions", route=route, reason=reason)
        else:
            self.metrics.observe_us("local_dispatch_decision_us", dur / 1000)
        if self.audit is not None:  # every routing decision, grants included, is audited
            self.audit.append("decision", callee=callee, tenant=ctx.tenant, trace_id=ctx.trace_id,
                              subject=ev.subject, route=route, reason=reason, code=code, depth=ctx.depth,
                              config_revision=self.config_revision, policy_revision=policy_revision)

    def _refuse(self, ctx, callee, reason, started, err: ChainError, counter: Optional[str] = None):
        if counter:
            self._bump(counter)
        self.metrics.inc("refused", reason=reason)
        self._record(ctx, callee, "refused", reason, started, err.code)
        raise err

    # -- context construction -----------------------------------------------------------
    def _compat_ctx(self, tenant, trace_id, path) -> CallContext:
        if self.production:
            raise Unauthenticated("compat call API refused in production mode; use invoke(ctx)")
        if not isinstance(tenant, str) or not tenant.strip():
            raise ValueError("tenant must be a non-empty string")
        if not isinstance(trace_id, str) or not trace_id.strip():
            raise ValueError("trace_id must be a non-empty string")
        chain = tuple(path or ())
        if any(not isinstance(p, str) or not p for p in chain):
            raise ValueError("path entries must be non-empty strings")
        tenant, trace_id = tenant.strip(), trace_id.strip()
        p = Principal("compat-caller", tenant, frozenset(), COMPAT_ISSUER, 0.0, float("inf"),
                      "compat", provenance="caller-asserted")
        return CallContext(p, trace_id, path=chain)

    def _check_principal(self, ctx: CallContext) -> None:
        """Production: the principal must be re-derivable from the carried credential by
        this chainer's own verifier -- a hand-built Principal object is refused."""
        if not isinstance(ctx, CallContext):
            raise Unauthenticated("invoke requires a CallContext")
        if not self.production:
            return
        p = ctx.principal
        if p.provenance != "hmac-sha256" or p.issuer not in self.trusted_issuers or not ctx.credential:
            raise Unauthenticated("principal not backed by a trusted runtime credential")
        v = self._vcache.get(ctx.credential)
        if v is None or v.expired:
            v = self.verifier.verify(ctx.credential)
            self._vcache[ctx.credential] = v
            while len(self._vcache) > 4096:
                self._vcache.popitem(last=False)
        if (v.subject, v.tenant, v.capabilities, v.issuer, v.token_id, v.expires_at) != \
                (p.subject, p.tenant, p.capabilities, p.issuer, p.token_id, p.expires_at):
            raise Unauthenticated("principal does not match its credential")

    # -- hop sealing: only chainer-derived child contexts count as nested hops ----------------
    def _mac(self, ctx: CallContext) -> str:
        msg = "\x1f".join((ctx.root_id or "", ctx.trace_id, "/".join(ctx.path), ctx.principal.token_id,
                           ctx.principal.tenant)).encode()
        return hmac.new(self._seal_key, msg, hashlib.sha256).hexdigest()

    def _seal_child(self, ctx: CallContext) -> CallContext:
        return replace(ctx, hop_seal=self._mac(ctx)) if ctx.root_id else ctx

    def _is_nested(self, ctx: CallContext) -> bool:
        return bool(ctx.hop_seal and ctx.root_id in self._active_roots
                    and hmac.compare_digest(ctx.hop_seal, self._mac(ctx)))

    # -- shared decision core ---------------------------------------------------------------
    def _decide(self, callee: str, request: Any, ctx: CallContext, started: int, legacy: bool):
        self.lifecycle.require_serving()
        if not isinstance(callee, str) or not callee.strip():
            raise ValueError("callee must be a non-empty string")
        if legacy:
            callee = callee.strip()  # 4.x behaviour; the production API never normalises silently
        check_id(callee, "callee")
        try:
            ctx.check_live()
        except ChainError as e:
            self._refuse(ctx, callee, e.category, started, e)
        if callee in ctx.path:
            self._refuse(ctx, callee, "cycle", started,
                         ChainCycle(" -> ".join(ctx.path + (callee,)), callee=callee, depth=ctx.depth),
                         "cycles_refused")
        if ctx.depth >= self.max_depth:
            self._refuse(ctx, callee, "depth", started,
                         ChainTooDeep(f"depth {ctx.depth} reached bound {self.max_depth}",
                                      depth=ctx.depth, max_depth=self.max_depth, callee=callee),
                         "depth_exceeded")
        placement = self.residency.resolve(callee)
        if placement is not None and placement.tenant != ctx.tenant:
            self._refuse(ctx, callee, "cross_tenant", started,
                         CrossTenantChain(f"{callee} belongs to another tenant", callee=callee,
                                          callee_tenant=placement.tenant, caller_tenant=ctx.tenant),
                         "cross_tenant_refused")
        rev = self._authorize(callee, request, ctx, placement, started, legacy)
        return callee, placement, rev

    def _authorize(self, callee, request, ctx, placement, started, legacy) -> Optional[int]:
        topology = "remote" if placement is None else "local"
        if self.capability_checker is not None:
            try:
                allowed = bool(self.capability_checker(callee, ctx.tenant, request, ctx.path, ctx.trace_id))
            except Exception as exc:
                self._refuse(ctx, callee, "provider_error", started,
                             ProviderUnavailable("capability checker failed; failing closed",
                                                 reason=type(exc).__name__, trace_id=ctx.trace_id))
            rev = None
        elif self.policy is not None:
            # caller identity comes only from a chainer-sealed path, never from caller-supplied path
            caller = ctx.path[-1] if ctx.path and self._is_nested(ctx) else None
            req = CapabilityRequest(ctx.principal.subject, ctx.tenant, caller,
                                    callee, ctx.operation, ctx.principal.capabilities, topology,
                                    ctx.depth, new_correlation_id())
            try:
                d = self.policy.decide(req)
            except ProviderUnavailable as e:
                self._refuse(ctx, callee, "provider_unavailable", started, e)
            allowed, rev = d.allow, d.policy_revision
        else:
            # Development-only compat authority: same-tenant local placement; remote
            # authorization is re-run by the peer endpoint.
            allowed = CompatLocalProvider().decide(
                CapabilityRequest("", ctx.tenant, None, callee, ctx.operation, frozenset(), topology,
                                  ctx.depth, "compat")).allow and (placement is None or placement.tenant == ctx.tenant)
            rev = 0
        if not allowed:
            self._refuse(ctx, callee, "capability", started,
                         CapabilityRefused(f"capability refused for {ctx.tenant} -> {callee}",
                                           callee=callee, tenant=ctx.tenant, trace_id=ctx.trace_id,
                                           depth=ctx.depth),
                         "capability_refused")
        return rev

    def _enter(self, ctx: CallContext):
        """Returns (root_id, admission_cm). Nested = sealed child of an active root."""
        from contextlib import contextmanager, nullcontext
        if self._is_nested(ctx):
            return ctx.root_id, nullcontext()
        root = secrets.token_hex(8)
        return root, _RootScope(self, ctx.tenant, root)

    def _stall_check(self, callee: str, started: int) -> None:
        if self.config is None:
            return
        if (perf_counter_ns() - started) / 1e9 > self.config.handler_stall_s:
            self.residency.set_health(callee, False)
            self.metrics.inc("handler_stalls", callee=callee)
            if self.audit is not None:
                self.audit.append("quarantine_placement", callee=callee, reason="stall")

    # -- sync path ------------------------------------------------------------------------------
    def call(self, callee: str, tenant: str, request: Any, *, path=None, trace_id: str = "t-0"):
        """4.x compatibility API (development mode only)."""
        started = perf_counter_ns()
        ctx = self._compat_ctx(tenant, trace_id, path)
        return self._invoke(callee, request, ctx, started, legacy=True, allow_remote=True)

    def invoke(self, callee: str, request: Any, ctx: CallContext, *, _allow_remote: bool = True):
        started = perf_counter_ns()
        self._check_principal(ctx)
        return self._invoke(callee, request, ctx, started, legacy=False, allow_remote=_allow_remote)

    def _invoke(self, callee, request, ctx, started, *, legacy, allow_remote):
        callee, placement, rev = self._decide(callee, request, ctx, started, legacy)
        root, adm = self._enter(ctx)
        with adm:
            with self._metrics_lock:
                self._trace.append((callee, ctx.trace_id))
            if placement is None:
                if not allow_remote:
                    self._refuse(ctx, callee, "not_resident_on_peer", started,
                                 TransportUnavailable("callee not resident on this peer", callee=callee))
                return self._remote(callee, request, ctx, started, rev, legacy)
            self._bump("hops_local")
            self.metrics.inc("hops_local", callee=callee)
            self._record(ctx, callee, "local", "same_host_same_tenant", started, policy_revision=rev)
            h_started = perf_counter_ns()
            try:
                if placement.abi == "hop":
                    out = placement.handler(Hop(self, ctx, callee, root), request)
                    if inspect.isawaitable(out):
                        out.close() if hasattr(out, "close") else None
                        raise ValidationFailed("async handler reached through sync invoke; use ainvoke",
                                               callee=callee)
                else:
                    out = placement.handler(self, request, ctx.path + (callee,), ctx.tenant, ctx.trace_id)
                return out
            except BaseException as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                if legacy and not isinstance(exc, ChainError):
                    raise  # 4.x behaviour: legacy handler exceptions propagate unchanged
                raise normalize(exc, origin="handler", correlation_id=ctx.trace_id) from None
            finally:
                self._stall_check(callee, h_started)

    def _remote_prelude(self, callee, ctx, started, rev):
        self._bump("hops_remote")
        self.metrics.inc("hops_remote", reason="not_resident")
        self._record(ctx, callee, "remote", "not_resident", started, policy_revision=rev)

    def _timeout(self, ctx) -> float:
        t = self.config.remote_timeout_s if self.config else 2.0
        if ctx.deadline is not None:
            t = min(t, ctx.deadline.remaining())
        return t

    def _remote(self, callee, request, ctx, started, rev, legacy):
        self._remote_prelude(callee, ctx, started, rev)
        if self.transport is None:
            if self.remote_dispatch is not None:
                return self.remote_dispatch(callee, ctx.tenant, request, ctx.path, ctx.trace_id)
            if self.config is not None and (self.production or self.config.require_remote_transport):
                raise TransportUnavailable("no remote transport configured", callee=callee)
            return ("remote", callee, request)  # 4.x compatibility sentinel (development only)
        attempt = 0
        while True:
            attempt += 1
            ctx.check_live()
            if self.breaker:
                self.breaker.before(callee)
            try:
                out = self.transport.send(callee, request, ctx, self._timeout(ctx))
                if self.breaker:
                    self.breaker.success(callee)
                return out
            except BaseException as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                err = normalize(exc, origin="transport", correlation_id=ctx.trace_id)
                if self.breaker and err.category in ("transport", "deadline"):
                    self.breaker.failure(callee)
                back = self.retry.should_retry(err, attempt, ctx.operation, ctx.idempotency_key,
                                               None if ctx.deadline is None else ctx.deadline.remaining()) \
                    if self.retry else None
                if back is None:
                    self.metrics.inc("remote_failures", code=err.code)
                    raise err from None
                self.metrics.inc("remote_retries")
                time.sleep(back)

    # -- async path (INV-16) ----------------------------------------------------------------------
    async def ainvoke(self, callee: str, request: Any, ctx: CallContext):
        started = perf_counter_ns()
        self._check_principal(ctx)
        callee, placement, rev = self._decide(callee, request, ctx, started, False)
        root, adm = self._enter(ctx)
        with adm:
            with self._metrics_lock:
                self._trace.append((callee, ctx.trace_id))
            if placement is None:
                self._remote_prelude(callee, ctx, started, rev)
                if self.transport is None:
                    if self.production or (self.config and self.config.require_remote_transport):
                        raise TransportUnavailable("no remote transport configured", callee=callee)
                    return ("remote", callee, request)
                return await self._aremote(callee, request, ctx)
            self._bump("hops_local")
            self.metrics.inc("hops_local", callee=callee)
            self._record(ctx, callee, "local", "same_host_same_tenant", started, policy_revision=rev)
            h_started = perf_counter_ns()
            try:
                if placement.abi == "hop":
                    out = placement.handler(Hop(self, ctx, callee, root), request)
                else:
                    out = placement.handler(self, request, ctx.path + (callee,), ctx.tenant, ctx.trace_id)
                if inspect.isawaitable(out):
                    remaining = None if ctx.deadline is None else max(0.0, ctx.deadline.remaining())
                    out = await asyncio.wait_for(out, remaining)
                return out
            except BaseException as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                if isinstance(exc, asyncio.CancelledError):
                    ctx.cancel.cancel("asyncio_cancelled")
                    raise
                raise normalize(exc, origin="handler", correlation_id=ctx.trace_id) from None
            finally:
                self._stall_check(callee, h_started)

    async def _aremote(self, callee, request, ctx):
        send = getattr(self.transport, "asend", None)
        attempt = 0
        while True:
            attempt += 1
            ctx.check_live()
            if self.breaker:
                self.breaker.before(callee)
            try:
                if send is not None:
                    out = await asyncio.wait_for(send(callee, request, ctx, self._timeout(ctx)), self._timeout(ctx))
                else:
                    out = await asyncio.wait_for(
                        asyncio.to_thread(self.transport.send, callee, request, ctx, self._timeout(ctx)),
                        self._timeout(ctx))
                if self.breaker:
                    self.breaker.success(callee)
                return out
            except asyncio.CancelledError:
                ctx.cancel.cancel("asyncio_cancelled")
                raise
            except Exception as exc:
                err = normalize(exc, origin="transport", correlation_id=ctx.trace_id)
                if self.breaker and err.category in ("transport", "deadline"):
                    self.breaker.failure(callee)
                back = self.retry.should_retry(err, attempt, ctx.operation, ctx.idempotency_key,
                                               None if ctx.deadline is None else ctx.deadline.remaining()) \
                    if self.retry else None
                if back is None:
                    raise err from None
                await asyncio.sleep(back)

    # -- operations -----------------------------------------------------------------------------------
    def quarantine(self, *, reason: str, actor: str) -> None:
        """Emergency disable: refuse every call until release()."""
        self.lifecycle.transition("quarantined", reason=reason, actor=actor)
        if self.audit:
            self.audit.append("quarantine", reason=reason[:128], actor=actor[:64])

    def release(self, *, reason: str, actor: str) -> None:
        self.lifecycle.transition("ready", reason=reason, actor=actor)
        if self.audit:
            self.audit.append("release", reason=reason[:128], actor=actor[:64])

    def health(self) -> dict:
        """Liveness/readiness + dependency status (GAP-019)."""
        state = self.lifecycle.state
        pol = self.policy
        deps = {
            "policy": "absent" if pol is None else ("degraded" if pol.stats["failures"] and pol.last_error else "ok"),
            "policy_authoritative": bool(pol and pol.authoritative),
            "transport": "absent" if self.transport is None else "ok",
            "audit": "absent" if self.audit is None else ("failing" if self.audit.sink_errors else "ok"),
            "open_circuits": self.breaker.open_circuits() if self.breaker else [],
        }
        adm = self.admission.snapshot() if self.admission else None
        ready = state in ("ready", "degraded") and (not self.production or (
            deps["policy_authoritative"] and deps["transport"] == "ok" and deps["audit"] == "ok"))
        return {"live": state != "stopped", "ready": ready, "state": state, "mode":
                "production" if self.production else "development", "dependencies": deps,
                "admission": adm, "residency": {"placements": len(self.residency),
                                                "revision": self.residency.revision,
                                                "stale_hits": self.residency.stale_hits,
                                                "suppressed_hits": self.residency.suppressed_hits},
                "config_revision": self.config_revision,
                "active_capabilities": {"async": True, "remote_transport": self.transport is not None,
                                        "audit": self.audit is not None, "admission": self.admission is not None}}

    def export_metrics(self) -> str:
        m = self.metrics
        if self.admission:
            s = self.admission.snapshot()
            m.set("in_flight", s["in_flight"]); m.set("admission_shed", s["shed"])
            m.set("saturation_ratio", round(s["in_flight"] / s["max_in_flight"], 6))
        m.set("residency_placements", len(self.residency))
        m.set("residency_stale_hits", self.residency.stale_hits)
        m.set("ready", 1 if self.health()["ready"] else 0)
        return m.prometheus()


__all__ = ["Chainer", "Hop", "Placement", "Residency", "DEFAULT_MAX_DEPTH", "DEFAULT_MAX_TELEMETRY_EVENTS"]
