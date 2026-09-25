"""SandboxController: the reference control plane that composes every primitive
(auth, admission, lifecycle, fencing, idempotency, egress binding, config
provenance, durable audit, telemetry, emergency controls, health).

It drives the in-memory ``sandbox.Session`` as its "guest" and a ``Plan`` +
``observe`` callback as its "host".  It is the executable specification of the
production control flow; the production node agent must reproduce these
semantics against real Firecracker processes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import threading
from typing import Callable, Iterable, Mapping

from ..sandbox import BASE_DIGEST, Session, new_session
from .audit_log import AuditStream
from .auth import TokenAuthority, authorize
from .config import digest_of
from .egress import EgressPolicy, enforce
from .errors import ControlError, map_exception
from .lifecycle import LeaseTable, Lifecycle, State, TeardownProof
from .resilience import AdmissionController, DependencyHealth, IdempotencyStore, Shape
from .runtime_plan import Plan, plan_session, reconcile
from .telemetry import ExplainLog, Metrics, classify

AUD = "inv71-controller"


@dataclass
class Managed:
    sid: str
    tenant: str
    shape: Shape
    lifecycle: Lifecycle
    epoch: int
    session: Session
    plan: Plan
    config_digest: str
    release: str


@dataclass
class Emergency:
    global_disable: bool = False
    tenants: set[str] = field(default_factory=set)
    quarantined_nodes: set[str] = field(default_factory=set)


class SandboxController:
    def __init__(self, *, node: str, site: str, auth: TokenAuthority, admission: AdmissionController,
                 egress: EgressPolicy, audit: AuditStream, config: Mapping, config_digest: str,
                 artifacts: Mapping[str, Mapping[str, str]], clock: Callable[[], float],
                 observe_host: Callable[[], Iterable[tuple[str, str]]], owner: str = "controller-a",
                 leases: LeaseTable | None = None, deps: DependencyHealth | None = None) -> None:
        self.node, self.site, self.owner = node, site, owner
        self.auth, self.admission, self.egress, self.audit = auth, admission, egress, audit
        self.config, self.config_digest, self.artifacts = dict(config), config_digest, artifacts
        self.clock, self.observe_host = clock, observe_host
        self.leases = leases or LeaseTable()
        self.deps = deps or DependencyHealth(clock)
        self.metrics, self.explain = Metrics(), ExplainLog()
        self.idem = IdempotencyStore(clock=clock)
        self.emergency = Emergency()
        self.sessions: dict[str, Managed] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------ helpers
    def _audit(self, actor, op, outcome, reason, *, tenant="", sid="", corr="") -> None:
        # Durable audit precedes acknowledgement; if the sink refuses, the action fails.
        self.audit.append(actor=actor, operation=op, outcome=outcome, reason=reason, tenant=tenant,
                          session=sid, correlation_id=corr, config_digest=self.config_digest,
                          policy_version=self.egress.version)

    def _reject(self, err: ControlError, *, op: str, actor: str, tenant="", sid="", corr="") -> ControlError:
        self.metrics.inc("heavybox_requests_total", operation=op, outcome=err.code.outcome.value)
        self.metrics.inc("heavybox_rejections_total", reason=err.code.code)
        self.explain.record(decision="deny", reason_code=err.code.code, operation=op, session=sid,
                            tenant_tier="silver", inputs={"config": self.config_digest,
                                                          "policy": self.egress.version, "class": classify(err.code.code)},
                            correlation_id=corr)
        try:
            self._audit(actor, op, "denied", err.code.code, tenant=tenant, sid=sid, corr=corr)
        except ControlError:
            pass  # the original rejection stands; audit outage is surfaced by health
        return err

    def _authn(self, token, action, tenant, op, corr, approver_token=None):
        try:
            claims = self.auth.verify(token, aud=AUD)
            approver = self.auth.verify(approver_token, aud=AUD) if approver_token else None
        except ControlError as e:
            raise self._reject(e, op=op, actor="anonymous", tenant=tenant, corr=corr)
        d = authorize(claims, action, tenant=tenant, site=self.site, approver=approver)
        if not d.allowed:
            code = "AUTHZ.TENANT_MISMATCH" if d.reason == "AUTHZ.TENANT_MISMATCH" else "AUTHZ.DENIED"
            raise self._reject(ControlError(code, d.reason), op=op, actor=claims.sub, tenant=tenant, corr=corr)
        return claims

    # ------------------------------------------------------------ operations
    def create(self, token: str, *, sid: str, tenant: str, shape: Shape, allow: Iterable[str] = (),
               idempotency_key: str, correlation_id: str = "", release: str = "") -> dict:
        op = "session.create"
        req_digest = digest_of({"sid": sid, "tenant": tenant, "shape": [shape.vcpu, shape.mem_mib],
                                "allow": sorted(allow), "release": release})
        claims = self._authn(token, op, tenant, op, correlation_id)
        with self._lock:
            prior = self.idem.get(f"{tenant}/{idempotency_key}", req_digest)
            if prior is not None:
                return prior
            if self.emergency.global_disable or tenant in self.emergency.tenants or self.node in self.emergency.quarantined_nodes:
                raise self._reject(ControlError("POLICY.EMERGENCY_DISABLED"), op=op, actor=claims.sub, tenant=tenant, sid=sid, corr=correlation_id)
            try:
                self.deps.gate_new_trust_decision()
            except ControlError as e:
                raise self._reject(e, op=op, actor=claims.sub, tenant=tenant, sid=sid, corr=correlation_id)
            if sid in self.sessions:
                raise self._reject(ControlError("VALIDATION.MALFORMED_REQUEST", "sid in use"), op=op, actor=claims.sub, tenant=tenant, sid=sid, corr=correlation_id)
            if shape.vcpu > self.config["session.vcpu"] or shape.mem_mib > self.config["session.mem_mib"]:
                raise self._reject(ControlError("CAPACITY.SESSION_LIMIT", "shape above ceiling"), op=op, actor=claims.sub, tenant=tenant, sid=sid, corr=correlation_id)
            lc = Lifecycle(sid, self.clock)
            lc.transition(State.VALIDATING, initiator="controller")
            try:
                self.admission.admit(tenant, shape)
            except ControlError as e:
                lc.transition(State.FAILED, initiator="controller")
                raise self._reject(e, op=op, actor=claims.sub, tenant=tenant, sid=sid, corr=correlation_id)
            try:
                lc.transition(State.ALLOCATING, initiator="controller")
                lease = self.leases.acquire(sid, self.owner)
                plan = plan_session(sid, self.config, self.artifacts)
                lc.transition(State.STARTING, initiator="node")
                sess = new_session(sid, allow)
                # READY postconditions: clean base digest, lease held, plan rendered.
                from ..sandbox import digest
                if digest(sess.fs) != BASE_DIGEST:
                    raise ControlError("HYPERVISOR.START_FAILED", "base digest")
                self.leases.check(sid, self.owner, lease.epoch)
                lc.transition(State.READY, initiator="node")
            except Exception as exc:
                self.admission.release(tenant, shape)
                err = map_exception(exc)
                if lc.state not in (State.FAILED,):
                    try:
                        lc.transition(State.FAILED, initiator="node")
                    except ControlError:
                        lc.transition(State.FAILED, initiator="watchdog")
                raise self._reject(err, op=op, actor=claims.sub, tenant=tenant, sid=sid, corr=correlation_id)
            m = Managed(sid, tenant, shape, lc, lease.epoch, sess, plan, self.config_digest, release)
            # Write ordering (C057-IMP-02): the durable audit record must exist before the
            # session is registered or acknowledged.  If the sink refuses, undo everything.
            try:
                self._audit(claims.sub, op, "allowed", "SESSION.READY", tenant=tenant, sid=sid, corr=correlation_id)
            except ControlError as e:
                sess.teardown()
                self.admission.release(tenant, shape)
                lc.transition(State.DRAINING, initiator="controller")
                lc.transition(State.STOPPING, initiator="controller")
                lc.transition(State.VERIFYING_TEARDOWN, initiator="node")
                lc.transition(State.CLOSED, initiator="node", proof=TeardownProof.from_reconciliation(
                    sid, sess.teardown(), reconcile([plan], self.observe_host(), closing=[sid])))
                self.metrics.inc("heavybox_requests_total", operation=op, outcome=e.code.outcome.value)
                raise
            self.sessions[sid] = m
            self.metrics.inc("heavybox_requests_total", operation=op, outcome="SUCCESS")
            self.explain.record(decision="allow", reason_code="SESSION.READY", operation=op, session=sid,
                                tenant_tier="silver", inputs={"config": self.config_digest, "base": BASE_DIGEST,
                                                              "epoch": str(lease.epoch), "release": release or "-"},
                                correlation_id=correlation_id)
            resp = {"schema": "PK_HEAVYBOX_SESSION/2", "sid": sid, "state": lc.state.value, "epoch": lease.epoch,
                    "base_digest": BASE_DIGEST, "config_digest": self.config_digest, "release": release}
            self.idem.put(f"{tenant}/{idempotency_key}", req_digest, resp)
            return resp

    def connect(self, token: str, *, sid: str, host: str, port: int, correlation_id: str = "") -> dict:
        op = "egress.decide"
        m = self._get(sid)
        claims = self._authn(token, "session.exec", m.tenant, op, correlation_id)
        if m.lifecycle.state not in (State.READY, State.RUNNING):
            raise self._reject(ControlError("LIFECYCLE.ILLEGAL_TRANSITION", m.lifecycle.state.value), op=op, actor=claims.sub, tenant=m.tenant, sid=sid, corr=correlation_id)
        try:
            cap = self.egress.decide(sid, host, port)
        except ControlError as e:
            self.metrics.inc("heavybox_egress_denied_total", reason=e.code.code)
            raise self._reject(e, op=op, actor=claims.sub, tenant=m.tenant, sid=sid, corr=correlation_id)
        enforce(cap, key=self.egress.key, sid=sid, address=cap.address, port=port, protocol="tcp", now=self.clock())
        if m.lifecycle.state is State.READY:
            m.lifecycle.transition(State.RUNNING, initiator="controller")
        self._audit(claims.sub, op, "allowed", "EGRESS.BOUND", tenant=m.tenant, sid=sid, corr=correlation_id)
        return {"sid": sid, "address": cap.address, "port": port, "policy_version": cap.policy_version}

    def teardown(self, token: str, *, sid: str, epoch: int, correlation_id: str = "") -> dict:
        op = "session.teardown"
        m = self._get(sid)
        claims = self._authn(token, op, m.tenant, op, correlation_id)
        with self._lock:
            if m.lifecycle.state is State.CLOSED:
                return self._closed_record(m)
            try:
                self.leases.check(sid, self.owner, epoch)
            except ControlError as e:
                raise self._reject(e, op=op, actor=claims.sub, tenant=m.tenant, sid=sid, corr=correlation_id)
            lc = m.lifecycle
            if lc.state in (State.READY, State.RUNNING):
                lc.transition(State.DRAINING, initiator="controller")
            if lc.state is State.DRAINING:
                lc.transition(State.STOPPING, initiator="controller")
            if lc.state is State.FROZEN:
                lc.transition(State.STOPPING, initiator="operator")
            lc.transition(State.VERIFYING_TEARDOWN, initiator="node")
            guest = m.session.teardown()
            rec = reconcile([m.plan], self.observe_host(), closing=[sid])
            proof = TeardownProof.from_reconciliation(sid, guest, rec)
            if proof.verified:
                lc.transition(State.CLOSED, initiator="node", proof=proof)
                self.admission.release(m.tenant, m.shape)
                self.metrics.inc("heavybox_teardowns_verified_total")
                self._audit(claims.sub, op, "allowed", "TEARDOWN.VERIFIED", tenant=m.tenant, sid=sid, corr=correlation_id)
                return self._closed_record(m)
            lc.transition(State.QUARANTINED, initiator="node")
            self.metrics.inc("heavybox_teardown_failures_total")
            self._audit(claims.sub, op, "failed", "TEARDOWN.VERIFICATION_FAILED", tenant=m.tenant, sid=sid, corr=correlation_id)
            raise ControlError("TEARDOWN.VERIFICATION_FAILED", f"leaked={len(rec.leaked)}")

    def compact(self, retention_s: float = 3600.0) -> int:
        """Evict CLOSED sessions older than the retention window and release their
        leases, so control-plane state is bounded under churn (C067).  The durable
        audit stream remains the long-term record."""
        now, n = self.clock(), 0
        with self._lock:
            for sid, m in list(self.sessions.items()):
                if m.lifecycle.state is State.CLOSED and now - m.lifecycle.entered_at >= retention_s:
                    self.leases.release(sid, self.owner, m.epoch)
                    del self.sessions[sid]
                    n += 1
        self.idem.sweep()
        self.auth.sweep()
        return n

    def _closed_record(self, m: Managed) -> dict:
        p = m.lifecycle.teardown_proof
        return {"schema": "PK_HEAVYBOX_TEARDOWN/2", "sid": m.sid, "verified": True, "state": "CLOSED",
                "base_digest": BASE_DIGEST, "audit_head": self.audit.head, "leaked": list(p.leaked) if p else [],
                "config_digest": m.config_digest}

    # ------------------------------------------------------------ emergency
    def emergency_disable(self, token: str, *, scope: str, target: str = "", reason: str, incident: str) -> None:
        claims = self._authn(token, "emergency.disable", "", "emergency.disable", incident)
        if not reason or not incident:
            raise ControlError("VALIDATION.MALFORMED_REQUEST", "reason and incident id required")
        if scope == "global":
            self.emergency.global_disable = True
        elif scope == "tenant":
            self.emergency.tenants.add(target)
        elif scope == "node":
            self.emergency.quarantined_nodes.add(target)
        else:
            raise ControlError("VALIDATION.MALFORMED_REQUEST", "scope")
        self._audit(claims.sub, "emergency.disable", "allowed", f"EMERGENCY.{scope.upper()}", corr=incident)

    def emergency_enable(self, token: str, approver_token: str, *, scope: str, target: str = "", incident: str) -> None:
        claims = self._authn(token, "emergency.enable", "", "emergency.enable", incident, approver_token=approver_token)
        if scope == "global":
            self.emergency.global_disable = False
        elif scope == "tenant":
            self.emergency.tenants.discard(target)
        elif scope == "node":
            self.emergency.quarantined_nodes.discard(target)
        self._audit(claims.sub, "emergency.enable", "allowed", f"EMERGENCY.{scope.upper()}.CLEARED", corr=incident)

    def freeze(self, token: str, *, sid: str, reason: str, incident: str) -> None:
        m = self._get(sid)
        claims = self._authn(token, "session.freeze", m.tenant, "session.freeze", incident)
        m.lifecycle.transition(State.FROZEN, initiator="operator")
        self._audit(claims.sub, "session.freeze", "allowed", "OPERATOR.FREEZE", tenant=m.tenant, sid=sid, corr=incident)

    # ------------------------------------------------------------ status
    def _get(self, sid: str) -> Managed:
        m = self.sessions.get(sid)
        if m is None:
            raise ControlError("VALIDATION.MALFORMED_REQUEST", "unknown session")
        return m

    def watchdog(self) -> list[str]:
        """Stall detection: fail overdue sessions and move FAILED to REAPING."""
        acted = []
        for m in list(self.sessions.values()):
            if m.lifecycle.overdue():
                st = m.lifecycle.state
                dst = State.QUARANTINED if st in (State.REAPING, State.VERIFYING_TEARDOWN) else State.FAILED
                m.lifecycle.transition(dst, initiator="watchdog")
                acted.append(f"{m.sid}:{st.value}->{dst.value}")
        return acted

    def status(self, *, privileged: bool) -> dict:
        counts: dict[str, int] = {}
        for m in self.sessions.values():
            counts[m.lifecycle.state.value] = counts.get(m.lifecycle.state.value, 0) + 1
        deg = self.deps.degraded()
        try:
            self.deps.gate_new_trust_decision()
            trust_ok = True
        except ControlError:
            trust_ok = False
        ready = (trust_ok and not self.emergency.global_disable and self.node not in self.emergency.quarantined_nodes)
        state = "QUARANTINED" if self.node in self.emergency.quarantined_nodes else (
            "NOT_READY" if not ready else ("DEGRADED" if deg else "READY"))
        out = {"schema": "PK_HEAVYBOX_STATUS/1", "live": True, "ready_for_new_sessions": ready, "state": state,
               "degraded_dependencies": deg, "config_digest": self.config_digest,
               "policy_version": self.egress.version, "api": "1.0",
               "audit": {"seq": self.audit.seq, "anchor_failures": self.audit.anchor_failures}}
        if privileged:
            out["sessions_by_state"] = counts
            out["owner"] = self.owner
        return out
