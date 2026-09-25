"""Authenticated local control endpoint (7) and readiness/liveness/metrics
HTTP probes (34, 31).

* Control: newline-delimited JSON over a UNIX domain socket created with mode
  0600 inside a 0700 directory.  Each line is one signed request (see
  ``security.sign_request``); each reply is one JSON line.  Oversized lines
  are rejected without being buffered past ``max_request_bytes``.
* Probes: loopback-only HTTP server exposing ``/livez``, ``/readyz`` and
  ``/metrics`` (Prometheus text).  Probes carry no mutating operations.
"""
from __future__ import annotations

import json
import os
import pathlib
import socketserver
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .controller import SupervisorController


class _ControlHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        ctl: SupervisorController = self.server.ctl  # type: ignore[attr-defined]
        limit = ctl.cfg.max_request_bytes
        while True:
            line = self.rfile.readline(limit + 1)
            if not line:
                return
            if len(line) > limit and not line.endswith(b"\n"):
                self.wfile.write(json.dumps({"ok": False, "error": {"code": "E_BAD_REQUEST",
                                 "message": "request too large"}}).encode() + b"\n")
                return
            resp = ctl.handle(line.strip())
            self.wfile.write(json.dumps(resp, sort_keys=True, default=str).encode() + b"\n")


class ControlServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, path: str | os.PathLike, ctl: SupervisorController) -> None:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(p.parent, 0o700)
        if p.exists():
            p.unlink()
        old = os.umask(0o177)
        try:
            super().__init__(str(p), _ControlHandler)
        finally:
            os.umask(old)
        os.chmod(p, 0o600)
        self.ctl = ctl


def make_probe_server(ctl: SupervisorController, port: int = 0) -> ThreadingHTTPServer:
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a) -> None:  # route via structured logger instead
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/livez":
                r = ctl.liveness()
                self._send(200 if r["live"] else 503, json.dumps(r).encode())
            elif self.path == "/readyz":
                r = ctl.readiness()
                self._send(200 if r["ready"] else 503, json.dumps(r).encode())
            elif self.path == "/metrics":
                self._send(200, ctl.metrics.render().encode(), "text/plain; version=0.0.4")
            else:
                self._send(404, b'{"error":"not found"}')

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.daemon_threads = True
    return srv


def serve_background(server) -> threading.Thread:
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t
