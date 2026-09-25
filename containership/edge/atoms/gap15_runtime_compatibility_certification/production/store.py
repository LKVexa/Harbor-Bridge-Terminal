"""Durable compatibility-matrix store, append-only ledger and audit stream.

Components 01 (durable store), 02 (evidence ledger), 11 (concurrency),
12 (audit stream), 15 (recovery), 47 (backup/restore/migration).

Engine: SQLite (stdlib) in WAL mode with ``synchronous=FULL`` and
``BEGIN IMMEDIATE`` write transactions — serializable single-writer,
crash-consistent, one file per store. See ``docs/ADR.md`` ADR-001 for the
consistency, RPO/RTO and replication decision (multi-node replication is an
external blocker).

Invariants enforced *by the database*, not only by this module:
* ``ledger`` and ``audit`` reject UPDATE and DELETE (triggers).
* every ledger/audit row carries ``prev_hash`` / ``entry_hash`` (SHA-256 chain).
* the partition is the leading column of every key and index.
* compare-and-swap on ``meta.matrix_revision`` inside the write transaction.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from .canonical import canonical_bytes, parse, sha256_hex
from .state import CertKey, CertPolicy, State, StateError, apply, certify, key_of, replay

SCHEMA_VERSION = 3
GENESIS = "0" * 64

MIGRATIONS: list = [
    (1, "base tables", """
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE ledger (
  seq INTEGER PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL,
  partition TEXT NOT NULL,
  body BLOB NOT NULL,
  prev_hash TEXT NOT NULL,
  entry_hash TEXT NOT NULL UNIQUE,
  recorded_at INTEGER NOT NULL
);
CREATE TRIGGER ledger_no_update BEFORE UPDATE ON ledger BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER ledger_no_delete BEFORE DELETE ON ledger BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TABLE audit (
  seq INTEGER PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  body BLOB NOT NULL,
  prev_hash TEXT NOT NULL,
  entry_hash TEXT NOT NULL UNIQUE
);
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
"""),
    (2, "materialized matrix + lookup columns", """
CREATE TABLE matrix (
  partition TEXT NOT NULL, artifact_digest TEXT NOT NULL, runtime TEXT NOT NULL, profile_id TEXT NOT NULL,
  result TEXT NOT NULL, observed_at INTEGER NOT NULL, evidence_id TEXT NOT NULL,
  matrix_revision INTEGER NOT NULL, created_seq INTEGER NOT NULL, updated_seq INTEGER NOT NULL,
  tombstone INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (partition, artifact_digest, runtime, profile_id)
) WITHOUT ROWID;
ALTER TABLE ledger ADD COLUMN artifact_digest TEXT;
ALTER TABLE ledger ADD COLUMN runtime TEXT;
ALTER TABLE ledger ADD COLUMN profile_id TEXT;
ALTER TABLE ledger ADD COLUMN signer TEXT;
ALTER TABLE ledger ADD COLUMN result TEXT;
ALTER TABLE ledger ADD COLUMN observed_at INTEGER;
ALTER TABLE ledger ADD COLUMN idem_key TEXT;
CREATE INDEX ledger_by_key ON ledger(partition, artifact_digest, runtime, profile_id, seq);
CREATE INDEX ledger_by_signer ON ledger(partition, signer, seq);
CREATE INDEX ledger_by_result_time ON ledger(partition, result, observed_at);
CREATE UNIQUE INDEX ledger_idem ON ledger(partition, idem_key) WHERE idem_key IS NOT NULL;
"""),
    (3, "checkpoints", """
