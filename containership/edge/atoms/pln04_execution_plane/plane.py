"""ExecutionPlane - the integrated 4.3.0 admission/lifecycle facade.

Admission pipeline (each step is a stable, audited decision point)::

    validate PK_ADMISSION/1 -> authenticate + authorize (M08) -> rollout gate (M30)
    -> residency (M38) -> signed classification (M07) -> idempotency
    -> bounded queue (M45) -> tier policy (runtime.select_tier)
    -> co-residency (M39) -> artifact allowlist (M09) -> capacity + fair share (M16)
    -> ownership lease / fencing epoch (M12) -> persist RESERVED (M11)
    -> provider start via circuit breaker + retry (M03/M13/M15)
    -> persist ACTIVE -> audit (M19) -> export (M36) -> metrics (M20/M44)

No record is ``active`` until the provider confirms creation.  Every failure
after reservation is compensated (stop -> zeroize -> terminated) and
resources are released only after a *verified* zeroization receipt (M40).
"""
from __future__ import annotations

import hashlib
from collections import deque
import json
import threading
import time
import uuid
from dataclasses import asdict, replace
from typing import Callable, Mapping

from . import runtime
from .errors import PlaneError, from_exception
from .observability import DurableAuditSink, EventExporter, LatencySlo, Telemetry, TelemetryPolicy
from .policy import PRODUCTION_REQUIREMENTS, PlaneConfig, RolloutControl, check_coresidency, check_residency
from .providers import LIFECYCLE, ProviderRegistry, ProviderRequest, Resources, check_transition
from .resilience import AdmissionGate, CircuitBreaker, FairShare, RetryPolicy, retry
from .security import (ArtifactPolicy, AttestationVerifier, Authenticator, CapabilityReport,
                       ClassificationVerifier, authorize)
from .store import FileStateStore, LeaseManager, MemoryStateStore, StateStore
from .validation import validate

LEASE_TTL_S = 30.0
IDEMPOTENCY_TTL_S = 24 * 3600.0


class _MemoryAudit:
    """Non-durable audit used only by development profiles without a sink."""

    def __init__(self, capacity: int = 10000) -> None:
        self.records: deque[dict] = deque(maxlen=capacity)
        self._node = runtime.Node({"process": True}, audit_limit=capacity)

    def append(self, kind: str, details: Mapping[str, object], timestamp_ns: int | None = None) -> dict:
        self._node._emit(kind, **dict(details))
        ev = self._node.audit_events()[-1]
        rec = {"sequence": ev.sequence, "timestamp_ns": ev.timestamp_ns, "kind": kind, "details": dict(details),
               "previous_hash": ev.previous_hash, "event_hash": ev.event_hash}
        self.records.append(rec)
        return rec


