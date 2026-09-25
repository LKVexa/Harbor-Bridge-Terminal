"""The production path: one service that ties every control together.

``SandboxService.launch()`` order (each step fails closed):

  authenticate -> authorize(launch) -> quarantine check -> payload limits ->
  offline/dependency check -> profile validation (policy) -> admission/quota ->
  lease -> lifecycle CREATED->APPLYING -> native launcher applies controls ->
  VERIFYING: kernel read-back must match -> READY -> sign PK_SANDBOX_APPLIED/2
  evidence -> audit + reason -> release gate -> RUNNING -> wait/timeout ->
  TERMINATING -> CLEANED -> admission release -> metrics/logs.
"""
from __future__ import annotations

import io
import os
import time
from dataclasses import dataclass
from typing import Any

from . import __version__
from .attestation import AuditChain, EvidenceSigner, NodeIdentity, digest, new_nonce
from .backends import probe, require
from .config import validate as validate_config
from .control import Admission, Authorizer, IdempotencyCache, LeaseTable, Limits, Quarantine, authenticate
from .errors import SandboxError
from .lifecycle import Lifecycle
from .linux import launcher as L
from .linux.primitives import CAPS
from .observability import Diagnostics, Logger, Metrics, Reasons, new_traceparent, trace_id
from .sandbox import SYSCALL_BUDGET, SandboxProfile

RELEASE_DIGEST_ENV = "INV39_RELEASE_DIGEST"


@dataclass
class LaunchRequest:
    token: str
    tenant: str
    workload: str
    profile: SandboxProfile
    argv: tuple[str, ...]
    env: dict[str, str] | None = None
    env_allow: frozenset[str] = frozenset()
    run_as: tuple[int, int] | None = None
    idempotency_key: str | None = None
    traceparent: str | None = None
    landlock_ro: tuple[str, ...] = ()
    landlock_rw: tuple[str, ...] = ()
    timeout_s: float | None = None
    stdio: tuple[int, int, int] | None = None