CREATE TABLE checkpoints (
  seq INTEGER PRIMARY KEY, ledger_seq INTEGER NOT NULL, head_hash TEXT NOT NULL,
  audit_seq INTEGER NOT NULL, audit_head TEXT NOT NULL, body BLOB NOT NULL
);
CREATE TRIGGER checkpoints_no_update BEFORE UPDATE ON checkpoints BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER checkpoints_no_delete BEFORE DELETE ON checkpoints BEGIN SELECT RAISE(ABORT, 'append-only'); END;
"""),
]


class StoreError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class Conflict(StoreError):
    def __init__(self, expected: int, current: int) -> None:
        super().__init__("E_REVISION_CONFLICT", f"expected revision {expected}, current {current}")
        self.expected = expected
        self.current = current


@dataclass(frozen=True)
class CommitResult:
    seqs: tuple
    revision: int
    head_hash: str
    idempotent: bool = False


def _chain(prev: str, body: bytes) -> str:
    return hashlib.sha256(prev.encode() + b"|" + body).hexdigest()


class Store:
    """One store per partition set on one node. Thread-safe via an internal lock."""

    def __init__(self, path: str, *, fault_hook: Optional[Callable[[str], None]] = None,
                 read_only: bool = False) -> None:
        self.path = path
        self.fault_hook = fault_hook or (lambda stage: None)
        self._lock = threading.RLock()
        uri = f"file:{path}?mode=ro" if read_only else f"file:{path}"
        self.db = sqlite3.connect(uri, uri=True, isolation_level=None, check_same_thread=False, timeout=5.0)
        self.db.execute("PRAGMA foreign_keys=ON")
        if not read_only:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.migrate()
        self.state = State()
        self.recover()

    # ------------------------------------------------------------------ schema
    def schema_version(self) -> int:
        try:
            row = self.db.execute("SELECT v FROM meta WHERE k='schema_version'").fetchone()
        except sqlite3.OperationalError:
            return 0
        return int(row[0]) if row else 0

    def migrate(self, *, target: int = SCHEMA_VERSION, dry_run: bool = False) -> list:
        """Forward-only migrations; refuses a database newer than this code (MC-01-06)."""
        with self._lock:
            current = self.schema_version()
            if current > SCHEMA_VERSION:
                raise StoreError("E_SCHEMA_TOO_NEW", f"database schema {current} > supported {SCHEMA_VERSION}; downgrade refused")
            pending = [m for m in MIGRATIONS if current < m[0] <= target]
            if dry_run:
                return [(m[0], m[1]) for m in pending]
            for mig_id, name, sql in pending:
                self.db.execute("BEGIN IMMEDIATE")
                try:
                    self.fault_hook(f"migration:{mig_id}")
                    for stmt in _split_sql(sql):
                        self.db.execute(stmt)
                    if mig_id == 1:
                        self.db.execute("INSERT INTO meta VALUES('matrix_revision','0')")
                        self.db.execute("INSERT INTO meta VALUES('schema_version','0')")
                    self.db.execute("UPDATE meta SET v=? WHERE k='schema_version'", (str(mig_id),))
                    self.db.execute("COMMIT")
                except BaseException:
                    self.db.execute("ROLLBACK")
                    raise
            return [(m[0], m[1]) for m in pending]

    # ---------------------------------------------------------------- recovery
    def recover(self) -> dict:
        """Verify both chains, replay the ledger, reconcile the materialised matrix (MC-15-03)."""
        with self._lock:
            events = self.events()
            self.verify_chain("ledger")
            self.verify_chain("audit")
            state = replay(events)
            rev = int(self.db.execute("SELECT v FROM meta WHERE k='matrix_revision'").fetchone()[0])
            if rev != state.revision:
                raise StoreError("E_RECOVERY_REVISION", f"meta revision {rev} != replayed {state.revision}")
            mismatches = self._reconcile_matrix(state)
            self.state = state
            return {"events": len(events), "revision": state.revision, "matrix_repairs": mismatches}

    def _reconcile_matrix(self, state: State) -> int:
        rows = {(r[0], r[1], r[2], r[3]): r[6] for r in self.db.execute("SELECT * FROM matrix")}
        want = {(k.partition, k.artifact_digest, k.runtime, k.profile_id): e["evidence_id"] for k, e in state.evidence.items()}
        if rows == want:
            return 0
        # materialisation is derived data: rebuild it from the ledger in one transaction
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("DELETE FROM matrix")
            for k, e in state.evidence.items():
                self._upsert_matrix(k, e, state.revision)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return len(set(rows.items()) ^ set(want.items()))

    def verify_chain(self, table: str) -> str:
        if table not in ("ledger", "audit"):
            raise ValueError(table)
        prev = GENESIS
        expected_seq = 1
        for seq, body, prev_hash, entry_hash in self.db.execute(
                f"SELECT seq, body, prev_hash, entry_hash FROM {table} ORDER BY seq"):
            if seq != expected_seq:
                raise StoreError("E_CHAIN_GAP", f"{table} sequence gap at {expected_seq} (found {seq})")
            if not isinstance(body, bytes):
                # a storage-class change (BLOB -> TEXT) is itself tampering; never crash on it
                raise StoreError("E_CHAIN_BROKEN", f"{table} row {seq} body is not a BLOB")
            if prev_hash != prev or _chain(prev, body) != entry_hash:
                raise StoreError("E_CHAIN_BROKEN", f"{table} hash chain broken at seq {seq}")
            prev = entry_hash
            expected_seq += 1
        return prev

    # ------------------------------------------------------------------- reads
    def events(self, *, partition: Optional[str] = None, upto_seq: Optional[int] = None) -> list:
        sql = "SELECT seq, body FROM ledger"
        args: list = []
        clauses = []
        if partition is not None:
            clauses.append("(partition=? OR partition='*')")
            args.append(partition)
        if upto_seq is not None:
            clauses.append("seq<=?")
            args.append(upto_seq)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        out = []
        for seq, body in self.db.execute(sql + " ORDER BY seq", args):
            ev = parse(body, max_bytes=1 << 20)
            ev["seq"] = seq
            out.append(ev)
        return out

    @property
    def revision(self) -> int:
        return self.state.revision

    def head(self, table: str = "ledger") -> tuple:
        row = self.db.execute(f"SELECT seq, entry_hash FROM {table} ORDER BY seq DESC LIMIT 1").fetchone()
        return row if row else (0, GENESIS)

    def lookup(self, partition: str, *, artifact_digest: Optional[str] = None, runtime: Optional[str] = None,
               profile_id: Optional[str] = None, signer: Optional[str] = None, result: Optional[str] = None,
               since: Optional[int] = None, until: Optional[int] = None, limit: int = 100, after_seq: int = 0) -> list:
        """Historical lookup; partition is mandatory and leads every index (MC-01-04, MC-01-09)."""
        if not isinstance(partition, str) or not partition:
            raise StoreError("E_PARTITION_REQUIRED", "every query is partition-scoped")
        limit = max(1, min(int(limit), 1000))
        sql = "SELECT seq, body FROM ledger WHERE partition=? AND seq>?"
        args: list = [partition, after_seq]
        for col, val in (("artifact_digest", artifact_digest), ("runtime", runtime), ("profile_id", profile_id),
                         ("signer", signer), ("result", result)):
            if val is not None:
                sql += f" AND {col}=?"
                args.append(val)
        if since is not None:
            sql += " AND observed_at>=?"
            args.append(since)
        if until is not None:
            sql += " AND observed_at<=?"
            args.append(until)
        sql += " ORDER BY seq LIMIT ?"
        args.append(limit)
        return [{**parse(b, max_bytes=1 << 20), "seq": s} for s, b in self.db.execute(sql, args)]

    def query_plan(self, sql: str, args: tuple = ()) -> list:
        return [r[-1] for r in self.db.execute("EXPLAIN QUERY PLAN " + sql, args)]

    def find_idempotent(self, partition: str, idem_key: str) -> Optional[dict]:
        row = self.db.execute("SELECT seq, body FROM ledger WHERE partition=? AND idem_key=?", (partition, idem_key)).fetchone()
        return {**parse(row[1], max_bytes=1 << 20), "seq": row[0]} if row else None

    def certify(self, key: CertKey, now: int, policy: CertPolicy = CertPolicy(), **kw) -> dict:
        with self._lock:
            return certify(self.state, key, now, policy, **kw)

    def reconstruct(self, key: CertKey, now: int, upto_seq: int, policy: CertPolicy = CertPolicy(), **kw) -> dict:
        """Deterministically reproduce the verdict as of ledger position ``upto_seq`` (MC-02-04)."""
        return certify(replay(self.events(upto_seq=upto_seq)), key, now, policy, **kw)

    # ------------------------------------------------------------------ writes
    def commit(self, events: list, *, audit: list, expected_revision: Optional[int] = None,
               recorded_at: int = 0) -> CommitResult:
        """Atomically append ledger events + materialise + advance revision + audit (MC-01-05, MC-10-05).

        Either every event, the matrix update, the revision and every audit
        event commit together, or nothing does.
        """
        if not events and not audit:
            raise StoreError("E_EMPTY_COMMIT", "nothing to commit")
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                current = int(self.db.execute("SELECT v FROM meta WHERE k='matrix_revision'").fetchone()[0])
                if current != self.state.revision:
                    # another process committed: refresh our view before judging CAS
                    self.db.execute("ROLLBACK")
                    self.recover()
                    self.db.execute("BEGIN IMMEDIATE")
                    current = int(self.db.execute("SELECT v FROM meta WHERE k='matrix_revision'").fetchone()[0])
                if expected_revision is not None and expected_revision != current:
                    raise Conflict(expected_revision, current)
                # validate on a scratch copy first so a bad event leaves no trace
                scratch = copy.deepcopy(self.state)
                seq, head = self.head("ledger")
                seqs = []
                bodies = []
                for ev in events:
                    seq += 1
                    ev = {k: v for k, v in ev.items() if k != "seq"}
                    apply(scratch, {**ev, "seq": seq})
                    body = canonical_bytes(ev)
                    bodies.append((seq, ev, body))
                self.fault_hook("before_ledger_append")
                for seq_i, ev, body in bodies:
                    h = _chain(head, body)
                    self.db.execute(
                        "INSERT INTO ledger(seq,event_id,event_type,partition,body,prev_hash,entry_hash,recorded_at,"
                        "artifact_digest,runtime,profile_id,signer,result,observed_at,idem_key) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (seq_i, ev["event_id"], ev["event_type"], ev["partition"], body, head, h, recorded_at,
                         ev.get("artifact_digest"), ev.get("runtime"), ev.get("profile_id"), ev.get("signer_key_id"),
                         ev.get("result"), ev.get("observed_at"), ev.get("idem_key")))
                    head = h
                    seqs.append(seq_i)
                self.fault_hook("after_ledger_append")
                for seq_i, ev, _ in bodies:
                    if ev["event_type"] == "evidence":
                        self._upsert_matrix(key_of(ev), {**ev, "seq": seq_i}, scratch.revision)
                self.fault_hook("before_revision_update")
                self.db.execute("UPDATE meta SET v=? WHERE k='matrix_revision'", (str(scratch.revision),))
                self.fault_hook("before_audit")
                for a in audit:
                    self._append_audit(a)
                self.fault_hook("before_commit")
                self.db.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                self.db.execute("ROLLBACK")
                raise StoreError("E_INTEGRITY", str(exc)) from exc
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            self.state = scratch
            self.fault_hook("after_commit")
            return CommitResult(tuple(seqs), scratch.revision, head)

    def commit_with_retry(self, build_events: Callable[[int], tuple], *, max_attempts: int = 5, base_delay_s: float = 0.005,
                          max_delay_s: float = 0.2, sleep: Callable[[float], None] = None, rand: Callable[[], float] = None) -> CommitResult:
        """Optimistic retry with bounded exponential backoff + full jitter and a hard budget (MC-11-05).

        ``build_events(observed_revision)`` must be pure/idempotent: it is re-run against the
        fresh revision on every attempt, so a retried write re-decides instead of replaying stale intent.
        """
        import random as _random
        import time as _time
        sleep = sleep or _time.sleep
        rand = rand or _random.random
        last: Optional[Conflict] = None
        for attempt in range(max_attempts):
            observed = self.revision
            events, audit = build_events(observed)
            try:
                return self.commit(events, audit=audit, expected_revision=observed)
            except Conflict as exc:
                last = exc
                sleep(min(max_delay_s, base_delay_s * (2 ** attempt)) * rand())
        raise StoreError("E_RETRY_BUDGET_EXHAUSTED", f"{max_attempts} optimistic attempts failed; last {last}")

    def audit_only(self, audit: list) -> None:
        """Audit events that do not change certification state (rejections, reads, admin)."""
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                for a in audit:
                    self._append_audit(a)
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def _append_audit(self, event: dict) -> None:
        seq, head = self.head("audit")
        body = canonical_bytes(event)
        self.db.execute("INSERT INTO audit(seq,event_id,body,prev_hash,entry_hash) VALUES(?,?,?,?,?)",
                        (seq + 1, event["event_id"], body, head, _chain(head, body)))

    def audit_events(self) -> list:
        return [{**parse(b, max_bytes=1 << 20), "seq": s} for s, b in self.db.execute("SELECT seq, body FROM audit ORDER BY seq")]

    def _upsert_matrix(self, k: CertKey, ev: dict, revision: int) -> None:
        self.db.execute(
            "INSERT INTO matrix VALUES(?,?,?,?,?,?,?,?,?,?,0) ON CONFLICT(partition,artifact_digest,runtime,profile_id) "
            "DO UPDATE SET result=excluded.result, observed_at=excluded.observed_at, evidence_id=excluded.evidence_id, "
            "matrix_revision=excluded.matrix_revision, updated_seq=excluded.updated_seq",
            (k.partition, k.artifact_digest, k.runtime, k.profile_id, ev["result"], ev["observed_at"],
             ev["evidence_id"], revision, ev["seq"], ev["seq"]))

    def matrix_view(self, partition: str) -> dict:
        rows = self.db.execute(
            "SELECT artifact_digest, runtime, profile_id, result, observed_at, evidence_id FROM matrix "
            "WHERE partition=? AND tombstone=0 ORDER BY artifact_digest, runtime, profile_id", (partition,)).fetchall()
        return {"schema": "PK_COMPATIBILITY_MATRIX/1", "partition": partition, "revision": self.state.revision,
                "results": [{"artifact_digest": a, "runtime": r, "profile_id": p, "compatible": res == "compatible",
                             "tested_at": t, "evidence_id": e} for a, r, p, res, t, e in rows]}

    # -------------------------------------------------------------- checkpoints
    def checkpoint(self, signer: Callable[[bytes], dict]) -> dict:
        """Signed checkpoint over both chain heads (MC-02-03, MC-02-07, MC-12-07)."""
        with self._lock:
            lseq, lhead = self.head("ledger")
            aseq, ahead = self.head("audit")
            body = {"schema": "GAP15_CHECKPOINT/1", "ledger_seq": lseq, "ledger_head": lhead,
                    "audit_seq": aseq, "audit_head": ahead, "revision": self.state.revision}
            signed = {"checkpoint": body, "signature": signer(canonical_bytes(body))}
            nseq = (self.db.execute("SELECT COALESCE(MAX(seq),0) FROM checkpoints").fetchone()[0]) + 1
            self.db.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?,?)", (nseq, lseq, lhead, aseq, ahead, canonical_bytes(signed)))
            return signed

    def export_ledger(self, path: str) -> dict:
        """Portable JSONL export for offline verification / legal retention (MC-02-07)."""
        n = 0
        with open(path, "wb") as fh:
            for seq, body, prev_hash, entry_hash in self.db.execute(
                    "SELECT seq, body, prev_hash, entry_hash FROM ledger ORDER BY seq"):
                fh.write(canonical_bytes({"seq": seq, "body": body.decode(), "prev_hash": prev_hash, "entry_hash": entry_hash}) + b"\n")
                n += 1
        return {"entries": n, "head": self.head("ledger")[1], "sha256": sha256_hex(open(path, "rb").read())}

    # ------------------------------------------------------------ backup/restore
    def backup(self, dest: str, *, sign: Callable[[bytes], dict], created_at: int, service_version: str) -> dict:
        """Online consistent backup + signed manifest (MC-01-08, MC-47-01, MC-47-02)."""
        with self._lock:
            target = sqlite3.connect(dest)
            try:
                self.db.backup(target)
            finally:
                target.close()
            data = open(dest, "rb").read()
            manifest = {"schema": "GAP15_BACKUP/1", "service_version": service_version,
                        "schema_version": self.schema_version(), "ledger_head": list(self.head("ledger")),
                        "audit_head": list(self.head("audit")), "revision": self.state.revision,
                        "file": os.path.basename(dest), "sha256": sha256_hex(data), "bytes": len(data),
                        "created_at": created_at, "encryption": "none:BLOCKED-requires-KMS"}
            signed = {"manifest": manifest, "signature": sign(canonical_bytes(manifest))}
            with open(dest + ".manifest.json", "wb") as fh:
                fh.write(canonical_bytes(signed))
            return signed


def restore_to_staging(backup_path: str, staging_path: str, *, verify_sig: Callable[[bytes, dict], bool],
                       expected_partitions: Optional[set] = None) -> dict:
    """Verify and restore a backup into an isolated staging path (MC-47-04, MC-15-05, MC-25-06)."""
    raw_manifest = open(backup_path + ".manifest.json", "rb").read()
    signed = parse(raw_manifest, max_bytes=1 << 16)
    manifest = signed["manifest"]
    if not verify_sig(canonical_bytes(manifest), signed["signature"]):
        raise StoreError("E_BACKUP_SIGNATURE", "backup manifest signature invalid")
    data = open(backup_path, "rb").read()
    if sha256_hex(data) != manifest["sha256"] or len(data) != manifest["bytes"]:
        raise StoreError("E_BACKUP_CORRUPT", "backup bytes do not match manifest")
    if manifest["schema_version"] > SCHEMA_VERSION:
        raise StoreError("E_SCHEMA_TOO_NEW", "backup was taken by a newer release; downgrade refused")
    if os.path.exists(staging_path):
        raise StoreError("E_STAGING_EXISTS", "restore never overwrites an existing store")
    with open(staging_path, "wb") as fh:
        fh.write(data)
    store = Store(staging_path)  # migrates forward if older, verifies chains, replays
    if list(store.head("ledger")) != manifest["ledger_head"] or list(store.head("audit")) != manifest["audit_head"]:
        raise StoreError("E_RESTORE_HEAD", "restored chain heads differ from manifest")
    partitions = {r[0] for r in store.db.execute("SELECT DISTINCT partition FROM ledger")} - {"*"}
    if expected_partitions is not None and not partitions <= expected_partitions:
        raise StoreError("E_RESTORE_PARTITION", f"backup contains foreign partitions {sorted(partitions - expected_partitions)}")
    # post-restore invariant: materialised verdict == replayed verdict for every key
    replayed = replay(store.events())
    for k in replayed.evidence:
        if certify(replayed, k, 0)["verdict"] != store.certify(k, 0)["verdict"]:
            raise StoreError("E_RESTORE_VERDICT", f"verdict drift for {k}")
    return {"store": store, "manifest": manifest, "partitions": sorted(partitions), "keys_verified": len(replayed.evidence)}


def _split_sql(sql: str) -> list:
    out, buf = [], []
    depth = 0
    for line in sql.strip().splitlines():
        buf.append(line)
        depth += line.count("BEGIN") - line.count("END;")
        if line.rstrip().endswith(";") and depth <= 0:
            out.append("\n".join(buf))
            buf = []
            depth = 0
    if buf:
        out.append("\n".join(buf))
    return [s for s in out if s.strip()]
