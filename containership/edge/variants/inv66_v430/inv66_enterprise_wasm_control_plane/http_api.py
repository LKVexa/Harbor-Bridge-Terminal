"""HTTP(S) surface for INV-66 (MC-049 operator endpoints + public APIs).

Routes (JSON unless noted):

  POST /v1/admit                 PK_ECP_ADMIT/1 request -> response
  GET  /v1/inventory?tenant=&lattice=
  GET  /v1/decisions/<id>/explain
  POST /v1/decisions/<id>/transition   {"to", "reason"}
  GET  /v1/audit?after=&limit=&kind=&tenant=
  POST /v1/audit/export
  POST /v1/config                (PK_ECP_CONFIG/1 document)
  POST /v1/config/rollback       {"revision"}
  POST /v1/freeze                {"scope", "on", "reason"}
  GET  /healthz  /readyz  /version     (unauthenticated, no tenant data)
  GET  /metrics                   Prometheus text (unauthenticated; bind to ops network)

Serve with TLS by passing an ``ssl.SSLContext``; with
``verify_mode=CERT_REQUIRED`` the client-certificate SHA-256 thumbprint is
passed to token verification (``cnf`` binding).  Errors are always the
``PK_ECP_ERROR/1`` envelope with the catalog HTTP status.
"""
from __future__ import annotations

import hashlib
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .errors import ControlPlaneError, Error

MAX_BODY = 110_000_000


def make_handler(svc):
    class Handler(BaseHTTPRequestHandler):
        server_version = "inv66"
        sys_version = ""

        def log_message(self, *args):   # structured logging happens in the service
            pass

        def _send(self, code: int, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else json.dumps(body, sort_keys=True).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _err(self, err: Error):
            self._send(err.http_status, {"schema": "PK_ECP_ERROR/1", "error": err.to_dict()})

        def _token(self):
            h = self.headers.get("Authorization", "")
            return h[7:] if h.startswith("Bearer ") else None

        def _peer(self):
            try:
                der = self.connection.getpeercert(binary_form=True)
            except (AttributeError, ValueError):
                return None
            return hashlib.sha256(der).hexdigest() if der else None

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ControlPlaneError(Error("MANIFEST_TOO_LARGE", "body too large"))
            try:
                return json.loads(self.rfile.read(n) or b"null")
            except ValueError:
                raise ControlPlaneError(Error("SCHEMA_INVALID", "body is not JSON")) from None

        def _route(self, method):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            parts = [p for p in u.path.split("/") if p]
            tok, peer = self._token(), self._peer()
            try:
                if method == "GET" and u.path == "/healthz":
                    h = svc.health()
                    return self._send(200 if h["status"] == "ok" else 503, h)
                if method == "GET" and u.path == "/readyz":
                    r = svc.readiness()
                    return self._send(200 if r["ready"] else 503, r)
                if method == "GET" and u.path == "/version":
                    return self._send(200, svc.version_info())
                if method == "GET" and u.path == "/metrics":
                    svc.refresh_gauges()
                    return self._send(200, svc.metrics.exposition(), "text/plain; version=0.0.4")
                if method == "POST" and u.path == "/v1/admit":
                    r = svc.admit(tok, self._body(), traceparent=self.headers.get("traceparent"), peer=peer)
                    return self._send(200 if r["admitted"] else 403, r)
                if method == "GET" and u.path == "/v1/inventory":
                    return self._send(200, svc.inventory(tok, q.get("tenant"), q.get("lattice"), peer=peer))
                if method == "GET" and len(parts) == 4 and parts[:2] == ["v1", "decisions"] and parts[3] == "explain":
                    return self._send(200, svc.explain(tok, parts[2], peer=peer))
                if method == "POST" and len(parts) == 4 and parts[:2] == ["v1", "decisions"] and parts[3] == "transition":
                    b = self._body() or {}
                    return self._send(200, svc.transition(tok, parts[2], b.get("to"), b.get("reason", ""), peer=peer))
                if method == "GET" and u.path == "/v1/audit":
                    return self._send(200, svc.audit_query(tok, after_sequence=int(q.get("after", 0)),
                                                           limit=int(q.get("limit", 100)), kind=q.get("kind"),
                                                           tenant=q.get("tenant"), peer=peer))
                if method == "POST" and u.path == "/v1/audit/export":
                    return self._send(200, svc.audit_export(tok, peer=peer))
                if method == "POST" and u.path == "/v1/config":
                    return self._send(200, svc.apply_config(tok, self._body(), peer=peer))
                if method == "POST" and u.path == "/v1/config/rollback":
                    return self._send(200, svc.rollback_config(tok, int((self._body() or {}).get("revision", 0)), peer=peer))
                if method == "POST" and u.path == "/v1/freeze":
                    b = self._body() or {}
                    return self._send(200, svc.set_freeze(tok, b.get("scope", ""), bool(b.get("on")), b.get("reason", ""), peer=peer))
                return self._err(Error("NOT_FOUND", "no such route"))
            except ControlPlaneError as exc:
                return self._err(exc.error)
            except (ValueError, TypeError):
                return self._err(Error("SCHEMA_INVALID", "malformed parameters"))
            except Exception:                           # never leak internals
                svc.log.log("error", "unhandled", path=u.path)
                return self._err(Error("INTERNAL", "internal error"))

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

    return Handler


def serve(svc, host: str = "127.0.0.1", port: int = 8466, ssl_context: ssl.SSLContext | None = None):
    httpd = ThreadingHTTPServer((host, port), make_handler(svc))
    httpd.daemon_threads = True
    if ssl_context is not None:
        httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd
