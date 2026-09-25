"""Wired INV-06 control plane: the one path through which a change reaches state.

Composes the package-local controls in the order fixed by
``governance/ARCHITECTURE.md`` so that no caller can skip authentication,
authorization, freeze/degraded checks, admission, policy, approval
signatures, leasing/fencing, provider execution, CAS commit or audit.  It
also emits the metric names used by ``ops/prometheus_rules.yml``.
"""
from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from typing import Any

from . import __version__
from .durable import FileStateBackend
from .execution import Provider, execute_plan
from .locking import FencedBackend, FileLeaseLock
from .observability import MetricsRegistry, StructuredLogger, TraceContext, explain_plan, health_status, lineage_record
from .policy import PolicyDenied, PolicyGate
from .resilience import AdmissionController, DegradedMode, FreezeController, IdempotencyStore, Watchdog
from .security import (
    AuthenticationFailed, Authorizer, SignedAuditLog, Signer, TokenAuthenticator, outage_decision, sign_plan, verify_signed_plan,
)
from .state import IacError


class PartialApply(IacError):
    code = "PK_IAC_PARTIAL_APPLY"


class ControlPlane:
    def __init__(self, *, tenant: str, backend: FileStateBackend, lock: FileLeaseLock, provider: Provider,
                 authenticator: TokenAuthenticator, authorizer: Authorizer, policy: PolicyGate, plan_signer: Signer,
                 audit: SignedAuditLog, logger: StructuredLogger | None = None, metrics: MetricsRegistry | None = None) -> None:
        self.tenant, self.backend, self.lock, self.provider = tenant, backend, lock, provider
        self.fenced = FencedBackend(backend, lock)
        self.authn, self.authz, self.policy, self.signer, self.audit = authenticator, authorizer, policy, plan_signer, audit
        self.log = logger or StructuredLogger()
        self.metrics = metrics or MetricsRegistry()
        self.freeze = FreezeController(lambda a, actor, d: self.audit.append(a, actor, d))
        self.degraded = DegradedMode(critical=["state", "policy", "identity", "audit"], noncritical=["telemetry"])
        self.admission = AdmissionController()
        self.idem = IdempotencyStore()
        self.watchdog = Watchdog()
        self.security_down: set[str] = set()

    # ------------------------------------------------------------ helpers
    def _principal(self, token: str, action: str):
        try:
            p = self.authn.authenticate(token)
        except AuthenticationFailed:
            self.metrics.inc("pk_iac_authn_failed_total", labels={"tenant": self.tenant})
            raise
        self.authz.check(p, action, tenant=self.tenant)
        return p

    def _err(self, exc: IacError, op: str) -> None:
        self.metrics.inc("pk_iac_errors_total", labels={"tenant": self.tenant, "operation": op, "code": exc.code})

    def _gauges(self) -> None:
        self.metrics.set("pk_iac_admission_queue_depth", self.admission.queue_depth, {"tenant": self.tenant})
        self.metrics.set("pk_iac_admission_shed_total", self.admission.shed, {"tenant": self.tenant})
        for dep in sorted(self.degraded.critical | self.degraded.noncritical):
            self.metrics.set("pk_iac_dependency_up", 0 if dep in self.degraded.down else 1, {"dependency": dep})

    # ------------------------------------------------------------ operations
    def plan(self, token: str, desired: Mapping[str, Any], *, trace: TraceContext | None = None) -> dict[str, Any]:
        trace = trace or TraceContext.new()
        outage_decision(self.security_down, "read")
        p = self._principal(token, "plan.create")
        with self.admission:
            state = self.backend.load_state()
            plan = state.plan(desired)
            try:
                decision = self.policy.check(plan, context={"tenant": self.tenant, "actor": p.subject})
            except PolicyDenied as exc:
                self.metrics.inc("pk_iac_policy_denied_total", labels={"tenant": self.tenant})
                self.audit.append("plan.denied", p.subject, {"plan_digest": plan["integrity"]["digest"], "reasons": exc.details.get("reasons")})
                raise
            self.audit.append("plan.created", p.subject, {"plan_digest": plan["integrity"]["digest"], "serial": plan["serial"]})
            self.log.log("INFO", "plan.created", tenant=self.tenant, operation="plan", trace=trace, serial=plan["serial"])
            self._gauges()
            return {"plan": plan, "planner": p.subject, "policy": decision,
                    "explain": explain_plan(plan, current=state.resources, desired=desired, policy_decision=decision)}

    def approve(self, token: str, plan: Mapping[str, Any], *, planner: str) -> dict[str, Any]:
        outage_decision(self.security_down, "mutate")
        p = self._principal(token, "plan.approve")
        Authorizer.separation_of_duties(planner, p.subject)
        signed = sign_plan(plan, self.signer, approver=p.subject)
        self.audit.append("plan.approved", p.subject, {"plan_digest": plan["integrity"]["digest"]})
        return signed

    def apply(self, token: str, signed_plan: Mapping[str, Any], *, desired: Mapping[str, Any], idempotency_key: str,
              release_id: str = "unreleased", trace: TraceContext | None = None) -> dict[str, Any]:
        trace = trace or TraceContext.new()
        outage_decision(self.security_down, "mutate")
        p = self._principal(token, "apply")
        self.freeze.check(self.tenant)
        self.degraded.require_mutation()
        plan = verify_signed_plan(signed_plan, self.signer)
        self.policy.check(plan, context={"tenant": self.tenant, "actor": p.subject})  # re-check at apply time
        digest = plan["integrity"]["digest"]

        def run() -> dict[str, Any]:
            op_id = uuid.uuid4().hex
            with self.admission, self.metrics.time("pk_iac_apply_seconds", {"tenant": self.tenant}):
                lease = self.lock.acquire(p.subject, ttl=300)
                self.watchdog.begin(op_id)
                try:
                    head = self.backend.head_serial()
                    state = self.backend.load_state()
                    current = state.resources
                    state.precheck(plan)  # stale/protected/mismatch refused BEFORE any provider call
                    result = execute_plan(plan, self.provider, desired=desired, current=current)
                    self.watchdog.progress(op_id)
                    if not result["complete"]:
                        drift = state.drift(self.provider.list())
                        self.audit.append("apply.partial", p.subject, {"plan_digest": digest, "done": result["done"], "drift": sorted(drift)})
                        exc = PartialApply("provider run incomplete; state not committed", details={"done": result["done"], "error": result["error"], "drift": sorted(drift)})
                        self._err(exc, "apply")
                        raise exc
                    serial = state.apply(plan)
                    self.fenced.commit(state.snapshot(), lease=lease, expected_serial=head,
                                       meta={"plan_digest": digest, "actor": p.subject, "approver": signed_plan["authorization"]["approver"]})
                    self.audit.append("apply.committed", p.subject, {"plan_digest": digest, "serial": serial})
                    self.metrics.inc("pk_iac_applies_total", labels={"tenant": self.tenant, "outcome": "ok"})
                    self.metrics.ingest_state_metrics(state.metrics(), self.tenant)
                    self.log.log("INFO", "apply.committed", tenant=self.tenant, operation="apply", trace=trace, serial=serial)
                    return {"serial": serial, "lineage": lineage_record(plan=plan, applied_serial=serial, release_id=release_id,
                                                                          artifact_versions={"inv06": __version__}, config_digest=hashlib.sha256(repr(sorted(desired)).encode()).hexdigest(), trace=trace)}
                finally:
                    self.watchdog.end(op_id)
                    self.lock.release(lease)
                    self._gauges()

        try:
            return self.idem.run(idempotency_key, digest, run)
        except IacError as exc:
            if not isinstance(exc, PartialApply):
                self._err(exc, "apply")
                self.audit.append("apply.refused", p.subject, {"plan_digest": digest, "code": exc.code})
            raise

    def health(self) -> dict[str, Any]:
        try:
            self.backend.load()
            ok = True
        except IacError:
            ok = False
        cur = self.lock.current()
        deps = {d: d not in self.degraded.down for d in self.degraded.critical | self.degraded.noncritical}
        return health_status(version=__version__, config_digest=None, dependencies=deps, critical=self.degraded.critical,
                             backend_ok=ok, lock_holder=cur.holder if cur else None, frozen=self.freeze.status(), watchdog=self.watchdog.status())
