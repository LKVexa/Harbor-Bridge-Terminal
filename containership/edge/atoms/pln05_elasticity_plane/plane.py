"""PLN-05 service boundary: the elasticity plane as an operable component.

Pipeline for one demand sample (every step fail-closed, in this order)::

    admission -> decode(PK_DEMAND/1) -> authenticate -> authorize(demand.submit)
    -> source binding -> trusted-time check -> controls (disable/quarantine)
    -> freshness -> idempotency/ordering -> confidence -> leadership (lease)
    -> freeze / degraded caps -> controller.observe -> PK_CAPACITY_TARGET/1
    -> persist state -> fenced publish -> explain + metrics + logs + trace

Threading contract: every public method is serialised by one re-entrant lock;
the controller itself is single-owner and never shared across scopes.
Nothing in the telemetry/explain path can raise into the decision path.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field
import hashlib
import json
import threading
import time

from . import wire  # noqa: I001
from .audit import AuditLog
from .configuration import ConfigStore
from .controller import REASONS, ElasticityController, Limits
from .errors import PlaneError
from .iam import POLICY_VERSION, Authenticator, Principal
from .keys import KeyRing
from .reliability import AdmissionController, CircuitBreaker
from .state import FencedSink, LeaseService, StateStore
from .telemetry import Logger, Metrics, Tracer

from . import __version__ as VERSION  # single source: VERSION file, checked by tools/check_repo.py
STATUS_SCHEMA = "PLN05_STATUS/1"


def _build_info() -> dict:
    """``build_info.json`` is written into release artifacts by tools/build_release.py."""
    import json as _json
    import pathlib as _pl
    p = _pl.Path(__file__).resolve().parent / "build_info.json"
    try:
        return _json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"build_id": "unreleased-source", "source_revision": None}


BUILD = _build_info()
EXPLAIN_SCHEMA = "PLN05_EXPLAIN/1"
SEEN_IDS = 256
MODES = ("active", "stale", "degraded", "frozen", "quarantined", "disabled", "draining")


@dataclass
class Scope:
    key: str
    tenant: str
    site: str
    workload: str
    controller: ElasticityController
    limits_revision: int
    issuer: str
    declared_ceiling: int
    sources: dict = field(default_factory=dict)
    seen: deque = field(default_factory=lambda: deque(maxlen=SEEN_IDS))
    controls: dict = field(default_factory=dict)
    last_demand_at: float | None = None
    last_decision: dict | None = None
    last_decision_at: float | None = None
    epoch: int = 0
    lease: object = None
    mode: str = "active"
    mode_since: float = 0.0
    mode_reason: str = "R_OK"
    decision_seq: int = 0

    def persistable(self) -> dict:
        snap = self.controller.snapshot()
        snap["limits"].update(revision=self.limits_revision, issuer=self.issuer,
                              declared_ceiling=self.declared_ceiling)
        return {**snap, "controls": dict(self.controls), "sources": dict(self.sources),
                "seen": list(self.seen), "epoch": self.epoch,
                "last_decision_id": self.last_decision["decision_id"] if self.last_decision else None,
                "last_decision": self.last_decision, "last_demand_at": self.last_demand_at,
                "mode": self.mode, "mode_reason": self.mode_reason, "mode_since": self.mode_since,
                "decision_seq": self.decision_seq}


class ElasticityPlane:
    def __init__(self, *, instance_id: str, ring: KeyRing, clock=time.time, mono=time.monotonic,
                 state_dir=None, config_dir=None, lease_service: LeaseService | None = None,
                 sink: FencedSink | None = None, audit_path=None, log_stream=None) -> None:
        self.instance_id = instance_id
        self.ring = ring
        self.clock, self.mono = clock, mono
        self._lock = threading.RLock()
        now = clock()
        self.config = ConfigStore(ring, now, config_dir)
        c = self.config.active
        self.auth = Authenticator(ring)
        self.audit = AuditLog(ring, audit_path)
        self.leases = lease_service or LeaseService()
        self.sink = sink or FencedSink()
        self.store = StateStore(state_dir, ring) if state_dir else None
        self.admission = AdmissionController(c.get("queue_capacity"), c.get("control_reserve"))
        self.metrics = Metrics(c.get("telemetry.label_allowlist"), c.get("telemetry.max_series"))
        self.log = Logger(stream=log_stream)
        self.tracer = Tracer(c.get("telemetry.trace_sample_ratio"))
        self.breakers = {name: CircuitBreaker(name, c.get("breaker.failure_threshold"),
                                              c.get("breaker.open_s"), c.get("breaker.half_open_probes"))
                         for name in ("sink", "coordination", "audit_sink")}
        self.scopes: dict[str, Scope] = {}
        self.leases_held: dict = {}
        self._tenant_stamp: dict = {}
        self.tenant_controls: dict[str, dict] = {}
        self.pending_resume: dict[str, str] = {}
        self.explain_store: OrderedDict[str, dict] = OrderedDict()
        self.by_correlation: dict[str, str] = {}
        self._last_now = now
        self.time_fault = False
        self.started_mono = mono()
        self.last_progress_mono = mono()
        self.processed = 0
        self.last_error: dict | None = None
        self.state_errors: list[str] = []
        self.draining = False

    # ------------------------------------------------------------------ utils
    def _now(self) -> float:
        now = self.clock()
        if now + 1.0 < self._last_now:
            self.time_fault = True  # wall clock jumped backwards: trusted time lost
        elif self.time_fault and now >= self._last_now:
            self.time_fault = False
        self._last_now = max(self._last_now, now)
        return now

    def _error(self, exc: PlaneError, correlation_id=None) -> PlaneError:
        exc.correlation_id = exc.correlation_id or correlation_id
        self.last_error = {"code": exc.code, "category": exc.category, "at": self.clock()}
        self.metrics.inc("errors", {"reason_code": exc.code})
        self.log.log("WARN" if exc.severity != "critical" else "ERROR", "boundary_error",
                     code=exc.code, correlation_id=exc.correlation_id)
        return exc

    def _audit(self, p: Principal | None, action: str, result: str, code: str, *, tenant="-",
               site="-", corr=None, rev=None) -> None:
        self.audit.append(actor=p.sub if p else "anonymous", actor_class=p.actor_class if p else "-",
                          tenant=tenant, site=site, action=action, result=result, reason_code=code,
                          now=self.clock(), correlation_id=corr, object_revision=rev)

    def _principal(self, token, action: str, tenant: str, site: str, corr=None) -> Principal:
        now = self._now()
        try:
            p = self.auth.authenticate(token, now)
        except PlaneError as exc:
            self._audit(None, action, "denied", exc.code, tenant=tenant, site=site, corr=corr)
            raise
        try:
            self.auth.authorize(p, action, tenant=tenant, site=site, now=now)
        except PlaneError as exc:
            self._audit(p, action, "denied", exc.code, tenant=tenant, site=site, corr=corr)
            raise
        return p

    @staticmethod
    def scope_key(tenant: str, site: str, workload: str) -> str:
        return f"{tenant}/{site}/{workload}"

    def _persist(self, s: Scope) -> None:
        if self.store is not None:
            self.store.save(s.key, s.persistable(), self.clock())

    def _load_scope(self, key: str) -> Scope | None:
        if key in self.scopes or self.store is None:
            return self.scopes.get(key)
        try:
            doc = self.store.load(key, self.clock())
        except PlaneError as exc:
            self.state_errors.append(f"{exc.code}:{key}")
            raise
        if doc is None:
            return None
        lim = dict(doc["limits"])
        rev, issuer, declared = lim.pop("revision"), lim.pop("issuer"), lim.pop("declared_ceiling")
        ctl = ElasticityController.restore({"current": doc["current"], "below": doc["below"],
                                            "suppressed": doc["suppressed"], "limits": lim})
        t, si, w = key.split("/")
        s = Scope(key, t, si, w, ctl, rev, issuer, declared, sources=dict(doc["sources"]),
                  controls=dict(doc["controls"]), epoch=doc["epoch"])
        s.seen.extend(doc["seen"])
        s.last_decision = doc.get("last_decision")
        s.last_demand_at = doc.get("last_demand_at")
        s.mode = doc.get("mode", "active")
        s.mode_reason = doc.get("mode_reason", "R_OK")
        s.mode_since = doc.get("mode_since", 0.0)
        s.decision_seq = doc.get("decision_seq", 0)
        self.scopes[key] = s
        return s

    # ------------------------------------------------------------- authority
    def submit_limits(self, raw, token) -> dict:
        with self._lock:
            msg = wire.decode("PK_CAPACITY_LIMITS", raw)
            corr = msg.get("correlation_id")
            p = self._principal(token, "limits.update", msg["tenant"], msg["site"], corr)
            if msg["issuer"] != p.sub:
                self._audit(p, "limits.update", "denied", "E_AUTHZ_SCOPE", tenant=msg["tenant"],
                            site=msg["site"], corr=corr)
                raise self._error(PlaneError("E_AUTHZ_SCOPE", "limits issuer must be the authenticated principal"), corr)
            key = self.scope_key(msg["tenant"], msg["site"], msg["workload"])
            now = self._now()
            self._require_trusted_time()
            self.audit.ensure_capacity()
            s = self._lead(key, now)  # only the leaseholder may change a scope (review finding 1)
            limits = Limits(msg["floor"], msg["ceiling"], msg["scale_up_at"], msg["scale_down_at"],
                            msg["grace_samples"])
            if s is not None and msg["revision"] <= s.limits_revision:
                raise self._error(PlaneError("E_OUT_OF_ORDER", "limits revision must increase",
                                             {"active": s.limits_revision}), corr)
            if s is None:
                s = Scope(key, msg["tenant"], msg["site"], msg["workload"],
                          ElasticityController(limits), msg["revision"], msg["issuer"], msg["ceiling"])
                s.lease, s.epoch = self.leases_held[key], self.leases_held[key].epoch
                self.scopes[key] = s
                try:
                    self._persist(s)
                except OSError:
                    del self.scopes[key]
                    raise self._error(PlaneError("E_STATE_UNAVAILABLE", "state could not be persisted"), corr) from None
            else:
                prev = s.controller.current

                def change():
                    # Envelope change: keep current (clamped), reset pending grace evidence.
                    s.controller = ElasticityController(limits, current=s.controller.current)
                    s.limits_revision, s.issuer, s.declared_ceiling = msg["revision"], msg["issuer"], msg["ceiling"]
                self._txn(s, change, corr)
                if s.controller.current != prev:
                    self._hold_decision(s, "constrained-hold", "R_ENVELOPE_CHANGED", "envelope changed", now)
            self._audit(p, "limits.update", "applied", "R_LIMITS_APPLIED", tenant=s.tenant, site=s.site,
                        corr=corr, rev=msg["revision"])
            return {"scope": key, "revision": s.limits_revision, "current": s.controller.current}

    def lower_ceiling(self, token, *, tenant: str, site: str, workload: str, ceiling: int,
                      correlation_id: str | None = None) -> dict:
        with self._lock:
            p = self._principal(token, "ceiling.lower", tenant, site, correlation_id)
            now = self._now()
            self.audit.ensure_capacity()
            s = self._lead(self.scope_key(tenant, site, workload), now)
            if s is None:
                raise PlaneError("E_CONFIG_INVALID", "no declared capacity envelope for scope")
            prev = s.controller.current
            probe = ElasticityController.restore(s.controller.snapshot())
            try:
                probe.lower_ceiling(ceiling)  # validate on a copy first: nothing mutates on refusal
            except ValueError:
                self._audit(p, "ceiling.lower", "denied", "E_AUTHORITY_ESCALATION", tenant=tenant, site=site)
                raise self._error(PlaneError("E_AUTHORITY_ESCALATION",
                                             "external ceiling must be within [floor, active ceiling]"),
                                  correlation_id) from None
            self._txn(s, lambda: s.controller.lower_ceiling(ceiling), correlation_id)
            if s.controller.current != prev:
                self._hold_decision(s, "constrained-hold", "R_ENVELOPE_CHANGED", "ceiling lowered", now)
            self._audit(p, "ceiling.lower", "applied", "R_CEILING_LOWERED", tenant=tenant, site=site,
                        rev=ceiling)
            return {"scope": s.key, "ceiling": s.controller.limits.ceiling, "current": s.controller.current}

    def _require_trusted_time(self) -> None:
        if self.time_fault:
            raise PlaneError("E_SECURITY_DEPENDENCY", "trusted time unavailable (clock discontinuity)")

    def _txn(self, s: Scope, change, corr=None) -> None:
        """Apply ``change`` to scope memory, persist, and roll memory back if persistence fails."""
        backup = (s.controller.snapshot(), s.limits_revision, s.issuer, s.declared_ceiling,
                  {k: (list(v) if isinstance(v, list) else v) for k, v in s.controls.items()})
        change()
        try:
            self._persist(s)
        except OSError:
            snap, s.limits_revision, s.issuer, s.declared_ceiling, s.controls = backup
            s.controller = ElasticityController.restore(snap)
            self.metrics.inc("state_write_failed")
            raise self._error(PlaneError("E_STATE_UNAVAILABLE", "state could not be persisted; change withheld"),
                              corr) from None

    def _require_scope(self, tenant, site, workload) -> Scope:
        s = self._load_scope(self.scope_key(tenant, site, workload))
        if s is None:
            raise PlaneError("E_CONFIG_INVALID", "no declared capacity envelope for scope")
        return s

    # ----------------------------------------------------------- data path
    def enqueue_demand(self, raw, token, klass: str = "demand") -> None:
        with self._lock:
            if self.draining:
                raise self._error(PlaneError("E_DISABLED", "plane is draining; not accepting demand"))
            if isinstance(raw, (bytes, bytearray)) and len(raw) > wire.MAX_BYTES:
                # reject before queueing or parsing (cheap early rejection)
                raise self._error(PlaneError("E_SCHEMA_TOO_LARGE", "payload exceeds byte ceiling"))
            try:
                self.admission.offer(klass, (raw, token))
            except PlaneError as exc:
                self.metrics.inc("admission_rejected", {"outcome": klass})
                raise self._error(exc)

    def process(self, max_items: int | None = None) -> list:
        """Drain up to ``max_items`` queued samples; returns decisions or PlaneErrors."""
        out = []
        while max_items is None or len(out) < max_items:
            # take + decide under one lock hold: two processors must not reorder FIFO work
            # (found by tests/concurrency: a released lock between take and decide let a
            # later sample from the same source overtake an earlier one -> E_OUT_OF_ORDER).
            with self._lock:
                item = self.admission.take()
                if item is None:
                    break
                try:
                    out.append(self._decide(*item))
                except PlaneError as exc:
                    out.append(exc)
        return out

    def submit_demand(self, raw, token) -> dict:
        """Synchronous path: admission-checked, decided under the lock, returns *this* sample's
        decision (a shared-queue hand-off could return another caller's result)."""
        with self._lock:
            if self.draining:
                raise self._error(PlaneError("E_DISABLED", "plane is draining; not accepting demand"))
            try:
                self.admission.check("demand")
            except PlaneError as exc:
                self.metrics.inc("admission_rejected", {"outcome": "demand"})
                raise self._error(exc)
            return self._decide(raw, token)

    def _decide(self, raw, token) -> dict:
        t0 = time.perf_counter()
        with self._lock:
            self.last_progress_mono = self.mono()
            self.processed += 1
            try:
                msg = wire.decode("PK_DEMAND", raw)
            except PlaneError as exc:
                raise self._error(exc)
            corr = msg.get("correlation_id")
            trace_id, span_id = self.tracer.start(msg.get("traceparent"))
            try:
                decision = self._decide_msg(msg, token, corr, trace_id, span_id)
            except PlaneError as exc:
                self.tracer.span(trace_id, span_id, "pln05.decide", 0.0, error=True, code=exc.code)
                raise self._error(exc, corr)
            ms = (time.perf_counter() - t0) * 1000.0
            self.metrics.observe("decision_latency_ms", ms, {"outcome": decision["outcome"]})
            self.tracer.span(trace_id, span_id, "pln05.decide", ms, outcome=decision["outcome"])
            return decision

    def _decide_msg(self, msg, token, corr, trace_id, span_id) -> dict:
        tenant, site, workload = msg["tenant"], msg["site"], msg["workload"]
        p = self._principal(token, "demand.submit", tenant, site, corr)
        if p.source != msg["source"]:
            self._audit(p, "demand.submit", "denied", "E_AUTHZ_SCOPE", tenant=tenant, site=site, corr=corr)
            raise PlaneError("E_AUTHZ_SCOPE", "message source does not match credential binding")
        now = self._now()
        if self.time_fault:
            raise PlaneError("E_SECURITY_DEPENDENCY", "trusted time unavailable (clock discontinuity)")
        if self.state_errors:
            raise PlaneError("E_STATE_CORRUPT", "controller state failed integrity checks; not ready")
        if self.audit.pressure >= 1.0:
            raise PlaneError("E_AUDIT_UNAVAILABLE", "audit buffer full; refusing to decide unaudited")
        s = self._lead(self.scope_key(tenant, site, workload), now)
        if s is None:
            raise PlaneError("E_CONFIG_INVALID", "no declared capacity envelope for scope")
        ctl_state = self._effective_controls(s)
        if "disabled" in ctl_state:
            raise PlaneError("E_DISABLED", "decision publication disabled for scope")
        if msg["source"] in s.controls.get("quarantined_sources", []) or "quarantined" in ctl_state:
            raise PlaneError("E_QUARANTINED", "source or scope quarantined")
        cfg = self.config.active
        if msg["observed_at"] > now + cfg.get("future_skew_s"):
            raise PlaneError("E_FUTURE_SKEW", "observation timestamp is in the future")
        age = now - msg["observed_at"]
        if age > cfg.get("stale_after_s"):
            self.metrics.inc("stale_rejected")
            raise PlaneError("E_STALE_INPUT", "demand sample older than stale_after_s",
                             {"max_age_s": int(cfg.get("stale_after_s"))})
        if msg["message_id"] in s.seen:
            raise PlaneError("E_DUPLICATE", "message already processed")
        if msg["seq"] <= s.sources.get(msg["source"], -1):
            raise PlaneError("E_OUT_OF_ORDER", "sequence not newer than last accepted for source")
        backup = (s.controller.snapshot(), dict(s.sources), list(s.seen), s.last_demand_at,
                  s.last_decision, s.last_decision_at, s.mode, s.mode_reason)
        try:
            return self._apply_sample(s, msg, p, now, corr, trace_id, span_id, ctl_state, cfg)
        except PlaneError as exc:
            if exc.code == "E_STATE_UNAVAILABLE":
                # Nothing was persisted or published: roll memory back so it matches disk.
                (snap, s.sources, seen, s.last_demand_at, s.last_decision, s.last_decision_at,
                 s.mode, s.mode_reason) = backup
                s.controller = ElasticityController.restore(snap)
                s.seen.clear()
                s.seen.extend(seen)
            raise

    def _apply_sample(self, s, msg, p, now, corr, trace_id, span_id, ctl_state, cfg) -> dict:
        s.seen.append(msg["message_id"])
        s.sources[msg["source"]] = msg["seq"]
        s.last_demand_at = now
        prev = s.controller.current
        lim = s.controller.limits
        util = msg["utilisation"]
        rejected_alt = None
        recovered = False
        if s.mode in ("stale", "degraded"):
            # Exit criterion for demand-loss modes: a fresh, authenticated, in-order sample.
            self._set_mode(s, "active", "R_RECOVERED", now)
            recovered = True
        degraded = self._security_degraded()
        if "frozen" in ctl_state:
            outcome, code, reason = "frozen", "R_FROZEN", "hold: scope frozen"
            target = prev
        elif msg.get("confidence", 1.0) < cfg.get("min_confidence"):
            outcome, code, reason, target = "hold", "R_LOW_CONFIDENCE", "hold: confidence below minimum", prev
        elif degraded and util >= lim.scale_up_at and not cfg.get("degraded.allow_scale_up"):
            outcome, code, reason, target = "degraded", "R_DEGRADED_NO_SCALE_UP", "hold: degraded mode forbids scale-up", prev
            rejected_alt = "scale-up"
        else:
            target, reason = s.controller.observe(util)
            outcome, code = REASONS[reason]
            if outcome == "scale-up" and target < prev + max(1, prev):
                rejected_alt = "full scale-up step (ceiling constrained)"
            if outcome == "scale-down" and target > prev // 2:
                rejected_alt = "full scale-down step (floor constrained)"
            if recovered and outcome == "hold":
                outcome = "recovery"
        return self._publish(s, msg, p, prev, target, outcome, code, reason, now, corr,
                             trace_id, span_id, rejected_alt)

    def _publish(self, s, msg, p, prev, target, outcome, code, reason, now, corr, trace_id,
                 span_id, rejected_alt) -> dict:
        lim = s.controller.limits
        mid = msg["message_id"] if msg else None
        # Per-scope persisted sequence makes ids unique even for two holds at the same instant
        # (review fuzzing: an envelope-change hold collided with an earlier one and was
        # silently de-duplicated by the consumer).
        s.decision_seq += 1
        decision_id = hashlib.sha256(f"{s.key}|{s.epoch}|{s.decision_seq}|{mid}|{now}".encode()).hexdigest()[:32]
        rec = {"schema": "PK_CAPACITY_TARGET/1", "decision_id": decision_id, "tenant": s.tenant,
               "site": s.site, "workload": s.workload, "target": target, "previous": prev,
               "outcome": outcome, "reason_code": code, "reason": reason, "floor": lim.floor,
               "ceiling": lim.ceiling, "epoch": s.epoch, "fencing_token": s.epoch,
               "config_checksum": self.config.active.checksum, "demand_message_id": mid,
               "decided_at": now, "traceparent": self.tracer.traceparent(trace_id, span_id)}
        if corr:
            rec["correlation_id"] = corr
        wire.validate("PK_CAPACITY_TARGET", rec)  # never emit an out-of-contract target
        before = (s.last_decision, s.last_decision_at, s.decision_seq - 1)
        s.last_decision, s.last_decision_at = rec, now
        try:
            self._persist(s)  # persist before publish: restart cannot forget an emitted decision
        except OSError:
            s.last_decision, s.last_decision_at, s.decision_seq = before
            self.metrics.inc("state_write_failed")
            raise PlaneError("E_STATE_UNAVAILABLE", "state could not be persisted; decision withheld") from None
        published = False
        if outcome != "frozen":
            try:
                published = self.breakers["sink"].call(lambda: self.sink.apply(rec), now)
            except PlaneError as exc:
                self.metrics.inc("publish_failed", {"reason_code": exc.code})
                if exc.code == "E_FENCED":
                    raise
            except Exception:  # noqa: BLE001 - a misbehaving sink adapter must not crash the plane
                self.breakers["sink"].record(False, now)
                self.metrics.inc("publish_failed", {"reason_code": "E_INTERNAL"})
        self._record_explain(s, rec, msg, p, rejected_alt, published)
        self.metrics.inc("decisions", {"outcome": outcome, "reason_code": code})
        if outcome == "hold" and code == "R_GRACE_HOLD":
            self.metrics.inc("suppressed_oscillations")
        self.log.log("INFO", "decision", operation="decide", node=self.instance_id, tenant=s.tenant,
                     site=s.site, workload=s.workload, decision_id=decision_id, outcome=outcome,
                     reason_code=code, correlation_id=corr, target=target, previous=prev)
        return dict(rec, published=published)

    def republish_last(self, tenant, site, workload) -> bool:
        """Re-emit the persisted last decision (same decision_id: the sink de-duplicates)."""
        with self._lock:
            s = self._lead(self.scope_key(tenant, site, workload), self._now())
            if s is None or s.last_decision is None:
                return False
            return self.sink.apply(dict(s.last_decision, fencing_token=s.epoch, epoch=s.epoch))

    # ---------------------------------------------------------- coordination
    def _lead(self, key: str, now: float, load: bool = True) -> Scope | None:
        """Hold the lease for ``key``; on a *new* term reload the scope from shared state.

        While a lease is held continuously no other instance can write the scope (every writer
        takes the lease first), so cached memory is current.  When the lease had lapsed or is
        newly acquired, the cached scope may be stale (another leader may have changed limits,
        seen ids or controls): it is dropped and reloaded from the store before any decision.
        (Review finding 1: a stale leader re-published from stale memory and overwrote a newer
        envelope on disk.)"""
        cfg = self.config.active
        dur, renew = cfg.get("lease.duration_s"), cfg.get("lease.renew_before_s")
        lease = self.leases_held.get(key)
        # Local expiry is judged on the wall clock; after a clock step backwards it cannot be
        # trusted, so every call then re-verifies with the coordination service
        # (multi-instance fuzzing: a lapsed lease looked valid again after a -50 s jump).
        trusted = not self.time_fault
        continuous = trusted and lease is not None and lease.expires > now
        try:
            if continuous and lease.expires - now > renew:
                pass
            elif lease is not None and (lease.expires > now or not trusted):
                lease = self.breakers["coordination"].call(lambda: self.leases.renew(lease, now, dur), now)
            else:
                lease = self.breakers["coordination"].call(
                    lambda: self.leases.acquire(key, self.instance_id, now, dur), now)
                continuous = False
        except PlaneError as exc:
            # Only an *unreachable* coordination service lets a still-valid lease ride out its
            # granted window; an explicit refusal (another owner, new epoch) ends it at once.
            unreachable = exc.code in ("E_SECURITY_DEPENDENCY", "E_CIRCUIT_OPEN")
            if not (unreachable and continuous):
                self.leases_held.pop(key, None)
                raise PlaneError("E_NOT_LEADER", "no valid lease for scope") from None
        self.leases_held[key] = lease
        if not continuous and self.store is not None:
            self.scopes.pop(key, None)
            self.tenant_controls.pop(key.split("/")[0], None)
        if not load:
            return None
        s = self._load_scope(key)
        if s is not None:
            if lease.epoch < s.epoch:
                raise PlaneError("E_FENCED", "lease epoch older than persisted epoch (stale resurrection)")
            s.epoch, s.lease = lease.epoch, lease
        return s

    def _security_degraded(self) -> bool:
        return self.audit.pressure >= 0.75 or not self.ring._keys or \
            not any(k.active(self.clock()) for k in self.ring._keys.values())

    # ----------------------------------------------------------- staleness
    def _set_mode(self, s: Scope, mode: str, reason: str, now: float) -> None:
        if s.mode != mode:
            self.log.log("WARN" if mode != "active" else "INFO", "mode_change", scope_mode=mode,
                         reason_code=reason)
            self.metrics.inc("mode_transitions", {"state": mode})
            s.mode, s.mode_since, s.mode_reason = mode, now, reason

    def tick(self) -> dict:
        """Evaluate staleness for every scope this instance leads; returns ``{scope: mode}``."""
        with self._lock:
            now = self._now()
            cfg = self.config.active
            out = {}
            for key in list(self.scopes):
                s = self.scopes.get(key)
                if s is None:
                    continue
                if s.last_demand_at is not None:
                    age = now - s.last_demand_at
                    self.metrics.set("demand_staleness_seconds", age)
                    want = None
                    if age > cfg.get("degraded_after_s") and s.mode in ("active", "stale"):
                        want = ("degraded", "R_DEMAND_LOST", "hold: demand lost")
                    elif age > cfg.get("stale_after_s") and s.mode == "active":
                        want = ("stale", "R_STALE_INPUT_HOLD", "hold: demand stale")
                    if want is not None:
                        try:
                            s = self._lead(key, now) or s  # only the leader publishes holds; fresh state
                        except PlaneError:
                            out[key] = s.mode
                            continue
                        if s.mode != want[0]:
                            self._set_mode(s, want[0], want[1], now)
                            outcome = "degraded" if want[0] == "degraded" else "stale-input-hold"
                            self._hold_decision(s, outcome, want[1], want[2], now)
                out[key] = s.mode
            return out

    def _hold_decision(self, s: Scope, outcome: str, code: str, reason: str, now: float) -> None:
        """Publish an explicit hold (same target) so consumers see the mode change; best effort."""
        try:
            s = self._lead(s.key, now) or s
            if "disabled" in self._effective_controls(s):
                return
            tid, sid = self.tracer.start(None)
            self._publish(s, None, None, s.controller.current, s.controller.current, outcome, code,
                          reason, now, None, tid, sid, None)
        except PlaneError as exc:
            self.metrics.inc("publish_failed", {"reason_code": exc.code})

    # -------------------------------------------------------------- controls
    def _tenant_key(self, tenant: str) -> str:
        return f"{tenant}/tenant-controls/all"

    def _tenant_ctl(self, tenant: str) -> dict:
        """Tenant-wide controls survive restart and are shared across instances (persisted like a
        scope; re-read whenever the file changes, so a freeze by any instance applies at once)."""
        if self.store is not None:
            stamp = self.store.stamp(self._tenant_key(tenant))
            if self._tenant_stamp.get(tenant) != stamp:
                self.tenant_controls.pop(tenant, None)
                self._tenant_stamp[tenant] = stamp
        if tenant not in self.tenant_controls:
            doc = None
            if self.store is not None:
                try:
                    doc = self.store.load(self._tenant_key(tenant), self.clock())
                except PlaneError as exc:
                    self.state_errors.append(f"{exc.code}:{tenant}/tenant-controls")
                    # fail safe: an unreadable control record is treated as "disabled"
                    doc = {"controls": {"disabled": {"reason": "control state unreadable", "expires": None}}}
            self.tenant_controls[tenant] = dict((doc or {}).get("controls", {}))
        return self.tenant_controls[tenant]

    def _persist_tenant(self, tenant: str, backup: dict) -> None:
        if self.store is not None:
            try:
                self.store.save(self._tenant_key(tenant), {"controls": self.tenant_controls[tenant]}, self.clock())
            except OSError:
                self.tenant_controls[tenant] = backup
                raise PlaneError("E_STATE_UNAVAILABLE", "control state could not be persisted") from None
            self._tenant_stamp[tenant] = self.store.stamp(self._tenant_key(tenant))

    def _effective_controls(self, s: Scope) -> set:
        now = self.clock()
        active = set()
        for src in (s.controls, self._tenant_ctl(s.tenant)):
            for name in ("frozen", "quarantined", "disabled"):
                c = src.get(name)
                if c and (c.get("expires") is None or c["expires"] > now):
                    active.add(name)
        return active

    def control(self, token, action: str, *, tenant: str, site: str, workload: str | None = None,
                reason: str, ticket: str, expires: float | None = None, source: str | None = None) -> dict:
        """Apply freeze / quarantine / disable at workload scope, or tenant-wide with ``site="*"``
        and ``workload=None`` (tenant-wide needs a credential valid for every site)."""
        names = {"freeze": ("control.freeze", "frozen"), "quarantine": ("control.quarantine", "quarantined"),
                 "disable": ("control.disable", "disabled")}
        if action not in names:
            raise PlaneError("E_AUTHZ_DENIED", "unknown control action")
        cap, flag = names[action]
        if not reason or not ticket:
            raise PlaneError("E_CONFIG_INVALID", "control actions require reason and ticket")
        if (workload is None) != (site == "*"):
            raise PlaneError("E_AUTHZ_SCOPE", "tenant-wide controls use site='*' and no workload")
        with self._lock:
            p = self._principal(token, cap, tenant, site)
            now = self._now()  # safety-reducing actions are allowed during a time fault
            self.audit.ensure_capacity()
            entry = {"actor": p.sub, "reason": reason[:120], "ticket": ticket[:64], "at": now,
                     "expires": expires}
            if workload is None:
                self._lead(self._tenant_key(tenant), now, load=False)
                ctl = self._tenant_ctl(tenant)
                backup = {k: dict(v) for k, v in ctl.items()}
                ctl[flag] = entry
                self._persist_tenant(tenant, backup)
                target = f"{tenant}/*"
            else:
                s = self._lead(self.scope_key(tenant, site, workload), now)
                if s is None:
                    raise PlaneError("E_CONFIG_INVALID", "no declared capacity envelope for scope")

                def change():
                    if action == "quarantine" and source is not None:
                        q = s.controls.setdefault("quarantined_sources", [])
                        if source not in q:
                            if len(q) >= 64:
                                raise PlaneError("E_OVERLOADED", "quarantine list full; quarantine the scope instead")
                            q.append(source)
                    else:
                        s.controls[flag] = entry
                self._txn(s, change)
                target = s.key
            self._audit(p, cap, "applied", f"R_{flag.upper()}", tenant=tenant, site=site, rev=ticket[:32])
            return {"scope": target, "control": flag, "active": True}

    RESUME_TTL_S = 900.0
    MAX_PENDING_RESUME = 1024

    def _controls_digest(self, tenant, site, workload) -> str:
        if workload is None:
            data = self._tenant_ctl(tenant)
        else:
            s = self._require_scope(tenant, site, workload)
            data = s.controls
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def resume(self, token, *, tenant: str, site: str, workload: str | None, ticket: str) -> dict:
        """Two-step resume: a different principal must confirm within RESUME_TTL_S, and the
        confirmation is bound to the exact control state that was proposed for release."""
        if (workload is None) != (site == "*"):
            raise PlaneError("E_AUTHZ_SCOPE", "tenant-wide resume uses site='*' and no workload")
        with self._lock:
            p = self._principal(token, "control.resume", tenant, site)
            now = self._now()
            self._require_trusted_time()  # resume expands authority: needs trusted time
            self.audit.ensure_capacity()
            key = f"{tenant}/{site}/{workload or '*'}"
            lease_key = self._tenant_key(tenant) if workload is None else self.scope_key(tenant, site, workload)
            self._lead(lease_key, now, load=workload is not None)
            digest = self._controls_digest(tenant, site, workload)
            for k in [k for k, v in self.pending_resume.items() if now - v["at"] > self.RESUME_TTL_S]:
                del self.pending_resume[k]
            first = self.pending_resume.get(key)
            if first is None or first["digest"] != digest:
                while len(self.pending_resume) >= self.MAX_PENDING_RESUME:
                    self.pending_resume.pop(next(iter(self.pending_resume)))
                self.pending_resume[key] = {"by": p.sub, "at": now, "digest": digest}
                self._audit(p, "control.resume", "proposed", "R_RESUME_PROPOSED", tenant=tenant, site=site)
                return {"scope": key, "state": "resume-proposed"}
            if first["by"] == p.sub:
                self._audit(p, "control.resume", "denied", "E_AUTHZ_DENIED", tenant=tenant, site=site)
                raise PlaneError("E_AUTHZ_DENIED", "resume must be confirmed by a different principal")
            del self.pending_resume[key]
            if workload is None:
                backup = {k: dict(v) for k, v in self._tenant_ctl(tenant).items()}
                self.tenant_controls[tenant] = {}
                self._persist_tenant(tenant, backup)
            else:
                s = self._require_scope(tenant, site, workload)
                self._txn(s, lambda: setattr(s, "controls", {}))
            self._audit(p, "control.resume", "applied", "R_RESUMED", tenant=tenant, site=site, rev=ticket[:32])
            return {"scope": key, "state": "resumed"}

    def drain(self) -> int:
        """Stop accepting demand, finish queued work; returns the number processed."""
        with self._lock:
            self.draining = True
        return len(self.process())

    # ---------------------------------------------------------------- config
    def activate_config(self, token, layers: dict, *, tenant: str = "-", site: str = "-") -> dict:
        with self._lock:
            p = self._principal(token, "config.change", tenant, site)
            self._require_trusted_time()
            self.audit.ensure_capacity()
            try:
                snap = self.config.activate(layers, issuer=p.sub, now=self.clock())
            except PlaneError as exc:
                self._audit(p, "config.change", "rejected", exc.code, tenant=tenant, site=site)
                raise
            self._audit(p, "config.change", "applied", "R_CONFIG_ACTIVE", tenant=tenant, site=site,
                        rev=snap.revision)
            return snap.describe()

    def rollback_config(self, token, *, tenant: str = "-", site: str = "-") -> dict:
        with self._lock:
            p = self._principal(token, "config.rollback", tenant, site)
            self._require_trusted_time()
            self.audit.ensure_capacity()
            snap = self.config.rollback(now=self.clock())
            self._audit(p, "config.rollback", "applied", "R_CONFIG_ROLLBACK", tenant=tenant, site=site,
                        rev=snap.revision)
            return snap.describe()

    # -------------------------------------------------------------- explain
    def _record_explain(self, s, rec, msg, p, rejected_alt, published) -> None:
        try:
            ex = {"schema": EXPLAIN_SCHEMA, "decision_id": rec["decision_id"], "tenant": s.tenant,
                  "site": s.site, "workload": s.workload, "outcome": rec["outcome"],
                  "reason_code": rec["reason_code"], "target": rec["target"], "previous": rec["previous"],
                  "input": None if msg is None else {
                      "message_id": msg["message_id"], "source": msg["source"], "seq": msg["seq"],
                      "observed_at": msg["observed_at"], "utilisation": msg["utilisation"]},
                  "envelope": {"floor": rec["floor"], "ceiling": rec["ceiling"],
                               "declared_ceiling": s.declared_ceiling, "limits_revision": s.limits_revision,
                               "issuer": s.issuer},
                  "hysteresis": {"pending_below": s.controller._below,
                                 "grace_samples": s.controller.limits.grace_samples},
                  "controls": sorted(self._effective_controls(s)), "mode": s.mode,
                  "config": {"revision": self.config.active.revision, "checksum": self.config.active.checksum},
                  "authorization": None if p is None else {
                      "principal_class": p.actor_class, "policy_version": POLICY_VERSION,
                      "action": "demand.submit"},
                  "ownership": {"instance": self.instance_id, "epoch": rec["epoch"],
                                "fencing_token": rec["fencing_token"]},
                  "release": {"package": "pln05-elasticity-plane", "version": VERSION},
                  "rejected_alternative": rejected_alt, "published": published,
                  "correlation_id": rec.get("correlation_id"), "decided_at": rec["decided_at"]}
            self.explain_store[rec["decision_id"]] = ex
            if rec.get("correlation_id"):
                self.by_correlation[rec["correlation_id"]] = rec["decision_id"]
            limit = self.config.active.get("explain.retention")
            while len(self.explain_store) > limit:
                old, gone = self.explain_store.popitem(last=False)
                if gone.get("correlation_id"):
                    self.by_correlation.pop(gone["correlation_id"], None)
        except Exception:  # noqa: BLE001 - explain must never break the decision path
            self.metrics.inc("telemetry_errors")

    def explain(self, token, *, decision_id: str | None = None, correlation_id: str | None = None,
                tenant: str, site: str) -> dict:
        with self._lock:
            self._principal(token, "explain.read", tenant, site)
            did = decision_id or self.by_correlation.get(correlation_id or "")
            ex = self.explain_store.get(did or "")
            if ex is None or ex["tenant"] != tenant or (site != "*" and ex["site"] != site):
                raise PlaneError("E_AUTHZ_SCOPE", "decision not found in caller scope")
            return dict(ex)

    def explain_query(self, token, *, tenant: str, site: str, workload: str | None = None,
                      since: float = 0.0, until: float = float("inf"), limit: int = 100) -> list:
        with self._lock:
            self._principal(token, "explain.read", tenant, site)
            rows = [dict(e) for e in self.explain_store.values()
                    if e["tenant"] == tenant and (site == "*" or e["site"] == site)
                    and (workload is None or e["workload"] == workload)
                    and since <= e["decided_at"] <= until]
            return rows[-max(0, min(limit, 1000)):]

    # --------------------------------------------------------------- status
    def health(self) -> dict:
        """Unauthenticated liveness/readiness (no tenant detail). Never blocks on dependencies."""
        from .health import evaluate
        return evaluate(self)

    def status(self, token=None, *, tenant: str = "-", site: str = "-") -> dict:
        from .health import evaluate
        h = evaluate(self)
        out = {"schema": STATUS_SCHEMA, "version": VERSION, "build": BUILD, "instance": self.instance_id,
               "live": h["live"], "ready": h["ready"], "state": h["state"], "blockers": h["blockers"],
               "config": {"revision": self.config.active.revision, "checksum": self.config.active.checksum},
               "schemas": {k: list(v) for k, v in wire.SUPPORTED.items()},
               "capability_policy": POLICY_VERSION, "dependencies": h["dependencies"],
               "last_error": self.last_error}
        if token is None:
            return out
        with self._lock:
            self._principal(token, "status.read_admin", tenant, site)
            out["scopes"] = [{"scope": s.key, "mode": s.mode, "mode_reason": s.mode_reason,
                              "floor": s.controller.limits.floor, "ceiling": s.controller.limits.ceiling,
                              "target": s.controller.current, "epoch": s.epoch,
                              "leader": bool(s.lease and s.lease.expires > self.clock()),
                              "controls": sorted(self._effective_controls(s)),
                              "last_decision_at": s.last_decision_at,
                              "demand_age_s": (self.clock() - s.last_demand_at) if s.last_demand_at else None}
                             for s in self.scopes.values()
                             if s.tenant == tenant and (site == "*" or s.site == site)]
            out["keys"] = self.ring.status(self.clock())
            return out
