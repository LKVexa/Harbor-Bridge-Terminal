"""Persistent, fenced history backend on SQLite (SG-01, SG-03, SG-05 reference, SG-09).

This is the repository's *reference* persistent backend: a real on-disk store
with atomic conditional append, lease/epoch fencing checked inside the same
transaction as every mutation, hash-chain validation on read, and quarantine on
corruption.  It is approved for single-host deployments and for conformance
testing of the backend contract.  It is NOT the INV-50 production state
abstraction; that binding stays BLOCKED until INV-50 is supplied (see
``STATUS_REGISTER.json``).

Durability contract: ``journal_mode=WAL`` + ``synchronous=FULL``; an append is
"completed" only when ``COMMIT`` returns.  A crash before COMMIT loses the
event (replay sees the previous tail); a crash after COMMIT keeps it.
``tests/test_crash_boundaries.py`` kills a real subprocess at both points.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import sqlite3
import time
from typing import Any, Callable, Iterable

from .durable import HistoryCorruption, HistoryEvent, InMemoryHistoryStore
from .errors import (HistoryQuarantined, OwnershipConflict, StaleOwner,
                     ConcurrentAppend, Unauthorized)
from .identity import WorkflowIdentity
from . import lifecycle as lc

BACKEND_SCHEMA_VERSION = 1
CRASH_ENV = "INV57_CRASH_AT"   # test hook: "<boundary>:<seq>", e.g. "after_commit:3"

_DDL = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS leases(wkey TEXT PRIMARY KEY, owner TEXT NOT NULL,
    epoch INTEGER NOT NULL, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS events(wkey TEXT NOT NULL, seq INTEGER NOT NULL,
    epoch INTEGER NOT NULL, body TEXT NOT NULL, digest TEXT NOT NULL,
    PRIMARY KEY(wkey, seq));
CREATE TABLE IF NOT EXISTS quarantine(wkey TEXT PRIMARY KEY, reason TEXT NOT NULL, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS lifecycle(wkey TEXT PRIMARY KEY, state TEXT NOT NULL,
    version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS lifecycle_log(wkey TEXT NOT NULL, version INTEGER NOT NULL,
    control TEXT NOT NULL, before TEXT NOT NULL, after TEXT NOT NULL, actor TEXT NOT NULL,
    reason TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY(wkey, version));
CREATE TABLE IF NOT EXISTS effects(effect_id TEXT PRIMARY KEY, wkey TEXT NOT NULL,
    activity_id TEXT NOT NULL, effect_class TEXT NOT NULL, request TEXT NOT NULL,
    status TEXT NOT NULL, receipt TEXT);
"""


def _crash_point(boundary: str, seq: int) -> None:
    spec = os.environ.get(CRASH_ENV)
    if spec and spec == f"{boundary}:{seq}":
        os._exit(137)  # abrupt process loss: no cleanup, no rollback handlers


@dataclass(frozen=True)
class Lease:
    wkey: str
    owner: str
    epoch: int
    expires_at: float


class SQLiteBackend:
    def __init__(self, path: str, *, clock: Callable[[], float] = time.time,
                 busy_timeout_ms: int = 5000) -> None:
        self.path = path
        self.clock = clock
        self._conn = sqlite3.connect(path, timeout=busy_timeout_ms / 1000,
                                     isolation_level=None, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
        self._conn.executescript(_DDL)
        row = self._conn.execute("SELECT v FROM meta WHERE k='schema_version'").fetchone()
        if row is None:
            self._conn.execute("INSERT OR IGNORE INTO meta VALUES('schema_version', ?)",
                               (str(BACKEND_SCHEMA_VERSION),))
        elif int(row[0]) > BACKEND_SCHEMA_VERSION:
            raise HistoryCorruption(
                f"backend schema {row[0]} is newer than supported {BACKEND_SCHEMA_VERSION}")

    def close(self) -> None:
        self._conn.close()

    # -- transactions -------------------------------------------------------
    def _txn(self):
        backend = self

        class _T:
            def __enter__(self_inner):
                backend._conn.execute("BEGIN IMMEDIATE")
                return backend._conn

            def __exit__(self_inner, et, ev, tb):
                if et is None:
                    backend._conn.execute("COMMIT")
                else:
                    backend._conn.execute("ROLLBACK")
                return False
        return _T()

    # -- ownership / fencing (MC-40, SG-03) ----------------------------------
    def acquire(self, identity: WorkflowIdentity, owner: str, ttl: float) -> Lease:
        if not owner or ttl <= 0:
            raise ValueError("owner must be non-empty and ttl positive")
        wkey = identity.key()
        now = self.clock()
        with self._txn() as c:
            row = c.execute("SELECT owner, epoch, expires_at FROM leases WHERE wkey=?",
                            (wkey,)).fetchone()
            if row and row[2] > now and row[0] != owner:
                raise OwnershipConflict("workflow is leased by another live owner")
            epoch = (row[1] if row else 0) + 1
            c.execute("INSERT OR REPLACE INTO leases VALUES(?,?,?,?)",
                      (wkey, owner, epoch, now + ttl))
        return Lease(wkey, owner, epoch, now + ttl)

    def renew(self, lease: Lease, ttl: float) -> Lease:
        now = self.clock()
        with self._txn() as c:
            self._check_lease(c, lease, now)
            c.execute("UPDATE leases SET expires_at=? WHERE wkey=?", (now + ttl, lease.wkey))
        return Lease(lease.wkey, lease.owner, lease.epoch, now + ttl)

    def release(self, lease: Lease) -> None:
        with self._txn() as c:
            self._check_lease(c, lease, self.clock())
            c.execute("UPDATE leases SET expires_at=0 WHERE wkey=?", (lease.wkey,))

    def _check_lease(self, c: sqlite3.Connection, lease: Lease, now: float) -> None:
        row = c.execute("SELECT owner, epoch, expires_at FROM leases WHERE wkey=?",
                        (lease.wkey,)).fetchone()
        if not row or row[0] != lease.owner or row[1] != lease.epoch:
            raise StaleOwner(f"lease epoch {lease.epoch} is no longer current")
        if row[2] <= now:
            raise StaleOwner(f"lease epoch {lease.epoch} expired")

    def lease_info(self, identity: WorkflowIdentity) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT owner, epoch, expires_at FROM leases WHERE wkey=?",
                                 (identity.key(),)).fetchone()
        if not row:
            return None
        return {"epoch": row[1], "expires_in": round(row[2] - self.clock(), 3)}

    # -- history (SG-01) -----------------------------------------------------
    def load_events(self, wkey: str) -> list[HistoryEvent]:
        q = self._conn.execute("SELECT reason FROM quarantine WHERE wkey=?", (wkey,)).fetchone()
        if q:
            raise HistoryQuarantined(f"history quarantined: {q[0]}")
        rows = self._conn.execute("SELECT seq, body, digest FROM events WHERE wkey=? ORDER BY seq",
                                  (wkey,)).fetchall()
        try:
            events = []
            for seq, body, digest in rows:
                ev = HistoryEvent.from_dict(json.loads(body))
                if ev.seq != seq or ev.digest != digest:
                    raise HistoryCorruption(f"row/body mismatch at seq {seq}")
                events.append(ev)
            InMemoryHistoryStore(events, max_events=max(len(events), 2))  # full chain check
        except (HistoryCorruption, ValueError, TypeError, RecursionError) as exc:
            self.quarantine(wkey, f"integrity: {type(exc).__name__}")
            raise HistoryQuarantined("history failed integrity validation; quarantined") from exc
        return events

    def quarantine(self, wkey: str, reason: str) -> None:
        with self._txn() as c:
            c.execute("INSERT OR REPLACE INTO quarantine VALUES(?,?,?)", (wkey, reason, self.clock()))

    def release_quarantine(self, wkey: str, *, capabilities: Iterable[str]) -> None:
        if "operator" not in set(capabilities):
            raise Unauthorized("releasing quarantine requires the operator capability")
        with self._txn() as c:
            c.execute("DELETE FROM quarantine WHERE wkey=?", (wkey,))

    def conditional_append(self, lease: Lease, event: HistoryEvent) -> None:
        body = json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"))
        with self._txn() as c:
            self._check_lease(c, lease, self.clock())
            if c.execute("SELECT 1 FROM quarantine WHERE wkey=?", (lease.wkey,)).fetchone():
                raise HistoryQuarantined("history is quarantined")
            tail = c.execute("SELECT MAX(seq) FROM events WHERE wkey=?", (lease.wkey,)).fetchone()[0]
            expected = -1 if tail is None else tail
            if event.seq != expected + 1:
                raise ConcurrentAppend(f"expected seq {expected + 1}, got {event.seq}")
            c.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                      (lease.wkey, event.seq, lease.epoch, body, event.digest))
            _crash_point("before_commit", event.seq)
        _crash_point("after_commit", event.seq)

    # -- backup / restore (MC-61) --------------------------------------------
    def backup(self, dest_path: str) -> dict[str, Any]:
        """Online, consistent backup; returns a manifest with per-workflow tail digests."""
        dest = sqlite3.connect(dest_path)
        try:
            self._conn.backup(dest)
        finally:
            dest.close()
        return {"schema_version": BACKEND_SCHEMA_VERSION, "tails": self._tails(self._conn)}

    @staticmethod
    def _tails(conn: sqlite3.Connection) -> dict[str, list]:
        rows = conn.execute("SELECT wkey, MAX(seq) FROM events GROUP BY wkey").fetchall()
        out = {}
        for wkey, seq in rows:
            d = conn.execute("SELECT digest FROM events WHERE wkey=? AND seq=?", (wkey, seq)).fetchone()[0]
            out[wkey] = [seq, d]
        return out

    @classmethod
    def restore(cls, backup_path: str, dest_path: str, manifest: dict[str, Any],
                **kw: Any) -> "SQLiteBackend":
        """Restore into a NEW path and verify every chain plus the manifest tails.

        Restoring over a live database is refused; leases are reset so that any
        worker from before the backup is fenced out (epochs continue upward).
        """
        if os.path.exists(dest_path):
            raise FileExistsError("restore target exists; restore into a fresh path")
        src = sqlite3.connect(backup_path)
        dst = sqlite3.connect(dest_path)
        try:
            src.backup(dst)
        finally:
            src.close()
            dst.close()
        b = cls(dest_path, **kw)
        if cls._tails(b._conn) != {k: list(v) for k, v in manifest["tails"].items()}:
            b.close()
            raise HistoryCorruption("restored history tails do not match the backup manifest")
        for wkey in manifest["tails"]:
            b.load_events(wkey)                     # full chain validation; quarantines on failure
        b._conn.execute("UPDATE leases SET expires_at=0, epoch=epoch+1000")
        return b

    def event_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    # -- lifecycle (MC-05, SG-08) -------------------------------------------
    def lifecycle_state(self, identity: WorkflowIdentity) -> tuple[lc.State, int]:
        row = self._conn.execute("SELECT state, version FROM lifecycle WHERE wkey=?",
                                 (identity.key(),)).fetchone()
        return (lc.State(row[0]), row[1]) if row else (lc.State.PENDING, 0)

    def control(self, identity: WorkflowIdentity, control: str, *, actor: str,
                capabilities: Iterable[str], reason: str = "",
                expected_version: int | None = None) -> lc.Transition:
        caps = set(capabilities)
        if control in lc.OPERATOR_ONLY and "operator" not in caps:
            raise Unauthorized(f"{control!r} requires the operator capability")
        if "workflow:control" not in caps and "operator" not in caps:
            raise Unauthorized("lifecycle control requires workflow:control")
        wkey = identity.key()
        with self._txn() as c:
            row = c.execute("SELECT state, version FROM lifecycle WHERE wkey=?", (wkey,)).fetchone()
            state, version = (lc.State(row[0]), row[1]) if row else (lc.State.PENDING, 0)
            if expected_version is not None and expected_version != version:
                raise ConcurrentAppend(f"lifecycle version is {version}, not {expected_version}")
            t = lc.transition(state, control, reason=reason)
            if t.changed:
                c.execute("INSERT OR REPLACE INTO lifecycle VALUES(?,?,?)",
                          (wkey, t.after.value, version + 1))
                c.execute("INSERT INTO lifecycle_log VALUES(?,?,?,?,?,?,?,?)",
                          (wkey, version + 1, control, t.before.value, t.after.value,
                           actor, reason[:256], self.clock()))
        return t

    def lifecycle_log(self, identity: WorkflowIdentity) -> list[dict]:
        rows = self._conn.execute(
            "SELECT version, control, before, after, actor, reason FROM lifecycle_log "
            "WHERE wkey=? ORDER BY version", (identity.key(),)).fetchall()
        return [dict(zip(("version", "control", "before", "after", "actor", "reason"), r))
                for r in rows]

    # -- effects (SG-04) -----------------------------------------------------
    def effect_prepare(self, lease: Lease, effect_id: str, activity_id: str,
                       effect_class: str, request: str) -> None:
        with self._txn() as c:
            self._check_lease(c, lease, self.clock())
            row = c.execute("SELECT wkey, activity_id, request FROM effects WHERE effect_id=?",
                            (effect_id,)).fetchone()
            if row is not None and (row[0], row[1], row[2]) != (lease.wkey, activity_id, request):
                # Never silently alias another workflow's (or another request's) effect record.
                raise Unauthorized("effect_id already bound to a different workflow/activity/request")
            if row is None:
                c.execute("INSERT INTO effects VALUES(?,?,?,?,?,'prepared',NULL)",
                          (effect_id, lease.wkey, activity_id, effect_class, request))
            _crash_point("effect_prepare_before_commit", 0)
        _crash_point("effect_prepare_after_commit", 0)

    def effect_mark(self, lease: Lease, effect_id: str, status: str, receipt: str | None) -> None:
        with self._txn() as c:
            self._check_lease(c, lease, self.clock())
            n = c.execute("UPDATE effects SET status=?, receipt=? WHERE effect_id=? AND wkey=?",
                          (status, receipt, effect_id, lease.wkey)).rowcount
            if n != 1:
                raise Unauthorized("effect record does not belong to this lease's workflow")
            _crash_point("effect_mark_before_commit", 0)
        _crash_point("effect_mark_after_commit", 0)

    def effect_get(self, effect_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT effect_id, activity_id, effect_class, request, status, receipt "
            "FROM effects WHERE effect_id=?", (effect_id,)).fetchone()
        return dict(zip(("effect_id", "activity_id", "effect_class", "request", "status",
                         "receipt"), row)) if row else None


class SQLiteHistoryStore(InMemoryHistoryStore):
    """HistoryStore bound to one workflow identity and one fencing lease."""

    def __init__(self, backend: SQLiteBackend, identity: WorkflowIdentity, lease: Lease, *,
                 max_events: int = 100_000) -> None:
        if lease.wkey != identity.key():
            raise StaleOwner("lease does not belong to this workflow identity")
        self.backend = backend
        self.identity = identity
        self.lease = lease
        super().__init__(backend.load_events(identity.key()), max_events=max_events)

    def _persist(self, event: HistoryEvent) -> None:
        self.backend.conditional_append(self.lease, event)

    def renew(self, ttl: float) -> None:
        self.lease = self.backend.renew(self.lease, ttl)
