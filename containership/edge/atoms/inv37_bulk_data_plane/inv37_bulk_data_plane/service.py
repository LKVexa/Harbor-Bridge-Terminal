"""BulkDataPlane service facade: the integration point that composes config,
security, fair admission, lifecycle, durable checkpoints, transports and
telemetry (INV-37-C014..C019, C025, C027, C046, C052, C056..C059, C071..C077).

Every public operation:
  1. extracts/creates trace context,
  2. authenticates the token and authorizes the action for the transfer's
     tenant/scope (deny by default, on every call),
  3. drives the lifecycle state machine (illegal transitions fail closed),
  4. records metrics, a structured log line and - for automated decisions - a
     Decision with reason code.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from . import shm_transport as shm
from .checkpoint import CheckpointStore, Lease, check_id
from .config import ActiveConfig, to_limits
from .data_plane import RESUME_SCHEMA, Receiver, _expected_chunk_length, _require_bytes, validate_manifest
from .errors import BulkDataPlaneError, CodedError, DigestMismatch, SecurityRejected, TransferIncomplete
from .lifecycle import Event, Lifecycle, StateMachine
from .outcomes import classify
from .quota import FairAdmission, Grant, TenantQuota
from .security import Authenticator, Authorizer, AuditLog, KeyRing, Principal, check_residency
from .telemetry import Decision, DecisionLog, Metrics, StructuredLogger, TraceContext, explain, pseudonym, release_lineage

RESUME2_SCHEMA = "PK_BULK_RESUME/2"
SUPPORTED = {
    "manifest": ["PK_BULK_MANIFEST/1"],
    "chunk": ["PK_BULK_CHUNK/1"],
    "resume": [RESUME_SCHEMA, RESUME2_SCHEMA],
    "transport": [shm.TRANSPORT_ABI, "INV37_COPY/1"],
    "auth": ["v1"],
}
MANDATORY_FEATURES = {"auth"}
KNOWN_FEATURES = set(SUPPORTED) | {"compression", "encryption"}


def negotiate(offer: Mapping[str, Any], *, require_auth: bool = True, local: Mapping[str, list[str]] = SUPPORTED) -> dict[str, Any]:
    """Deterministically pick the highest mutually supported version per surface.

    ``offer`` = {surface: [versions...], "mandatory": [feature,...]}.  Unknown
    mandatory features, missing mutual versions, or an auth downgrade refuse
    with ``version_incompatible``.  Unknown optional surfaces are ignored.
    """
    unknown_mandatory = set(offer.get("mandatory", [])) - KNOWN_FEATURES
    if unknown_mandatory:
        raise CodedError("version_incompatible", "peer requires unknown features", features=sorted(unknown_mandatory))
    chosen: dict[str, Any] = {}
    for surface, versions in local.items():
        peer = offer.get(surface)
        if peer is None:
            if surface == "auth" and require_auth:
                raise CodedError("version_incompatible", "peer offers no authentication; downgrade refused")
            if surface in ("manifest", "chunk"):
                raise CodedError("version_incompatible", "peer omitted mandatory surface", surface=surface)
            continue
        mutual = [v for v in versions if v in peer]
        if not mutual:
            raise CodedError("version_incompatible", "no mutually supported version", surface=surface,
                             local=versions, peer=list(peer))
        chosen[surface] = max(mutual, key=lambda v: (v.rsplit("/", 1)[-1].isdigit() and int(v.rsplit("/", 1)[-1]), v))
    if "encryption" in offer.get("mandatory", []):
        from .security import encryption_provider_available

        if not encryption_provider_available():
            raise CodedError("encryption_unavailable", "peer requires encryption; no approved provider")
    return chosen


@dataclass
class Transfer:
    tid: str
    tenant: str
    manifest: dict[str, Any]
    sm: StateMachine
    grant: Grant | None
    trace: TraceContext
    region: Any = None
    zc: shm.ZeroCopyReceiver | None = None
    mem: Receiver | None = None
    lease: Lease | None = None
    verified: set[int] = field(default_factory=set)
    created: float = field(default_factory=time.monotonic)
    last_progress: float = field(default_factory=time.monotonic)
    transport: str = "copy"
    counter: shm.CopyCounter = field(default_factory=shm.CopyCounter)
    lock: threading.RLock = field(default_factory=threading.RLock)


class BulkDataPlane:
    def __init__(self, cfg: ActiveConfig, *, keyring: KeyRing, node: str = "node-0", region: str = "local",
                 audit_path: str | None = None, clock=time.time, log_stream=None, caps: Mapping[str, Any] | None = None) -> None:
        if not cfg.admission_allowed:
            raise CodedError("invalid_config", "configuration has fatal findings; admission disabled",
                             findings=[f.code for f in cfg.findings if f.severity == "fatal"])
        e = cfg.effective
        self.cfg = cfg
        self.e = e
        self.node = node
        self.region = region
        self.limits = to_limits(e)
        self._key = keyring.signing()[1]
        self._diag_key = hashlib.sha256(b"inv37-diag" + self._key).digest()
        self.audit = AuditLog(audit_path, self._key)
        self.authn = Authenticator(keyring, clock=clock, clock_skew=e["security.clock_skew"], node=node, audit=self.audit)
        self.authz = Authorizer(self.audit)
        self.require_auth = e["security.require_authentication"]
        tenants = {n: TenantQuota(t.get("weight", 1), t.get("max_active_transfers", e["tenancy.default_max_active_transfers"]),
                                  t.get("max_bytes_in_flight", e["tenancy.default_max_bytes_in_flight"]))
                   for n, t in e["tenancy.tenants"].items()}
        self.tenant_regions = {n: t.get("regions", []) for n, t in e["tenancy.tenants"].items()}
        self.admission = FairAdmission(max_active=e["limits.max_concurrent_transfers"], max_bytes=e["limits.host_memory_budget"],
                                       max_pending=e["limits.max_pending_transfers"],
                                       default=TenantQuota(1, e["tenancy.default_max_active_transfers"], e["tenancy.default_max_bytes_in_flight"]),
                                       tenants=tenants)
        self.store = (CheckpointStore(e["checkpoint.directory"], seal_key=self._key, fsync=e["checkpoint.fsync"],
                                      max_bytes=e["checkpoint.max_bytes"])
                      if e["checkpoint.enabled"] and e["checkpoint.directory"] else None)
        self.caps = dict(caps) if caps is not None else shm.probe()
        self.metrics = Metrics()
        self.log = StructuredLogger(node=node, level=e["telemetry.log_level"], stream=log_stream,
                                    path=e["telemetry.file"] if e["telemetry.export"] == "file" else None)
        self.decisions = DecisionLog()
        self.lineage = release_lineage()
        self.transfers: dict[str, Transfer] = {}
        self.quarantined_tenants: set[str] = set()
        self._lock = threading.RLock()
        self.dependency_status: dict[str, str] = {"checkpoint": "ok" if self.store else "disabled",
                                                  "telemetry_export": "ok", "policy": "ok", "time": "ok"}
        self.started = time.time()

    # ---------------------------------------------------------------- helpers
    def _principal(self, token: Any, action: str, tenant: str | None, tid: str | None) -> Principal:
        try:
            p = self.authn.verify(token)
        except SecurityRejected:
            self.metrics.inc("security_rejections_total", reason="authn")
            raise
        self.authz.check(p, action, tenant=tenant if tenant is not None else p.tenant, transfer_id=tid)
        return p

    def _decide(self, t: Transfer | None, decision: str, outcome: str, reason: str, inputs: dict, policy: dict,
                constraints: dict) -> None:
        self.decisions.record(Decision(decision, outcome, reason, inputs, policy, constraints,
                                       transfer_id=t.tid if t else inputs.get("transfer_id"),
                                       trace_id=t.trace.trace_id if t else None, config_digest=self.cfg.digest,
                                       artifact=self.lineage["source_digest"]))

    def _get(self, tid: str) -> Transfer:
        with self._lock:
            t = self.transfers.get(tid)
        if t is None:
            raise CodedError("transfer_closed", "unknown transfer", transfer_id=tid)
        return t

    def _persist_state(self, t: Transfer) -> None:
        if self.store and t.lease:
            try:
                self.store.set_lifecycle(t.lease, t.sm.state.value)
            except CodedError:
                raise
            except OSError:
                self.dependency_status["checkpoint"] = "degraded"

    def _fail(self, t: Transfer, exc: BulkDataPlaneError) -> None:
        cls = classify(exc)
        self.metrics.inc("errors_total", code=exc.code, outcome=cls["outcome"])
        self.log.log("warning", "error", exc.message, tenant=pseudonym(self._diag_key, t.tenant), transfer_id=t.tid,
                     trace=t.trace, code=exc.code, outcome=cls["outcome"])

    # ------------------------------------------------------------ operations
    def create_transfer(self, token: Any, manifest: Mapping[str, Any], *, transfer_id: str,
                        traceparent: str | None = None, dest_region: str | None = None,
                        transport: str | None = None, timeout: float | None = None) -> dict[str, Any]:
        check_id(transfer_id)
        trace = TraceContext.parse(traceparent, self.e["telemetry.trace_sample_ratio"])
        p = self._principal(token, "create-transfer", None, transfer_id)
        tenant = p.tenant
        if self.admission.frozen:
            self._decide(None, "admission", "reject", "admission_frozen", {"transfer_id": transfer_id}, {"freeze": True}, {})
            raise CodedError("admission_frozen", "admission is frozen by operator")
        if tenant in self.quarantined_tenants:
            raise CodedError("quarantined", "tenant is quarantined")
        # Precedence (POLICY_PRECEDENCE.md): security > residency > integrity > safety limits > SLO > cost.
        check_residency(dest_region or self.region, self.e["security.allowed_regions"], self.tenant_regions.get(tenant))
        tv = time.perf_counter()
        m = validate_manifest(manifest, limits=self.limits)
        self.metrics.observe("manifest_validate_seconds", time.perf_counter() - tv)
        with self._lock:
            if transfer_id in self.transfers:
                existing = self.transfers[transfer_id]
                if existing.manifest["object"] == m["object"] and existing.tenant == tenant:
                    return self._describe(existing)   # idempotent create
                raise CodedError("resume_conflict", "transfer id already bound to another manifest/tenant")
        mode = shm.select_transport(transport or self.e["transport.mode"], self.e["transport.require_zero_copy"], self.caps)
        try:
            grant = self.admission.acquire(tenant, m["size"], timeout=self.e["timeouts.admission"] if timeout is None else timeout)
        except CodedError as exc:
            self._decide(None, "admission", "reject", exc.code, {"transfer_id": transfer_id, "tenant": pseudonym(self._diag_key, tenant),
                                                                 "bytes": m["size"]},
                         {"quota": vars(self.admission.quota(tenant))}, self.admission.metrics()["limits"])
            self.metrics.inc("admission_rejected_total", reason=exc.details.get("reason", exc.code) if exc.details else exc.code)
            raise
        sm = StateMachine()
        t = Transfer(transfer_id, tenant, m, sm, grant, trace, transport=mode)
        sm.on_transition = lambda a, ev, b, r: self.metrics.inc("transitions_total", to=b.value)
        sm.fire(Event.VALIDATE)
        try:
            if mode == "shm":
                t.region = shm.SharedRegion(m["size"], transfer_id=transfer_id, tenant=tenant, key=self._key,
                                            max_mapped=self.e["limits.max_mapped_bytes"])
                t.zc = shm.ZeroCopyReceiver(m, t.region.buf, limits=self.limits, counter=t.counter)
            elif self.store:
                t.lease = self.store.acquire(transfer_id, self.node)
                self.store.create(t.lease, m, tenant=tenant, meta={"trace_id": trace.trace_id})
            else:
                t.mem = Receiver(m, self.limits)
        except BaseException:
            self.admission.release(grant)
            if t.region:
                t.region.close()
            sm.fire(Event.REJECT, "resource_setup_failed")
            raise
        sm.fire(Event.VALIDATED)
        if m["chunk_count"] == 0:
            sm.fire(Event.ALL_CHUNKS)
        with self._lock:
            self.transfers[transfer_id] = t
        self._decide(t, "admission", "admit", "ok", {"bytes": m["size"], "tenant": pseudonym(self._diag_key, tenant)},
                     {"quota": vars(self.admission.quota(tenant))}, {"active": self.admission.metrics()["active"]})
        self._decide(t, "transport_select", f"select:{mode}", "capability_probe",
                     {"requested": transport or self.e["transport.mode"]}, {"require_zero_copy": self.e["transport.require_zero_copy"]},
                     {"shared_memory": self.caps.get("shared_memory"), "host_guest": self.caps.get("host_guest")})
        self.metrics.inc("transfers_created_total", transport=mode)
        self.metrics.set("transfers_active", self.admission.metrics()["active"])
        self.audit.append("transfer.create", {"sub": p.sub, "tenant": tenant, "transfer_id": transfer_id, "object": m["object"]})
        self.log.log("info", "create", "transfer admitted", tenant=pseudonym(self._diag_key, tenant), transfer_id=transfer_id,
                     trace=trace, transport=mode, size=m["size"])
        return self._describe(t)

    def _describe(self, t: Transfer) -> dict[str, Any]:
        out = {"transfer_id": t.tid, "state": t.sm.state.value, "transport": t.transport,
               "traceparent": t.trace.child().header()}
        if t.region is not None:
            out["descriptor"] = t.region.descriptor()
        return out

    def region_view(self, token: Any, tid: str) -> memoryview:
        """Producer-side writable view (attach-buffer capability)."""
        t = self._get(tid)
        self._principal(token, "attach-buffer", t.tenant, tid)
        if t.region is None:
            raise CodedError("unsupported_capability", "transfer is not using shared memory")
        return t.region.buf

    def accept_chunk(self, token: Any, tid: str, index: int, payload: Any = None) -> dict[str, Any]:
        """Copy path: ``payload`` bytes.  Shm path: payload is None and the chunk
        is already in the region (``commit``)."""
        t = self._get(tid)
        self._principal(token, "write-chunk", t.tenant, tid)
        t0 = time.perf_counter()
        with t.lock:
            if t.sm.state in (Lifecycle.COMPLETE_UNVERIFIED, Lifecycle.VERIFIED) and index in t.verified:
                self.metrics.inc("duplicate_chunks_total")
                return {"index": index, "new": False, "state": t.sm.state.value, "verified": len(t.verified)}
            if t.sm.state in (Lifecycle.READY, Lifecycle.DISCONNECTED, Lifecycle.FAILED_RETRYABLE):
                t.sm.fire({Lifecycle.READY: Event.CHUNK, Lifecycle.DISCONNECTED: Event.RECONNECT,
                           Lifecycle.FAILED_RETRYABLE: Event.RETRY}[t.sm.state], "chunk_arrival")
            elif t.sm.state is Lifecycle.RECEIVING:
                t.sm.fire(Event.CHUNK)
            else:
                t.sm.fire(Event.CHUNK)  # raises illegal_transition with the current state
            try:
                if t.zc is not None:
                    if payload is not None:
                        raise CodedError("invalid_manifest", "shm transfers commit in place; payload must be None")
                    new = t.zc.commit(index)
                elif t.mem is not None:
                    before = len(t.mem.received)
                    t.mem.accept(index, payload)
                    new = len(t.mem.received) > before
                    t.counter.copy(len(_require_bytes(payload)))  # Receiver stores tobytes()
                else:
                    new = self._accept_durable(t, index, payload)
            except DigestMismatch as exc:
                self._fail(t, exc)
                self.metrics.inc("digest_failures_total", level="chunk")
                raise
            except OSError as exc:
                t.sm.fire(Event.RETRYABLE_ERROR, "checkpoint_io")
                self.dependency_status["checkpoint"] = "degraded"
                raise CodedError("timeout", "checkpoint write failed; retry", error=type(exc).__name__) from None
            if new:
                t.verified.add(index)
                t.last_progress = time.monotonic()
                self.metrics.inc("chunks_verified_total")
                self.metrics.inc("bytes_verified_total", self._chunk_len(t, index))
            else:
                self.metrics.inc("duplicate_chunks_total")
                self.metrics.inc("bytes_resent_total", self._chunk_len(t, index))
            if len(t.verified) == t.manifest["chunk_count"] and t.sm.state is Lifecycle.RECEIVING:
                t.sm.fire(Event.ALL_CHUNKS)
                self._persist_state(t)
        self.metrics.observe("chunk_accept_seconds", time.perf_counter() - t0)
        return {"index": index, "new": new, "state": t.sm.state.value, "verified": len(t.verified)}

    def _chunk_len(self, t: Transfer, i: int) -> int:
        return _expected_chunk_length(t.manifest["size"], t.manifest["chunk"], i, t.manifest["chunk_count"])

    def _accept_durable(self, t: Transfer, index: int, payload: Any) -> bool:
        m = t.manifest
        view = _require_bytes(payload, "payload")
        if type(index) is not int or not 0 <= index < m["chunk_count"]:
            raise DigestMismatch("chunk index is not in the manifest", index=index)
        if len(view) != self._chunk_len(t, index):
            raise DigestMismatch("chunk length does not match manifest geometry", index=index)
        if not hmac.compare_digest(hashlib.sha256(view).hexdigest(), m["chunks"][index]):
            raise DigestMismatch("chunk does not verify", index=index)
        if index in t.verified:
            return False
        self.store.write_chunk(t.lease, index, index * m["chunk"], view, t.verified | {index}, t.sm.state.value)
        t.counter.copy(len(view))  # durable write is a required copy into storage
        return True

    def resume_token(self, token: Any, tid: str) -> dict[str, Any]:
        t = self._get(tid)
        self._principal(token, "read-progress", t.tenant, tid)
        body = {"schema": RESUME2_SCHEMA, "transfer_id": tid, "manifest_object": t.manifest["object"],
                "verified": sorted(t.verified), "epoch": t.lease.epoch if t.lease else 0, "issued_at": time.time()}
        body["mac"] = hmac.new(self._key, json.dumps(body, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        self.metrics.observe("resume_token_seconds", time.time() - body["issued_at"])
        return body

    def reconcile(self, token: Any, tid: str, peer: Mapping[str, Any], *, max_age: float = 86400.0) -> dict[str, Any]:
        """Reconnect handshake: validate the peer's resume token and return the
        authoritative missing set.  Local verified progress always wins."""
        t = self._get(tid)
        self._principal(token, "resume", t.tenant, tid)
        body = dict(peer)
        mac = body.pop("mac", "")
        if body.get("schema") == RESUME2_SCHEMA:
            expect = hmac.new(self._key, json.dumps(body, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(str(mac), expect):
                raise SecurityRejected("authentication_failed", "resume token invalid")
            if time.time() - float(body.get("issued_at", 0)) > max_age:
                raise CodedError("resume_conflict", "stale resume token")
            if t.lease and body.get("epoch") not in (t.lease.epoch, t.lease.epoch - 1):
                raise CodedError("stale_owner", "resume token from superseded owner epoch")
        elif body.get("schema") != RESUME_SCHEMA:
            raise CodedError("version_incompatible", "unsupported resume schema", schema=body.get("schema"))
        if body.get("manifest_object") != t.manifest["object"] or body.get("transfer_id", tid) != tid:
            raise CodedError("resume_conflict", "resume token refers to a different object/transfer")
        claimed = set(body.get("verified", []))
        with t.lock:
            if t.sm.state is Lifecycle.DISCONNECTED:
                t.sm.fire(Event.RECONNECT, "reconcile")
            missing = [i for i in range(t.manifest["chunk_count"]) if i not in t.verified]
        disagreement = sorted(claimed - t.verified)
        self._decide(t, "resume_reconcile", "local_wins", "ok" if not disagreement else "peer_overclaims",
                     {"peer_claimed": len(claimed), "local_verified": len(t.verified)}, {"authority": "receiver"}, {})
        return {"missing": missing, "peer_overclaimed": disagreement[:1000]}

    def finalize(self, token: Any, tid: str) -> Any:
        t = self._get(tid)
        self._principal(token, "finalize", t.tenant, tid)
        t0 = time.perf_counter()
        with t.lock:
            if t.sm.state is Lifecycle.VERIFIED:
                return self._object(t)          # idempotent finalize
            if t.sm.state is not Lifecycle.COMPLETE_UNVERIFIED:
                missing = [i for i in range(t.manifest["chunk_count"]) if i not in t.verified]
                if missing:
                    raise TransferIncomplete("object is incomplete", missing=missing[:1000], missing_count=len(missing))
                t.sm.fire(Event.VERIFY_OK)      # raises illegal_transition
            try:
                obj = self._object(t, verify=True)
            except (DigestMismatch, CodedError) as exc:
                t.sm.fire(Event.VERIFY_FAIL, "final_verification_failed")
                self._persist_state(t)
                self._quarantine_transfer(t, "final_verification_failed")
                self.metrics.inc("digest_failures_total", level="object")
                self._decide(t, "quarantine", "quarantine", "object_digest_mismatch", {}, {"auto": True}, {})
                raise CodedError("object_digest_mismatch", "final verification failed; transfer quarantined") from exc
            t.sm.fire(Event.VERIFY_OK)
            self._persist_state(t)
        self.metrics.observe("finalize_seconds", time.perf_counter() - t0)
        self.metrics.inc("transfers_verified_total")
        self.audit.append("transfer.verified", {"transfer_id": tid, "object": t.manifest["object"]})
        return obj

    def _object(self, t: Transfer, verify: bool = False) -> Any:
        from .data_plane import verify_object

        if t.zc is not None:
            return t.zc.object_view()
        if t.mem is not None:
            return t.mem.assemble()
        data = self.store.read_object(t.tid)
        t.counter.copy(len(data))
        if verify:
            verify_object(t.manifest, data, limits=self.limits)
        return data

    def cancel(self, token: Any, tid: str, reason: str = "caller") -> dict[str, Any]:
        t = self._get(tid)
        self._principal(token, "cancel", t.tenant, tid)
        with t.lock:
            if t.sm.state in (Lifecycle.CANCELLING, Lifecycle.CANCELLED):
                return self._describe(t)
            t.sm.fire(Event.CANCEL, reason)
            self._release_resources(t, discard=True)
            t.sm.fire(Event.CANCEL_DONE)
        self.metrics.inc("transfers_cancelled_total")
        self.audit.append("transfer.cancel", {"transfer_id": tid, "reason": reason})
        return self._describe(t)

    def close(self, token: Any, tid: str) -> None:
        t = self._get(tid)
        self._principal(token, "finalize", t.tenant, tid)
        with t.lock:
            if t.sm.state is Lifecycle.CLOSED:
                return
            t.sm.fire(Event.CLOSE)
            self._release_resources(t, discard=t.sm.state is not Lifecycle.QUARANTINED)
            t.sm.fire(Event.CLOSE_DONE)
        with self._lock:
            self.transfers.pop(tid, None)

    def _release_resources(self, t: Transfer, *, discard: bool) -> None:
        if t.grant:
            self.admission.release(t.grant)
            t.grant = None
        if t.region is not None:
            t.zc = None  # drop in-place views before unmapping
            t.region.close()
        if t.mem is not None:
            t.mem.close(clear=True)
        if discard and self.store and t.lease:
            self.store.delete(t.tid)
        self.metrics.set("transfers_active", self.admission.metrics()["active"])

    # ------------------------------------------------------------ operator
    def _quarantine_transfer(self, t: Transfer, reason: str) -> None:
        if t.sm.state is not Lifecycle.QUARANTINED:
            t.sm.fire(Event.QUARANTINE, reason)
        if self.store and t.lease:
            self.store.quarantine(t.tid, reason=reason)
            t.lease = None
        if t.grant:
            self.admission.release(t.grant)
            t.grant = None
        self.audit.append("transfer.quarantine", {"transfer_id": t.tid, "reason": reason})
        self.metrics.inc("quarantines_total")

    def quarantine(self, admin_token: Any, tid: str, reason: str) -> None:
        t = self._get(tid)
        self._principal(admin_token, "quarantine", t.tenant, tid)
        with t.lock:
            self._quarantine_transfer(t, reason)

    def quarantine_tenant(self, admin_token: Any, tenant: str, on: bool = True) -> None:
        self._principal(admin_token, "quarantine", tenant, None)
        (self.quarantined_tenants.add if on else self.quarantined_tenants.discard)(tenant)
        self.audit.append("tenant.quarantine", {"tenant": tenant, "on": on})

    def release(self, admin_token: Any, tid: str) -> None:
        t = self._get(tid)
        self._principal(admin_token, "release", t.tenant, tid)
        t.sm.fire(Event.RELEASE, "operator_release")

    def freeze(self, admin_token: Any, on: bool = True) -> None:
        p = self._principal(admin_token, "freeze", "*", None)
        self.admission.freeze(on)
        self.audit.append("admission.freeze", {"sub": p.sub, "on": on})
        self._decide(None, "freeze", "freeze" if on else "unfreeze", "operator", {"sub": p.sub}, {}, {})

    # ------------------------------------------------------------ recovery
    def recover(self) -> list[str]:
        """Restart reconstruction from durable checkpoints.  Transfers resume in
        DISCONNECTED; corrupt checkpoints are quarantined by the store."""
        if not self.store:
            return []
        recovered = []
        for tid in self.store.list():
            try:
                st = self.store.load(tid)
            except CodedError as exc:
                self.metrics.inc("recovery_failures_total", code=exc.code)
                continue
            if st.get("lifecycle") in ("verified", "closed", "cancelled", "quarantined"):
                continue
            lease = self.store.acquire(tid, self.node)
            sm = StateMachine()
            for ev in (Event.VALIDATE, Event.VALIDATED, Event.DISCONNECT):
                sm.fire(ev, "recovered")
            try:
                grant = self.admission.acquire(st["tenant"], st["manifest"]["size"], timeout=0)
            except CodedError:
                grant = None
            t = Transfer(tid, st["tenant"], st["manifest"], sm, grant, TraceContext.new(), lease=lease,
                         verified=set(st["verified"]))
            if len(t.verified) == t.manifest["chunk_count"]:
                sm.fire(Event.RECONNECT)
                sm.fire(Event.ALL_CHUNKS)
            with self._lock:
                self.transfers[tid] = t
            recovered.append(tid)
            self.log.log("info", "recover", "transfer recovered", transfer_id=tid, verified=len(t.verified),
                         dropped=len(st.get("dropped_on_load", [])))
        self.metrics.inc("transfers_recovered_total", len(recovered))
        return recovered

    # ------------------------------------------------------------ health
    def sweep(self, now: float | None = None) -> dict[str, list[str]]:
        """Stall detection (C052): idle transfers -> DISCONNECTED; total-time
        exceeded -> FAILED_TERMINAL (timeout)."""
        now = time.monotonic() if now is None else now
        stalled, expired = [], []
        with self._lock:
            items = list(self.transfers.values())
        for t in items:
            with t.lock:
                if t.sm.state in (Lifecycle.RECEIVING, Lifecycle.READY) and now - t.last_progress > self.e["timeouts.idle_chunk"]:
                    t.sm.fire(Event.DISCONNECT, "idle_timeout")
                    stalled.append(t.tid)
                    self._decide(t, "stall_detect", "disconnect", "idle_timeout",
                                 {"idle_s": round(now - t.last_progress, 3)}, {"idle_chunk": self.e["timeouts.idle_chunk"]}, {})
                if t.sm.state in (Lifecycle.RECEIVING, Lifecycle.READY, Lifecycle.DISCONNECTED, Lifecycle.FAILED_RETRYABLE) \
                        and now - t.created > self.e["timeouts.total_transfer"]:
                    t.sm.fire(Event.TERMINAL_ERROR, "total_timeout")
                    expired.append(t.tid)
                    self._release_resources(t, discard=False)
        self.metrics.set("transfers_stalled", sum(1 for t in items if t.sm.state is Lifecycle.DISCONNECTED))
        return {"stalled": stalled, "expired": expired}

    def health(self) -> dict[str, Any]:
        if self.log.export_errors:
            self.dependency_status["telemetry_export"] = "degraded"
        adm = self.admission.metrics()
        degraded = [k for k, v in self.dependency_status.items() if v not in ("ok", "disabled")]
        self.metrics.set("admission_saturation", adm["saturation"])
        status = "frozen" if adm["frozen"] else ("degraded" if degraded or any(f.severity == "degraded" for f in self.cfg.findings) else "ok")
        self.metrics.set("health_ok", 1 if status == "ok" else 0)
        self.metrics.set("admission_frozen", 1 if adm["frozen"] else 0)
        return {"status": status, "live": True, "ready": not adm["frozen"] and self.cfg.admission_allowed,
                "version": self.lineage["version"], "artifact_digest": self.lineage["source_digest"],
                "config_digest": self.cfg.digest, "policy_digest": self._policy_digest(), "profile": self.e["profile"], "dependencies": dict(self.dependency_status),
                "capabilities": {k: self.caps.get(k) for k in ("shared_memory", "host_guest", "mode")},
                "limits": {k: v for k, v in self.e.items() if k.startswith("limits.")},
                "utilization": {"active": adm["active"], "pending": adm["pending"], "bytes_in_flight": adm["bytes_in_flight"],
                                "saturation": adm["saturation"]},
                "uptime_s": round(time.time() - self.started, 3)}

    @staticmethod
    def _policy_digest() -> str | None:
        from .precedence import load

        try:
            return load()["digest"]
        except (OSError, CodedError):
            return None

    def diagnostics(self, token: Any, tid: str) -> dict[str, Any]:
        t = self._get(tid)
        pr = self.authn.verify(token)
        p = self._principal(token, "inspect" if "inspect" in pr.actions else "read-progress", t.tenant, tid)
        show_tenant = "inspect" in p.actions
        return {"transfer_id": tid, "tenant": t.tenant if show_tenant else pseudonym(self._diag_key, t.tenant),
                **t.sm.snapshot(), "verified": len(t.verified), "chunks": t.manifest["chunk_count"],
                "transport": t.transport, "copies": t.counter.as_dict(), "trace_id": t.trace.trace_id}

    def explain(self, admin_token: Any, tid: str | None = None) -> str:
        self._principal(admin_token, "inspect", None, tid)
        return explain(self.decisions.for_transfer(tid) if tid else self.decisions.all())