class ExecutionPlane:
    def __init__(
        self,
        config: PlaneConfig,
        registry: ProviderRegistry,
        *,
        store: StateStore | None = None,
        audit: DurableAuditSink | None = None,
        telemetry: Telemetry | None = None,
        authenticator: Authenticator | None = None,
        classifier: ClassificationVerifier | None = None,
        artifacts: ArtifactPolicy | None = None,
        attestor: AttestationVerifier | None = None,
        exporter: EventExporter | None = None,
        capability_report: CapabilityReport | None = None,
        owner_id: str | None = None,
        retry_policy: RetryPolicy | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self.config = config
        self.registry = registry
        self.store = store or MemoryStateStore()
        self.audit = audit or _MemoryAudit()
        tel = config["telemetry"]
        self.telemetry = telemetry or Telemetry(TelemetryPolicy(
            trace_sample_rate=tel.get("trace_sample_rate", 0.1),
            tenant_identifier_mode=tel.get("tenant_identifier_mode", "hashed"),
            retention_days_logs=tel.get("retention_days_logs", 30),
            retention_days_audit=tel.get("retention_days_audit", 400)))
        self.authenticator = authenticator
        self.classifier = classifier
        self.artifacts = artifacts
        self.attestor = attestor
        self.exporter = exporter
        self.capability_report = capability_report
        self.owner_id = owner_id or f"{config['node_id']}:{uuid.uuid4().hex[:8]}"
        self._mono = monotonic
        self._wall = wall
        self._retry = retry_policy or RetryPolicy()
        if config.production:
            missing = [name for name, ok in zip(PRODUCTION_REQUIREMENTS, (
                authenticator, classifier, artifacts, attestor,
                isinstance(self.store, FileStateStore) or (type(self.store) is not MemoryStateStore),
                isinstance(self.audit, DurableAuditSink),
                not any(registry.get(t).reference for t in registry.tiers()))) if not ok]
            if missing:
                raise PlaneError("PLN04-VAL-001", details={"reason": "production profile missing: " + ", ".join(missing)})
        lim = config["limits"]
        self.node = runtime.Node({t: False for t in registry.tiers()} or {"process": False},
                                 max_instances=lim["max_instances"], per_tenant_limit=lim["per_tenant_limit"])
        self.gate = AdmissionGate(max_inflight=lim["max_inflight"], max_queue=lim["max_queue"],
                                  per_tenant_queue=lim["per_tenant_queue"])
        self.fair = FairShare(cpu_milli=lim["cpu_milli"], memory_mib=lim["memory_mib"],
                              weights=config["tenant_weights"], headroom=lim["headroom"])
        self.rollout = RolloutControl(config["rollout"]["stage"], config["rollout"]["canary_tenants"])
        self.leases = LeaseManager(self.store, clock=monotonic, on_split_brain=self._split_brain)
        self.breakers = {t: CircuitBreaker(f"provider:{t}") for t in registry.tiers()}
        self.slo = LatencySlo(p50_ms=config["slo"]["p50_ms"], p99_ms=config["slo"]["p99_ms"])
        self._attest_expiry: dict[str, float] = {}
        self._leases: dict[str, object] = {}
        # striped per-workload locks: bounded memory regardless of workload churn
        self._wl_locks = tuple(threading.Lock() for _ in range(256))
        self._lock = threading.RLock()
        self._audit("config_applied", generation=config.generation, profile=config["profile"], site=config["site"])

    # ------------------------------------------------------------------ helpers
    def _audit(self, kind: str, **details: object) -> dict:
        rec = self.audit.append(kind, details)
        if self.exporter is not None:
            try:
                self.exporter.enqueue({"schema": "PK_TIER_LIFECYCLE/1", "event": kind, **rec})
            except PlaneError:
                self.telemetry.inc("pln04_export_backpressure")
        self.telemetry.log("info", kind, security=True, **details)
        return rec

    def _split_brain(self, key: str, holder: str, claimant: str) -> None:
        self.telemetry.inc("pln04_split_brain_detected")
        self._audit("split_brain_detected", workload=key, reason=f"claimant {claimant} vs holder {holder}")

    def _wl_lock(self, workload: str) -> threading.Lock:
        return self._wl_locks[int(hashlib.blake2b(workload.encode(), digest_size=2).hexdigest(), 16) % 256]

    def _record(self, workload: str) -> tuple[int, dict] | None:
        return self.store.get(f"inst/{workload}")

    def _transition(self, workload: str, target: str, **fields: object) -> dict:
        ver, rec = self._record(workload) or (0, None)
        if rec is None:
            raise PlaneError("PLN04-STATE-004", details={"workload": workload, "to_state": target})
        check_transition(rec["state"], target)
        rec = {**rec, **fields, "state": target, "updated_ns": time.time_ns()}
        self.store.cas(f"inst/{workload}", ver, rec)
        return rec

    # ------------------------------------------------------------------ attestation (M05/M06/M37)
    def attest_tier(self, tier: str, evidence: str | None = None) -> float:
        """Make ``tier`` eligible for admission.  Returns the attestation expiry (wall seconds)."""
        provider = self.registry.get(tier)
        cap = provider.probe()
        if not cap.available:
            raise PlaneError("PLN04-ATT-002", details={"tier": tier, "reason": cap.reason or "provider unavailable"})
        if self.capability_report is not None and not self.capability_report.supports(tier):
            raise PlaneError("PLN04-ATT-002", details={"tier": tier, "reason": "hardware capability missing"})
        if self.attestor is not None:
            expiry = self.attestor.verify(evidence or "", node_id=self.config["node_id"], tier=tier)
        elif self.config.production:
            raise PlaneError("PLN04-ATT-002", details={"tier": tier, "reason": "no attestation verifier"})
        else:
            expiry = self._wall() + self.config["attestation"]["max_age_s"]
        self._attest_expiry[tier] = expiry
        self.node.restore_attestation(tier)
        self._audit("attestation_restored", tier=tier, reason="verified" if self.attestor else "probe-only (non-production)")
        return expiry

    def fail_tier(self, tier: str, reason: str) -> tuple[str, ...]:
        affected = self.node.fail_attestation(tier)
        for wl in affected:
            try:
                self._transition(wl, "quarantined")
            except PlaneError:
                pass
        self._attest_expiry.pop(tier, None)
        self._audit("attestation_failed", tier=tier, affected_workloads=list(affected), reason=reason)
        self.telemetry.inc("pln04_attestation_failures", tier=tier)
        return affected

    def refresh_attestation(self) -> list[str]:
        """Fail closed every tier whose attestation expired (call periodically)."""
        now = self._wall()
        expired = [t for t, exp in list(self._attest_expiry.items()) if exp <= now]
        for tier in expired:
            self.fail_tier(tier, "attestation expired")
        return expired

    # ------------------------------------------------------------------ admission
    def admit(self, request: Mapping, *, token: str | None = None, command: tuple[str, ...] = (),
              traceparent: str | None = None) -> dict:
        started = self._mono()
        trace_id, _ = self.telemetry.new_trace(traceparent)
        request_id = request.get("request_id") if isinstance(request, Mapping) else None
        tier_label = "none"
        try:
            decision = self._admit(dict(request), token, command, trace_id)
            tier_label = decision.get("tier", "none")
            self.telemetry.inc("pln04_admissions", outcome=decision["outcome"], tier=tier_label)
            return decision
        except PlaneError as exc:
            exc.request_id = exc.request_id or request_id
            self.telemetry.inc("pln04_admission_errors", error_code=exc.code)
            raise
        except Exception as exc:
            err = from_exception(exc, request_id)
            self.telemetry.inc("pln04_admission_errors", error_code=err.code)
            raise err from exc
        finally:
            self.telemetry.observe("pln04_admission_latency_ms", (self._mono() - started) * 1000.0)

    def _admit(self, req: dict, token: str | None, command: tuple[str, ...], trace_id: str) -> dict:
        validate(req, "PK_ADMISSION/1")
        if req["kind"] != "request":
            raise PlaneError("PLN04-VAL-001", details={"field": "kind", "reason": "must be request"})
        workload, tenant, trust_class = req["workload"], req["tenant"], req["trust_class"]
        runtime._require_identifier(workload, "workload")
        runtime._require_identifier(tenant, "tenant")
        if self.authenticator is not None:
            actor = self.authenticator.authenticate(token)
            authorize(actor, "admission:create", tenant=tenant)
        self.rollout.check(tenant)
        check_residency(self.config, tenant, req.get("site"))
        policy_digest = "sha256:" + "0" * 64
        if self.classifier is not None:
            cls = self.classifier.verify(req.get("classification_token"), workload=workload, tenant=tenant)
            if cls.trust_class != trust_class:
                raise PlaneError("PLN04-POL-002", details={"trust_class": trust_class, "reason": "request disagrees with signed classification"})
            policy_digest = cls.policy_digest

        body = {k: v for k, v in req.items() if k not in ("request_id", "classification_token")}
        req_digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        idem = req.get("idempotency_key")
        if idem:
            prior = self.store.get(f"idem/{tenant}/{idem}")
            if prior is not None:
                if prior[1]["digest"] != req_digest:
                    raise PlaneError("PLN04-CONF-002", details={"workload": workload})
                return {**prior[1]["decision"], "request_id": req["request_id"]}

        deadline = self._mono() + req.get("deadline_ms", 30000) / 1000.0
        self.gate.acquire(tenant, deadline, self._mono)
        try:
            with self._wl_lock(workload):
                decision = self._admit_locked(req, command, trace_id, policy_digest, deadline)
        finally:
            self.gate.release()
        if idem:
            try:
                self.store.cas(f"idem/{tenant}/{idem}", 0, {"digest": req_digest, "decision": decision,
                                                            "stored_at": self._wall()})
            except PlaneError:
                pass
        return decision

    def _admit_locked(self, req: dict, command, trace_id: str, policy_digest: str, deadline: float) -> dict:
        workload, tenant, trust_class = req["workload"], req["tenant"], req["trust_class"]
        existing = self.node.instance(workload)
        if existing is not None:
            tier = runtime.admit(self.node, workload, tenant, trust_class)  # reuse / conflict / quarantine rules
            return {"schema": "PK_ADMISSION/1", "kind": "decision", "request_id": req["request_id"],
                    "outcome": "admitted", "tier": tier, "workload": workload, "tenant": tenant}
        stored = self._record(workload)
        if stored is not None and stored[1]["state"] != "terminated":
            if stored[1]["tenant"] != tenant:
                raise PlaneError("PLN04-AUTHZ-002", details={"workload": workload})
            raise PlaneError("PLN04-STATE-004", details={"workload": workload, "state": stored[1]["state"],
                                                         "reason": "prior instance not yet reconciled"})
        try:
            tier = runtime.select_tier(self.node, trust_class)
        except runtime.NoSufficientTier as exc:
            self._audit("admission_refused", workload=workload, tenant=tenant, trust_class=trust_class,
                        minimum_tier=runtime.TRUST_CLASSES[trust_class], attested=self.node.attested())
            raise PlaneError("PLN04-POL-001", details={"workload": workload, "trust_class": trust_class,
                                                       "minimum_tier": runtime.TRUST_CLASSES[trust_class],
                                                       "attested": self.node.attested()}) from exc
        check_coresidency(self.config, tenant, trust_class, tier, self.node.instances.values())
        artifact_digest = req.get("artifact_digest") or ("sha256:" + "0" * 64)
        if self.artifacts is not None:
            self.artifacts.check(req.get("artifact_digest"), tier)
        if len(self.node.instances) >= self.node.max_instances:
            raise PlaneError("PLN04-CAP-001", details={"limit": self.node.max_instances}, retry_after_s=1.0)
        if self.node.tenant_count(tenant) >= self.node.per_tenant_limit:
            raise PlaneError("PLN04-CAP-001", details={"tenant": tenant, "limit": self.node.per_tenant_limit}, retry_after_s=1.0)
        res = req.get("resources", {})
        resources = Resources(res.get("cpu_milli", 1000), res.get("memory_mib", 256))
        self.fair.reserve(tenant, resources.cpu_milli, resources.memory_mib)
        lease = None
        try:
            lease = self.leases.acquire(workload, self.owner_id, LEASE_TTL_S)
            prior_ver = stored[0] if stored else 0
            record = {"workload": workload, "tenant": tenant, "trust_class": trust_class, "tier": tier,
                      "state": "reserved", "epoch": lease.epoch, "policy_digest": policy_digest,
                      "artifact_digest": artifact_digest, "resources": asdict(resources),
                      "owner": self.owner_id, "config_generation": self.config.generation,
                      "created_ns": time.time_ns(), "trace_id": trace_id}
            self.store.cas(f"inst/{workload}", prior_ver, record)
            self._audit("workload_reserved", workload=workload, tenant=tenant, tier=tier, epoch=lease.epoch, trust_class=trust_class)
        except Exception:
            self.fair.release(tenant, resources.cpu_milli, resources.memory_mib)
            if lease is not None:
                self.leases.release(lease)
            raise
        self._leases[workload] = lease

        provider = self.registry.get(tier)
        preq = ProviderRequest(workload=workload, tenant=tenant, tier=tier, policy_digest=policy_digest,
                               artifact_digest=artifact_digest, idempotency_key="pk-" + hashlib.sha256(f"{workload}\x00{lease.epoch}".encode()).hexdigest()[:40],
                               deadline_ns=time.monotonic_ns() + int(max(0.0, deadline - self._mono()) * 1e9),
                               epoch=lease.epoch, resources=resources, command=tuple(command))
        validate(preq.envelope(), "PK_PROVIDER_REQUEST/1")
        try:
            self._transition(workload, "provisioning")
            self._transition(workload, "starting")
            self.leases.validate(lease)
            inst = retry(lambda: self.breakers[tier].call(lambda: provider.start(preq)), self._retry,
                         on_retry=lambda n, e: self.telemetry.inc("pln04_provider_retries", tier=tier))
        except Exception as exc:  # SystemExit/KeyboardInterrupt = crash: left for recover()/reap()
            err = exc if isinstance(exc, PlaneError) else from_exception(exc)
            self._audit("provider_start_failed", workload=workload, tenant=tenant, tier=tier, reason=err.code)
            self._compensate(workload, tenant, resources, lease)
            raise err from (exc if err is not exc else None)
        self._transition(workload, "active", provider=inst.provider, provider_version=inst.provider_version,
                         provider_instance_id=inst.provider_instance_id, started_ns=inst.started_ns)
        self.node.put_instance(runtime.InstanceRecord(workload, tenant, trust_class, tier, "active", lease.epoch))
        self._audit("workload_admitted", workload=workload, tenant=tenant, trust_class=trust_class, tier=tier,
                    epoch=lease.epoch, provider=inst.provider)
        return {"schema": "PK_ADMISSION/1", "kind": "decision", "request_id": req["request_id"], "outcome": "admitted",
                "tier": tier, "workload": workload, "tenant": tenant, "epoch": lease.epoch}

    def _compensate(self, workload: str, tenant: str, resources: Resources, lease) -> None:
        """Failed start: failed -> zeroizing -> terminated; release only after verified zeroization."""
        provider = self.registry.get(self._record(workload)[1]["tier"])
        try:
            self._transition(workload, "failed")
            try:
                provider.stop(workload, lease.epoch)
            except PlaneError:
                pass
            self._transition(workload, "zeroizing")
            receipt = provider.zeroize(workload, lease.epoch)
            if not receipt.verified:
                self._transition(workload, "failed", reason="zeroization unverified")
                return  # resources stay reserved: never reuse unproven-clean resources
            self._transition(workload, "terminated", zeroize_method=receipt.method)
            self.store.delete(f"inst/{workload}", self._record(workload)[0])
        finally:
            rec = self._record(workload)
            if rec is None:
                self.fair.release(tenant, resources.cpu_milli, resources.memory_mib)
                self.leases.release(lease)
                self._leases.pop(workload, None)

    # ------------------------------------------------------------------ teardown (M14/M40)
    def teardown(self, workload: str, tenant: str | None = None, *, token: str | None = None,
                 privileged: bool = False) -> bool:
        runtime._require_identifier(workload, "workload")
        if self.authenticator is not None:
            actor = self.authenticator.authenticate(token)
            authorize(actor, "admission:teardown:privileged" if privileged else "admission:teardown", tenant=tenant)
        if tenant is None and not privileged:
            raise PlaneError("PLN04-AUTHZ-001", details={"reason": "tenant is required unless privileged"})
        with self._wl_lock(workload):
            stored = self._record(workload)
            if stored is None:
                return False
            rec = stored[1]
            if tenant is not None and rec["tenant"] != tenant:
                raise PlaneError("PLN04-AUTHZ-002", details={"workload": workload})
            return self._destroy(workload, rec, reason="teardown", privileged=privileged)

    def _destroy(self, workload: str, rec: dict, *, reason: str, privileged: bool = False) -> bool:
        provider = self.registry.get(rec["tier"])
        epoch = rec["epoch"]
        if rec["state"] in ("active", "quarantined", "orphaned", "failed"):
            self._transition(workload, "stopping")
            self._audit("workload_stopping", workload=workload, tenant=rec["tenant"], tier=rec["tier"], epoch=epoch)
            try:
                provider.stop(workload, epoch)
            except PlaneError as exc:
                self._transition(workload, "failed", reason=exc.code)
                raise
            self._transition(workload, "zeroizing")
        elif rec["state"] in ("reserved", "provisioning", "starting"):
            self._transition(workload, "failed")
            self._transition(workload, "zeroizing")
        elif rec["state"] == "stopping":
            self._transition(workload, "zeroizing")
        receipt = provider.zeroize(workload, epoch)
        if not receipt.verified:
            self._transition(workload, "failed", reason="zeroization unverified")
            self._audit("workload_quarantined", workload=workload, tenant=rec["tenant"], tier=rec["tier"],
                        reason="zeroization unverified: resources withheld from reuse")
            raise PlaneError("PLN04-PROV-003", details={"workload": workload, "provider": provider.name})
        self._transition(workload, "terminated", zeroize_method=receipt.method)
        self._audit("workload_zeroized", workload=workload, tenant=rec["tenant"], tier=rec["tier"], reason=receipt.method)
        self.store.delete(f"inst/{workload}", self._record(workload)[0])
        self.node.drop_instance(workload)
        res = rec.get("resources", {})
        self.fair.release(rec["tenant"], res.get("cpu_milli", 0), res.get("memory_mib", 0))
        lease = self._leases.pop(workload, None)
        if lease is not None:
            self.leases.release(lease)
        self._audit("workload_torn_down", workload=workload, tenant=rec["tenant"], tier=rec["tier"],
                    prior_state=rec["state"], privileged=privileged, reason=reason)
        return True

    # ------------------------------------------------------------------ recovery / reaper / drain (M11/M14)
    def recover(self) -> dict:
        """Startup reconciliation.  Never resumes execution from memory: an instance is
        ``active`` again only if its provider confirms it running *and* its tier is attested;
        everything else becomes ``orphaned`` for the reaper."""
        summary = {"active": 0, "orphaned": 0}
        for key, ver, rec in list(self.store.items("inst/")):
            wl = rec["workload"]
            provider = self.registry.get(rec["tier"])
            running = provider.observe(wl) == "running"
            if rec["state"] == "active" and running and rec["tier"] in self.node.attested():
                self.node.put_instance(runtime.InstanceRecord(wl, rec["tenant"], rec["trust_class"], rec["tier"], "active", rec["epoch"]))
                res = rec.get("resources", {})
                self.fair.reserve(rec["tenant"], res.get("cpu_milli", 1), res.get("memory_mib", 1))
                summary["active"] += 1
            elif rec["state"] not in ("terminated", "orphaned", "failed", "zeroizing", "stopping"):
                if "orphaned" in LIFECYCLE.get(rec["state"], ()):
                    self._transition(wl, "orphaned")
                else:
                    self._transition(wl, "failed", reason="recovered mid-transition")
                summary["orphaned"] += 1
            else:
                summary["orphaned"] += 1
        self._audit("state_recovered", reason=json.dumps(summary, sort_keys=True))
        return summary

    def reap(self) -> dict:
        """Destroy orphaned/failed instances and provider resources unknown to the store."""
        reaped, stuck = [], []
        for _, _, rec in list(self.store.items("inst/")):
            if rec["state"] in ("orphaned", "failed", "stopping", "zeroizing"):
                with self._wl_lock(rec["workload"]):
                    try:
                        self._destroy(rec["workload"], rec, reason="reaper", privileged=True)
                        reaped.append(rec["workload"])
                    except PlaneError:
                        stuck.append(rec["workload"])
        for tier in self.registry.tiers():
            provider = self.registry.get(tier)
            for inst in provider.list_instances():
                if self._record(inst.workload) is None:
                    try:
                        provider.stop(inst.workload, inst.epoch)
                        receipt = provider.zeroize(inst.workload, inst.epoch)
                        (reaped if receipt.verified else stuck).append(inst.workload)
                        self._audit("orphan_reaped", workload=inst.workload, tier=tier, reason="unknown to state store")
                    except PlaneError:
                        stuck.append(inst.workload)
        self.telemetry.gauge("pln04_reaper_stuck", len(stuck))
        return {"reaped": sorted(reaped), "stuck": sorted(stuck), "idempotency_pruned": self.prune_idempotency()}

    def prune_idempotency(self, max_age_s: float = IDEMPOTENCY_TTL_S) -> int:
        """Idempotency records are retained for ``max_age_s`` (retry horizon), then dropped."""
        cutoff, pruned = self._wall() - max_age_s, 0
        for key, ver, rec in list(self.store.items("idem/")):
            if rec.get("stored_at", 0) < cutoff:
                try:
                    self.store.delete(key, ver)
                    pruned += 1
                except PlaneError:
                    pass
        return pruned

    def drain(self, reason: str = "node drain") -> dict:
        self.rollout.emergency_disable(reason)
        self._audit("node_drain_started", reason=reason)
        done, failed = [], []
        for _, _, rec in list(self.store.items("inst/")):
            try:
                with self._wl_lock(rec["workload"]):
                    cur = self._record(rec["workload"])
                    if cur is not None:
                        self._destroy(rec["workload"], cur[1], reason="drain", privileged=True)
                done.append(rec["workload"])
            except PlaneError:
                failed.append(rec["workload"])
        return {"drained": sorted(done), "failed": sorted(failed)}

    def emergency_disable(self, reason: str) -> None:
        self.rollout.emergency_disable(reason)
        self._audit("admission_disabled", reason=reason)

    def auto_rollback(self, *, max_error_ratio: float = 0.2, min_requests: int = 50) -> str | None:
        """M30 - automated rollback: disable admissions when the latency SLO is breached or the
        provider/dependency error ratio exceeds ``max_error_ratio``.  Returns the reason or None."""
        snap = self.telemetry.snapshot()["counters"]
        ok = sum(v for k, v in snap.items() if k.startswith("pln04_admissions{"))
        bad = sum(v for k, v in snap.items() if k.startswith("pln04_admission_errors{")
                  and any(c in k for c in ("PROV-", "DEP-", "TIME-", "INT-")))
        reason = None
        if self.slo.evaluate(self.telemetry.histogram("pln04_admission_latency_ms"))["status"] == "BREACHED":
            reason = "latency SLO breached"
        elif ok + bad >= min_requests and bad / (ok + bad) > max_error_ratio:
            reason = f"error ratio {bad / (ok + bad):.2f} > {max_error_ratio}"
        if reason and self.rollout.stage != "disabled":
            self.emergency_disable(f"auto-rollback: {reason}")
        return reason

    def enable(self, stage: str = "full", canary_tenants=()) -> None:
        self.rollout.set_stage(stage, canary_tenants)
        self._audit("admission_enabled", reason=stage)

    # ------------------------------------------------------------------ read APIs (M20)
    def catalogue(self) -> dict:
        doc = {"schema": "PK_TIER_CATALOGUE/1", "node_id": self.config["node_id"], "generation": 0,
               "tiers": dict(self.node.catalogue())}
        validate(doc, "PK_TIER_CATALOGUE/1")
        return doc

    def health(self) -> dict:
        checks = {
            "state_store": bool(self.store.healthy()),
            "attested_tier": bool(self.node.attested()),
            "admission_enabled": self.rollout.stage != "disabled",
            "providers_closed": all(b.state != "open" for b in self.breakers.values()),
        }
        if self.exporter is not None:
            checks["export_backlog_ok"] = self.exporter.pending() < 10000
        return {"live": True, "ready": all(checks.values()), "checks": checks,
                "slo": self.slo.evaluate(self.telemetry.histogram("pln04_admission_latency_ms"))}

    def explain(self, workload: str) -> dict:
        """Why is this workload where it is?  Record + policy floor + attested tiers."""
        stored = self._record(workload)
        rec = None if stored is None else stored[1]
        out = {"workload": workload, "record": rec, "attested_tiers": self.node.attested(),
               "config_generation": self.config.generation}
        if rec:
            out["policy_floor"] = runtime.TRUST_CLASSES[rec["trust_class"]]
            out["reason"] = (f"trust class {rec['trust_class']!r} requires >= {out['policy_floor']!r}; "
                             f"weakest attested sufficient tier at admission was {rec['tier']!r}")
        return out
