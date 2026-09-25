"""Transport-neutral production request pipeline for INV-61 (PK_WRPC_FRAME/2).

Order of checks for every request (each stage is fail-closed, emits a typed
status, a metric, a structured log line and - for security decisions - an
audit record):

  decode -> authenticate (MAC + TLS peer binding) -> replay -> disabled/drain
  -> deadline -> interface/version -> function/fingerprint -> authorize
  -> fence (mutating calls) -> circuit breaker -> admission -> arg decode
  -> idempotency -> dispatch under deadline -> encode

Unauthenticated peers never reach interface lookup or dispatch (M03/M06).
"""
from __future__ import annotations

import concurrent.futures as cf
from dataclasses import dataclass
import hashlib
import secrets
import threading
import time
from typing import Any, Callable

from . import codec, negotiation
from .observability import Health, Metrics, StructuredLogger, TelemetryPolicy, TraceContext, Tracer
from .resilience import AdmissionController, CancellationToken, CircuitBreaker, IdempotencyCache, RETRYABLE
from .rpc import fingerprint
from .security import AuditLog, KeyRing, Policy, ReplayGuard, SecurityError, verify_mac
from .state import FenceError, FencedResource, LeaseAuthority, StateStore
from .wit_model import Interface


@dataclass
class Export:
    iface: Interface
    name: str
    impl: Callable[..., Any]
    param_type: Any      # resolved tuple type
    result_type: Any     # resolved or None
    fp: str
    mutating: bool
    wants_cancel: bool
    inline: bool = False


def _status(request_id: str, status: str, detail: str | None = None, result: bytes | None = None) -> dict:
    return {"request_id": request_id, "status": status, "detail": detail, "result": result,
            "retryable": status in RETRYABLE}



