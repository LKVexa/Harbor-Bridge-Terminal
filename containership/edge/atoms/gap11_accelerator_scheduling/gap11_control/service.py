"""GAP11-P0-13 API transport/server + request pipeline.

Pipeline per request (the order is a security property and is tested):
  size/deadline -> admission (bounded in-flight) -> authenticate -> decode+schema
  -> authorize (deny by default) -> quota -> controller (idempotent, fenced) -> audit.

``Service.handle`` is transport-independent; ``serve_http`` binds it to a
``ThreadingHTTPServer`` on loopback with Content-Length limits and socket timeouts.
mTLS termination is NOT implemented here (no PKI in this environment) — the HTTP
binding is for local integration only and refuses non-loopback binds.
"""
from __future__ import annotations

import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .common import ControlError, Telemetry
from .controller import Controller
from .observability import Metrics, child_trace, refusal_class
from .scheduler import QuotaBook
from .security import Authenticator, Policy, Principal
from .wire import HTTP_STATUS, MAX_MESSAGE_BYTES, decode, error_envelope

ROUTES = {
    "/v1/allocate": ("PK_ACCELERATOR_ALLOCATION_REQUEST/1", "lease:allocate"),
    "/v1/release": ("PK_ACCELERATOR_RELEASE_REQUEST/1", "lease:release"),
    "/v1/scrub": ("PK_SCRUB_REQUEST/1", "device:scrub"),
}


class Service:
    def __init__(self, controller: Controller, authn: Authenticator, policy: Policy, quotas: QuotaBook, *,
                 max_inflight: int = 32, metrics: Metrics | None = None, telemetry: Telemetry | None = None) -> None:
        self.ctl, self.authn, self.policy, self.quotas = controller, authn, policy, quotas
        self.sem = threading.BoundedSemaphore(max_inflight)
        self.metrics = metrics or Metrics()
        self.tel = telemetry or controller.tel
        self.clock = controller.clock

    def handle(self, path: str, body: bytes, credential: Any, *, traceparent: str | None = None,
               deadline_ms: int | None = None) -> tuple[int, dict[str, Any]]:
        started = time.perf_counter()
        trace = child_trace(traceparent)
        op = {"/v1/allocate": "allocate", "/v1/release": "release", "/v1/scrub": "scrub"}.get(path, "inventory")
        request_id = None
        if not self.sem.acquire(blocking=False):
            return self._fail(ControlError("OVERLOADED"), op, started, None, trace)
        try:
            t0 = self.clock.monotonic()
            if path not in ROUTES and path != "/v1/inventory":
                raise ControlError("SCHEMA_INVALID", "unknown route")
            if len(body) > MAX_MESSAGE_BYTES:
                raise ControlError("MESSAGE_TOO_LARGE")
            principal = self.authn.authenticate(credential)
            if path == "/v1/inventory":
                return 200, self._inventory(principal)
            schema, action = ROUTES[path]
            msg = decode(body, schema)
            request_id = self.scoped_id(path, principal, msg["request_id"])
            if deadline_ms is not None or "deadline_ms" in msg:
                budget = (deadline_ms or msg["deadline_ms"]) / 1000.0
                if self.clock.monotonic() - t0 > budget:
                    raise ControlError("DEADLINE_EXCEEDED")
            result = self._dispatch(path, action, msg, principal)
            self.metrics.inc("requests", operation=op, code="OK")
            self.metrics.observe("request_latency", time.perf_counter() - started, operation=op)
            self.tel.emit("service", op, request_id=request_id, trace_id=trace["trace_id"], span_id=trace["span_id"])
            return 200, {**result, "traceparent": trace["traceparent"]}
        except ControlError as exc:
            return self._fail(exc, op, started, request_id, trace)
        finally:
            self.sem.release()

    @staticmethod
    def scoped_id(path: str, p: Principal, rid: str) -> str:
        """Idempotency keys are namespaced by the authenticated tenant (operators: ``op``),
        so one tenant can neither replay nor collide with another tenant's key."""
        return f"op:{rid}" if path == "/v1/scrub" else f"{p.tenant}:{rid}"

    def _fail(self, exc: ControlError, op: str, started: float, request_id: str | None, trace: dict[str, str]) -> tuple[int, dict[str, Any]]:
        self.metrics.inc("requests", operation=op, code=exc.code)
        self.metrics.observe("request_latency", time.perf_counter() - started, operation=op)
        self.tel.emit("service", "refusal", code=exc.code, severity="WARN", request_id=request_id or "-",
                      trace_id=trace["trace_id"], detail=refusal_class(exc.code))
        return HTTP_STATUS.get(exc.code, 500 if refusal_class(exc.code) == "software_defect" else 409), error_envelope(exc, request_id)

    def _authorize(self, principal: Principal, action: str, resource: dict[str, Any]) -> None:
        d = self.policy.decide(principal, action, resource)
        if not d["allow"]:
            raise ControlError(d["code"], d["reason"])

    def _dispatch(self, path: str, action: str, msg: dict[str, Any], p: Principal) -> dict[str, Any]:
        if path == "/v1/allocate":
            if msg["tenant"] != p.tenant:
                raise ControlError("POLICY_DENIED", "tenant does not match authenticated principal")
            self._authorize(p, action, {"tenant": msg["tenant"], "kind": msg.get("kind", "gpu")})
            active = [l for _, (_, l) in self.ctl.leases().items()]
            self.quotas.check(p.tenant, active, msg)
            req = {k: msg[k] for k in ("tenant", "workload", "memory_gb", "kind", "generation", "features", "partition") if k in msg}
            return self.ctl.allocate(req, request_id=self.scoped_id(path, p, msg["request_id"]), actor=p.subject)
        if path == "/v1/release":
            cur = self.ctl.store.get(f"lease/{msg['lease_id']}")
            tenant = cur[1]["tenant"] if cur else p.tenant
            self._authorize(p, action, {"tenant": tenant, "kind": "gpu"})
            return self.ctl.release(msg["lease_id"], request_id=self.scoped_id(path, p, msg["request_id"]), actor=p.subject, tenant=p.tenant)
        if path == "/v1/scrub":
            self._authorize(p, action, {"kind": "gpu"})
            return self.ctl.scrub(msg["device"], request_id=self.scoped_id(path, p, msg["request_id"]), actor=p.subject)
        raise ControlError("SCHEMA_INVALID", "unknown route")

    def _inventory(self, p: Principal) -> dict[str, Any]:
        sensitive = self.policy.decide(p, "inventory:read_sensitive", {"kind": "gpu"})["allow"]
        if not sensitive:
            self._authorize(p, "inventory:read", {"kind": "gpu"})
        devs = []
        for name, (_, d) in sorted(self.ctl.devices().items()):
            rec = {k: d[k] for k in ("device", "kind", "generation", "memory_gb", "features", "partitions", "state", "health")}
            if sensitive:
                rec["security_tenant"] = d["security_tenant"]
            devs.append(rec)
        return {"schema": "PK_ACCELERATOR_INVENTORY/1", "devices": devs}


