"""INV-27 service facade: authenticated admission and supervised execution.

Brings together: authn/authz (MC-024/025), admission control + load shedding (MC-053), deadlines
(MC-026), quarantine / emergency disable (MC-058, MC-035), per-tenant quotas (MC-018), idempotent
run keyed by (tenant, idempotency_key) (MC-057), fencing tokens against split-brain controllers
(MC-057), lifecycle (MC-016), journal + restart reconciliation (MC-056), tamper-evident audit
(MC-048), metrics/logs/trace (MC-070..072), decision records and explain (MC-074/075), and a
health/readiness/version endpoint (MC-069).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field

from . import lifecycle
from .admission import AdmittedImage, SitePolicy, admit
from .audit import AuditLog
from .authz import Authenticator, authorize
from .errors import UkError
from .resilience import Admission, Deadline
from .telemetry import Logger, Metrics, TraceContext
from .vmm import LaunchSpec, Supervisor

VERSION = "4.3.0"


@dataclass
class Instance:
    instance_id: str
    tenant: str
    image_ref: str
    seal: dict
    state: str = "pending"
    history: list = field(default_factory=list)
    running: object = None
    idempotency_key: str | None = None


class _NullStream:
    def write(self, _s: str) -> int:
        return 0


class Journal:
    """Append-only JSONL journal; each line carries the sha256 of the previous line (MC-056)."""

    def __init__(self, path: str | None, key: bytes | None = None) -> None:
        # key: HMAC key from the host secret store.  Without it the chain detects edits but not a full
        # re-chain by someone with write access (v4.3.0 review finding) - production must pass a key.
        self.path = path
        self.key = key
        self._lock = threading.Lock()
        self._prev = "0" * 64
        if path and os.path.exists(path):
            for rec in self.replay():
                self._prev = rec["_h"]

    def append(self, rec: dict) -> None:
        if not self.path:
            return
        with self._lock:
            body = {**rec, "_prev": self._prev}
            h = self._digest(body)
            line = json.dumps({**body, "_h": h}, sort_keys=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._prev = h

    def _digest(self, body: dict) -> str:
        raw = json.dumps(body, sort_keys=True).encode()
        return hmac.new(self.key, raw, hashlib.sha256).hexdigest() if self.key else hashlib.sha256(raw).hexdigest()

    def replay(self) -> list[dict]:
        out, prev = [], "0" * 64
        if not self.path or not os.path.exists(self.path):
            return out
        with open(self.path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        for i, line in enumerate(lines):
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                if i == len(lines) - 1 or (i == len(lines) - 2 and lines[-1] == ""):
                    break           # torn final write: ignore the partial tail (crash consistency)
                raise UkError("UK_STATE_CORRUPT", f"journal line {i + 1} is not JSON")
            if not isinstance(rec, dict) or rec.get("_prev") != prev:
                raise UkError("UK_STATE_CORRUPT", f"journal chain broken at line {i + 1}")
            body = {k: v for k, v in rec.items() if k != "_h"}
            if not hmac.compare_digest(self._digest(body), str(rec.get("_h"))):
                raise UkError("UK_STATE_CORRUPT", f"journal line {i + 1} hash mismatch")
            prev = rec["_h"]
            out.append(rec)
        return out


class UnikernelService:
    def __init__(self, policy: SitePolicy, supervisor: Supervisor, authn: Authenticator, *,
                 max_instances_per_tenant: int = 16, admission: Admission | None = None,
                 audit: AuditLog | None = None, metrics: Metrics | None = None, logger: Logger | None = None,
                 journal_path: str | None = None, journal_key: bytes | None = None, boot_deadline_s: float = 10.0) -> None:
        self.policy = policy
        self.supervisor = supervisor
        self.authn = authn
        self.quota = max_instances_per_tenant
        self.admission = admission or Admission(rate_per_s=50, burst=20, max_inflight=32)
        self.audit = audit or AuditLog()
        self.metrics = metrics or Metrics()
        self.logger = logger or Logger(stream=_NullStream())
        self.journal = Journal(journal_path, journal_key)
        self.boot_deadline_s = boot_deadline_s
        self.instances: dict[str, Instance] = {}
        self.by_key: dict[tuple, str] = {}
        self.quarantined_images: set = set()
        self.quarantined_tenants: set = set()
        self.disabled = False
        self.fence = 0
        self.decisions: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._reconcile()

    # ---------------------------------------------------------------- admin
    def set_fence(self, token: int) -> None:
        with self._lock:
            if token <= self.fence:
                raise UkError("UK_STALE_FENCE", f"fence {token} <= current {self.fence}")
            self.fence = token

    def _check_fence(self, token: int | None) -> None:
        if token is not None and token != self.fence:
            raise UkError("UK_STALE_FENCE", f"caller fence {token} != {self.fence}")

    def disable(self, token: str, reason: str) -> None:
        p = self.authn.authenticate(token)
        authorize(p, "component.disable")
        self.disabled = True
        self.audit.emit(p.sub, "component.disable", "INV-27", "ok", {"reason": reason})

    def enable(self, token: str, reason: str) -> None:
        p = self.authn.authenticate(token)
        authorize(p, "component.disable")
        self.disabled = False
        self.audit.emit(p.sub, "component.enable", "INV-27", "ok", {"reason": reason})

    def quarantine(self, token: str, *, image_ref: str | None = None, tenant: str | None = None,
                   reason: str = "") -> list[str]:
        """Freeze an image digest or tenant: blocks new runs and stops matching running instances."""
        p = self.authn.authenticate(token)
        authorize(p, "instance.quarantine")
        stopped = []
        with self._lock:
            if image_ref:
                self.quarantined_images.add(image_ref)
            if tenant:
                self.quarantined_tenants.add(tenant)
            victims = [i for i in self.instances.values() if i.state == "running"
                       and (i.image_ref == image_ref or i.tenant == tenant)]
        for inst in victims:
            self._transition(inst, "quarantined", "UK_QUARANTINED")
            self._stop(inst, "UK_QUARANTINED")
            stopped.append(inst.instance_id)
        self.audit.emit(p.sub, "quarantine", image_ref or tenant or "?", "ok", {"reason": reason, "stopped": stopped})
        return stopped

    # ---------------------------------------------------------------- core
    def run(self, token: str, *, tenant: str, image_bytes: bytes, bound_digest: str, manifest, envelope,
            idempotency_key: str, fence: int | None = None, deadline_ms: int = 5000,
            traceparent: str | None = None, now: dt.datetime | None = None) -> Instance:
        trace = TraceContext.parse(traceparent)
        t0 = time.perf_counter()
        p = self.authn.authenticate(token)
        authorize(p, "image.admit", tenant=tenant)
        authorize(p, "instance.run", tenant=tenant)
        if self.disabled:
            raise UkError("UK_DISABLED")
        self._check_fence(fence)
        if not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key) <= 128:
            raise UkError("UK_INVALID_REQUIREMENT", "idempotency_key 8..128 chars required")
        with self._lock:
            existing = self.by_key.get((tenant, idempotency_key))
            if existing:
                inst = self.instances[existing]
                if inst.image_ref != "sha256:" + hashlib.sha256(image_bytes).hexdigest():
                    raise UkError("UK_INSTANCE_DUPLICATE", "idempotency key reused for a different image")
                return inst
        deadline = Deadline.after(deadline_ms)
        with self.admission.admit(tenant):
            if tenant in self.quarantined_tenants:
                raise UkError("UK_QUARANTINED", "tenant quarantined")
            try:
                adm = admit(image_bytes, bound_digest=bound_digest, manifest=manifest, envelope=envelope,
                            policy=self.policy, tenant=tenant, now=now)
            except UkError as e:
                dec = e.details.get("decision", {})
                did = str(uuid.uuid4())
                self.decisions[did] = dec
                self.metrics.inc("uk_seal_failures_total", reason=e.code)
                self.metrics.inc("uk_images_admitted_total", outcome="refused")
                self.audit.emit(p.sub, "image.admit", dec.get("image") or "?", "refused",
                                {"code": e.code, "decision_id": did, "tenant": tenant})
                self.logger.log("warn", "admit", e.message, tenant=tenant, decision_id=did, trace=trace, code=e.code)
                e.details["decision_id"] = did
                raise
            deadline.check()
            if adm.blob.ref in self.quarantined_images:
                raise UkError("UK_QUARANTINED", "image digest quarantined")
            with self._lock:
                if (tenant, idempotency_key) in self.by_key:   # lost a race with an identical request
                    raise UkError("UK_INSTANCE_DUPLICATE", "concurrent request with the same idempotency key")
                live = sum(1 for i in self.instances.values() if i.tenant == tenant
                           and i.state in ("pending", "verified", "starting", "running", "quarantined"))
                # (v4.3.0 fix: counting only starting/running let concurrent runs overcommit the quota)
                if live >= self.quota:
                    raise UkError("UK_QUOTA_EXCEEDED", f"{live} >= {self.quota}")
                inst = Instance(str(uuid.uuid4()), tenant, adm.blob.ref, dict(adm.seal), idempotency_key=idempotency_key)
                self.instances[inst.instance_id] = inst
                self.by_key[(tenant, idempotency_key)] = inst.instance_id
            self.decisions[inst.instance_id] = adm.decision
            self._transition(inst, "verified", "UK_OK")
            self.metrics.inc("uk_images_admitted_total", outcome="admitted", toolchain=adm.facts.toolchain)
            self.metrics.observe("uk_syscall_set_size", float(len(adm.facts.syscalls)))
            self.audit.emit(p.sub, "image.admit", adm.blob.ref, "admitted",
                            {"instance": inst.instance_id, "tenant": tenant, "seal": dict(adm.seal)})
            self._start(inst, adm, trace)
        self.metrics.observe("uk_run_latency_ms", (time.perf_counter() - t0) * 1000)
        return inst

    def _start(self, inst: Instance, adm: AdmittedImage, trace) -> None:
        self._transition(inst, "starting", "UK_OK")
        spec = LaunchSpec(inst.instance_id, adm.blob, adm.facts.architecture, adm.manifest.boot.memory_mib,
                          adm.manifest.boot.vcpus, adm.manifest.boot.cmdline, adm.manifest.boot.ready_marker,
                          adm.plan, self.boot_deadline_s)
        try:
            inst.running, plan = self.supervisor.launch(spec)
        except UkError as e:
            self._transition(inst, "failed", e.code)
            self._transition(inst, "stopped", e.code)
            self.audit.emit("inv27", "instance.start", inst.instance_id, "failed", {"code": e.code})
            raise
        self._transition(inst, "running", "UK_OK")
        self.metrics.set("uk_unikernel_instances", self._count(inst.tenant), tenant=inst.tenant)
        self.audit.emit("inv27", "instance.start", inst.instance_id, "running", {"argv0": plan["argv"][0],
                                                                                 "backend": plan["backend"]})
        self.logger.log("info", "start", "instance running", tenant=inst.tenant, decision_id=inst.instance_id, trace=trace)

    def stop(self, token: str, instance_id: str, *, fence: int | None = None) -> Instance:
        p = self.authn.authenticate(token)
        inst = self.instances.get(instance_id)
        if inst is None:
            raise UkError("UK_UNKNOWN_INSTANCE")
        authorize(p, "instance.stop", tenant=inst.tenant)
        self._check_fence(fence)
        if inst.state == "stopped":
            return inst                       # idempotent
        self._transition(inst, "stopping", "UK_OK")
        self._stop(inst, "UK_OK")
        self.audit.emit(p.sub, "instance.stop", instance_id, "stopped", {})
        return inst

    def _stop(self, inst: Instance, reason: str) -> None:
        if inst.state == "quarantined":
            self._transition(inst, "stopping", reason)
        if inst.running is not None:
            self.supervisor.stop(inst.running)
        if inst.state != "stopped":
            self._transition(inst, "stopped", reason)
        self.metrics.set("uk_unikernel_instances", self._count(inst.tenant), tenant=inst.tenant)

    def _count(self, tenant: str) -> int:
        return sum(1 for i in self.instances.values() if i.tenant == tenant and i.state == "running")

    def _transition(self, inst: Instance, target: str, reason: str) -> None:
        with self._lock:
            lifecycle.check(inst.state, target)
            inst.history.append({"from": inst.state, "to": target, "reason": reason, "ts": time.time()})
            inst.state = target
            self.journal.append({"instance": inst.instance_id, "tenant": inst.tenant, "image": inst.image_ref,
                                 "state": target, "reason": reason, "key": inst.idempotency_key})

    def _reconcile(self) -> None:
        """On restart: rebuild instances from the journal.  No VMM process survives a controller restart
        (process group owned by this controller), so any non-terminal instance is failed -> stopped."""
        last: dict[str, dict] = {}
        for rec in self.journal.replay():
            last[rec["instance"]] = rec
        for iid, rec in last.items():
            inst = Instance(iid, rec["tenant"], rec["image"], {}, state=rec["state"], idempotency_key=rec.get("key"))
            self.instances[iid] = inst
            if rec.get("key"):
                self.by_key[(rec["tenant"], rec["key"])] = iid
            if inst.state in ("starting", "running", "quarantined", "stopping", "verified", "pending"):
                if inst.state in ("starting", "running"):
                    self._transition(inst, "failed", "UK_STATE_CORRUPT")
                    self._transition(inst, "stopped", "UK_STATE_CORRUPT")
                elif inst.state in ("quarantined",):
                    self._transition(inst, "stopping", "UK_STATE_CORRUPT")
                    self._transition(inst, "stopped", "UK_STATE_CORRUPT")
                elif inst.state == "stopping":
                    self._transition(inst, "stopped", "UK_STATE_CORRUPT")
                else:
                    self._transition(inst, "rejected", "UK_STATE_CORRUPT")

    # ---------------------------------------------------------------- observability
    def health(self) -> dict:
        now = dt.datetime.now(dt.timezone.utc)
        try:
            self.policy.trust.check_fresh(now)
            trust = "fresh"
        except UkError:
            trust = "stale"
        try:
            vmm = self.supervisor.backend.probe()
        except UkError as e:
            vmm = f"unavailable: {e.code}"
        ready = not self.disabled and trust == "fresh" and not vmm.startswith("unavailable")
        return {"schema": "PK_UNIKERNEL_STATUS/1", "component": "INV-27", "version": VERSION,
                "live": True, "ready": ready, "disabled": self.disabled, "trust_root": trust,
                "trust_root_version": self.policy.trust.version, "vmm": vmm,
                "config_revision": self.policy.config_revision, "fence": self.fence,
                "instances": {s: sum(1 for i in self.instances.values() if i.state == s) for s in lifecycle.TRANSITIONS},
                "audit_head": list(self.audit.head()), "inflight": self.admission.inflight}

    def explain(self, decision_or_instance_id: str) -> str:
        dec = self.decisions.get(decision_or_instance_id)
        if dec is None:
            raise UkError("UK_UNKNOWN_INSTANCE", "no decision recorded under that id")
        from .explain import render
        return render(dec)
