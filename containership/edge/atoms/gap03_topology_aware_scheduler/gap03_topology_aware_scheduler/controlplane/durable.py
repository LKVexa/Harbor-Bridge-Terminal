"""Crash-safe, hash-chained write-ahead log + snapshot store (shared by MC-004/005/007/013/015/017/022).

Write ordering: validate -> apply to a *copy* of state -> append WAL line ->
flush -> fsync -> swap state.  A record is acknowledged only after fsync.
Recovery: load newest verified snapshot, replay the WAL tail, verify the hash
chain; a torn final line (crash mid-write) is truncated and reported, any
other chain break is an INTEGRITY_FAILURE (fail closed).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time

from . import canonical
from .canonical import readb
from .errors import SchedulerError

GENESIS = "0" * 64


def _fsync_dir(path: str) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write(path: str, data: bytes) -> None:
    tmp = f"{path}.tmp-{os.getpid()}-{threading.get_ident()}"
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_dir(os.path.dirname(path) or ".")


class FileLock:
    """Cross-process exclusive lock using O_EXCL (used for migrations/compaction)."""

    def __init__(self, path: str, *, stale_after: float = 300.0):
        self.path, self.stale_after = path, stale_after

    def __enter__(self):
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.time() - os.path.getmtime(self.path) > self.stale_after:
                raise SchedulerError("CONFLICT", "stale lock present; operator must clear it after verification")
            raise SchedulerError("CONFLICT", "lock held by another process")
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return self

    def __exit__(self, *exc):
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass


class DurableStore:
    """Subclasses define KIND, SCHEMA_VERSION, initial_state() and apply(state, op) -> result."""

    KIND = "base"
    SCHEMA_VERSION = 1
    MIGRATIONS: dict = {}  # {from_version: fn(state) -> state}
    SNAPSHOT_EVERY = 1000

    def __init__(self, directory: str, *, fault=None, clock=time.time, metrics=None):
        self.metrics = metrics
        self.dir = directory
        self.fault = fault  # fault-injection hook: fault(stage) may raise OSError
        self.clock = clock
        self.read_only = False
        self._lock = threading.RLock()
        os.makedirs(os.path.join(directory, "archive"), exist_ok=True)
        self.wal_path = os.path.join(directory, "wal.jsonl")
        self.meta_path = os.path.join(directory, "meta.json")
        self.recovery_report: dict = {}
        self._recover()

    # ---- hooks -----------------------------------------------------------------
    def initial_state(self) -> dict:
        return {}

    def apply(self, state: dict, op: dict):  # pragma: no cover - abstract
        raise NotImplementedError

    def check_invariants(self, state: dict) -> None:
        """Storage-level constraints; raise SchedulerError('INTEGRITY_FAILURE') on violation."""

    # ---- internals ---------------------------------------------------------------
    def _hash(self, prev: str, seq: int, ts: int, op: dict) -> str:
        return hashlib.sha256(prev.encode() + canonical.dumps({"seq": seq, "ts": ts, "op": op})).hexdigest()

    def _snapshots(self):
        names = [n for n in os.listdir(self.dir) if n.startswith("snapshot-") and n.endswith(".json")]
        return sorted(names, key=lambda n: int(n[9:-5]), reverse=True)

    def _recover(self):
        with self._lock:
            if os.path.exists(self.meta_path):
                meta = canonical.loads(readb(self.meta_path))
                if meta.get("kind") != self.KIND:
                    raise SchedulerError("INTEGRITY_FAILURE", "store kind mismatch")
                if meta.get("schema_version") > self.SCHEMA_VERSION:
                    raise SchedulerError("UNSUPPORTED_VERSION", "store written by a newer schema; refuse to downgrade")
                self.schema_on_disk = meta["schema_version"]
            else:
                atomic_write(self.meta_path, canonical.dumps({"kind": self.KIND, "schema_version": self.SCHEMA_VERSION}))
                self.schema_on_disk = self.SCHEMA_VERSION
            state, seq, head = self.initial_state(), 0, GENESIS
            report = {"snapshot": None, "replayed": 0, "torn_tail_repaired": False}
            for name in self._snapshots():
                try:
                    snap = canonical.loads(readb(os.path.join(self.dir, name)), max_bytes=1 << 28)
                    if snap["digest"] != canonical.digest(snap["state"]):
                        raise ValueError("digest")
                    state, seq, head = snap["state"], snap["seq"], snap["head"]
                    report["snapshot"] = name
                    break
                except Exception:
                    report.setdefault("bad_snapshots", []).append(name)
            if self.schema_on_disk < self.SCHEMA_VERSION:
                self.pending_migration = True
            else:
                self.pending_migration = False
            if os.path.exists(self.wal_path):
                with open(self.wal_path, "rb") as fh:
                    raw = fh.read()
                lines = raw.split(b"\n")
                good_bytes = 0
                for idx, line in enumerate(lines):
                    if not line:
                        good_bytes += 1 if idx < len(lines) - 1 else 0
                        continue
                    last = idx == len(lines) - 1
                    try:
                        rec = canonical.loads(line, max_bytes=1 << 24)
                    except canonical.CanonicalError:
                        if last:
                            report["torn_tail_repaired"] = True
                            break
                        raise SchedulerError("INTEGRITY_FAILURE", f"corrupt WAL record at line {idx + 1}") from None
                    if rec["seq"] <= seq:
                        good_bytes += len(line) + 1
                        continue  # already covered by snapshot
                    if rec["seq"] != seq + 1 or rec["prev"] != head or rec["hash"] != self._hash(head, rec["seq"], rec["ts"], rec["op"]):
                        raise SchedulerError("INTEGRITY_FAILURE", f"WAL chain break at seq {rec.get('seq')}")
                    state = copy.deepcopy(state)
                    self.apply(state, rec["op"])
                    seq, head = rec["seq"], rec["hash"]
                    report["replayed"] += 1
                    good_bytes += len(line) + 1
                if report["torn_tail_repaired"]:
                    with open(self.wal_path, "r+b") as fh:
                        fh.truncate(good_bytes)
                        fh.flush()
                        os.fsync(fh.fileno())
            self.check_invariants(state)
            self.state, self.seq, self.head = state, seq, head
            self.recovery_report = report

    def submit(self, op: dict):
        """Validate+apply atomically, persist, then acknowledge. Returns apply() result."""
        with self._lock:
            if self.read_only:
                raise SchedulerError("DEPENDENCY_UNAVAILABLE", f"{self.KIND} store is read-only")
            if self.pending_migration:
                raise SchedulerError("DEPENDENCY_UNAVAILABLE", "schema migration pending")
            canonical.dumps(op)
            candidate = copy.deepcopy(self.state)
            result = self.apply(candidate, op)
            self.check_invariants(candidate)
            seq, ts = self.seq + 1, int(self.clock())
            h = self._hash(self.head, seq, ts, op)
            line = canonical.dumps({"seq": seq, "ts": ts, "prev": self.head, "op": op, "hash": h}) + b"\n"
            t_write = time.perf_counter()
            try:
                if self.fault:
                    self.fault("before_write")
                with open(self.wal_path, "ab") as fh:
                    if self.fault:
                        self.fault("mid_write")
                    fh.write(line)
                    fh.flush()
                    if self.fault:
                        self.fault("before_fsync")
                    os.fsync(fh.fileno())
            except OSError as exc:
                self.read_only = True  # unknown on-disk state -> stop accepting writes until recovery
                raise SchedulerError("DEPENDENCY_UNAVAILABLE", f"durable write failed: {exc.__class__.__name__}") from None
            if self.metrics:
                self.metrics.observe("gap03_store_write_latency_ms", (time.perf_counter() - t_write) * 1000, store=self.KIND)
            self.state, self.seq, self.head = candidate, seq, h
            if self.seq % self.SNAPSHOT_EVERY == 0:
                self.snapshot()
            return result

    def view(self) -> dict:
        with self._lock:
            return copy.deepcopy(self.state)

    def snapshot(self) -> str:
        """Write a verified snapshot and archive (not delete) the covered WAL segment."""
        with self._lock:
            name = f"snapshot-{self.seq}.json"
            atomic_write(os.path.join(self.dir, name), canonical.dumps(
                {"kind": self.KIND, "schema_version": self.SCHEMA_VERSION, "seq": self.seq, "head": self.head,
                 "state": self.state, "digest": canonical.digest(self.state)}))
            if os.path.exists(self.wal_path) and os.path.getsize(self.wal_path):
                os.replace(self.wal_path, os.path.join(self.dir, "archive", f"wal-upto-{self.seq}.jsonl"))
                _fsync_dir(self.dir)
            return name

    def verify_history(self) -> dict:
        """Re-verify the full forensic chain across archived segments + live WAL."""
        head, seq, count = GENESIS, 0, 0
        segs = sorted(os.listdir(os.path.join(self.dir, "archive")), key=lambda n: int(n.split("-")[-1].split(".")[0]))
        paths = [os.path.join(self.dir, "archive", s) for s in segs] + ([self.wal_path] if os.path.exists(self.wal_path) else [])
        for path in paths:
            for line in readb(path).split(b"\n"):
                if not line:
                    continue
                rec = canonical.loads(line, max_bytes=1 << 24)
                if rec["seq"] != seq + 1 or rec["prev"] != head or rec["hash"] != self._hash(head, rec["seq"], rec["ts"], rec["op"]):
                    return {"ok": False, "break_at": rec.get("seq"), "verified": count}
                head, seq, count = rec["hash"], rec["seq"], count + 1
        return {"ok": head == self.head and seq == self.seq, "verified": count, "head": head}

    # ---- migrations -------------------------------------------------------------------
    def migrate(self, *, dry_run: bool = True) -> dict:
        with FileLock(os.path.join(self.dir, "migration.lock")):
            with self._lock:
                version, state, steps = self.schema_on_disk, copy.deepcopy(self.state), []
                while version < self.SCHEMA_VERSION:
                    fn = self.MIGRATIONS.get(version)
                    if fn is None:
                        raise SchedulerError("UNSUPPORTED_VERSION", f"no migration from v{version}")
                    state = fn(state)
                    steps.append(f"v{version}->v{version + 1}")
                    version += 1
                self.check_invariants(state)
                plan = {"from": self.schema_on_disk, "to": self.SCHEMA_VERSION, "steps": steps, "dry_run": dry_run,
                        "state_digest_before": canonical.digest(self.state), "state_digest_after": canonical.digest(state)}
                if dry_run:
                    return plan
                # pre-migration snapshot is the rollback point
                plan["rollback_snapshot"] = self.snapshot()
                self.state = state
                atomic_write(self.meta_path, canonical.dumps({"kind": self.KIND, "schema_version": self.SCHEMA_VERSION}))
                self.schema_on_disk, self.pending_migration = self.SCHEMA_VERSION, False
                self.snapshot()
                return plan

    # ---- export/import -----------------------------------------------------------------
    def export(self) -> dict:
        with self._lock:
            return {"kind": self.KIND, "schema_version": self.SCHEMA_VERSION, "seq": self.seq, "head": self.head,
                    "state": copy.deepcopy(self.state), "digest": canonical.digest(self.state)}
