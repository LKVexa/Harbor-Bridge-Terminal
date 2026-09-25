"""Checklist 19: explicit HTTP/JSON control-plane transport.

Boundary properties (each covered by tests/test_service.py):

* authentication  - ``Authorization: Bearer <token>``; tokens are stored only
  as SHA-256 digests and compared in constant time; missing/bad -> 401.
* authorization   - every route maps to one capability checked per node.
* timeouts        - per-connection socket timeout (``request_timeout_s``).
* size limits     - ``Content-Length`` required on bodies and capped at
  ``max_request_bytes``; oversize -> 413 without reading the body.
* backpressure    - token-bucket rate limit (429) and a non-blocking
  in-flight limiter (503 + ``Retry-After``).
* idempotency     - POST routes honour ``Idempotency-Key``; replaying the
  same key with the same body returns the stored response, with a different
  body -> 409 ``idempotency_conflict``.  Cache is bounded (LRU).
* structured errors - every failure is a ``PK_ERROR/1`` body.
* negotiation     - ``Accept-Schema`` header per checklist 20.
* transport security - binding a non-loopback address without an
  ``ssl.SSLContext`` is refused at construction (C047 applicability: once
  posture crosses a network it must be encrypted in transit).
* cancellation    - a client disconnect aborts the handler; decisions are
  side-effect free except the audit/explain record, which is written once.

Routes::

    GET  /healthz                         (unauthenticated liveness + health state)
    GET  /metrics                         posture.read
    POST /v1/posture                      posture.write   (attested envelope)
    GET  /v1/status/<node>                posture.read
    POST /v1/cotenancy                    cotenancy.decide
    GET  /v1/explain/<decision_id>        decision.explain
    POST /v1/control/quarantine|release   control.emergency
    POST /v1/control/freeze|unfreeze      control.emergency (unscoped only)
"""
from __future__ import annotations

import collections
import hashlib
import hmac
import ipaddress
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .authz import CAP_POSTURE_READ
from .defense import MitigationMissing
from .negotiation import negotiate
from .registry import PostureRegistry
from .resilience import ConcurrencyLimiter, TokenBucket, classify_code

HTTP_STATUS = {
    "authn_failed": 401, "authz_denied": 403, "bad_request": 400, "payload_too_large": 413,
    "rate_limited": 429, "overloaded": 503, "version_unsupported": 406, "idempotency_conflict": 409,
    "not_found": 404, "internal_error": 500, "schema_version_unrepresentable": 406,
}
IDEMPOTENCY_CACHE = 4096


class TokenStore:
    def __init__(self) -> None:
        self._t: dict[str, str] = {}

    def add(self, token: str, principal: str) -> None:
        if len(token) < 32:
            raise ValueError("bearer tokens must be at least 32 characters")
        self._t[hashlib.sha256(token.encode()).hexdigest()] = principal

    def resolve(self, header: str | None) -> str | None:
        if not header or not header.startswith("Bearer "):
            return None
        digest = hashlib.sha256(header[7:].strip().encode()).hexdigest()
        for known, principal in self._t.items():
            if hmac.compare_digest(known, digest):
                return principal
        return None


def _err(code: str, message: str, **details) -> dict:
    return {"schema": "PK_ERROR/1", "code": code, "message": message, "details": details}


class Inv43Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, registry: PostureRegistry, tokens: TokenStore, *,
                 ssl_context: ssl.SSLContext | None = None) -> None:
        host = addr[0]
        try:
            loop = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loop = host == "localhost"
        if not loop and ssl_context is None:
            raise ValueError("refusing to serve INV-43 on a non-loopback address without TLS")
        cfg = registry.config.active
        self.registry, self.tokens = registry, tokens
        self.max_bytes = cfg["max_request_bytes"]
        self.timeout_s = cfg["request_timeout_s"]
        self.bucket = TokenBucket(cfg["rate_per_s"], max(1, int(cfg["rate_per_s"])))
        self.limiter = ConcurrencyLimiter(cfg["max_inflight"])
        self.idem: "collections.OrderedDict[str, tuple[str, int, dict]]" = collections.OrderedDict()
        self.idem_lock = threading.Lock()
        super().__init__(addr, _Handler)
        if ssl_context is not None:
            self.socket = ssl_context.wrap_socket(self.socket, server_side=True)


