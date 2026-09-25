"""Composed INV-04 service: controller + transport (components 24, 26, 47
wiring; integrates 3, 5, 8, 22-35, 44-50).

``Orchestrator`` owns one site's control loop.  ``Service.handle`` is a
transport-neutral request handler (method, path, headers, body) -> (status,
headers, body) that enforces, in order: protocol negotiation, size limit,
authentication, schema validation, authorization, tenant scope, admission,
leadership, idempotency, then executes and maps any error to
``application/problem+json`` carrying the PK_ORCH_ERROR/1 envelope.
``serve()`` binds it to the stdlib HTTP server; TLS/mTLS termination is
expected from the deployment (component 29, see docs/ADR-0001).
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from .api import InMemoryClusterAPI, check_discovery
from .config import RuntimeConfig
from .drain import DrainCoordinator, DrainOptions
from .errors import TRANSPORT_MAP, IncompatibleProtocol, RuntimeFault, SchemaViolation
from .handoff import take_snapshot
from .journal import AuditTrail, IdempotencyRegistry, Journal
from .lease import LeaderElector
from .observability import ConvergenceSLO, Health, Registry, Tracer, get_logger, log_event, standard_metrics
from .resilience import Context, TokenBucket
from .security import (DEFAULT_RULES, AdmissionPolicy, Authorizer, TokenAuthenticator, scope_filter)
from .store import VersionedStore
from .validation import MAX_BYTES, advertise, negotiate, parse_and_validate, validate
from ..model import OrchestrationError


def problem(exc: BaseException, *, instance: str = "") -> tuple[int, dict]:
    """Map any error to (HTTP status, problem+json body with PK_ORCH_ERROR/1 fields)."""
    if isinstance(exc, (RuntimeFault, OrchestrationError)) or hasattr(exc, "as_dict"):
        env = exc.as_dict()  # type: ignore[union-attr]
    else:
        env = {"code": "ORCH_RUNTIME_ERROR", "message": "internal error"}  # never leak internals
    status, grpc, k8s = TRANSPORT_MAP.get(env["code"], TRANSPORT_MAP["ORCH_RUNTIME_ERROR"])
    body = {"type": f"urn:pk:orch:error:{env['code']}", "title": env["code"], "status": status,
            "detail": env["message"], "instance": instance, "grpc_status": grpc, "k8s_reason": k8s, **env}
    return status, body


REJECTION_CODES = {"budget_breach": "ORCH_BUDGET_BREACH", "no_capacity": "ORCH_NO_CAPACITY",
                   "unknown_node": "ORCH_UNKNOWN_NODE", "drain_policy": "ORCH_DRAIN_POLICY",
                   "eviction_failed": "ORCH_EVICTION_BLOCKED", "verify_timeout": "ORCH_DEADLINE_EXCEEDED"}


class Orchestrator:
    def __init__(self, api: InMemoryClusterAPI, *, config: RuntimeConfig | None = None, journal: Journal | None = None,
                 identity: str = "inv04-0", clock: Callable[[], float] = time.time):
        self.api = api
        self.cfg = config or RuntimeConfig()
        self.journal = journal or Journal()
        self.clock = clock
        self.lease_store = VersionedStore()
        self.elector = LeaderElector(self.lease_store, f"inv04-{self.cfg.site}", identity,
                                     lease_seconds=self.cfg.lease_seconds, renew_deadline=self.cfg.renew_deadline_s,
                                     clock=clock)
        self.registry = Registry()
        self.m = standard_metrics(self.registry)
        self.tracer = Tracer()
        self.log = get_logger("inv04")
        self.slo = ConvergenceSLO(self.cfg.convergence_slo_s, self.cfg.convergence_objective)
        self.audit = AuditTrail(self.journal)
        self.idem = IdempotencyRegistry(self.journal)
        self.health = Health()
        self.health.add("leader", lambda: (self.elector.is_leader(), "leader" if self.elector.is_leader() else "standby"))
        self.health.add("api_discovery", self._discovery_ok)
        self.drainer = DrainCoordinator(api, self.journal, fencing_token=lambda: self.elector.token,
                                        on_transition=self._on_transition, settle=self.api.run_controllers,
                                        sleep=lambda s: None)

    def _discovery_ok(self) -> tuple[bool, str]:
        check_discovery(self.api)
        return True, "served"

    def _on_transition(self, op_id: str, phase: str, reason: str) -> None:
        log_event(self.log, "drain transition", op_id=op_id, phase=phase, reason=reason)

    def start(self) -> None:
        check_discovery(self.api)
        self.elector.try_acquire_or_renew()
        self.m["leader"].set(1 if self.elector.is_leader() else 0)
        if self.elector.is_leader():
            self.drainer.recover()
        self.health.started = True

    def observe(self) -> None:
        pods, _ = self.api.list_pods()
        for w, want in sorted(self.api.desired.items()):
            have = sum(1 for p in pods if p.workload == w and p.phase == "Running")
            self.m["replicas_desired"].set(want, workload=w)
            self.m["replicas_running"].set(have, workload=w)
            self.m["replica_drift"].set(want - have, workload=w)
            self.slo.observe(w, want, have)
        self.health.heartbeat()

    def reconcile(self) -> int:
        self.elector.require_leader()
        t0 = time.monotonic()
        with self.tracer.span("reconcile"):
            created = self.api.run_controllers()
        self.m["reconcile_seconds"].observe(time.monotonic() - t0)
        self.m["reconcile_total"].inc(outcome="ok")
        self.observe()
        return created

    def drain(self, node: str, *, op_id: str, actor: str, options: DrainOptions | None = None) -> dict:
        self.elector.require_leader()
        t0 = time.monotonic()
        with self.tracer.span("drain", node=node, op_id=op_id):
            res = self.drainer.drain(node, op_id=op_id, options=options,
                                     ctx=Context(timeout=self.cfg.drain_timeout_s))
        self.m["drains_total"].inc(outcome=res.phase, reason=res.reason.split(":")[0])
        self.m["drain_seconds"].observe(time.monotonic() - t0, outcome=res.phase)
        if res.reason == "budget_breach":
            self.m["budget_blocks"].inc()
        if res.reason == "no_capacity":
            self.m["capacity_failures"].inc()
        self.slo.record_drain(breached_budget=False)  # breaches are refused before eviction by construction
        self.audit.record(actor=actor, action="drain", target=node, outcome=res.phase, reason=res.reason)
        self.observe()
        return res.as_dict()

    def inventory(self, tenant: str | None = None) -> dict:
        pods, rv = self.api.list_pods()
        if tenant is not None:
            pods = scope_filter(pods, tenant, dict(self.cfg.namespace_tenants))
        return take_snapshot(pods, rv, clock=self.clock).as_dict()


class Service:
    def __init__(self, orch: Orchestrator, authn: TokenAuthenticator, *, authz: Authorizer | None = None,
                 admission: AdmissionPolicy | None = None):
        self.o = orch
        self.authn = authn
        self.authz = authz or Authorizer(list(DEFAULT_RULES))
        self.admission = admission or AdmissionPolicy()
        self.limiter = TokenBucket(orch.cfg.api_qps, orch.cfg.api_burst)
        self._drain_lock = threading.Lock()

    def handle(self, method: str, path: str, headers: dict[str, str], body: bytes = b"") -> tuple[int, dict, bytes]:
        h = {k.lower(): v for k, v in headers.items()}
        try:
            if path.startswith("/healthz") or path.startswith("/readyz") or path.startswith("/livez"):
                code, data = {"/healthz": self.o.health.startup, "/livez": self.o.health.liveness,
                              "/readyz": self.o.health.readiness}.get(path, self.o.health.readiness)()
                return self._json(code, data)
            if path == "/metrics":
                return 200, {"content-type": "text/plain; version=0.0.4"}, self.o.registry.render().encode()
            if path == "/v1/versions":
                return self._json(200, advertise())
            self.limiter.acquire(what="api")
            if len(body) > MAX_BYTES:
                raise SchemaViolation("request body too large")
            principal = self.authn.authenticate(h.get("authorization"))
            tenant = h.get("x-pk-tenant", principal.tenant)
            site = self.o.cfg.site
            if method == "POST" and path == "/v1/drain":
                rev = negotiate("PK_ORCH_DRAIN", [v.strip() for v in h.get("x-pk-accept-revision", "1.0").split(",")])
                req = parse_and_validate("PK_ORCH_DRAIN/1", body)
                if rev == "1.0" and set(req) - {"node"}:
                    raise IncompatibleProtocol("revision 1.0 accepts only 'node'")
                self.authz.authorize(principal, "drain", tenant=tenant, site=site)
                self.admission.admit("drain", principal, tenant=tenant, site=site,
                                     emergency_reason=h.get("x-pk-emergency-reason", ""))
                key = req.get("idempotency_key") or h.get("idempotency-key")
                if not key:
                    raise SchemaViolation("drain requires an idempotency key (body or Idempotency-Key header)")
                opts = DrainOptions(dry_run=bool(req.get("dry_run", False)),
                                    delete_emptydir_data=bool(req.get("delete_emptydir_data", False)),
                                    force_unmanaged=bool(req.get("force_unmanaged", False)))
                with self._drain_lock:
                    self.admission.begin(site)
                    try:
                        result, replayed = self.o.idem.execute(
                            key, {"node": req["node"], "opts": opts.__dict__, "tenant": tenant},
                            lambda: self.o.drain(req["node"], op_id=f"drain:{key}", actor=principal.subject, options=opts))
                    finally:
                        self.admission.end(site)
                status = 200
                rej_code: str | None = None
                if result["phase"] != "completed":
                    rej_code = REJECTION_CODES.get(result["reason"].split(":")[0], "ORCH_DRAIN_POLICY")
                    status = TRANSPORT_MAP[rej_code][0]
                payload = {**result, "replayed": replayed}
                if rej_code:
                    payload.update({"code": rej_code, "message": f"drain {result['phase']}: {result['reason']}"})
                return self._json(status, payload, {"x-pk-revision": rev})
            if method == "GET" and path == "/v1/inventory":
                self.authz.authorize(principal, "inventory", tenant=tenant, site=site)
                snap = self.o.inventory(tenant)
                validate("PK_ORCH_INVENTORY/1", {w: sorted(p["node"] for p in ps) for w, ps in snap["workloads"].items()})
                return self._json(200, snap)
            if method == "POST" and path == "/v1/reconcile":
                self.authz.authorize(principal, "reconcile", tenant=tenant, site=site)
                self.admission.admit("reconcile", principal, tenant=tenant, site=site)
                return self._json(200, {"created": self.o.reconcile()})
            return self._json(404, {"code": "ORCH_NOT_FOUND", "message": "no such route"})
        except BaseException as exc:  # noqa: BLE001 - every error becomes a stable envelope
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            status, body_ = problem(exc, instance=path)
            self.o.m["api_errors"].inc(code=body_["code"])
            log_event(self.o.log, "request failed", path=path, code=body_["code"], status=status)
            return status, {"content-type": "application/problem+json"}, json.dumps(body_, sort_keys=True).encode()

    @staticmethod
    def _json(code: int, data: Any, extra: dict | None = None) -> tuple[int, dict, bytes]:
        return code, {"content-type": "application/json", **(extra or {})}, json.dumps(data, sort_keys=True).encode()


def serve(service: Service, host: str = "127.0.0.1", port: int = 8404) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _do(self):
            n = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(min(n, MAX_BYTES + 1)) if n else b""
            code, headers, out = service.handle(self.command, self.path, dict(self.headers), body)
            self.send_response(code)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("content-length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        do_GET = do_POST = _do

        def log_message(self, *a):  # route through structured logger instead
            pass

    srv = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True, name="inv04-http").start()
    return srv
