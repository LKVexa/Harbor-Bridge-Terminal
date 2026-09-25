"""INV-26 snapshot service: the complete secure capture/restore path (X001-X012).

Order of checks for **restore** (each refusal happens before any later side effect):

 1. emergency-disable switch                                  (C059)
 2. request schema + interface limits                         (C022, C028)
 3. caller authentication (aud/env/site/exp/kid/alg)          (C023, C044)
 4. deployment-tier applicability + residency                 (C012, C019)
 5. capability authorization, scope-bound to request tenant   (C024)
 6. restore grant: signature, audience=node, fields bound to
    the request, manifest digest + generation current         (X008)
 7. grant consumption (durable CAS; replay -> refused,
    same-idempotency-key retry -> recorded result)            (C025, C058)
 8. admission control (rate, fairness, queue, inflight)       (C017, C054)
 9. snapshot state (AVAILABLE; QUARANTINED refused)           (C015, C059)
10. tenant/workload/environment + device-model binding       (v5 baseline)
11. blob fetch + ciphertext digest + AEAD per chunk + DEK
    unwrap bound to the security context                      (C047, X009)
12. hypervisor load with the guest PAUSED                     (X001)
13. fresh 256-bit seed -> injector must acknowledge           (X002)
14. resume -> READY; any failure in 12-14 destroys the guest  (C014)

Every outcome -> stable code, audit event, metrics, structured log, decision
record. Nothing below the public boundary leaks exception text.
"""
from __future__ import annotations

import hashlib
import secrets
import shutil
import tempfile
import threading
import time
import uuid
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from . import __version__
from . import crypto, lifecycle, policy, schema
from .audit import AuditLog, AuditUnavailable
from .auth import Authenticator, Principal, authorize
from .config import ConfigStore, digest as config_digest
from .errors import SnapshotServiceError, envelope
from .explain import DecisionRecorder, render_text
from .hypervisor import EntropyInjector, HypervisorPort
from .metastore import MetaStore
from .resilience import Admission, CircuitBreaker, Deadline, RetryBudget, retry
from .snapshot import model_fingerprint
from .storage import BlobStore
from .telemetry import Health, Metrics, StructuredLogger, child_traceparent

FRAME_MAGIC = b"INV26F1\x00"
MAX_DECISIONS = 2000


def frame(state: bytes, memory: bytes) -> bytes:
    return FRAME_MAGIC + len(state).to_bytes(8, "big") + state + memory


def unframe(data: bytes) -> tuple[bytes, bytes]:
    if not data.startswith(FRAME_MAGIC) or len(data) < 16:
        raise SnapshotServiceError("SNAP_STORAGE_CORRUPT", "bad frame")
    n = int.from_bytes(data[8:16], "big")
    if n > len(data) - 16:
        raise SnapshotServiceError("SNAP_STORAGE_CORRUPT", "bad frame length")
    return data[16:16 + n], data[16 + n:]


