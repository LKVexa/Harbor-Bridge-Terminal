"""HTTP/1.1 + JSON transport with mTLS and NDJSON watch streaming (MC-014, MC-022, MC-030).

Endpoints (all JSON; errors use the structured error model with the HTTP
status derived from the error code):

    POST /v1/hello            protocol negotiation (unauthenticated handshake data only)
    POST /v1/txn | /v1/range | /v1/compact
    POST /v1/lease/grant | /v1/lease/keepalive | /v1/lease/revoke
    POST /v1/watch            chunked NDJSON stream of frames (events/progress/canceled)
    POST /v1/admin/<action>   freeze, unfreeze, drain, quarantine, maintenance, break_glass,
                              policy, policy_rollback, loglevel, explain, diagnostics
    GET  /livez /readyz /version      (shallow, no sensitive detail)
    GET  /metrics             Prometheus text (requires admin.diagnostics unless loopback metrics enabled)

Request headers: ``traceparent`` (W3C), ``x-request-id``, ``x-cstate-deadline-ms``,
``x-cstate-attempt``, ``x-cstate-namespace`` (admin cross-namespace target:
``tenant/env/site/workload``), ``authorization: Bearer <token>`` (only if enabled).
"""
from __future__ import annotations

import json
import re
import socket
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .errors import ERROR_CATALOG, InvalidArgument, StateError, Unauthenticated, to_wire
from .schema import loads
from .security import CLUSTER, MTLSAuthenticator, Namespace, TokenAuthenticator
from .service import CancelToken, ControlStateService, RequestContext

_RID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class _Handler(BaseHTTPRequestHandler):
    server: "ControlStateHTTPServer"
    protocol_version = "HTTP/1.1"
    server_version = "inv05"
    sys_version = ""

    def log_message(self, fmt: str, *args: Any) -> None:  # structured logger handles request logs
        return

    # -------------------------------------------------------------- plumbing
    def _send(self, status: int, obj: Any, ctype: str = "application/json") -> None:
        body = obj.encode() if isinstance(obj, str) else json.dumps(obj, sort_keys=True, default=str).encode()
        self.send_response(status)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        self.server.svc.metrics.inc("cstate_net_bytes_total", len(body), dir="out")

    def _err(self, exc: BaseException) -> None:
        w = to_wire(exc)
        headers = {}
        if "retry_after_s" in w["details"]:
            headers["retry-after"] = str(max(1, int(round(w["details"]["retry_after_s"]))))
        body = json.dumps({"error": w}).encode()
        self.send_response(ERROR_CATALOG[w["code"]].http_status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> Any:
        n = self.headers.get("content-length")
        if n is None or not n.isdigit():
            raise InvalidArgument("content-length required", field="content-length")
        n = int(n)
        limit = self.server.svc.limits.max_request_bytes
        if n > limit:
            from .errors import LimitExceeded
            raise LimitExceeded("request too large", limit="max_request_bytes", limit_value=limit)
        raw = self.rfile.read(n)
        self.server.svc.metrics.inc("cstate_net_bytes_total", len(raw), dir="in")
        return loads(raw, limit)

    def _principal(self):
        cert = None
        if isinstance(self.connection, ssl.SSLSocket):
            cert = self.connection.getpeercert()
        if cert:
            return self.server.mtls.authenticate(cert)
        auth = self.headers.get("authorization", "")
        if self.server.tokens and auth.lower().startswith("bearer "):
            return self.server.tokens.authenticate(auth[7:].strip())
        raise Unauthenticated("no client identity presented")

    def _ctx(self) -> RequestContext:
        try:
            p = self._principal()
        except Unauthenticated as exc:
            self.server.svc.metrics.inc("cstate_authn_failures_total", reason="rejected")
            self.server.svc.audit.record("authn", "authenticate", actor="anonymous", outcome="failed",
                                         source_identity=self.client_address[0], reason=str(exc)[:80])
            self.server.svc.log.log("WARN", "CS2000", "authentication failed", peer=self.client_address[0])
            raise
        rid = self.headers.get("x-request-id", "")
        ctx = RequestContext(p, traceparent=self.headers.get("traceparent"), cancel=CancelToken())
        if rid:
            if not _RID.match(rid):
                raise InvalidArgument("invalid x-request-id", field="x-request-id")
            ctx.request_id = rid
        dl = self.headers.get("x-cstate-deadline-ms")
        if dl:
            if not dl.isdigit() or not 0 < int(dl) <= 600_000:
                raise InvalidArgument("invalid deadline header", field="x-cstate-deadline-ms")
            ctx.deadline = time.monotonic() + int(dl) / 1000
        at = self.headers.get("x-cstate-attempt", "1")
        ctx.attempt = int(at) if at.isdigit() and 0 < int(at) < 100 else 1
        return ctx

    def _target(self) -> Namespace | None:
        t = self.headers.get("x-cstate-namespace")
        if not t:
            return None
        parts = t.split("/")
        if len(parts) != 4:
            raise InvalidArgument("x-cstate-namespace must be tenant/env/site/workload", field="x-cstate-namespace")
        return Namespace(*parts)

    # -------------------------------------------------------------- routes
    def do_GET(self) -> None:
        svc = self.server.svc
        try:
            if self.path == "/livez":
                r = svc.liveness()
                return self._send(200 if r["status"] == "ok" else 503, {"status": r["status"]})
            if self.path == "/readyz":
                r = svc.readiness()
                return self._send(200 if r["status"] in ("ready", "degraded") else 503, {"status": r["status"]})
            if self.path == "/version":
                return self._send(200, svc.version())
            if self.path == "/metrics":
                ctx = self._ctx()
                svc.authz.require(ctx.principal, "admin.diagnostics", CLUSTER)
                svc.refresh_gauges()
                return self._send(200, svc.metrics.render(), "text/plain; version=0.0.4")
            self._send(404, {"error": {"code": "CSTATE_INVALID_ARGUMENT", "message": "not found"}})
        except BaseException as exc:  # noqa: BLE001 - mapped to safe wire errors
            self._err(exc)

    def do_POST(self) -> None:
        svc = self.server.svc
        try:
            if self.path == "/v1/hello":
                return self._send(200, svc.hello(self._body()))
            ctx = self._ctx()
            body = self._body()
            target = self._target()
            p = self.path
            if p == "/v1/txn":
                return self._send(200, svc.txn(ctx, body, target))
            if p == "/v1/range":
                return self._send(200, svc.range(ctx, body, target))
            if p == "/v1/compact":
                return self._send(200, svc.compact(ctx, body))
            if p == "/v1/lease/grant":
                return self._send(200, svc.lease_grant(ctx, body))
            if p == "/v1/lease/keepalive":
                return self._send(200, svc.lease_keepalive(ctx, body))
            if p == "/v1/lease/revoke":
                return self._send(200, svc.lease_revoke(ctx, body))
            if p == "/v1/watch":
                return self._stream_watch(ctx, body, target)
            if p.startswith("/v1/admin/"):
                return self._send(200, self._admin(ctx, p[len("/v1/admin/"):], body))
            self._send(404, {"error": {"code": "CSTATE_INVALID_ARGUMENT", "message": "not found"}})
        except BaseException as exc:  # noqa: BLE001
            self._err(exc)

    def _admin(self, ctx: RequestContext, action: str, body: dict[str, Any]) -> Any:
        svc = self.server.svc
        if action == "freeze":
            return svc.freeze(ctx, body.get("scope", ""), body.get("reason", ""))
        if action == "unfreeze":
            return svc.unfreeze(ctx, body.get("scope", ""))
        if action == "drain":
            return svc.drain(ctx, float(body.get("grace_s", 5)))
        if action == "quarantine":
            return svc.quarantine(ctx, body.get("reason", ""))
        if action == "maintenance":
            return svc.maintenance(ctx, bool(body.get("enter", True)), body.get("reason", ""))
        if action == "break_glass":
            return svc.break_glass(ctx, bool(body.get("disable", True)), body.get("reason", ""))
        if action == "policy":
            return {"version": svc.set_policy(ctx, body)}
        if action == "policy_rollback":
            return {"version": svc.rollback_policy(ctx)}
        if action == "loglevel":
            svc.set_log_level(ctx, body.get("level", ""))
            return {"level": body.get("level")}
        if action == "explain":
            return {"explanation": svc.get_explanation(ctx, str(body.get("request_id", "")))}
        if action == "diagnostics":
            return svc.diagnostics(ctx)
        raise InvalidArgument("unknown admin action", field="action")

    def _stream_watch(self, ctx: RequestContext, body: dict[str, Any], target: Namespace | None) -> None:
        svc = self.server.svc
        w = svc.watch(ctx, body, target)
        interval = min(max(body.get("progress_interval_ms", 5000), 100), 60_000) / 1000.0
        idle_limit = self.server.idle_timeout_s
        self.send_response(200)
        self.send_header("content-type", "application/x-ndjson")
        self.send_header("transfer-encoding", "chunked")
        self.send_header("cache-control", "no-store")
        self.end_headers()
        last_event = time.monotonic()
        try:
            while not self.server.stopping.is_set():
                f = w.poll(timeout=interval)
                if f.type == "events":
                    last_event = time.monotonic()
                    with svc.tracer.span("cstate.watch.deliver", ctx.traceparent, op="watch", watch_id=w.id,
                                         revision=f.revision, events=len(f.events)):
                        pass
                self._chunk(json.dumps(f.to_dict(), default=str) + "\n")
                if f.type == "canceled":
                    break
                if time.monotonic() - last_event > idle_limit:
                    self._chunk(json.dumps({"type": "canceled", "watch_id": w.id, "revision": svc.store.revision,
                                            "error": {"code": "CSTATE_TIMEOUT", "message": "idle timeout",
                                                      "details": {"resume_revision": w._resume_point()}}}) + "\n")
                    break
            self._chunk("")
        except (BrokenPipeError, ConnectionResetError, socket.timeout, OSError):
            pass  # client went away: cancel below (MC-014-04)
        finally:
            w.cancel()
            self.close_connection = True

    def _chunk(self, s: str) -> None:
        data = s.encode()
        self.server.svc.metrics.inc("cstate_net_bytes_total", len(data), dir="out")
        self.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
        self.wfile.flush()


class ControlStateHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128

    def __init__(self, addr: tuple[str, int], svc: ControlStateService, *, mtls: MTLSAuthenticator,
                 tokens: TokenAuthenticator | None = None, ssl_context: ssl.SSLContext | None = None,
                 idle_timeout_s: float = 300.0, socket_timeout_s: float = 30.0) -> None:
        super().__init__(addr, _Handler)
        self.svc, self.mtls, self.tokens, self.idle_timeout_s = svc, mtls, tokens, idle_timeout_s
        self.stopping = threading.Event()
        self.socket_timeout_s = socket_timeout_s
        self.ssl_context = ssl_context
        self.tls_failures = 0

    def get_request(self):
        """Accept only; the TLS handshake runs in the per-connection thread so a
        slow or hostile handshake cannot stall the accept loop (MC-014-05)."""
        sock, addr = super().get_request()
        sock.settimeout(self.socket_timeout_s)
        if self.ssl_context is not None:
            sock = self.ssl_context.wrap_socket(sock, server_side=True, do_handshake_on_connect=False)
        return sock, addr

    def finish_request(self, request, client_address):
        if isinstance(request, ssl.SSLSocket):
            try:
                request.do_handshake()
            except (ssl.SSLError, OSError):
                self.tls_failures += 1
                self.svc.metrics.inc("cstate_net_connections_total", result="tls_failed")
                self.svc.metrics.inc("cstate_authn_failures_total", reason="tls_handshake")
                return
        self.svc.metrics.inc("cstate_net_connections_total", result="accepted")
        super().finish_request(request, client_address)

    def handle_error(self, request, client_address):  # no tracebacks to stderr; count instead
        self.svc.log.log("WARN", "CS1101", "connection error", peer=str(client_address[0]))

    def serve_background(self) -> threading.Thread:
        t = threading.Thread(target=self.serve_forever, name="inv05-http", daemon=True)
        t.start()
        return t

    def graceful_shutdown(self, grace_s: float = 5.0) -> None:
        """Stop admitting, drain watch streams, then close (MC-031-02, MC-050-05)."""
        self.svc.controls.draining = True
        self.svc.hub.drain(grace_s)
        self.stopping.set()
        self.shutdown()
        self.server_close()
