"""GAP-10 production controller: wires every component into one decision path,
plus component 17 (health/readiness API) and component 23 (operator explain).

Decision path for one node::

    GAP-09 envelope -> TelemetryAdapter (01, 27, 28)
                    -> aggregate (10) with calibration (09)
                    -> ThermalState kernel (v4.2.0 model.py)
                    -> predictor (11) / battery (12) / cooling (13) / accelerators (14)
                    -> precedence (16) with controls (18) and partition bound (26)
                    -> fenced persist (04, 08) -> publish PK_POWER_CEILING/1
                    -> audit (20), metrics (21), logs/traces (22)
"""
from __future__ import annotations

import hashlib
import time as _time
from dataclasses import dataclass, field

from ..model import BAND_RANK, PowerThermalPolicy, ThermalState
from .calibration import CalibrationInventory
from .clock import TrustedClock
from .coordination import CircuitBreaker, ControlPlane, LeaseManager, PartitionManager, RetryPolicy, call_with_policy
from .enforcement import DECISION_SCHEMA
from .errors import ErrorCode, Gap10Error
from .keys import KeyRing, canonical
from .observability import AuditSink, StructuredLogger, new_metrics, new_span_id, new_trace_id
from .policy_service import PolicyService
from .predictive import BatteryModel, CoolingDomainModel, RateOfRisePredictor, accelerator_band
from .shedding import Constraint, resolve
from .store import FileStateStore, NodeRecord
from .telemetry import AggregationPolicy, TelemetryAdapter, aggregate


@dataclass
class NodeContext:
    state: ThermalState
    site: str = "unknown"
    scope: str = "default/prod"
    last_sample: dict | None = None
    last_decision: dict | None = None
    extra_reasons: tuple = ()
    accelerators: tuple = ()
    battery_model: BatteryModel | None = None
    on_mains: bool = True
    restored: bool = False


