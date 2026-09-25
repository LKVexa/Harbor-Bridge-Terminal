"""ControlEndpoint - the full-stack INV-36 path over any byte stream.

    stream -> Connection (PK_CTRL_STREAM/1)
           -> quarantine + connection limits -> PK_CTRL_HS/1 -> Session (PK_CTRL_FRAME/2)
           -> decode PK_CTRL_MSG/1 -> dedup -> quarantine(op) -> authorize -> admit -> handler

Unauthenticated bytes never reach decode/dispatch (MC-14.014); authorization is
the single decision point before side effects (MC-07.008); overload handling
happens after authentication and authorization (MC-09.020).
"""
from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from .audit_log import AuditLog
from .errors import ErrorCode, Inv36Error
from .handshake import ClientHandshake, HandshakeError, HandshakePolicy, HandshakeResult, ServerHandshake, new_registry
from .health import AdmissionController, HealthMonitor, OverloadError, PRIORITY_OF, Priority
from .keys import SigningKey
from .messages import ControlMessage, MessageFormatError, UnknownMessageType, decode
from .observability import MetricsRegistry, StructuredLogger, Tracer, accept_trace
from .policy import Authorizer, AuthzError, Principal
from .quarantine import Context, Directive, QuarantineError, QuarantineRegistry, Scope
from .recovery import DedupWindow
from .stream import FRAME, HANDSHAKE, Connection, StreamError
from .transport import AuthFailure, OutOfOrder, Replay, Session, TransportError

Handler = Callable[[Principal, ControlMessage], "ControlMessage | None"]


class ConnectionLimit(Inv36Error, RuntimeError):
    code = ErrorCode.CONNECTION_LIMIT


@dataclass
class PenaltyBox:
    """Isolate peers after repeated authentication failures (MC-03.031)."""

    limit: int = 5
    cooldown_s: float = 60.0
    clock: Callable[[], float] = time.monotonic
    _fails: dict[str, list[float]] = field(default_factory=dict, init=False)

    def record(self, peer: str) -> bool:
        now = self.clock()
        lst = [t for t in self._fails.get(peer, []) if now - t < self.cooldown_s] + [now]
        if len(self._fails) > 4096:
            self._fails.clear()
        self._fails[peer] = lst
        return len(lst) >= self.limit

    def blocked(self, peer: str) -> bool:
        now = self.clock()
        return len([t for t in self._fails.get(peer, []) if now - t < self.cooldown_s]) >= self.limit


@dataclass
class EndpointConfig:
    node: str = "node-0"
    site: str = "site-0"
    max_sessions: int = 256
    max_sessions_per_tenant: int = 64
    session_max_age_s: float = 3600.0
    session_max_frames: int = 1 << 32
    auth_failure_limit: int = 5
    trust_peer_trace: bool = True
    build_digest: str = ""


class Channel:
    def __init__(self, ep: "ControlEndpoint", conn: Connection, session: Session, hs: HandshakeResult,
                 source: str) -> None:
        self.ep, self.conn, self.session = ep, conn, session
        self.peer = Principal.from_credential(hs.peer)
        self.evidence = hs.evidence()
        self.source = source
        self.established = time.monotonic()
        self.correlation = hashlib.sha256(hs.session_id).hexdigest()[:16]
        self.closed = False
        self._lock = threading.Lock()

    # -- lifecycle -------------------------------------------------------------------
    def needs_rekey(self) -> bool:
        age = time.monotonic() - self.established
        frames = max(self.session.send_seq, self.session.recv_seq)
        return age >= self.ep.cfg.session_max_age_s or frames >= self.ep.cfg.session_max_frames

    def close(self, reason: str = "closed", *, graceful: bool = True) -> None:
        with self._lock:
            if self.closed:
                return
            self.closed = True
        self.session.close()                # drop traffic keys (MC-11.014)
        self.conn.close(graceful=graceful)  # close socket, discard buffered bytes
        self.ep._forget(self, reason)

    def ctx(self, operation: str = "") -> Context:
        return Context(subject=self.peer.subject, tenant=self.peer.tenant, endpoint=self.source,
                       node=self.ep.cfg.node, site=self.ep.cfg.site, operation=operation)

    # -- data path ---------------------------------------------------------------------
    def send(self, msg: ControlMessage) -> None:
        if self.closed:
            raise TransportError("channel closed", code=ErrorCode.SESSION_CLOSED)
        t0 = time.perf_counter()
        frame = self.session.seal(msg.encode())
        self.ep.metrics.observe("inv36_latency_seconds", time.perf_counter() - t0, stage="seal")
        self.conn.send_record(FRAME, frame)
        self.ep.metrics.inc("inv36_frames_total", direction="out")
        self.ep.metrics.observe("inv36_frame_bytes", len(frame))
        self.ep.health.progress()

    def receive(self) -> ControlMessage:
        """Receive one authenticated message (no dispatch). Integrity failures close the channel."""
        try:
            rtype, payload = self.conn.recv_record()
        except StreamError:
            self.close("stream_failure", graceful=False)  # asymmetric failure: drop our half too
            raise
        if rtype != FRAME:
            self.close("unexpected_record", graceful=False)
            raise TransportError("unexpected record type after handshake", code=ErrorCode.FRAME_FORMAT)
        t0 = time.perf_counter()
        try:
            plaintext = self.session.open(payload)
        except AuthFailure:
            self.ep._integrity("auth_failure", self)
            raise
        except (Replay, OutOfOrder) as exc:
            self.ep._integrity(exc.code.name.lower(), self)
            raise
        except TransportError as exc:
            self.ep._integrity(exc.code.name.lower(), self)
            raise
        self.ep.metrics.observe("inv36_latency_seconds", time.perf_counter() - t0, stage="open")
        self.ep.metrics.inc("inv36_frames_total", direction="in")
        self.ep.health.progress()
        try:
            return decode(plaintext)
        except (MessageFormatError, UnknownMessageType) as exc:
            self.ep._integrity(exc.code.name.lower(), self, close=isinstance(exc, MessageFormatError))
            raise

    def serve_one(self) -> ControlMessage | None:
        """Receive, authorize and dispatch one message; return the handler's reply (already sent)."""
        msg = self.receive()
        return self.ep._dispatch(self, msg)


