# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""INV-30 service boundary (GAP-016..GAP-019, GAP-021, GAP-033..GAP-038, GAP-048..GAP-053).

Callers never hold a ``Capability`` object: they hold an opaque handle
(``cap_<128-bit random>``) bound to one tenant and one signed root grant. Every
request is schema-validated, authenticated, authorized, admitted, deadline-bound,
audited, measured, traced, and explained. Every refusal is a PK_FAILURE/1 envelope.

State is deliberately volatile (see docs/STATE_AND_RECOVERY.md): a restart
invalidates every handle, which is the fail-safe direction for capabilities.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from . import __version__ as VERSION
from . import lifecycle, schema
from .audit import AuditLedger
from .authz import Authenticator, MintingAuthority
from .backend import HARDWARE, MODEL, SemanticModelBackend, select_backend
from .config import digest as config_digest
from .core import Capability, CapabilityError, Invalidated
from .errors import (SchemaInvalid, Unauthorized, Disabled, HardwareRequired, IdempotencyConflict, LimitExceeded, NotFound, Quarantined,
                     TenantMismatch, envelope)
from .limits import Limits
from .resilience import AdmissionController, CircuitBreaker, Deadline, StallDetector
from .telemetry import DecisionLog, Logger, Metrics, child_traceparent, tenant_bucket as _tb


@dataclass
class _Entry:
    cap: Capability
    tenant: str
    grant: dict
    parent: str | None
    children: set = field(default_factory=set)
    state: str = lifecycle.ACTIVE


class Lease:
    """Single-writer fencing lease (duplicate-controller protection, GAP-037).

    The epoch lives in a file; acquiring increments it. A service whose epoch is
    no longer current refuses every mutating operation (stale controller).
    """

    def __init__(self, path):
        self.path = path

    def _read(self) -> int:
        try:
            with open(self.path, encoding="utf-8") as fh:
                return int(fh.read().strip() or 0)
        except FileNotFoundError:
            return 0

    def acquire(self) -> int:
        epoch = self._read() + 1
        tmp = f"{self.path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(str(epoch))
        os.replace(tmp, self.path)
        return epoch

    def current(self, epoch: int) -> bool:
        return self._read() == epoch


