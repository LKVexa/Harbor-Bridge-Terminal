"""Operator HTTP surface: health/readiness, metrics, status, explain, sync
trigger and freeze controls (components 10, 35, 38, 20).

Stdlib ``http.server`` (threaded), bound to loopback by default and wrapped
in TLS/mTLS by ``netsec`` when certificates are configured.  Every route
except ``/healthz`` requires a ``PKT1`` bearer token and a capability:

    GET  /healthz                  liveness (no auth, no detail)
    GET  /readyz                   readiness (auth: status.read)
    GET  /metrics                  Prometheus text (auth: metrics.read when required)
    GET  /v1/status                PK_GITOPS_STATUS/1 (status.read)
    GET  /v1/explain/<decision>    PK_GITOPS_EXPLAIN/1 (explain.read)
    POST /v1/sync?ref=refs/...     trigger reconcile (sync.trigger)
    POST /v1/freeze                {"scope","name","reason"} (freeze.set)

Request bodies are capped at 16 KiB; errors are ``PK_GITOPS_ERROR/1``
envelopes with the request's correlation id; ``traceparent`` is honoured.
"""
from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .errors import GitOpsError, LimitExceeded, Malformed, Unauthenticated, from_exception

MAX_BODY = 16 << 10
STATUS = {"PKG-AUTH-001": 401, "PKG-AUTH-002": 403, "PKG-INPUT-001": 400, "PKG-INPUT-002": 413,
          "PKG-OPS-001": 423, "PKG-OPS-004": 429, "PKG-OPS-002": 503}


def make_handler(ctl, auth, authz, metrics, *, metrics_require_auth: bool = True):
    class H(BaseHTTPRequestHandler):
        server_version = "inv07"
        sys_version = ""

        def log_message(self, *a):  # structured events only
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body, sort_keys=True).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Correlation-Id", self.cid)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _principal(self):
            h = self.headers.get("Authorization", "")
            if not h.startswith("Bearer "):
                raise Unauthenticated("bearer token required")
            return auth.verify(h[7:].strip())

        def _route(self, method):
            self.cid = secrets.token_hex(8)
            try:
                u = urlsplit(self.path)
                if method == "GET" and u.path == "/healthz":
                    return self._send(200, {"status": "alive"})
                if method == "GET" and u.path == "/metrics":
                    if metrics_require_auth:
                        authz.require(self._principal(), "metrics.read")
                    return self._send(200, metrics.exposition().encode(), "text/plain; version=0.0.4")
                p = self._principal()
                if method == "GET" and u.path == "/readyz":
                    authz.require(p, "status.read")
                    st = ctl.status()
                    return self._send(200 if st["health"] != "blocked" else 503, {"health": st["health"],
                                                                                   "reasons": st["reasons"]})
                if method == "GET" and u.path == "/v1/status":
                    authz.require(p, "status.read")
                    return self._send(200, ctl.status())
                if method == "GET" and u.path.startswith("/v1/explain/"):
                    authz.require(p, "explain.read")
                    rec = ctl.explain.get(u.path.rsplit("/", 1)[1][:64])
                    return self._send(200 if rec else 404, rec or {"error": "not found"})
                if method == "POST":
                    n = int(self.headers.get("Content-Length") or 0)
                    if n > MAX_BODY:
                        raise LimitExceeded("request body too large")
                    body = json.loads(self.rfile.read(n) or b"{}") if n else {}
                    if u.path == "/v1/sync":
                        authz.require(p, "sync.trigger")
                        ref = (parse_qs(u.query).get("ref") or [""])[0]
                        return self._send(200, ctl.reconcile(ref, traceparent=self.headers.get("traceparent")))
                    if u.path == "/v1/freeze":
                        authz.require(p, "freeze.set")
                        if not isinstance(body, dict) or not {"scope", "name", "reason"} <= set(body):
                            raise Malformed("scope, name and reason required")
                        return self._send(200, ctl.freezes.freeze(body["scope"], str(body["name"])[:128],
                                                                  reason=str(body["reason"])[:512], actor=p.sub))
                self._send(404, {"error": "not found"})
            except GitOpsError as exc:
                self._send(STATUS.get(exc.code, 500 if exc.code == "PKG-INTERNAL-001" else 409),
                           from_exception(exc, self.cid))
            except ValueError:
                self._send(400, from_exception(Malformed("bad request"), self.cid))
            except Exception as exc:  # noqa: BLE001
                self._send(500, from_exception(exc, self.cid))

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

    return H


def serve(ctl, auth, authz, metrics, *, host: str = "127.0.0.1", port: int = 0, ssl_context=None,
          metrics_require_auth: bool = True):
    srv = ThreadingHTTPServer((host, port), make_handler(ctl, auth, authz, metrics,
                                                          metrics_require_auth=metrics_require_auth))
    if ssl_context is not None:
        srv.socket = ssl_context.wrap_socket(srv.socket, server_side=True)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv
