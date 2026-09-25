"""SCH-01 4.3.0 scheduler service - the governed placement path.

Composes the missing components into one decision path:

  admission (MC-21/30) -> service state (MC-33) -> authn (MC-19) -> authz (MC-20)
  -> idempotency (MC-21) -> classification from governed config (MC-16/22)
  -> attestation (MC-25) -> hard filters incl. deployment context (MC-07), latency (MC-12),
     topology (MC-13), residency/data path (MC-14), accelerators (MC-15), runtime (MC-11),
     occupancy isolation (MC-26), quota/fair share (MC-10)
  -> deterministic scoring -> fenced durable reservation (MC-31/32) -> audit (MC-27)
  -> metrics/logs/traces (MC-38..40) -> PK_PLACEMENT/2 with explanation (MC-41).

The 4.2.0 ``engine.place`` API is unchanged and remains the v1 contract.
"""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from . import lifecycle
from .allocators import AcceleratorPool, QuotaLedger
from .audit import AuditLedger
from .config import ConfigStore
from .engine import REQUIRED_TIER, TIER_ORDER
from .errors import SchedulerError, from_exception
from .model import DEPLOYMENT_CONTEXTS, NodeSpec, Occupant, PlacementRequest
from .resilience import AdmissionController, CircuitBreaker, IdempotencyCache, RequestContext
from .security import AttestationVerifier, Authenticator, SecretProvider, authorize
from .state import FencingAuthority, Journal
from .telemetry import Logger, Metrics, Tracer

PLACEMENT_SCHEMA = "PK_PLACEMENT/2"
HARDWARE_ISOLATED = frozenset({"microvm", "vm"})
_PKG = Path(__file__).resolve().parent


def release_lineage() -> dict[str, str]:
    ver = (_PKG / "VERSION").read_text(encoding="utf-8").strip()
    h = hashlib.sha256()
    for name in ("engine.py", "scheduler.py", "model.py", "config.py"):
        h.update((_PKG / name).read_bytes())
    return {"version": ver, "decision_code_sha256": h.hexdigest()}


