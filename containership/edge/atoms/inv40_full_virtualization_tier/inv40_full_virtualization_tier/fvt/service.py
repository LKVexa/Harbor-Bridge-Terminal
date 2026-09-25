"""FullVmService - the production boundary of INV-40 (REPO-003, C021-C030,
C040-C059, C071-C077).

Request path for every mutating call:
  schema -> authenticate -> authorize(op, tenant) -> fencing epoch ->
  quarantine check -> admission (concurrency/queue/quota) -> circuit breaker ->
  provider (bounded retry only when safe) -> reference runtime invariants
  (FullVm) -> journal (fsync) -> audit (hash chain) -> metrics/log/decision.

The unchanged v4.2.0 ``runtime.FullVm`` remains the single enforcement point
for primitive refusal, footprint ceiling, lifecycle and device exclusivity;
this layer never bypasses it.
"""
from __future__ import annotations

import json
import secrets
import threading
import time

from . import config as cfgmod
from . import schema
from ._rt import runtime
from .audit import AuditLog
from .errors import OpError, classify
from .fencing import LeaseTable
from .identity import Authenticator, KeyProvider, authorize
from .journal import Journal
from .provider import Provider
from .resilience import Admission, CircuitBreaker, Deadline, retry
from .telemetry import Decisions, Logger, Metrics, child_traceparent, parse_traceparent, tenant_label

VERSION = "4.3.0"