@dataclass
class Gap10Controller:
    controller_id: str
    shard: str
    keyring: KeyRing
    store: FileStateStore
    leases: LeaseManager
    policies: PolicyService
    clock: TrustedClock = field(default_factory=TrustedClock)
    calibration: CalibrationInventory = field(default_factory=CalibrationInventory)
    aggregation: AggregationPolicy = field(default_factory=AggregationPolicy)
    predictor: RateOfRisePredictor = field(default_factory=RateOfRisePredictor)
    cooling: CoolingDomainModel = field(default_factory=CoolingDomainModel)
    partition: PartitionManager = field(default_factory=PartitionManager)
    audit: AuditSink = field(default_factory=AuditSink)
    logger: StructuredLogger = field(default_factory=StructuredLogger)
    metrics: object = field(default_factory=new_metrics)
    controls: ControlPlane | None = None
    telemetry: TelemetryAdapter | None = None
    nodes: dict[str, NodeContext] = field(default_factory=dict)
    fencing_token: int | None = None
    store_healthy: bool = True
    dependency_health: dict[str, bool] = field(default_factory=dict)
    store_breaker: CircuitBreaker = field(default_factory=lambda: CircuitBreaker("state-store", 3, 30.0))
    store_retry: RetryPolicy = field(default_factory=lambda: RetryPolicy(max_attempts=3, base_delay_s=0.01, deadline_s=0.2))

    def __post_init__(self):
        if self.telemetry is None:
            self.telemetry = TelemetryAdapter(self.keyring)
        if self.controls is None:
            self.controls = ControlPlane(self.keyring, self.audit)

    # ------------------------------------------------------------ ownership
    def acquire(self) -> int:
        now = self.clock.now()
        try:
            self.fencing_token = self.leases.acquire(self.shard, self.controller_id, now)
        except Gap10Error as e:
            self.audit.append("ownership.rejected", self.controller_id, now, shard=self.shard, code=e.code.value)
            self.fencing_token = None
            raise
        self.audit.append("ownership.acquired", self.controller_id, now, shard=self.shard, token=self.fencing_token)
        return self.fencing_token

    def _require_leader(self, now: float) -> int:
        if self.fencing_token is None:
            raise Gap10Error(ErrorCode.OWNERSHIP_CONFLICT, f"{self.controller_id} does not hold {self.shard}")
        try:
            self.leases.validate(self.shard, self.controller_id, self.fencing_token, now)
            # heartbeat: renew while still valid (same token)
            self.leases.acquire(self.shard, self.controller_id, now)
        except Gap10Error:
            self.audit.append("ownership.lost", self.controller_id, now, shard=self.shard, token=self.fencing_token)
            self.fencing_token = None
            raise
        return self.fencing_token

    # ------------------------------------------------------------ nodes
    def _policy_for(self, ctx_node: str, scope: str) -> tuple[PowerThermalPolicy, str]:
        rev = self.policies.effective(scope, ctx_node)
        base = rev.policy if rev else PowerThermalPolicy()
        profile, _calibrated = self.calibration.profile_for(ctx_node)
        return profile.derive_policy(base), (rev.revision_id if rev else "builtin-default")

    def register(self, node: str, *, scope: str = "default/prod", site: str = "unknown", battery_model=None,
                 on_mains=True) -> NodeContext:
        policy, _ = self._policy_for(node, scope)
        st = ThermalState(node, policy=policy)
        ctx = NodeContext(st, site, scope, battery_model=battery_model, on_mains=on_mains)
        try:
            rec = self.store.load(node)
            if rec is not None:
                # restart can only keep or raise restriction: resume at the persisted band,
                # never below 'critical' until a fresh trusted sample arrives.
                persisted = max(rec.band, rec.hysteresis_band, key=BAND_RANK.__getitem__)
                st.band = max(persisted, "critical", key=BAND_RANK.__getitem__)
                st.last_observed_at = rec.last_trusted_observed_at
                if rec.last_trusted_seq is not None:
                    self.telemetry._last_seq[("restored", node)] = rec.last_trusted_seq
                ctx.restored = True
                self.audit.append("state.restored", self.controller_id, self.clock.now(), node=node, band=st.band,
                                  generation=rec.generation)
        except Gap10Error as e:
            self.store_healthy = e.code != ErrorCode.STORE_UNAVAILABLE and self.store_healthy
            st.band = "critical"
            ctx.extra_reasons = (f"state restore failed ({e.code.value}); starting constrained",)
        self.nodes[node] = ctx
        return ctx

    # ------------------------------------------------------------ ingest
    def ingest(self, raw, *, trace_id: str | None = None) -> dict:
        now = self.clock.now()
        trace_id = trace_id or new_trace_id()
        try:
            sample = self.telemetry.ingest(raw, now=now)
        except Gap10Error as e:
            self.metrics.inc("gap10_telemetry_samples_total", {"outcome": e.code.name.lower()})
            self.logger.log("warning", "telemetry.rejected", trace_id=trace_id, code=e.code.value, message=e.message)
            if e.code in (ErrorCode.TELEMETRY_BAD_SIGNATURE, ErrorCode.TELEMETRY_UNAUTHENTICATED,
                          ErrorCode.TELEMETRY_UNAUTHORIZED, ErrorCode.TELEMETRY_REPLAYED):
                self.audit.append("security.failure", "telemetry", now, code=e.code.value)
            raise
        self.metrics.inc("gap10_telemetry_samples_total", {"outcome": "accepted"})
        ctx = self.nodes.get(sample.node) or self.register(sample.node, site=sample.site)
        restored_seq = self.telemetry._last_seq.pop(("restored", sample.node), None)
        if restored_seq is not None and sample.seq <= restored_seq:
            self.telemetry.counters["replayed"] += 1
            raise Gap10Error(ErrorCode.TELEMETRY_REPLAYED, f"seq {sample.seq} <= persisted {restored_seq}")
        agg = aggregate(sample.sensors, self.aggregation)
        reasons = []
        temp = agg.temperature_c
        if not agg.complete:
            reasons.append(f"partial sensor trust: missing={list(agg.missing_required)} untrusted={list(agg.untrusted_sensors)}")
        if not self.clock.trusted():
            reasons.append("clock untrusted; freshness unverifiable")
            temp = None
        budget = sample.power_budget_watts or (self.calibration.budget_for(sample.node) if sample.power_draw_watts is not None else None)
        ctx.state.update(temperature=temp, battery=sample.battery_fraction, power_draw_watts=sample.power_draw_watts,
                         power_budget_watts=budget, observed_at=sample.observed_at, now=now)
        if not agg.complete and BAND_RANK[ctx.state.band] < BAND_RANK["critical"]:
            ctx.state.band = "critical"
        if temp is not None:
            self.predictor.observe(sample.node, sample.observed_at, temp)
        ctx.last_sample = {**sample.provenance(), "aggregate_c": temp, "limiting_sensor": agg.limiting_sensor,
                           "sensors": [vars(s) for s in sample.sensors], "power_draw_watts": sample.power_draw_watts,
                           "power_budget_watts": budget, "battery_fraction": sample.battery_fraction}
        ctx.extra_reasons = tuple(reasons)
        return self.decide(sample.node, trace_id=trace_id)

    # ------------------------------------------------------------ decide
    def decide(self, node: str, *, full_capacity: int = 100, trace_id: str | None = None) -> dict:
        t0 = _time.perf_counter()
        now = self.clock.now()
        token = self._require_leader(now)
        ctx = self.nodes[node]
        st = ctx.state
        policy, revision = self._policy_for(node, ctx.scope)
        if policy != st.policy:
            st.policy = policy
        band = st.band
        reasons = list(st.reasons) + list(ctx.extra_reasons)
        kernel_band = band
        # predictive / correlated raises
        extras = [self.predictor.band(node, policy)]
        if ctx.battery_model is not None:
            load = (ctx.last_sample or {}).get("power_draw_watts")
            extras.append(ctx.battery_model.band(st.battery, load, ctx.on_mains))
        self.cooling.report(node, band)
        extras.append(self.cooling.band_for(node))
        if ctx.accelerators:
            ab, _pw, ar = accelerator_band(ctx.accelerators, policy)
            extras.append((ab, ar))
        for b, r in extras:
            if BAND_RANK[b] > BAND_RANK[band]:
                band = b
            if r and BAND_RANK[b] > BAND_RANK["nominal"]:
                reasons.append(r)
        if band == "emergency" and kernel_band != "emergency":
            # only observed emergencies exclude; derived raises are capped at critical
            band = "critical"
        fraction = policy.band_ceiling[band]
        constraints = [Constraint("thermal-safety", fraction, f"band {band}")]
        cbound, creasons, disabled = self.controls.bound(node, now)
        if cbound < 1.0:
            constraints.append(Constraint("emergency-operator", cbound, "; ".join(creasons)))
        pbound, preason = self.partition.bound(node, fraction, now)
        if preason:
            constraints.append(Constraint("maintenance", pbound, preason))
        if not self.store_healthy:
            constraints.append(Constraint("maintenance", policy.critical_ceiling, "state store unhealthy"))
        effective, trail = resolve(constraints)
        reasons.extend(c["reason"] for c in trail if c["applied"] and c["source"] != "thermal-safety")
        excluded = band == "emergency" or effective == 0.0
        body = {"schema": DECISION_SCHEMA, "node": node, "band": band, "ceiling": int(full_capacity * effective),
                "ceiling_fraction": effective, "excluded": excluded, "reasons": reasons,
                "reason": "; ".join(reasons), "telemetry_status": st.telemetry_status,
                "policy_revision": revision, "fencing_token": token, "controller_id": self.controller_id,
                "issued_at": now, "automation_disabled": disabled}
        body["decision_id"] = "dec-" + hashlib.sha256(canonical(body)).hexdigest()[:16]
        body["precedence_trail"] = trail
        # persist (fenced); on failure restrict and report unhealthy
        try:
            rec = NodeRecord(node, band, st.last_observed_at, (ctx.last_sample or {}).get("seq"), revision, st.band,
                             token, controls=tuple(c.control_id for c in self.controls.active_for(node, now)),
                             updated_at=now)
            try:
                call_with_policy(lambda: self.store.save(rec), breaker=self.store_breaker, policy=self.store_retry,
                                 now=self.clock.now, retry_on=(OSError,))
            except Gap10Error as inner:
                # unwrap: fencing/corruption are not retryable and must surface as themselves
                raise inner if inner.code != ErrorCode.DEPENDENCY_TIMEOUT else Gap10Error(ErrorCode.STORE_UNAVAILABLE, inner.message)
            self.store_healthy = True
        except Gap10Error as e:
            if e.code == ErrorCode.FENCING_TOKEN_STALE:
                self.audit.append("ownership.lost", self.controller_id, now, node=node)
                self.fencing_token = None
                raise
            self.store_healthy = False
            self.metrics.inc("gap10_dependency_failures_total", {"dependency": "state-store", "code": e.code.value})
            crit = policy.critical_ceiling
            if body["ceiling_fraction"] > crit:
                body["ceiling_fraction"] = crit
                body["ceiling"] = int(full_capacity * crit)
                body["reasons"] = reasons + ["state store unavailable: decision not durable"]
                body["reason"] = "; ".join(body["reasons"])
        prev = ctx.last_decision
        if prev is None or prev["band"] != band or prev["ceiling_fraction"] != body["ceiling_fraction"]:
            self.audit.append("node.band_changed", self.controller_id, now, node=node,
                              before_band=None if prev is None else prev["band"], after_band=band,
                              before_fraction=None if prev is None else prev["ceiling_fraction"],
                              after_fraction=body["ceiling_fraction"], policy_revision=revision,
                              decision=body["decision_id"])
        if excluded and not (prev and prev["excluded"]):
            self.audit.append("node.excluded", self.controller_id, now, node=node, decision=body["decision_id"],
                              reason=body["reason"][:500])
            self.metrics.inc("gap10_thermal_exclusions_total", {"reason": band})
        if prev and prev["excluded"] and not excluded:
            self.audit.append("node.readmitted", self.controller_id, now, node=node, decision=body["decision_id"])
        if any("hysteresis" in r for r in reasons):
            self.metrics.inc("gap10_hysteresis_holds_total", {"node": node})
        ctx.last_decision = body
        lbl = {"node": node}
        self.metrics.set("gap10_power_ceiling_slots", body["ceiling"], lbl)
        self.metrics.set("gap10_ceiling_fraction", body["ceiling_fraction"], lbl)
        self.metrics.set("gap10_sensor_absent", 1 if st.temperature is None else 0, lbl)
        if st.temperature is not None:
            self.metrics.set("gap10_node_temperature_celsius", st.temperature, lbl)
        if st.power_draw_watts is not None and st.power_budget_watts:
            self.metrics.set("gap10_power_ratio", st.power_draw_watts / st.power_budget_watts, lbl)
        if st.last_observed_at is not None:
            self.metrics.set("gap10_telemetry_age_seconds", now - st.last_observed_at, lbl)
        self.metrics.set("gap10_controls_active", len(self.controls.active_for(node, now)), lbl)
        if ctx.battery_model is not None and not ctx.on_mains and st.battery is not None:
            rt = ctx.battery_model.runtime_s(st.battery, (ctx.last_sample or {}).get("power_draw_watts"))
            if rt is not None:
                self.metrics.set("gap10_battery_runtime_seconds", rt, lbl)
        self.metrics.observe("gap10_decision_latency_seconds", _time.perf_counter() - t0)
        self.logger.log("info", "decision", trace_id=trace_id, span_id=new_span_id(), node=node, site=ctx.site,
                        decision_id=body["decision_id"], band=band, ceiling_fraction=body["ceiling_fraction"],
                        policy_revision=revision)
        return body

    # ------------------------------------------------------------ 05 shadow / dry-run
    def shadow(self, node: str, revision_id: str) -> dict:
        """Evaluate a candidate policy revision against the node's last trusted
        sample without mutating state, persisting, or publishing."""
        import copy
        ctx = self.nodes[node]
        rev = self.policies.revisions.get(revision_id)
        if rev is None:
            raise Gap10Error(ErrorCode.POLICY_UNKNOWN_REVISION, revision_id)
        sample = ctx.last_sample or {}
        profile, _ = self.calibration.profile_for(node)
        st = copy.deepcopy(ctx.state)
        st.policy = profile.derive_policy(rev.policy)
        st.last_observed_at = None
        band = st.update(temperature=sample.get("aggregate_c"), battery=sample.get("battery_fraction"),
                         power_draw_watts=sample.get("power_draw_watts"), power_budget_watts=sample.get("power_budget_watts"))
        live = ctx.last_decision or {}
        return {"node": node, "candidate_revision": revision_id, "candidate_band": band,
                "candidate_fraction": st.policy.band_ceiling[band], "live_band": live.get("band"),
                "live_fraction": live.get("ceiling_fraction"), "reasons": list(st.reasons), "applied": False}

    # ------------------------------------------------------------ 17 health
    def health(self) -> dict:
        now = self.clock.now()
        leader = self.fencing_token is not None and self.leases.holder(self.shard, now) is not None \
            and self.leases.holder(self.shard, now)[0] == self.controller_id
        tel = self.telemetry.health(now)
        ages = {n: (None if c.state.last_observed_at is None else now - c.state.last_observed_at) for n, c in self.nodes.items()}
        max_age = max((a for a in ages.values() if a is not None), default=None)
        clock = self.clock.status()
        checks = {
            "leader": leader,
            "clock_trusted": clock["trusted"],
            "state_store": self.store_healthy and self.store.available,
            "telemetry_fresh": not tel["degraded"],
            "policy_active": any(self.policies.active.values()),
            **{f"dep:{k}": v for k, v in self.dependency_health.items()},
        }
        safe = all(checks.values())
        self.metrics.set("gap10_safe_to_enforce", 1 if safe else 0)
        return {
            "schema": "PK_GAP10_HEALTH/1", "live": True, "ready": leader, "safe_to_enforce": safe,
            "checks": checks, "active_policy_revisions": dict(self.policies.active),
            "max_sample_age_s": max_age, "sample_age_s": ages, "clock": clock, "telemetry": tel,
            "fencing_token": self.fencing_token, "controls_active": len(self.controls.controls),
            "partitioned": not self.partition.connected,
        }

    # ------------------------------------------------------------ 23 explain
    def explain(self, node: str, enforcement=None) -> dict:
        ctx = self.nodes.get(node)
        if ctx is None or ctx.last_decision is None:
            return {"node": node, "decision": None, "explanation": "no decision issued; consumers must fail closed"}
        d, st = ctx.last_decision, ctx.state
        p = st.policy
        crossings = []
        t = st.temperature
        if t is not None:
            for name in ("elevated_c", "critical_c", "emergency_c"):
                crossings.append({"threshold": name, "value": getattr(p, name), "observed": t, "crossed": t >= getattr(p, name)})
        out = {
            "node": node, "decision": {k: v for k, v in d.items() if k != "precedence_trail"},
            "source_sample": ctx.last_sample, "policy_revision": d["policy_revision"],
            "policy": {k: getattr(p, k) for k in ("elevated_c", "critical_c", "emergency_c", "recovery_margin_c",
                                                   "battery_reserve", "power_elevated_ratio", "power_critical_ratio",
                                                   "power_emergency_ratio", "max_sensor_age_seconds")},
            "threshold_crossings": crossings,
            "hysteresis": {"held": any("hysteresis" in r for r in d["reasons"]), "kernel_band": st.band},
            "precedence_trail": d["precedence_trail"],
            "controls": [vars(c) for c in self.controls.active_for(node, self.clock.now())],
            "prediction_c": self.predictor.predict(node),
        }
        if enforcement is not None:
            div = enforcement.divergence(node, self.clock.now())
            out["downstream"] = {"diverged": div is not None, "detail": div,
                                 "applied": enforcement.backend.applied_limit(node)}
        return out
