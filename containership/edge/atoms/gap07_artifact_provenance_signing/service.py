"""Minimal HTTPS/HTTP JSON service around ``AdmissionController`` (stdlib only).

Endpoints: ``POST /admit`` (GAP-07 admission request JSON -> decision JSON;
HTTP 200 only for ``allow``, 403 deny, 503 defer, 500 error), ``GET /readyz``,
``GET /livez``, ``GET /metrics`` (Prometheus text).  Bodies are size-bounded
and parsed strictly.  TLS is terminated by passing an ``ssl.SSLContext``.
Translation of Kubernetes ``AdmissionReview`` objects (pod image refs ->
registry bundles) is estate-specific and not included.
"""
from __future__ import annotations

import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .canonical import strict_loads
from .errors import GapError

MAX_BODY = 4 * 1024 * 1024
STATUS = {"allow": 200, "deny": 403, "defer": 503, "error": 500}


def make_server(controller: Any, host: str = "127.0.0.1", port: int = 8443, *, tls: ssl.SSLContext | None = None,
                exporter: Any = None, tracker: Any = None) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "gap07"
        sys_version = ""

        def log_message(self, *a: Any) -> None:  # structured logging is the controller's job
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/livez":
                self._send(200, json.dumps(controller.health.liveness()).encode())
            elif self.path == "/readyz":
                r = controller.health.readiness()
                self._send(200 if r["ready"] else 503, json.dumps(r).encode())
            elif self.path == "/metrics":
                m = controller.metrics
                r = controller.health.readiness()
                for dep, v in r["checks"].items():
                    m._counters[("gap07_ready", (("dependency", dep),))] = 1.0 if v["ok"] else 0.0
                if exporter is not None:
                    m._counters[("gap07_audit_export_healthy", ())] = 1.0 if exporter.healthy else 0.0
                if tracker is not None:
                    m._counters[("gap07_propagation_slo_breach", ())] = float(tracker.report(0)["breaches"])
                self._send(200, m.exposition().encode(), "text/plain; version=0.0.4")
            else:
                self._send(404, b'{"error":"not found"}')

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/admit":
                self._send(404, b'{"error":"not found"}')
                return
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                n = -1
            if not 0 < n <= MAX_BODY:
                self._send(413, b'{"outcome":"deny","code":"INPUT_TOO_LARGE","runnable":false}')
                return
            raw = self.rfile.read(n)
            try:
                req = strict_loads(raw, max_bytes=MAX_BODY)
                if self.headers.get("traceparent") and isinstance(req, dict):
                    req.setdefault("traceparent", self.headers["traceparent"])
            except GapError as exc:
                self._send(400, json.dumps({"outcome": "deny", "code": exc.code, "runnable": False}).encode())
                return
            d = controller.admit(req)
            self._send(STATUS.get(d["outcome"], 500), json.dumps(d, sort_keys=True, default=str).encode())

    srv = ThreadingHTTPServer((host, port), Handler)
    if tls is not None:
        srv.socket = tls.wrap_socket(srv.socket, server_side=True)
    return srv


def serve_in_thread(srv: ThreadingHTTPServer) -> threading.Thread:
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="gap07-http")
    t.start()
    return t
