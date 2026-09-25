"""HTTP(S) surface for the control plane (stdlib ``http.server``).

Routes (JSON in/out; errors are ``PK_ECP_ERROR/1`` envelopes with the registry's HTTP status):

    POST /v1/admit               PK_ECP_ADMIT/1           Authorization: Bearer <token>
    POST /v1/rbac                PK_ECP_RBAC/1
    POST /v1/audit/query         PK_ECP_AUDIT/1 query
    GET  /v1/audit/export?from=&to=
    GET  /v1/inventory?tenant=&lattice=
    GET  /v1/explain/<decision_id>
    POST /v1/quarantine/freeze|release   {"scope", "reason"}
    GET  /healthz  (liveness)   /readyz (readiness, 503 unless ready)   /version   /metrics

Version negotiation (MC-018): a request may send ``Accept-Protocol: PK_ECP_ADMIT/1``;
an unsupported value returns ``ECP_UNSUPPORTED_VERSION`` with the supported list.

Transport security (MC-034): ``serve(..., tls=ssl_context)`` wraps the socket.  With
``ssl.CERT_REQUIRED`` the verified client certificate's SPIFFE URI SAN is used as the
peer identity when no bearer token is presented.  Certificates/keys come from the
secret provider; rotation = reload the context (``Server.reload_tls``).
"""
from __future__ import annotations

import json
import ssl
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional

from .errors import EcpError
from .service import PROTOCOLS, VERSION, ControlPlaneService

MAX_BODY = 8_000_000


def _peer_spiffe(sock) -> Optional[str]:
    try:
        cert = sock.getpeercert()
    except (AttributeError, ValueError):
        return None
    for typ, val in (cert or {}).get("subjectAltName", ()):
        if typ == "URI" and val.startswith("spiffe://"):
            return val
    return None


def make_handler(svc: ControlPlaneService):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"inv66/{VERSION}"
        sys_version = ""

        def log_message(self, fmt, *args):  # structured logging happens in the service
            return

        def _send(self, status: int, body: Any, ctype: str = "application/json") -> None:
            data = body.encode() if isinstance(body, str) else json.dumps(body, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _err(self, e: EcpError, rid: Optional[str] = None) -> None:
            env = e.envelope(rid)
            if e.spec.retryable and "retry_after_ms" in e.details:
                self.send_response(e.spec.http)
                data = json.dumps(env, sort_keys=True).encode()
                self.send_header("Retry-After", str(max(1, int(e.details["retry_after_ms"]) // 1000)))
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self._send(e.spec.http, env)

        def _body(self) -> Any:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise EcpError("ECP_RESOURCE_LIMIT", "request body too large", limit=MAX_BODY, observed=n)
            try:
                return json.loads(self.rfile.read(n) or b"null")
            except (ValueError, RecursionError):
                raise EcpError("ECP_SCHEMA_INVALID", "body is not acceptable JSON") from None

        def _cred(self) -> tuple[Optional[str], Optional[str]]:
            a = self.headers.get("Authorization", "")
            token = a[7:] if a.startswith("Bearer ") else None
            return token, (_peer_spiffe(self.connection) if token is None else None)

        def _principal(self):
            token, peer = self._cred()
            return svc.principal(token, peer)

        def _negotiate(self) -> None:
            want = self.headers.get("Accept-Protocol")
            if want and want not in PROTOCOLS:
                raise EcpError("ECP_UNSUPPORTED_VERSION", "protocol not supported", observed_version=want[:64],
                               expected_version=",".join(PROTOCOLS)[:512])

        def do_GET(self):  # noqa: N802
            u = urllib.parse.urlparse(self.path)
            q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
            try:
                self._negotiate()
                if u.path == "/healthz":
                    return self._send(200, {"status": "alive", "version": VERSION})
                if u.path == "/readyz":
                    h = svc.health()
                    return self._send(200 if h["ready"] else 503, h)
                if u.path == "/version":
                    h = svc.health()
                    return self._send(200, {"version": VERSION, "protocols": list(PROTOCOLS),
                                            "config_generation": h["config_generation"]})
                if u.path == "/metrics":
                    return self._send(200, svc.metrics.render(), "text/plain; version=0.0.4")
                if u.path == "/v1/inventory":
                    return self._send(200, svc.inventory_view(self._principal(), q.get("tenant"), q.get("lattice")))
                if u.path.startswith("/v1/explain/"):
                    return self._send(200, svc.explain(u.path.rsplit("/", 1)[1], self._principal()))
                if u.path == "/v1/audit/export":
                    return self._send(200, svc.audit_export(self._principal(), int(q.get("from", 1)),
                                                            int(q["to"]) if "to" in q else None))
                raise EcpError("ECP_NOT_FOUND", "no such route")
            except EcpError as e:
                self._err(e)
            except Exception:  # noqa: BLE001 - never leak internals
                self._err(EcpError("ECP_INTERNAL", "internal error"))

        def do_POST(self):  # noqa: N802
            u = urllib.parse.urlparse(self.path)
            rid = None
            try:
                self._negotiate()
                body = self._body()
                rid = body.get("request_id") if isinstance(body, dict) else None
                if u.path == "/v1/admit":
                    if not isinstance(body, dict):
                        raise EcpError("ECP_SCHEMA_INVALID", "body must be an object")
                    if self.headers.get("traceparent") and "traceparent" not in body:
                        body["traceparent"] = self.headers["traceparent"]
                    token, peer = self._cred()
                    return self._send(200, svc.admit(body, token, peer=peer))
                p = self._principal()
                if u.path == "/v1/rbac":
                    return self._send(200, svc.rbac(body, p))
                if u.path == "/v1/audit/query":
                    return self._send(200, svc.audit_query(body, p))
                if u.path == "/v1/quarantine/freeze":
                    return self._send(200, svc.freeze(body["scope"], p, body.get("reason", "")))
                if u.path == "/v1/quarantine/release":
                    return self._send(200, svc.release(body["scope"], p, body.get("reason", "")))
                raise EcpError("ECP_NOT_FOUND", "no such route")
            except EcpError as e:
                self._err(e, rid if isinstance(rid, str) else None)
            except (KeyError, TypeError, AttributeError):
                self._err(EcpError("ECP_SCHEMA_INVALID", "malformed request"), None)
            except Exception:  # noqa: BLE001
                self._err(EcpError("ECP_INTERNAL", "internal error"), None)

    return Handler


class Server:
    def __init__(self, svc: ControlPlaneService, host: str = "127.0.0.1", port: int = 0,
                 tls: Optional[ssl.SSLContext] = None):
        self.httpd = ThreadingHTTPServer((host, port), make_handler(svc))
        self.httpd.daemon_threads = True
        self._tls = tls
        if tls is not None:
            self.httpd.socket = tls.wrap_socket(self.httpd.socket, server_side=True)
        self.thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address[:2]
        host = host.decode() if isinstance(host, bytes) else host
        return f"{'https' if self._tls else 'http'}://{host}:{port}"

    def start(self) -> "Server":
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def reload_tls(self, certfile: str, keyfile: str) -> None:
        """Rotate the server certificate without restart (new handshakes use the new chain)."""
        if self._tls is None:
            raise EcpError("ECP_CONFIG_INVALID", "server started without TLS")
        self._tls.load_cert_chain(certfile, keyfile)