class RpcService:
    def __init__(self, *, node_id: str, keyring: KeyRing, policy: Policy, audit: AuditLog,
                 logger: StructuredLogger | None = None, metrics: Metrics | None = None,
                 tracer: Tracer | None = None, health: Health | None = None,
                 state: StateStore | None = None, limits: codec.Limits = codec.DEFAULT_LIMITS,
                 replay_window_ms: int = 30_000, admission: AdmissionController | None = None,
                 idempotency: IdempotencyCache | None = None, leases: LeaseAuthority | None = None,
                 clock_ms: Callable[[], int] = lambda: int(time.time() * 1000),
                 workers: int = 32, telemetry: TelemetryPolicy | None = None) -> None:
        from . import __version__
        self.node_id = node_id
        self.keyring, self.policy, self.audit = keyring, policy, audit
        self.log = logger or StructuredLogger(node_id, sink=lambda _l: None)
        self.metrics = metrics or Metrics()
        self.tracer = tracer or Tracer()
        self.health = health or Health(__version__)
        self.state = state
        self.limits = limits  # applies to argument/result values
        # envelope fields use default string/collection bounds, frame-size capped
        self.env_limits = codec.Limits(max_frame_bytes=limits.max_frame_bytes)
        self.replay = ReplayGuard(replay_window_ms, not_before_ms=clock_ms())
        self.admission = admission or AdmissionController()
        self.idem = idempotency or IdempotencyCache()
        self.leases = leases or LeaseAuthority()
        self.fence = FencedResource()
        self.clock_ms = clock_ms
        self.telemetry = telemetry or TelemetryPolicy()
        self.exports: dict[tuple[str, str], Export] = {}
        self.versions: dict[str, str] = {}
        self.breakers: dict[tuple[str, str], CircuitBreaker] = {}
        self.disabled = False
        self.draining = False
        self.owner_epoch: int | None = None
        self._tokens: dict[str, CancellationToken] = {}
        self._tlock = threading.Lock()
        self._pool = cf.ThreadPoolExecutor(max_workers=workers, thread_name_prefix="inv61-call")
        self._inflight = 0
        self._inflight_lock = threading.Lock()
        self.health.capabilities = []
        for name, kind, help_ in (
            ("inv61_requests_total", "counter", "Requests by interface, function and status"),
            ("inv61_request_seconds", "histogram", "Server-side request latency"),
            ("inv61_inflight", "gauge", "Calls currently dispatched"),
        ):
            self.metrics.describe(name, kind, help_)
        if state is not None:
            self._restore()

    # ------------------------------------------------------------ registry
    def export(self, iface: Interface, func: str, impl: Callable[..., Any], *, mutating: bool = False,
               wants_cancel: bool = False, inline: bool = False) -> None:
        """Register ``impl`` for a WIT-declared function.

        ``inline=True`` (direct composition, C066) runs a callee that is known
        to be non-blocking and bounded on the receiving thread, skipping the
        worker-pool hop.  Its deadline is checked after it returns; a hanging
        inline callee is NOT abandoned, so blocking or unbounded callees must
        never be exported inline.
        """
        f = iface.funcs.get(func)
        if f is None:
            raise ValueError(f"{func} is not declared in {iface.qualified}")
        key = (iface.qualified, func)
        if key in self.exports:
            raise ValueError(f"duplicate export {key}")
        if not callable(impl):
            raise TypeError("impl must be callable")
        prev = self.versions.setdefault(iface.qualified, iface.version)
        if prev != iface.version:
            raise ValueError("one version per interface per service")
        self.exports[key] = Export(
            iface, func, impl,
            ("tuple", tuple(iface.resolve(t) for _, t in f.params)),
            None if f.result is None else iface.resolve(f.result),
            fingerprint(f.param_types(), f.result_types()), mutating, wants_cancel, inline)
        self.breakers[key] = CircuitBreaker()
        self.health.capabilities.append(f"{iface.qualified}@{iface.version}#{func}")

    # ------------------------------------------------------ ownership (M19)
    def acquire_ownership(self, resource: str, ttl_s: float) -> bool:
        lease = self.leases.acquire(resource, self.node_id, ttl_s)
        self.owner_epoch = lease.epoch if lease else None
        return lease is not None

    # -------------------------------------------------- emergency controls
    def set_disabled(self, disabled: bool, actor: str) -> None:
        self.disabled = self.health.disabled = disabled
        self.audit.append("emergency-disable" if disabled else "emergency-enable", actor=actor, node=self.node_id)
        self.log.warning("emergency-disable" if disabled else "emergency-enable", actor=actor)
        self.checkpoint()

    def begin_drain(self) -> None:
        self.draining = self.health.draining = True

    def inflight(self) -> int:
        return self._inflight

    # ------------------------------------------------- durable state (M20)
    def checkpoint(self) -> None:
        if self.state is None:
            return
        self.state.save({"idempotency": self.idem.snapshot(), "fence": self.fence.highest,
                         "lease_epoch": self.leases.epoch, "audit_head": self.audit.head,
                         "audit_seq": self.audit.seq, "disabled": self.disabled})

    def _restore(self) -> None:
        st = self.state.load()
        if not st:
            return
        self.idem.restore(st.get("idempotency", []))
        self.fence.highest = int(st.get("fence", 0))
        self.leases._epoch = max(self.leases.epoch, int(st.get("lease_epoch", 0)))
        self.disabled = self.health.disabled = bool(st.get("disabled", False))
        # The audit log must contain at least what the checkpoint anchored.
        if self.audit.seq < int(st.get("audit_seq", 0)):
            raise SecurityError("audit-truncated-since-checkpoint")

    # ------------------------------------------------------ negotiation (M05)
    def hello(self, body: bytes) -> bytes:
        try:
            h = codec.decode(codec.HELLO, body, self.limits)
            key = self.keyring.lookup(h["peer"], self.clock_ms() / 1000)
            chosen = negotiation.choose(h["offered"], h["min_accepted"])
        except (codec.CodecError, SecurityError, negotiation.NegotiationError) as e:
            code = getattr(e, "code", "negotiation")
            self.audit.append("negotiation-failure", reason=code)
            self.metrics.inc("inv61_handshakes_total", status="fail")
            raise negotiation.NegotiationError(code) from None
        server_nonce = secrets.token_hex(16)
        blob = negotiation.transcript(h["peer"], h["offered"], h["min_accepted"], h["client_nonce"],
                                      self.node_id, chosen, server_nonce)
        self.metrics.inc("inv61_handshakes_total", status="ok")
        return codec.encode(codec.HELLO_ACK, {"peer": self.node_id, "chosen": chosen,
                                              "server_nonce": server_nonce,
                                              "transcript_mac": negotiation.transcript_mac(key.secret, blob)})

    def cancel(self, body: bytes) -> None:
        try:
            rid = codec.decode(codec.CANCEL, body, self.limits)["request_id"]
        except codec.CodecError:
            return
        with self._tlock:
            tok = self._tokens.get(rid)
        if tok:
            tok.cancel("cancelled")

    # ---------------------------------------------------------- requests
    def handle(self, body: bytes, tls_peer: str | None = None) -> bytes:
        t0 = time.perf_counter()
        resp, labels = self._handle(body, tls_peer)
        self.metrics.inc("inv61_requests_total", **labels)
        self.metrics.observe("inv61_request_seconds", time.perf_counter() - t0,
                             interface=labels["interface"], function=labels["function"])
        self.health.heartbeat()
        try:
            return codec.encode(codec.RESPONSE_ENVELOPE, resp, self.env_limits)
        except codec.CodecError:
            # Never let a response-encoding failure escape to the transport:
            # fall back to a minimal typed error that always fits.
            self.metrics.inc("inv61_response_encode_failures_total")
            return codec.encode(codec.RESPONSE_ENVELOPE, _status("", "internal", "response-encode"))

    def _handle(self, body: bytes, tls_peer: str | None) -> tuple[dict, dict]:
        lab = {"interface": "-", "function": "-", "status": "?"}

        def done(env_id: str, status: str, detail: str | None = None, result: bytes | None = None):
            lab["status"] = status
            return _status(env_id, status, detail, result), lab

        try:
            env = codec.decode(codec.REQUEST_ENVELOPE, body, self.env_limits)
        except codec.CodecError as e:
            return done("", "malformed-frame", e.code)
        rid = env["request_id"]
        now_ms = self.clock_ms()

        # authentication before anything that reveals interface state
        try:
            key = verify_mac(env, self.keyring, now_ms / 1000)
            if tls_peer is not None and tls_peer != key.principal:
                raise SecurityError("tls-peer-mismatch")
        except SecurityError as e:
            self.audit.append("authn-failure", reason=e.code, key_id=env["key_id"][:64])
            self.log.warning("authn-failure", reason=e.code, request_id=rid[:64])
            return done(rid, "unauthenticated")
        principal, tenant = key.principal, env["tenant"]
        try:
            self.replay.check(principal, env["nonce"], env["issued_ms"], now_ms)
        except SecurityError as e:
            if e.code == "replay-cache-full":  # capacity, not an attack: retryable shed
                self.metrics.inc("inv61_replay_cache_full_total")
                return done(rid, "overloaded", "replay-cache-full")
            self.audit.append("replay-rejected", principal=principal, reason=e.code, request_id=rid[:64])
            return done(rid, "replay", e.code)

        if self.disabled:
            return done(rid, "disabled")
        if self.draining:
            return done(rid, "draining")
        if now_ms >= env["deadline_ms"]:
            return done(rid, "deadline-exceeded")

        iface_q = env["interface"]
        ver = self.versions.get(iface_q)
        if ver is None:
            return done(rid, "unknown-interface")
        if env["version"] != ver:
            self.audit.append("version-drift", principal=principal, interface=iface_q,
                              offered=env["version"][:64], expected=ver)
            return done(rid, "version-mismatch", ver)
        ex = self.exports.get((iface_q, env["function"]))
        if ex is None:
            return done(rid, "unknown-function")
        lab["interface"], lab["function"] = iface_q, ex.name
        if env["fp"] != ex.fp:
            self.audit.append("signature-mismatch", principal=principal, interface=iface_q, function=ex.name)
            return done(rid, "signature-mismatch")

        dec = self.policy.decide(principal, tenant, iface_q, ex.name, now_ms / 1000)
        if not dec.allowed:
            self.audit.append("authz-deny", principal=principal, tenant=tenant, interface=iface_q,
                              function=ex.name, reason=dec.reason, policy=self.policy.version)
            return done(rid, "permission-denied", dec.reason)

        if ex.mutating:
            try:
                if self.owner_epoch is None:
                    raise FenceError("not owner")
                self.fence.check(self.owner_epoch)
            except FenceError:
                self.audit.append("fence-rejected", interface=iface_q, function=ex.name)
                return done(rid, "fenced")

        breaker = self.breakers[(iface_q, ex.name)]
        if not breaker.allow():
            return done(rid, "circuit-open")
        adm = self.admission.admit(tenant)
        if adm != "ok":
            return done(rid, adm)
        try:
            return self._dispatch(env, ex, principal, tenant, breaker, done)
        finally:
            self.admission.release(tenant)

    def _dispatch(self, env, ex: Export, principal, tenant, breaker, done):
        rid = env["request_id"]
        try:
            args = codec.decode(ex.param_type, env["args"], self.limits)
        except codec.CodecError as e:
            breaker.record(True)
            return done(rid, "invalid-args", e.code)

        idem_key = None
        if env["idempotency_key"] is not None:
            idem_key = (tenant, principal, ex.iface.qualified, ex.name, env["idempotency_key"])
            digest = hashlib.sha256(env["args"]).hexdigest()
            state, cached = self.idem.begin(idem_key, digest)
            if state == "done":
                self.metrics.inc("inv61_idempotent_replays_total")
                return done(rid, "ok", "idempotent-replay", cached)
            if state == "running":
                return done(rid, "unavailable", "in-progress")
            if state == "conflict":
                return done(rid, "idempotency-conflict")
            if state == "full":
                return done(rid, "overloaded", "idempotency-cache-full")

        parent = TraceContext.parse(env["traceparent"])
        span = self.tracer.start(f"{ex.iface.qualified}/{ex.name}", parent)
        tok = CancellationToken()
        with self._tlock:
            self._tokens[rid] = tok
        with self._inflight_lock:
            self._inflight += 1
            self.metrics.set("inv61_inflight", self._inflight)
        try:
            kwargs = {"cancel": tok} if ex.wants_cancel else {}
            remaining = max(0.0, (env["deadline_ms"] - self.clock_ms()) / 1000)
            try:
                if ex.inline:
                    value = ex.impl(*args, **kwargs)
                    if self.clock_ms() >= env["deadline_ms"]:
                        raise cf.TimeoutError
                else:
                    value = self._pool.submit(ex.impl, *args, **kwargs).result(timeout=remaining)
            except cf.TimeoutError:
                tok.cancel("deadline")
                if idem_key:
                    self.idem.abort(idem_key)
                self.tracer.finish(span, "deadline-exceeded", **{"rpc.status": "deadline-exceeded"})
                return done(rid, "deadline-exceeded")
            except Exception:
                breaker.record(False)
                if idem_key:
                    self.idem.abort(idem_key)
                self.tracer.finish(span, "callee-trap", **{"rpc.status": "callee-trap"})
                return done(rid, "callee-trap")
            if tok.cancelled:
                if idem_key:
                    self.idem.abort(idem_key)
                return done(rid, "cancelled")
            try:
                payload = b"" if ex.result_type is None else codec.encode(ex.result_type, value, self.limits)
            except codec.CodecError:
                breaker.record(False)
                if idem_key:
                    self.idem.abort(idem_key)
                return done(rid, "callee-trap", "result-type")
            breaker.record(True)
            if idem_key:
                self.idem.complete(idem_key, payload)
                self.checkpoint()
            self.tracer.finish(span, "ok", **{"rpc.status": "ok", "rpc.interface": ex.iface.qualified,
                                             "rpc.function": ex.name})
            return done(rid, "ok", None, payload)
        finally:
            with self._tlock:
                self._tokens.pop(rid, None)
            with self._inflight_lock:
                self._inflight -= 1
                self.metrics.set("inv61_inflight", self._inflight)

    def close(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)
        self.checkpoint()
