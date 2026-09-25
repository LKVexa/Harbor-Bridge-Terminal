"""DisconnectedNode: the production composition of GAP-04 (v4.3.0).

Every state change is ONE journal frame carrying the full post-state (GAP04-C18):
lease, policy, epochs, generation, controller snapshot, idempotency index,
quarantine/override state, and in-flight reconciliation progress. Recovery
takes the last state frame, so lease/policy/epoch/decision-log can never
disagree after a crash. Decisions are written ahead (WAL) before the supervisor
is told to act; effects are recorded after; unfinished effects are resumed
idempotently on restart (command_id == decision_id).
"""
from __future__ import annotations

import copy
import hashlib
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .. import __version__ as CODE_VERSION
from ..controller import TIERS, AutonomyController, ControllerError
from . import canonical, crypto
from .adapters import (CONTRACTS, CapabilityPlane, ReachabilityMonitor, ReferencePolicyEngine, Replication,
                       Supervisor, negotiate)
from .authz import Authorizer, Principal
from .clock import TrustedClock
from .config import validate_config
from .errors import (AdapterError, Gap04Error, Quarantined, ReconcileError, StorageFull, TrustedTimeError, to_error)
from .faults import crashpoint
from .fencing import OwnershipLock
from .journal import Journal, JournalLimits
from .observability import StructuredLogger, TraceContext, standard_metrics
from .resilience import Admission, CircuitBreaker, RetryBudget
from .storage import FileKeyProvider, KeyProvider, Keyring
from .trust import TrustStore, VerifiedPolicy, verify_lease, verify_policy
from .trust import policy_digest as TRpolicy_digest

STATE_SCHEMA = "PK_GAP04_STATE/1"
STATE_SCHEMA_VERSION = 1
HEALTH_SCHEMA = "PK_GAP04_HEALTH/1"
MAX_SEEN_LEASES = 64
TIER_NUM = {t: i for i, t in enumerate(TIERS)}
QUARANTINE_TOKEN = "PK_QUARANTINE_RELEASE/1"
QUARANTINE_CMD = "PK_QUARANTINE_COMMAND/1"


def fresh_state() -> dict:
    return {"schema": STATE_SCHEMA, "schema_version": STATE_SCHEMA_VERSION, "generation": 0,
            "authority_watermark": 0, "revoked_lease_ids": [], "policy_min_version": 0, "trust_min_version": 0,
            "trust": None, "clock_hwm": 0, "lease": None, "lease_fp": None, "policy": None, "policy_cached_at": 0,
            "seen_leases": {}, "controller": None, "requests": {}, "effects": {}, "quarantine": None,
            "overrides": {}, "reconcile": None, "last_reconciliation": None, "config_version": None,
            "config_digest": None, "storage_frozen": False}


# ------------------------------------------------------------------ state migrations (C41)
MIGRATIONS: dict[int, Any] = {}  # from_version -> fn(state) -> state ; v1 is current


def migrate_state(st: dict) -> dict:
    v = st.get("schema_version")
    if st.get("schema") != STATE_SCHEMA or not isinstance(v, int):
        raise Gap04Error("state schema unrecognized", code="GAP04-E0404")
    while v < STATE_SCHEMA_VERSION:
        if v not in MIGRATIONS:
            raise Gap04Error("no migration path", code="GAP04-E0404", details={"from": v})
        st = MIGRATIONS[v](st)
        v = st["schema_version"]
    if v > STATE_SCHEMA_VERSION:
        raise Gap04Error("state written by newer version; refusing downgrade", code="GAP04-E0404", details={"version": v})
    for k, val in fresh_state().items():
        st.setdefault(k, val)
    return st


@dataclass
class Adapters:
    policy_engine: ReferencePolicyEngine
    capabilities: CapabilityPlane | None
    supervisor: Supervisor
    replication: Replication
    reachability: ReachabilityMonitor


