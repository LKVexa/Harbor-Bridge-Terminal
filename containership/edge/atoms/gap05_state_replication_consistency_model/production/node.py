"""ReplicaNode - integration of the GAP-05 production components around the unchanged
causal core (``model.ReplicatedKey``).

Accept path for every write (local, relayed or recovered), in order; any refusal
happens *before* durable or in-memory mutation::

    schema/op_id (MC07,MC09) -> limits (MC30) -> namespace (MC06) -> authz (MC13)
    -> provenance (MC02) -> fencing (MC32) -> freeze check (MC22) -> admission (MC29)
    -> counter guard (MC03) -> tombstone floor (MC19/MC20) -> equivocation pre-check
    -> audit capacity (MC11) -> WAL append+fsync (MC04) -> core apply
    -> audit record (MC10) -> metrics/logs/analytics (MC26,27,44)

State is striped over ``shards`` locks (MC41); each state key is
``tenant \\x1f environment \\x1f key`` - the separator is a control character that the
wire schema forbids inside any component, so namespaces cannot collide (MC06).
"""
from __future__ import annotations

import copy
import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from ..model import ReplicatedKey, Write, dominates
from . import crdt
from .audit import AuditLedger
from .authz import Authorizer, Permission
from .durable import SnapshotStore, WriteAheadLog, _maybe_crash
from .errors import (CapacityError, ConflictStillOpen, Gap05Error, IntegrityError, NamespaceError,
                     SchemaError, SecurityError)
from .identity import ReplicaKeys
from .limits import DEFAULT_LIMITS, Limits
from .membership import CounterAllocator, CounterGuard, MembershipStore
from .observe import Admission, ConflictAnalytics, Metrics, StructuredLog, new_span_id, new_trace_id
from .protect import Keyring, sign_write, verify_write
from .schemas import (CONFLICT_SCHEMA, make_merge_result, make_write_doc, validate_write_doc)

SEP = "\x1f"
STATE_FORMAT_VERSION = 2


def state_key(tenant: str, environment: str, key: str) -> str:
    for part in (tenant, environment, key):
        if not isinstance(part, str) or not part or SEP in part:
            raise NamespaceError("namespace components must be non-empty and free of separators")
    return f"{tenant}{SEP}{environment}{SEP}{key}"


def split_key(sk: str) -> tuple[str, str, str]:
    t, e, k = sk.split(SEP)
    return t, e, k


@dataclass(frozen=True)
class FrontierView:
    """MC23 - immutable read-only view; callers cannot mutate node state through it."""

    tenant: str
    environment: str
    key: str
    active: tuple
    quarantined: tuple
    discarded_count: int
    open: bool
    frozen: bool
    floor: tuple


class ReplicaNode:
    def __init__(self, data_dir: Path, keys: ReplicaKeys, membership: MembershipStore, *,
                 policy_provider, limits: Limits = DEFAULT_LIMITS, keyring: Keyring | None = None,
                 shards: int = 16, admission: Admission | None = None, audit_archive: Path | None = None,
                 audit_segment_records: int = 10_000, audit_max_segments: int = 4, counter_max_gap: int = 1024,
                 log_sink=None):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.name = keys.replica
        self.keys = keys
        self.membership = membership
        self.limits = limits
        self.keyring = keyring
        self.metrics = Metrics()
        self.log = StructuredLog(log_sink)
        self.analytics = ConflictAnalytics()
        self.audit = AuditLedger(self.dir / "audit", keys.private_key, segment_records=audit_segment_records,
                                 max_active_segments=audit_max_segments, archive_dir=audit_archive)
        self.authz = Authorizer(policy_provider, self.audit)
        self.admission = admission or Admission()
        self.allocator = CounterAllocator(self.dir / "counters.json", self.name)
        self.guard = CounterGuard(max_gap=counter_max_gap)
        self.snapshots = SnapshotStore(self.dir / "snapshots")
        self._shards = [threading.RLock() for _ in range(max(1, shards))]
        self._global = threading.RLock()
        self.keys_state: dict[str, ReplicatedKey] = {}
        self.docs: dict[str, dict] = {}            # op_id -> write doc (frontier + recent)
        self.by_vector: dict[tuple, str] = {}      # (state_key, vector) -> op_id
        self.floors: dict[str, dict] = {}          # state_key -> tombstone floor vector (MC19/MC20)
        self.frozen: set[str] = set()
        self.recent_ops: dict[str, None] = {}      # bounded durable-dedupe window (MC09)
        self.recent_window = 100_000
        self.generation = 0
        self.degraded: str | None = None
        self.recovery_mode = False
        self.recovery_report: dict = {}
        self.discarded_before_snapshot: dict = {}
        self._recover()
        if (self.dir / "RESTORED").exists():
            self.recovery_mode = True  # MC25: restored state is stale until a peer sync completes

    def finish_recovery(self) -> None:
        (self.dir / "RESTORED").unlink(missing_ok=True)
        self.recovery_mode = False
        self.audit.append("recovery_complete")

    # ------------------------------------------------------------------ helpers
    def _shard(self, sk: str) -> threading.RLock:
        return self._shards[int(hashlib.blake2s(sk.encode(), digest_size=4).hexdigest(), 16) % len(self._shards)]

    def _rk(self, sk: str) -> ReplicatedKey:
        rk = self.keys_state.get(sk)
        if rk is None:
            rk = ReplicatedKey(key=sk, replicas=self.membership.current.known, max_siblings=self.limits.max_siblings)
            self.keys_state[sk] = rk
        elif not self.membership.current.known <= rk.replicas:
            rk.replicas = self.membership.current.known  # membership grew (MC15); history stays valid
        return rk

    def _to_core(self, doc: dict) -> Write:
        sk = state_key(doc["tenant"], doc["environment"], doc["key"])
        return Write(sk, doc["value"], doc["site"], tuple(tuple(e) for e in doc["vector"]))

    def _seal(self, doc: dict) -> dict:
        if self.keyring is None:
            return {"doc": doc}
        body = dict(doc)
        env = self.keyring.encrypt(body.pop("value").encode("utf-8"), tenant=doc["tenant"],
                                   environment=doc["environment"], purpose="wal")
        return {"doc": body, "enc_value": env}

    def _unseal(self, sealed: dict) -> dict:
        doc = dict(sealed["doc"])
        if "enc_value" in sealed:
            if self.keyring is None:
                raise SecurityError("WAL is encrypted but no keyring configured", code="SEC_KEY_UNAVAILABLE")
            doc["value"] = self.keyring.decrypt(sealed["enc_value"], tenant=doc["tenant"],
                                                environment=doc["environment"], purpose="wal").decode("utf-8")
        return doc

    # ------------------------------------------------------------------ recovery
    def _recover(self) -> None:
        snap, rejected = self.snapshots.latest_valid()
        base_seq = 0
        if snap is not None:
            state = snap["state"]
            if state.get("state_format") != STATE_FORMAT_VERSION:
                raise IntegrityError("snapshot state format needs migration", code="CORR_NEEDS_MIGRATION")
            self.generation = snap["generation"]
            base_seq = snap["wal_seq"]
            self.floors = {sk: dict(v) for sk, v in state["floors"].items()}
            self.frozen = set(state["frozen"])
            self.guard = CounterGuard.restore(state["guard"])
            self.recent_ops = dict.fromkeys(state["recent_ops"])
            for sealed in state["frontier"]:
                self._apply_core(self._unseal(sealed), recovering=True)
            self.discarded_before_snapshot = dict(state["discarded_counts"])
        self.wal = WriteAheadLog(self.dir / "wal.log")
        replayed = errors = 0
        for rec in self.wal.records_after(base_seq):
            try:
                if rec["kind"] == "apply":
                    doc = self._unseal(rec["body"])
                    self._apply_core(doc, recovering=True)
                    replayed += 1
                elif rec["kind"] == "freeze":
                    self.frozen.add(rec["body"]["sk"])
                elif rec["kind"] == "unfreeze":
                    self.frozen.discard(rec["body"]["sk"])
                elif rec["kind"] == "gc":
                    self._gc_key(rec["body"]["sk"], rec["body"]["floor"])
            except Gap05Error as exc:
                errors += 1
                self.log.emit("error", "recovery_record_rejected", code=exc.code, seq=rec["seq"])
            except ValueError as exc:  # core model refusal (e.g. equivocation)
                errors += 1
                self.log.emit("error", "recovery_record_rejected", code="CORR_CORE_REFUSED", seq=rec["seq"],
                              detail=str(exc))
        # Close the crash window between WAL durability and the audit append: every
        # replayed apply record newer than the last audited WAL sequence is audited now.
        last_audited = self.audit.last_field("wal_seq") or 0
        backfilled = 0
        for rec in self.wal.records_after(max(base_seq, last_audited)):
            if rec["kind"] == "apply":
                d = rec["body"]["doc"]
                self.audit.append("apply_recovered", wal_seq=rec["seq"], op_id=d["op_id"], tenant=d["tenant"],
                                  environment=d["environment"], site=d["site"], epoch=d["epoch"])
                backfilled += 1
        self.recovery_report = {"audit_backfilled": backfilled, "snapshot_generation": self.generation, "snapshot_rejected": rejected,
                                "wal": self.wal.recovery_report, "replayed": replayed, "rejected": errors}
        for sk, rk in self.keys_state.items():
            for w in rk.siblings + [e["write"] for e in rk.quarantine]:
                if w.site == self.name:
                    self.allocator.observe(sk, dict(w.vector)[self.name])

    # ------------------------------------------------------------------ core apply
    def _apply_core(self, doc: dict, *, recovering: bool = False) -> str:
        sk = state_key(doc["tenant"], doc["environment"], doc["key"])
        vec = {s: c for s, c in doc["vector"]}
        floor = self.floors.get(sk)
        if floor is not None and all(c <= floor.get(s, 0) for s, c in vec.items()):
            return "superseded"
        rk = self._rk(sk)
        outcome = rk.apply(self._to_core(doc))
        if self.name in vec:  # never re-issue an own counter a peer already holds (restore safety)
            self.allocator.observe(sk, vec[self.name])
        if outcome != "duplicate":
            self.docs[doc["op_id"]] = doc
            self.by_vector[(sk, tuple(tuple(e) for e in doc["vector"]))] = doc["op_id"]
            self.guard.record(sk, doc["site"], vec, doc["op_id"])
        self.recent_ops[doc["op_id"]] = None
        if len(self.recent_ops) > self.recent_window:
            for old in list(self.recent_ops)[: len(self.recent_ops) // 10]:
                del self.recent_ops[old]
        return outcome

    def _frontier_docs(self, sk: str) -> list[dict]:
        rk = self.keys_state.get(sk)
        if rk is None:
            return []
        out = []
        for w in rk.siblings + [e["write"] for e in rk.quarantine]:
            out.append(self.docs[self.by_vector[(sk, w.vector)]])
        return out

    # ------------------------------------------------------------------ accept path
    def submit(self, doc: dict, *, principal: str, relay: bool = False, recovery: bool = False,
               trace_id: str | None = None, allow_frozen: bool = False) -> dict:
        trace_id = trace_id or new_trace_id()
        span = new_span_id()
        try:
            result = self._submit(doc, principal=principal, relay=relay, recovery=recovery, trace_id=trace_id,
                                  allow_frozen=allow_frozen)
        except Gap05Error as exc:
            self.metrics.inc("apply_total", outcome="rejected", code=exc.code)
            self.log.emit("warn", "write_rejected", code=exc.code, principal=principal,
                          op_id=doc.get("op_id") if isinstance(doc, dict) else None, trace_id=trace_id, span_id=span)
            raise
        self.log.emit("info", "write_applied", outcome=result["outcome"], op_id=result["op_id"],
                      tenant=result["tenant"], environment=result["environment"], site=doc.get("site"),
                      principal=principal, trace_id=trace_id, span_id=span, value=doc.get("value"))
        return result

    def _submit(self, doc, *, principal, relay, recovery, trace_id, allow_frozen=False) -> dict:
        if self.degraded:
            raise IntegrityError(f"node is fail-stopped: {self.degraded}", code="CORR_FAIL_STOP")
        doc = validate_write_doc(doc, self.limits)
        self.limits.check_key(doc["key"])
        self.limits.check_value(doc["value"])
        self.limits.check_vector(doc["vector"])
        sk = state_key(doc["tenant"], doc["environment"], doc["key"])
        perm = Permission.REPLICATE if relay else Permission.WRITE
        self.authz.require(principal, perm, doc["tenant"], doc["environment"])
        verify_write(doc, self.membership)
        vec = {s: c for s, c in doc["vector"]}
        unknown = set(vec) - set(self.membership.current.known)
        if unknown:
            raise SecurityError(f"vector names unknown replicas {sorted(unknown)}", code="SEC_UNKNOWN_REPLICA")
        self.membership.check_authorship(doc["site"], doc["epoch"], sk, vec[doc["site"]])
        with self._shard(sk):
            if sk in self.frozen and not relay and not allow_frozen:
                raise ConflictStillOpen("key is frozen by an operator", code="CORR_KEY_FROZEN")
            if doc["op_id"] in self.recent_ops or doc["op_id"] in self.docs:
                self.metrics.inc("apply_total", outcome="duplicate")
                self.metrics.inc("replay_total")
                return make_merge_result(tenant=doc["tenant"], environment=doc["environment"], key=doc["key"],
                                         op_id=doc["op_id"], outcome="duplicate", reason="op_id already applied")
            self.admission.admit(doc["tenant"], doc["key"], recovery=recovery)
            self.guard.check(sk, doc["site"], vec, doc["op_id"])
            rk = self.keys_state.get(sk)
            if rk is not None and len(rk.siblings) + len(rk.quarantine) >= self.limits.max_unresolved_per_key:
                if not any(dominates(vec, dict(w.vector)) for w in rk.siblings + [e["write"] for e in rk.quarantine]):
                    raise CapacityError("unresolved frontier at max_unresolved_per_key; refusing (write not "
                                        "accepted, sender must retry after resolution)", code="CAP_FRONTIER_FULL")
            existing = self.by_vector.get((sk, tuple(tuple(e) for e in doc["vector"])))
            if existing is not None and existing != doc["op_id"] and existing in self.docs:
                raise IntegrityError("vector already identifies different content (equivocation)",
                                     code="SEC_VECTOR_EQUIVOCATION")
            self.audit.ensure_capacity()
            wal_rec = self.wal.append("apply", self._seal(doc))
            _maybe_crash("node_after_wal_before_audit")
            try:
                outcome = self._apply_core(doc)
            except Exception as exc:  # durable but not applied -> fail-stop, recovery will classify
                self.degraded = f"apply failed after WAL append: {exc}"
                raise IntegrityError(self.degraded, code="CORR_FAIL_STOP") from exc
            self.audit.append("apply", wal_seq=wal_rec["seq"], op_id=doc["op_id"], tenant=doc["tenant"], environment=doc["environment"],
                              key_digest=hashlib.sha256(doc["key"].encode()).hexdigest()[:16], site=doc["site"],
                              principal=principal, outcome=outcome, epoch=doc["epoch"], trace_id=trace_id)
            rk = self.keys_state.get(sk)
            width = len(rk.siblings) if rk else 0
            qdepth = len(rk.quarantine) if rk else 0
        self.metrics.inc("apply_total", outcome=outcome)
        self.metrics.set("frontier_width", width, tenant=doc["tenant"])
        self.metrics.set("quarantine_depth", qdepth, tenant=doc["tenant"])
        self.metrics.observe("vector_entries", len(doc["vector"]))
        self.metrics.set("wal_records", len(self.wal.records))
        self.analytics.record(doc["tenant"], doc["key"], outcome,
                              [w.site for w in (rk.siblings if rk else [])])
        conflict = self.conflict_set(doc["tenant"], doc["environment"], doc["key"]) if outcome in (
            "conflict", "quarantined") else None
        return make_merge_result(tenant=doc["tenant"], environment=doc["environment"], key=doc["key"],
                                 op_id=doc["op_id"], outcome=outcome, conflict=conflict)

    # ------------------------------------------------------------------ local authoring
    def write(self, tenant, environment, key, value, *, principal, context: dict | None = None,
              deleted: bool = False, value_type: str | None = None, _resolving: bool = False) -> dict:
        if self.recovery_mode:
            raise IntegrityError("node restored from backup: sync from a peer before authoring",
                                 code="CORR_RECOVERY_MODE")
        sk = state_key(tenant, environment, key)
        with self._shard(sk):
            frontier = self._frontier_docs(sk)
            if context is None:
                if len(frontier) > 1:
                    raise ConflictStillOpen("key has an open conflict; pass the observed context or resolve",
                                            code="CORR_CONFLICT_OPEN")
                context = {s: c for d in frontier for s, c in d["vector"]}
            vec = {s: c for s, c in context.items()}
            floor = self.floors.get(sk, {})
            for s, c in floor.items():
                vec[s] = max(vec.get(s, 0), c)
            own = max(self.allocator.next(sk), vec.get(self.name, 0) + 1)
            self.allocator.observe(sk, own)
            vec[self.name] = own
            doc = make_write_doc(tenant=tenant, environment=environment, key=key, value=value, site=self.name,
                                 vector=vec, epoch=self.membership.epoch, deleted=deleted, value_type=value_type)
            doc = sign_write(doc, self.keys.private_key)
            return self.submit(doc, principal=principal, allow_frozen=_resolving)

    def delete(self, tenant, environment, key, *, principal, context=None) -> dict:
        return self.write(tenant, environment, key, "", principal=principal, context=context, deleted=True)

    def resolve(self, tenant, environment, key, value, *, principal, decision: dict | None = None) -> dict:
        sk = state_key(tenant, environment, key)
        self.authz.require(principal, Permission.RESOLVE, tenant, environment)
        with self._shard(sk):
            frontier = self._frontier_docs(sk)
            if len(frontier) <= 1:
                raise ConflictStillOpen("nothing to resolve", code="CORR_NOTHING_TO_RESOLVE")
            ctx: dict = {}
            for d in frontier:
                for s, c in d["vector"]:
                    ctx[s] = max(ctx.get(s, 0), c)
            if decision is not None:
                from .schemas import digest
                if decision.get("frontier_digest") != digest(self.conflict_set(tenant, environment, key)):
                    raise ConflictStillOpen("frontier changed since the policy decision; re-request",
                                            code="CORR_STALE_DECISION")
            result = self.write(tenant, environment, key, value, principal=principal, context=ctx, _resolving=True)
            if sk in self.frozen:
                self.wal.append("unfreeze", {"sk": sk})
                self.frozen.discard(sk)
            self.audit.append("resolve", tenant=tenant, environment=environment, principal=principal,
                              op_id=result["op_id"], resolved=[d["op_id"] for d in frontier],
                              policy_version=(decision or {}).get("policy_version"),
                              evidence=(decision or {}).get("evidence"))
            self.analytics.record_resolution(tenant, key, (decision or {}).get("policy_version", "manual"))
            return result

    # ------------------------------------------------------------------ reads / views
    def read(self, tenant, environment, key, *, principal) -> dict:
        self.authz.require(principal, Permission.READ, tenant, environment)
        sk = state_key(tenant, environment, key)
        with self._shard(sk):
            frontier = self._frontier_docs(sk)
        if not frontier:
            return {"state": "absent"}
        if len(frontier) == 1:
            d = frontier[0]
            return {"state": "deleted"} if d.get("deleted") else {"state": "value", "value": d["value"]}
        types = {d.get("value_type") for d in frontier}
        if len(types) == 1 and crdt.is_commutative(next(iter(types))) and not any(d.get("deleted") for d in frontier):
            vt = next(iter(types))
            return {"state": "value", "value": crdt.merge_all(vt, [d["value"] for d in frontier]), "merged": vt}
        return {"state": "conflict", "conflict": self.conflict_set(tenant, environment, key)}

    def conflict_set(self, tenant, environment, key) -> dict:
        sk = state_key(tenant, environment, key)
        rk = self.keys_state.get(sk)
        if rk is None:
            return {"schema": CONFLICT_SCHEMA, "key": key, "siblings": [], "quarantined": [], "open": False,
                    "total_unresolved": 0}
        cs = rk.conflict_set()
        cs["key"] = key
        for group in ("siblings", "quarantined"):
            for item in cs[group]:
                item["vector"] = [list(e) for e in item["vector"]]
        return cs

    def view(self, tenant, environment, key) -> FrontierView:
        sk = state_key(tenant, environment, key)
        with self._shard(sk):
            rk = self.keys_state.get(sk)
            active = tuple(MappingProxyType(copy.deepcopy(d)) for d in self._frontier_docs(sk)[: len(rk.siblings)]) if rk else ()
            quarantined = tuple(MappingProxyType(copy.deepcopy(d)) for d in self._frontier_docs(sk)[len(rk.siblings):]) if rk else ()
            return FrontierView(tenant, environment, key, active, quarantined,
                                len(rk.discarded) if rk else 0, bool(rk and not rk.converged), sk in self.frozen,
                                tuple(sorted(self.floors.get(sk, {}).items())))

    def state_keys(self):
        return sorted(self.keys_state)

    # ------------------------------------------------------------------ tombstone GC (MC19/MC20)
    def gc_tombstones(self, acknowledged: dict[str, dict]) -> list[str]:
        """Collect converged tombstones every *active* replica has acknowledged.

        ``acknowledged`` maps replica -> {state_key: vector it has durably applied}.
        A collected key keeps a compact *floor* vector so any write the tombstone
        dominates is still classified superseded (no resurrection).
        """
        collected = []
        active = self.membership.current.active
        for sk in list(self.keys_state):
            frontier = self._frontier_docs(sk)
            if len(frontier) != 1 or not frontier[0].get("deleted"):
                continue
            vec = {s: c for s, c in frontier[0]["vector"]}
            if all(sk in acknowledged.get(r, {}) and all(acknowledged[r][sk].get(s, 0) >= c for s, c in vec.items())
                   for r in active):
                self.wal.append("gc", {"sk": sk, "floor": vec})
                self._gc_key(sk, vec)
                self.audit.append("tombstone_gc", key_digest=hashlib.sha256(sk.encode()).hexdigest()[:16],
                                  floor=vec)
                collected.append(sk)
        return collected

    def _gc_key(self, sk: str, floor: dict) -> None:
        prev = self.floors.get(sk, {})
        self.floors[sk] = {s: max(prev.get(s, 0), floor.get(s, 0)) for s in set(prev) | set(floor)}
        rk = self.keys_state.pop(sk, None)
        if rk:
            for w in rk.siblings + [e["write"] for e in rk.quarantine]:
                op = self.by_vector.pop((sk, w.vector), None)
                self.docs.pop(op, None)

    # ------------------------------------------------------------------ operator (MC22)
    def freeze(self, tenant, environment, key, *, principal, reason: str):
        self.authz.require(principal, Permission.QUARANTINE_ADMIN, tenant, environment)
        sk = state_key(tenant, environment, key)
        self.wal.append("freeze", {"sk": sk})
        self.frozen.add(sk)
        self.audit.append("freeze", principal=principal, reason=reason,
                          key_digest=hashlib.sha256(sk.encode()).hexdigest()[:16])

    def unfreeze(self, tenant, environment, key, *, principal, reason: str):
        self.authz.require(principal, Permission.QUARANTINE_ADMIN, tenant, environment)
        sk = state_key(tenant, environment, key)
        self.wal.append("unfreeze", {"sk": sk})
        self.frozen.discard(sk)
        self.audit.append("unfreeze", principal=principal, reason=reason,
                          key_digest=hashlib.sha256(sk.encode()).hexdigest()[:16])

    def quarantine_list(self, tenant, environment, *, principal) -> list[dict]:
        self.authz.require(principal, Permission.INSPECT_CONFLICTS, tenant, environment)
        out = []
        for sk in self.state_keys():
            t, e, k = split_key(sk)
            if (t, e) != (tenant, environment):
                continue
            rk = self.keys_state[sk]
            if rk.quarantine or not rk.converged:
                out.append({"key": k, "active": len(rk.siblings), "quarantined": len(rk.quarantine),
                            "frozen": sk in self.frozen})
        return out

    def quarantine_export(self, tenant, environment, key, *, principal) -> dict:
        self.authz.require(principal, Permission.INSPECT_CONFLICTS, tenant, environment)
        cs = self.conflict_set(tenant, environment, key)
        self.audit.append("quarantine_export", principal=principal, tenant=tenant, environment=environment,
                          total=cs["total_unresolved"])
        return cs

    # ------------------------------------------------------------------ checkpoint (MC05)
    def checkpoint(self) -> Path:
        with self._global:
            locks = list(self._shards)
            for lk in locks:
                lk.acquire()
            try:
                frontier = [self._seal(d) for sk in self.state_keys() for d in self._frontier_docs(sk)]
                state = {"state_format": STATE_FORMAT_VERSION, "frontier": frontier,
                         "floors": self.floors, "frozen": sorted(self.frozen), "guard": self.guard.export(),
                         "recent_ops": list(self.recent_ops),
                         "discarded_counts": {sk: len(rk.discarded) for sk, rk in self.keys_state.items()},
                         "membership_epoch": self.membership.epoch}
                self.generation += 1
                seq = self.wal.next_seq - 1
                path = self.snapshots.write(self.generation, seq, state)
                self.wal.compact_before(seq)
                self.audit.append("checkpoint", generation=self.generation, wal_seq=seq)
                return path
            finally:
                for lk in reversed(locks):
                    lk.release()

    # ------------------------------------------------------------------ health (MC28)
    def health(self) -> dict:
        q_total = sum(len(rk.quarantine) for rk in self.keys_state.values())
        q_pressure = q_total / self.limits.max_quarantine_total
        reasons = []
        if self.degraded:
            reasons.append(f"fail-stop: {self.degraded}")
        if self.recovery_mode:
            reasons.append("recovery mode: awaiting peer sync")
        if self.recovery_report.get("rejected"):
            reasons.append(f"recovery rejected {self.recovery_report['rejected']} durable records")
        if self.audit.pressure >= 0.9:
            reasons.append("audit pressure >= 90%")
        if q_pressure >= 0.9:
            reasons.append("quarantine pressure >= 90%")
        try:
            self.membership.current.validate()
            membership_ok = True
        except Gap05Error:
            membership_ok = False
            reasons.append("membership invalid")
        return {"live": self.degraded is None, "ready": not reasons, "reasons": reasons,
                "membership_epoch": self.membership.epoch, "replica": self.name,
                "schemas": {"PK_REPLICATED_WRITE": [1], "PK_MERGE_RESULT": [1], "PK_CONFLICT_SET": [1]},
                "wal_records_since_checkpoint": len(self.wal.records), "snapshot_generation": self.generation,
                "quarantine_total": q_total, "quarantine_pressure": q_pressure, "audit_pressure": self.audit.pressure,
                "frozen_keys": len(self.frozen), "recovery": self.recovery_report, "membership_ok": membership_ok}

    def close(self):
        self.wal.close()