def encode_credential(token: dict[str, Any]) -> str:
    return "GAP11 " + base64.urlsafe_b64encode(json.dumps(token).encode()).decode()


def _decode_credential(header: str | None) -> Any:
    if not header or not header.startswith("GAP11 ") or len(header) > 8192:
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(header[6:].encode()))
    except Exception:
        return None


def serve_http(service: Service, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise ControlError("CONFIG_INVALID", "plaintext HTTP binding is loopback-only; production needs mTLS termination")

    class H(BaseHTTPRequestHandler):
        timeout = 10

        def log_message(self, *a: Any) -> None:  # structured telemetry instead of stderr
            pass

        def _send(self, status: int, payload: dict[str, Any] | str, ctype: str = "application/json") -> None:
            data = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                return self._send(200, {"live": True})
            if self.path == "/metrics":
                return self._send(200, service.metrics.expose(), "text/plain; version=0.0.4")
            status, body = service.handle(self.path, b"", _decode_credential(self.headers.get("Authorization")))
            self._send(status, body)

        def do_POST(self) -> None:
            try:
                n = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                n = -1
            if n < 0 or n > MAX_MESSAGE_BYTES:
                return self._send(413 if n > 0 else 411, error_envelope(ControlError("MESSAGE_TOO_LARGE" if n > 0 else "SCHEMA_INVALID")))
            body = self.rfile.read(n)
            dl = self.headers.get("X-Deadline-Ms")
            status, out = service.handle(self.path, body, _decode_credential(self.headers.get("Authorization")),
                                         traceparent=self.headers.get("traceparent"),
                                         deadline_ms=int(dl) if dl and dl.isdigit() else None)
            self._send(status, out)

    srv = ThreadingHTTPServer((host, port), H)
    srv.daemon_threads = True
    srv.request_queue_size = 64
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
