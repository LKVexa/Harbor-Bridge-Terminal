"""G13-MC-015 versioned service transport (HTTP/JSON, ``/v1``).

Endpoints: ``POST /v1/evaluate``, ``POST /v1/explain``, ``POST /v1/bundles/stage``,
``POST /v1/bundles/activate``, ``POST /v1/bundles/load``, ``POST /v1/rollback``,
``POST /v1/control``, ``GET /v1/health``, ``GET /v1/ready``, ``GET /v1/status``,
``GET /metrics``.

* Authentication: ``Authorization: Bearer <PK_POLICY_TOKEN/1>`` on every call
  except ``/v1/health`` (liveness).  ``/metrics`` and ``/v1/status`` need
  ``policy.status``.
* Deadlines: ``X-Deadline-Ms`` (capped by config); cancellation is cooperative.
* Backpressure: admission control returns 503 + ``Retry-After``.
* Tracing: W3C ``traceparent`` is accepted and echoed.
* Bind to loopback by default; terminate TLS in front (sidecar/ingress) --
  documented in docs/RUNBOOKS.md.  Body size capped before reading.
"""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .authz import Capability as Cap
from .errors import (Overloaded, PolicyError, RequestRejected, StalePolicyRefused, Unauthenticated,
                     Unauthorized, EvaluationDisabled, NoActivePolicy, DeadlineExceeded, BundleRejected,
                     DependencyUnavailable, ConfigRejected)

_STATUS = [(Unauthenticated, 401), (Unauthorized, 403), (Overloaded, 503), (DeadlineExceeded, 504),
           (StalePolicyRefused, 503), (EvaluationDisabled, 503), (NoActivePolicy, 503),
           (DependencyUnavailable, 503), (BundleRejected, 422), (RequestRejected, 400), (ConfigRejected, 400)]


def http_status(exc: PolicyError) -> int:
    for cls, code in _STATUS:
        if isinstance(exc, cls):
            return code
    return 500


def make_handler(service, authenticator, *, max_body: int = 2_097_152):
    class Handler(BaseHTTPRequestHandler):
        server_version = "GAP13/5.0"
        sys_version = ""

        def log_message(self, fmt, *args):  # route through structured logger instead of stderr
            return

        def _send(self, code: int, obj: Any, *, ctype="application/json", headers=None) -> None:
            body = obj.encode() if isinstance(obj, str) else json.dumps(obj, sort_keys=True).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _principal(self):
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                raise Unauthenticated("missing bearer token")
            return authenticator.authenticate(auth[7:].strip())

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if n < 0 or n > max_body:
                raise RequestRejected("request body too large")
            raw = self.rfile.read(n)
            try:
                obj = json.loads(raw or b"{}")
            except ValueError as exc:
                raise RequestRejected("body is not JSON") from exc
            if not isinstance(obj, dict):
                raise RequestRejected("body must be a JSON object")
            return obj

        def _deadline(self):
            v = self.headers.get("X-Deadline-Ms")
            ms = service.config.default_deadline_ms
            if v is not None:
                try:
                    ms = max(1, min(int(v), 30_000))
                except ValueError as exc:
                    raise RequestRejected("bad X-Deadline-Ms") from exc
            return service.mono() + ms / 1000.0

        def _dispatch(self, method: str) -> None:
            tp = self.headers.get("traceparent")
            try:
                path = self.path.split("?", 1)[0]
                if method == "GET" and path == "/v1/health":
                    return self._send(200, {"live": True})
                p = self._principal()
                if method == "GET" and path == "/v1/ready":
                    h = service.health()
                    return self._send(200 if h["ready"] else 503, h)
                if method == "GET" and path == "/v1/status":
                    service._authorize(p, Cap.STATUS, action="status")
                    return self._send(200, service.status())
                if method == "GET" and path == "/metrics":
                    service._authorize(p, Cap.STATUS, action="metrics")
                    return self._send(200, service.metrics.prometheus(), ctype="text/plain; version=0.0.4")
                if method != "POST":
                    return self._send(404, {"code": "G13-E404", "message": "not found"})
                body = self._body()
                if path == "/v1/evaluate":
                    out = service.evaluate(p, body.get("attributes", {}), traceparent=tp, deadline=self._deadline())
                elif path == "/v1/explain":
                    out = service.explain(p, body.get("attributes", {}), traceparent=tp, deadline=self._deadline())
                elif path in ("/v1/bundles/stage", "/v1/bundles/load"):
                    env = base64.b64decode(body.get("envelope_b64", ""), validate=True)
                    out = service.stage(p, env) if path.endswith("stage") else service.load(p, env, reason=body.get("reason", ""))
                elif path == "/v1/bundles/activate":
                    out = service.activate(p, str(body.get("digest", "")), reason=body.get("reason", ""))
                elif path == "/v1/rollback":
                    out = service.rollback(p, reason=str(body.get("reason", "")), target_digest=body.get("digest"))
                elif path == "/v1/control":
                    out = service.set_control(p, str(body.get("state")), reason=str(body.get("reason", "")),
                                              change_id=str(body.get("change_id", "")), expires_at=body.get("expires_at"))
                else:
                    return self._send(404, {"code": "G13-E404", "message": "not found"})
                hdrs = {"traceparent": f"00-{out['trace_id']}-{'0'*15}1-01"} if isinstance(out, dict) and out.get("trace_id") else None
                return self._send(200, out, headers=hdrs)
            except PolicyError as exc:
                hdrs = {"Retry-After": "1"} if exc.retryable else None
                return self._send(http_status(exc), exc.to_dict(), headers=hdrs)
            except (ValueError, TypeError) as exc:
                return self._send(400, {"schema": "PK_POLICY_ERROR/1", "code": "G13-E200",
                                        "message": "malformed request", "retryable": False, "details": {}})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

    return Handler


def serve(service, authenticator, host: str = "127.0.0.1", port: int = 8413) -> tuple[ThreadingHTTPServer, threading.Thread]:
    srv = ThreadingHTTPServer((host, port), make_handler(service, authenticator,
                                                         max_body=service.config.limits.max_bundle_bytes * 2))
    srv.daemon_threads = True
    t = threading.Thread(target=srv.serve_forever, name="gap13-rpc", daemon=True)
    t.start()
    return srv, t
