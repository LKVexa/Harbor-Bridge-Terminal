"""INV-45 service facade: submit -> rewrite -> verify -> seal -> trusted load -> execute.

The trusted loader (``SfiService.load``) is the only path from bytes to an
executable instance.  It accepts nothing but a sealed descriptor plus the exact
bytes, and it re-establishes every binding at load time (TOCTOU closure, C044):

1. authenticate caller; authenticate descriptor MAC + expiry;
2. capability ``sfi.load`` bound to the descriptor's tenant and artifact digest;
3. one-time descriptor nonce (replay);
4. SHA-256 of the presented bytes == descriptor digest;
5. profile digest and config digest == the *currently active* ones;
6. quarantine (global / tenant / artifact);
7. anti-rollback floor per workload;
8. defence in depth: independent re-verification of the bytes, and proof digest match.

Any failure is a stable ``SfiError``; nothing partially trusted is retained.
"""
from __future__ import annotations

import io
import secrets as _secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import config as cfgmod
from . import sfi, trust
from .audit import AuditLog
from .authz import CAPABILITIES, Authorizer, IdentityProvider, Principal, ReplayCache
from .controls import Admission, CircuitBreaker, Deadline, DurableState, Lifecycle
from .errors import SfiError
from .telemetry import Explainer, Logger, Metrics, Trace

SERVICE_VERSION = "4.3.0"


@dataclass
class Loaded:
    handle: str
    tenant: str
    workload: str
    artifact_sha256: str
    artifact: bytes
    proof: dict[str, Any]
    lifecycle: Lifecycle = field(default_factory=lambda: Lifecycle("SEALED"))