class ControlEndpoint:
    def __init__(self, *, identity: SigningKey, credential: bytes, hs_policy: HandshakePolicy,
                 authorizer: Authorizer, quarantine: QuarantineRegistry, audit: AuditLog | None = None,
                 metrics: MetricsRegistry | None = None, logger: StructuredLogger | None = None,
                 health: HealthMonitor | None = None, admission: AdmissionController | None = None,
                 dedup: DedupWindow | None = None, cfg: EndpointConfig | None = None,
                 handlers: dict[str, Handler] | None = None, config_store=None) -> None:
        self.identity, self.credential, self.hs_policy = identity, credential, hs_policy
        self.authorizer, self.quarantine, self.audit = authorizer, quarantine, audit
        self.metrics = metrics or MetricsRegistry()
        self.logger = logger or StructuredLogger(level="warning")
        self.health = health or HealthMonitor()
        self.admission = admission or AdmissionController()
        self.dedup = dedup or DedupWindow()
        self.cfg = cfg or EndpointConfig()
        self.handlers = dict(handlers or {})
        self.tracer = Tracer(metrics=self.metrics)
        self.registry = new_registry(hs_policy.session_id_cache)
        self.penalty = PenaltyBox(self.cfg.auth_failure_limit)
        self.channels: set[Channel] = set()
        self._lock = threading.Lock()
        self.decisions: list[dict] = []  # bounded explain history
        self.config_store = config_store
        self.draining = False
        quarantine.register_terminator(self._terminate_matching)

    # -- bookkeeping ---------------------------------------------------------------------
    def _audit(self, ev: str, data: dict, **kw) -> None:
        if self.audit is not None:
            self.audit.emit(ev, data, **kw)

    def _decision(self, kind: str, reason: str, **data) -> None:
        rec = {"t": round(time.time(), 3), "kind": kind, "reason": reason, **data}
        self.decisions.append(rec)
        del self.decisions[:-256]

    def _forget(self, ch: Channel, reason: str) -> None:
        with self._lock:
            self.channels.discard(ch)
            self.metrics.set("inv36_active_sessions", len(self.channels))
        self.logger.log("info", "session_closed", reason=reason, session=ch.correlation)

    def _integrity(self, reason: str, ch: Channel, *, close: bool = True) -> None:
        self.metrics.inc("inv36_integrity_failures_total", reason=reason)
        if reason == "auth_failure":
            self.metrics.inc("inv36_auth_failures_total")
        self.logger.log("security", "integrity_failure", reason=reason, session=ch.correlation)
        self._audit("integrity.failure", {"reason": reason}, actor=ch.peer.subject, tenant=ch.peer.tenant,
                    correlation_id=ch.correlation)
        self._decision("integrity", reason, peer=ch.peer.subject)
        if self.penalty.record(ch.peer.subject) or self.penalty.record("src:" + ch.source):
            self._audit("replay.threshold", {"reason": reason}, actor=ch.peer.subject)
        if close:
            ch.close(f"integrity:{reason}", graceful=False)

    def _terminate_matching(self, d: Directive) -> int:
        with self._lock:
            victims = [c for c in self.channels if d.scope is Scope.GLOBAL or c.ctx().value(d.scope) == d.value]
        for c in victims:
            c.close(f"quarantine:{d.directive_id}", graceful=False)
        return len(victims)

    # -- establishment ---------------------------------------------------------------------
    def _limits(self, tenant: str) -> None:
        with self._lock:
            if len(self.channels) >= self.cfg.max_sessions:
                raise ConnectionLimit("process session limit reached")
            if sum(1 for c in self.channels if c.peer.tenant == tenant) >= self.cfg.max_sessions_per_tenant:
                raise ConnectionLimit("tenant session limit reached", detail={"tenant_limit": True})

    def _pre_accept(self, source: str):
        def check(peer) -> None:
            if self.penalty.blocked(peer.subject) or self.penalty.blocked("src:" + source):
                raise HandshakeError("peer isolated after repeated failures", code=ErrorCode.HS_POLICY)
            self.quarantine.check_session(Context(subject=peer.subject, tenant=peer.tenant, endpoint=source,
                                                  node=self.cfg.node, site=self.cfg.site))
            self._limits(peer.tenant)
        return check

    def _register(self, conn: Connection, hs: HandshakeResult, source: str) -> Channel:
        session = Session(hs.local.subject, hs.peer.subject, hs.shared, session_id=hs.session_id)
        hs.wipe()
        ch = Channel(self, conn, session, hs, source)
        with self._lock:
            self.channels.add(ch)
            self.metrics.set("inv36_active_sessions", len(self.channels))
        self.metrics.inc("inv36_handshakes_total", outcome="success")
        self.metrics.observe("inv36_latency_seconds", hs.completed - hs.started, stage="handshake")
        self._audit("handshake.success", hs.evidence(), actor=hs.peer.subject, tenant=hs.peer.tenant,
                    correlation_id=ch.correlation)
        self.health.progress()
        return ch

    def _hs_failed(self, exc: Exception, source: str) -> None:
        code = getattr(exc, "code", None)
        name = code.name if isinstance(code, ErrorCode) else type(exc).__name__
        self.metrics.inc("inv36_handshakes_total", outcome="failure", code=name)
        self.logger.log("security", "handshake_failure", reason=name, endpoint=source)
        self._audit("handshake.failure", {"code": name, "source": source})
        self._decision("handshake", name, source=source)
        if isinstance(code, ErrorCode) and code.disposition.value in ("integrity_failure", "denied"):
            self.penalty.record("src:" + source)

    def drain(self, *, reason: str = "drain") -> int:
        """Stop admitting new sessions, then close every channel gracefully (MC-03.025).

        Work is synchronous per channel, so there is no queued outbound work to
        flush beyond what callers are already sending; each close sends a CLOSE
        record bounded by a 1 s write deadline.
        """
        self.draining = True
        with self._lock:
            victims = list(self.channels)
        for c in victims:
            c.close(reason, graceful=True)
        self._decision("lifecycle", "drained", closed=len(victims))
        return len(victims)

    def accept(self, conn: Connection, *, source: str = "unknown") -> Channel:
        try:
            if self.draining:
                raise HandshakeError("endpoint draining", code=ErrorCode.NOT_READY)
            if self.penalty.blocked("src:" + source):
                raise HandshakeError("source isolated", code=ErrorCode.HS_POLICY)
            self.quarantine.check_session(Context(endpoint=source, node=self.cfg.node, site=self.cfg.site))
            conn.exchange_preamble()
            srv = ServerHandshake(self.hs_policy, self.identity, self.credential, self.registry,
                                  pre_accept=self._pre_accept(source))
            rtype, ch_msg = conn.recv_record()
            if rtype != HANDSHAKE:
                raise HandshakeError("expected CLIENT_HELLO", code=ErrorCode.HS_FORMAT)
            conn.send_record(HANDSHAKE, srv.on_client_hello(ch_msg))
            rtype, cf = conn.recv_record()
            if rtype != HANDSHAKE:
                raise HandshakeError("expected CLIENT_FINISH", code=ErrorCode.HS_FORMAT)
            return self._register(conn, srv.on_client_finish(cf), source)
        except (Inv36Error, StreamError) as exc:
            self._hs_failed(exc, source)
            conn.close()
            raise

    def connect(self, conn: Connection, *, source: str = "unknown") -> Channel:
        try:
            if self.draining:
                raise HandshakeError("endpoint draining", code=ErrorCode.NOT_READY)
            self.quarantine.check_session(Context(endpoint=source, node=self.cfg.node, site=self.cfg.site))
            conn.exchange_preamble()
            cli = ClientHandshake(self.hs_policy, self.identity, self.credential)
            conn.send_record(HANDSHAKE, cli.hello())
            rtype, sh = conn.recv_record()
            if rtype != HANDSHAKE:
                raise HandshakeError("expected SERVER_HELLO", code=ErrorCode.HS_FORMAT)
            cf, result = cli.on_server_hello(sh)
            self.quarantine.check_session(Context(subject=result.peer.subject, tenant=result.peer.tenant,
                                                  endpoint=source, node=self.cfg.node, site=self.cfg.site))
            conn.send_record(HANDSHAKE, cf)
            return self._register(conn, result, source)
        except (Inv36Error, StreamError) as exc:
            self._hs_failed(exc, source)
            conn.close()
            raise

    # -- dispatch ---------------------------------------------------------------------------
    def _dispatch(self, ch: Channel, msg: ControlMessage) -> ControlMessage | None:
        op = msg.type_name
        trace = accept_trace(msg.traceparent, trusted_peer=self.cfg.trust_peer_trace)
        if not self.dedup.check_and_record(msg.op_id):
            self._decision("dedup", "duplicate_op_id", op=op)
            self.metrics.inc("inv36_integrity_failures_total", reason="duplicate_op")
            return None
        # quarantine precedence over allow policy (MC-11.003)
        privileged = PRIORITY_OF.get(op, Priority.NORMAL) is not Priority.OPTIONAL
        try:
            self.quarantine.check_operation(ch.ctx(op), privileged=privileged)
        except QuarantineError:
            self._decision("quarantine", "operation_quarantined", op=op, peer=ch.peer.subject)
            raise
        with self.tracer.span("policy", trace, op=op):
            try:
                decision = self.authorizer.enforce(ch.peer, msg.msg_type, msg.tenant)
            except AuthzError as exc:
                self.metrics.inc("inv36_authz_denials_total", reason=str(exc.detail.get("reason", exc.code.name)))
                self._decision("authz", str(exc.detail.get("reason")), op=op, peer=ch.peer.subject)
                self.logger.log("security", "authz_denied", reason=str(exc.detail.get("reason")),
                                tenant=msg.tenant, session=ch.correlation)
                raise
        prio = PRIORITY_OF.get(op, Priority.NORMAL)
        try:
            self.admission.admit(msg.tenant, prio)
        except OverloadError:
            self.metrics.inc("inv36_dropped_total", priority=prio.name)
            self._decision("admission", "shed", op=op, priority=prio.name)
            raise
        self.metrics.set("inv36_queue_depth", self.admission.depth)
        self.metrics.set("inv36_saturation_ratio", self.admission.saturation)
        self.health.queue_saturation = self.admission.saturation
        try:
            handler = self.handlers.get(op)
            if handler is None:
                self._decision("dispatch", "no_handler", op=op)
                return None
            with self.tracer.span("dispatch", trace, op=op):
                reply = handler(ch.peer, msg)
            self._decision("dispatch", decision.reason, op=op, policy_version=decision.policy_version)
            if reply is not None:
                ch.send(reply)
            return reply
        finally:
            self.admission.release(msg.tenant)

    # -- operator views -----------------------------------------------------------------------
    def explain(self) -> dict:
        """Operator explain view (MC-12.020)."""
        h = self.health.evaluate()
        try:
            pv = self.authorizer.store.current().version
        except AuthzError:
            pv = None
        from . import __version__, _wire
        cfg = self.config_store.current.provenance() if self.config_store is not None and \
            getattr(self.config_store, "_current", None) is not None else None
        flags = dict(self.config_store.current.values["feature_flags"]) if cfg else {}
        return {
            "schema": "inv36.explain/1", "version": __version__, "build_digest": self.cfg.build_digest,
            "node": self.cfg.node, "site": self.cfg.site, "draining": self.draining,
            "protocols": {"stream": f"PK_CTRL_STREAM/{_wire.STREAM_VERSION}", "handshake": f"PK_CTRL_HS/{_wire.HS_VERSION}",
                          "frame": f"PK_CTRL_FRAME/{_wire.FRAME_VERSION}", "message": f"PK_CTRL_MSG/{_wire.MSG_VERSION}"},
            "capabilities": {"operations": sorted(self.handlers), "feature_flags": flags},
            "config": cfg, "health": h, "policy_version": pv,
            "active_sessions": len(self.channels),
            "sessions": [{"peer": c.peer.subject, "role": c.peer.role, "tenant": c.peer.tenant,
                          "age_s": round(time.monotonic() - c.established, 3), "send_seq": c.session.send_seq,
                          "recv_seq": c.session.recv_seq, "needs_rekey": c.needs_rekey(),
                          "correlation": c.correlation} for c in list(self.channels)],
            "queue": {"depth": self.admission.depth, "high_water": self.admission.high_water,
                      "shedding": self.admission.shedding, "shed": dict(self.admission.shed_count)},
            "quarantine": self.quarantine.state(),
            "recent_decisions": self.decisions[-32:],
        }
