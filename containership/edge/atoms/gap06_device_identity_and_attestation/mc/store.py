"""MC-07 / MC-16 / MC-27: durable, crash-consistent security state.

A write-ahead log of JSON records, each line ``<sha256(prev_hash+body)> <body>``
fsync'd before the call returns; snapshots are written to a temp file, fsync'd
and atomically renamed.  On open, the log is replayed and verified; a torn final
line (crash mid-write) is truncated, any other corruption raises E_STATE_CORRUPT.
Transactions: ``with store.transaction() as tx: tx.put(...)`` commits as one
log record or not at all.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import threading
from pathlib import Path

from .errors import fail

GENESIS = "0" * 64
MAX_RECORD = 1 << 20


def _h(prev: str, body: str) -> str:
    return hashlib.sha256((prev + body).encode()).hexdigest()


class DurableStore:
    """Key/value tables: tables[name][key] = json value.  Monotonic generation."""

    def __init__(self, directory: str | os.PathLike, *, fsync: bool = True):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "wal.log"
        self.snap_path = self.dir / "snapshot.json"
        self.fsync = fsync
        self.tables: dict = {}
        self.generation = 0
        self.head = GENESIS
        self._lock = threading.RLock()
        self._recover()

    # -- recovery ---------------------------------------------------------
    def _recover(self):
        if self.snap_path.exists():
            snap = json.loads(self.snap_path.read_text("utf-8"))
            body = json.dumps(snap["tables"], sort_keys=True)
            if hashlib.sha256(body.encode()).hexdigest() != snap["digest"]:
                raise fail("E_STATE_CORRUPT", "snapshot digest mismatch")
            self.tables, self.generation, self.head = snap["tables"], snap["generation"], snap["head"]
        if not self.log_path.exists():
            return
        data = self.log_path.read_bytes()
        lines = data.split(b"\n")
        good = 0
        for i, raw in enumerate(lines):
            if not raw:
                good += 1
                continue
            last = i == len(lines) - 1  # no trailing newline => torn write
            try:
                digest, body = raw.decode().split(" ", 1)
                rec = json.loads(body)
            except Exception:
                if last:
                    break
                raise fail("E_STATE_CORRUPT", f"unparseable WAL line {i}")
            if rec["gen"] <= self.generation:
                good += len(raw) + 1
                continue
            if _h(self.head, body) != digest or rec["gen"] != self.generation + 1:
                raise fail("E_STATE_CORRUPT", f"WAL chain broken at line {i}")
            self._apply(rec["ops"])
            self.generation, self.head = rec["gen"], digest
            good += len(raw) + 1
        if good < len(data):  # truncate torn tail
            with open(self.log_path, "r+b") as f:
                f.truncate(good)

    def _apply(self, ops):
        for op, table, key, value in ops:
            t = self.tables.setdefault(table, {})
            if op == "put":
                t[key] = value
            elif op == "del":
                t.pop(key, None)

    # -- API --------------------------------------------------------------
    def get(self, table, key, default=None):
        with self._lock:
            return copy.deepcopy(self.tables.get(table, {}).get(key, default))

    def items(self, table):
        with self._lock:
            return copy.deepcopy(self.tables.get(table, {}))

    @contextlib.contextmanager
    def transaction(self, *, expect_generation: int | None = None):
        with self._lock:
            if expect_generation is not None and expect_generation != self.generation:
                raise fail("E_CONFLICT", "optimistic concurrency conflict")
            tx = _Tx()
            yield tx
            if tx.ops:
                self._commit(tx.ops)

    def put(self, table, key, value):
        with self.transaction() as tx:
            tx.put(table, key, value)

    def _commit(self, ops):
        rec = {"gen": self.generation + 1, "ops": ops}
        body = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        if len(body) > MAX_RECORD:
            raise fail("E_OVERLOADED", "transaction too large")
        digest = _h(self.head, body)
        with open(self.log_path, "ab") as f:
            f.write(f"{digest} {body}\n".encode())
            f.flush()
            if self.fsync:
                os.fsync(f.fileno())
        self._apply(ops)
        self.generation, self.head = rec["gen"], digest

    def snapshot(self):
        with self._lock:
            body = json.dumps(self.tables, sort_keys=True)
            snap = {"tables": self.tables, "generation": self.generation, "head": self.head,
                    "digest": hashlib.sha256(body.encode()).hexdigest()}
            tmp = self.snap_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snap, f, sort_keys=True)
                f.flush()
                if self.fsync:
                    os.fsync(f.fileno())
            os.replace(tmp, self.snap_path)
            return self.generation

    def backup(self, dest: str | os.PathLike) -> str:
        """MC-27 backup: snapshot + copy; returns sha256 of the backup file."""
        self.snapshot()
        dest = Path(dest)
        dest.write_bytes(self.snap_path.read_bytes())
        return hashlib.sha256(dest.read_bytes()).hexdigest()

    @classmethod
    def restore(cls, backup_file, directory, *, min_generation: int = 0) -> "DurableStore":
        """Restore refuses a backup older than ``min_generation`` (rollback would
        reopen replay windows / resurrect revoked identities)."""
        snap = json.loads(Path(backup_file).read_text("utf-8"))
        if snap["generation"] < min_generation:
            raise fail("E_POLICY_ROLLBACK", "backup older than the monotonic security floor")
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        (d / "snapshot.json").write_text(json.dumps(snap, sort_keys=True), "utf-8")
        return cls(d)


class _Tx:
    def __init__(self):
        self.ops = []

    def put(self, table, key, value):
        json.dumps(value)  # must be serialisable
        self.ops.append(["put", table, str(key), value])

    def delete(self, table, key):
        self.ops.append(["del", table, str(key), None])