class SandboxService:
    AUDIENCE = "inv39.sandbox"

    def __init__(self, *, identity: NodeIdentity, principal_keys: dict[str, bytes], authz: Authorizer,
                 config: dict[str, Any] | None = None, audit_path: str | None = None, log_stream=None,
                 dependencies_online=lambda: True):
        self.identity = identity
        self.keys = principal_keys
        self.authz = authz
        self.config = validate_config(config or {})
        self.config_digest = digest(self.config)
        self.audit = AuditChain(audit_path)
        self.signer = EvidenceSigner(identity)
        self.metrics = Metrics()
        self.log = Logger(log_stream or io.StringIO(), node=identity.node_id)
        self.diag = Diagnostics(self.config["telemetry"]["sample_rate"])
        self.reasons = Reasons(self.audit)
        self.quarantine = Quarantine(authz, self.audit)
        self.admission = Admission(Limits(max_concurrent=self.config["max_concurrent"],
                                          max_per_tenant=self.config["max_per_tenant"],
                                          max_queue=self.config["max_queue"]))
        self.leases = LeaseTable()
        self.idem = IdempotencyCache()
        self.dependencies_online = dependencies_online
        self.started_at = time.time()
        self.release_digest = os.environ.get(RELEASE_DIGEST_ENV, "unreleased-dev-build")
        self.features = probe()
        self.active: dict[str, Lifecycle] = {}

    # ------------------------------------------------------------ status (MC-075)
    def status(self) -> dict[str, Any]:
        try:
            require(self.features, need_userns=self.config["require_userns"],
                    need_landlock=self.config["require_landlock"])
            ready, why = True, []
        except SandboxError as e:
            ready, why = False, [e.message]
        deps = bool(self.dependencies_online())
        return {"schema": "PK_SANDBOX_STATUS/1", "version": __version__, "node": self.identity.node_id,
                "healthy": True, "ready": ready and deps, "not_ready_reasons": why + ([] if deps else ["dependencies offline"]),
                "config_digest": self.config_digest, "release_digest": self.release_digest,
                "backend": self.config["backend"], "features": self.features,
                "active_controls": ["seccomp-bpf", "no_new_privs", "capabilities", "namespaces", "rlimits",
                                    "fd-closure", "env-sanitization", "mount-private"]
                + (["landlock"] if self.features.get("landlock_abi") else []),
                "active_sandboxes": len(self.active), "audit_head": self.audit.head,
                "uptime_s": round(time.time() - self.started_at, 3)}

    # ------------------------------------------------------------ launch
    def launch(self, req: LaunchRequest) -> dict[str, Any]:
        tp = new_traceparent(req.traceparent)
        if req.idempotency_key:
            return self.idem.run(req.idempotency_key,
                                 {"t": req.tenant, "w": req.workload, "p": req.profile.digest, "a": req.argv},
                                 lambda: self._launch(req, tp))
        return self._launch(req, tp)

    def _refuse(self, e: SandboxError, req: LaunchRequest, tp: str, kind="rejection"):
        self.metrics.inc("errors", {"code": e.code})
        if e.code in ("E_PROFILE_INVALID", "E_NOT_APPLIED", "E_APPLY_FAILED"):
            self.metrics.inc("profile_failures", {"code": e.code, "profile": req.profile.name})
        self.reasons.record(kind, "refused", subject=f"{req.tenant}/{req.workload}", code=e.code,
                            because=[e.message], profile_digest=req.profile.digest, config_digest=self.config_digest)
        self.log.log("warn", "launch refused", tenant=req.tenant, workload=req.workload, operation="launch",
                     trace=tp, code=e.code, detail=e.message)
        return e

    def _launch(self, req: LaunchRequest, tp: str) -> dict[str, Any]:
        sid = f"{self.identity.node_id}/{req.tenant}/{req.workload}/{new_nonce()[:12]}"
        admitted = False
        lc = Lifecycle(sid)
        try:
            principal = authenticate(self.keys, req.token, self.AUDIENCE)
            self.authz.check(principal, "launch", req.tenant)
            self.quarantine.check(req.tenant, f"{req.tenant}/{req.workload}", self.identity.node_id)
            if not self.dependencies_online() and self.config["offline_mode"] == "refuse":
                raise SandboxError("E_DEPENDENCY_UNAVAILABLE", "control-plane dependencies offline; refusing (MC-009)")
            defects = req.profile.validate()
            if len(req.profile.syscalls) > self.config["syscall_budget"]:
                defects.append(f"allow-list {len(req.profile.syscalls)} exceeds budget {self.config['syscall_budget']}")
            if defects:
                raise SandboxError("E_PROFILE_INVALID", "; ".join(defects))
            require(self.features, need_userns=self.config["require_userns"],
                    need_landlock=self.config["require_landlock"] or bool(req.landlock_ro or req.landlock_rw))
            self.admission.acquire(req.tenant)
            admitted = True
            fence = self.leases.acquire(sid, self.identity.node_id)
            self.active[sid] = lc
            lc.to("APPLYING", "admitted")
            spec = L.LaunchSpec(argv=tuple(req.argv), syscalls=req.profile.syscalls,
                                capabilities=req.profile.capabilities, namespaces=req.profile.namespaces,
                                env=dict(req.env or {}), env_allow=req.env_allow,
                                rlimits=dict(self.config["rlimits"]), run_as=req.run_as,
                                deny_action=self.config["deny_action"], stdio=req.stdio,
                                landlock_ro=req.landlock_ro, landlock_rw=req.landlock_rw,
                                timeout_s=req.timeout_s or self.config["default_timeout_s"])
            record: dict[str, Any] = {}

            def on_ready(pid, ev):
                lc.to("VERIFYING", "controls applied; kernel read-back collected")
                self.leases.check(sid, self.identity.node_id, fence)
                lc.to("READY", "read-back matches profile")
                rb = ev["kernel_read_back"]
                body = {
                    "schema": "PK_SANDBOX_APPLIED/2", "sandbox_id": sid, "tenant": req.tenant,
                    "workload": req.workload, "process": str(pid), "profile": req.profile.name,
                    "profile_digest": req.profile.digest, "config_digest": self.config_digest,
                    "release_digest": self.release_digest, "nonce": new_nonce(), "verified": True,
                    "verification_scope": "kernel_read_back_before_exec",
                    "evidence_source": "kernel_read_back",
                    "os_enforcement_proven": True,
                    "launcher_attested": {"seccomp_program_digest": ev["seccomp_program_digest"],
                                          "seccomp_rule_contents": "not readable via /proc (MC-047)",
                                          "landlock": bool(req.landlock_ro or req.landlock_rw)},
                    "default_deny": True, "residual_syscalls": len(req.profile.syscalls),
                    "within_budget": len(req.profile.syscalls) <= SYSCALL_BUDGET,
                    "capabilities_retained": sorted(c for c in CAPS if rb["cap_eff"] >> CAPS.index(c) & 1),
                    "namespaces": rb["namespaces_new"], "kernel": {k: rb[k] for k in (
                        "no_new_privs", "seccomp_mode", "seccomp_filters", "cap_eff", "cap_prm", "cap_inh",
                        "cap_bnd", "cap_amb", "fds", "rlimits", "net_interfaces", "shared_mount_propagation")},
                    "shares_kernel": True,
                    "isolation_note": ("process-level only: a kernel bug reached through any of the "
                                       f"{len(req.profile.syscalls)} allowed syscalls defeats this tier"),
                    "trace_id": trace_id(tp)}
                record.update(self.signer.sign(body))
                self.audit.append("applied", {"sandbox_id": sid, "evidence_digest": digest(record)})
                lc.to("RUNNING", "gate released to execve")

            t0 = time.monotonic()
            try:
                res = L.launch(spec, on_ready=on_ready)
            except SandboxError:
                if lc.state not in ("FAILED", "CLEANED"):
                    lc.to("FAILED", "launcher refused")
                raise
            self.metrics.observe("launch_seconds", time.monotonic() - t0, {"profile": req.profile.name})
            lc.to("TERMINATING", "timeout" if res.timed_out else "workload exited")
            lc.to("CLEANED", "tree reaped")
            self.metrics.inc("sandbox_starts", {"profile": req.profile.name, "outcome": "ok"})
            self.metrics.set("residual_syscalls", {"profile": req.profile.name}, len(req.profile.syscalls))
            self.metrics.set("retained_capabilities", {"profile": req.profile.name}, len(req.profile.capabilities))
            self.reasons.record("termination", "timeout-kill" if res.timed_out else "exited", subject=sid,
                                code="E_TIMEOUT" if res.timed_out else None,
                                because=[f"exit={res.exit_code} signal={res.signal}"],
                                profile_digest=req.profile.digest, evidence=digest(record))
            self.log.log("info", "sandbox finished", tenant=req.tenant, workload=req.workload,
                         operation="launch", trace=tp, exit_code=res.exit_code, timed_out=res.timed_out)
            return {"outcome": "success" if res.exit_code == 0 else "partial", "sandbox_id": sid,
                    "exit_code": res.exit_code, "signal": res.signal, "timed_out": res.timed_out,
                    "evidence": record, "lifecycle": [h[2] for h in lc.history], "traceparent": tp}
        except SandboxError as e:
            if lc.state not in ("FAILED", "CLEANED"):
                lc.to("FAILED", e.code)
            if lc.state == "FAILED":
                lc.to("CLEANED", "nothing ran")
            self.metrics.inc("sandbox_starts", {"profile": req.profile.name, "outcome": e.code})
            raise self._refuse(e, req, tp)
        finally:
            self.active.pop(sid, None)
            if admitted:
                self.admission.release(req.tenant, ok=lc.state == "CLEANED" and "FAILED" not in
                                       [h[2] for h in lc.history])