class FullVmService:
    def __init__(self, *, provider: Provider, keys: KeyProvider, state_dir, config: dict | None = None,
                 node: str = "node-0", leases: LeaseTable | None = None, clock=time.time,
                 log_sink=None, sleep=time.sleep):
        import pathlib
        self.state_dir = pathlib.Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config_store = cfgmod.ConfigStore(self.state_dir / "config")
        active = self.config_store.active()
        if config is not None:
            self.config_store.activate(cfgmod.layer(config), author="bootstrap", reason="service init")
        elif active is None:
            self.config_store.activate(cfgmod.layer(), author="bootstrap", reason="secure defaults")
        self.cfg = self.config_store.active()["config"]
        if self.cfg["environment"] == "prod" and not provider.production:
            raise OpError("PK_FULL_VM_CONFIG_INVALID", f"provider '{provider.name}' is not production-grade")
        self.provider, self.node, self.leases, self.sleep = provider, node, leases, sleep
        self.authn = Authenticator(keys, clock=clock)
        self.audit = AuditLog(self.state_dir / "audit.jsonl")
        self.journal = Journal(self.state_dir / "journal.wal")
        self.metrics, self.decisions = Metrics(), Decisions()
        self.log = Logger(node, sink=log_sink)
        self.registry = runtime.DeviceLeaseRegistry()
        self.admission = Admission(self.cfg["max_concurrent_ops"], self.cfg["max_queue"],
                                   self.cfg["tenant_guest_quota"], self.cfg["tenant_memory_quota_mib"])
        self.breaker = CircuitBreaker(self.cfg["breaker_failure_threshold"], self.cfg["breaker_reset_ms"])
        self.guests: dict[str, runtime.FullVm] = {}
        self.handles: dict[str, dict] = {}
        self.idem: dict[str, dict] = {}
        self.quarantined: dict[str, str] = {}   # scope ("tier" | "tenant:x" | "guest:id") -> reason
        self._lock = threading.RLock()
        self._booting: set[str] = set()
        self.started_at = time.time()
        self.recovered = self.recover()

    # ------------------------------------------------------------------ plumbing
    def _ctx(self, token, op, tenant, controller, epoch, trace_parent):
        trace_id, _ = parse_traceparent(trace_parent)
        try:
            p = self.authn.authenticate(token)
            authorize(p, op, tenant)
        except OpError as e:
            self.audit.append(actor="unknown" if e.code != "PK_FULL_VM_FORBIDDEN" else e.details.get("subject", "?"),
                              action=op, outcome="deny", code=e.code, tenant=tenant_label(tenant), trace_id=trace_id)
            self.metrics.inc("authz_denials", {"op": op, "code": e.code})
            self.decisions.record("authz", "deny", str(e), inputs={"op": op, "tenant": tenant_label(tenant)},
                                  policy="capability tokens: exact op + tenant", trace_id=trace_id)
            raise
        if self.leases is not None and op in {"create", "boot", "stop", "destroy"}:
            if controller is None or epoch is None:
                raise OpError("PK_FULL_VM_STALE_OWNER", "fencing token required")
            self.leases.check(controller, epoch)
        return p, trace_id

    def _quarantine_check(self, tenant, instance_id=None):
        for scope in ("tier", f"tenant:{tenant}", f"guest:{instance_id}"):
            if scope in self.quarantined:
                raise OpError("PK_FULL_VM_QUARANTINED", f"{scope} quarantined: {self.quarantined[scope]}", scope=scope)

    def _run(self, op, fn, *, principal, tenant, trace_id, **audit_fields):
        t0 = time.monotonic()
        span, child = child_traceparent(trace_id)
        try:
            out = fn(child)
            self.metrics.inc("ops_total", {"op": op, "result": "ok"})
            self.audit.append(actor=principal.sub, action=op, outcome="ok", tenant=tenant_label(tenant),
                              trace_id=trace_id, span=span, **audit_fields)
            self.log.log("info", op, "ok", tenant=tenant, trace_id=trace_id, span=span, **audit_fields)
            return out
        except Exception as exc:  # noqa: BLE001
            err = classify(exc)
            self.metrics.inc("ops_total", {"op": op, "result": err["code"]})
            self.audit.append(actor=principal.sub, action=op, outcome="error", code=err["code"],
                              tenant=tenant_label(tenant), trace_id=trace_id, span=span, **audit_fields)
            self.log.log("error", op, err["message"], tenant=tenant, trace_id=trace_id, code=err["code"])
            if isinstance(exc, OpError):
                raise
            raise OpError(err["code"], err["message"]) from exc
        finally:
            self.metrics.observe("op_latency_ms", int((time.monotonic() - t0) * 1000), {"op": op})

    def _guest(self, instance_id) -> runtime.FullVm:
        g = self.guests.get(instance_id)
        if g is None:
            raise OpError("PK_FULL_VM_INVALID_REQUEST", "unknown guest", instance_id=instance_id)
        return g

    # ------------------------------------------------------------------ API
    def create(self, token, request: dict | str | bytes, *, controller=None, epoch=None) -> dict:
        raw = request if isinstance(request, (str, bytes)) else json.dumps(request)
        try:
            req = schema.parse_and_validate(raw, "PK_FULL_VM_CREATE_REQUEST.v1")
        except schema.SchemaError as exc:
            self.metrics.inc("invalid_requests", {"op": "create"})
            raise OpError("PK_FULL_VM_INVALID_REQUEST", str(exc)) from None
        tenant = req["tenant"]
        p, trace_id = self._ctx(token, "create", tenant, controller, epoch, req.get("trace_parent"))
        ikey = f"{tenant}/{req['idempotency_key']}"
        with self._lock:
            if ikey in self.idem:
                prev = self.idem[ikey]
                if prev["request_digest"] != cfgmod.digest(req):
                    raise OpError("PK_FULL_VM_INVALID_REQUEST", "idempotency key reused with a different request")
                return dict(prev["result"], idempotent_replay=True)

        def do(_child):
            self._quarantine_check(tenant)
            approved = self.cfg["approved_image_digests"]
            if (approved or self.cfg["environment"] == "prod") and req["image_digest"] not in approved:
                self.decisions.record("image", "deny", "digest not on approved list",
                                      inputs={"digest": req["image_digest"]}, policy="approved_image_digests",
                                      trace_id=trace_id)
                raise OpError("PK_FULL_VM_INTEGRITY_FAILED", "image digest not approved")
            if req["memory_mib"] > self.cfg["footprint_ceiling_mib"]:
                raise OpError("PK_FULL_VM_FOOTPRINT_EXCEEDED", "requested memory above ceiling")
            devices = runtime.FULL_DEVICE_MODEL | frozenset(req.get("extra_devices", []))
            if "gpu" in " ".join(devices) and not self.cfg["allow_gpu_passthrough"]:
                raise OpError("PK_FULL_VM_FORBIDDEN", "GPU passthrough disabled by policy")
            self.admission.reserve(tenant, req["memory_mib"])
            vm = runtime.FullVm(req["name"], tenant, req["memory_mib"], devices=devices,
                                instance_id="vm-" + secrets.token_hex(8))
            with self._lock:
                self.guests[vm.instance_id] = vm
            self.journal.append({"op": "create", "instance_id": vm.instance_id, "name": vm.name, "tenant": tenant,
                                 "memory_mib": vm.memory_mib, "state": "created", "image": req["image_digest"],
                                 "devices": sorted(devices)})
            res = {"schema": "PK_FULL_VM/1", "instance_id": vm.instance_id, "guest": vm.name, "tenant": tenant,
                   "state": vm.state, "memory_mib": vm.memory_mib, "devices": len(vm.devices),
                   "footprint_ceiling_mib": self.cfg["footprint_ceiling_mib"], "trace_id": trace_id}
            with self._lock:
                self.idem[ikey] = {"request_digest": cfgmod.digest(req), "result": res}
            return res
        return self._run("create", do, principal=p, tenant=tenant, trace_id=trace_id)

    def boot(self, token, instance_id: str, *, controller=None, epoch=None, trace_parent=None,
             deadline_ms: int | None = None) -> dict:
        vm = self._guest(instance_id)
        p, trace_id = self._ctx(token, "boot", vm.tenant, controller, epoch, trace_parent)

        def do(_child):
            self._quarantine_check(vm.tenant, instance_id)
            with self._lock:   # D-01: one boot in flight per guest, else N hypervisors launch
                if instance_id in self._booting or vm.state == "running":
                    raise OpError("PK_FULL_VM_INVALID_STATE", "boot already in flight or guest running")
                self._booting.add(instance_id)
            try:
                return _boot()
            finally:
                with self._lock:
                    self._booting.discard(instance_id)

        def _boot():
            dl = Deadline(deadline_ms or self.cfg["op_timeout_ms"])
            self.admission.acquire(timeout_s=dl.remaining_ms() / 1000.0)
            try:
                self.breaker.before()
                probe = self.provider.probe()
                if not probe.usable:
                    self.metrics.inc("primitive_refusals")
                    self.decisions.record("boot", "refuse", "hardware primitive unavailable",
                                          inputs={"reasons": probe.reasons, "guest": instance_id},
                                          policy="require_hardware_primitive=true; no software fallback",
                                          trace_id=trace_id)
                spec = {"name": vm.name, "instance_id": instance_id, "memory_mib": vm.memory_mib}

                def launch():
                    return self.provider.launch(spec)
                handle = None
                if probe.usable:
                    try:
                        handle = retry(launch, attempts=self.cfg["retry_max_attempts"], idempotent=True,
                                       deadline=dl, sleep=self.sleep,
                                       on_retry=lambda n, e, d: self.metrics.inc("retries", {"code": e.code}))
                        self.breaker.success()
                    except OpError as e:
                        if e.code in {"PK_FULL_VM_PROVIDER_UNAVAILABLE", "PK_FULL_VM_PROVIDER_FAILED",
                                      "PK_FULL_VM_TIMEOUT", "PK_FULL_VM_GUEST_START_FAILED"}:
                            self.breaker.failure()
                        raise
                try:
                    res = vm.start(primitive_usable=probe.usable,
                                   elapsed_ms=int(handle["elapsed_ms"]) if handle else 0,
                                   resident_mib=int(handle["resident_mib"]) if handle else 0,
                                   registry=self.registry)
                except Exception:
                    if handle is not None:   # never orphan a privileged hypervisor process
                        self.provider.destroy(handle)
                    raise
                self.handles[instance_id] = handle
                self.journal.append({"op": "boot", "instance_id": instance_id, "state": "running",
                                     "boot_ms": res["boot_ms"], "resident_mib": res["resident_mib"]})
                self.metrics.observe("boot_ms", res["boot_ms"], {"status": res["status"]})
                self.metrics.set("resident_mib", res["resident_mib"], {"guest": instance_id})
                if res["status"] == "degraded":
                    self.decisions.record("boot", "degraded", "boot exceeded budget",
                                          inputs={"boot_ms": res["boot_ms"], "budget_ms": res["budget_ms"]},
                                          policy="boot_budget_ms", trace_id=trace_id)
                return res
            finally:
                self.admission.release()
        return self._run("boot", do, principal=p, tenant=vm.tenant, trace_id=trace_id, guest=instance_id)

    def stop(self, token, instance_id, *, controller=None, epoch=None, trace_parent=None) -> dict:
        vm = self._guest(instance_id)
        p, trace_id = self._ctx(token, "stop", vm.tenant, controller, epoch, trace_parent)

        def do(_c):
            h = self.handles.pop(instance_id, None)
            if vm.state == "running" and h is not None:
                self.provider.stop(h)
            res = vm.stop()
            self.journal.append({"op": "stop", "instance_id": instance_id, "state": "stopped"})
            return res
        return self._run("stop", do, principal=p, tenant=vm.tenant, trace_id=trace_id, guest=instance_id)

    def destroy(self, token, instance_id, *, controller=None, epoch=None, trace_parent=None) -> dict:
        vm = self._guest(instance_id)
        p, trace_id = self._ctx(token, "destroy", vm.tenant, controller, epoch, trace_parent)

        def do(_c):
            h = self.handles.pop(instance_id, None)
            if h is not None:
                self.provider.destroy(h)
            was = vm.state
            res = vm.destroy()
            if was != "destroyed":
                self.admission.unreserve(vm.tenant, vm.memory_mib)
                self.journal.append({"op": "destroy", "instance_id": instance_id, "state": "destroyed"})
            return res
        return self._run("destroy", do, principal=p, tenant=vm.tenant, trace_id=trace_id, guest=instance_id)

    def quarantine(self, token, scope: str, reason: str, *, lift=False) -> dict:
        tenant = scope.split(":", 1)[1] if scope.startswith("tenant:") else \
            self._guest(scope.split(":", 1)[1]).tenant if scope.startswith("guest:") else "*"
        p = self.authn.authenticate(token)
        if tenant == "*":
            if p.kind == "service" or "admin" not in p.ops:
                raise OpError("PK_FULL_VM_FORBIDDEN", "tier quarantine needs admin")
        else:
            authorize(p, "quarantine", tenant)
        with self._lock:
            if lift:
                self.quarantined.pop(scope, None)
            else:
                self.quarantined[scope] = reason
                if scope.startswith("guest:"):
                    iid = scope.split(":", 1)[1]
                    h = self.handles.pop(iid, None)
                    if h is not None:
                        self.provider.destroy(h)
                    if self.guests[iid].state == "running":
                        self.guests[iid].stop()
        did = self.decisions.record("quarantine", "lift" if lift else "apply", reason,
                                    inputs={"scope": scope}, policy="operator control", trace_id=None)
        self.audit.append(actor=p.sub, action="quarantine", outcome="ok", scope=scope, lift=lift, reason=reason)
        return {"scope": scope, "quarantined": not lift, "decision": did}

    # ------------------------------------------------------------------ recovery
    def recover(self) -> dict:
        """Restart semantics: journaled guests are rebuilt; any guest journaled
        'running' whose hypervisor handle did not survive is reconciled to
        'stopped' (leases released), never assumed alive."""
        st = self.journal.state()
        reconciled = 0
        for iid, r in st.items():
            if "tenant" not in r:
                continue
            devices = frozenset(r.get("devices") or runtime.FULL_DEVICE_MODEL)
            vm = runtime.FullVm(r["name"], r["tenant"], r["memory_mib"], devices=devices, instance_id=iid)
            if r.get("state") in {"running", "stopped"}:
                vm.state = "stopped"
                if r.get("state") == "running":
                    reconciled += 1
                    self.journal.append({"op": "reconcile", "instance_id": iid, "state": "stopped"})
            self.guests[iid] = vm
            self.admission.reserve(r["tenant"], r["memory_mib"])
        return {"guests": len(st), "reconciled_to_stopped": reconciled, "torn_tail": self.journal.torn_tail}

    # ------------------------------------------------------------------ observability
    def health(self) -> dict:
        probe = self.provider.probe()
        running = sum(1 for g in self.guests.values() if g.state == "running")
        self.metrics.set("full_vm_instances", running, {"state": "running"})
        prov = self.config_store.active()["provenance"]
        return {"component": "INV-40", "version": VERSION, "node": self.node,
                "live": True, "ready": probe.usable and self.breaker.state != "open" and "tier" not in self.quarantined,
                "primitive": {"usable": probe.usable, "reasons": probe.reasons},
                "provider": {"name": self.provider.name, "production": self.provider.production},
                "breaker": self.breaker.state,
                "config": {"digest": prov["digest"], "generation": prov["generation"],
                           "config_version": prov["config_version"], "environment": self.cfg["environment"]},
                "capabilities": sorted(k for k in ("allow_nested_virtualization", "allow_gpu_passthrough",
                                                   "allow_live_migration") if self.cfg[k]),
                "dependencies": {"telemetry_sink_failures": self.log.sink_failures,
                                 "key_service": self.authn.keys.available},
                "admission": {"in_flight": self.admission.in_flight, "waiting": self.admission.waiting,
                              "shed": self.admission.shed},
                "guests": {"total": len(self.guests), "running": running},
                "quarantine": dict(self.quarantined), "audit_head": self.audit.head(),
                "recovered": self.recovered}
