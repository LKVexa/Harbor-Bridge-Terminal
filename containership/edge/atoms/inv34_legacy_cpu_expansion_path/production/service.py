"""HTTP control-plane boundary (MC-009, MC-013, MC-014, MC-027, MC-050, MC-051, MC-055).

SPDX-License-Identifier: NOASSERTION

``Api.handle`` is a pure function of (method, path, headers, body) so every
route is contract-testable without sockets; ``serve`` wraps it in the stdlib
``ThreadingHTTPServer``.  TLS termination is expected in front of this
process (integration item, see governance/BLOCKERS.json).
"""
from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .. import __version__
from ..expansion import ExpansionError, REQUEST_SCHEMA
from .observation import ObservationRejected
from .resilience import AdmissionController, Overloaded
from .security import Authenticator, AuthError, CapabilityPolicy, Forbidden, QuotaExceeded, VmBinding
from .store import StoreError
from .telemetry import StructuredLogger, child_traceparent

SUPPORTED_PROTOCOLS = ("1",)
MAX_BODY = 16 * 1024
REQUEST_FIELDS = {"schema", "request_id", "vm_id", "target_vcpus", "expected_generation"}

STATUS_FOR_CODE = {
    "INVALID_REQUEST": 400, "UNAUTHENTICATED": 401, "FORBIDDEN": 403, "NOT_FOUND": 404,
    "IDEMPOTENCY_CONFLICT": 409, "STALE_GENERATION": 409, "SHRINK_NOT_SUPPORTED": 422,
    "GUEST_LIMIT_EXCEEDED": 422, "HOTPLUG_UNSUPPORTED": 422, "EXPANSION_DISABLED": 423,
    "POLICY_DENIED": 422, "HOST_CAPACITY_EXCEEDED": 409, "QUOTA_EXCEEDED": 429, "OVERLOADED": 429,
    "DEGRADED_MODE": 503, "DEADLINE_EXCEEDED": 504, "UNSUPPORTED_PROTOCOL": 426,
    "PAYLOAD_TOO_LARGE": 413, "STORE_ERROR": 503,
}


def _err(code: str, msg: str, retryable: bool = False, **ctx: Any) -> tuple[int, dict]:
    return STATUS_FOR_CODE.get(code, 500), {"error": {"code": code, "message": msg, "retryable": retryable,
                                                      "context": ctx}}