class _Handler(BaseHTTPRequestHandler):
    server: Inv43Server
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # structured logging happens in the registry
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(self.server.timeout_s)

    def _send(self, status: int, body: dict, extra: dict | None = None) -> None:
        data = json.dumps(body, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _fail(self, exc: MitigationMissing) -> None:
        status = HTTP_STATUS.get(exc.code)
        if status is None:
            status = 409 if classify_code(exc.code).value in {"policy_rejection", "degraded_input"} else 503
        extra = {"Retry-After": "1"} if status in (429, 503) else None
        self._send(status, exc.to_dict(), extra)

    def _body(self) -> dict:
        n = self.headers.get("Content-Length")
        if n is None or not n.isdigit():
            raise MitigationMissing("Content-Length required", code="bad_request", details={})
        if int(n) > self.server.max_bytes:
            self.close_connection = True
            raise MitigationMissing("request body too large", code="payload_too_large",
                                    details={"limit": self.server.max_bytes})
        raw = self.rfile.read(int(n))
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise MitigationMissing("body is not JSON", code="bad_request", details={}) from None
        if not isinstance(body, dict):
            raise MitigationMissing("body must be a JSON object", code="bad_request", details={})
        return body

    def _principal(self) -> str:
        p = self.server.tokens.resolve(self.headers.get("Authorization"))
        if p is None:
            raise MitigationMissing("authentication required", code="authn_failed", details={})
        return p

    def _dispatch(self, method: str) -> None:
        srv = self.server
        path = self.path.split("?", 1)[0]
        if method == "GET" and path == "/healthz":
            reg = srv.registry
            self._send(200, {"health": reg.health.state(degraded_nodes=len(reg.degraded_nodes())).value})
            return
        if not srv.bucket.take():
            self._fail(MitigationMissing("rate limited", code="rate_limited", details={}))
            return
        try:
            with srv.limiter:
                self._route(method, path)
        except MitigationMissing as exc:
            self._fail(exc)
        except Exception as exc:  # defect: structured, never a permit
            self._send(500, _err("internal_error", type(exc).__name__))

    def _route(self, method: str, path: str) -> None:
        srv, reg = self.server, self.server.registry
        principal = self._principal()
        parts = [p for p in path.split("/") if p]
        if method == "GET" and path == "/metrics":
            reg.authz.check(principal, CAP_POSTURE_READ, None)
            data = reg.metrics.render().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if method == "GET" and len(parts) == 3 and parts[:2] == ["v1", "status"]:
            v = negotiate("PK_MITIGATIONS", self.headers.get("Accept-Schema"))
            self._send(200, reg.status(principal, parts[2], version=v))
            return
        if method == "GET" and len(parts) == 3 and parts[:2] == ["v1", "explain"]:
            self._send(200, reg.explain(principal, parts[2]))
            return
        if method != "POST":
            raise MitigationMissing("no such route", code="not_found", details={"path": path})
        body = self._body()
        key = self.headers.get("Idempotency-Key")
        body_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if key is not None:
            ck = f"{principal}:{key}"
            with srv.idem_lock:
                hit = srv.idem.get(ck)
            if hit is not None:
                if hit[0] != body_hash:
                    raise MitigationMissing("idempotency key reused with a different body",
                                            code="idempotency_conflict", details={})
                self._send(hit[1], hit[2], {"Idempotent-Replay": "true"})
                return
        status, out = self._post(principal, parts, body)
        if key is not None:
            with srv.idem_lock:
                srv.idem[f"{principal}:{key}"] = (body_hash, status, out)
                while len(srv.idem) > IDEMPOTENCY_CACHE:
                    srv.idem.popitem(last=False)
        self._send(status, out)

    def _post(self, principal: str, parts: list[str], body: dict) -> tuple[int, dict]:
        reg = self.server.registry
        if parts == ["v1", "posture"]:
            return 202, reg.submit(principal, body.get("envelope"), gap02=body.get("gap02"))
        if parts == ["v1", "cotenancy"]:
            negotiate("PK_COTENANCY", self.headers.get("Accept-Schema"))
            out = reg.decide(principal, body.get("node"), body.get("a"), body.get("b"), tier=body.get("tier"),
                             traceparent=self.headers.get("traceparent"), op_id=self.headers.get("Idempotency-Key"))
            return (200 if out.get("permitted") else 409), out
        if len(parts) == 3 and parts[:2] == ["v1", "control"]:
            action = parts[2]
            if action == "quarantine":
                reg.quarantine(principal, body.get("node"), body.get("reason"))
            elif action == "release":
                reg.release(principal, body.get("node"))
            elif action in ("freeze", "unfreeze"):
                reg.freeze(principal, action == "freeze")
            else:
                raise MitigationMissing("no such control", code="not_found", details={})
            return 200, {"ok": True, "action": action}
        raise MitigationMissing("no such route", code="not_found", details={})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


def serve(registry: PostureRegistry, tokens: TokenStore, host: str = "127.0.0.1", port: int = 0,
          ssl_context: ssl.SSLContext | None = None) -> tuple[Inv43Server, threading.Thread]:
    srv = Inv43Server((host, port), registry, tokens, ssl_context=ssl_context)
    t = threading.Thread(target=srv.serve_forever, name="inv43-http", daemon=True)
    t.start()
    return srv, t
