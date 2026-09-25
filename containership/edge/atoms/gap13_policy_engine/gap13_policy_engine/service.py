"""GAP-13 production policy service.

Composes the standalone evaluator with the production control plane:

* G13-MC-007 stale-policy enforcement (warning / hard expiry, three modes,
  monotonic age, clock-anomaly handling, restart-safe age);
* G13-MC-013 rollback manager (last-known-good retention, operator and
  automatic rollback, audited);
* G13-MC-014 atomic concurrent swap (read-copy-update: evaluations read one
  immutable snapshot reference; writers serialise on a lock);
* G13-MC-020 emergency controls (NORMAL, UPDATE_FROZEN, DENY_ONLY,
  EVALUATION_DISABLED, plus a durable quarantine list);
* G13-MC-021 health/readiness/status;
* G13-MC-031 admission control / load shedding;
and wires verification (MC-001), parsing (MC-002), attribute trust (MC-005/6),
anti-replay (MC-008), authorization (MC-009), audit (MC-010), cache (MC-012),
errors (MC-016), config/provenance (MC-018/19) and telemetry (MC-022..026).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from . import __version__ as ENGINE_RELEASE
from .attributes import AttributeSchema, StaticContextProvider, TrustedContextProvider, build_request
from .audit import AuditLog
from .authz import Authorizer, Capability as Cap, Principal
from .cache import BundleCache
from .config import ConfigProvenance, EngineConfig
from .engine import PolicyEngine
from .errors import (BundleQuarantined, BundleRejected, DeadlineExceeded, EvaluationDisabled,
                     NoActivePolicy, Overloaded, PolicyError, StalePolicyRefused, Unauthorized,
                     UpdateFrozen, VerificationFailed, CacheCorrupt, ConfigRejected)
from .replay import AntiReplayState
from .storage import Corrupt, read_record, write_record
from .telemetry import Lineage, Metrics, Redactor, StructuredLogger, Tracer
from .verify import BundleVerifier, VerificationResult, VerificationState

CONTROL_STATES = ("NORMAL", "UPDATE_FROZEN", "DENY_ONLY", "EVALUATION_DISABLED")
CONTROL_KIND = "PK_POLICY_CONTROL/1"
_CONTROL_CAP = {"NORMAL": Cap.CONTROL_CLEAR, "UPDATE_FROZEN": Cap.CONTROL_FREEZE,
                "DENY_ONLY": Cap.CONTROL_DENY_ONLY, "EVALUATION_DISABLED": Cap.CONTROL_DISABLE}


@dataclass(frozen=True)
class Snapshot:
    engine: PolicyEngine
    envelope: bytes
    result: VerificationResult
    activated_wall: float
    activated_mono: float
    base_age: float = 0.0          # age carried across restart


class PolicyService:
    def __init__(self, config: EngineConfig, verifier: BundleVerifier, *,
                 state_dir: str | Path | None = None,
                 context: TrustedContextProvider | None = None,
                 schema: AttributeSchema | None = None,
                 authorizer: Authorizer | None = None,
                 require_separation_of_duties: bool = True,
                 wall=time.time, mono=time.monotonic,
                 provenance: ConfigProvenance | None = None,
                 lineage: Lineage | None = None,
                 redactor: Redactor | None = None) -> None:
        self.config = config
        self.verifier = verifier
        self.wall, self.mono = wall, mono
        self.state_dir = Path(state_dir) if state_dir else None
        sd = self.state_dir
        self.audit = AuditLog(sd / "audit.jsonl" if sd else None, buffer_limit=config.limits.audit_buffer_records,
                              clock=wall)
        self.replay = AntiReplayState(sd / "antireplay.json" if sd else None)
        self.cache = BundleCache(sd / "cache.json" if sd else None)
        self.context = context or StaticContextProvider({})
        self.schema = schema or AttributeSchema(unknown=config.unknown_attribute_policy)
        self.authz = authorizer or Authorizer(config.environment, config.site, clock=wall)
        self.sod = require_separation_of_duties
        self.redactor = redactor or Redactor()
        self.metrics = Metrics()
        self.log = StructuredLogger(self.redactor, site=config.site, environment=config.environment)
        self.tracer = Tracer(self.redactor)
        self.lineage = lineage or Lineage(ENGINE_RELEASE)
        self.provenance = provenance or ConfigProvenance.create(config, author="default", source="built-in",
                                                                version=ENGINE_RELEASE, now=wall())
        self._write = threading.RLock()
        self._snap: Snapshot | None = None
        self._staged: dict[str, tuple[VerificationResult, bytes, str]] = {}
        self._inflight = 0
        self._inflight_lock = threading.Lock()
        self._stale_state = "none"
        self._last_wall = wall()
        self.clock_anomalies = 0
        self._control = {"state": "NORMAL", "reason": "", "change_id": "", "by": "", "since": 0,
                         "expires_at": None, "quarantine": []}
        self._load_control()
        self.dependency_state: dict[str, str] = {"verifier": "ok", "context": "ok", "audit": "ok"}

    # ------------------------------------------------------------------ durable control state (MC-020)
    def _load_control(self) -> None:
        if self.state_dir is None:
            return
        try:
            body = read_record(self.state_dir / "control.json", kind=CONTROL_KIND)
        except Corrupt:
            # unknown safety state -> most conservative: deny-only + frozen, surfaced as not-ready
            body = {**self._control, "state": "DENY_ONLY", "reason": "control state corrupt at startup",
                    "change_id": "auto", "by": "system", "since": int(self.wall())}
        if body:
            self._control = body

    def _save_control(self) -> None:
        if self.state_dir is not None:
            write_record(self.state_dir / "control.json", self._control, kind=CONTROL_KIND)

    def _control_state(self) -> str:
        c = self._control
        if c["state"] not in ("NORMAL",) and c.get("expires_at") and self.wall() >= c["expires_at"] \
                and c["state"] in ("UPDATE_FROZEN", "DENY_ONLY"):
            prev = c["state"]
            with self._write:
                self._control = {**c, "state": "NORMAL", "reason": f"time-bounded {prev} expired",
                                 "since": int(self.wall()), "expires_at": None}
                self._save_control()
                self.audit.emit("control.expired", target=prev, reason="time-bounded control expired")
        return self._control["state"]

    def set_control(self, principal: Principal, state: str, *, reason: str, change_id: str,
                    expires_at: int | None = None) -> dict[str, Any]:
        if state not in CONTROL_STATES:
            raise ConfigRejected(f"unknown control state {state}")
        if not reason or not change_id:
            raise ConfigRejected("reason and change_id are required for every control transition")
        if state == "EVALUATION_DISABLED" and expires_at is not None:
            raise ConfigRejected("EVALUATION_DISABLED is never auto-expiring")
        self._authorize(principal, _CONTROL_CAP[state], action=f"control.{state}")
        with self._write:
            old = self._control["state"]
            self._control = {**self._control, "state": state, "reason": reason, "change_id": change_id,
                             "by": principal.subject, "since": int(self.wall()), "expires_at": expires_at}
            self._save_control()
            self.audit.emit("control.transition", actor=principal.subject, target=state, reason=reason,
                            correlation_id=change_id, old_state=old, new_state=state,
                            breakglass=principal.kind == "breakglass")
            self.metrics.set("control_state", 1, state=state)
            self.log.log("G13-L030", "warning", state=state, reason=reason)
        return dict(self._control)

    def quarantine(self, principal: Principal, *, digest: str | None = None, bundle_id: str | None = None,
                   generation: int | None = None, reason: str, change_id: str) -> None:
        if not (digest or bundle_id or generation) or not reason or not change_id:
            raise ConfigRejected("quarantine needs a selector, reason and change_id")
        self._authorize(principal, Cap.CONTROL_QUARANTINE, action="control.quarantine")
        with self._write:
            entry = {"digest": digest, "bundle_id": bundle_id, "generation": generation,
                     "reason": reason, "change_id": change_id, "by": principal.subject}
            self._control = {**self._control, "quarantine": self._control["quarantine"] + [entry]}
            self._save_control()
            self.audit.emit("control.quarantine", actor=principal.subject, target=str(digest or bundle_id or generation),
                            reason=reason, correlation_id=change_id)
            snap = self._snap
            if snap is not None and self._is_quarantined(snap.result):
                # active bundle quarantined: fall back to newest non-quarantined LKG or deny-only
                if not self._auto_rollback("active bundle quarantined"):
                    self._control = {**self._control, "state": "DENY_ONLY",
                                     "reason": "active bundle quarantined; no safe LKG", "change_id": change_id}
                    self._save_control()

    def _is_quarantined(self, result: VerificationResult) -> bool:
        b = result.bundle
        for q in self._control["quarantine"]:
            if (q["digest"] and q["digest"] == b.digest) or (q["bundle_id"] and q["bundle_id"] == b.bundle_id) \
                    or (q["generation"] is not None and q["generation"] == b.generation):
                return True
        return False

    # ------------------------------------------------------------------ authorization helper
    def _authorize(self, principal: Principal | None, cap: Cap, *, action: str, tenant: str | None = None) -> None:
        try:
            self.audit.require_capacity()
            self.authz.require(principal, cap, tenant=tenant)
        except Unauthorized as exc:
            self.metrics.inc("auth_denied", capability=cap.value)
            self.log.log("G13-L040", "warning", code=exc.code, operation=action)
            self.audit.emit("authz.denied", actor=getattr(principal, "subject", "anonymous"), target=action,
                            result="denied", reason=str(exc))
            raise

    # ------------------------------------------------------------------ bundle lifecycle
    def _verify(self, envelope: bytes) -> VerificationResult:
        try:
            res = self.verifier.verify(envelope, now=int(self.wall()))
            self.dependency_state["verifier"] = "ok"
        except PolicyError:
            self.dependency_state["verifier"] = "unavailable"
            self.metrics.inc("dependency_failures", dependency="verifier")
            raise
        self.metrics.inc("bundle_verifications", state=res.state.value)
        self.audit.emit("bundle.verify", target=str(res.digest), result=res.state.value, reason=res.reason,
                        key_id=res.key_id, issuer=res.issuer, trust_store_version=res.trust_store_version,
                        generation=res.bundle.generation if res.bundle else None,
                        bundle_id=res.bundle.bundle_id if res.bundle else None)
        if res.state is not VerificationState.VERIFIED:
            self.log.log("G13-L011", "warning", reason=res.reason, state=res.state.value)
            raise VerificationFailed(f"bundle verification {res.state.value}: {res.reason}",
                                     details={"state": res.state.value})
        return res

    def stage(self, principal: Principal, envelope: bytes) -> dict[str, Any]:
        self._authorize(principal, Cap.BUNDLE_STAGE, action="bundle.stage")
        res = self._verify(envelope)
        if self._is_quarantined(res):
            raise BundleQuarantined("bundle is quarantined")
        verdict = self.replay.check(res.bundle)
        with self._write:
            if len(self._staged) >= 16:
                self._staged.pop(next(iter(self._staged)))
            self._staged[res.digest] = (res, bytes(envelope), principal.subject)
        self.audit.emit("bundle.stage", actor=principal.subject, target=res.digest, replay=verdict,
                        generation=res.bundle.generation)
        return {"digest": res.digest, "replay": verdict, **res.bundle.identity()}

    def activate(self, principal: Principal, digest: str, *, reason: str = "") -> dict[str, Any]:
        self._authorize(principal, Cap.BUNDLE_ACTIVATE, action="bundle.activate")
        with self._write:
            staged = self._staged.get(digest)
            if staged is None:
                raise BundleRejected("no staged bundle with that digest")
            res, envelope, stager = staged
            if self.sod and stager == principal.subject and principal.kind != "breakglass":
                self.audit.emit("bundle.activate", actor=principal.subject, target=digest, result="denied",
                                reason="separation of duties: stager cannot activate")
                raise Unauthorized("separation of duties: the principal that staged a bundle cannot activate it")
            self._activate_locked(res, envelope, actor=principal.subject, reason=reason)
            self._staged.pop(digest, None)
            return self.status()

    def load(self, principal: Principal, envelope: bytes, *, reason: str = "") -> dict[str, Any]:
        """Stage and activate in one call; only permitted when SoD is disabled for the deployment."""
        if self.sod and principal.kind != "breakglass":
            raise Unauthorized("separation of duties enabled: use stage() then activate() by another principal")
        self._authorize(principal, Cap.BUNDLE_ACTIVATE, action="bundle.load")
        res = self._verify(envelope)
        with self._write:
            self._activate_locked(res, bytes(envelope), actor=principal.subject, reason=reason)
        return self.status()

    def _activate_locked(self, res: VerificationResult, envelope: bytes, *, actor: str, reason: str,
                         rollback: bool = False, base_age: float = 0.0, persist: bool = True) -> None:
        if self._control_state() == "UPDATE_FROZEN" and not rollback:
            raise UpdateFrozen("bundle updates are frozen by operator control")
        if self._is_quarantined(res):
            raise BundleQuarantined("bundle is quarantined")
        replay = self.replay.check(res.bundle, rollback_authorized=rollback)
        engine = PolicyEngine(self.config.environment, staleness_bound=self.config.staleness_hard_seconds)
        engine.activate(res, now=0)                    # semantic validation (scope escalation etc.)
        now_w, now_m = self.wall(), self.mono()
        if persist:
            if replay != "authorized-rollback":
                self.replay.commit(res.bundle)         # durable anti-rollback floor first
            self.cache.record_activation(envelope, {"digest": res.digest, "generation": res.bundle.generation,
                                                    "bundle_id": res.bundle.bundle_id,
                                                    "activated_at_ms": int(now_w * 1000)})
        # RCU publish: single reference assignment; in-flight evaluations keep their snapshot
        self._snap = Snapshot(engine, envelope, res, now_w, now_m, base_age)
        self._stale_state = "none"
        self.metrics.set("bundle_generation", res.bundle.generation)
        self.metrics.inc("bundle_activations", kind="rollback" if rollback else "normal")
        self.audit.emit("bundle.rollback" if rollback else "bundle.activate", actor=actor, target=res.digest,
                        reason=reason, generation=res.bundle.generation, bundle_id=res.bundle.bundle_id,
                        replay=replay)
        self.log.log("G13-L012" if rollback else "G13-L010", digest=res.digest, generation=res.bundle.generation)

    def rollback(self, principal: Principal, *, reason: str, target_digest: str | None = None) -> dict[str, Any]:
        """G13-MC-013 operator rollback to a retained last-known-good bundle."""
        if not reason:
            raise ConfigRejected("rollback requires a reason")
        self._authorize(principal, Cap.BUNDLE_ROLLBACK, action="bundle.rollback")
        with self._write:
            active = self._snap.result.digest if self._snap else None
            for entry in self.cache.entries():
                if entry["digest"] == active or (target_digest and entry["digest"] != target_digest):
                    continue
                res = self._verify(self.cache.envelope(entry))
                if self._is_quarantined(res):
                    continue
                self._activate_locked(res, self.cache.envelope(entry), actor=principal.subject, reason=reason,
                                      rollback=True)
                return self.status()
        raise BundleRejected("no eligible last-known-good bundle for rollback")

    def _auto_rollback(self, why: str) -> bool:
        active = self._snap.result.digest if self._snap else None
        for entry in self.cache.entries():
            if entry["digest"] == active:
                continue
            try:
                res = self._verify(self.cache.envelope(entry))
                if self._is_quarantined(res):
                    continue
                self._activate_locked(res, self.cache.envelope(entry), actor="system", reason=why, rollback=True)
                return True
            except PolicyError:
                continue
        return False

    def restore_from_cache(self) -> bool:
        """Restart reconstruction: re-verify newest cached envelope; age persists across restart."""
        try:
            self.cache.load()
        except Corrupt as exc:
            self.audit.emit("cache.corrupt", result="error", reason=str(exc))
            self.metrics.inc("cache_corrupt")
            return False
        with self._write:
            for entry in self.cache.entries():
                try:
                    env = self.cache.envelope(entry)
                    res = self._verify(env)
                    if self._is_quarantined(res):
                        continue
                    wall_age = self.wall() - entry["activated_at_ms"] / 1000.0
                    if wall_age < 0:          # clock went backwards across restart: do not extend trust
                        self.clock_anomalies += 1
                        wall_age = float(self.config.staleness_hard_seconds) + 1
                    self._activate_locked(res, env, actor="system", reason="restart restore", rollback=True,
                                          base_age=wall_age, persist=False)
                    return True
                except PolicyError as exc:
                    self.audit.emit("cache.restore_skip", result="error", reason=str(exc)[:200])
        return False

    # ------------------------------------------------------------------ staleness (MC-007)
    def bundle_age(self, snap: Snapshot | None = None) -> float | None:
        snap = snap or self._snap
        if snap is None:
            return None
        mono_age = snap.base_age + (self.mono() - snap.activated_mono)
        now_w = self.wall()
        if now_w + self.config.clock_skew_tolerance_seconds < self._last_wall:
            self.clock_anomalies += 1           # wall clock rollback: rely on monotonic age only
        self._last_wall = max(self._last_wall, now_w)
        wall_age = snap.base_age + (now_w - snap.activated_wall)
        age = max(mono_age, wall_age)           # forward jumps can only shorten trust
        b = snap.result.bundle
        if b.expires_at is not None and now_w >= b.expires_at:
            age = max(age, float(self.config.staleness_hard_seconds) + 1)
        return age

    def _staleness(self, snap: Snapshot) -> str:
        age = self.bundle_age(snap)
        state = "hard" if age > self.config.staleness_hard_seconds else \
            "warning" if age > self.config.staleness_warning_seconds else "none"
        if state != self._stale_state:
            ev = {"warning": "G13-L020", "hard": "G13-L021", "none": "G13-L022"}[state]
            self.log.log(ev, "warning" if state != "none" else "info", state=state)
            self.audit.emit(f"stale.{state if state != 'none' else 'recovered'}", target=snap.result.digest,
                            age_s=int(age), mode=self.config.stale_mode)
            self._stale_state = state
        self.metrics.set("bundle_age_seconds", age)
        self.metrics.set("bundle_time_to_expiry_seconds", max(0, self.config.staleness_hard_seconds - age))
        return state

    # ------------------------------------------------------------------ evaluation path
    def _admit(self) -> None:
        with self._inflight_lock:
            if self._inflight >= self.config.limits.max_concurrency:
                self.metrics.inc("overload_shed")
                self.log.log("G13-L050", "warning")
                raise Overloaded("concurrency limit reached; request shed", details={"retry_after_ms": 50})
            self._inflight += 1

    def _release(self) -> None:
        with self._inflight_lock:
            self._inflight -= 1

    def evaluate(self, principal: Principal | None, attributes: Mapping[str, Any], *,
                 traceparent: str | None = None, deadline: float | None = None,
                 explain: bool = False) -> dict[str, Any]:
        cap = Cap.EXPLAIN if explain else Cap.EVALUATE
        self._authorize(principal, cap, action="evaluate")
        t0 = time.perf_counter()
        span = self.tracer.start("gap13.explain" if explain else "gap13.evaluate", traceparent)
        self._admit()
        try:
            if deadline is not None and self.mono() > deadline:
                raise DeadlineExceeded("deadline elapsed before evaluation")
            control = self._control_state()
            if control == "EVALUATION_DISABLED":
                raise EvaluationDisabled("evaluation disabled by emergency control")
            snap = self._snap                                     # one immutable snapshot per request
            if snap is None:
                raise NoActivePolicy("no verified policy bundle is active")
            try:
                trusted = self.context.context(principal.subject)
                self.dependency_state["context"] = "ok"
            except PolicyError:
                self.dependency_state["context"] = "unavailable"
                raise
            request = build_request(attributes, trusted, self.schema, self.config.limits)
            stale = self._staleness(snap)
            mode = "normal"
            if stale == "hard":
                if self.config.stale_mode == "FAIL_CLOSED":
                    self.metrics.inc("stale_refusals")
                    raise StalePolicyRefused("active policy is past its hard staleness bound",
                                             details={"mode": "FAIL_CLOSED"})
                mode = "stale-" + self.config.stale_mode.lower()
                self.metrics.inc("stale_evaluations", mode=self.config.stale_mode)
            if explain:
                out = snap.engine.explain(request, max_matches=self.config.limits.max_explanation_matches)
                if Cap.EXPLAIN_DETAILED not in principal.capabilities:
                    out["matched"] = []
                    out["detail"] = "summary (policy.explain.detailed required for matched-rule list)"
            else:
                out = snap.engine.evaluate(request)
            out["stale"] = stale != "none"
            forced = None
            if control == "DENY_ONLY":
                forced = "emergency DENY_ONLY control"
            elif stale == "hard" and self.config.stale_mode == "DENY_ONLY":
                forced = "stale policy (DENY_ONLY mode)"
            if forced and out["effect"] == "allow":
                out["effect"] = "deny"
                out["reason"] = f"{forced}; rule {out.get('rule') or out.get('winner')} would have allowed"
                mode = "deny-only"
            out["mode"] = mode if not forced else "deny-only"
            self.lineage.annotate(out)
            out["trace_id"] = span.trace_id
            rule = out.get("rule", out.get("winner"))
            self.metrics.inc("verdicts", effect=out["effect"], tenant=self.redactor.pseudonym(request.get("tenant")))
            if rule is None:
                self.metrics.inc("default_denies")
            if out.get("tie_break"):
                self.metrics.inc("specificity_ties")
            if rule is not None:
                self.metrics.inc("rule_hits", rule=rule)
            self.log.log("G13-L002" if rule is None else "G13-L001", effect=out["effect"], rule=rule,
                         version=out["version"], trace_id=span.trace_id, tenant=request.get("tenant"))
            return out
        except PolicyError as exc:
            self.metrics.inc("errors", code=exc.code)
            raise
        finally:
            self._release()
            ms = (time.perf_counter() - t0) * 1000
            self.metrics.observe("evaluate_latency_ms", ms)
            self.tracer.finish(span, latency_ms=round(ms, 3))

    def explain(self, principal: Principal | None, attributes: Mapping[str, Any], **kw: Any) -> dict[str, Any]:
        out = self.evaluate(principal, attributes, explain=True, **kw)
        if principal is not None and Cap.EXPLAIN_DETAILED in principal.capabilities:
            self.audit.emit("explain.detailed", actor=principal.subject, target=out.get("winner") or "")
        return out

    # ------------------------------------------------------------------ health / status (MC-021)
    def health(self) -> dict[str, Any]:
        snap = self._snap
        control = self._control_state()
        reasons = []
        if snap is None:
            reasons.append("no active bundle")
        elif self._staleness(snap) == "hard" and self.config.stale_mode == "FAIL_CLOSED":
            reasons.append("policy past hard staleness bound (FAIL_CLOSED)")
        if control == "EVALUATION_DISABLED":
            reasons.append("evaluation disabled")
        if self.audit.sink_down:
            reasons.append("audit sink down (buffering)")
        degraded = []
        if snap is not None and self._stale_state in ("warning", "hard"):
            degraded.append(f"policy staleness {self._stale_state}")
        if control in ("DENY_ONLY", "UPDATE_FROZEN"):
            degraded.append(f"control {control}")
        if self.clock_anomalies:
            degraded.append("clock anomaly observed")
        return {"schema": "PK_POLICY_HEALTH/1", "live": True, "ready": not reasons,
                "not_ready_reasons": reasons, "degraded": degraded}

    def status(self) -> dict[str, Any]:
        snap = self._snap
        b = snap.result.bundle if snap else None
        return {
            "schema": "PK_POLICY_STATUS/1",
            "engine_release": ENGINE_RELEASE,
            "environment": self.config.environment,
            "site": self.config.site,
            "active": None if b is None else {**b.identity(), "rules": len(b.rules),
                                               "key_id": snap.result.key_id,
                                               "trust_store_version": snap.result.trust_store_version,
                                               "verifier_version": snap.result.verifier_version},
            "bundle_age_seconds": None if snap is None else round(self.bundle_age(snap), 3),
            "staleness": {"state": self._stale_state, "warning_s": self.config.staleness_warning_seconds,
                          "hard_s": self.config.staleness_hard_seconds, "mode": self.config.stale_mode},
            "anti_rollback": self.replay.status(),
            "control": {k: v for k, v in self._control.items()},
            "dependencies": dict(self.dependency_state),
            "audit": self.audit.health(),
            "inflight": self._inflight,
            "config_provenance": self.provenance.to_dict(),
            "health": self.health(),
        }

    # ------------------------------------------------------------------ configuration (MC-018/019)
    def reconfigure(self, principal: Principal, config: EngineConfig, *, source: str, version: str) -> ConfigProvenance:
        self._authorize(principal, Cap.CONFIG_CHANGE, action="config.change")
        with self._write:
            prov = ConfigProvenance.create(config, author=principal.subject, source=source, version=version,
                                           previous=self.provenance, now=self.wall())
            old = self.provenance.config_digest
            self.config = config
            self.provenance = prov
            # emergency state is *not* touched by reconfiguration (MC-020)
            self.audit.emit("config.change", actor=principal.subject, target=prov.config_digest,
                            old_digest=old, new_digest=prov.config_digest, version=version)
            self.log.log("G13-L070", digest=prov.config_digest, version=version)
        return prov