class SfiService:
    def __init__(self, *, root: Path, keyring: trust.KeyRing, trust_store: trust.ArtifactTrustStore,
                 idp: IdentityProvider, engine: Any = None, owner: str = "inv45-controller",
                 log_stream: Any = None, generation_store: Optional[cfgmod.GenerationStore] = None):
        self.root = Path(root)
        self.keyring = keyring
        self.trust_store = trust_store
        self.idp = idp
        self.engine = engine
        self.gens = generation_store or cfgmod.GenerationStore(self.root / "config")
        self.gens.recover()
        self.audit = AuditLog(self.root / "audit" / "audit.jsonl")
        self.state = DurableState(self.root / "state", owner)
        self.metrics = Metrics()
        self.log = Logger(stream=log_stream or io.StringIO())
        self.explainer = Explainer()
        self.authz = Authorizer(audit=lambda e: self.audit.emit(e) if not e["allowed"] else None)
        self.replay = ReplayCache()
        self.instances: dict[str, Loaded] = {}
        self._lock = threading.Lock()
        self.engine_breaker = CircuitBreaker("node-v8", threshold=3, cooldown=30.0)
        self._verify_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._reload()

    # ------------------------------------------------------------------ configuration
    def _reload(self) -> None:
        self.generation, self.cfg = self.gens.active()
        self.cfg_digest = cfgmod.digest(self.cfg)
        self.profile = cfgmod.profile(self.cfg)
        self.limits = cfgmod.limits(self.cfg)
        a = self.cfg["admission"]
        self.admission = Admission(a["max_concurrent"], a["max_per_tenant"], a["max_queue"])
        self.keyring.max_age_seconds = float(self.cfg["trust"]["trust_max_age_seconds"])
        self._verify_cache.clear()

    def activate_config(self, token: str, cfg: dict[str, Any], *, approval: Optional[str] = None) -> int:
        p = self._auth(token, "sfi.policy.write")
        try:
            n = self.gens.activate(cfg, author=p.subject, source="api", approval=approval,
                                   expected_current=self.generation)
        except SfiError as e:
            self.audit.emit({"event": "config.activate", "outcome": "rejected", "code": e.code, "subject": p.subject})
            raise
        self._reload()
        self.audit.emit({"event": "config.activate", "outcome": "ok", "generation": n, "subject": p.subject,
                         "config_sha256": self.cfg_digest})
        return n

    def rollback_config(self, token: str, to_generation: int, reason: str) -> int:
        p = self._auth(token, "sfi.policy.write")
        n = self.gens.rollback(to_generation, author=p.subject, reason=reason)
        self._reload()
        self.audit.emit({"event": "config.rollback", "outcome": "ok", "generation": n, "subject": p.subject,
                         "reason": reason, "config_sha256": self.cfg_digest})
        return n

    # ------------------------------------------------------------------ helpers
    def _auth(self, token: Any, cap: str, *, tenant: Optional[str] = None,
              digest: Optional[str] = None) -> Principal:
        try:
            p = self.idp.authenticate(token)
        except SfiError as e:
            self.audit.emit({"event": "authn.failed", "outcome": "denied", "code": e.code, "capability": cap})
            self.metrics.inc("sfi_authn_failures")
            raise
        self.authz.check(p, cap, tenant=tenant, artifact_sha256=digest)
        return p

    def _decide(self, decision: str, outcome: str, constraint: str, trace: Trace, **inputs: Any) -> str:
        return self.explainer.record(
            decision=decision, outcome=outcome, constraint=constraint, trace=trace, inputs=inputs,
            policy={"profile_sha256": self.profile.digest(), "config_sha256": self.cfg_digest,
                    "generation": self.generation},
            topology={"node": self.log.node, "engine": "node-v8" if self.engine else "none",
                      "service_version": SERVICE_VERSION})

    def _blocked(self, tenant: str, digest: str, *, for_execute: bool = False) -> None:
        q = self.state.blocked(tenant, digest)
        if q and (not for_execute or q["action"] == "disable"):
            raise SfiError("SFI_QUARANTINED", "target is quarantined", scope=q["scope"], reason=q["reason"],
                           tenant=tenant)

    # ------------------------------------------------------------------ submit
    def submit(self, token: str, artifact: bytes, *, tenant: str, workload: str, version: int,
               signed_statement: dict[str, Any], traceparent: Optional[str] = None) -> dict[str, Any]:
        trace = Trace.from_header(traceparent)
        t0 = time.perf_counter()
        p = self._auth(token, "sfi.submit", tenant=tenant)
        lc = Lifecycle()
        try:
            with self.admission.slot(tenant):
                self._blocked(tenant, sfi.sha256_hex(bytes(artifact)) if isinstance(artifact, (bytes, bytearray)) else "")
                st = self.trust_store.verify_statement(bytes(artifact), signed_statement)
                if st["workload"] != workload or st["version"] != version:
                    raise SfiError("SFI_SIGNATURE_INVALID", "signed statement does not bind this workload/version",
                                   workload=workload)
                floor = int(self.state.read()["floors"].get(workload, 0))
                if version < floor:
                    raise SfiError("SFI_ROLLBACK_REJECTED", "version below anti-rollback floor", floor=floor,
                                   observed_version=version, workload=workload)
                rw = sfi.rewrite(bytes(artifact), self.profile, self.limits)
                lc.to("VALIDATED", "parsed+type-validated")
                proof = sfi.verify(rw.artifact, self.profile, self.limits)
                lc.to("VERIFIED", "independent verifier")
                pd = sfi.proof_digest(proof)
                desc = trust.seal(self.keyring, proof=proof, proof_sha256=pd, config_sha256=self.cfg_digest,
                                  tenant=tenant, workload=workload, artifact_version=version,
                                  ttl_seconds=float(self.cfg["trust"]["descriptor_ttl_seconds"]))
                lc.to("SEALED", "descriptor issued")
        except SfiError as e:
            if lc.state != "REJECTED":
                lc.state = "REJECTED"
            self.metrics.inc("sfi_modules_loaded", outcome="rejected", code=e.code)
            if e.code == "SFI_UNMASKED_ACCESS":
                self.metrics.inc("sfi_unmasked_accesses", float(e.details.get("unmasked_count", 1)))
            did = self._decide("submit", "rejected", e.code, trace, tenant=tenant, workload=workload)
            self.audit.emit({"event": "submit", "outcome": "rejected", "code": e.code, "tenant": tenant,
                             "workload": workload, "subject": p.subject, "trace_id": trace.trace_id})
            self.log.log("warning", "submit", trace, outcome="rejected", code=e.code, tenant=tenant)
            e.details["target"] = did
            raise
        ms = (time.perf_counter() - t0) * 1000
        self.metrics.inc("sfi_modules_verified", outcome="ok")
        self.metrics.observe_ms("sfi_submit_latency_ms", ms)
        did = self._decide("submit", "sealed", "all accesses confined; policy satisfied", trace, tenant=tenant,
                           workload=workload, artifact_sha256=proof["artifact_sha256"])
        self.audit.emit({"event": "submit", "outcome": "sealed", "tenant": tenant, "workload": workload,
                         "artifact_sha256": proof["artifact_sha256"], "proof_sha256": pd,
                         "profile_sha256": proof["profile_sha256"], "config_sha256": self.cfg_digest,
                         "subject": p.subject, "trace_id": trace.trace_id, "artifact_version": version,
                         "rewritten_accesses": rw.rewritten_accesses, "duration_ms": round(ms, 3)})
        self.log.log("info", "submit", trace, outcome="sealed", tenant=tenant, workload=workload,
                     artifact_sha256=proof["artifact_sha256"])
        return {"artifact": rw.artifact, "descriptor": desc, "proof": proof, "rewrite": rw.as_dict(),
                "decision_id": did, "traceparent": trace.header()}

    # ------------------------------------------------------------------ trusted loader
    def load(self, token: str, artifact: bytes, descriptor: dict[str, Any],
             traceparent: Optional[str] = None) -> str:
        trace = Trace.from_header(traceparent)
        subject = None
        try:
            body = trust.open_descriptor(self.keyring, descriptor)
            tenant, digest = body["tenant"], body["artifact_sha256"]
            p = self._auth(token, "sfi.load", tenant=tenant, digest=digest)
            subject = p.subject
            if not isinstance(artifact, (bytes, bytearray)):
                raise SfiError("SFI_SCHEMA_INVALID", "artifact must be bytes", field="artifact")
            artifact = bytes(artifact)
            actual = sfi.sha256_hex(artifact)
            if actual != digest:
                raise SfiError("SFI_DIGEST_MISMATCH", "artifact bytes differ from sealed digest",
                               artifact_sha256=actual, expected_sha256=digest)
            if body["profile_sha256"] != self.profile.digest():
                raise SfiError("SFI_SEAL_MISMATCH", "descriptor sealed under a different profile",
                               reason="profile changed; re-verify")
            if body["config_sha256"] != self.cfg_digest:
                raise SfiError("SFI_SEAL_MISMATCH", "descriptor sealed under a different config generation",
                               reason="config changed; re-verify")
            self._blocked(tenant, digest)
            self.replay.consume(body["nonce"], body["expires_at"])
            key = (digest, body["profile_sha256"])
            proof = self._verify_cache.get(key)
            if proof is None:
                proof = sfi.verify(artifact, self.profile, self.limits)
                self._verify_cache[key] = proof
            if sfi.proof_digest(proof) != body["proof_sha256"]:
                raise SfiError("SFI_SEAL_MISMATCH", "proof digest differs from sealed proof")
            self.state.enforce_floor(body["workload"], int(body["artifact_version"]))
        except SfiError as e:
            self.metrics.inc("sfi_loads", outcome="rejected", code=e.code)
            self.audit.emit({"event": "load", "outcome": "rejected", "code": e.code, "subject": subject,
                             "trace_id": trace.trace_id})
            self._decide("load", "rejected", e.code, trace)
            raise
        handle = "h_" + _secrets.token_hex(8)
        ld = Loaded(handle, tenant, body["workload"], digest, artifact, proof)
        ld.lifecycle.to("LOADED", "trusted loader")
        with self._lock:
            self.instances[handle] = ld
        self.metrics.inc("sfi_loads", outcome="ok")
        self.audit.emit({"event": "load", "outcome": "ok", "tenant": tenant, "artifact_sha256": digest,
                         "subject": subject, "trace_id": trace.trace_id})
        self._decide("load", "loaded", "descriptor, digest, profile, config, quarantine, floor all bound",
                     trace, tenant=tenant, artifact_sha256=digest)
        return handle

    # ------------------------------------------------------------------ execute
    def execute(self, token: str, handle: str, calls: list[dict[str, Any]], *, memory_pages: Optional[int] = None,
                traceparent: Optional[str] = None) -> dict[str, Any]:
        trace = Trace.from_header(traceparent)
        ld = self.instances.get(handle)
        if ld is None:
            raise SfiError("SFI_NOT_VERIFIED", "unknown or unloaded handle", target=handle[:32])
        p = self._auth(token, "sfi.execute", tenant=ld.tenant, digest=ld.artifact_sha256)
        self._blocked(ld.tenant, ld.artifact_sha256, for_execute=True)
        if self.engine is None:
            raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "no execution engine configured", dependency="engine")
        imported = bool(ld.proof["memory"] and ld.proof["memory"]["imported"])
        pages = memory_pages or (ld.proof["memory"]["min_pages"] if imported else 0)
        job = {"modules": [{"name": "m", "bytes": ld.artifact, "allow": ld.proof["function_imports"]}],
               "memory_pages": pages if imported else 0,
               "calls": [{"module": "m", **c} for c in calls]}
        with self.admission.slot(ld.tenant):
            ld.lifecycle.to("RUNNING", "execute")
            try:
                out = self.engine_breaker.call(lambda: self.engine.run(job))
            finally:
                ld.lifecycle.to("LOADED", "execute done")
        self.metrics.inc("sfi_executions", outcome="ok")
        self.audit.emit({"event": "execute", "outcome": "ok", "tenant": ld.tenant, "subject": p.subject,
                         "artifact_sha256": ld.artifact_sha256, "trace_id": trace.trace_id})
        return out

    def stop(self, token: str, handle: str) -> None:
        ld = self.instances.get(handle)
        if ld is None:
            return
        self._auth(token, "sfi.execute", tenant=ld.tenant, digest=ld.artifact_sha256)
        ld.lifecycle.to("STOPPED", "operator stop")
        with self._lock:
            self.instances.pop(handle, None)

    # ------------------------------------------------------------------ quarantine
    def quarantine(self, token: str, scope: str, target: str, action: str, reason: str,
                   second_token: Optional[str] = None) -> None:
        a = self.idp.authenticate(token)
        approvers = [a.subject]
        if scope == "global":
            if second_token is None:
                raise SfiError("SFI_DUAL_AUTH_REQUIRED", "global quarantine needs two approvers", scope=scope)
            b = self.idp.authenticate(second_token)
            self.authz.check_dual(a, b, "sfi.quarantine")
            approvers.append(b.subject)
            target = "*"
        else:
            self.authz.check(a, "sfi.quarantine", tenant=target if scope == "tenant" else None)
        self.state.set_quarantine(scope, target, action, reason, approvers)
        with self._lock:
            for h, ld in list(self.instances.items()):
                hit = scope == "global" or (scope == "tenant" and ld.tenant == target) or \
                      (scope == "artifact" and ld.artifact_sha256 == target)
                if hit and action == "disable":
                    ld.lifecycle.to("QUARANTINED", reason[:64])
                    ld.lifecycle.to("STOPPED", "disabled")
                    del self.instances[h]
        self.audit.emit({"event": "quarantine", "action": action, "scope": scope, "target": target,
                         "reason": reason, "approvers": approvers, "outcome": "ok"})
        self.metrics.inc("sfi_quarantine_actions", action=action, scope=scope)

    def release(self, token: str, scope: str, target: str, second_token: Optional[str] = None) -> bool:
        a = self.idp.authenticate(token)
        if scope == "global":
            if second_token is None:
                raise SfiError("SFI_DUAL_AUTH_REQUIRED", "global release needs two approvers", scope=scope)
            self.authz.check_dual(a, self.idp.authenticate(second_token), "sfi.quarantine")
            target = "*"
        else:
            self.authz.check(a, "sfi.quarantine", tenant=target if scope == "tenant" else None)
        gone = self.state.release(scope, target)
        self.audit.emit({"event": "quarantine.release", "scope": scope, "target": target, "outcome": "ok",
                         "subject": a.subject})
        return gone

    # ------------------------------------------------------------------ health
    def health(self) -> dict[str, Any]:
        deps: dict[str, str] = {}
        try:
            self.keyring._fresh()
            deps["key_service"] = "ok" if self.keyring.active else "no-active-key"
        except SfiError:
            deps["key_service"] = "stale"
        deps["engine"] = "absent" if self.engine is None else self.engine_breaker.state
        deps["audit_sink"] = "ok" if not self.audit.spool else f"spooling:{len(self.audit.spool)}"
        q = self.state.read()["quarantine"]
        if "global:*" in q:
            status = "quarantined"
        elif deps["key_service"] == "stale":
            status = "dependency_stale"
        elif deps["key_service"] != "ok" or deps["engine"] in ("open",) or deps["audit_sink"] != "ok":
            status = "degraded"
        else:
            status = "ready"
        return {"schema": "PK_SFI_HEALTH/1", "status": status, "alive": True, "ready": status == "ready",
                "version": SERVICE_VERSION, "profile_id": self.profile.profile_id,
                "profile_sha256": self.profile.digest(), "config_generation": self.generation,
                "config_sha256": self.cfg_digest, "dependencies": deps,
                "capabilities": sorted(CAPABILITIES),
                "quarantine_entries": len(q), "instances": len(self.instances),
                "admission": self.admission.snapshot()}
