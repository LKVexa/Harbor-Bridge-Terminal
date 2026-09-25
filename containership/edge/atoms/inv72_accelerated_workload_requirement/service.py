"""Governed INV-72 service: the one entry point that composes every v4.3.0 control.

``AcceleratorService.request()`` pipeline (each step fails closed; order is part of the contract):

  disabled? -> authenticate -> authorize(capability, tenant) -> admission -> deadline/cancel ->
  schema + config limits -> precedence (security/residency over cost) -> inventory (fresh | degraded | stale) ->
  atomic decide+reserve (quota, quarantine, fencing, idempotency) -> audit -> metrics/log/trace -> record

Every call returns a PK_ACCEL_MATCH/1 document (or raises ``AccelError`` whose ``to_dict()`` is a
PK_ACCEL_ERROR/1 document).  Decisions are retained in a bounded ring so ``explain()`` can show the
operator the inputs, policy, inventory generation, config generation and rationale behind any decision
(C076, C077), with release lineage attached (C078).
"""
from __future__ import annotations

import collections
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from . import compat
from .audit import AuditLog
from .config import ConfigStore
from .discovery import InventoryCache
from .errors import AccelError, REGISTRY
from .matcher import (InventoryValidationError, LimitExceededError, RequirementValidationError)
from .precedence import Claim, resolve
from .resilience import Admission, CancelToken, Deadline
from .schema_check import check
from .state import ReservationStore
from .telemetry import Logger, Metrics, TraceContext
from .trust import Authenticator, Principal, authorize

CAPABILITIES_ADVERTISED = ("PK_ACCEL_REQ/1", "PK_ACCEL_INVENTORY/1", "PK_ACCEL_MATCH/1", "PK_ACCEL_ERROR/1",
                           "PK_ACCEL_STATUS/1", "idempotency", "fencing", "quarantine", "explain", "degraded-offline")


@dataclass
class Lineage:
    """Release lineage attached to every decision (C078)."""
    component_version: str = compat.COMPONENT_VERSION
    release_manifest_sha256: str | None = None
    workload_release: str | None = None