class SnapshotService:
    def __init__(self, *, meta: MetaStore, config: ConfigStore, blobs: BlobStore, kms: crypto.KeyService,
                 hypervisor: HypervisorPort, entropy: EntropyInjector, authn: Authenticator, audit: AuditLog,
                 node_id: str, metrics: Metrics | None = None, logger: StructuredLogger | None = None,
                 workdir: str | None = None, clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep):
        self.meta, self.config, self.blobs, self.kms = meta, config, blobs, kms
        self.hv, self.entropy, self.authn, self.audit = hypervisor, entropy, authn, audit
        self.node_id, self.clock, self.sleep = node_id, clock, sleep
        self.metrics = metrics or Metrics()
        self.log = logger or StructuredLogger(stream=_NullStream())
        self.workdir = Path(workdir or tempfile.mkdtemp(prefix="inv26-work-"))
        self.workdir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._decisions: OrderedDict[str, dict] = OrderedDict()
        self._dlock = threading.Lock()
        self._inflight_ops: dict[str, tuple[str, float]] = {}
        self._cfg: tuple[int, dict] | None = None
        self._breakers: dict[str, CircuitBreaker] = {}
        self._budget = RetryBudget()
        self._admission: Admission | None = None
        self.reload_config()
        if self._cfg is not None:
            rt = self._cfg[1]["runtime"]
            if rt["adapter"] != hypervisor.name or rt["arch"] != hypervisor.arch:
                raise SnapshotServiceError("SNAP_CONFIG_INVALID",
                                           f"configured runtime {rt['adapter']}/{rt['arch']} does not match adapter "
                                           f"{hypervisor.name}/{hypervisor.arch}")
            if authn.profile != self._cfg[1]["profile"] and self._cfg[1]["profile"] == "production":
                raise SnapshotServiceError("SNAP_CONFIG_INVALID", "authenticator profile weaker than configuration")
        self.health_model = Health(
            version=__version__, profile=(self._cfg[1]["profile"] if self._cfg else "unknown"),
            probes={"kms": kms.health, "storage": blobs.health, "hypervisor": hypervisor.health,
                    "audit": lambda: audit.buffered == 0, "metadata": lambda: True,
                    "telemetry": lambda: self.log.export_failures == 0},
            critical=frozenset({"kms", "storage", "hypervisor", "metadata"}))

    # ------------------------------------------------------------------ config
    def reload_config(self) -> None:
        active = self.config.active()
        if active is None:
            self._cfg = None
            return
        rev, doc = active
        self._cfg = (rev, doc)  # single reference swap: readers never see a mixed config
        a, b = doc["admission"], doc["breaker"]
        self._admission = Admission(max_inflight=a["max_inflight"], max_queue=a["max_queue"],
                                    per_tenant=a["per_tenant"], tenant_rate=a["tenant_rate_per_s"],
                                    tenant_burst=a["tenant_burst"])
        self._breakers = {d: CircuitBreaker(d, threshold=b["threshold"], cooldown_s=b["cooldown_ms"] / 1000)
                          for d in ("kms", "storage", "hypervisor")}
        self._budget = RetryBudget(ratio=doc["retry"]["budget_ratio"])

    def _require_cfg(self) -> tuple[int, dict]:
        if self._cfg is None:
            raise SnapshotServiceError("SNAP_CONFIG_INVALID", "no active configuration")
        return self._cfg

    # ------------------------------------------------------------- boundary
    def handle(self, operation: str, token: str | None, request: Any, *, lineage: Any = None,
               traceparent: str | None = None, deadline: Deadline | None = None) -> tuple[int, dict]:
        """Public entry point: returns (http_status, body). Never raises."""
        op_id = uuid.uuid4().hex
        trace_id, span_id, _tp = child_traceparent(traceparent or (request.get("traceparent")
                                                                    if isinstance(request, dict) else None))
        t0 = time.monotonic()
        rev = self._cfg[0] if self._cfg else None
        rec = DecisionRecorder(operation, op_id, config_revision=rev, policy_version=policy.POLICY_VERSION,
                               correlation_id=op_id, lineage_in=lineage)
        tenant = request.get("tenant") if isinstance(request, dict) and isinstance(request.get("tenant"), str) else None
        try:
            fn = {"capture": self._capture, "restore": self._restore, "delete": self._delete,
                  "quarantine": self._quarantine, "release": self._release, "inspect": self._inspect,
                  "disable": self._disable, "enable": self._enable}.get(operation)
            if fn is None:
                raise SnapshotServiceError("SNAP_INVALID_REQUEST", "unknown operation")
            principal = self._authenticate(token, rec)
            body = fn(principal, request, rec, op_id, deadline)
            status, outcome, code = 200, body.get("outcome", "success"), "OK"
            rec.decide(outcome, "all-checks-passed" if not body.get("replayed") else "idempotent-replay")
        except SnapshotServiceError as exc:
            status, outcome, code = exc.spec.http, exc.outcome, exc.code
            body = envelope(exc, op_id)
            rec.decide(outcome, exc.code)
            self._count_refusal(exc, tenant)
            level = "warning" if exc.spec.security else "info"
            self.log.log(level, f"{operation}.refused", correlation_id=op_id, trace_id=trace_id, span_id=span_id,
                         tenant=tenant, code=exc.code, detail=exc.detail)
        except Exception as exc:  # defect: never leak text across the boundary
            err = SnapshotServiceError("SNAP_INTERNAL", type(exc).__name__)
            status, outcome, code = 500, err.outcome, err.code
            body = envelope(err, op_id)
            rec.decide(outcome, "SNAP_INTERNAL")
            self.log.log("error", f"{operation}.defect", correlation_id=op_id, trace_id=trace_id,
                         span_id=span_id, tenant=tenant, exc=type(exc).__name__)
        ms = (time.monotonic() - t0) * 1000
        self.metrics.inc("inv26_requests_total", labels={"op": operation, "outcome": outcome, "code": code,
                                                         "tenant": tenant or "-"})
        self.metrics.observe("inv26_request_latency_ms", ms, labels={"op": operation})
        if status == 200:
            self.log.log("info", f"{operation}.ok", correlation_id=op_id, trace_id=trace_id, span_id=span_id,
                         tenant=tenant, ms=round(ms, 3))
        with self._dlock:
            self._decisions[op_id] = rec.rec
            while len(self._decisions) > MAX_DECISIONS:
                self._decisions.popitem(last=False)
        try:  # decision summary into the audit chain (buffered; C076)
            self.audit.append(f"decision.{operation}", actor="inv26", tenant=tenant, outcome=outcome,
                              reason=code, correlation_id=op_id, config_revision=rev,
                              checks=[f"{c['check']}:{'pass' if c['passed'] else 'fail'}" for c in rec.rec["checks"]])
        except AuditUnavailable:
            pass
        body.setdefault("correlation_id", op_id)
        return status, body

    def _count_refusal(self, exc: SnapshotServiceError, tenant: str | None) -> None:
        self.metrics.inc("inv26_refusals_total", labels={"code": exc.code, "tenant": tenant or "-"})
        if exc.code == "SNAP_TENANT_MISMATCH":
            self.metrics.inc("inv26_cross_tenant_refusals_total")
        if exc.code == "SNAP_MODEL_MISMATCH":
            self.metrics.inc("inv26_model_mismatches_total")
        if exc.code == "SNAP_OVERLOADED":
            self.metrics.inc("inv26_admission_rejected_total", labels={"reason": exc.detail[:32]})

    def _authenticate(self, token: str | None, rec: DecisionRecorder) -> Principal:
        try:
            p = self.authn.authenticate(token or "")
        except SnapshotServiceError as exc:
            rec.check("authenticate", False, exc.code)
            raise
        rec.check("authenticate", True, p.subject)
        if p.breakglass:
            self._audit_fail_closed("breakglass.use", actor=p.subject, outcome="used", reason=p.breakglass_reason)
        return p

    def _audit_fail_closed(self, op: str, **kw) -> None:
        try:
            self.audit.append(op, fail_closed=True, **kw)
        except AuditUnavailable:
            raise SnapshotServiceError("SNAP_AUDIT_UNAVAILABLE", op) from None

    def _disabled(self) -> bool:
        cur = self.meta.get("control/disable")
        return bool(cur and cur[1].get("disabled"))

    def _preamble(self, p: Principal, req: Any, schema_id: str, cap: str, rec: DecisionRecorder,
                  operation: str) -> tuple[int, dict, dict]:
        if self._disabled():
            rec.check("emergency_disable", False, "active")
            raise SnapshotServiceError("SNAP_DISABLED", "emergency disable active")
        rec.check("emergency_disable", True)
        rev, cfg = self._require_cfg()
        req = schema.require(req, schema_id)
        rec.check("schema", True, schema_id)
        rec.inputs(tenant=req["tenant"], workload=req["workload"], environment=req["environment"],
                   snapshot_id=req["snapshot_id"], node=self.node_id)
        mode = policy.check_tier(cfg["tier"], operation)
        rec.check("tier_applicability", True, f"{cfg['tier']}:{mode}")
        site = req.get("site", cfg["site"])
        if site != cfg["site"]:
            rec.check("residency", False, f"request site {site} != node site")
            raise SnapshotServiceError("SNAP_RESIDENCY_VIOLATION", "request site is not this node's site")
        policy.check_residency(cfg, site, cfg["region"])
        rec.check("residency", True, site)
        if req["environment"] != cfg["environment"]:
            rec.check("environment_boundary", False)
            raise SnapshotServiceError("SNAP_ENVIRONMENT_MISMATCH", "request environment is not this node's")
        try:
            authorize(p, cap, tenant=req["tenant"], workload=req["workload"], environment=req["environment"])
        except SnapshotServiceError:
            rec.check("authorize", False, cap)
            raise
        rec.check("authorize", True, cap)
        if len(req["devices"]) > cfg["quotas"]["max_devices"]:
            raise SnapshotServiceError("SNAP_LIMIT_EXCEEDED", "device count")
        return rev, cfg, req

    # -------------------------------------------------------------- helpers
    def _dep(self, name: str, fn: Callable[[], Any], deadline: Deadline, cfg: dict) -> Any:
        deadline.check(name)
        r = cfg["retry"]

        def once():
            return self._breakers[name].call(fn)
        return retry(once, attempts=r["attempts"], base_s=r["base_ms"] / 1000, cap_s=r["cap_ms"] / 1000,
                     deadline=deadline, budget=self._budget, sleep=self.sleep,
                     on_retry=lambda e, n: self.metrics.inc("inv26_retries_total", labels={"dependency": name}))

    def _ctx(self, rec_val: dict) -> dict:
        return {k: rec_val[k] for k in ("snapshot_id", "tenant", "workload", "environment", "site",
                                        "fingerprint", "generation")}

    @contextmanager
    def _track(self, op_id: str, stage: str):
        self._inflight_ops[op_id] = (stage, time.monotonic())
        self.metrics.set("inv26_inflight", len(self._inflight_ops))
        try:
            yield
        finally:
            self._inflight_ops.pop(op_id, None)
            self.metrics.set("inv26_inflight", len(self._inflight_ops))

    def _set_state(self, key: str, gen: int, value: dict, state: str, fence=None, **extra) -> int:
        lifecycle.check_transition("snapshot", value["state"], state)
        value.update(extra, state=state, updated_at=int(self.clock() * 1000))
        return self.meta.transact({key: (gen, value)}, fence=fence)[key]

    # -------------------------------------------------------------- capture
    def _capture(self, p: Principal, req: Any, rec: DecisionRecorder, op_id: str, deadline: Deadline | None):
        rev, cfg, req = self._preamble(p, req, "PK_SNAPSHOT_CAPTURE_REQUEST/2", "snapshot.capture", rec, "capture")
        if req["memory_mib"] > cfg["quotas"]["max_memory_mib"]:
            raise SnapshotServiceError("SNAP_LIMIT_EXCEEDED", "memory_mib above quota")
        tenant, sid = req["tenant"], req["snapshot_id"]
        req_digest = hashlib.sha256(schema.canonical_bytes({k: v for k, v in req.items()
                                                            if k not in ("traceparent", "deadline_ms")})).hexdigest()
        idem_key = f"idem/{tenant}/{req['idempotency_key']}"
        prior = self.meta.get(idem_key)
        if prior is not None:
            if prior[1]["request_sha256"] != req_digest:
                raise SnapshotServiceError("SNAP_INVALID_REQUEST", "idempotency key reused with a different request")
            if prior[1].get("result"):
                rec.check("idempotency", True, "replay of committed capture")
                return dict(prior[1]["result"], replayed=True)
        existing = self.meta.scan(f"tidx/{tenant}/")
        if len(existing) >= cfg["quotas"]["max_snapshots_per_tenant"]:
            rec.check("quota", False, "snapshot count")
            raise SnapshotServiceError("SNAP_QUOTA_EXCEEDED", "snapshot count")
        used = sum(v[1].get("bytes", 0) for v in existing.values())
        est = req["memory_mib"] * 1024 * 1024
        if used + est > cfg["quotas"]["max_bytes_per_tenant"]:
            rec.check("quota", False, "bytes")
            raise SnapshotServiceError("SNAP_QUOTA_EXCEEDED", "retained bytes")
        rec.check("quota", True)
        fingerprint = model_fingerprint(req["devices"])
        deadline = deadline or Deadline(min(cfg["timeouts_ms"]["capture"], req.get("deadline_ms", 10 ** 9)) / 1000)
        key = f"snap/{sid}"
        with self._admission.slot(tenant), self._track(op_id, "capture"):
            rec.check("admission", True)
            value = {"snapshot_id": sid, "tenant": tenant, "workload": req["workload"],
                     "environment": req["environment"], "site": cfg["site"], "fingerprint": fingerprint,
                     "memory_mib": req["memory_mib"], "state": "ABSENT", "generation": 1,
                     "config_revision": rev, "created_at": int(self.clock() * 1000), "op_id": op_id}
            try:
                value["state"] = "CAPTURING"
                gens = self.meta.transact({key: (0, value), idem_key: (0, {"request_sha256": req_digest,
                                                                            "op_id": op_id, "result": None}),
                                           f"tidx/{tenant}/{sid}": (0, {"bytes": 0})})
            except SnapshotServiceError as exc:
                if exc.code == "SNAP_STALE_GENERATION":
                    raise SnapshotServiceError("SNAP_DUPLICATE", sid) from None
                raise
            gen = gens[key]
            blob_written = committed = False
            work = Path(tempfile.mkdtemp(prefix=f"cap-{op_id[:8]}-", dir=self.workdir))
            t0 = time.monotonic()
            try:
                self._dep("hypervisor", lambda: self.hv.pause(req["vm_id"]), deadline, cfg)
                state, memory = self._dep("hypervisor", lambda: self.hv.capture(req["vm_id"], work), deadline, cfg)
                ctx = self._ctx(value)
                env, blob = self._dep("kms", lambda: crypto.seal_envelope(frame(state, memory), ctx=ctx, kms=self.kms,
                                                                          key_id=cfg["kms"]["key_id"]), deadline, cfg)
                del state, memory
                self._dep("storage", lambda: self.blobs.put(tenant, sid, value["generation"], blob), deadline, cfg)
                blob_written = True
                gen = self._set_state(key, gen, value, "CAPTURED")
                manifest = {"schema": "PK_SNAPSHOT_MANIFEST/1", **{k: value[k] for k in (
                    "snapshot_id", "tenant", "workload", "environment", "site", "fingerprint", "memory_mib",
                    "generation", "created_at")},
                    "runtime": {"adapter": self.hv.name, "version": self.hv.version, "arch": self.hv.arch},
                    "capture_schema": "PK_SNAPSHOT/2", "envelope": env}
                schema.require(manifest, "PK_SNAPSHOT_MANIFEST/1")
                gen = self._set_state(key, gen, value, "VERIFYING")
                stored = self._dep("storage", lambda: self.blobs.get(tenant, sid, value["generation"]), deadline, cfg)
                if hashlib.sha256(stored).hexdigest() != env["ciphertext_sha256"]:  # read-back scrub
                    self._set_state(key, gen, value, "QUARANTINED", quarantine_reason="post-write digest mismatch")
                    raise SnapshotServiceError("SNAP_STORAGE_CORRUPT", "read-back digest mismatch")
                msha = hashlib.sha256(schema.canonical_bytes(manifest)).hexdigest()
                ms = (time.monotonic() - t0) * 1000
                result = {"schema": "PK_SNAPSHOT/2", "snapshot_id": sid, "tenant": tenant, "workload": req["workload"],
                          "environment": req["environment"], "fingerprint": fingerprint, "generation": value["generation"],
                          "manifest_sha256": msha, "state": "AVAILABLE", "capture_ms": round(ms, 3),
                          "entropy_stale": True, "outcome": "success", "operation_id": op_id}
                # commit point: AVAILABLE + idempotency result + quota index in ONE durable transaction
                lifecycle.check_transition("snapshot", value["state"], "AVAILABLE")
                value.update(state="AVAILABLE", manifest=manifest, manifest_sha256=msha,
                             updated_at=int(self.clock() * 1000))
                self.meta.transact({key: (gen, value),
                                    idem_key: (None, {"request_sha256": req_digest, "op_id": op_id, "result": result,
                                                      "created_at": int(self.clock() * 1000)}),
                                    f"tidx/{tenant}/{sid}": (None, {"bytes": len(blob)})})
                committed = True
            except BaseException as exc:
                if committed:  # failure after the commit point never undoes a committed snapshot
                    raise
                if blob_written:
                    try:
                        self.blobs.delete(tenant, sid, value["generation"])
                    except SnapshotServiceError:
                        pass  # reconcile() will collect it
                self._retire_failed(key, getattr(exc, "code", "SNAP_INTERNAL"), idem_key)
                raise
            finally:
                shutil.rmtree(work, ignore_errors=True)
        self.metrics.inc("inv26_snapshots_captured_total", labels={"tenant": tenant, "fingerprint": fingerprint[:12]})
        self.metrics.observe("inv26_capture_ms", ms, labels={"adapter": self.hv.name})
        self.audit.append("snapshot.capture", actor=p.subject, tenant=tenant, outcome="success", resource=sid,
                          correlation_id=op_id, manifest_sha256=msha, config_revision=rev)
        return result

    # -------------------------------------------------------------- restore
    def _restore(self, p: Principal, req: Any, rec: DecisionRecorder, op_id: str, deadline: Deadline | None):
        rev, cfg, req = self._preamble(p, req, "PK_SNAPSHOT_RESTORE_REQUEST/2", "snapshot.restore", rec, "restore")
        try:
            g = self.authn.verify_grant(req["grant"])
        except SnapshotServiceError as exc:
            rec.check("grant", False, exc.detail)
            raise SnapshotServiceError("SNAP_GRANT_INVALID", exc.detail) from None
        for f, want in (("snapshot_id", req["snapshot_id"]), ("tenant", req["tenant"]),
                        ("workload", req["workload"]), ("environment", req["environment"]),
                        ("node", self.node_id), ("target_vm_id", req["target_vm_id"])):
            if g.get(f) != want:
                rec.check("grant", False, f"{f} not bound to this request")
                raise SnapshotServiceError("SNAP_GRANT_INVALID", f"grant {f} does not match")
        rec.check("grant", True, "bound to request and node")
        grant_key = f"grant/{hashlib.sha256(str(g['nonce']).encode()).hexdigest()}"
        prior = self.meta.get(grant_key)
        if prior is not None:
            gv = prior[1]
            if gv["idempotency_key"] != req["idempotency_key"]:
                rec.check("anti_replay", False, "grant already consumed")
                self.audit.append("grant.replay", actor=p.subject, tenant=req["tenant"], outcome="refused",
                                  reason="SNAP_GRANT_REPLAYED", correlation_id=op_id)
                raise SnapshotServiceError("SNAP_GRANT_REPLAYED", "grant already consumed")
            if gv["state"] == "READY":
                rec.check("anti_replay", True, "idempotent retry returns recorded result")
                return dict(gv["result"], replayed=True)
            if gv["state"] in lifecycle.TRANSIENT_RESTORE:
                raise SnapshotServiceError("SNAP_STALE_GENERATION", "restore for this grant in progress")
            if not gv.get("retryable") or gv.get("attempts", 1) >= 3:
                raise SnapshotServiceError("SNAP_GRANT_REPLAYED", "grant consumed by a terminal failure")
            consumed = self.meta.transact({grant_key: (prior[0], dict(gv, state="PENDING", op_id=op_id,
                                                                     attempts=gv.get("attempts", 1) + 1))})
        else:
            try:
                consumed = self.meta.transact({grant_key: (0, {"state": "PENDING", "op_id": op_id,
                                                               "idempotency_key": req["idempotency_key"],
                                                               "exp": g.get("exp"), "attempts": 1,
                                                               "result": None})})
            except SnapshotServiceError as exc:
                if exc.code == "SNAP_STALE_GENERATION":  # lost a concurrent race for the same grant
                    raise SnapshotServiceError("SNAP_GRANT_REPLAYED", "concurrent consumption") from None
                raise
        rec.check("anti_replay", True, "grant consumed")
        ggen = consumed[grant_key]

        def grant_state(state: str, **extra):
            nonlocal ggen
            cur = self.meta.get(grant_key)
            lifecycle.check_transition("restore", cur[1]["state"], state)
            ggen = self.meta.transact({grant_key: (ggen, dict(cur[1], state=state, **extra))})[grant_key]

        guest_loaded = False
        vm = req["target_vm_id"]
        try:
            with self._admission.slot(req["tenant"]), self._track(op_id, "restore"):
                rec.check("admission", True)
                deadline = deadline or Deadline(min(cfg["timeouts_ms"]["restore"], req.get("deadline_ms", 10 ** 9)) / 1000)
                cur = self.meta.get(f"snap/{req['snapshot_id']}")
                if cur is None or cur[1]["state"] in ("DELETED", "DELETING"):
                    raise SnapshotServiceError("SNAP_NOT_FOUND", req["snapshot_id"])
                sv = cur[1]
                # security boundaries (v5.0.0 baseline) -- before any storage/KMS/hypervisor work
                for field_, code in (("tenant", "SNAP_TENANT_MISMATCH"), ("workload", "SNAP_WORKLOAD_MISMATCH"),
                                     ("environment", "SNAP_ENVIRONMENT_MISMATCH")):
                    if sv[field_] != req[field_]:
                        rec.check(f"{field_}_binding", False)
                        raise SnapshotServiceError(code, f"{field_} binding refused")
                    rec.check(f"{field_}_binding", True)
                if sv["state"] == "QUARANTINED":
                    raise SnapshotServiceError("SNAP_QUARANTINED", req["snapshot_id"])
                if sv["state"] not in lifecycle.RESTORABLE:
                    raise SnapshotServiceError("SNAP_ILLEGAL_TRANSITION", f"snapshot is {sv['state']}")
                fp = model_fingerprint(req["devices"])
                if fp != sv["fingerprint"]:
                    rec.check("device_model", False)
                    raise SnapshotServiceError("SNAP_MODEL_MISMATCH", "fingerprint differs")
                rec.check("device_model", True)
                if g["manifest_sha256"] != sv["manifest_sha256"] or g["generation"] != sv["generation"]:
                    rec.check("grant_manifest", False)
                    raise SnapshotServiceError("SNAP_GRANT_INVALID", "grant is for another manifest/generation")
                rec.check("grant_manifest", True)
                t0 = time.monotonic()
                grant_state("RESTORING")
                blob = self._dep("storage", lambda: self.blobs.get(sv["tenant"], sv["snapshot_id"], sv["generation"]),
                                 deadline, cfg)
                plain = self._dep("kms", lambda: crypto.open_envelope(blob, env=sv["manifest"]["envelope"],
                                                                     ctx=self._ctx(sv), kms=self.kms), deadline, cfg)
                rec.check("integrity", True, "digest+AEAD verified")
                state, memory = unframe(plain)
                del plain
                deadline.check("hypervisor.load")
                work = Path(tempfile.mkdtemp(prefix=f"rst-{op_id[:8]}-", dir=self.workdir))
                try:
                    guest_loaded = True
                    self._dep("hypervisor", lambda: self.hv.load(vm, work, state, memory), deadline, cfg)
                finally:
                    shutil.rmtree(work, ignore_errors=True)
                del state, memory
                grant_state("RESEEDING")
                seed = secrets.token_bytes(32)
                proof = hashlib.sha256(seed).hexdigest()
                try:
                    self.entropy.inject(vm, seed)
                except Exception as exc:
                    raise SnapshotServiceError("SNAP_ENTROPY_FAILED", type(exc).__name__) from None
                finally:
                    seed = b""  # drop our only reference
                rec.check("entropy_ack", True)
                self._dep("hypervisor", lambda: self.hv.resume(vm), deadline, cfg)
                ms = (time.monotonic() - t0) * 1000
                self.metrics.inc("inv26_reseeds_total")
                result = {"schema": "PK_SNAPSHOT_RESTORE/2", "snapshot_id": sv["snapshot_id"], "tenant": sv["tenant"],
                          "workload": sv["workload"], "environment": sv["environment"], "operation_id": op_id,
                          "restore_ms": round(ms, 4), "budget_ms": float(cfg["restore_budget_ms"]),
                          "within_budget": ms <= cfg["restore_budget_ms"], "entropy_reseeded": True,
                          "entropy_proof_sha256": proof, "state": "READY", "outcome": "success"}
                schema.require(result, "PK_SNAPSHOT_RESTORE/2")
                grant_state("READY", result=result)
        except BaseException as exc:
            if guest_loaded:
                try:
                    self.hv.destroy(vm)  # a partially restored guest is never left runnable
                except Exception:
                    pass
            cur = self.meta.get(grant_key)
            if cur and cur[1]["state"] in lifecycle.TRANSIENT_RESTORE:
                retryable = bool(getattr(exc, "retryable", False))
                self.meta.transact({grant_key: (cur[0], dict(cur[1], state="FAILED", retryable=retryable,
                                                             failure=getattr(exc, "code", "SNAP_INTERNAL")))})
            raise
        self.metrics.observe("inv26_restore_ms", ms, labels={"adapter": self.hv.name})
        self.audit.append("snapshot.restore", actor=p.subject, tenant=sv["tenant"], outcome="success",
                          resource=sv["snapshot_id"], correlation_id=op_id, node=self.node_id, vm=vm,
                          config_revision=rev, entropy_proof_sha256=proof)
        return result

    def _retire_failed(self, key: str, failure: str, idem_key: str | None) -> None:
        """Move a failed capture to history so the id (and idempotency key) can be retried."""
        cur = self.meta.get(key)
        if not cur or cur[1]["state"] not in ("CAPTURING", "CAPTURED", "VERIFYING", "FAILED"):
            return
        v = dict(cur[1], state="FAILED", failure=failure)
        dels = {key: cur[0]}
        tidx = f"tidx/{v['tenant']}/{v['snapshot_id']}"
        if self.meta.get(tidx):
            dels[tidx] = None
        if idem_key and self.meta.get(idem_key):
            dels[idem_key] = None
        self.meta.transact({f"snaphist/{v['snapshot_id']}/{v['op_id']}": (0, v)}, dels)

    # ------------------------------------------------------------ admin ops
    def _lookup(self, p: Principal, req: Any, cap: str, rec: DecisionRecorder) -> tuple[int, dict]:
        if not isinstance(req, dict) or not isinstance(req.get("snapshot_id"), str):
            raise SnapshotServiceError("SNAP_INVALID_REQUEST", "snapshot_id required")
        cur = self.meta.get(f"snap/{req['snapshot_id']}")
        if cur is None:
            raise SnapshotServiceError("SNAP_NOT_FOUND", req["snapshot_id"])
        v = cur[1]
        authorize(p, cap, tenant=v["tenant"], workload=v["workload"], environment=v["environment"])
        rec.check("authorize", True, cap)
        return cur

    def _delete(self, p, req, rec, op_id, deadline):
        gen, v = self._lookup(p, req, "snapshot.delete", rec)
        self._audit_fail_closed("snapshot.delete", actor=p.subject, tenant=v["tenant"], outcome="committing",
                                resource=v["snapshot_id"], correlation_id=op_id)
        key = f"snap/{v['snapshot_id']}"
        gen = self._set_state(key, gen, v, "DELETING")
        self.blobs.delete(v["tenant"], v["snapshot_id"], v["generation"])
        if "manifest" in v:  # crypto-erase: the wrapped DEK is the only path to the plaintext
            v["manifest"]["envelope"]["wrapped_dek"] = "erased"
        self._set_state(key, gen, v, "DELETED", deleted_at=int(self.clock() * 1000))
        if self.meta.get(f"tidx/{v['tenant']}/{v['snapshot_id']}"):
            self.meta.transact(deletes={f"tidx/{v['tenant']}/{v['snapshot_id']}": None})
        return {"schema": "PK_SNAPSHOT_ADMIN/1", "snapshot_id": v["snapshot_id"], "state": "DELETED",
                "crypto_erased": True, "outcome": "success"}

    def _quarantine(self, p, req, rec, op_id, deadline):
        gen, v = self._lookup(p, req, "snapshot.quarantine", rec)
        reason = str(req.get("reason", ""))[:200]
        self._audit_fail_closed("snapshot.quarantine", actor=p.subject, tenant=v["tenant"], outcome="committing",
                                resource=v["snapshot_id"], reason=reason, correlation_id=op_id)
        self._set_state(f"snap/{v['snapshot_id']}", gen, v, "QUARANTINED", quarantine_reason=reason)
        return {"schema": "PK_SNAPSHOT_ADMIN/1", "snapshot_id": v["snapshot_id"], "state": "QUARANTINED",
                "outcome": "success"}

    def _release(self, p, req, rec, op_id, deadline):
        gen, v = self._lookup(p, req, "snapshot.quarantine", rec)
        if not p.breakglass and v.get("quarantine_reason", "").startswith("post-write"):
            raise SnapshotServiceError("SNAP_FORBIDDEN", "integrity quarantine needs break-glass release")
        self._audit_fail_closed("snapshot.release", actor=p.subject, tenant=v["tenant"], outcome="committing",
                                resource=v["snapshot_id"], correlation_id=op_id)
        self._set_state(f"snap/{v['snapshot_id']}", gen, v, "AVAILABLE")
        return {"schema": "PK_SNAPSHOT_ADMIN/1", "snapshot_id": v["snapshot_id"], "state": "AVAILABLE",
                "outcome": "success"}

    def _inspect(self, p, req, rec, op_id, deadline):
        _gen, v = self._lookup(p, req, "snapshot.inspect", rec)
        public = {k: v.get(k) for k in ("snapshot_id", "tenant", "workload", "environment", "site", "fingerprint",
                                        "memory_mib", "generation", "state", "config_revision", "manifest_sha256",
                                        "created_at")}
        return {"schema": "PK_SNAPSHOT_INSPECT/1", **public, "outcome": "success"}

    def _set_disable(self, p, flag: bool, req, op_id):
        authorize(p, "snapshot.admin", tenant=None)
        self._audit_fail_closed("control.disable" if flag else "control.enable", actor=p.subject,
                                outcome="committing", reason=str((req or {}).get("reason", ""))[:200],
                                correlation_id=op_id)
        cur = self.meta.get("control/disable")
        self.meta.transact({"control/disable": (cur[0] if cur else 0, {"disabled": flag, "by": p.subject,
                                                                        "at": int(self.clock() * 1000)})})
        return {"schema": "PK_SNAPSHOT_ADMIN/1", "disabled": flag, "outcome": "success"}

    def _disable(self, p, req, rec, op_id, deadline):
        return self._set_disable(p, True, req, op_id)

    def _enable(self, p, req, rec, op_id, deadline):
        return self._set_disable(p, False, req, op_id)

    # ------------------------------------------------------- recovery / ops
    def reconcile(self) -> dict:
        """Crash recovery (C057, X011): resolve transient records and orphan blobs."""
        report = {"schema": "PK_SNAPSHOT_RECONCILE/1", "snapshots_failed": [], "deletes_completed": [],
                  "grants_failed": [], "orphan_blobs_removed": []}
        for key, (gen, v) in self.meta.scan("snap/").items():
            target = lifecycle.recovery_action("snapshot", v["state"])
            if target is None:
                continue
            if target == "FAILED":
                try:
                    self.blobs.delete(v["tenant"], v["snapshot_id"], v["generation"])
                except SnapshotServiceError:
                    pass
                self._retire_failed(key, "recovered-after-crash", None)
                report["snapshots_failed"].append(v["snapshot_id"])
            elif target == "DELETED":
                self.blobs.delete(v["tenant"], v["snapshot_id"], v["generation"])
                self.meta.transact({key: (gen, dict(v, state="DELETED"))})
                report["deletes_completed"].append(v["snapshot_id"])
        for key, (gen, v) in self.meta.scan("grant/").items():
            if v["state"] in lifecycle.TRANSIENT_RESTORE:
                self.meta.transact({key: (gen, dict(v, state="FAILED", retryable=True, failure="recovered-after-crash"))})
                report["grants_failed"].append(key[-12:])
        live = {(v["tenant"], f"{v['snapshot_id']}.g{v['generation']}.blob")
                for _, (_, v) in self.meta.scan("snap/").items() if v["state"] in ("AVAILABLE", "QUARANTINED")}
        tenants = {v["tenant"] for _, (_, v) in self.meta.scan("snap/").items()}
        for t in tenants:
            for name in self.blobs.list(t):
                if (t, name) not in live:
                    sid, g = name.rsplit(".g", 1)
                    self.blobs.delete(t, sid, int(g.split(".")[0]))
                    report["orphan_blobs_removed"].append(f"{t}/{name}")
        self.audit.append("reconcile", actor="inv26", outcome="done", **{k: len(v) for k, v in report.items()
                                                                          if isinstance(v, list)})
        return report

    def gc(self, *, tombstone_retention_s: float = 7 * 86400, idempotency_ttl_s: float = 86400,
           grant_grace_s: float = 60.0) -> dict:
        """Bound durable metadata growth (C017, C067).

        * consumed grant records are dropped once the grant itself has expired
          (+ grace > clock skew): an expired grant fails authentication anyway, so
          forgetting its nonce cannot re-enable a replay;
        * capture idempotency records expire after ``idempotency_ttl_s``;
        * DELETED tombstones and failed-capture history expire after ``tombstone_retention_s``.
        """
        now = self.clock()
        drop: dict[str, int] = {}
        for key, (gen, v) in self.meta.scan("grant/").items():
            exp = v.get("exp")
            if v.get("state") in ("READY", "FAILED") and isinstance(exp, (int, float)) and exp + grant_grace_s < now:
                drop[key] = gen
        for key, (gen, v) in self.meta.scan("idem/").items():
            if v.get("result") is not None and v.get("created_at", 0) / 1000 + idempotency_ttl_s < now:
                drop[key] = gen
        for key, (gen, v) in self.meta.scan("snap/").items():
            if v.get("state") == "DELETED" and v.get("deleted_at", 0) / 1000 + tombstone_retention_s < now:
                drop[key] = gen
        for key, (gen, v) in self.meta.scan("snaphist/").items():
            if v.get("updated_at", v.get("created_at", 0)) / 1000 + tombstone_retention_s < now:
                drop[key] = gen
        for i in range(0, len(drop), 200):
            batch = dict(list(drop.items())[i:i + 200])
            self.meta.transact(deletes=batch)
        return {"schema": "PK_SNAPSHOT_GC/1", "removed": len(drop)}

    def scrub(self) -> dict:
        """Storage scrub (C095, C059): re-verify every AVAILABLE blob's digest; quarantine mismatches."""
        report = {"schema": "PK_SNAPSHOT_SCRUB/1", "checked": 0, "quarantined": []}
        for key, (gen, v) in self.meta.scan("snap/").items():
            if v["state"] != "AVAILABLE":
                continue
            report["checked"] += 1
            try:
                blob = self.blobs.get(v["tenant"], v["snapshot_id"], v["generation"])
                ok = hashlib.sha256(blob).hexdigest() == v["manifest"]["envelope"]["ciphertext_sha256"]
            except SnapshotServiceError:
                ok = False
            if not ok:
                self._set_state(key, gen, v, "QUARANTINED", quarantine_reason="post-write scrub digest mismatch")
                report["quarantined"].append(v["snapshot_id"])
        self.audit.append("scrub", actor="inv26", outcome="done", checked=report["checked"],
                          quarantined=len(report["quarantined"]))
        return report

    def rewrap_all(self) -> dict:
        """KEK rotation (C047): re-wrap every live DEK under the current KEK version.

        The manifest digest changes, so outstanding restore grants over the old
        digest become invalid (fail-closed) and must be re-issued.
        """
        n = 0
        for key, (gen, v) in self.meta.scan("snap/").items():
            if v["state"] not in ("AVAILABLE", "QUARANTINED"):
                continue
            env = v["manifest"]["envelope"]
            kv, wrapped = self.kms.rewrap(env["key_id"], env["key_version"], env["wrapped_dek"], self._ctx(v))
            env.update(key_version=kv, wrapped_dek=wrapped)
            v["manifest_sha256"] = hashlib.sha256(schema.canonical_bytes(v["manifest"])).hexdigest()
            self.meta.transact({key: (gen, v)})
            n += 1
        self._audit_fail_closed("kms.rewrap_all", actor="inv26", outcome="done", count=n)
        return {"schema": "PK_SNAPSHOT_REWRAP/1", "rewrapped": n}

    def stalled(self) -> list[dict]:
        now = time.monotonic()
        out = []
        for op, (stage, t) in list(self._inflight_ops.items()):
            limit = lifecycle.STATE_TIMEOUT_S["CAPTURING" if stage == "capture" else "RESTORING"]
            if now - t > limit:
                out.append({"operation_id": op, "stage": stage, "age_s": round(now - t, 3)})
        self.metrics.set("inv26_stalled_operations", len(out))
        return out

    def health(self) -> dict:
        rev, doc = self._cfg if self._cfg else (None, None)
        for name, br in self._breakers.items():
            self.metrics.set("inv26_breaker_state", {"closed": 0, "half_open": 1, "open": 2}[br.state],
                             labels={"dependency": name})
        caps = [op for op in ("capture", "restore", "delete") if doc and
                policy.APPLICABILITY[doc["tier"]].get(op) != "prohibited"]
        return self.health_model.document(config_revision=rev, config_digest=config_digest(doc) if doc else None,
                                          capabilities=caps, disabled=self._disabled(), stalled=len(self.stalled()))

    def explain(self, operation_id: str, *, text: bool = False):
        with self._dlock:
            rec = self._decisions.get(operation_id)
        if rec is None:
            return None
        return render_text(rec) if text else rec


class _NullStream:
    def write(self, _s: str) -> None:
        pass
