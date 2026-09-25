"""Durable, fenced, tamper-evident state journal (INV-63-C032, C049, C057, C058, C095).

Mutable state lives ONLY in the journal directory (never beside the immutable
package).  Layout::

    <state_dir>/journal.jsonl   append-only, one hash-chained record per line
    <state_dir>/epoch           monotonically increasing controller epoch (fencing)

Crash consistency: each record is written with a single ``write`` + ``fsync``.
On open, a torn final line (crash mid-write) is detected and truncated; any
corruption *before* the tail (hash mismatch, bad JSON) is a STATE_CORRUPT
failure — the store refuses to start rather than silently dropping history.

Fencing: a controller acquires the lease by bumping ``epoch``; every append
carries the writer's epoch and is rejected if a newer epoch exists, so a stale
controller (split brain after partition) cannot commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from .errors import DeploymentError, ErrorCode

GENESIS = "0" * 64


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(rec: dict[str, Any]) -> str:
    body = {k: rec[k] for k in ("seq", "epoch", "ts", "kind", "data", "prev")}
    return hashlib.sha256(_canon(body).encode()).hexdigest()


def _fsync_dir(path: pathlib.Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


@dataclass
class Record:
    seq: int
    epoch: int
    ts: float
    kind: str
    data: dict[str, Any]
    prev: str
    digest: str


class Journal:
    def __init__(self, state_dir: str | os.PathLike, *, clock: Callable[[], float] = time.time,
                 sealer: Any = None, max_bytes: int = 256 * 1024 * 1024):
        self.dir = pathlib.Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "journal.jsonl"
        self.epoch_path = self.dir / "epoch"
        self.clock = clock
        self.sealer = sealer
        self.max_bytes = max_bytes
        self.records: list[Record] = []
        self.epoch = 0           # epoch held by THIS handle (0 = not leader)
        self.recovered_torn_tail = False
        self._load()
        self._size = self.path.stat().st_size   # size this handle has seen (concurrent-writer detection)

    # ------------------------------------------------------------ recovery
    def _load(self) -> None:
        if not self.path.exists():
            self.path.touch()
            _fsync_dir(self.dir)
            return
        raw = self.path.read_bytes()
        lines = raw.split(b"\n")
        tail = lines[-1]
        complete = lines[:-1]
        prev = GENESIS
        good_len = 0
        for i, line in enumerate(complete):
            try:
                obj = json.loads(line)
                data = obj["data"]
                if isinstance(data, str) and self.sealer is not None:
                    data_plain = json.loads(self.sealer.open(data))
                else:
                    data_plain = data
                rec = Record(obj["seq"], obj["epoch"], obj["ts"], obj["kind"], data, obj["prev"], obj["digest"])
            except DeploymentError:
                raise
            except Exception:
                raise DeploymentError(ErrorCode.STATE_CORRUPT, f"journal line {i + 1} unparseable") from None
            if rec.seq != i + 1 or rec.prev != prev or _digest(obj) != rec.digest:
                raise DeploymentError(ErrorCode.STATE_CORRUPT, f"journal chain broken at seq {i + 1}",
                                      {"seq": i + 1})
            rec.data = data_plain
            self.records.append(rec)
            prev = rec.digest
            good_len += len(line) + 1
        if tail:
            # torn write: last line lacks its newline -> discard (never acknowledged)
            with open(self.path, "r+b") as fh:
                fh.truncate(good_len)
                fh.flush()
                os.fsync(fh.fileno())
            self.recovered_torn_tail = True

    # ------------------------------------------------------------ fencing
    def current_epoch(self) -> int:
        try:
            return int(self.epoch_path.read_text().strip() or 0)
        except FileNotFoundError:
            return 0
        except ValueError:
            raise DeploymentError(ErrorCode.STATE_CORRUPT, "epoch file corrupt") from None

    def acquire(self) -> int:
        """Become leader by bumping the epoch atomically (write-temp, fsync, rename)."""
        new = self.current_epoch() + 1
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".epoch.")
        with os.fdopen(fd, "w") as fh:
            fh.write(str(new))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.epoch_path)
        _fsync_dir(self.dir)
        self.epoch = new
        return new

    # ------------------------------------------------------------ append
    @property
    def head(self) -> str:
        return self.records[-1].digest if self.records else GENESIS

    def append(self, kind: str, data: dict[str, Any]) -> Record:
        if self.epoch == 0:
            raise DeploymentError(ErrorCode.STALE_EPOCH, "journal handle is not the leader")
        latest = self.current_epoch()
        if latest != self.epoch:
            raise DeploymentError(ErrorCode.STALE_EPOCH, f"fenced: epoch {self.epoch} < {latest}",
                                  {"held": self.epoch, "current": latest})
        # detect a concurrent writer that appended since we loaded
        if self.path.stat().st_size != self._expected_size():
            raise DeploymentError(ErrorCode.CONFLICT, "journal changed underneath this handle")
        if self.path.stat().st_size > self.max_bytes:
            raise DeploymentError(ErrorCode.QUOTA_EXCEEDED, "journal size limit reached; run DeploymentService.compact()")
        stored = self.sealer.seal(_canon(data).encode()) if self.sealer is not None else data
        obj = {"seq": len(self.records) + 1, "epoch": self.epoch, "ts": self.clock(), "kind": kind,
               "data": stored, "prev": self.head}
        obj["digest"] = _digest(obj)
        line = (_canon(obj) + "\n").encode()
        with open(self.path, "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        self._size = self._expected_size() + len(line)
        rec = Record(obj["seq"], obj["epoch"], obj["ts"], kind, data, obj["prev"], obj["digest"])
        self.records.append(rec)
        return rec

    def _expected_size(self) -> int:
        if not hasattr(self, "_size"):
            self._size = self.path.stat().st_size
        return self._size

    def compact(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Atomically replace the journal with a single snapshot record (C057/C067).

        The snapshot record's data carries the pre-compaction head digest and
        record count so the history boundary is itself tamper-evident; take a
        backup() first when full history must be retained.
        """
        if self.epoch == 0 or self.current_epoch() != self.epoch:
            raise DeploymentError(ErrorCode.STALE_EPOCH, "only the current leader may compact")
        data = dict(snapshot)
        data["_compacted"] = {"previous_head": self.head, "previous_records": len(self.records)}
        stored = self.sealer.seal(_canon(data).encode()) if self.sealer is not None else data
        obj = {"seq": 1, "epoch": self.epoch, "ts": self.clock(), "kind": "snapshot", "data": stored, "prev": GENESIS}
        obj["digest"] = _digest(obj)
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".journal.")
        with os.fdopen(fd, "wb") as fh:
            fh.write((_canon(obj) + "\n").encode())
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)
        _fsync_dir(self.dir)
        before = len(self.records)
        self.records = [Record(1, self.epoch, obj["ts"], "snapshot", data, GENESIS, obj["digest"])]
        self._size = self.path.stat().st_size
        return {"records_before": before, "records_after": 1, "head": self.head}

    def verify(self) -> bool:
        try:
            Journal(self.dir, sealer=self.sealer)
            return True
        except DeploymentError:
            return False

    def __iter__(self) -> Iterator[Record]:
        return iter(list(self.records))

    # ------------------------------------------------------------ backup / restore
    def backup(self, dest: str | os.PathLike) -> dict[str, Any]:
        dest = pathlib.Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.path, dest / "journal.jsonl")
        manifest = {"schema": "INV63_BACKUP/1", "records": len(self.records), "head": self.head,
                    "sha256": hashlib.sha256((dest / "journal.jsonl").read_bytes()).hexdigest(),
                    "taken_at": self.clock()}
        (dest / "BACKUP.json").write_text(_canon(manifest))
        return manifest

    @staticmethod
    def restore(backup_dir: str | os.PathLike, state_dir: str | os.PathLike, sealer: Any = None) -> "Journal":
        b = pathlib.Path(backup_dir)
        manifest = json.loads((b / "BACKUP.json").read_text())
        data = (b / "journal.jsonl").read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
            raise DeploymentError(ErrorCode.STATE_CORRUPT, "backup checksum mismatch")
        s = pathlib.Path(state_dir)
        s.mkdir(parents=True, exist_ok=True)
        if (s / "journal.jsonl").exists() and (s / "journal.jsonl").stat().st_size:
            raise DeploymentError(ErrorCode.PRECONDITION_FAILED, "restore target is not empty")
        (s / "journal.jsonl").write_bytes(data)
        j = Journal(s, sealer=sealer)
        if j.head != manifest["head"]:
            raise DeploymentError(ErrorCode.STATE_CORRUPT, "restored head mismatch")
        return j