@dataclass
class AcceleratorService:
    config: ConfigStore
    inventory: InventoryCache
    store: ReservationStore
    auth: Authenticator | None
    audit: AuditLog = field(default_factory=AuditLog)
    metrics: Metrics = field(default_factory=Metrics)
    logger: Logger = field(default_factory=Logger)
    lineage: Lineage = field(default_factory=Lineage)
    clock: Callable[[], float] = time.time
    decisions_kept: int = 1000
    stall_after_s: float = 60.0
    _admission: Admission | None = None
    _admission_cfg: int | None = None
    _decisions: collections.OrderedDict = field(default_factory=collections.OrderedDict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    disabled: str | None = None
    last_progress: float = field(default_factory=time.time)
    fence: int = 0

    # ------------------------------------------------------------------ helpers
    def _adm(self) -> Admission:
        gen = self.config.active
        if self._admission is None or self._admission_cfg != (gen.number if gen else None):
            a = self.config.get()["admission"]
            self._admission = Admission(a["rate_per_s"], a["burst"], a["max_inflight"])
            self._admission_cfg = gen.number if gen else None
        return self._admission

    def _principal(self, token: str | None, capability: str, tenant: str | None) -> Principal:
        cfg = self.config.get()
        if self.auth is None:
            if cfg.get("require_authentication", True):
                raise AccelError("ACCEL_DEPENDENCY_UNAVAILABLE", "authentication required but no authenticator")
            p = Principal("anonymous-far-edge", frozenset({"*"}), frozenset({"accel.match", "accel.reserve",
                                                                             "accel.release", "accel.read"}))
        else:
            p = self.auth.authenticate(token or "")
        authorize(p, capability, tenant)
        return p

    def _record(self, doc: dict, ctx: dict) -> None:
        with self._lock:
            self._decisions[doc["decision_id"]] = {"decision": doc, **ctx}
            while len(self._decisions) > self.decisions_kept:
                self._decisions.popitem(last=False)

    # ------------------------------------------------------------------ public API
    def request(self, req: Mapping[str, Any], *, token: str | None = None, traceparent: str | None = None,
                cancel: CancelToken | None = None, reserve: bool = True) -> dict:
        t0 = time.perf_counter()
        trace = TraceContext.parse(traceparent)
        decision_id = f"dec-{uuid.uuid4().hex[:16]}"
        tenant = req.get("tenant") if isinstance(req, Mapping) else None
        actor = "unauthenticated"
        try:
            if self.disabled:
                raise AccelError("ACCEL_DISABLED", self.disabled)
            if not isinstance(req, Mapping):
                raise AccelError("ACCEL_INVALID_REQUIREMENT", "requirement must be an object")
            req = compat.accept_request(dict(req))
            principal = self._principal(token, "accel.reserve" if reserve else "accel.match",
                                        tenant if isinstance(tenant, str) else None)
            actor = principal.name
            with self._adm().admit(str(tenant)):
                deadline = Deadline.after(req.get("deadline_ms", 1000))
                errs = check(req, "PK_ACCEL_REQ-1")
                if errs:
                    code = "ACCEL_LIMIT_EXCEEDED" if any("maximum" in e or "longer" in e or "more than" in e
                                                         for e in errs) else "ACCEL_INVALID_REQUIREMENT"
                    raise AccelError(code, "; ".join(errs[:3]))
                cfg = self.config.get()
                if req.get("count", 1) > cfg["limits"]["max_count"]:
                    raise AccelError("ACCEL_LIMIT_EXCEEDED", f"count exceeds profile max_count {cfg['limits']['max_count']}")
                rationale_pre, core = [], dict(req)
                if core.get("isolation") == "shared" and not cfg.get("allow_shared_partitions", True):
                    res = resolve([Claim("security", "deny", f"profile {cfg['profile']} forbids shared partitions"),
                                   Claim("cost", "allow", "caller asked to share a partition")])
                    core["isolation"] = "dedicated"
                    rationale_pre.append(f"precedence: {res['by']} {res['action']} - {res['reason']}; isolation forced to dedicated")
                (cancel or CancelToken()).check()
                deadline.check()
                devices, inv = self.inventory.current()
                if len(devices) > cfg["limits"]["max_inventory"]:
                    raise AccelError("ACCEL_LIMIT_EXCEEDED", "inventory exceeds profile max_inventory")
                degraded = ["inventory-offline-grace"] if inv["state"] == "degraded" else []
                allowed = req.get("allowed_nodes")
                if allowed is not None:
                    devices = [d for d in devices if d.node in set(allowed)]
                    rationale_pre.append(f"residency: restricted to {len(set(allowed))} allowed node(s)")
                quota = cfg["quotas"].get("per_tenant", {}).get(tenant, cfg["quotas"]["default_devices_per_tenant"])
                (cancel or CancelToken()).check()
                deadline.check()
                if reserve:
                    rsv, dec = self.store.reserve(core, devices, fence=self.fence, quota=quota)
                else:
                    from .matcher import decide
                    rsv = None
                    dec = decide(core, self.store.overlay(devices), reserve=False, excluded=self.store.excluded())
                    if dec["selected"] is not None and self.store.tenant_device_count(tenant) + len(dec["selected"]) > quota:
                        dec = {**dec, "selected": None, "code": "ACCEL_QUOTA_EXCEEDED",
                               "reasons": dec["reasons"] + [{"code": "ACCEL_QUOTA_EXCEEDED", "device": None,
                                                            "text": f"tenant quota {quota} device(s) would be exceeded"}]}
            outcome = ("degraded" if degraded else "success") if dec["selected"] is not None else "refused"
            doc = {"schema": "PK_ACCEL_MATCH/1", "decision_id": decision_id, "outcome": outcome,
                   "selected": dec["selected"], "code": dec.get("code"),
                   "reasons": [{"code": r["code"], "device": r["device"], "text": r["text"]} for r in dec["reasons"]],
                   "rationale": rationale_pre + list(dec.get("rationale", [])),
                   "reservation_id": rsv.reservation_id if rsv else None,
                   "inventory_generation": inv["generation"], "config_generation": self.config.active.number,
                   "trace_id": trace.trace_id, "degraded": degraded, "component_version": compat.COMPONENT_VERSION}
            self._record(doc, {"request": dict(req), "effective": core, "principal": actor, "inventory": inv,
                               "config_digest": self.config.active.digest, "quota": quota,
                               "lineage": vars(self.lineage).copy(), "at": self.clock()})
            self.audit.emit(actor, "accel.reserve" if reserve else "accel.match", decision_id, outcome,
                            {"tenant": tenant, "selected": dec["selected"], "code": dec.get("code"),
                             "reservation": doc["reservation_id"]})
            self.metrics.inc("accel_matched_total" if dec["selected"] else "accel_refused_total",
                             cls=core.get("class"), reason=dec.get("code") or "ok")
            if rsv:
                self.metrics.inc("accel_reserved_total")
            self.logger.log("info", "request", outcome, tenant=tenant, workload=req.get("workload"),
                            decision_id=decision_id, trace=trace, code=dec.get("code"))
            return doc
        except (RequirementValidationError, InventoryValidationError, LimitExceededError) as e:
            err = AccelError(e.code, str(e))
            self._fail(err, actor, decision_id, tenant, trace)
            raise err from e
        except AccelError as e:
            self._fail(e, actor, decision_id, tenant, trace)
            raise
        finally:
            self.last_progress = self.clock()
            self.metrics.observe("accel_decision_latency_ms", (time.perf_counter() - t0) * 1000)
            self._gauges()

    def _fail(self, e: AccelError, actor: str, decision_id: str, tenant: Any, trace: TraceContext) -> None:
        if e.code == "ACCEL_OVERLOADED":
            self.metrics.inc("accel_shed_total")
        self.metrics.inc("accel_errors_total", code=e.code)
        self.audit.emit(actor, "accel.request", decision_id, e.code, {"tenant": tenant, "message": e.message})
        self.logger.log("warn" if e.retryable else "error", "request", e.message,
                        tenant=tenant if isinstance(tenant, str) else None, decision_id=decision_id,
                        trace=trace, code=e.code)

    def _gauges(self) -> None:
        try:
            self.metrics.set("accel_active_reservations", len(self.store.active()))
            self.metrics.set("accel_quarantined_devices", len(self.store.quarantined))
            age = self.inventory.age()
            self.metrics.set("accel_inventory_age_seconds", age if age is not None else -1)
            if self._admission:
                self.metrics.set("accel_inflight", self._admission.inflight)
        except Exception:  # gauges never break a decision
            pass

    def release(self, reservation_id: str, *, tenant: str, token: str | None = None) -> dict:
        p = self._principal(token, "accel.release", tenant)
        r = self.store.release(reservation_id, tenant=tenant, fence=self.fence)
        self.audit.emit(p.name, "accel.release", reservation_id, "released", {"tenant": tenant})
        self.metrics.inc("accel_released_total")
        return r.to_dict()

    # ------------------------------------------------------------------ operator controls (C059, C092)
    def quarantine(self, dev_id: str, reason: str, *, token: str | None = None, revoke: bool = False) -> list:
        p = self._principal(token, "accel.operate", None)
        out = self.store.revoke_device(dev_id, reason, fence=self.fence) if revoke else (
            self.store.quarantine(dev_id, reason, fence=self.fence) or [])
        self.audit.emit(p.name, "accel.quarantine", dev_id, "revoked" if revoke else "quarantined",
                        {"reason": reason, "revoked": out})
        return out

    def drain(self, dev_id: str, reason: str, *, token: str | None = None) -> None:
        p = self._principal(token, "accel.operate", None)
        self.store.drain(dev_id, reason, fence=self.fence)
        self.audit.emit(p.name, "accel.drain", dev_id, "draining", {"reason": reason})

    def disable(self, reason: str, *, token: str | None = None) -> None:
        p = self._principal(token, "accel.operate", None)
        self.disabled = reason or "emergency disable"
        self.audit.emit(p.name, "accel.disable", "INV-72", "disabled", {"reason": reason})

    def enable(self, *, token: str | None = None) -> None:
        p = self._principal(token, "accel.operate", None)
        self.disabled = None
        self.audit.emit(p.name, "accel.enable", "INV-72", "enabled", {})

    def take_leadership(self, fence: int) -> None:
        """A new controller instance advances the fence; older instances' writes are then refused."""
        self.store.advance_fence(fence)
        self.fence = fence

    # ------------------------------------------------------------------ read side (C052, C071, C077)
    def status(self) -> dict:
        inv = self.inventory.status()
        gen = self.config.active
        reasons = []
        if self.disabled:
            reasons.append(f"disabled: {self.disabled}")
        if gen is None:
            reasons.append("no active configuration")
        if inv["state"] in ("empty", "stale"):
            reasons.append(f"inventory {inv['state']}")
        stalled = (self._admission is not None and self._admission.inflight > 0
                   and self.clock() - self.last_progress > self.stall_after_s)
        if stalled:
            reasons.append(f"stalled: no progress for > {self.stall_after_s:g}s with requests in flight")
        doc = {"schema": "PK_ACCEL_STATUS/1", "component": "INV-72", "version": compat.COMPONENT_VERSION,
               "live": not stalled, "ready": not reasons, "reasons": reasons,
               "config_generation": gen.number if gen else None, "inventory": inv,
               "dependencies": {"discovery": inv["state"], "authenticator": "configured" if self.auth else "absent",
                                "telemetry_log_failures": self.logger.failures},
               "capabilities": list(CAPABILITIES_ADVERTISED), "disabled": bool(self.disabled), "stalled": stalled}
        return doc

    def explain(self, decision_id: str, *, token: str | None = None) -> str:
        self._principal(token, "accel.read", None)
        rec = self._decisions.get(decision_id)
        if rec is None:
            raise AccelError("ACCEL_UNKNOWN_RESERVATION", f"decision {decision_id} not retained")
        from .explain import render
        return render(rec)

    def decision_record(self, decision_id: str) -> dict | None:
        return self._decisions.get(decision_id)


def outcome_of(code: str | None) -> str:
    return "success" if code is None else REGISTRY[code].outcome
