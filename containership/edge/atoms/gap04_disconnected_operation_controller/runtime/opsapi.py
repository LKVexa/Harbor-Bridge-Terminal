"""Externally consumable health/readiness/metrics endpoint (GAP04-C25, C26).

GET /livez  /readyz  /healthz  /metrics  (JSON / Prometheus text).
Served over mTLS when an ``ssl.SSLContext`` is supplied; each path is mapped to
an authorization boundary (health.read / metrics.read). Without TLS the server
only binds loopback and requires an explicit ``allow_insecure_loopback=True``.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .authz import Authorizer, principal_from_peercert
from .errors import Gap04Error, to_error

ROUTES = {"/livez": "health.read", "/readyz": "health.read", "/healthz": "health.read", "/metrics": "metrics.read"}


def make_server(node, host="127.0.0.1", port=0, ssl_context=None, authorizer: Authorizer | None = None,
                allow_insecure_loopback=False):
    if ssl_context is None and not (allow_insecure_loopback and host in ("127.0.0.1", "::1")):
        raise Gap04Error("ops API requires mTLS unless explicitly bound insecure to loopback", code="GAP04-E0104")

    class H(BaseHTTPRequestHandler):
        server_version = "gap04-ops/4.3.0"

        def log_message(self, *a):  # route through structured logger instead
            pass

        def _send(self, code, body: bytes, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            b = ROUTES.get(self.path)
            if b is None:
                return self._send(404, b'{"error":"not found"}', "application/json")
            try:
                if ssl_context is not None:
                    p = principal_from_peercert(self.connection.getpeercert())
                    if authorizer is not None:
                        authorizer.check(b, p)
                if self.path == "/metrics":
                    node.health()
                    return self._send(200, node.metrics.render().encode(), "text/plain; version=0.0.4")
                h = node.health()
                if self.path == "/livez":
                    return self._send(200, json.dumps({"live": True}).encode(), "application/json")
                code = 200 if (self.path == "/healthz" or h["ready"]) else 503
                return self._send(code, json.dumps(h, sort_keys=True, default=str).encode(), "application/json")
            except Exception as e:
                err = to_error(e)
                return self._send(err["http_status"], json.dumps(err).encode(), "application/json")

    srv = ThreadingHTTPServer((host, port), H)
    if ssl_context is not None:
        srv.socket = ssl_context.wrap_socket(srv.socket, server_side=True)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv
