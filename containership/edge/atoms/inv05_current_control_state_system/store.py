"""Production control-state engine for INV-05 (v4.3.0).

This is the revisioned multi-version key/value engine behind the service.
It supersedes the minimal :mod:`state` reference model (kept unchanged for
backward compatibility) and implements:

* revision-aware point/range/prefix reads with stable pagination (MC-008);
* explicit deletes with tombstones and typed DELETE/EXPIRE events (MC-009);
* compare / success / failure transactions evaluated and applied against one
  revision, with per-op results and no partial success (MC-010);
* typed compare predicates on existence, value, version, create/mod revision,
  lease attachment and lease fencing tokens (MC-011);
* a versioned event model (MC-016) and atomic snapshot acquisition (MC-017);
* leases with TTL, keepalive, fencing tokens and attached-key cleanup (MC-018);
* compaction that respects protected revisions (MC-019-04);
* token idempotency for replay-safe retries (MC-026-05);
* a write-ahead ``journal`` hook: every mutation is journaled *before* it is
  applied or acknowledged, and a journal failure puts the engine into a
  fail-closed ``FAILED`` state (MC-006-01, MC-044-05).

Every mutation is expressed as a deterministic *record* that is both written to
the journal and applied through :meth:`ControlStore.apply_record`, so recovery
replays exactly the code path that produced the acknowledged state.

Transaction semantics (normative):

1. All compares are evaluated against the store at revision ``R`` (the current
   revision when the store lock is taken).  Evaluation is atomic; there is no
   short-circuit that can observe a different revision.
2. The branch (``success`` if every compare holds, else ``failure``) is
   validated as a whole before anything is journaled.  A branch may not write
   the same key twice nor put a key it also deletes (ambiguous).
3. Range ops inside a branch read the pre-transaction state at ``R``.
4. If the branch mutates anything, all its mutations share revision ``R+1``;
   events carry ``(revision, index)`` ordering.  Otherwise the revision is
   unchanged.
"""
from __future__ import annotations

import base64
import bisect
import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable, Optional, Protocol, Sequence

from .errors import (
    CompactedError, FailedClosed, FutureRevision, IdempotencyConflict, InvalidArgument,
    LeaseNotFound, LimitExceeded, Overloaded, StateError, Unavailable, UnsupportedPredicate,
)
from .limits import Limits, canonical_json, validate_key, validate_revision, validate_value

EVENT_SCHEMA_VERSION = "cstate.event/1"
RECORD_SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- model

@dataclass(frozen=True)
class KeyVersion:
    mod_revision: int
    value: Any
    create_revision: int
    version: int              # per-key logical version; 0 == tombstone
    lease: int = 0

    @property
    def deleted(self) -> bool:
        return self.version == 0


@dataclass(frozen=True)
class KeyValue:
    key: str
    value: Any
    create_revision: int
    mod_revision: int
    version: int
    lease: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Event:
    """Typed change event (MC-016).  ``kind`` in CREATE/UPDATE/DELETE/EXPIRE."""
    revision: int
    index: int
    kind: str
    key: str
    value: Any
    prev_value: Any
    create_revision: int
    mod_revision: int
    version: int
    lease: int = 0
    txn_id: str = ""
    schema: str = EVENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Event":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


EVENT_KINDS = ("CREATE", "UPDATE", "DELETE", "EXPIRE")

COMPARE_TARGETS = {
    "EXISTS": {"=="},
    "VALUE": {"==", "!="},
    "VERSION": {"==", "!=", "<", ">", "<=", ">="},
    "CREATE": {"==", "!=", "<", ">", "<=", ">="},
    "MOD": {"==", "!=", "<", ">", "<=", ">="},
    "LEASE": {"==", "!="},
    "FENCE": {"=="},
}


@dataclass(frozen=True)
class Compare:
    """Typed predicate.  For ``FENCE`` the key is ``lease:<id>`` and the operand
    is the fencing token the caller believes it holds."""
    key: str
    target: str
    op: str
    operand: Any


@dataclass(frozen=True)
class Put:
    key: str
    value: Any
    lease: int = 0


@dataclass(frozen=True)
class Delete:
    key: str
    prefix: bool = False


@dataclass(frozen=True)
class Range:
    key: str
    range_end: str = ""          # exclusive; "" == point read
    prefix: bool = False
    revision: int = 0            # 0 == current
    limit: int = 0
    page_token: str = ""


Op = Put | Delete | Range


@dataclass
class RangeResult:
    revision: int
    kvs: list[KeyValue]
    more: bool = False
    next_token: str = ""
    count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"revision": self.revision, "kvs": [kv.to_dict() for kv in self.kvs],
                "more": self.more, "next_token": self.next_token, "count": self.count}


@dataclass
class TxnResult:
    succeeded: bool
    revision: int
    responses: list[dict[str, Any]]
    compare_results: list[bool] = field(default_factory=list)
    txn_id: str = ""
    durability: str = "memory"
    replayed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"succeeded": self.succeeded, "revision": self.revision, "responses": self.responses,
                "compare_results": self.compare_results, "txn_id": self.txn_id,
                "durability": self.durability, "replayed": self.replayed}


@dataclass
class Lease:
    id: int
    ttl: int
    owner: str
    fence: int
    granted_revision: int
    deadline: float
    keys: set[str] = field(default_factory=set)

    def remaining(self, now: float) -> float:
        return max(0.0, self.deadline - now)


class Journal(Protocol):
    durability: str

    def append(self, record: dict[str, Any]) -> None: ...


def prefix_end(prefix: str) -> str:
    """Smallest string greater than every string with *prefix* ("" = unbounded)."""
    if not prefix:
        return ""
    last = ord(prefix[-1])
    if last >= 0x10FFFF:
        return prefix_end(prefix[:-1])
    return prefix[:-1] + chr(last + 1)


def request_fingerprint(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=repr).encode()).hexdigest()


# --------------------------------------------------------------------------- engine

class ControlStore:
    """Thread-safe MVCC control-state engine.  See module docstring."""

    def __init__(self, limits: Limits | None = None, *, journal: Journal | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.limits = limits or Limits()
        self.journal = journal
        self.clock = clock
        self._lock = threading.RLock()
        self._rev = 0
        self._compact_rev = 0
        self._keys: dict[str, list[KeyVersion]] = {}
        self._sorted: list[str] = []
        self._events: list[Event] = []
        self._leases: dict[int, Lease] = {}
        self._next_lease = 1
        self._fence = 0
        self._protected: dict[str, int] = {}
        self._idem: OrderedDict[str, tuple[str, dict[str, Any]]] = OrderedDict()
        self._listeners: list[Callable[[list[Event], int], None]] = []
        self.failed_reason: str = ""
        self.counters: dict[str, int] = {"txn_total": 0, "txn_conflicts": 0, "compacted_refusals": 0,
                                         "leases_expired": 0, "idempotent_replays": 0}

    # ----------------------------------------------------------------- properties
    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def revision(self) -> int:
        with self._lock:
            return self._rev

    @property
    def compact_revision(self) -> int:
        with self._lock:
            return self._compact_rev

    @property
    def history_size(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def key_count(self) -> int:
        with self._lock:
            return sum(1 for v in self._keys.values() if not v[-1].deleted)

    @property
    def failed(self) -> bool:
        return bool(self.failed_reason)

    def add_listener(self, fn: Callable[[list[Event], int], None]) -> None:
        """Register a commit listener; called under the store lock, must not block."""
        with self._lock:
            self._listeners.append(fn)

    # ----------------------------------------------------------------- guards
    def _check_serving(self) -> None:
        if self.failed_reason:
            raise FailedClosed(f"store failed closed: {self.failed_reason}", reason=self.failed_reason)

    def fail_closed(self, reason: str) -> None:
        with self._lock:
            self.failed_reason = reason or "unspecified"

    def _check_read_rev(self, rev: int) -> int:
        rev = validate_revision(rev)
        if rev == 0:
            return self._rev
        if rev > self._rev:
            raise FutureRevision(f"revision {rev} is in the future", current_revision=self._rev, revision=rev)
        if rev < self._compact_rev:
            self.counters["compacted_refusals"] += 1
            raise CompactedError(f"revision {rev} compacted", compact_revision=self._compact_rev, revision=rev)
        return rev

    # ----------------------------------------------------------------- reads
    def _version_at(self, key: str, rev: int) -> KeyVersion | None:
        versions = self._keys.get(key)
        if not versions:
            return None
        i = bisect.bisect_right([v.mod_revision for v in versions], rev) - 1
        if i < 0:
            return None
        v = versions[i]
        return None if v.deleted else v

    def get(self, key: str, revision: int = 0) -> KeyValue | None:
        key = validate_key(key, self.limits)
        with self._lock:
            self._check_serving()
            rev = self._check_read_rev(revision)
            v = self._version_at(key, rev)
            return None if v is None else KeyValue(key, v.value, v.create_revision, v.mod_revision, v.version, v.lease)

    @staticmethod
    def _encode_token(key: str, rev: int, end: str) -> str:
        return base64.urlsafe_b64encode(json.dumps({"k": key, "r": rev, "e": end}).encode()).decode()

    @staticmethod
    def _decode_token(tok: str) -> tuple[str, int, str]:
        try:
            d = json.loads(base64.urlsafe_b64decode(tok.encode()))
            return str(d["k"]), validate_revision(d["r"]), str(d["e"])
        except (ValueError, KeyError, TypeError, StateError) as exc:
            raise InvalidArgument("malformed page token", field="page_token") from exc

    def range(self, r: Range) -> RangeResult:
        """Point/prefix/range read at a fixed revision with stable pagination (MC-008)."""
        with self._lock:
            self._check_serving()
            return self._range_locked(r)

    def _range_locked(self, r: Range) -> RangeResult:
        start = validate_key(r.key, self.limits) if r.key else ""
        if r.prefix:
            end = prefix_end(start)
        elif r.range_end:
            end = validate_key(r.range_end, self.limits)
            if end <= start:
                raise InvalidArgument("range_end must be greater than key", field="range_end")
        else:
            end = None  # point read
        limit = r.limit or self.limits.default_page_size
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise InvalidArgument("limit must be a positive int", field="limit")
        if limit > self.limits.max_page_size:
            raise LimitExceeded("page too large", limit="max_page_size", limit_value=self.limits.max_page_size)
        rev_req = r.revision
        after = None
        if r.page_token:
            tk, trev, tend = self._decode_token(r.page_token)
            if end is None or tend != end:
                raise InvalidArgument("page token does not match range", field="page_token")
            after, rev_req = tk, trev
        rev = self._check_read_rev(rev_req)
        if end is None:
            v = self._version_at(start, rev)
            kvs = [] if v is None else [KeyValue(start, v.value, v.create_revision, v.mod_revision, v.version, v.lease)]
            return RangeResult(rev, kvs, False, "", len(kvs))
        lo = bisect.bisect_right(self._sorted, after) if after is not None else bisect.bisect_left(self._sorted, start)
        hi = bisect.bisect_left(self._sorted, end) if end else len(self._sorted)
        kvs: list[KeyValue] = []
        more = False
        size = 0
        for k in self._sorted[lo:hi]:
            v = self._version_at(k, rev)
            if v is None:
                continue
            if len(kvs) >= limit:
                more = True
                break
            size += len(k) + len(canonical_json(v.value))
            if size > self.limits.max_response_bytes and kvs:
                more = True
                break
            kvs.append(KeyValue(k, v.value, v.create_revision, v.mod_revision, v.version, v.lease))
        tok = self._encode_token(kvs[-1].key, rev, end) if more else ""
        return RangeResult(rev, kvs, more, tok, len(kvs))

    def snapshot(self, prefix: str = "") -> RangeResult:
        """Atomic full snapshot of *prefix* plus its revision (MC-017-01)."""
        with self._lock:
            self._check_serving()
            out: list[KeyValue] = []
            rev = self._rev
            tok = ""
            while True:
                res = self._range_locked(Range(key=prefix, prefix=True, revision=rev,
                                               limit=self.limits.max_page_size, page_token=tok))
                out.extend(res.kvs)
                if not res.more:
                    return RangeResult(rev, out, False, "", len(out))
                tok = res.next_token

    def events_since(self, from_rev: int, prefix: str = "") -> list[Event]:
        """Retained events with ``revision >= from_rev`` (caller must hold lock for atomicity)."""
        from_rev = validate_revision(from_rev, "start_revision")
        with self._lock:
            if from_rev == 0:
                from_rev = self._rev + 1
            if from_rev <= self._compact_rev:
                self.counters["compacted_refusals"] += 1
                raise CompactedError(f"revision {from_rev} compacted; relist",
                                     compact_revision=self._compact_rev, revision=from_rev)
            i = bisect.bisect_left([e.revision for e in self._events], from_rev)
            evs = self._events[i:]
            return [e for e in evs if e.key.startswith(prefix)] if prefix else list(evs)

    # ----------------------------------------------------------------- compare
    def _validate_compare(self, c: Compare) -> None:
        if not isinstance(c, Compare):
            raise InvalidArgument("compare must be a Compare", field="compare")
        ops = COMPARE_TARGETS.get(c.target)
        if ops is None or c.op not in ops:
            raise UnsupportedPredicate(f"unsupported predicate {c.target} {c.op}", field="compare",
                                       supported=sorted(COMPARE_TARGETS))
        if c.target == "FENCE":
            if not isinstance(c.key, str) or not c.key.startswith("lease:") or not c.key[6:].isdigit():
                raise InvalidArgument("FENCE compare key must be 'lease:<id>'", field="compare.key")
            validate_revision(c.operand, "compare.operand")
            return
        validate_key(c.key, self.limits)
        if c.target == "EXISTS":
            if not isinstance(c.operand, bool):
                raise UnsupportedPredicate("EXISTS operand must be bool", field="compare.operand")
        elif c.target == "VALUE":
            validate_value(c.operand, self.limits)
        else:
            validate_revision(c.operand, "compare.operand")

    def _eval_compare(self, c: Compare, rev: int) -> bool:
        if c.target == "FENCE":
            lease = self._leases.get(int(c.key[6:]))
            return lease is not None and lease.deadline > self.clock() and lease.fence == c.operand
        v = self._version_at(c.key, rev)
        if c.target == "EXISTS":
            return (v is not None) == c.operand
        if c.target == "VALUE":
            eq = v is not None and canonical_json(v.value) == canonical_json(c.operand)
            return eq if c.op == "==" else not eq
        actual = {"VERSION": v.version if v else 0, "CREATE": v.create_revision if v else 0,
                  "MOD": v.mod_revision if v else 0, "LEASE": v.lease if v else 0}[c.target]
        return {"==": actual == c.operand, "!=": actual != c.operand, "<": actual < c.operand,
                ">": actual > c.operand, "<=": actual <= c.operand, ">=": actual >= c.operand}[c.op]

    # ----------------------------------------------------------------- txn
    def _validate_branch(self, ops: Sequence[Op]) -> None:
        if len(ops) > self.limits.max_txn_ops:
            raise LimitExceeded("too many ops", limit="max_txn_ops", limit_value=self.limits.max_txn_ops)
        put_keys: set[str] = set()
        del_points: set[str] = set()
        del_prefixes: list[str] = []
        total = 0
        for op in ops:
            if isinstance(op, Put):
                validate_key(op.key, self.limits)
                total += len(validate_value(op.value, self.limits)) + len(op.key)
                validate_revision(op.lease, "lease")
                if op.key in put_keys:
                    raise InvalidArgument(f"duplicate put of {op.key!r} in one branch", field="ops")
                put_keys.add(op.key)
            elif isinstance(op, Delete):
                validate_key(op.key, self.limits)
                if op.prefix:
                    del_prefixes.append(op.key)
                else:
                    del_points.add(op.key)
            elif isinstance(op, Range):
                pass
            else:
                raise InvalidArgument(f"unknown op type {type(op).__name__}", field="ops")
        if total > self.limits.max_request_bytes:
            raise LimitExceeded("transaction too large", limit="max_request_bytes",
                                limit_value=self.limits.max_request_bytes)
        for k in put_keys:
            if k in del_points or any(k.startswith(p) for p in del_prefixes):
                raise InvalidArgument(f"branch both puts and deletes {k!r}", field="ops")

    def txn(self, compares: Sequence[Compare] = (), success: Sequence[Op] = (), failure: Sequence[Op] = (),
            *, request_id: str = "", txn_id: str = "", actor: str = "") -> TxnResult:
        compares, success, failure = list(compares), list(success), list(failure)
        if len(compares) > self.limits.max_txn_compares:
            raise LimitExceeded("too many compares", limit="max_txn_compares",
                                limit_value=self.limits.max_txn_compares)
        for c in compares:
            self._validate_compare(c)
        self._validate_branch(success)
        self._validate_branch(failure)
        fp = ""
        if request_id:
            if not isinstance(request_id, str) or len(request_id) > 128:
                raise InvalidArgument("request_id must be a str of <=128 chars", field="request_id")
            fp = request_fingerprint([[asdict(c) for c in compares],
                                      [[type(o).__name__, asdict(o)] for o in success],
                                      [[type(o).__name__, asdict(o)] for o in failure]])
        with self._lock:
            self._check_serving()
            if request_id and request_id in self._idem:
                old_fp, res = self._idem[request_id]
                if old_fp != fp:
                    raise IdempotencyConflict("request_id reused with a different request", field="request_id")
                self.counters["idempotent_replays"] += 1
                r = TxnResult(**res)
                r.replayed = True
                return r
            self._expire_leases_locked()
            rev = self._rev
            results = [self._eval_compare(c, rev) for c in compares]
            ok = all(results)
            branch = success if ok else failure
            new_rev = rev + 1
            responses: list[dict[str, Any]] = []
            events: list[Event] = []
            for op in branch:
                if isinstance(op, Range):
                    responses.append({"range": self._range_locked(
                        Range(op.key, op.range_end, op.prefix, op.revision or rev, op.limit, op.page_token)).to_dict()})
                elif isinstance(op, Put):
                    if op.lease:
                        lease = self._leases.get(op.lease)
                        if lease is None or lease.deadline <= self.clock():
                            raise LeaseNotFound(f"lease {op.lease} not found", field="lease")
                    prev = self._version_at(op.key, rev)
                    kind = "UPDATE" if prev else "CREATE"
                    ev = Event(new_rev, len(events), kind, op.key, op.value, prev.value if prev else None,
                               prev.create_revision if prev else new_rev, new_rev,
                               (prev.version + 1) if prev else 1, op.lease, txn_id)
                    events.append(ev)
                    responses.append({"put": {"prev": prev.value if prev else None, "revision": new_rev}})
                else:
                    targets = self._delete_targets(op, rev)
                    for k, prev in targets:
                        events.append(Event(new_rev, len(events), "DELETE", k, None, prev.value,
                                            prev.create_revision, new_rev, 0, 0, txn_id))
                    responses.append({"delete": {"deleted": len(targets)}})
            if events and len(self._events) + len(events) > self.limits.max_history_events:
                raise Overloaded("history backlog full; compaction required", retry_after_s=1.0,
                                 limit="max_history_events")
            self.counters["txn_total"] += 1
            if not ok:
                self.counters["txn_conflicts"] += 1
            result = TxnResult(ok, new_rev if events else rev, responses, results, txn_id,
                               self.journal.durability if (self.journal and events) else "memory")
            if events or request_id:
                record = {"t": "txn", "v": RECORD_SCHEMA_VERSION, "rev": new_rev if events else rev,
                          "events": [e.to_dict() for e in events], "actor": actor}
                if request_id:
                    record["req"] = {"id": request_id, "fp": fp, "result": result.to_dict()}
                self._commit(record)
            return result

    def _delete_targets(self, op: Delete, rev: int) -> list[tuple[str, KeyVersion]]:
        if not op.prefix:
            v = self._version_at(op.key, rev)
            return [(op.key, v)] if v else []
        lo = bisect.bisect_left(self._sorted, op.key)
        hi = bisect.bisect_left(self._sorted, prefix_end(op.key)) if prefix_end(op.key) else len(self._sorted)
        out = []
        for k in self._sorted[lo:hi]:
            v = self._version_at(k, rev)
            if v:
                out.append((k, v))
        return out

    # convenience wrappers ----------------------------------------------------
    def put(self, key: str, value: Any, *, lease: int = 0, **kw: Any) -> TxnResult:
        return self.txn((), [Put(key, value, lease)], **kw)

    def delete(self, key: str, *, prefix: bool = False, **kw: Any) -> TxnResult:
        return self.txn((), [Delete(key, prefix)], **kw)

    def cas(self, key: str, expected_mod: int, value: Any, **kw: Any) -> TxnResult:
        return self.txn([Compare(key, "MOD", "==", expected_mod)], [Put(key, value)], **kw)

    # ----------------------------------------------------------------- leases
    def lease_grant(self, ttl: int, owner: str = "") -> Lease:
        if isinstance(ttl, bool) or not isinstance(ttl, int) or not (
                self.limits.min_lease_ttl_s <= ttl <= self.limits.max_lease_ttl_s):
            raise InvalidArgument(f"ttl must be in [{self.limits.min_lease_ttl_s}, {self.limits.max_lease_ttl_s}]",
                                  field="ttl")
        with self._lock:
            self._check_serving()
            if owner and sum(1 for l in self._leases.values() if l.owner == owner) >= self.limits.max_leases_per_identity:
                raise LimitExceeded("too many leases", limit="max_leases_per_identity",
                                    limit_value=self.limits.max_leases_per_identity)
            rec = {"t": "lease_grant", "v": RECORD_SCHEMA_VERSION, "id": self._next_lease, "ttl": ttl,
                   "owner": owner, "fence": self._fence + 1, "rev": self._rev}
            self._commit(rec)
            return self._copy_lease(self._leases[rec["id"]])

    @staticmethod
    def _copy_lease(l: Lease) -> Lease:
        return Lease(l.id, l.ttl, l.owner, l.fence, l.granted_revision, l.deadline, set(l.keys))

    def lease_keepalive(self, lease_id: int) -> Lease:
        with self._lock:
            self._check_serving()
            self._expire_leases_locked()
            l = self._leases.get(lease_id)
            if l is None:
                raise LeaseNotFound(f"lease {lease_id} not found")
            l.deadline = self.clock() + l.ttl  # volatile: re-armed on recovery (see ADR-004)
            return self._copy_lease(l)

    def lease_get(self, lease_id: int) -> Lease:
        with self._lock:
            self._expire_leases_locked()
            l = self._leases.get(lease_id)
            if l is None:
                raise LeaseNotFound(f"lease {lease_id} not found")
            return self._copy_lease(l)

    def lease_revoke(self, lease_id: int, *, reason: str = "revoke") -> int:
        with self._lock:
            self._check_serving()
            if lease_id not in self._leases:
                raise LeaseNotFound(f"lease {lease_id} not found")
            return self._end_lease_locked(lease_id, reason)

    def leases(self) -> list[Lease]:
        with self._lock:
            return [self._copy_lease(l) for l in self._leases.values()]

    def _end_lease_locked(self, lease_id: int, reason: str) -> int:
        lease = self._leases[lease_id]
        kind = "EXPIRE" if reason == "expire" else "DELETE"
        new_rev = self._rev + 1
        events = []
        for k in sorted(lease.keys):
            v = self._version_at(k, self._rev)
            if v and v.lease == lease_id:
                events.append(Event(new_rev, len(events), kind, k, None, v.value, v.create_revision,
                                    new_rev, 0, lease_id, f"lease-{reason}-{lease_id}").to_dict())
        self._commit({"t": "lease_end", "v": RECORD_SCHEMA_VERSION, "id": lease_id, "reason": reason,
                      "rev": new_rev if events else self._rev, "events": events})
        if reason == "expire":
            self.counters["leases_expired"] += 1
        return len(events)

    def _expire_leases_locked(self) -> int:
        if self.failed_reason:
            return 0
        now = self.clock()
        n = 0
        for lid in [l.id for l in self._leases.values() if l.deadline <= now]:
            self._end_lease_locked(lid, "expire")
            n += 1
        return n

    def tick(self) -> int:
        """Expire due leases; called by the service's background ticker."""
        with self._lock:
            return self._expire_leases_locked()

    # ----------------------------------------------------------------- compaction
    def protect(self, name: str, revision: int) -> None:
        """Pin a revision (snapshot/checkpoint) so compaction cannot pass it (MC-019-04)."""
        with self._lock:
            self._protected[name] = self._check_read_rev(revision)

    def unprotect(self, name: str) -> None:
        with self._lock:
            self._protected.pop(name, None)

    @property
    def protected(self) -> dict[str, int]:
        with self._lock:
            return dict(self._protected)

    def compact(self, revision: int) -> int:
        revision = validate_revision(revision, "compact_revision")
        with self._lock:
            self._check_serving()
            if revision > self._rev:
                raise InvalidArgument(f"cannot compact beyond current revision {self._rev}", field="revision",
                                      current_revision=self._rev)
            if revision <= self._compact_rev:
                return 0
            floor = min(self._protected.values(), default=None)
            if floor is not None and revision > floor:
                raise InvalidArgument(f"revision {revision} is past protected revision {floor}",
                                      field="revision", limit_value=floor)
            before = len(self._events)
            self._commit({"t": "compact", "v": RECORD_SCHEMA_VERSION, "rev": revision})
            return before - len(self._events)

    # ----------------------------------------------------------------- commit/apply
    def _commit(self, record: dict[str, Any]) -> None:
        """Journal (durably, if configured) then apply.  Journal failure => FAILED."""
        if self.journal is not None:
            try:
                self.journal.append(record)
            except Exception as exc:  # disk full, EIO, fsync failure ... never ack
                self.failed_reason = f"journal append failed: {type(exc).__name__}"
                raise FailedClosed("durable journal write failed; store is fail-closed",
                                   reason="journal_failure") from exc
        self.apply_record(record)

    def apply_record(self, rec: dict[str, Any]) -> None:
        """Deterministically apply one journal record (used live and on replay)."""
        t = rec.get("t")
        if rec.get("v", 1) != RECORD_SCHEMA_VERSION:
            raise ValueError(f"unsupported record version {rec.get('v')}")
        if t == "txn":
            evs = [Event.from_dict(e) for e in rec["events"]]
            self._apply_events(evs, rec["rev"])
            req = rec.get("req")
            if req:
                self._idem[req["id"]] = (req["fp"], req["result"])
                while len(self._idem) > self.limits.max_idempotency_entries:
                    self._idem.popitem(last=False)
        elif t == "lease_grant":
            self._leases[rec["id"]] = Lease(rec["id"], rec["ttl"], rec.get("owner", ""), rec["fence"], rec["rev"],
                                            self.clock() + rec["ttl"])
            self._next_lease = max(self._next_lease, rec["id"] + 1)
            self._fence = max(self._fence, rec["fence"])
        elif t == "lease_end":
            self._leases.pop(rec["id"], None)
            self._apply_events([Event.from_dict(e) for e in rec["events"]], rec["rev"])
        elif t == "compact":
            self._apply_compact(rec["rev"])
        else:
            raise ValueError(f"unknown record type {t!r}")

    def _apply_events(self, evs: list[Event], rev: int) -> None:
        if not evs:
            return
        if rev != self._rev + 1:
            raise ValueError(f"non-contiguous revision {rev} after {self._rev}")
        for e in evs:
            versions = self._keys.get(e.key)
            if versions is None:
                versions = self._keys[e.key] = []
                bisect.insort(self._sorted, e.key)
            prev = versions[-1] if versions else None
            if prev is not None and prev.lease and prev.lease in self._leases:
                self._leases[prev.lease].keys.discard(e.key)
            if e.kind in ("DELETE", "EXPIRE"):
                versions.append(KeyVersion(rev, None, 0, 0, 0))
            else:
                versions.append(KeyVersion(rev, e.value, e.create_revision, e.version, e.lease))
                if e.lease and e.lease in self._leases:
                    self._leases[e.lease].keys.add(e.key)
            self._events.append(e)
        self._rev = rev
        for fn in list(self._listeners):
            try:
                fn(evs, rev)
            except Exception:  # listeners must never break commit
                pass

    def _apply_compact(self, rev: int) -> None:
        self._events = [e for e in self._events if e.revision > rev]
        for k in list(self._keys):
            vs = self._keys[k]
            i = bisect.bisect_right([v.mod_revision for v in vs], rev) - 1
            if i > 0:
                vs = vs[i:]
            if vs and vs[0].mod_revision <= rev and vs[0].deleted:
                vs = vs[1:]
            if vs:
                self._keys[k] = vs
            else:
                del self._keys[k]
                j = bisect.bisect_left(self._sorted, k)
                if j < len(self._sorted) and self._sorted[j] == k:
                    self._sorted.pop(j)
        self._compact_rev = max(self._compact_rev, rev)

    # ----------------------------------------------------------------- snapshot export
    def export_state(self) -> dict[str, Any]:
        """Full consistent state for WAL snapshots and backups."""
        with self._lock:
            return {"schema": "cstate.snapshot/1", "revision": self._rev, "compact_revision": self._compact_rev,
                    "keys": {k: [asdict(v) for v in vs] for k, vs in self._keys.items()},
                    "events": [e.to_dict() for e in self._events],
                    "leases": [{"id": l.id, "ttl": l.ttl, "owner": l.owner, "fence": l.fence,
                                "granted_revision": l.granted_revision, "keys": sorted(l.keys)}
                               for l in self._leases.values()],
                    "next_lease": self._next_lease, "fence": self._fence,
                    "idem": [[k, fp, res] for k, (fp, res) in self._idem.items()]}

    def load_state(self, st: dict[str, Any]) -> None:
        if st.get("schema") != "cstate.snapshot/1":
            raise ValueError("unsupported snapshot schema")
        with self._lock:
            self._rev = st["revision"]
            self._compact_rev = st["compact_revision"]
            self._keys = {k: [KeyVersion(**v) for v in vs] for k, vs in st["keys"].items()}
            self._sorted = sorted(self._keys)
            self._events = [Event.from_dict(e) for e in st["events"]]
            now = self.clock()
            self._leases = {l["id"]: Lease(l["id"], l["ttl"], l["owner"], l["fence"], l["granted_revision"],
                                           now + l["ttl"], set(l["keys"])) for l in st["leases"]}
            self._next_lease = st["next_lease"]
            self._fence = st["fence"]
            self._idem = OrderedDict((k, (fp, res)) for k, fp, res in st.get("idem", []))

    def check_invariants(self) -> list[str]:
        """Return a list of violated invariants (empty == consistent).  Used by
        restore verification, recovery and property tests."""
        problems = []
        with self._lock:
            revs = [(e.revision, e.index) for e in self._events]
            if revs != sorted(revs) or len(set(revs)) != len(revs):
                problems.append("event order not strictly increasing")
            if self._events and self._events[0].revision <= self._compact_rev:
                problems.append("retained event at or below compact revision")
            if any(e.revision > self._rev for e in self._events):
                problems.append("event beyond current revision")
            if self._sorted != sorted(self._keys):
                problems.append("sorted key index out of sync")
            for k, vs in self._keys.items():
                mods = [v.mod_revision for v in vs]
                if mods != sorted(mods) or len(set(mods)) != len(mods):
                    problems.append(f"versions of {k!r} not strictly increasing")
                if mods and mods[-1] > self._rev:
                    problems.append(f"{k!r} modified beyond current revision")
            for l in self._leases.values():
                if l.fence > self._fence:
                    problems.append(f"lease {l.id} fence beyond counter")
        return problems
