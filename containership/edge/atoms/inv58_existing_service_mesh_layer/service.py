"""INV-58 boundary service: the single enforcement point for every public operation.

Every call follows the same fail-closed pipeline (docs/REQUIREMENTS.md INV58-SR-001):

    validate envelope/version/size -> authenticate -> authorize (capability,
    actor type, mechanism, tenant scope) -> lifecycle/freeze/quarantine ->
    admission control -> execute (bounded, tenant-keyed state) -> decision
    journal + audit + metrics + structured log (trace-correlated)

State is keyed by tenant so no operation can read or write another tenant's
routes, bypass evidence or journal entries (MC-013).  Trust-dependency outages
follow the validated ``trust_outage_policy`` (MC-014); noncritical telemetry
outage degrades rather than fails (MC-019).
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Mapping

from . import __version__
from .audit import AuditLog
from .authz import Authenticator, Authorizer, CapabilityPolicy, Principal
from .config import ConfigError, ConfigStore, Provenance, validate
from .errors import MeshError
from .integrity import Verifier, hmac_check
from .mesh_logic import BypassDetector, RoutePolicyRegistry, Unmappable, map_identity, reconcile
from .resilience import AdmissionController, CircuitBreaker, ControlSwitches, FencingGuard, Lifecycle
from .secret_refs import SecretResolutionError, SecretResolver, redact
from .telemetry import Metrics, Pseudonymizer, StructuredLogger, TraceContext

INTERFACE_VERSIONS = {
    "reconcile": ("PK_MESH_RECONCILE/1",),
    "identity": ("PK_MESH_IDENTITY/1",),
    "bypass": ("PK_MESH_BYPASS/1",),
}
STATUS_SCHEMA = "PK_MESH_STATUS/1"
SNAPSHOT_SCHEMA = "PK_MESH_SNAPSHOT/1"
DECISION_SCHEMA = "PK_MESH_DECISION/1"
OP_CLASS = {
    "status": "status", "reconcile": "data", "route.read": "read", "route.migrate": "mutate",
    "identity": "data", "bypass": "data", "bypass.read": "read", "config.validate": "config",
    "config.activate": "config", "config.rollback": "config", "audit.read": "read", "audit.export": "read",
    "control.freeze": "control", "control.quarantine": "control", "control.break_glass": "control",
    "state.restore": "control", "artifact.verify": "read",
}
DEPENDENCIES = ("identity", "policy", "key", "time", "attestation", "telemetry", "audit_sink")


@dataclass(frozen=True)
class ReleaseLineage:
    artifact_version: str = __version__
    source_digest: str = "unknown"
    build_id: str = "local"


class MeshLayerService:
    def __init__(self, *, resolver: SecretResolver, node: str = "node-0", site: str = "site-0",
                 clock: Callable[[], float] = time.time, lineage: ReleaseLineage = ReleaseLineage(),
                 log_sink: Callable[[str], None] | None = None, max_journal: int = 5_000,
                 max_idempotency: int = 10_000):
        self.resolver, self.node, self.site, self.clock, self.lineage = resolver, node, site, clock, lineage
        self.config = ConfigStore(clock=clock)
        self.lifecycle = Lifecycle(on_transition=self._on_transition)
        self.metrics = Metrics()
        self.fencing = FencingGuard()
        self.controls = ControlSwitches()
        self._deps = {d: True for d in DEPENDENCIES}
        self._breakers = {d: CircuitBreaker(clock=clock) for d in DEPENDENCIES}
        self._registries: dict[str, RoutePolicyRegistry] = {}
        self._detectors: dict[str, BypassDetector] = {}
        self._journal: dict[str, list] = {}
        self._max_journal = max_journal
        self._idem: OrderedDict[tuple, tuple[str, dict]] = OrderedDict()
        self._max_idem = max_idempotency
        self._lock = RLock()
        self._log_sink = log_sink
        self.audit: AuditLog | None = None
        self.log: StructuredLogger | None = None
        self._authn: Authenticator | None = None
        self._authz: Authorizer | None = None
        self._admission: AdmissionController | None = None
        self._cfg: dict | None = None
        self._last_progress = clock()
        self._ops_ok = 0
        self._ops_err = 0
        self._pending_transitions: list = []

    # ------------------------------------------------------------ bootstrap
    def bootstrap(self, doc: Mapping, *, author: str, source: str) -> Provenance:
        """Empty environment -> ready (MC-010).  Fails closed on any error."""
        self.lifecycle.to("bootstrapping", "bootstrap requested")
        try:
            prov = self.config.activate(doc, author=author, source=source, reason="bootstrap")
            self._apply(self.config.active()[0])
        except (ConfigError, SecretResolutionError, MeshError) as exc:
            self.lifecycle.to("failed", f"bootstrap failed: {type(exc).__name__}")
            raise
        self.lifecycle.to("ready", "bootstrap complete")
        self._audit("config.activated", None, None, prov.digest, "ALLOW", "bootstrap", attrs=prov.as_dict())
        return prov

    def _apply(self, cfg: dict) -> None:
        """Resolve secrets and (re)build runtime objects from a validated config."""
        try:
            audit_key = self.resolver.resolve(cfg["audit_key_ref"]).reveal()
            token_ref = cfg["token_key_ref"]
            art_ref = cfg["artifact_key_ref"]
            self.resolver.resolve(token_ref)
            self.resolver.resolve(art_ref)
        except SecretResolutionError:
            self._deps["key"] = False
            raise
        pol = cfg["policy"]
        policy = CapabilityPolicy(pol["version"], {k: frozenset(v) for k, v in pol["roles"].items()},
                                  issued_at=self.clock(), max_age_s=pol["max_age_s"])
        bindings = {rid: (b["actor_type"], frozenset(b.get("roles", [])), frozenset(b.get("tenants", [])))
                    for rid, b in cfg["spiffe_bindings"].items()}

        def token_key() -> bytes:
            if not self._deps["key"]:
                raise SecretResolutionError("key service unavailable")
            return self.resolver.resolve(token_ref).reveal()

        lim = cfg["limits"]
        with self._lock:
            old_audit = self.audit
            if old_audit is None:
                self.audit = AuditLog(audit_key, clock=self.clock)
            self.log = StructuredLogger(self.node, Pseudonymizer(hashlib.sha256(b"pseudo" + audit_key).digest()),
                                        sink=self._log_sink, clock=self.clock,
                                        redact_hc=cfg["telemetry"]["redact_high_cardinality"])
            self.metrics._max = lim["max_label_cardinality"]
            self._authn = Authenticator(trust_domain=cfg["trust_domain"], token_key=token_key,
                                        spiffe_bindings=bindings, clock=self.clock)
            if self._authz is None:
                self._authz = Authorizer(policy, clock=self.clock)
            else:
                self._authz.replace_policy(policy)
            adm = cfg["admission"]
            if self._admission is None:
                self._admission = AdmissionController(adm["rate_per_s"], adm["burst"], lim["max_inflight"],
                                                      adm["tenant_share"], clock=time.monotonic)
            else:
                self._admission.reconfigure(adm["rate_per_s"], adm["burst"], lim["max_inflight"], adm["tenant_share"])
            br = cfg["breaker"]
            for d in DEPENDENCIES:
                self._breakers[d] = CircuitBreaker(br["failure_threshold"], br["reset_timeout_s"], br["half_open_max"])
            self._verifier = Verifier(hmac_check(lambda: self.resolver.resolve(art_ref).reveal()))
            self._cfg = cfg
            # Re-key tenant state: tenants removed from config keep their data
            # (reconstructable) but become unreachable until re-declared.
            for t in cfg["tenants"]:
                if t not in self._registries:
                    self._registries[t] = RoutePolicyRegistry(max_routes=lim["max_routes_per_tenant"])
                if t not in self._detectors or self._detectors[t].meshed != frozenset(cfg["meshed_destinations"]):
                    self._detectors[t] = BypassDetector(set(cfg["meshed_destinations"]), max_flags=lim["max_flags"],
                                                        max_destinations=lim["max_destinations"])
                self._journal.setdefault(t, [])

    # ------------------------------------------------------------- plumbing
    def _on_transition(self, old: str, new: str, reason: str) -> None:
        if self.audit is not None:
            self._audit("lifecycle.transition", None, None, f"{old}->{new}", "INFO", reason)

    def _audit(self, etype, actor, tenant, target, decision, reason, corr=None, attrs=None):
        if self.audit is None:
            return
        if not self._deps["audit_sink"]:
            # audit_sink is fail_closed: security operations cannot proceed unaudited
            raise MeshError("E_DEPENDENCY_UNAVAILABLE", "audit sink unavailable; failing closed")
        pv = self._authz.policy.version if self._authz else None
        self.audit.emit(etype, actor=actor, tenant=tenant, target=target, decision=decision, reason=reason,
                        correlation_id=corr, policy_version=pv, attrs=attrs)

    def _principal(self, credential: Mapping | None) -> Principal | str:
        if not isinstance(credential, Mapping):
            return "DENY_UNAUTHENTICATED"
        if not self._deps["identity"]:
            return "DENY_TRUST_UNAVAILABLE"
        if not self._deps["time"]:
            return "DENY_TRUST_UNAVAILABLE"
        if "san" in credential and "token" not in credential:
            return self._authn.from_spiffe(credential["san"])
        if "token" in credential and "san" not in credential:
            return self._authn.from_token(credential["token"])
        return "DENY_UNAUTHENTICATED"

    def _guard(self, credential, operation: str, tenant: str | None, trace_header: str | None,
               *, route_key: str | None = None):
        """Returns (principal, trace, correlation_id, admitted_tenant)."""
        if self._authz is None:
            raise MeshError("E_NOT_READY", "component not bootstrapped")
        trace = TraceContext.parse(trace_header)
        trace = trace.child() if trace else TraceContext.new()
        corr = trace.trace_id
        principal = self._principal(credential)
        if not self._deps["policy"]:
            principal = "DENY_TRUST_UNAVAILABLE"
        decision = self._authz.authorize(principal, operation, tenant)
        actor = principal.subject if isinstance(principal, Principal) else None
        self.metrics.inc("inv58_authz_decisions_total", operation=operation, code=decision.code)
        if not decision.allowed or decision.capability in ("route.migrate", "config.activate", "config.rollback",
                                                           "control.freeze", "control.quarantine",
                                                           "control.break_glass", "state.restore", "audit.export"):
            self._audit("authz.decision", actor, tenant, operation, decision.code,
                        "privileged" if decision.allowed else "denied", corr, attrs={"capability": decision.capability})
        if not decision.allowed:
            code = {"DENY_TENANT_SCOPE": "E_TENANT_SCOPE", "DENY_TRUST_UNAVAILABLE": "E_DEPENDENCY_UNAVAILABLE"}.get(
                decision.code, "E_UNAUTHENTICATED" if decision.code in (
                    "DENY_UNAUTHENTICATED", "DENY_EXPIRED", "DENY_NOT_YET_VALID", "DENY_REPLAY", "DENY_BAD_SIGNATURE",
                    "DENY_AUDIENCE", "DENY_AMBIGUOUS_IDENTITY") else "E_PERMISSION_DENIED")
            self.metrics.inc("inv58_errors_total", operation=operation, code=code)
            self.log.log("warn", "authz.denied", operation=operation, tenant=tenant, trace=trace, correlation_id=corr,
                         actor=actor, decision=decision.code)
            raise MeshError(code, "request denied", {"decision": decision.code}, corr)
        if tenant is not None and tenant not in self._registries:
            # checked only after authentication so unauthenticated callers cannot probe tenant existence
            self.metrics.inc("inv58_errors_total", operation=operation, code="E_TENANT_SCOPE")
            self._audit("authz.decision", actor, tenant, operation, "DENY_TENANT_SCOPE", "undeclared tenant", corr)
            raise MeshError("E_TENANT_SCOPE", "request denied", {"decision": "DENY_TENANT_SCOPE"}, corr)
        op_class = OP_CLASS[operation]
        if op_class == "mutate" and self.controls.frozen:
            raise MeshError("E_FROZEN", "component frozen", correlation_id=corr)
        if not self.lifecycle.accepts(op_class):
            raise MeshError("E_NOT_READY", f"lifecycle state {self.lifecycle.state} rejects {op_class}", correlation_id=corr)
        if op_class in ("mutate", "data") and tenant and self.controls.is_quarantined(f"tenant:{tenant}", f"route:{tenant}/{route_key}"):
            raise MeshError("E_FROZEN", "tenant or route quarantined", correlation_id=corr)
        return principal, trace, corr

    def _admit(self, tenant: str, operation: str, corr: str):
        if not self._admission.try_acquire(tenant):
            self.metrics.inc("inv58_admission_shed_total", tenant=tenant)
            raise MeshError("E_OVERLOADED", "load shed", correlation_id=corr)

    def _done(self, tenant, operation, t0, ok: bool, code: str = "OK"):
        with self._lock:
            self._last_progress = self.clock()
            if ok:
                self._ops_ok += 1
            else:
                self._ops_err += 1
        self.metrics.inc("inv58_requests_total", operation=operation, tenant=tenant or "-", outcome="ok" if ok else code)
        self.metrics.observe("inv58_latency_seconds", max(0.0, time.perf_counter() - t0), operation=operation)
        self.metrics.set("inv58_inflight", self._admission._inflight)
        self.metrics.set("inv58_saturation_ratio", self._admission.saturation())

    def _journal_add(self, tenant: str, entry: dict) -> None:
        with self._lock:
            j = self._journal.setdefault(tenant, [])
            j.append(entry)
            del j[:-self._max_journal]

    def _decision_record(self, tenant, operation, inputs, output, reason, corr, principal) -> dict:
        prov = self.config.provenance()  # no deep copy per decision (OPT-2: cost grew with tenant count)
        cfg = (None, prov) if prov else None
        return {
            "schema": DECISION_SCHEMA, "ts": self.clock(), "tenant": tenant, "operation": operation,
            "inputs": inputs, "output": output, "reason": reason, "correlation_id": corr,
            "actor_type": principal.actor_type if isinstance(principal, Principal) else None,
            "policy_version": self._authz.policy.version, "config_digest": cfg[1].digest if cfg else None,
            "config_version": cfg[1].version if cfg else None,
            "constraints": {"max_budget": self._cfg["max_budget"], "default_budget": self._cfg["default_budget"]},
            "topology": {"node": self.node, "site": self.site},
            "release": {"artifact_version": self.lineage.artifact_version, "source_digest": self.lineage.source_digest,
                        "build_id": self.lineage.build_id},
        }

    @staticmethod
    def _negotiate(interface: str, requested: str | None) -> str:
        supported = INTERFACE_VERSIONS[interface]
        if requested is None:
            return supported[-1]
        if requested not in supported:
            raise MeshError("E_UNSUPPORTED_VERSION", "unsupported interface version",
                            {"requested": requested, "supported": ",".join(supported)})
        return requested

    def _budget(self, budget: int | None) -> int:
        b = self._cfg["default_budget"] if budget is None else budget
        if isinstance(b, bool) or not isinstance(b, int) or b < 1:
            raise MeshError("E_INVALID_ARGUMENT", "budget must be a positive integer")
        if b > self._cfg["max_budget"]:
            raise MeshError("E_BUDGET_EXCEEDED", "budget exceeds configured max_budget",
                            {"budget": b, "max_budget": self._cfg["max_budget"]})
        return b

    def _payload_ok(self, *values) -> None:
        size = sum(len(str(v)) for v in values)
        if size > self._cfg["limits"]["max_payload_bytes"]:
            raise MeshError("E_PAYLOAD_TOO_LARGE", "payload exceeds max_payload_bytes")

    # ---------------------------------------------------------- data plane
    def reconcile(self, credential, tenant: str, route: str, app_attempts: int, mesh_attempts: int,
                  budget: int | None = None, *, version: str | None = None, traceparent: str | None = None) -> dict:
        principal, trace, corr = self._guard(credential, "reconcile", tenant, traceparent, route_key=route)
        self._negotiate("reconcile", version)
        self._payload_ok(route)
        self._admit(tenant, "reconcile", corr)
        t0 = time.perf_counter()
        try:
            try:
                out = reconcile(route, app_attempts, mesh_attempts, self._budget(budget))
            except ValueError as exc:
                raise MeshError("E_INVALID_ARGUMENT", str(exc), correlation_id=corr) from None
            self.metrics.observe("inv58_effective_attempts", out["effective_attempts"], tenant=tenant)
            self._journal_add(tenant, self._decision_record(tenant, "reconcile",
                              {"route": route, "app": app_attempts, "mesh": mesh_attempts, "budget": budget},
                              out, out["reason"], corr, principal))
            self._done(tenant, "reconcile", t0, True)
            return out
        except MeshError as e:
            self._done(tenant, "reconcile", t0, False, e.code)
            raise
        finally:
            self._admission.release(tenant)

    def migrate_route(self, credential, tenant: str, route: str, app_attempts: int, mesh_attempts: int,
                      budget: int | None = None, *, fence: int, idempotency_key: str,
                      traceparent: str | None = None) -> dict:
        principal, trace, corr = self._guard(credential, "route.migrate", tenant, traceparent, route_key=route)
        self._payload_ok(route, idempotency_key)
        if not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key) <= 128:
            raise MeshError("E_INVALID_ARGUMENT", "idempotency_key must be 8..128 chars", correlation_id=corr)
        request = {"route": route, "app": app_attempts, "mesh": mesh_attempts, "budget": budget}
        req_digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        ikey = (tenant, idempotency_key)
        with self._lock:
            if ikey in self._idem:
                prior_digest, prior = self._idem[ikey]
                if prior_digest != req_digest:
                    raise MeshError("E_CONFLICT", "idempotency key reused with different request", correlation_id=corr)
                if prior is None:  # same request still executing on another thread
                    raise MeshError("E_CONFLICT", "idempotent request already in progress", correlation_id=corr)
                return dict(prior, replayed=True)
            # reserve the key before executing (race found by test_idempotency_key_race_executes_once)
            self._idem[ikey] = (req_digest, None)
        committed = False
        try:
            self._admit(tenant, "route.migrate", corr)
        except MeshError:
            with self._lock:
                self._idem.pop(ikey, None)
            raise
        t0 = time.perf_counter()
        try:
            try:
                self.fencing.check_and_advance(f"route:{tenant}", fence)
            except MeshError as e:
                self._audit("fence.rejected", principal.subject, tenant, route, "DENY", "stale fencing token", corr)
                raise MeshError(e.code, e.message, e.details, corr) from None
            try:
                out = self._registries[tenant].migrate_route(route, app_attempts, mesh_attempts, self._budget(budget))
            except OverflowError:
                raise MeshError("E_CAPACITY", "tenant route capacity reached", correlation_id=corr) from None
            except ValueError as exc:
                self._audit("route.rejected", principal.subject, tenant, route, "DENY", str(exc)[:128], corr)
                raise MeshError("E_INVALID_ARGUMENT", str(exc), correlation_id=corr) from None
            out = dict(out, tenant=tenant, fence=fence)
            with self._lock:
                self._idem[ikey] = (req_digest, out)
                committed = True
                while len(self._idem) > self._max_idem:
                    k, (_, v) = next(iter(self._idem.items()))
                    if v is None:
                        break  # never evict an in-progress reservation
                    self._idem.popitem(last=False)
            self._audit("route.migrated", principal.subject, tenant, route, "ALLOW", out["reason"], corr,
                        attrs={"revision": out["revision"], "owner": out["owner"], "fence": fence})
            self._journal_add(tenant, self._decision_record(tenant, "route.migrate", request, out, out["reason"], corr, principal))
            self.metrics.set("inv58_route_registry_size", len(self._registries[tenant].snapshot()[1]), tenant=tenant)
            self._done(tenant, "route.migrate", t0, True)
            return out
        except MeshError as e:
            self._done(tenant, "route.migrate", t0, False, e.code)
            raise
        finally:
            if not committed:
                with self._lock:
                    if self._idem.get(ikey, (None, 0))[1] is None:
                        self._idem.pop(ikey, None)
            self._admission.release(tenant)

    def get_route(self, credential, tenant: str, route: str, *, traceparent: str | None = None) -> dict | None:
        self._guard(credential, "route.read", tenant, traceparent)
        try:
            return self._registries[tenant].get(route)
        except ValueError as exc:
            raise MeshError("E_INVALID_ARGUMENT", str(exc)) from None

    def map_identity(self, credential, tenant: str, san: str, *, version: str | None = None,
                     traceparent: str | None = None) -> dict:
        principal, trace, corr = self._guard(credential, "identity", tenant, traceparent)
        self._negotiate("identity", version)
        self._payload_ok(san)
        t0 = time.perf_counter()
        self._admit(tenant, "identity", corr)
        try:
            try:
                runtime = map_identity(san, self._cfg["trust_domain"])
            except Unmappable as exc:
                self.metrics.inc("inv58_identity_unmapped_total", reason="unmappable")
                self._audit("identity.rejected", principal.subject, tenant, None, "DENY", str(exc)[:128], corr)
                raise MeshError("E_IDENTITY_UNMAPPABLE", "identity cannot be mapped", correlation_id=corr) from None
            segs = runtime[len("runtime:"):].split("/")
            owner = segs[1] if len(segs) >= 2 and segs[0] == "ns" else None
            if owner != tenant:
                self.metrics.inc("inv58_identity_unmapped_total", reason="tenant_mismatch")
                self._audit("identity.rejected", principal.subject, tenant, None, "DENY", "identity belongs to another tenant", corr)
                raise MeshError("E_TENANT_SCOPE", "identity outside requested tenant", correlation_id=corr)
            out = {"san": san, "trust_domain": self._cfg["trust_domain"], "runtime_identity": runtime}
            self._done(tenant, "identity", t0, True)
            return out
        except MeshError as e:
            self._done(tenant, "identity", t0, False, e.code)
            raise
        finally:
            self._admission.release(tenant)

    def report_flow(self, credential, tenant: str, src: str, dst: str, mtls: bool, *,
                    version: str | None = None, traceparent: str | None = None) -> dict:
        principal, trace, corr = self._guard(credential, "bypass", tenant, traceparent)
        self._negotiate("bypass", version)
        self._payload_ok(src, dst)
        self._admit(tenant, "bypass", corr)
        t0 = time.perf_counter()
        try:
            try:
                flagged = self._detectors[tenant].observe(src, dst, mtls)
            except ValueError as exc:
                raise MeshError("E_INVALID_ARGUMENT", str(exc), correlation_id=corr) from None
            if flagged:
                self.metrics.inc("inv58_bypass_flows_total", tenant=tenant)
                self._audit("bypass.detected", principal.subject, tenant, dst, "FLAG", "plaintext to meshed destination",
                            corr, attrs={"src_pseudonym": self.log._pseudo(src)})
                self.log.log("warn", "bypass.detected", operation="bypass", tenant=tenant, trace=trace,
                             correlation_id=corr, src=src, dst=dst)
            self.metrics.set("inv58_bypass_backlog", sum(len(d.snapshot()) for d in self._detectors.values()))
            self._done(tenant, "bypass", t0, True)
            return {"src": src, "dst": dst, "mtls": mtls, "bypass": flagged}
        except MeshError as e:
            self._done(tenant, "bypass", t0, False, e.code)
            raise
        finally:
            self._admission.release(tenant)

    def bypass_evidence(self, credential, tenant: str, *, traceparent: str | None = None) -> tuple:
        self._guard(credential, "bypass.read", tenant, traceparent)
        return self._detectors[tenant].snapshot()

    # ------------------------------------------------------- control plane
    def activate_config(self, credential, doc: Mapping, *, expected_digest: str | None = None,
                        traceparent: str | None = None) -> dict:
        principal, trace, corr = self._guard(credential, "config.activate", None, traceparent)
        try:
            prov = self.config.activate(doc, author=principal.subject, source="api", expected_digest=expected_digest,
                                        health_probe=self._probe_config)
        except ConfigError as exc:
            self.metrics.inc("inv58_config_activations_total", result="rejected")
            self._audit("config.rejected", principal.subject, None, None, "DENY", "; ".join(exc.problems)[:400], corr)
            raise MeshError("E_CONFIG_INVALID", "configuration rejected",
                            {"problems": "; ".join(exc.problems)[:240]}, corr) from None
        self._apply(self.config.active()[0])
        self.metrics.inc("inv58_config_activations_total", result="activated")
        self._audit("config.activated", principal.subject, None, prov.digest, "ALLOW", "activated", corr, attrs=prov.as_dict())
        return prov.as_dict()

    def validate_config(self, credential, doc: Mapping) -> dict:
        principal, trace, corr = self._guard(credential, "config.validate", None, None)
        try:
            v = validate(doc)
        except ConfigError as exc:
            return {"valid": False, "problems": exc.problems}
        from .config import digest
        return {"valid": True, "digest": digest(v)}

    def _probe_config(self, cfg: dict) -> bool:
        try:
            for ref in ("audit_key_ref", "token_key_ref", "artifact_key_ref"):
                self.resolver.resolve(cfg[ref])
            return True
        except SecretResolutionError:
            return False

    def rollback_config(self, credential, *, to_digest: str | None = None) -> dict:
        principal, trace, corr = self._guard(credential, "config.rollback", None, None)
        try:
            prov = self.config.rollback(author=principal.subject, to_digest=to_digest)
        except ConfigError as exc:
            raise MeshError("E_CONFLICT", "; ".join(exc.problems), correlation_id=corr) from None
        self._apply(self.config.active()[0])
        self._audit("config.rolled_back", principal.subject, None, prov.digest, "ALLOW", "operator rollback", corr, attrs=prov.as_dict())
        return prov.as_dict()

    def freeze(self, credential, on: bool, *, reason: str) -> dict:
        principal, _, corr = self._guard(credential, "control.freeze", None, None)
        self.controls.freeze(on)
        self._audit("control.freeze" if on else "control.unfreeze", principal.subject, None, "component", "ALLOW", reason[:200], corr)
        if on and self.lifecycle.state in ("ready", "degraded"):
            self.lifecycle.to("frozen", reason[:200])
        elif not on and self.lifecycle.state == "frozen":
            self.lifecycle.to("ready", reason[:200])
        return self.controls.snapshot()

    def quarantine(self, credential, tenant: str, *, route: str | None = None, on: bool = True, reason: str) -> dict:
        principal, _, corr = self._guard(credential, "control.quarantine", tenant, None)
        key = f"route:{tenant}/{route}" if route else f"tenant:{tenant}"
        self.controls.quarantine(key, on)
        self._audit("control.quarantine", principal.subject, tenant, key, "ALLOW", f"{'on' if on else 'off'}: {reason[:180]}", corr)
        return self.controls.snapshot()

    def arm_break_glass(self, credential, *, seconds: float, reason: str) -> dict:
        """First person of the two-person rule: an operator holding control.freeze arms a
        window (<= 1 h).  The armer can never be the one who invokes break-glass."""
        principal, _, corr = self._guard(credential, "control.freeze", None, None)
        self._authz.arm_break_glass(seconds)
        self._bg_armed_by = principal.subject
        self._audit("control.break_glass", principal.subject, None, "arm", "ARMED", reason[:200], corr,
                    attrs={"seconds": seconds})
        return {"armed_by": principal.subject, "seconds": seconds}

    def break_glass(self, credential, *, reason: str) -> dict:
        """Emergency disable: freezes mutations.  Requires a window armed by a *different*
        operator (two-person rule, RR-07)."""
        principal, _, corr = self._guard(credential, "control.break_glass", None, None)
        if getattr(self, "_bg_armed_by", None) in (None, principal.subject):
            self._audit("control.break_glass", principal.subject, None, "component", "DENY", "two-person rule", corr)
            raise MeshError("E_PERMISSION_DENIED", "break-glass must be armed by a different operator",
                            {"decision": "DENY_TWO_PERSON_RULE"}, corr)
        self.controls.freeze(True)
        if self.lifecycle.state in ("ready", "degraded"):
            self.lifecycle.to("frozen", "break-glass")
        self._audit("control.break_glass", principal.subject, None, "component", "ALLOW", reason[:200], corr)
        return self.controls.snapshot()

    def verify_artifact(self, credential, manifest: Mapping, data: bytes, approved: Mapping[str, frozenset]) -> dict:
        principal, _, corr = self._guard(credential, "artifact.verify", None, None)
        v = Verifier(self._verifier.signature_check, approved)
        try:
            return v.verify(manifest, data)
        except MeshError as e:
            self._audit("integrity.failure", principal.subject, None, str(manifest.get("name", "?"))[:64], "DENY", e.message, corr)
            raise

    # -------------------------------------------------- dependency handling
    def set_dependency(self, name: str, available: bool) -> None:
        """Probe hook: record a trust/noncritical dependency's availability."""
        if name not in DEPENDENCIES:
            raise ValueError(name)
        self._deps[name] = bool(available)
        self._breakers[name].record(bool(available))
        self.metrics.set("inv58_breaker_state", {"closed": 0, "half_open": 1, "open": 2}[self._breakers[name].state], dependency=name)
        policy = self._cfg["trust_outage_policy"].get(name, "fail_closed") if self._cfg else "fail_closed"
        st = self.lifecycle.state
        if not available and policy == "fail_safe_degraded" and st == "ready":
            self.lifecycle.to("degraded", f"{name} unavailable")
        elif available and st == "degraded" and all(self._deps.values()):
            self.lifecycle.to("ready", f"{name} recovered")

    # ------------------------------------------------------- health/status
    def health(self) -> dict:
        """Liveness + stall detection (MC-017, MC-024).  Unauthenticated-safe: no tenant data."""
        cfg = self._cfg or {"health": {"stall_after_s": 30.0, "max_error_ratio": 0.5, "min_samples": 20}}
        with self._lock:
            idle = self.clock() - self._last_progress
            total = self._ops_ok + self._ops_err
            ratio = self._ops_err / total if total else 0.0
        inflight = self._admission._inflight if self._admission else 0
        stalled = inflight > 0 and idle > cfg["health"]["stall_after_s"]
        error_burst = total >= cfg["health"]["min_samples"] and ratio > cfg["health"]["max_error_ratio"]
        state = self.lifecycle.state
        live = state not in ("failed", "stopped") and not stalled
        return {"live": live, "stalled": stalled, "error_ratio": round(ratio, 4), "error_burst": error_burst,
                "state": state}

    def readiness(self) -> dict:
        h = self.health()
        critical_down = [d for d in DEPENDENCIES if not self._deps[d]
                         and (self._cfg or {}).get("trust_outage_policy", {}).get(d, "fail_closed") == "fail_closed"]
        ready = h["live"] and self.lifecycle.state in ("ready", "degraded") and not critical_down
        return {"ready": ready, "state": self.lifecycle.state, "critical_dependencies_down": critical_down}

    def status(self, credential=None) -> dict:
        self._guard(credential, "status", None, None)
        cfg = self.config.active()
        return redact({
            "schema": STATUS_SCHEMA, "component": "INV-58", "version": __version__,
            "release": self.lineage.__dict__, "node": self.node, "site": self.site,
            "health": self.health(), "readiness": self.readiness(),
            "config": {"digest": cfg[1].digest, "version": cfg[1].version, "activated_at": cfg[1].activated_at,
                       "author": cfg[1].author} if cfg else None,
            "policy_version": self._authz.policy.version if self._authz else None,
            "dependencies": {d: {"available": self._deps[d], "breaker": self._breakers[d].state} for d in DEPENDENCIES},
            "capabilities": {"interfaces": {k: list(v) for k, v in INTERFACE_VERSIONS.items()},
                             "operations": sorted(OP_CLASS)},
            "controls": {"frozen": self.controls.frozen, "quarantined_count": len(self.controls.snapshot()["quarantined"])},
            "tenants": len(self._registries),
            "audit": {"records": len(self.audit.records()) if self.audit else 0,
                      "head": self.audit.head if self.audit else None},
        })

    def explain(self, credential, tenant: str, route: str | None = None, limit: int = 20) -> list[dict]:
        """Operator explain view (MC-026): decisions with inputs, policy, config, topology, release."""
        self._guard(credential, "route.read", tenant, None)
        limit = max(1, min(int(limit), 200))
        with self._lock:
            entries = [e for e in self._journal.get(tenant, []) if route is None or e["inputs"].get("route") == route]
        return copy.deepcopy(entries[-limit:])

    def audit_export(self, credential) -> dict:
        principal, _, corr = self._guard(credential, "audit.export", None, None)
        ok, why = self.audit.verify()
        return {"verified": ok, "reason": why, "anchor": self.audit.anchor(), "head": self.audit.head,
                "records": list(self.audit.records())}

    # ------------------------------------------------- snapshot / restore
    def snapshot(self) -> dict:
        """Reconstructable state (MC-037): route registries, fencing, controls. Sealed."""
        with self._lock:
            body = {
                "schema": SNAPSHOT_SCHEMA, "taken_at": self.clock(), "version": __version__,
                "config_digest": self.config.active()[1].digest if self.config.active() else None,
                "routes": {t: r.snapshot()[1] for t, r in self._registries.items()},
                "revisions": {t: r.snapshot()[0] for t, r in self._registries.items()},
                "fencing": self.fencing.snapshot(), "controls": self.controls.snapshot(),
            }
        raw = json.dumps(body, sort_keys=True).encode()
        key = self.resolver.resolve(self._cfg["audit_key_ref"]).reveal()
        return {"body": body, "seal": hmac.new(key, raw, hashlib.sha256).hexdigest()}

    def restore(self, credential, snap: Mapping) -> dict:
        principal, _, corr = self._guard(credential, "state.restore", None, None)
        body = snap.get("body") if isinstance(snap, Mapping) else None
        if not isinstance(body, dict) or body.get("schema") != SNAPSHOT_SCHEMA:
            raise MeshError("E_INVALID_ARGUMENT", "not a PK_MESH_SNAPSHOT/1", correlation_id=corr)
        raw = json.dumps(body, sort_keys=True).encode()
        key = self.resolver.resolve(self._cfg["audit_key_ref"]).reveal()
        if not hmac.compare_digest(str(snap.get("seal")), hmac.new(key, raw, hashlib.sha256).hexdigest()):
            self._audit("integrity.failure", principal.subject, None, "snapshot", "DENY", "seal mismatch", corr)
            raise MeshError("E_INTEGRITY", "snapshot seal mismatch", correlation_id=corr)
        restored = 0
        new_regs: dict[str, RoutePolicyRegistry] = {}
        with self._lock:
            for tenant, routes in body["routes"].items():
                if tenant not in self._registries:
                    continue  # never resurrect an undeclared tenant
                reg = RoutePolicyRegistry(max_routes=self._cfg["limits"]["max_routes_per_tenant"])
                policies = {}
                for route, pol in sorted(routes.items()):
                    check = reconcile(route, pol["app"], pol["mesh"], pol["budget"])  # re-validates invariants
                    if (check["owner"], check["app"], check["mesh"]) != (pol["owner"], pol["app"], pol["mesh"]):
                        raise MeshError("E_INTEGRITY", "snapshot policy violates retry invariants", correlation_id=corr)
                    policies[route] = dict(pol)
                    restored += 1
                if len(policies) > reg.max_routes:
                    raise MeshError("E_CAPACITY", "snapshot exceeds tenant route capacity", correlation_id=corr)
                with reg._lock:
                    reg._policies = policies
                    reg._revision = int(body["revisions"].get(tenant, 0))
                new_regs[tenant] = reg
            self._registries.update(new_regs)  # all-or-nothing swap
            self.fencing.restore(body["fencing"])
            self.controls.freeze(body["controls"]["frozen"])
            for q in body["controls"]["quarantined"]:
                self.controls.quarantine(q, True)
        self._audit("state.restored", principal.subject, None, "snapshot", "ALLOW", f"{restored} routes", corr)
        return {"restored_routes": restored}