class DisconnectedNode:
    def __init__(self, state_dir: Path, *, config: dict, trust: TrustStore, owner_id: str, adapters: Adapters,
                 clock: TrustedClock | None = None, authorizer: Authorizer | None = None,
                 key_provider: KeyProvider | None = None, logger: StructuredLogger | None = None,
                 encrypt_journal: bool = True):
        self.cfg = validate_config(copy.deepcopy(config))
        self.site = self.cfg["scope"]["site"]
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.metrics = standard_metrics()
        self.log = logger or StructuredLogger(self.site, owner_id)
        self.authz = authorizer
        self.adapters = adapters
        for layer, a in (("GAP-13", adapters.policy_engine), ("GAP-01", adapters.supervisor),
                         ("GAP-05", adapters.replication), ("GAP-12", adapters.reachability)):
            negotiate(layer, a.CONTRACT)
        if adapters.capabilities is not None:
            negotiate("PLN-07", adapters.capabilities.CONTRACT)
        self.owner = OwnershipLock(self.dir)
        self.generation = self.owner.acquire(owner_id)
        had_keys = (self.dir / "keys.json").exists() if key_provider is None else True
        had_journal = (self.dir / "journal" / "journal.wal").exists()
        self.keyring = Keyring.open(key_provider or FileKeyProvider(self.dir / "keys.json"))
        if had_keys and key_provider is None and not had_journal:
            self.owner.release()
            raise Gap04Error("durable journal missing for an initialized node; refusing silent reset",
                             code="GAP04-E0401", details={"state_dir": str(self.dir)})
        j = self.cfg["journal"]
        self.journal = Journal(self.dir / "journal", self.keyring, generation=self.owner.current_generation,
                               limits=JournalLimits(j["max_bytes"], j["reserve_bytes"], j["min_disk_free_bytes"]),
                               encrypt=encrypt_journal, on_pressure=self._on_pressure)
        self.state = self._recover()
        self.trust = trust
        if self.state["trust"]:
            stored = TrustStore.from_doc(self.state["trust"])
            if stored.bundle_version > trust.bundle_version:
                self.trust = stored  # never regress to an older trust bundle
        c = self.cfg["clock"]
        hwm = max(self.state["clock_hwm"], self._max_clock_frame())
        self.clock = clock or TrustedClock(tolerance_s=c["tolerance_s"], max_drift_s=c["max_drift_s"],
                                           persist_interval_s=c["persist_interval_s"],
                                           allow_rtc_after_reboot=c["allow_rtc_after_reboot"])
        self.clock.hwm = max(self.clock.hwm, hwm + (self.clock.persist_interval_s if hwm else 0))
        self.clock.on_persist = self._persist_clock
        self.controller = (AutonomyController.from_snapshot(self.state["controller"])
                           if self.state["controller"] else None)
        a = self.cfg["admission"]
        self.admission = Admission(a["max_concurrency"], a["max_queue"])
        self.retry_budget = RetryBudget(a["retry_budget_percent"])
        self.breakers = {k: CircuitBreaker(k) for k in ("GAP-01", "GAP-05", "GAP-13", "PLN-07")}
        self._last_tier: str | None = None
        self.state["generation"] = self.generation
        self.state["config_version"] = self.cfg["config_version"]
        self.state["config_digest"] = canonical.digest(self.cfg)
        self.metrics.set("build_info", 1, version=CODE_VERSION, config=str(self.cfg["config_version"]))
        self._commit("open", {"owner": owner_id, "code_version": CODE_VERSION})
        if self._pending_compact > self.journal.base_seq:
            # crash between reconcile-complete and compaction: finish the compaction now
            self.journal.compact(self._pending_compact, archive_dir=self.dir / "archive")
        self.log.info("node.open", op="open", generation=self.generation, recovered_seq=self.journal.seq,
                      truncated_tail=self.journal.truncated_tail)

    # ================================================================ persistence
    def _recover(self) -> dict:
        """Last full snapshot + replay of delta frames (decisions, effects, batch acks).

        Snapshots never embed the per-partition decision log (that would make
        storage O(n^2) and overflow the frame bound); the log is rebuilt from the
        decision frames of the snapshot's *open* partition epoch only, so frames
        left behind by a crash between reconcile-complete and compaction are ignored.
        """
        frames = list(self.journal.frames())
        last = None
        self._pending_compact = 0
        for fr in frames:
            b = fr.get("body", {})
            if isinstance(b, dict) and "state" in b:
                last = b["state"]
            if isinstance(b, dict) and b.get("event") == "reconcile_complete":
                self._pending_compact = fr["seq"] - 1
        st = migrate_state(last) if last else fresh_state()
        ctl = st.get("controller")
        if ctl and ctl.get("partitioned_since") is not None:
            ep = ctl["partition_epoch"]
            for fr in frames:
                if fr["kind"] == "decision" and fr["body"]["decision"]["partition_epoch"] == ep:
                    d = fr["body"]["decision"]
                    ctl["decisions"].append(d)
                    ctl["last_event_at"] = max(ctl["last_event_at"], d["at"])
                    st["requests"][d["request_id"]] = d["decision_id"]
                elif fr["kind"] == "effect":
                    st["effects"][fr["body"]["decision_id"]] = fr["body"]["status"]
        rs = st.get("reconcile")
        if rs:
            rs.setdefault("outcomes", {})
            for fr in frames:
                b = fr["body"]
                if fr["kind"] == "reconcile_ack" and b.get("txn_id") == rs["txn_id"] and "outcomes" in b:
                    rs["outcomes"].update(b["outcomes"])
        return st

    def _max_clock_frame(self) -> int:
        m = 0
        for fr in self.journal.frames():
            if fr["kind"] == "clock":
                m = max(m, fr["body"]["hwm"])
        return m

    def _persist_clock(self, hwm: int) -> None:
        self.state["clock_hwm"] = hwm
        try:
            self.journal.append("clock", {"hwm": hwm})
        except StorageFull:
            pass  # reserve exhausted: time persists with the next state frame; node already frozen

    def _snapshot(self) -> dict:
        st = self.state
        st["clock_hwm"] = max(st["clock_hwm"], self.clock.hwm if hasattr(self, "clock") else 0)
        st["trust"] = self.trust.to_doc() if getattr(self, "trust", None) else st["trust"]
        ctl = getattr(self, "controller", None)
        snap = {k: v for k, v in st.items() if k not in ("requests", "effects", "controller", "reconcile")}
        snap = copy.deepcopy(snap)
        snap["requests"], snap["effects"] = {}, {}
        if ctl is not None:
            cs = ctl.to_snapshot(include_decisions=False)   # rebuilt from decision frames on recovery
            snap["controller"] = cs
        else:
            snap["controller"] = st.get("controller")
            if snap["controller"]:
                snap["controller"] = dict(snap["controller"], decisions=[])
        if st.get("reconcile"):
            snap["reconcile"] = {k: v for k, v in st["reconcile"].items() if k != "outcomes"}
            snap["reconcile"]["outcomes"] = {}
        else:
            snap["reconcile"] = None
        return snap

    def _commit(self, kind: str, extra: Mapping[str, Any] | None = None, *, frame_kind: str = "state") -> dict:
        body = dict(extra or {})
        body["event"] = kind
        body["state"] = self._snapshot()
        return self.journal.append(frame_kind, body)

    def _on_pressure(self, reason: str, usage: dict) -> None:
        self.metrics.inc("storage_alarms_total", reason=reason)
        self.log.warning("storage.pressure", op="journal", reason=reason, usage=usage)
        if reason == "journal_full" and not self.state.get("storage_frozen"):
            # C20: deterministic emergency freeze using reserved capacity
            self.state["storage_frozen"] = True
            if self.controller:
                self.controller.tier_cap = "freeze"
            try:
                self._commit("storage_freeze", {"usage": usage}, frame_kind="storage_alarm")
            except StorageFull:
                self.log.error("storage.reserve_exhausted", op="journal")

    # ================================================================ helpers
    def _now(self) -> int:
        try:
            return self.clock.now()
        except TrustedTimeError as e:
            self.metrics.inc("verification_failures_total", code=e.code)
            raise

    def _authz(self, boundary: str, principal: Principal | None) -> None:
        if self.authz is not None:
            self.authz.check(boundary, principal)

    def _require_reachable(self, what: str) -> None:
        if not self.adapters.reachability.reachable:
            raise Gap04Error(f"{what} requires verified control-plane reachability", code="GAP04-E0100",
                             details={"reachability": self.adapters.reachability.state})

    def _policy(self) -> VerifiedPolicy | None:
        if not self.state["policy"]:
            return None
        return verify_policy(self.state["policy"], trust=self.trust, now=self.clock.hwm,
                             min_policy_version=self.state["policy_min_version"])

    def _effective_cap(self, now: int) -> str | None:
        caps = []
        if self.state["storage_frozen"]:
            caps.append("freeze")
        if self.clock.confidence == "rtc":
            caps.append("freeze")
        for o in self.state["overrides"].values():
            if o["active"] and o["expires_at"] > now and o["kind"] in ("tier_cap", "freeze"):
                caps.append(o["value"] if o["kind"] == "tier_cap" else "freeze")
        return max(caps, key=lambda t: TIER_NUM[t]) if caps else None

    def _check_quarantine(self, now: int) -> None:
        if self.state["quarantine"]:
            raise Quarantined("controller quarantined", details={"reason": self.state["quarantine"]["reason"]})
        for o in self.state["overrides"].values():
            if o["active"] and o["kind"] == "disable" and o["expires_at"] > now:
                raise Quarantined("controller disabled by operator override", details={"override": o["id"]})

    # ================================================================ trust / policy / lease
    def install_trust(self, doc: Mapping[str, Any], principal: Principal | None = None) -> int:
        with self._lock:
            self._authz("trust.install", principal)
            self._require_reachable("trust bundle install")
            ts = TrustStore.from_doc(doc, min_version=max(self.state["trust_min_version"], self.trust.bundle_version))
            self.trust = ts
            self.state["trust_min_version"] = ts.bundle_version
            self._commit("trust_install", {"bundle_version": ts.bundle_version})
            return ts.bundle_version

    def install_policy(self, bundle: Mapping[str, Any], principal: Principal | None = None) -> dict:
        with self._lock:
            self._authz("policy.install", principal)
            self._require_reachable("policy install")
            now = self._now()
            try:
                vp = verify_policy(bundle, trust=self.trust, now=now, min_policy_version=self.state["policy_min_version"])
            except Gap04Error as e:
                self.metrics.inc("verification_failures_total", code=e.code)
                raise
            if vp.policy_version == self.state["policy_min_version"] and self.state["policy"] \
                    and TRpolicy_digest(self.state["policy"]) != vp.digest:
                raise Gap04Error("policy version reused with different content", code="GAP04-E0221")
            if self.controller and (self.controller.partitioned_since is not None or self.controller._decisions):
                raise Gap04Error("reconcile before refreshing policy", code="GAP04-E0002")
            self.state["policy"] = dict(bundle)
            self.state["policy_min_version"] = vp.policy_version
            self.state["policy_cached_at"] = now
            if self.controller:
                self.controller.cache_policy(now, control_plane_reachable=True)
            self._commit("policy_install", {"policy_version": vp.policy_version, "digest": vp.digest,
                                            "author": vp.author, "approver": vp.approver})
            self.log.info("policy.installed", op="policy", version=vp.policy_version, digest=vp.digest)
            return {"policy_version": vp.policy_version, "digest": vp.digest}

    def install_lease(self, envelope: bytes | str | Mapping[str, Any], principal: Principal | None = None) -> dict:
        with self._lock:
            self._authz("lease.install", principal)
            self._require_reachable("lease install")
            now = self._now()
            pol = self._policy()
            if pol is None:
                raise Gap04Error("no verified policy installed", code="GAP04-E0207")
            try:
                vl = verify_lease(envelope, trust=self.trust, expected_scope=self.cfg["scope"], now=now,
                                  min_authority_epoch=self.state["authority_watermark"],
                                  expected_policy_digest=pol.digest,
                                  revoked_lease_ids=frozenset(self.state["revoked_lease_ids"]))
            except Gap04Error as e:
                self.metrics.inc("verification_failures_total", code=e.code)
                self.log.warning("lease.rejected", op="lease", code=e.code, details=e.details)
                raise
            if vl.expires_at - max(now, vl.not_before) > self.cfg["lease"]["max_lifetime_s"]:
                raise Gap04Error("lease lifetime exceeds site configuration", code="GAP04-E0205")
            seen = self.state["seen_leases"]
            if vl.lease_id in seen:
                if seen[vl.lease_id] != vl.fingerprint:
                    raise Gap04Error("lease id reused with different content", code="GAP04-E0210")
                if self.state["lease_fp"] == vl.fingerprint:
                    return vl.audit_view()  # idempotent re-delivery
                raise Gap04Error("superseded lease replayed", code="GAP04-E0210")
            if self.controller and (self.controller.partitioned_since is not None or self.controller._decisions):
                raise Gap04Error("reconcile before installing a new lease", code="GAP04-E0002")
            old = self.controller
            start = max(now, vl.not_before, old._last_event_at if old else 0)
            if start >= vl.expires_at:
                raise Gap04Error("lease has no remaining validity", code="GAP04-E0205")
            ctl = AutonomyController(
                site=self.site, granted_at=start, lease_ticks=vl.expires_at - start,
                policy_cached_at=min(self.state["policy_cached_at"], start),
                max_policy_staleness_ticks=self.cfg["max_policy_staleness_s"],
                max_decisions=self.cfg["max_decisions_per_partition"],
                tier_schedule=tuple(tuple(x) for x in self.cfg["tier_schedule"]),
                lease_capabilities=vl.capabilities)
            if old:
                ctl._partition_epoch = old.partition_epoch
            self.controller = ctl
            seen[vl.lease_id] = vl.fingerprint
            while len(seen) > MAX_SEEN_LEASES:
                seen.pop(next(iter(seen)))
            self.state["lease"] = envelope if isinstance(envelope, dict) else canonical.loads(envelope)
            self.state["lease_fp"] = vl.fingerprint
            self.state["authority_watermark"] = max(self.state["authority_watermark"], vl.authority_epoch)
            crashpoint("lease.before_commit")
            self._commit("lease_install", {"lease": vl.audit_view()})
            self.log.info("lease.installed", op="lease", **vl.audit_view())
            return vl.audit_view()

    def _current_lease(self):
        if not self.state["lease"]:
            return None
        return verify_lease(self.state["lease"], trust=self.trust, expected_scope=self.cfg["scope"],
                            now=min(self.clock.hwm, self.controller.expires_at() - 1) if self.controller else self.clock.hwm,
                            min_authority_epoch=self.state["authority_watermark"], expected_policy_digest=None,
                            revoked_lease_ids=frozenset(self.state["revoked_lease_ids"]))

    def apply_revocations(self, authority_epoch: int, revoked_lease_ids=(), revoked_grants=(),
                          principal: Principal | None = None) -> dict:
        """C06: raise the authority watermark; stale/revoked leases can never become valid again."""
        with self._lock:
            self._authz("trust.install", principal)
            self._require_reachable("revocation update")
            if authority_epoch < self.state["authority_watermark"]:
                raise Gap04Error("authority watermark regression", code="GAP04-E0206")
            self.state["authority_watermark"] = authority_epoch
            self.state["revoked_lease_ids"] = sorted(set(self.state["revoked_lease_ids"]) | set(revoked_lease_ids))[-1024:]
            dropped = False
            if self.state["lease"]:
                le = self.state["lease"]
                if le["lease_id"] in self.state["revoked_lease_ids"] or le["authority_epoch"] < authority_epoch:
                    if self.controller and (self.controller.partitioned_since is not None or self.controller._decisions):
                        raise Gap04Error("reconcile before applying revocation of active lease", code="GAP04-E0002")
                    self.state["lease"], self.state["lease_fp"], dropped = None, None, True
                    if self.controller:
                        self.controller.lease_capabilities = frozenset()
            if self.adapters.capabilities is not None:
                self.adapters.capabilities.apply_revocations(authority_epoch, set(revoked_grants))
            self._commit("revocation", {"authority_epoch": authority_epoch, "lease_dropped": dropped})
            return {"authority_watermark": authority_epoch, "lease_dropped": dropped}

    # ================================================================ connectivity
    def observe_reachability(self, heartbeat: Mapping[str, Any] | None, latency_ms: int = 0) -> str:
        with self._lock:
            now = self._now()
            state = self.adapters.reachability.observe(heartbeat, now, latency_ms)
            for s in ("up", "down", "degraded", "flapping"):
                self.metrics.set("reachability_state", 1 if s == state else 0, state=s)
            if state in ("down", "flapping") and self.controller and self.controller.partitioned_since is None:
                self.controller.partition(max(now, self.controller._last_event_at))
                self._commit("partition", {"reachability": state, "partition_epoch": self.controller.partition_epoch})
                self.log.warning("partition.entered", op="partition", epoch=self.controller.partition_epoch, reachability=state)
            return state

    # ================================================================ decisions
    def decide(self, kind: str, subject: str, request_id: str, *, principal: Principal | None = None,
               traceparent: str | None = None) -> dict:
        t0 = time.perf_counter()
        trace = TraceContext.parse(traceparent)
        try:
            with self.admission.slot(), self._lock:
                rec = self._decide(kind, subject, request_id, principal, trace)
            self.metrics.observe("decision_latency_seconds", time.perf_counter() - t0)
            return rec
        except Exception as e:
            err = to_error(e)
            self.metrics.inc("denials_total", code=err["code"])
            if err["code"] == "GAP04-E0700":
                self.metrics.inc("admission_rejections_total")
            self.log.warning("decision.refused", op="decide", trace=trace, code=err["code"], kind=kind, subject=subject)
            if isinstance(e, Gap04Error):
                raise
            raise Gap04Error(str(e), code=err["code"], details=err["details"]) from e

    def _decide(self, kind, subject, request_id, principal, trace) -> dict:
        self._authz("decide", principal)
        if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
            raise Gap04Error("request_id must be 8..128 chars", code="GAP04-E0004")
        now = self._now()
        req_hash = canonical.digest({"kind": kind, "subject": subject, "principal": principal.spiffe_id if principal else None})
        if request_id in self.state["requests"]:
            did = self.state["requests"][request_id]
            prev = next((d for d in reversed(self.controller._decisions if self.controller else []) if d.get("decision_id") == did), None)
            if prev is not None and prev.get("request_hash") != req_hash:
                raise Gap04Error("request id reused with different content", code="GAP04-E0601",
                                 details={"request_id": request_id, "decision_id": did})
            for d in reversed(self.controller._decisions if self.controller else []):
                if d.get("decision_id") == did:
                    self.metrics.inc("replays_total")
                    self.log.info("decision.replayed", op="decide", decision_id=did, request_id=request_id)
                    return dict(copy.deepcopy(d), replayed=True)
        self._check_quarantine(now)
        if self.controller is None or not self.state["lease"]:
            raise Gap04Error("no verified autonomy lease", code="GAP04-E0100")
        self.controller.tier_cap = self._effective_cap(now)
        pol = self._policy()
        if pol is None:
            raise Gap04Error("no verified policy", code="GAP04-E0207")
        lease = self.state["lease"]
        if pol.digest != lease["policy"]["digest"]:
            raise Gap04Error("lease/policy binding mismatch", code="GAP04-E0207")
        tier = self.controller.tier(now)
        ok, why = self.breakers["GAP-13"].call(self.adapters.policy_engine.evaluate, pol, kind, subject, tier)
        if not ok:
            raise Gap04Error(f"policy denied: {why}", code="GAP04-E0101", details={"policy_reason": why})
        grant_id = None
        if self.adapters.capabilities is not None:
            if principal is None:
                raise Gap04Error("capability check requires an authenticated principal", code="GAP04-E0105")
            grant_id = self.adapters.capabilities.check(principal.spiffe_id, f"gap04.decide.{kind}", now)
        before_last_event = self.controller._last_event_at
        rec = self.controller.decide(kind, subject, now, reason=f"tier={tier};{why}")
        epoch = self.controller.partition_epoch
        decision_id = "d-" + hashlib.sha256(f"{self.site}|{epoch}|{request_id}".encode()).hexdigest()[:32]
        rec.update({"decision_id": decision_id, "request_id": request_id, "lease_id": lease["lease_id"],
                    "lease_fingerprint": self.state["lease_fp"], "authority_epoch": lease["authority_epoch"],
                    "policy_version": pol.policy_version, "policy_digest": pol.digest, "generation": self.generation,
                    "config_version": self.cfg["config_version"], "code_version": CODE_VERSION,
                    "grant_id": grant_id, "trace_id": trace.trace_id, "request_hash": req_hash})
        self.controller._decisions[-1] = copy.deepcopy(rec)
        self.state["requests"][request_id] = decision_id
        try:
            self.journal.append("decision", {"decision": copy.deepcopy(rec)})   # one atomic delta frame
        except StorageFull:
            self.controller._decisions.pop()          # O(1) undo: the decision never became durable
            self.controller._last_event_at = before_last_event
            self.state["requests"].pop(request_id, None)
            raise
        crashpoint("decide.after_wal")
        self.metrics.inc("decisions_total", kind=kind, tier=tier)
        if tier != self._last_tier:
            self.metrics.inc("tier_transitions_total", tier=tier)
            self._last_tier = tier
        self.log.info("decision.accepted", op="decide", trace=trace, workload=subject, decision_id=decision_id,
                      kind=kind, tier=tier)
        self._execute(rec, trace)
        crashpoint("decide.after_effect")
        return rec

    def _execute(self, rec: dict, trace: TraceContext) -> None:
        cmd = {"contract": CONTRACTS["GAP-01"], "command_id": rec["decision_id"], "kind": rec["kind"],
               "subject": rec["subject"], "authority_epoch": rec["authority_epoch"], "generation": self.generation,
               "traceparent": trace.child().header()}
        try:
            res = self.breakers["GAP-01"].call(self.adapters.supervisor.execute, cmd)
            status = res["status"]
        except Exception as e:
            status = "failed:" + to_error(e)["code"]
        self.state["effects"][rec["decision_id"]] = status
        try:
            self.journal.append("effect", {"decision_id": rec["decision_id"], "status": status})
        except StorageFull:
            pass

    def resume_effects(self) -> int:
        """Re-drive decisions whose effect was not recorded before a crash (idempotent by command_id)."""
        with self._lock:
            done = set(self.state["effects"])
            for fr in self.journal.frames():
                if fr["kind"] == "effect":
                    done.add(fr["body"]["decision_id"])
                    self.state["effects"][fr["body"]["decision_id"]] = fr["body"]["status"]
            n = 0
            for d in (self.controller.decisions if self.controller else []):
                if d.get("decision_id") and d["decision_id"] not in done:
                    self._execute(d, TraceContext.new())
                    n += 1
            return n

    # ================================================================ reconciliation (C07, C08)
    def reconnect(self, principal: Principal | None = None, traceparent: str | None = None) -> dict:
        with self._lock:
            self._authz("reconcile", principal)
            self._require_reachable("reconciliation")
            if self.adapters.reachability.state == "degraded" and self.controller and \
                    len(self.controller._decisions) > self.cfg["reconcile"]["batch_size"]:
                raise Gap04Error("degraded link: bulk reconciliation deferred", code="GAP04-E0600")
            if self.controller is None or self.controller.partitioned_since is None:
                raise Gap04Error("no active partition to reconcile", code="GAP04-E0001")
            trace = TraceContext.parse(traceparent)
            now = self._now()
            export = self.journal.export(0)
            Journal.verify_export(export, bytes(self.keyring.audit_key))  # self-check before disclosure
            decisions = self.controller.decisions
            rs = self.state["reconcile"]
            if rs is None:
                txn = "tx-" + hashlib.sha256(f"{self.site}|{self.controller.partition_epoch}|{export['head']}".encode()).hexdigest()[:32]
                rs = {"txn_id": txn, "started_at": now, "acked": [], "outcomes": {}, "audit_head": export["head"],
                      "attempts": 0}
                self.state["reconcile"] = rs
                self._commit("reconcile_begin", {"txn_id": txn}, frame_kind="reconcile_begin")
                crashpoint("reconcile.after_begin")
            bs = self.cfg["reconcile"]["batch_size"]
            batches = [decisions[i:i + bs] for i in range(0, len(decisions), bs)] or [[]]
            for n, batch in enumerate(batches):
                if n in rs["acked"]:
                    continue
                payload = {"contract": CONTRACTS["GAP-05"], "txn_id": rs["txn_id"], "batch_no": n, "site": self.site,
                           "partition_epoch": self.controller.partition_epoch,
                           "partitioned_since": self.controller.partitioned_since, "generation": self.generation,
                           "audit_head": rs["audit_head"], "traceparent": trace.child().header(),
                           "decisions": [{k: d[k] for k in ("decision_id", "kind", "subject", "at", "tier",
                                                            "policy_digest", "lease_id")} for d in batch]}
                res = self._submit_with_retry(payload)
                for o in res["outcomes"]:
                    outcome = o["outcome"]
                    if outcome == "conflict":
                        self.metrics.inc("reconcile_conflicts_total")
                        outcome = self._resolve_conflict(o["decision_id"])
                    rs["outcomes"][o["decision_id"]] = outcome
                    self.metrics.inc("reconcile_outcomes_total", outcome=outcome)
                rs["acked"].append(n)
                batch_out = {o["decision_id"]: rs["outcomes"][o["decision_id"]] for o in res["outcomes"]}
                self._commit("reconcile_batch_ack", {"txn_id": rs["txn_id"], "batch": n, "ack": res["ack"],
                                                     "outcomes": batch_out}, frame_kind="reconcile_ack")
                crashpoint("reconcile.after_batch_ack")
            record = self.controller.reconcile(max(now, self.controller._last_event_at))
            record["schema"] = "PK_RECONCILIATION_RECORD/2"
            record.update({"txn_id": rs["txn_id"], "outcomes": rs["outcomes"], "audit_anchor": export["anchor"],
                           "audit_head": rs["audit_head"], "generation": self.generation,
                           "authority_epoch": self.state["authority_watermark"],
                           "conflicts": sum(1 for v in rs["outcomes"].values() if v != "accepted")})
            self.state["reconcile"] = None
            self.state["requests"] = {}
            self.state["effects"] = {}
            self.state["last_reconciliation"] = {k: record[k] for k in ("txn_id", "partition_epoch", "decision_count",
                                                                        "conflicts", "reconnected_at", "audit_head")}
            ack = self._commit("reconcile_complete", {"txn_id": rs["txn_id"]}, frame_kind="reconcile_ack")
            crashpoint("reconcile.before_compact")
            self.journal.compact(ack["seq"] - 1, archive_dir=self.dir / "archive")
            self.log.info("reconcile.complete", op="reconcile", trace=trace, txn_id=rs["txn_id"],
                          decisions=record["decision_count"], conflicts=record["conflicts"])
            return record

    def _submit_with_retry(self, payload: dict) -> dict:
        attempts = self.cfg["reconcile"]["max_attempts"]
        self.retry_budget.record_attempt()
        last: Exception | None = None
        for i in range(attempts):
            if i > 0:
                if not self.retry_budget.try_retry():
                    break
                self.metrics.inc("retries_total", dependency="GAP-05")
            try:
                return self.breakers["GAP-05"].call(self.adapters.replication.submit, payload)
            except Gap04Error as e:
                last = e
                if e.code == "GAP04-E0701":
                    break
        self.state["reconcile"]["attempts"] += 1
        self._commit("reconcile_partial", {"txn_id": payload["txn_id"], "batch": payload["batch_no"]},
                     frame_kind="reconcile_ack")
        raise ReconcileError("reconciliation incomplete; progress persisted, retry reconnect()",
                             details={"txn_id": payload["txn_id"], "batch": payload["batch_no"],
                                      "cause": to_error(last)["code"] if last else None})

    def _resolve_conflict(self, decision_id: str) -> str:
        """Authoritative state wins: compensate the local effect; if compensation cannot
        be confirmed, quarantine the subject for operator resolution."""
        try:
            r = self.breakers["GAP-01"].call(self.adapters.supervisor.compensate, decision_id)
            if r.get("status") == "compensated":
                return "compensated"
        except Exception:
            pass
        return "quarantined"

    # ================================================================ overrides & quarantine (C24, C42)
    def request_override(self, kind: str, *, value: str | None, reason: str, ttl_s: int, requester: Principal) -> str:
        with self._lock:
            self._authz("override.request", requester)
            if kind not in ("freeze", "tier_cap", "disable"):
                raise Gap04Error("unknown override kind", code="GAP04-E0004")
            if kind == "tier_cap" and value not in ("sustain", "freeze", "expired"):
                raise Gap04Error("tier_cap may only narrow authority", code="GAP04-E0004")
            if not reason or len(reason.strip()) < 8:
                raise Gap04Error("override reason required (>=8 chars)", code="GAP04-E0004")
            if not 0 < ttl_s <= self.cfg["overrides"]["max_ttl_s"]:
                raise Gap04Error("override ttl out of bounds", code="GAP04-E0004")
            now = self._now()
            oid = "ov-" + hashlib.sha256(f"{now}|{requester.spiffe_id}|{kind}|{reason}".encode()).hexdigest()[:16]
            self.state["overrides"][oid] = {"id": oid, "kind": kind, "value": value, "reason": reason,
                                            "requester": requester.spiffe_id, "approvers": [], "requested_at": now,
                                            "expires_at": now + ttl_s, "active": False}
            self._maybe_activate(oid)
            self._commit("override_request", {"override": oid}, frame_kind="override")
            return oid

    def approve_override(self, oid: str, approver: Principal) -> dict:
        with self._lock:
            self._authz("override.approve", approver)
            o = self.state["overrides"].get(oid)
            if o is None:
                raise Gap04Error("unknown override", code="GAP04-E0004")
            if approver.spiffe_id == o["requester"]:
                raise Gap04Error("requester cannot approve own override", code="GAP04-E0802")
            if approver.spiffe_id not in o["approvers"]:
                o["approvers"].append(approver.spiffe_id)
            self._maybe_activate(oid)
            self._commit("override_approve", {"override": oid, "active": o["active"]}, frame_kind="override")
            return dict(o)

    def _maybe_activate(self, oid: str) -> None:
        o = self.state["overrides"][oid]
        need = 1 if self.cfg["overrides"]["two_person_required"] else 0
        # narrowing overrides (freeze/tier_cap/disable) all fail safe, still require the configured approvals
        o["active"] = len(o["approvers"]) >= need

    def clear_storage_freeze(self, principal: Principal | None = None) -> dict:
        """Exit storage emergency freeze only after space is recovered: integrity re-verify,
        utilization below the high watermark, and no reconciliation backlog (C20-015)."""
        with self._lock:
            self._authz("override.approve", principal)
            if not self.state["storage_frozen"]:
                return {"storage_frozen": False}
            Journal.verify_export(self.journal.export(0), bytes(self.keyring.audit_key))
            u = self.journal.usage()
            if u["utilization_ppm"] >= 700_000 or (self.controller and self.controller._decisions):
                raise Gap04Error("freeze exit prerequisites not met", code="GAP04-E0400",
                                 details={"utilization_ppm": u["utilization_ppm"],
                                          "pending": len(self.controller._decisions) if self.controller else 0})
            self.state["storage_frozen"] = False
            self._commit("storage_unfreeze", {"by": principal.spiffe_id if principal else None}, frame_kind="storage_alarm")
            return {"storage_frozen": False}

    def cancel_override(self, oid: str, principal: Principal) -> dict:
        with self._lock:
            self._authz("override.request", principal)
            o = self.state["overrides"].get(oid)
            if o is None:
                raise Gap04Error("unknown override", code="GAP04-E0004")
            o["active"] = False
            o["cancelled_by"] = principal.spiffe_id
            self._commit("override_cancel", {"override": oid}, frame_kind="override")
            return {"override": oid, "effective_tier_cap": self._effective_cap(self.clock.hwm)}

    def quarantine(self, reason: str, principal: Principal | None = None, *, command: Mapping[str, Any] | None = None) -> dict:
        """Immediate safe freeze. Local operators (authorized) or a signed remote command may trigger it."""
        with self._lock:
            now = self.clock.hwm
            source = "local"
            if command is not None:
                self._verify_signed(command, QUARANTINE_CMD, "quarantine", now)
                source = "remote:" + command["issuer"]
                reason = command.get("reason", reason)
            else:
                self._authz("quarantine", principal)
            self.state["quarantine"] = {"reason": reason, "source": source, "at": now,
                                        "by": principal.spiffe_id if principal else source,
                                        "nonce": crypto.b64e(hashlib.sha256(f"{now}|{reason}".encode()).digest()[:12])}
            self.metrics.set("quarantined", 1)
            self._commit("quarantine", {"reason": reason, "source": source}, frame_kind="quarantine")
            self.log.error("controller.quarantined", op="quarantine", reason=reason, source=source)
            return dict(self.state["quarantine"])

    def release_quarantine(self, token: Mapping[str, Any], approver: Principal | None = None) -> None:
        """Recovery needs a control-plane signed release bound to this quarantine's nonce,
        plus an authorized local approver distinct from whoever quarantined it."""
        with self._lock:
            q = self.state["quarantine"]
            if not q:
                return
            self._authz("quarantine.release", approver)
            if approver is not None and approver.spiffe_id == q["by"]:
                raise Gap04Error("release approver must differ from quarantining principal", code="GAP04-E0802")
            self._require_reachable("quarantine release")
            self._verify_signed(token, QUARANTINE_TOKEN, "quarantine", self._now())
            if token.get("quarantine_nonce") != q["nonce"]:
                raise Gap04Error("release token not bound to this quarantine", code="GAP04-E0104")
            self.state["quarantine"] = None
            self.metrics.set("quarantined", 0)
            self._commit("quarantine_release", {"by": token["issuer"]}, frame_kind="quarantine")

    def _verify_signed(self, doc: Mapping[str, Any], version: str, purpose: str, now: int) -> None:
        if doc.get("version") != version or doc.get("site") != self.site:
            raise Gap04Error("signed command malformed or wrong site", code="GAP04-E0104")
        key = self.trust.resolve(doc["key_id"], doc["issuer"], doc["alg"], purpose, now)
        body = {k: v for k, v in doc.items() if k != "sig"}
        if not crypto.verify(key.public_key, canonical.dumps(body), doc.get("sig", "")):
            raise Gap04Error("signed command signature invalid", code="GAP04-E0104")

    # ================================================================ health / readiness (C25)
    def health(self) -> dict:
        with self._lock:
            try:
                now = self.clock.now()
                clock_ok = True
            except TrustedTimeError:
                now, clock_ok = self.clock.hwm, False
            ctl = self.controller
            if ctl:
                ctl.tier_cap = self._effective_cap(now)
            tier = ctl.tier(max(now, 0)) if ctl else "expired"
            lease_rem = max(0, ctl.expires_at() - now) if ctl and self.state["lease"] else 0
            pol_age = now - self.state["policy_cached_at"] if self.state["policy"] else None
            usage = self.journal.usage()
            self.metrics.set("tier", TIER_NUM[tier])
            self.metrics.set("lease_remaining_seconds", lease_rem)
            if pol_age is not None:
                self.metrics.set("policy_staleness_seconds", pol_age)
            self.metrics.set("journal_utilization_ratio", usage["utilization_ppm"] / 1e6)
            self.metrics.set("journal_bytes", usage["bytes"])
            deps = {"GAP-12": self.adapters.reachability.state,
                    **{k: b.state for k, b in self.breakers.items()}}
            ready_reasons = []
            if not clock_ok:
                ready_reasons.append("clock_unanchored")
            if self.state["quarantine"]:
                ready_reasons.append("quarantined")
            if self.state["storage_frozen"]:
                ready_reasons.append("storage_frozen")
            if not self.state["lease"]:
                ready_reasons.append("no_lease")
            if not self.state["policy"]:
                ready_reasons.append("no_policy")
            return {
                "schema": HEALTH_SCHEMA, "site": self.site, "code_version": CODE_VERSION,
                "config_version": self.cfg["config_version"], "config_digest": self.state["config_digest"],
                "generation": self.generation, "clock": self.clock.status(), "now": now,
                "live": True, "ready": not ready_reasons, "not_ready_reasons": ready_reasons,
                "dependencies": deps,
                "lease": {"lease_id": (self.state["lease"] or {}).get("lease_id"), "remaining_s": lease_rem,
                          "authority_watermark": self.state["authority_watermark"]},
                "tier": tier, "partitioned": bool(ctl and ctl.partitioned_since is not None),
                "partition_epoch": ctl.partition_epoch if ctl else 0,
                "policy": {"version": self.state["policy_min_version"], "age_s": pol_age,
                           "stale": pol_age is not None and pol_age > self.cfg["max_policy_staleness_s"]},
                "journal": usage,
                "reconciliation": {"in_progress": self.state["reconcile"] is not None,
                                   "pending_decisions": len(ctl._decisions) if ctl else 0,
                                   "last": self.state["last_reconciliation"]},
                "quarantine": self.state["quarantine"] is not None,
                "overrides_active": sorted(o["id"] for o in self.state["overrides"].values()
                                           if o["active"] and o["expires_at"] > now),
            }

    def close(self) -> None:
        with self._lock:
            try:
                self._commit("close", {})
            except Exception:
                pass
            self.keyring.close()
            self.owner.release()
