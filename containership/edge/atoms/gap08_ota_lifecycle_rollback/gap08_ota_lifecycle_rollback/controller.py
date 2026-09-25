"""GAP-08 rollout controller — the integration of components 1-30.

Every mutating operation follows the same spine::

    authorize -> admission/rate -> dependency guard (fail closed) -> lease/fence
    -> freeze -> policy (window, topology, compatibility, artifact validity)
    -> write-ahead intent (CAS commit) -> fenced idempotent node commands
    -> authenticated acks -> CAS commit of outcome -> seal audit externally

so every node mutation is causally traceable:
authorized intent -> verified artifact -> policy/topology admission -> fenced
command -> authenticated ack -> observed state -> sealed audit record.

The pure state machine (``rollout.Rollout``) remains the single place where
rollout invariants are enforced; the controller never writes ``versions``
except through it (plus quarantine release, which is re-validated).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from . import deferred as dq
from .admission import AdmissionController
from .artifact import ArtifactVerifier, VerifiedArtifact
from .audit_sink import FileWormSink
from .authz import ApprovalLedger, Cap, Policy, Principal
from .common import Clock, SystemClock, new_id
from .compat import check as compat_check
from .conflicts import ConflictDetector, Scope
from .dependencies import DependencyHealth, OpClass
from .errors import (DependencyUnavailable, EvidenceRejected, IllegalTransition, IntegrityFailure,
                     StaleFence, ValidationFailed)
from .executor import CommandExecutor, Outcome
from .freeze import FreezeControl
from .health import GatePolicy, HealthGateAdapter
from .lease import Lease, LeaseService
from .rollout import Rollout, StateIntegrityError
from .store import StateStore
from .telemetry import Telemetry
from .topology import Inventory, TopologyEngine
from .windows import MaintenancePolicy

CONTROLLER_SCHEMA = "PK_CONTROLLER_STATE/1"
TERMINAL = frozenset({"complete", "rolled_back", "rollback_incomplete", "cancelled", "abandoned"})


@dataclass
class Controller:
    controller_id: str
    store: StateStore
    leases: LeaseService
    conflicts: ConflictDetector
    sink: FileWormSink
    health: HealthGateAdapter
    verifier: ArtifactVerifier
    executor: CommandExecutor
    topology: TopologyEngine
    inventory: Callable[[], Inventory]
    freeze: FreezeControl
    approvals: ApprovalLedger
    deps: DependencyHealth
    admission: AdmissionController = field(default_factory=AdmissionController)
    windows: MaintenancePolicy = field(default_factory=MaintenancePolicy)
    telemetry: Telemetry = field(default_factory=Telemetry)
    clock: Clock = field(default_factory=SystemClock)
    gate_policy: GatePolicy = field(default_factory=GatePolicy)
    lease_ttl_s: float = 30.0
    _leases: dict[str, Lease] = field(default_factory=dict)
    _lease_lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def policy(self) -> Policy:
        return self.approvals.policy

    # ------------------------------------------------------------------ internals
    def _lease(self, rollout_id: str) -> Lease:
        with self._lease_lock:
            return self._lease_locked(rollout_id)

    def _lease_locked(self, rollout_id: str) -> Lease:
        res = f"rollout/{rollout_id}"
        lease = self._leases.get(rollout_id)
        if lease is None:
            lease = self.leases.acquire(res, self.controller_id, self.lease_ttl_s)
        else:
            try:
                lease = self.leases.renew(lease, self.lease_ttl_s)
            except StaleFence:
                # Lease lapsed: re-acquire (mints a higher fence; raises Conflict if another
                # controller now holds it).  The old token is dead everywhere downstream.
                lease = self.leases.acquire(res, self.controller_id, self.lease_ttl_s)
        self._leases[rollout_id] = lease
        return lease

    def _load(self, rollout_id: str) -> tuple[dict[str, Any], Rollout, int]:
        rec = self.store.load(rollout_id)
        state = rec.state
        if state.get("schema") != CONTROLLER_SCHEMA:
            raise IntegrityFailure("unknown controller state schema", resource=rollout_id)
        try:
            core = Rollout.from_snapshot(state["core"])
        except StateIntegrityError as exc:
            self.telemetry.inc("gap08_state_restore_failures_total")
            raise IntegrityFailure(str(exc), resource=rollout_id, cause=exc) from exc
        return state, core, rec.revision

    def _commit(self, state: dict[str, Any], core: Rollout, revision: int, fence: int) -> int:
        state["core"] = core.snapshot()
        state["updated_at"] = self.clock.now()
        rec = self.store.commit(state["rollout_id"], state, expected_revision=revision, fence=fence)
        return rec.revision

    def _seal(self, state: dict[str, Any], core: Rollout, revision: int, fence: int, *, strict: bool) -> int:
        """Seal unsealed local audit events externally; persist the receipt head."""
        start = state.get("sealed_count", 0)
        pending = core.audit_log[start:]
        if not pending:
            return revision
        sealed = start
        try:
            for ev in pending:
                receipt = self.sink.append(dict(ev))  # full event: the sink can reconstruct history
                sealed += 1
                state["audit_head"] = receipt.to_dict()
        except DependencyUnavailable:
            self.telemetry.inc("gap08_dependency_unavailable_total", dependency="audit_sink")
            state["sealed_count"] = sealed
            revision = self._commit(state, core, revision, fence)
            if strict:
                raise
            return revision
        state["sealed_count"] = sealed
        return self._commit(state, core, revision, fence)

    def _flush_unsealed(self, state, core, revision, fence) -> int:
        if state.get("sealed_count", 0) < len(core.audit_log):
            return self._seal(state, core, revision, fence, strict=True)
        return revision

    def _guard(self, op: OpClass) -> None:
        try:
            self.deps.guard(op)
        except DependencyUnavailable as exc:
            self.telemetry.inc("gap08_dependency_unavailable_total", dependency=str(exc.resource))
            raise

    def _scoped(self, who: Principal, cap: Cap, state: dict[str, Any]) -> None:
        self.policy.check(who, cap, state["rollout_id"], environment=state["environment"])

    def _event(self, core: Rollout, event: str, who: Principal | None, **payload: Any) -> dict[str, Any]:
        return core._record(event, by=who.id if who else self.controller_id, **payload)

    def _gauges(self, state: dict[str, Any], core: Rollout) -> None:
        self.telemetry.set("gap08_deferred_nodes", len(core.deferred))
        self.telemetry.set("gap08_quarantined_nodes", len(core.quarantined))
        ages = dq.ages(state["deferred_queue"], now=self.clock.now())
        self.telemetry.set("gap08_deferred_oldest_age_seconds", max(ages.values()) if ages else 0)
        for v in {core.bundle, core.pinned_target}:
            if v:
                self.telemetry.set("gap08_nodes_on_version", len(core.fleet_on(v)), version=v)

    def _finish(self, state: dict[str, Any], phase: str) -> None:
        state["phase"] = phase
        self.conflicts.release(state["rollout_id"])
        self.admission.finish_rollout(state["rollout_id"])

    def _verified(self, state) -> VerifiedArtifact:
        return VerifiedArtifact(**state["artifact"])

    def _query_versions(self, rollout_id: str, fence: int, nodes: Iterable[str]) -> dict[str, Outcome]:
        return self.executor.run(rollout_id=rollout_id, fence=fence, op="query", nodes=nodes,
                                 target_version=None, digest=None, attempt_group=new_id("q"))

    # ------------------------------------------------------------------ create
    def create(self, who: Principal, *, bundle: str, waves: list[list[str]], environment: str,
               verification: Mapping[str, Any], compat_profile: Mapping[str, str],
               lineage: str | None = None, rollout_id: str | None = None) -> dict[str, Any]:
        t0 = time.perf_counter()
        rollout_id = rollout_id or new_id("ro")
        self.policy.check(who, Cap.START, rollout_id, environment=environment)
        self.admission.api(who.id)
        self._guard(OpClass.FORWARD)
        artifact = self.verifier.admit(verification, bundle=bundle)
        self.freeze.check(rollout_id=rollout_id, artifact_digest=artifact.digest)
        compat = compat_check(compat_profile)
        core = Rollout(bundle, waves=waves, rollout_id=rollout_id)
        for w in core.waves:
            self.admission.check_wave(len(w))
        inv = self.inventory()
        missing = sorted(core.scheduled_nodes - set(inv.nodes))
        if missing:
            raise ValidationFailed(f"nodes missing from topology inventory: {missing[:10]}", resource=rollout_id)
        scope = Scope.of(environment, core.scheduled_nodes, inv.sites(core.scheduled_nodes), lineage)
        self.conflicts.reserve(rollout_id, scope)
        try:
            self.admission.admit_rollout(rollout_id)
            lease = self._lease(rollout_id)
            observed = self._query_versions(rollout_id, lease.token, sorted(core.scheduled_nodes))
            bad = {n: o.reason for n, o in observed.items() if o.status != "ok"}
            if bad:
                raise DependencyUnavailable(f"cannot pin: unauthenticated/unknown node state {bad}",
                                            resource=rollout_id)
            core.pin({n: o.observed_version for n, o in observed.items()})
            core.admit({"schema": "PK_VERIFICATION/1", "verified": True, "kind": "bundle", "bundle": bundle,
                        "digest": artifact.digest})
            self._event(core, "rollout_created", who, environment=environment, lineage=lineage,
                        artifact=artifact.to_dict(), compatibility=compat, inventory_version=inv.version,
                        controller=self.controller_id, fence=lease.token)
            state = {"schema": CONTROLLER_SCHEMA, "rollout_id": rollout_id, "phase": "admitted", "paused": False,
                     "environment": environment, "lineage": lineage, "sites": sorted(scope.sites),
                     "artifact": artifact.to_dict(), "pending": None, "deferred_queue": {}, "quarantine": {},
                     "sealed_count": 0, "audit_head": None, "retry_seq": 0, "rollback_intent": None, "created_by": who.id,
                     "created_at": self.clock.now(), "needs_reconcile": [], "core": core.snapshot()}
            rec = self.store.create(rollout_id, state, fence=lease.token)
            self._seal(state, core, rec.revision, lease.token, strict=True)
        except BaseException:
            self.conflicts.release(rollout_id)
            self.admission.finish_rollout(rollout_id)
            raise
        self.telemetry.observe("gap08_step_seconds", time.perf_counter() - t0, op="create")
        self.telemetry.log("rollout_created", rollout_id=rollout_id, bundle=bundle, by=who.id)
        return self.status(rollout_id)

    # ------------------------------------------------------------------ apply wave / retry
    def _dispatch(self, state, core, revision, lease, *, kind: str, nodes: list[str], cohort: str) -> int:
        art = self._verified(state)
        state["pending"] = {"kind": kind, "cohort": cohort, "nodes": nodes, "status": "dispatching",
                            "attempt_group": state["retry_seq"], "applied_at": None, "outcomes": {}}
        self._event(core, "dispatch_intent", None, kind=kind, cohort=cohort, nodes=nodes, fence=lease.token)
        revision = self._commit(state, core, revision, lease.token)  # write-ahead intent
        revision = self._seal(state, core, revision, lease.token, strict=True)
        return self._send(state, core, revision, lease, art)

    def _send(self, state, core, revision, lease, art) -> int:
        p = state["pending"]
        outs = self.executor.run(rollout_id=core.rollout_id, fence=lease.token, op="install", nodes=p["nodes"],
                                 target_version=core.bundle, digest=art.digest, attempt_group=p["attempt_group"])
        for n, o in outs.items():
            self.telemetry.inc("gap08_commands_total", op="install", outcome=o.status)
        p["outcomes"] = {n: o.to_dict() for n, o in outs.items()}
        p["status"] = "awaiting_gate"
        p["applied_at"] = self.clock.now()
        state["phase"] = "awaiting_gate"
        state["needs_reconcile"] = sorted(set(state["needs_reconcile"]) |
                                          {n for n, o in outs.items() if o.status == "unknown"})
        self._event(core, "dispatch_result", None, cohort=p["cohort"],
                    outcomes={n: {"status": o.status, "reason": o.reason, "ack_ref": o.ack_ref,
                                  "command_id": o.command_id} for n, o in outs.items()})
        revision = self._commit(state, core, revision, lease.token)
        return self._seal(state, core, revision, lease.token, strict=False)

    def _forward_checks(self, state, core, who: Principal, nodes: list[str], cap: Cap) -> tuple[Lease, int]:
        self.policy.check(who, cap, core.rollout_id, environment=state["environment"])
        self.admission.api(who.id)
        self._guard(OpClass.FORWARD)
        lease = self._lease(core.rollout_id)
        if state["phase"] in TERMINAL:
            raise IllegalTransition(f"rollout is {state['phase']}", resource=core.rollout_id)
        if state["paused"]:
            raise IllegalTransition("rollout is paused", resource=core.rollout_id)
        if state.get("rollback_intent"):
            raise IllegalTransition("a rollback is in progress", resource=core.rollout_id)
        if state["pending"] is not None:
            raise IllegalTransition("a gate is pending for the previous dispatch", resource=core.rollout_id)
        art = self._verified(state)
        self.freeze.check(rollout_id=core.rollout_id, artifact_digest=art.digest)
        if not self.verifier.still_valid(art):
            raise EvidenceRejected("artifact verification expired or revoked", resource=core.rollout_id)
        inv = self.inventory()
        now = self.clock.now()
        for site in sorted(inv.sites(nodes)):
            self.windows.check(site, now)
        unavailable = set(core.quarantined) | set(core.deferred)
        decision = self.topology.admit_wave(nodes, inv, now=now, unavailable=unavailable - set(nodes))
        self._event(core, "policy_admitted", who, nodes=nodes, topology=decision)
        return lease, now

    def step(self, who: Principal, rollout_id: str) -> dict[str, Any]:
        t0 = time.perf_counter()
        state, core, revision = self._load(rollout_id)
        if core.wave_index >= len(core.waves):
            raise IllegalTransition("all waves dispatched; use retry_deferred", resource=rollout_id)
        wave = core.waves[core.wave_index]
        lease, _ = self._forward_checks(state, core, who, wave, Cap.STEP)
        revision = self._flush_unsealed(state, core, revision, lease.token)
        self.admission.check_wave(len(wave))
        revision = self._dispatch(state, core, revision, lease, kind="wave", nodes=list(wave),
                                  cohort=f"wave-{core.wave_index + 1}")
        self.telemetry.observe("gap08_step_seconds", time.perf_counter() - t0, op="step")
        return self.status(rollout_id)

    def retry_deferred(self, who: Principal, rollout_id: str, *, force: bool = False) -> dict[str, Any]:
        state, core, revision = self._load(rollout_id)
        self._scoped(who, Cap.RETRY_DEFERRED, state)   # authorize before revealing anything
        now = self.clock.now()
        nodes = sorted(core.deferred) if force else [n for n in dq.due(state["deferred_queue"], now=now)
                                                     if n in core.deferred]
        if not nodes:
            return self.status(rollout_id)
        lease, _ = self._forward_checks(state, core, who, nodes, Cap.RETRY_DEFERRED)
        self.admission.check_deferred(len(core.deferred))
        state["retry_seq"] += 1
        return self._after(self._dispatch(state, core, revision, lease, kind="retry", nodes=nodes,
                                          cohort=f"retry-{state['retry_seq']}"), rollout_id)

    def reverify(self, who: Principal, rollout_id: str, verification: Mapping[str, Any]) -> dict[str, Any]:
        """Refresh an expired GAP-07 verification before deferred retries.

        The new statement must name the same bundle *and the same content digest*; a different digest
        is a different artifact and needs a new rollout.  If GAP-07 is unavailable the rollout simply
        cannot make forward progress (fail closed) — rollback remains available.
        """
        self.policy.check(who, Cap.RETRY_DEFERRED, rollout_id)
        self._guard(OpClass.FORWARD)
        state, core, revision = self._load(rollout_id)
        self._scoped(who, Cap.RETRY_DEFERRED, state)
        old = self._verified(state)
        art = self.verifier.admit(verification, bundle=core.bundle)
        if art.digest != old.digest:
            raise EvidenceRejected("re-verification names a different content digest", resource=rollout_id)
        lease = self._lease(rollout_id)
        state["artifact"] = art.to_dict()
        self._event(core, "artifact_reverified", who, verification_ref=art.verification_ref,
                    expires_at=art.expires_at)
        revision = self._commit(state, core, revision, lease.token)
        self._seal(state, core, revision, lease.token, strict=True)
        return self.status(rollout_id)

    def _after(self, _rev: int, rollout_id: str) -> dict[str, Any]:
        return self.status(rollout_id)

    # ------------------------------------------------------------------ gate
    def gate(self, who: Principal, rollout_id: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        self.policy.check(who, Cap.GATE, rollout_id)
        state, core, revision = self._load(rollout_id)
        self._scoped(who, Cap.GATE, state)
        p = state["pending"]
        if p is None or p["status"] != "awaiting_gate" or state.get("rollback_intent"):
            raise IllegalTransition("no dispatch is awaiting a gate", resource=rollout_id)
        lease = self._lease(rollout_id)
        applied = sorted(n for n, o in p["outcomes"].items() if o["status"] == "ok")
        failed = sorted(n for n, o in p["outcomes"].items() if o["status"] == "failed")
        unknown = sorted(n for n, o in p["outcomes"].items() if o["status"] == "unknown")
        try:
            self._guard(OpClass.FORWARD)
            decision = self.health.evaluate(evidence, rollout_id=rollout_id, cohort=p["cohort"], nodes=applied,
                                            applied_at=p["applied_at"], policy=self.gate_policy)
        except (EvidenceRejected, DependencyUnavailable) as exc:
            self.telemetry.inc("gap08_gate_verdicts_total", outcome="evidence_rejected")
            self.telemetry.log("gate_evidence_rejected", level="warning", rollout_id=rollout_id, code=exc.code,
                               detail=exc.detail)
            raise
        healthy = decision.healthy and not failed
        ev = {"evidence_id": decision.evidence_id, "evidence_digest": decision.evidence_digest,
              "source": decision.source, "coverage": decision.coverage, "detail": decision.detail,
              "install_failures": failed, "unknown_outcomes": unknown}
        self.telemetry.inc("gap08_gate_verdicts_total", outcome="healthy" if healthy else "unhealthy")
        if not healthy:
            # write-ahead: the rollback intent must win the CAS *before* any node is touched
            return self._rollback_with_intent(state, core, revision, lease, requested_by=who.id,
                                              reason=f"health gate {p['cohort']} failed", gate_id=p["cohort"],
                                              evidence=ev, trigger="gate")
        offline = sorted(set(failed) | set(unknown))
        if p["kind"] == "wave":
            verdict = core.run_wave(healthy=True, offline=offline, gate_id=p["cohort"], evidence=ev)
            for n in offline:
                dq.enqueue(state["deferred_queue"], n, now=self.clock.now(),
                           reason=p["outcomes"][n]["reason"] or "offline")
        else:
            now = self.clock.now()
            for n in offline:
                dq.record_attempt(state["deferred_queue"], n, now=now, ok=False, reason=p["outcomes"][n]["reason"])
            verdict = (core.retry_deferred(healthy=True, nodes=applied, gate_id=p["cohort"], evidence=ev)
                       if applied else {"touched": []})
            for n in applied:
                if n in state["deferred_queue"]:
                    dq.record_attempt(state["deferred_queue"], n, now=now, ok=True, reason=None)
        state["pending"] = None
        st = core.state.value
        state["phase"] = {"complete": "complete", "deferred": "deferred"}.get(st, "admitted")
        if state["phase"] == "complete":
            self._finish(state, "complete")
        self._gauges(state, core)
        revision = self._commit(state, core, revision, lease.token)
        self._seal(state, core, revision, lease.token, strict=False)
        return {**self.status(rollout_id), "verdict": {k: verdict.get(k) for k in ("touched", "deferred", "healthy")
                                                       if k in verdict}, "gate": ev, "healthy": True}

    # ------------------------------------------------------------------ operator controls (28, 29)
    def rollback(self, who: Principal, rollout_id: str, *, reason: str) -> dict[str, Any]:
        self.policy.check(who, Cap.ROLLBACK, rollout_id)
        self._guard(OpClass.ROLLBACK)
        state, core, revision = self._load(rollout_id)
        self._scoped(who, Cap.ROLLBACK, state)
        if state["phase"] in TERMINAL:
            raise IllegalTransition(f"rollout is {state['phase']}", resource=rollout_id)
        if state.get("rollback_intent"):
            raise IllegalTransition("a rollback is already in progress; use recover()", resource=rollout_id)
        lease = self._lease(rollout_id)
        return self._rollback_with_intent(state, core, revision, lease, requested_by=who.id,
                                          reason=f"operator {who.id}: {reason}", gate_id="operator-rollback",
                                          evidence={"operator": who.id, "reason": reason}, trigger="operator")

    def _rollback_with_intent(self, state, core, revision, lease, *, requested_by: str, reason: str,
                              gate_id: str, evidence: dict[str, Any], trigger: str) -> dict[str, Any]:
        """Two-phase rollback: (1) CAS-commit a rollback intent, (2) command nodes, (3) commit outcome.

        Step (1) serialises against any concurrent gate/step/rollback: whoever loses the CAS never touches
        a node.  A crash between (1) and (3) is finished by ``recover()`` (rollback commands are idempotent).
        """
        rid = core.rollout_id
        if not state.get("rollback_intent"):
            state["rollback_intent"] = {"requested_by": requested_by, "reason": reason, "gate_id": gate_id,
                                        "evidence": evidence, "trigger": trigger, "at": self.clock.now()}
            self._event(core, "rollback_intent", None, requested_by=requested_by, reason=reason, trigger=trigger)
            revision = self._commit(state, core, revision, lease.token)
        p = state["pending"]
        pending_applied = sorted(n for n, o in (p or {}).get("outcomes", {}).items() if o["status"] == "ok")
        if p is not None and p["status"] == "dispatching":
            pending_applied = list(p["nodes"])   # results unknown: treat every dispatched node as possibly updated
        on_bundle = set(core.fleet_on(core.bundle))
        candidates = sorted((on_bundle | set(pending_applied)) - set(core.quarantined))
        outs = self.executor.run(rollout_id=rid, fence=lease.token, op="rollback", nodes=candidates,
                                 target_version=core.pinned_target, digest=None,
                                 attempt_group=f"rb{state['retry_seq']}")
        failures = sorted(n for n, o in outs.items() if o.status != "ok")
        for n, o in outs.items():
            self.telemetry.inc("gap08_commands_total", op="rollback", outcome=o.status)
        ev = {**evidence, "rollback_outcomes": {n: {"status": o.status, "reason": o.reason} for n, o in outs.items()}}
        if p is not None and p["kind"] == "wave":
            offline = sorted(set(p["nodes"]) - set(pending_applied))
            core.run_wave(healthy=False, offline=offline, gate_id=gate_id, evidence=ev, rollback_failures=failures)
        elif p is not None and p["kind"] == "retry" and pending_applied:
            core.retry_deferred(healthy=False, nodes=pending_applied, gate_id=gate_id, evidence=ev,
                                rollback_failures=failures)
        else:
            core.rollback(reason=reason, fail_nodes=failures)
        state["pending"] = None
        state["rollback_intent"] = None
        for n in failures:
            state["quarantine"][n] = {"since": self.clock.now(), "reason": "rollback failed", "status": "quarantined"}
        self.telemetry.inc("gap08_rollbacks_total", trigger=trigger, complete=str(not failures).lower())
        self.telemetry.inc("gap08_rollback_failed_nodes_total", len(failures))
        self._finish(state, "rollback_incomplete" if failures else "rolled_back")
        self._gauges(state, core)
        revision = self._commit(state, core, revision, lease.token)
        self._seal(state, core, revision, lease.token, strict=False)  # buffered if the sink is down
        return {**self.status(rid), "healthy": False, "gate": ev}

    def pause(self, who: Principal, rollout_id: str, reason: str) -> dict[str, Any]:
        return self._flag(who, rollout_id, Cap.PAUSE, True, reason)

    def resume(self, who: Principal, rollout_id: str, reason: str) -> dict[str, Any]:
        return self._flag(who, rollout_id, Cap.RESUME, False, reason)

    def _flag(self, who, rollout_id, cap, paused, reason) -> dict[str, Any]:
        self.policy.check(who, cap, rollout_id)
        self._guard(OpClass.ROLLBACK)
        state, core, revision = self._load(rollout_id)
        self._scoped(who, cap, state)
        if state["phase"] in TERMINAL:
            raise IllegalTransition(f"rollout is {state['phase']}", resource=rollout_id)
        lease = self._lease(rollout_id)
        state["paused"] = paused
        self._event(core, "paused" if paused else "resumed", who, reason=reason)
        revision = self._commit(state, core, revision, lease.token)
        self._seal(state, core, revision, lease.token, strict=False)
        return self.status(rollout_id)

    def cancel(self, who: Principal, rollout_id: str, *, mode: str = "rollback", reason: str,
               approval_id: str | None = None) -> dict[str, Any]:
        """Cancellation semantics (component 28).

        * nothing touched yet -> ``cancelled`` (terminal, no node commands);
        * partially applied + ``mode='rollback'`` -> operator rollback;
        * partially applied + ``mode='abandon'`` -> leave nodes as-is, terminal
          ``abandoned``; requires OVERRIDE with a second-person approval and
          flags every scheduled node for reconciliation.
        """
        self.policy.check(who, Cap.CANCEL, rollout_id)
        self._guard(OpClass.ROLLBACK)
        state, core, revision = self._load(rollout_id)
        self._scoped(who, Cap.CANCEL, state)
        if state["phase"] in TERMINAL:
            raise IllegalTransition(f"rollout is {state['phase']}", resource=rollout_id)
        touched = core.wave_index > 0 or state["pending"] is not None
        if not touched:
            lease = self._lease(rollout_id)
            self._event(core, "cancelled", who, reason=reason, touched=False)
            self._finish(state, "cancelled")
            revision = self._commit(state, core, revision, lease.token)
            self._seal(state, core, revision, lease.token, strict=False)
            return self.status(rollout_id)
        if mode == "rollback":
            return self.rollback(who, rollout_id, reason=f"cancel: {reason}")
        if mode != "abandon":
            raise ValidationFailed("mode must be 'rollback' or 'abandon'")
        self.policy.check(who, Cap.OVERRIDE, rollout_id)
        appr = self.approvals.consume(approval_id or "", Cap.OVERRIDE, f"abandon:{rollout_id}")
        lease = self._lease(rollout_id)
        self._event(core, "abandoned", who, reason=reason, approval=appr["approval_id"], approver=appr["approver"])
        state["pending"] = None
        state["needs_reconcile"] = sorted(core.scheduled_nodes)
        self._finish(state, "abandoned")
        revision = self._commit(state, core, revision, lease.token)
        self._seal(state, core, revision, lease.token, strict=False)
        return self.status(rollout_id)

    def release_quarantine(self, who: Principal, rollout_id: str, node: str, *, approval_id: str,
                           evidence_note: str) -> dict[str, Any]:
        """Quarantine recovery workflow (component 29).

        Release needs: QUARANTINE_RELEASE capability, a second-person approval
        bound to ``release:<rollout>:<node>``, a remediation note, and an
        *authenticated* query showing the node now runs the pinned target.
        """
        self.policy.check(who, Cap.QUARANTINE_RELEASE, rollout_id)
        self._guard(OpClass.ROLLBACK)
        state, core, revision = self._load(rollout_id)
        self._scoped(who, Cap.QUARANTINE_RELEASE, state)
        if node not in core.quarantined:
            raise ValidationFailed(f"{node} is not quarantined", resource=node)
        if not evidence_note.strip():
            raise ValidationFailed("remediation evidence note required")
        appr = self.approvals.consume(approval_id, Cap.QUARANTINE_RELEASE, f"release:{rollout_id}:{node}")
        lease = self._lease(rollout_id)
        obs = self._query_versions(rollout_id, lease.token, [node])[node]
        if obs.status != "ok" or obs.observed_version != core.pinned_target:
            raise EvidenceRejected(f"{node} is not verifiably on {core.pinned_target}: {obs.status}/"
                                   f"{obs.observed_version}", resource=node)
        core.versions[node] = core.pinned_target
        core.rollback_failed = [n for n in core.rollback_failed if n != node]
        core.quarantined = [n for n in core.quarantined if n != node]
        self._event(core, "quarantine_released", who, node=node, approval=appr["approval_id"],
                    approver=appr["approver"], ack_ref=obs.ack_ref, note=evidence_note)
        state["quarantine"][node] = {**state["quarantine"].get(node, {}), "status": "released",
                                     "released_at": self.clock.now()}
        if state["phase"] == "rollback_incomplete" and not core.rollback_failed:
            state["phase"] = "rolled_back"
        self._gauges(state, core)
        revision = self._commit(state, core, revision, lease.token)
        self._seal(state, core, revision, lease.token, strict=False)
        return self.status(rollout_id)

    # ------------------------------------------------------------------ reconciliation (30)
    def reconcile(self, who: Principal, rollout_id: str) -> dict[str, Any]:
        """Compare recorded state with authenticated observed versions; never mutates nodes."""
        self.policy.check(who, Cap.RECONCILE, rollout_id)
        state, core, revision = self._load(rollout_id)
        self._scoped(who, Cap.RECONCILE, state)
        lease = self._lease(rollout_id)
        obs = self._query_versions(rollout_id, lease.token, sorted(core.scheduled_nodes))
        drift, unreachable = {}, []
        for n, o in obs.items():
            if o.status != "ok":
                unreachable.append(n)
                continue
            if o.observed_version != core.versions.get(n):
                drift[n] = {"recorded": core.versions.get(n), "observed": o.observed_version,
                            "class": ("installed_while_deferred" if n in core.deferred and o.observed_version ==
                                      core.bundle else "unexpected_version")}
        state["needs_reconcile"] = sorted(set(unreachable) | set(drift))
        self._event(core, "reconciled", who, drift=drift, unreachable=unreachable)
        self.telemetry.set("gap08_drift_nodes", len(drift))
        revision = self._commit(state, core, revision, lease.token)
        self._seal(state, core, revision, lease.token, strict=False)
        return {"rollout_id": rollout_id, "drift": drift, "unreachable": unreachable,
                "recommendation": ("hold: resolve drift before new mutations" if drift or unreachable else "in sync")}

    # ------------------------------------------------------------------ restart / takeover
    def recover(self, rollout_id: str) -> dict[str, Any]:
        """Take over a rollout after controller crash/failover (new fence), finish any
        write-ahead dispatch idempotently, and re-seal buffered audit events."""
        state, core, revision = self._load(rollout_id)
        lease = self._lease(rollout_id)
        if state["phase"] not in TERMINAL:
            inv = self.inventory()
            self.conflicts.reserve(rollout_id, Scope.of(state["environment"], core.scheduled_nodes,
                                                        inv.sites(core.scheduled_nodes), state["lineage"]))
            self.admission.admit_rollout(rollout_id)
        self._event(core, "controller_takeover", None, controller=self.controller_id, fence=lease.token)
        revision = self._commit(state, core, revision, lease.token)
        intent = state.get("rollback_intent")
        if intent and state["phase"] not in TERMINAL:
            # finish an already-authorized rollback (idempotent node commands)
            return self._rollback_with_intent(state, core, revision, lease, requested_by=intent["requested_by"],
                                              reason=intent["reason"], gate_id=intent["gate_id"],
                                              evidence=intent["evidence"], trigger=intent["trigger"])
        p = state["pending"]
        if p is not None and p["status"] == "dispatching":
            revision = self._send(state, core, revision, lease, self._verified(state))
        self._seal(state, core, revision, lease.token, strict=False)
        return self.status(rollout_id)

    # ------------------------------------------------------------------ read
    def status(self, rollout_id: str) -> dict[str, Any]:
        rec = self.store.load(rollout_id)
        s = rec.state
        c = s["core"]
        return {"rollout_id": rollout_id, "revision": rec.revision, "fence": rec.fence, "phase": s["phase"],
                "paused": s["paused"], "bundle": c["bundle"], "pinned_target": c["pinned_target"],
                "wave_index": c["wave_index"], "waves": len(c["waves"]), "deferred": c["deferred"],
                "quarantined": c["quarantined"], "rollback_failed": c["rollback_failed"],
                "pending": (None if s["pending"] is None else
                            {k: s["pending"][k] for k in ("kind", "cohort", "status", "nodes", "applied_at")}),
                "sealed": s.get("sealed_count", 0), "audit_events": len(c["audit_log"]),
                "needs_reconcile": s.get("needs_reconcile", [])}
