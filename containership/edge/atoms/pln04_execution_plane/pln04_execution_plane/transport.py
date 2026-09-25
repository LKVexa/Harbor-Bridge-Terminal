"""M34 - Concrete HTTP/JSON transport for PK_ADMISSION/1, PK_TIER_CATALOGUE/1 and operations.

Routes (all JSON; bearer credential in ``Authorization``)::

    POST   /v1/admissions                 PK_ADMISSION/1 request -> decision
    DELETE /v1/admissions/{workload}?tenant=T[&privileged=1]
    GET    /v1/catalogue                  PK_TIER_CATALOGUE/1
    GET    /v1/explain/{workload}         requires plane:read
    GET    /healthz  /readyz  /metrics    (metrics: Prometheus text)

Errors are always ``PlaneError.public()`` bodies with the canonical code and
the code's HTTP status; ``Retry-After`` is sent only for codes that allow it.
A WIT/gRPC binding would map the same codes; only HTTP ships in-tree.

Production must terminate TLS/mTLS in front of (or instead of) this stdlib
server; the handler itself refuses bodies over the validation byte limit,
unknown content types, and slow clients via a socket timeout.
"""
from __future__ import annotations

import json
import math
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from .errors import PlaneError, from_exception
from .security import authorize
from .validation import MAX_DOCUMENT_BYTES, parse


def make_handler(plane):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PLN04/4.3.0"
        sys_version = ""
        timeout = 10

        def log_message(self, fmt, *args):  # route access logs through structured telemetry
            plane.telemetry.log("debug", "http_access", path=self.path.split("?")[0], status=args[1] if len(args) > 1 else None)

        def _send(self, status: int, body, *, content_type: str = "application/json", headers: dict | None = None):
            data = body.encode() if isinstance(body, str) else json.dumps(body, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _error(self, exc: BaseException):
            err = exc if isinstance(exc, PlaneError) else from_exception(exc)
            headers = {}
            if err.retry_after_s is not None:
                headers["Retry-After"] = str(max(1, math.ceil(err.retry_after_s)))
            self._send(err.spec.http_status, err.public(), headers=headers)

        def _token(self):
            auth = self.headers.get("Authorization", "")
            return auth[7:].strip() if auth.startswith("Bearer ") else None

        def _read_actor(self, capability: str):
            if plane.authenticator is None:
                return None
            actor = plane.authenticator.authenticate(self._token())
            authorize(actor, capability)
            return actor

        def do_POST(self):
            try:
                path = urlsplit(self.path).path
                if path != "/v1/admissions":
                    return self._send(404, {"error_code": "not_found"})
                ctype = self.headers.get("Content-Type", "").split(";")[0].strip()
                if ctype != "application/json":
                    raise PlaneError("PLN04-VAL-003", details={"reason": "content type must be application/json"})
                length = self.headers.get("Content-Length")
                if length is None or not length.isdigit():
                    raise PlaneError("PLN04-VAL-001", details={"reason": "Content-Length required"})
                if int(length) > MAX_DOCUMENT_BYTES:
                    raise PlaneError("PLN04-VAL-002", details={"limit": MAX_DOCUMENT_BYTES})
                doc = parse(self.rfile.read(int(length)), "PK_ADMISSION/1")
                decision = plane.admit(doc, token=self._token(), traceparent=self.headers.get("traceparent"))
                self._send(200, decision)
            except BaseException as exc:  # noqa: BLE001 - every failure maps to a stable code
                self._error(exc)

        def do_DELETE(self):
            try:
                parts = urlsplit(self.path)
                if not parts.path.startswith("/v1/admissions/"):
                    return self._send(404, {"error_code": "not_found"})
                workload = unquote(parts.path[len("/v1/admissions/"):])
                q = parse_qs(parts.query)
                tenant = q.get("tenant", [None])[0]
                privileged = q.get("privileged", ["0"])[0] == "1"
                removed = plane.teardown(workload, tenant, token=self._token(), privileged=privileged)
                self._send(200, {"workload": workload, "removed": removed})
            except BaseException as exc:  # noqa: BLE001
                self._error(exc)

        def do_GET(self):
            try:
                path = urlsplit(self.path).path
                if path == "/healthz":
                    return self._send(200, {"live": True})
                if path == "/readyz":
                    h = plane.health()
                    return self._send(200 if h["ready"] else 503, h)
                if path == "/metrics":
                    self._read_actor("plane:read")
                    return self._send(200, plane.telemetry.prometheus(), content_type="text/plain; version=0.0.4")
                if path == "/v1/catalogue":
                    self._read_actor("catalogue:read")
                    return self._send(200, plane.catalogue())
                if path.startswith("/v1/explain/"):
                    self._read_actor("plane:read")
                    return self._send(200, plane.explain(unquote(path[len("/v1/explain/"):])))
                self._send(404, {"error_code": "not_found"})
            except BaseException as exc:  # noqa: BLE001
                self._error(exc)

    return Handler


def serve(plane, host: str = "127.0.0.1", port: int = 0) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Start a background server (loopback by default).  Returns (server, thread)."""
    server = ThreadingHTTPServer((host, port), make_handler(plane))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="pln04-http", daemon=True)
    thread.start()
    return server, thread