class CapabilityService:
    def __init__(self, cfg: dict, *, authenticator: Authenticator, authority: MintingAuthority,
                 node: str = "node-0", backend=None, audit: AuditLedger | None = None, lease: Lease | None = None,
                 log_stream=False, clock=time.monotonic):
        self.cfg, self.node = cfg, node
        self.limits = Limits(**cfg["limits"]) if cfg.get("limits") else Limits()
        self.auth, self.authority = authenticator, authority
        self.backend = backend or select_backend(require_hardware=cfg["require_hardware"], mode=cfg["mode"])
        self.enforcement = getattr(self.backend, "enforcement", MODEL)
        self.audit = audit or AuditLedger()
        self.metrics, self.decisions = Metrics(), DecisionLog(node=node, release=VERSION)
        self.log = Logger(node=node, stream=log_stream)
        self.metrics.inc("invariant_violation_served", 0.0)  # exported as 0 so absence != healthy
        self.admission = AdmissionController(max_inflight=self.limits.max_inflight, tenant_rate=1e6,
                                             tenant_burst=self.limits.max_queue_depth, clock=clock)
        self.breaker = CircuitBreaker(clock=clock)
        self.stall = StallDetector(clock=clock)
        self.lease, self.epoch = lease, (lease.acquire() if lease else None)
        self.state = "bootstrapping"
        self._lock = threading.RLock()
        self._table: dict[str, _Entry] = {}
        self._per_tenant: dict[str, int] = {}
        self._idem: OrderedDict[str, tuple[str, dict]] = OrderedDict()
        self.quarantined_tenants: set[str] = set()
        self.state = lifecycle.transition(lifecycle.SERVICE_TRANSITIONS, self.state, "ready")
        self.audit.append("service.start", "ok", node=node, version=VERSION, enforcement=self.enforcement,
                          config_digest=config_digest(cfg), epoch=self.epoch)

    # ------------------------------------------------------------------ plumbing
    _SCHEMA_FOR = {"mint": "capability", "derive": "capability", "invalidate": "capability", "access": "access"}

    def _run(self, op: str, request: dict, auth: dict, fn):
        corr = uuid.uuid4().hex
        trace_id, tp = child_traceparent(request.get("traceparent"))
        tenant = request.get("tenant", "-") if isinstance(request, dict) else "-"
        t0 = time.perf_counter()
        try:
            # Validate shape first: hostile input never reaches auth, admission or state.
            if not isinstance(request, dict):
                raise SchemaInvalid("request must be an object")
            schema.validate(self._SCHEMA_FOR[op], request)
            if "tenant" not in request:
                raise SchemaInvalid("tenant is required at the service boundary")
            if self.state == "disabled":
                raise Disabled("INV-30 is emergency-disabled")
            if self.state == "quarantined" and op != "invalidate":
                raise Quarantined("INV-30 is quarantined; only invalidation is permitted")
            principal = self.auth.authenticate(action=op, body=request, **auth)
            self.auth.authorize(principal, op, tenant)
            if tenant in self.quarantined_tenants and op != "invalidate":
                raise Quarantined(f"tenant is quarantined")
            if self.lease and op in ("mint", "derive") and not self.lease.current(self.epoch):
                raise Disabled("stale controller: lease epoch superseded")
            deadline = Deadline(request.get("deadline_ms", 5000) / 1000.0)
            if op == "invalidate":
                # Security-critical: revocation is never shed by admission control (GAP-035-IMP-04).
                result = fn(principal, corr)
            else:
                with self.admission.admit(tenant):
                    deadline.check()
                    result = fn(principal, corr)
                    deadline.check()
            self.stall.beat()
            self.metrics.inc("requests", op=op, outcome="ok")
            self.decisions.record("allow", f"{op} permitted", inputs={"op": op, "tenant_bucket": _tb(tenant)},
                                  policy="precedence:capability-invariant>security>...", correlation_id=corr)
            self.log.log("info", f"{op}.ok", tenant=tenant, operation=op, correlation_id=corr, trace_id=trace_id)
            return dict(result, correlation_id=corr, traceparent=tp)
        except Exception as exc:  # noqa: BLE001 - boundary converts everything to an envelope
            env = envelope(exc, corr, VERSION)
            self.metrics.inc("requests", op=op, outcome=env["code"])
            if env["code"] == "BOUNDS_VIOLATION":
                self.metrics.inc("bounds_violations")
            elif env["code"] == "PERMISSION_VIOLATION":
                self.metrics.inc("permission_violations")
            elif env["code"] == "INVALIDATED":
                self.metrics.inc("invalidated_uses")
            self.decisions.record("deny", env["code"], inputs={"op": op, "tenant_bucket": _tb(tenant)},
                                  policy="fail-closed", correlation_id=corr)
            if env["category"] in ("security", "policy"):
                self.audit.append(f"{op}.refused", env["code"], tenant=tenant, correlation_id=corr)
            self.log.log("warning", f"{op}.refused", tenant=tenant, operation=op, correlation_id=corr,
                         trace_id=trace_id, code=env["code"])
            return dict(env, traceparent=tp)
        finally:
            self.metrics.observe_ms("latency_ms", (time.perf_counter() - t0) * 1000, op=op)

    def _get(self, handle: str, tenant: str) -> _Entry:
        e = self._table.get(handle)
        if e is None:
            raise NotFound("unknown capability handle")
        if e.tenant != tenant:
            raise TenantMismatch("capability belongs to a different tenant")
        self.authority.verify(e.grant, tenant=tenant)
        return e

    def _insert(self, cap, tenant, grant, parent) -> str:
        if len(self._table) >= self.limits.max_capabilities_total:
            raise LimitExceeded("global capability limit reached")
        if self._per_tenant.get(tenant, 0) >= self.limits.max_capabilities_per_tenant:
            raise LimitExceeded("tenant capability quota reached")
        if tenant not in self._per_tenant and len(self._per_tenant) >= self.limits.max_tenants:
            raise LimitExceeded("tenant limit reached")
        handle = "cap_" + os.urandom(16).hex()
        self._table[handle] = _Entry(cap, tenant, grant, parent)
        self._per_tenant[tenant] = self._per_tenant.get(tenant, 0) + 1
        if parent:
            self._table[parent].children.add(handle)
        self.metrics.set("active_capabilities", len(self._table))
        return handle

    # ------------------------------------------------------------------ operations
    def mint(self, request: dict, auth: dict) -> dict:
        """Mint a root capability. ``require_hardware`` in the request is honoured fail-closed."""
        def op(principal, corr):
            schema.validate("capability", request)
            if request.get("op") != "mint" or "tenant" not in request:
                raise SchemaInvalid("mint requires op='mint' and a tenant")
            if request.get("require_hardware") and self.enforcement != HARDWARE:
                raise HardwareRequired("workload requires hardware capability enforcement; this node has none")
            cap = self.breaker.call(lambda: self.backend.mint(request["base"], request["length"],
                                                              request["permissions"]))
            grant = self.authority.grant(tenant=request["tenant"], base=cap.base, length=cap.length,
                                         permissions=cap.permissions, enforcement=self.enforcement,
                                         minted_by=principal.name)
            with self._lock:
                handle = self._insert(cap, request["tenant"], grant, None)
            self.audit.append("mint", "ok", tenant=request["tenant"], grant_id=grant["grant_id"],
                              principal=principal.name, correlation_id=corr, enforcement=self.enforcement)
            return {"schema": "PK_CAPABILITY/1", "handle": handle, "enforcement": self.enforcement,
                    "grant_id": grant["grant_id"]}
        return self._run("mint", request, auth, op)

    def derive(self, request: dict, auth: dict) -> dict:
        def op(principal, corr):
            schema.validate("capability", request)
            key = request.get("idempotency_key")
            fp = config_digest({k: v for k, v in request.items() if k not in ("traceparent", "deadline_ms")})
            with self._lock:
                if key:
                    prior = self._idem.get(f"{request['tenant']}:{key}")
                    if prior:
                        if prior[0] != fp:
                            raise IdempotencyConflict("idempotency key reused with a different request")
                        return prior[1]
                e = self._get(request["handle"], request["tenant"])
                child = e.cap.derive(base=request["base"], length=request["length"],
                                     permissions=request.get("permissions"))
                handle = self._insert(child, e.tenant, e.grant, request["handle"])
                self.metrics.inc("capability_derivations", narrowing=_narrow_bucket(e.cap, child))
                out = {"schema": "PK_CAPABILITY/1", "handle": handle, "enforcement": self.enforcement}
                if key:
                    self._idem[f"{request['tenant']}:{key}"] = (fp, out)
                    while len(self._idem) > self.limits.idempotency_cache_entries:
                        self._idem.popitem(last=False)
            self.audit.append("derive", "ok", tenant=request["tenant"], correlation_id=corr)
            return out
        return self._run("derive", request, auth, op)

    def access(self, request: dict, auth: dict) -> dict:
        def op(principal, corr):
            schema.validate("access", request)
            with self._lock:
                e = self._get(request["handle"], request["tenant"])
            rec = e.cap.check(address=request["address"], size=request["size"], operation=request["operation"])
            # Defence in depth: independently re-verify the zero-budget invariant before serving.
            a, n = request["address"], request["size"]
            if not (e.cap.valid and e.cap.base <= a and a + n <= e.cap.limit
                    and request["operation"] in e.cap.permissions):
                self.metrics.inc("invariant_violation_served")
                raise RuntimeError("invariant self-check failed; access withheld")
            rec["enforcement"] = self.enforcement if self.enforcement == HARDWARE else rec["enforcement"]
            schema.validate("access_result", rec)
            return rec
        return self._run("access", request, auth, op)

    def invalidate(self, request: dict, auth: dict) -> dict:
        """Invalidate a handle and (revocation sweep) every capability derived from it."""
        def op(principal, corr):
            schema.validate("capability", request)
            with self._lock:
                self._get(request["handle"], request["tenant"])
                swept, stack = [], [request["handle"]]
                while stack:
                    h = stack.pop()
                    ent = self._table[h]
                    if ent.state != lifecycle.INVALIDATED:
                        ent.cap.invalidate()
                        ent.state = lifecycle.transition(lifecycle.CAPABILITY_TRANSITIONS, ent.state,
                                                         lifecycle.INVALIDATED)
                        swept.append(h)
                    stack.extend(ent.children)
            self.audit.append("invalidate", "ok", tenant=request["tenant"], swept=len(swept), correlation_id=corr)
            return {"schema": "PK_CAPABILITY/1", "invalidated": len(swept)}
        return self._run("invalidate", request, auth, op)

    # ------------------------------------------------------------------ operator controls
    def quarantine_tenant(self, tenant: str, *, operator: str, reason: str):
        self.quarantined_tenants.add(tenant)
        self.audit.append("quarantine.tenant", "ok", tenant=tenant, operator=operator, reason=reason)

    def release_tenant(self, tenant: str, *, operator: str, reason: str):
        self.quarantined_tenants.discard(tenant)
        self.audit.append("release.tenant", "ok", tenant=tenant, operator=operator, reason=reason)

    def set_state(self, target: str, *, operator: str, reason: str):
        with self._lock:
            self.state = lifecycle.transition(lifecycle.SERVICE_TRANSITIONS, self.state, target)
            if target == "disabled":  # emergency disable revokes everything: fail safe
                for ent in self._table.values():
                    if ent.state != lifecycle.INVALIDATED:
                        ent.cap.invalidate()
                        ent.state = lifecycle.INVALIDATED
        self.audit.append(f"service.{target}", "ok", operator=operator, reason=reason)

    def open_deep_diagnostics(self, *, operator: str, principal_auth: dict, ttl_s: float, reason: str) -> str:
        """Privileged, expiring, audited diagnostics session (GAP-052-IMP-03). Requires the 'admin' action."""
        body = {"op": "deep_diagnostics", "ttl_s": ttl_s, "reason": reason}
        p = self.auth.authenticate(action="admin", body=body, **principal_auth)
        self.auth.authorize(p, "admin", "*")
        if not 0 < ttl_s <= 3600:
            raise SchemaInvalid("ttl_s must be in (0, 3600]")
        token = os.urandom(16).hex()
        self._diag = {"token": token, "expires": time.monotonic() + ttl_s, "operator": operator}
        self.audit.append("diagnostics.open", "ok", operator=operator, principal=p.name, ttl_s=ttl_s, reason=reason)
        return token

    def deep_diagnostics(self, token: str) -> dict:
        d = getattr(self, "_diag", None)
        if not d or d["token"] != token or time.monotonic() > d["expires"]:
            raise Unauthorized("no valid deep-diagnostics session")
        self.audit.append("diagnostics.read", "ok", operator=d["operator"])
        with self._lock:  # tenant ids appear here (privileged), bases/handles still never do
            per_tenant = dict(self._per_tenant)
        return {"per_tenant_capabilities": per_tenant, "quarantined": sorted(self.quarantined_tenants),
                "breaker": self.breaker.state, "inflight": self.admission.inflight, "shed": self.admission.shed}

    # ------------------------------------------------------------------ introspection
    def health(self) -> dict:
        from .deps import pk_core_status, sibling_status
        status = self.state if self.state in ("quarantined", "disabled") else (
            "stalled" if self.stall.stalled(self.admission.inflight) else
            "degraded" if self.breaker.state != "closed" or self.state == "degraded" else "healthy")
        h = {"schema": "INV30_HEALTH/1", "status": status, "ready": status in ("healthy", "degraded"),
             "version": VERSION, "enforcement": self.enforcement, "config_digest": config_digest(self.cfg),
             "mode": self.cfg["mode"], "active_capabilities": sum(
                 1 for e in self._table.values() if e.state != lifecycle.INVALIDATED),
             "dependencies": {"pk_core": pk_core_status()["state"],
                              **{k: v["state"] for k, v in sibling_status().items()},
                              "backend": self.backend.available()["available"],
                              "circuit": self.breaker.state},
             "saturation": round(self.admission.saturation(), 4), "epoch": self.epoch,
             "schemas": {"capability": "PK_CAPABILITY/1", "access": "PK_CAPABILITY_ACCESS/1",
                         "failure": "PK_FAILURE/1"},
             "hardware": {k: v for k, v in _probe().items() if k in ("state", "signal")},
             "ready_for_hardware_workloads": self.enforcement == HARDWARE and self.state in ("ready",),
             "audit_head": self.audit.head}
        schema.validate("health", h)
        return h


def _probe():
    from .discovery import probe_cheri
    return probe_cheri()


def _narrow_bucket(parent: Capability, child: Capability) -> str:
    ratio = child.length / parent.length if parent.length else 1.0
    return "none" if ratio == 1 else "<10%" if ratio < 0.1 else "<50%" if ratio < 0.5 else ">=50%"