class Api:
    def __init__(self, service, authn: Authenticator, policy: CapabilityPolicy, bindings: dict[str, VmBinding],
                 *, config_repo=None, release: str = "", admission: AdmissionController | None = None,
                 logger: StructuredLogger | None = None) -> None:
        self.svc, self.authn, self.policy, self.bindings = service, authn, policy, bindings
        self.config_repo, self.release = config_repo, release or f"inv34-{__version__}"
        self.admission = admission or AdmissionController()
        self.log = logger or StructuredLogger("inv34.api")
        self.started = time.time()

    # -- dispatcher -----------------------------------------------------------
    def handle(self, method: str, path: str, headers: dict[str, str], body: bytes) -> tuple[int, dict, dict]:
        h = {k.lower(): v for k, v in headers.items()}
        trace_id, span_id, tp = child_traceparent(h.get("traceparent"))
        out_headers = {"traceparent": tp, "x-inv34-protocol": SUPPORTED_PROTOCOLS[-1],
                       "content-type": "application/json"}
        url = urlsplit(path)
        route = (method, url.path)
        try:
            if route == ("GET", "/healthz"):
                return 200, out_headers, {"status": "alive"}
            if route == ("GET", "/readyz"):
                return self._ready(out_headers)
            if route == ("GET", "/version"):
                return 200, out_headers, self._version()
            if route == ("GET", "/metrics"):
                out_headers["content-type"] = "text/plain; version=0.0.4"
                self._refresh_gauges()
                return 200, out_headers, {"_text": self.svc.metrics.render()}
            proto = h.get("x-inv34-protocol", "1")
            if proto not in SUPPORTED_PROTOCOLS:
                s, b = _err("UNSUPPORTED_PROTOCOL", f"protocol {proto!r} not supported",
                            supported=list(SUPPORTED_PROTOCOLS))
                return s, out_headers, b
            if len(body) > MAX_BODY:
                s, b = _err("PAYLOAD_TOO_LARGE", "body exceeds 16 KiB")
                return s, out_headers, b
            dl = h.get("x-inv34-deadline-ms")
            if dl is not None and (not dl.isdigit() or int(dl) <= 0):
                s, b = _err("DEADLINE_EXCEEDED", "deadline already expired; no side effect performed")
                return s, out_headers, b
            auth = h.get("authorization", "")
            principal = self.authn.authenticate(auth[6:] if auth.startswith("INV34 ") else None)
            q = parse_qs(url.query)
            try:
                self.admission.acquire(timeout_s=min(2.0, int(dl) / 1000 if dl else 2.0))
            except Overloaded as exc:
                s, b = _err("OVERLOADED", str(exc), True)
                out_headers["retry-after"] = "1"
                return s, out_headers, b
            try:
                return self._route(route, principal, q, body, out_headers, trace_id)
            finally:
                self.admission.release()
        except AuthError as exc:
            self.svc.audit.append("authn.failed", reason=str(exc), path=url.path)
            s, b = _err("UNAUTHENTICATED", str(exc))
        except Forbidden as exc:
            self.svc.audit.append("authz.denied", reason=str(exc), path=url.path)
            s, b = _err("FORBIDDEN", str(exc))
        except QuotaExceeded as exc:
            s, b = _err("QUOTA_EXCEEDED", str(exc), True)
        except ObservationRejected as exc:
            s, b = _err("INVALID_REQUEST", str(exc), observation_code=exc.code)
        except ExpansionError as exc:
            d = exc.as_dict()
            s, b = _err(d["code"], d["message"], d["retryable"], **{k: v for k, v in d["context"].items()
                                                                   if isinstance(v, (int, str, bool, list))})
        except StoreError as exc:
            s, b = _err("STORE_ERROR", exc.__class__.__name__, True)
        except (ValueError, KeyError) as exc:
            s, b = _err("INVALID_REQUEST", f"malformed request: {exc.__class__.__name__}")
        self.svc.metrics.inc("inv34_http_errors_total", code=b["error"]["code"])
        return s, out_headers, b

    def _binding(self, vm_id: Any) -> VmBinding:
        if not isinstance(vm_id, str) or vm_id not in self.bindings:
            raise Forbidden("unknown or unbound VM")   # do not reveal existence
        return self.bindings[vm_id]

    def _route(self, route, principal, q, body, hdrs, trace_id):
        if route == ("POST", "/v1/cpu/expand"):
            req = json.loads(body or b"{}")
            if not isinstance(req, dict) or set(req) - REQUEST_FIELDS or req.get("schema") != REQUEST_SCHEMA:
                raise ValueError("request does not match PK_CPU_EXPANSION_REQUEST/1")
            vm = self._binding(req.get("vm_id"))
            self.policy.authorize(principal, "cpu.expand", vm)
            digest = self.config_repo.active_digest() if self.config_repo else ""
            res = self.svc.submit(vm.vm_id, req.get("request_id"), req.get("target_vcpus"),
                                  req.get("expected_generation"), actor=principal.principal_id,
                                  trace_id=trace_id, config_digest=digest or "")
            return (202 if res["status"] == "accepted" else 200), hdrs, res
        if route == ("GET", "/v1/cpu/status"):
            vm = self._binding((q.get("vm_id") or [None])[0])
            self.policy.authorize(principal, "cpu.status", vm)
            return 200, hdrs, self.svc.status(vm.vm_id)
        if route == ("POST", "/v1/cpu/observe"):
            report = json.loads(body or b"{}")
            vm = self._binding(report.get("vm_id") if isinstance(report, dict) else None)
            self.policy.authorize(principal, "cpu.observe", vm)
            return 200, hdrs, self.svc.observe(report)
        if route in (("POST", "/v1/ops/disable"), ("POST", "/v1/ops/enable")):
            req = json.loads(body or b"{}")
            vm = self._binding(req.get("vm_id"))
            action = "ops.disable" if route[1].endswith("disable") else "ops.enable"
            self.policy.authorize(principal, action, vm)
            return 200, hdrs, self.svc.set_enabled(vm.vm_id, action == "ops.enable", principal.principal_id)
        if route == ("GET", "/v1/explain"):
            vm = self._binding((q.get("vm_id") or [None])[0])
            self.policy.authorize(principal, "ops.explain", vm)
            return 200, hdrs, self.explain(vm.vm_id)
        return 404, hdrs, {"error": {"code": "NOT_FOUND", "message": "no such route", "retryable": False}}

    # -- surfaces ---------------------------------------------------------------
    def _refresh_gauges(self) -> None:
        stalled = pending = backlog = 0
        for vm in self.bindings:
            try:
                st = self.svc.status(vm)
            except Exception:  # noqa: BLE001 - a missing VM document must not break the exporter
                continue
            backlog += st["pending_vcpus"]
            pending += st["pending_operations"]
            stalled += st["convergence"]["state"] in ("STALLED", "PARTIAL_STALL")
        self.svc.metrics.set("inv34_stalled_vms", stalled)
        self.svc.metrics.set("inv34_pending_vcpus", backlog)
        self.svc.metrics.set("inv34_pending_operations", pending)
        self.svc.metrics.set("inv34_admission_in_flight", self.admission.in_flight)
        self.svc.metrics.set("inv34_admission_shed_total", self.admission.shed)

    def _version(self) -> dict:
        return {"component": "INV-34", "version": __version__, "release": self.release,
                "protocols": list(SUPPORTED_PROTOCOLS), "adapter": getattr(self.svc.adapter, "name", "?"),
                "adapter_version": getattr(self.svc.adapter, "version", "?"),
                "config_digest": self.config_repo.active_digest() if self.config_repo else None}

    def _ready(self, hdrs) -> tuple[int, dict, dict]:
        mode = self.svc.health.mode()
        cfg_ok = True
        if self.config_repo is not None:
            try:
                self.config_repo.active()
            except Exception:
                cfg_ok = False
        ready = cfg_ok
        body = {"ready": ready, "mode": mode, "dependencies": dict(self.svc.health.status),
                "config_active": cfg_ok, "breaker": self.svc.breaker.state, **self._version()}
        return (200 if ready else 503), hdrs, body

    def explain(self, vm_id: str) -> dict:
        """Links inputs, policy trace, state generation, config and adapter history (MC-055)."""
        doc = self.svc.store.load(vm_id)
        return {"vm_id": vm_id, "status": self.svc.status(vm_id),
                "last_policy_decision": self.svc.last_decision.get(vm_id),
                "journal": doc["journal"][-5:], "config_digest": self.config_repo.active_digest()
                if self.config_repo else None, "release": self.release,
                "dependency_mode": self.svc.health.mode()}


def serve(api: Api, host: str = "127.0.0.1", port: int = 8734) -> ThreadingHTTPServer:  # pragma: no cover
    class H(BaseHTTPRequestHandler):
        def _do(self, method):
            n = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(min(n, MAX_BODY + 1))
            status, hdrs, payload = api.handle(method, self.path, dict(self.headers), body)
            data = payload["_text"].encode() if "_text" in payload else json.dumps(payload, sort_keys=True).encode()
            self.send_response(status)
            for k, v in hdrs.items():
                self.send_header(k, v)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._do("GET")

        def do_POST(self):
            self._do("POST")

        def log_message(self, *a):
            pass
    return ThreadingHTTPServer((host, port), H)