class Scheduler:
    def __init__(self, *, secrets: SecretProvider, state_dir: str | Path, clock: Callable[[], int],
                 attestation: AttestationVerifier, config: ConfigStore | None = None,
                 fencing: FencingAuthority | None = None, audit_path: str | Path | None = None):
        self.clock = clock
        self.secrets = secrets
        self.state_dir = Path(state_dir); self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or ConfigStore(secrets, at=clock())
        self.authn = Authenticator(secrets, clock=clock)
        self.attest = attestation
        self.fencing = fencing or FencingAuthority(self.state_dir / "epoch")
        self.audit = AuditLedger(audit_path or self.state_dir / "audit.jsonl", secrets)
        self.metrics, self.log, self.tracer = Metrics(), Logger(), Tracer()
        adm = self.config.get("admission"); brk = self.config.get("breaker")
        self.admission = AdmissionController(adm["max_inflight"])
        self.breaker = CircuitBreaker("attestation", brk["failure_threshold"], brk["reset_after"], clock)
        self.idem = IdempotencyCache()
        self.nodes: dict[str, NodeSpec] = {}
        self._proven: dict[str, tuple[frozenset[str] | None, int]] = {}
        self.quarantined: set[str] = set()
        self.leases: dict[str, dict[str, Any]] = {}
        self.accel = AcceleratorPool()
        self.quota = self._new_quota()
        self._lock = threading.RLock()
        self.state = "STARTING"
        self.epoch = 0
        self.last_decision_at = -1
        self.journal = Journal(self.state_dir / "journal.jsonl")
        self._recover()

    # ------------------------------------------------------------ lifecycle
    def _new_quota(self) -> QuotaLedger:
        return QuotaLedger(self.config.get("tenant_quota"), self.config.get("default_quota"),
                           self.config.get("fair_share_max_fraction"))

    def _set_state(self, dst: str) -> None:
        lifecycle.check(lifecycle.SERVICE_TRANSITIONS, self.state, dst)
        self.state = dst
        self.metrics.gauge("service_state", lifecycle.SERVICE_STATES.index(dst))

    def _recover(self) -> None:
        self._set_state("RECOVERING")
        self.epoch = self.fencing.acquire()
        self.leases = self.journal.replay()
        for lid, lease in self.leases.items():
            if lease["state"] not in lifecycle.TERMINAL:
                self.quota.reserve(lease["tenant"], lease["slots"])
                self.accel.lease(lease["node"], [_Dev(d) for d in lease.get("devices", [])], lid)  # type: ignore[arg-type]
        self.audit.append("service.recover", "system", {"epoch": self.epoch, "leases": len(self.leases)}, self.clock())
        self._set_state("READY")

    # ------------------------------------------------------------ node registry
    def report_node(self, token: Mapping[str, Any], spec: NodeSpec) -> None:
        p = self.authn.authenticate(token)
        authorize(p, "node.report")
        if p.kind != "node" or p.subject != spec.name:
            raise SchedulerError("FORBIDDEN", "a node may only report for itself")
        spec.report.validate()
        proven: frozenset[str] | None = None
        if spec.attestation is not None:
            # verified once at ingest (anti-replay counter advances here); freshness re-checked at use
            try:
                proven = self.breaker.call(lambda: self.attest.verify(spec.name, spec.report.tiers,
                                                                      spec.attestation, self.clock()))
            except SchedulerError as e:
                if e.code == "CIRCUIT_OPEN":
                    raise
                self.audit.append("node.attestation_failed", p.subject, {"node": spec.name, "code": e.code,
                                                                         "why": str(e)}, self.clock())
                proven = None
        with self._lock:
            self.nodes[spec.name] = spec
            self._proven[spec.name] = (proven, (spec.attestation or {}).get("evidence", {}).get("at", -1))
        self.metrics.inc("node_reports")

    # ------------------------------------------------------------ operator controls (MC-33)
    def operator(self, token: Mapping[str, Any], action: str, *, node: str | None = None, reason: str = "") -> str:
        p = self.authn.authenticate(token)
        op = {"freeze": "admin.freeze", "unfreeze": "admin.freeze", "disable": "admin.disable",
              "enable": "admin.disable", "quarantine": "admin.quarantine", "unquarantine": "admin.quarantine"}.get(action)
        if op is None:
            raise SchedulerError("INVALID_REQUEST", f"unknown operator action {action!r}")
        authorize(p, op)
        if p.kind != "human":
            raise SchedulerError("FORBIDDEN", "operator controls require a human principal")
        if not reason.strip():
            raise SchedulerError("INVALID_REQUEST", "operator actions require a reason")
        with self._lock:
            if action == "freeze": self._set_state("FROZEN")
            elif action == "unfreeze": self._set_state("READY")
            elif action == "disable": self._set_state("DISABLED")
            elif action == "enable": self._set_state("READY")
            elif action == "quarantine":
                if not node: raise SchedulerError("INVALID_REQUEST", "node required")
                self.quarantined.add(node)
            elif action == "unquarantine":
                self.quarantined.discard(node or "")
        self.audit.append(f"operator.{action}", p.subject, {"node": node, "reason": reason}, self.clock())
        return self.state

    # ------------------------------------------------------------ health (MC-37)
    def health(self) -> dict[str, Any]:
        try:
            self.fencing.check(self.epoch); fenced = False
        except SchedulerError:
            fenced = True
        try:
            self.secrets.get("audit"); secrets_ok = True
        except SchedulerError:
            secrets_ok = False
        ready = self.state == "READY" and not fenced and secrets_ok and self.breaker.state != "OPEN"
        return {"schema": "PK_SCHEDULER_HEALTH/1", "state": "FENCED" if fenced else self.state,
                "live": self.state != "STOPPED", "ready": ready, **release_lineage(),
                "config_rev": self.config.active.rev, "config_digest": self.config.active.digest,
                "dependencies": {"secret_provider": "ok" if secrets_ok else "unavailable",
                                 "attestation_breaker": self.breaker.state, "fencing": "lost" if fenced else "held"},
                "capabilities": sorted(["latency-aware", "topology-aware", "residency", "accelerators",
                                        "quota-fair-share", "attestation", "durable-journal", "fencing"]),
                "inflight": self.admission.inflight, "nodes": len(self.nodes), "active_leases":
                    sum(1 for l in self.leases.values() if l["state"] not in lifecycle.TERMINAL)}

    # ------------------------------------------------------------ placement
    def classify(self, req: PlacementRequest) -> dict[str, Any]:
        w = req.workload
        trust = self.config.get("provenance_trust").get(w.provenance)
        if trust is None:
            raise SchedulerError("UNKNOWN_PROVENANCE", f"{w.name}: unknown provenance",
                                 details={"provenance": w.provenance})
        latency = "interactive" if w.latency_sensitive else "batch"
        return {"schema": "PK_WORKLOAD_CLASS/1", "workload": w.name, "trust_class": trust,
                "required_tier": REQUIRED_TIER[trust], "latency_class": latency, "hardware": sorted(w.needs)}

    def _reserved_since(self, node: str, reported_at: int) -> int:
        return sum(l["slots"] for l in self.leases.values()
                   if l["node"] == node and l["state"] not in lifecycle.TERMINAL and l["issued_at"] >= reported_at)

    def _effective_free(self, spec: NodeSpec) -> int:
        return spec.report.free_slots - self._reserved_since(spec.name, spec.report.reported_at)

    def _occupants(self, node: str) -> list[Occupant]:
        return [l["occupant"] for l in self.leases.values()
                if l["node"] == node and l["state"] not in lifecycle.TERMINAL and "occupant" in l]

    def evaluate(self, req: PlacementRequest, klass: Mapping[str, Any], spec: NodeSpec, now: int
                 ) -> tuple[tuple[str, ...], dict[str, Any]]:
        """Return (rejection codes, facts) for one node.  Pure w.r.t. scheduler state."""
        w, r = req.workload, spec.report
        reasons: list[str] = []
        facts: dict[str, Any] = {}
        ctx = DEPLOYMENT_CONTEXTS[spec.context]
        if spec.name in self.quarantined: reasons.append("NODE_QUARANTINED")
        if spec.environment != req.environment: reasons.append("ENVIRONMENT_MISMATCH")
        if not spec.connected and not ctx["disconnected_ok"]: reasons.append("NODE_DISCONNECTED")
        if r.thermally_excluded: reasons.append("THERMALLY_EXCLUDED")
        if self._effective_free(spec) < req.slots: reasons.append("NO_FREE_SLOTS")
        bound = min(ctx["max_report_age"], self.config.get("freshness_bound")) if spec.context in ("cloud", "datacenter") \
            else ctx["max_report_age"]
        if r.reported_at > now: reasons.append("REPORT_FROM_FUTURE")
        elif now - r.reported_at > bound: reasons.append("STALE_REPORT")
        if w.site_affinity and r.site != w.site_affinity: reasons.append("SITE_MISMATCH")
        if not w.needs <= r.capabilities: reasons.append("MISSING_CAPABILITY")
        # attestation: the tiers we may rely on are only those the evidence proves
        tiers = r.tiers
        if self.config.get("require_attestation"):
            proven, at = self._proven.get(spec.name, (None, -1))
            if proven is None:
                reasons.append("ATTESTATION_FAILED"); tiers = frozenset()
            elif now - at > self.attest.max_age:
                reasons.append("ATTESTATION_STALE"); tiers = frozenset()
            else:
                tiers = proven
        floor = TIER_ORDER.index(klass["required_tier"])
        sufficient = [t for t in TIER_ORDER[floor:] if t in tiers and t in spec.runtimes]
        if req.runtime:
            sufficient = [t for t in sufficient if spec.runtimes.get(t) == req.runtime]
        if not any(t in tiers for t in TIER_ORDER[floor:]):
            reasons.append("INSUFFICIENT_TIER")
        elif not sufficient:
            reasons.append("NO_RUNTIME")
        facts["tier"] = sufficient[0] if sufficient else None
        if req.residency and spec.jurisdiction not in req.residency: reasons.append("RESIDENCY")
        if req.dataset and req.dataset not in spec.data_paths: reasons.append("DATA_PATH")
        if req.anti_affinity_zone and spec.zone == req.anti_affinity_zone: reasons.append("ANTI_AFFINITY")
        if klass["latency_class"] == "interactive" and req.origin_site:
            budget = self.config.get("latency_budget_ms").get("interactive")
            rtt = spec.latency_ms.get(req.origin_site)
            facts["rtt_ms"] = rtt
            if rtt is None or rtt > budget: reasons.append("LATENCY_BUDGET")
        if req.accelerators:
            devs = self.accel.pick(spec.name, spec.accelerators, req.accelerators)
            if devs is None: reasons.append("NO_ACCELERATOR")
            facts["devices"] = devs or []
        # MC-26 occupancy isolation: cross-tenant co-location only when both sides are
        # hardware-isolated, attested, and on distinct tier instances.
        if any(t != w.tenant for t in r.occupants.values()):
            reasons.append("TENANT_ISOLATION")   # legacy occupants carry no isolation metadata
        others = [o for o in self._occupants(spec.name) if o.tenant != w.tenant]
        if others and not (facts["tier"] in HARDWARE_ISOLATED
                           and all(o.attested and o.tier in HARDWARE_ISOLATED for o in others)):
            reasons.append("TENANT_ISOLATION")
        return tuple(dict.fromkeys(reasons)), facts

    def _score(self, klass, spec: NodeSpec, facts, req: PlacementRequest) -> tuple:
        wts = self.config.get("features")
        lat = facts.get("rtt_ms") if (klass["latency_class"] == "interactive" and wts["latency_aware"]) else 0
        topo = 0 if (not wts["topology_aware"] or not req.preferred_zone or spec.zone == req.preferred_zone) else 1
        return (TIER_ORDER.index(facts["tier"]), lat or 0, topo, -self._effective_free(spec), spec.name)

    def place(self, token: Mapping[str, Any], req: PlacementRequest, ctx: RequestContext,
              traceparent: str | None = None) -> dict[str, Any]:
        span = self.tracer.start("sch01.place", traceparent, workload=req.workload.name)
        t0 = time.perf_counter()
        tenant = req.workload.tenant
        try:
            with self.admission:
                out = self._place(token, req, ctx, span)
            self.metrics.inc("placements", {"outcome": "placed", "tier": out["tier"], "trust": out["trust_class"]})
            self.log.emit("INFO", "placement", request_id=ctx.request_id, trace_id=span["trace_id"],
                          span_id=span["span_id"], workload=req.workload.name, tenant=tenant, node=out["node"],
                          operation="place", decision=out["result_class"], config_rev=self.config.active.rev)
            self.tracer.end(span, "OK", node=out["node"])
            return out
        except BaseException as exc:  # noqa: BLE001 - boundary translation
            err = from_exception(exc)
            self.metrics.inc("placement_refusals", {"code": err.code})
            self.log.emit("WARN", "placement_refused", request_id=ctx.request_id, trace_id=span["trace_id"],
                          span_id=span["span_id"], workload=req.workload.name, tenant=tenant, operation="place",
                          decision=lifecycle.result_class(err.code), code=err.code, config_rev=self.config.active.rev)
            self.tracer.end(span, "ERROR", code=err.code)
            raise err from None
        finally:
            self.metrics.observe("placement_seconds", time.perf_counter() - t0)

    def _place(self, token, req: PlacementRequest, ctx: RequestContext, span) -> dict[str, Any]:
        if self.state == "DISABLED": raise SchedulerError("SCHEDULER_DISABLED", "scheduler disabled by operator")
        if self.state == "FROZEN": raise SchedulerError("FROZEN", "placements frozen by operator")
        if self.state not in ("READY", "DEGRADED"): raise SchedulerError("OVERLOADED", f"scheduler {self.state}")
        p = self.authn.authenticate(token)
        authorize(p, "placement.request", req.workload.tenant)
        body = _request_body(req)
        prior = self.idem.lookup(ctx.idempotency_key, body)
        if prior is not None:
            return prior
        now = self.clock()
        ctx.check(now)
        if now < self.last_decision_at:
            raise SchedulerError("INVALID_REQUEST", "clock regression detected; refusing to decide")
        klass = self.classify(req)
        with self._lock:
            if any(l["workload"] == req.workload.name and l["state"] not in lifecycle.TERMINAL
                   for l in self.leases.values()):
                raise SchedulerError("DUPLICATE_LEASE", f"{req.workload.name} already holds a lease")
            specs = sorted(self.nodes.values(), key=lambda s: s.name)
            evaluated = [(s, *self.evaluate(req, klass, s, now)) for s in specs]
            viable = [(s, f) for s, rs, f in evaluated if not rs]
            counts: dict[str, int] = {}
            for _, rs, _ in evaluated:
                for code in rs: counts[code] = counts.get(code, 0) + 1
            if not viable:
                raise SchedulerError("NO_CANDIDATE", f"{req.workload.name}: no node satisfies the hard constraints",
                                     details={"required_tier": klass["required_tier"], "candidate_count": len(specs),
                                              "rejection_counts": dict(sorted(counts.items()))})
            fleet = sum(max(0, self._effective_free(s)) for s in specs) + sum(
                l["slots"] for l in self.leases.values() if l["state"] not in lifecycle.TERMINAL)
            self.quota.check(req.workload.tenant, req.slots, fleet)
            spec, facts = min(viable, key=lambda sf: self._score(klass, sf[0], sf[1], req))
            sc = self._score(klass, spec, facts, req)
            ctx.check(self.clock())   # never commit past the deadline
            lease_id = hashlib.sha256(f"{req.workload.name}|{spec.name}|{now}|{self.journal.seq}".encode()).hexdigest()[:24]
            tier = facts["tier"]
            devices = facts.get("devices", [])
            occ = Occupant(req.workload.name, req.workload.tenant, klass["trust_class"], tier,
                           f"{spec.name}/{tier}/{lease_id}", spec.runtimes[tier], tuple(d.device_id for d in devices),
                           attested=bool(self.config.get("require_attestation")))
            lease = {"lease_id": lease_id, "workload": req.workload.name, "tenant": req.workload.tenant,
                     "node": spec.name, "tier": tier, "slots": req.slots, "issued_at": now,
                     "expires": now + self.config.get("lease_ticks"), "devices": [d.device_id for d in devices],
                     "epoch": self.epoch}
            # fenced, durable commit: journal first, then in-memory state
            self.fencing.guarded(self.epoch, lambda: self.journal.append(
                self.epoch, {"type": "reserve", "lease_id": lease_id, "lease": lease}))
            self.leases[lease_id] = dict(lease, state="RESERVED", occupant=occ)
            self.quota.reserve(req.workload.tenant, req.slots)
            if devices: self.accel.lease(spec.name, devices, lease_id)
            self.last_decision_at = now
        degraded = []
        if req.preferred_zone and spec.zone != req.preferred_zone: degraded.append("PREFERRED_ZONE_UNMET")
        result = {
            "schema": PLACEMENT_SCHEMA, "workload": req.workload.name, "tenant": req.workload.tenant,
            "node": spec.name, "site": spec.report.site, "zone": spec.zone, "tier": tier,
            "runtime": spec.runtimes[tier], "trust_class": klass["trust_class"],
            "latency_class": klass["latency_class"], "lease_id": lease_id, "lease_issued_at": now,
            "lease_expires": lease["expires"], "devices": lease["devices"], "jurisdiction": spec.jurisdiction,
            "candidates_total": len(specs), "candidates_considered": len(viable),
            "result_class": "DEGRADED_SUCCESS" if degraded else "SUCCESS", "degraded": degraded,
            "decision": {"strategy": "tier/latency/topology/free-slots/name", "score": list(sc)},
            "explain": {"config_rev": self.config.active.rev, "config_digest": self.config.active.digest,
                        "rejection_counts": dict(sorted(counts.items())), "rtt_ms": facts.get("rtt_ms"),
                        "epoch": self.epoch, "trace_id": span["trace_id"], **release_lineage()},
        }
        self.audit.append("placement.reserve", p.subject, {"lease_id": lease_id, "workload": req.workload.name,
                                                             "node": spec.name, "tier": tier}, now)
        self.idem.store(ctx.idempotency_key, body, result)
        return result

    # ------------------------------------------------------------ lease lifecycle
    def transition(self, token, lease_id: str, dst: str) -> dict[str, Any]:
        p = self.authn.authenticate(token)
        with self._lock:
            lease = self.leases.get(lease_id)
            if lease is None: raise SchedulerError("NOT_FOUND", "unknown lease")
            authorize(p, "placement.release", lease["tenant"])
            lifecycle.check(lifecycle.TRANSITIONS, lease["state"], dst)
            ev = {"RELEASED": "release", "ADMITTED": "admit", "RUNNING": "run", "REVOKED": "revoke"}[dst]
            self.fencing.guarded(self.epoch, lambda: self.journal.append(self.epoch, {"type": ev, "lease_id": lease_id}))
            lease["state"] = dst
            if dst in lifecycle.TERMINAL: self._free(lease)
        self.audit.append(f"lease.{ev}", p.subject, {"lease_id": lease_id}, self.clock())
        return {k: v for k, v in lease.items() if k != "occupant"}

    def expire(self) -> list[str]:
        now, out = self.clock(), []
        with self._lock:
            for lid, lease in self.leases.items():
                if lease["state"] == "RESERVED" and now >= lease["expires"]:
                    self.fencing.guarded(self.epoch, lambda lid=lid: self.journal.append(
                        self.epoch, {"type": "expire", "lease_id": lid}))
                    lease["state"] = "EXPIRED"; self._free(lease); out.append(lid)
        for lid in out:
            self.audit.append("lease.expire", "system", {"lease_id": lid}, now)
        return out

    def _free(self, lease):
        self.quota.release(lease["tenant"], lease["slots"]); self.accel.release(lease["lease_id"])

    def explain(self, token, lease_id: str) -> dict[str, Any]:
        p = self.authn.authenticate(token)
        lease = self.leases.get(lease_id)
        if lease is None: raise SchedulerError("NOT_FOUND", "unknown lease")
        authorize(p, "placement.explain", lease["tenant"])
        recs = [r for r in self.audit.read() if r["subject"].get("lease_id") == lease_id]
        return {"schema": "PK_PLACEMENT_EXPLAIN/1", "lease": {k: v for k, v in lease.items() if k != "occupant"},
                "audit": recs, "config": self.config.provenance()[-1], **release_lineage()}


class _Dev:
    def __init__(self, device_id: str):
        self.device_id = device_id


def _request_body(req: PlacementRequest) -> dict[str, Any]:
    w = req.workload
    return {"workload": [w.name, w.tenant, w.provenance, w.latency_sensitive, sorted(w.needs), w.site_affinity],
            "env": req.environment, "acc": sorted(dict(req.accelerators).items()), "excl": req.accelerator_exclusive,
            "res": sorted(req.residency), "ds": req.dataset, "aaz": req.anti_affinity_zone,
            "pz": req.preferred_zone, "origin": req.origin_site, "rt": req.runtime, "slots": req.slots}
