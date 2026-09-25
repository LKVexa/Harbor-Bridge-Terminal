"""Network service (19): a stdlib HTTP/JSON service for submit / query /
catalogue / health.

* request bodies are size-bounded before parsing; JSON depth bounded by CSP/1;
* ``/v1/query`` requires a GAP09-QTOKEN/1 bearer (``Authorization: GAP09
  <kid>:<sig>`` + ``X-GAP09-Token`` base64 JSON) -- tenant comes from the
  verified token scope, never from the body;
* ``/v1/submit`` feeds ``VerifiedIngest``; ``Throttled`` maps to HTTP 429 with
  ``Retry-After``;
* errors are the stable ``{code, message}`` shape (no stack traces);
* TLS/mTLS is enabled by passing an ``ssl.SSLContext`` from ``auth``.
It binds 127.0.0.1 by default.  It is a reference service, not a hardened
production edge (no HTTP/2, no connection-level DoS controls beyond limits).
"""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ..runtime import Sample, SignalError
from .errors import Throttled

MAX_BODY = 1 << 20
STATUS = {"malformed": 400, "invalid_sample": 400, "invalid_batch": 400, "invalid_time": 400, "unattributed": 400,
          "unauthenticated": 401, "reporter_untrusted": 401, "unauthorized": 403, "cross_tenant_query": 403,
          "scope_violation": 403, "quarantined": 403, "replay_detected": 409, "timestamp_conflict": 409,
          "throttled": 429, "quota_exceeded": 429, "capacity_exceeded": 429, "time_untrusted": 503,
          "dependency_unavailable": 503, "trust_unavailable": 503}


def make_server(*, ingest, store, authenticator, catalogue, health, host: str = "127.0.0.1", port: int = 0,
                ssl_context=None, clock=lambda: 0):
    class H(BaseHTTPRequestHandler):
        server_version = "gap09/5.1.0"
        sys_version = ""

        def log_message(self, *a):  # no request logging of bodies/headers
            pass

        def _send(self, code: int, obj: Any, headers: dict | None = None) -> None:
            body = json.dumps(obj, sort_keys=True).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _err(self, exc: SignalError) -> None:
            hdr = {"Retry-After": str(max(1, int(exc.retry_after + 0.999)))} if isinstance(exc, Throttled) else None
            self._send(STATUS.get(exc.code, 500), {"code": exc.code, "message": str(exc)}, hdr)

        def _body(self) -> Any:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                raise ValueError("body size")
            return json.loads(self.rfile.read(n))

        def do_GET(self):
            if self.path == "/v1/health":
                return self._send(200, health.report())
            if self.path == "/v1/catalogue":
                return self._send(200, catalogue.document())
            self._send(404, {"code": "not_found", "message": "no such route"})

        def do_POST(self):
            try:
                body = self._body()
            except Exception:
                return self._send(400, {"code": "malformed", "message": "body missing, oversized or not JSON"})
            try:
                if self.path == "/v1/submit":
                    # wire shape is PK_SIGNAL_SUBMISSION/2 exactly; key id and
                    # profile travel inside ``attestation`` (the v5 schema has
                    # no top-level key_id -- finding F-02)
                    if body.get("schema") != "PK_SIGNAL_SUBMISSION/2" or set(body) != {
                            "schema", "reporter", "submission_id", "issued_at", "samples", "signature", "attestation"}:
                        raise KeyError("schema")
                    att = body["attestation"]
                    if att.get("profile") != "GAP09-CSP/1":
                        raise KeyError("profile")
                    samples = [Sample(**s) for s in body["samples"]]
                    n = ingest.submit(reporter=body["reporter"], samples=samples, submission_id=body["submission_id"],
                                      issued_at=body["issued_at"], signature=body["signature"], key_id=att["key_id"])
                    return self._send(202, {"accepted": n})
                if self.path == "/v1/query":
                    auth = self.headers.get("Authorization", "")
                    if not auth.startswith("GAP09 ") or ":" not in auth:
                        return self._send(401, {"code": "unauthenticated", "message": "missing credentials"})
                    kid, sig = auth[6:].split(":", 1)
                    token = json.loads(base64.b64decode(self.headers.get("X-GAP09-Token", "")))
                    now = clock()
                    principal, scope = authenticator.authenticate(token, kid, sig, now=now)
                    authenticator.authorize(scope, tenant=body["tenant"], environment=body["environment"],
                                            site=body["site"], workload=body["workload"])
                    res = store.read(caller_tenant=body["tenant"], tenant=body["tenant"],
                                     environment=body["environment"], site=body["site"],
                                     workload=body["workload"], signal=body["signal"], now=now)
                    return self._send(200, res)
                self._send(404, {"code": "not_found", "message": "no such route"})
            except SignalError as exc:
                self._err(exc)
            except (KeyError, TypeError, ValueError):
                self._send(400, {"code": "malformed", "message": "request fields invalid"})
            except Exception:
                self._send(500, {"code": "internal_error", "message": "internal error"})

    srv = ThreadingHTTPServer((host, port), H)
    srv.daemon_threads = True
    if ssl_context is not None:
        srv.socket = ssl_context.wrap_socket(srv.socket, server_side=True)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv
