"""MC04 - Durable write-ahead log and recovery; MC05 - crash-consistent snapshots.

WAL record framing (little-endian)::

    MAGIC(4)="G5WL" | length(u32) | sha256(payload)(32) | payload(JSON, canonical)

* Append is ``write`` + ``flush`` + ``os.fsync`` before the caller may acknowledge.
* Recovery scans from the start.  A short or checksum-failing **final** record is a
  torn tail (crash mid-append of an unacknowledged record) and is truncated.  A bad
  record followed by further valid framing is mid-log corruption: recovery fails closed
  with ``IntegrityError`` and requires an operator restore (never silently skipped).

Snapshots (checkpoints) are written as ``snapshot-<generation>.json`` via temp file +
fsync + ``os.replace`` + directory fsync, and embed a sha256 over their canonical body.
Recovery loads the newest snapshot that validates, falling back to older generations,
then replays the WAL records whose sequence number is greater than the snapshot's.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import threading
from pathlib import Path
from typing import Iterator

from .errors import IntegrityError
from .schemas import canonical_bytes

MAGIC = b"G5WL"
HEADER = struct.Struct("<4sI32s")
SNAPSHOT_FORMAT = "GAP05_SNAPSHOT/2"
WAL_FORMAT = "GAP05_WAL/1"

# Fault-injection hook for crash tests (MC35): name of a boundary at which to abort.
CRASH_POINT_ENV = "GAP05_CRASH_AT"


def _maybe_crash(point: str) -> None:
    if os.environ.get(CRASH_POINT_ENV) == point:
        os._exit(77)


def fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:  # pragma: no cover - platforms without directory fds
        return
    try:
        os.fsync(fd)
    except OSError:  # pragma: no cover
        pass
    finally:
        os.close(fd)


def atomic_write(path: Path, data: bytes) -> None:
    path = Path(path)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        _maybe_crash("atomic_before_fsync")
        os.fsync(fh.fileno())
    _maybe_crash("atomic_before_replace")
    os.replace(tmp, path)
    fsync_dir(path.parent)


class WriteAheadLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.recovery_report: dict = {}
        self._records = list(self._recover())
        self._fh = open(self.path, "ab")
        self.next_seq = (self._records[-1]["seq"] + 1) if self._records else 1

    def _recover(self) -> Iterator[dict]:
        if not self.path.exists():
            self.recovery_report = {"records": 0, "truncated_bytes": 0}
            return
        data = self.path.read_bytes()
        offset, good_end, out = 0, 0, []
        truncated_reason = None
        while offset < len(data):
            if len(data) - offset < HEADER.size:
                truncated_reason = "short header"
                break
            magic, length, digest = HEADER.unpack_from(data, offset)
            start, end = offset + HEADER.size, offset + HEADER.size + length
            if magic != MAGIC:
                truncated_reason = "bad magic"
                break
            if end > len(data):
                truncated_reason = "short payload"
                break
            payload = data[start:end]
            if hashlib.sha256(payload).digest() != digest:
                truncated_reason = "checksum"
                break
            record = json.loads(payload)
            if out and record.get("seq") != out[-1]["seq"] + 1:
                raise IntegrityError("WAL sequence gap", code="CORR_WAL_SEQUENCE")
            out.append(record)
            offset = good_end = end
        if truncated_reason is not None:
            # Distinguish torn tail from mid-log corruption: search for a later valid frame.
            if self._later_valid_frame(data, good_end + 1):
                raise IntegrityError(
                    f"WAL corruption at byte {good_end} ({truncated_reason}) with valid data after it",
                    code="CORR_WAL_CORRUPT",
                )
            with open(self.path, "r+b") as fh:
                fh.truncate(good_end)
                fh.flush()
                os.fsync(fh.fileno())
        self.recovery_report = {"records": len(out), "truncated_bytes": len(data) - good_end,
                                "truncated_reason": truncated_reason}
        yield from out

    @staticmethod
    def _later_valid_frame(data: bytes, start: int) -> bool:
        idx = data.find(MAGIC, start)
        while idx != -1:
            if len(data) - idx >= HEADER.size:
                _m, length, digest = HEADER.unpack_from(data, idx)
                end = idx + HEADER.size + length
                if end <= len(data) and hashlib.sha256(data[idx + HEADER.size:end]).digest() == digest:
                    return True
            idx = data.find(MAGIC, idx + 1)
        return False

    @property
    def records(self) -> list[dict]:
        return list(self._records)

    def append(self, kind: str, body: dict) -> dict:
        with self._lock:
            record = {"format": WAL_FORMAT, "seq": self.next_seq, "kind": kind, "body": body}
            payload = canonical_bytes(record)
            frame = HEADER.pack(MAGIC, len(payload), hashlib.sha256(payload).digest()) + payload
            _maybe_crash("wal_before_write")
            half = len(frame) // 2
            self._fh.write(frame[:half])
            if os.environ.get(CRASH_POINT_ENV) == "wal_mid_write":
                self._fh.flush()
                os._exit(77)
            self._fh.write(frame[half:])
            self._fh.flush()
            _maybe_crash("wal_before_fsync")
            os.fsync(self._fh.fileno())
            _maybe_crash("wal_after_fsync")
            self._records.append(record)
            self.next_seq += 1
            return record

    def records_after(self, seq: int) -> list[dict]:
        return [r for r in self._records if r["seq"] > seq]

    def compact_before(self, seq: int) -> None:
        """Drop records covered by a durable snapshot (atomic rewrite)."""
        with self._lock:
            keep = [r for r in self._records if r["seq"] > seq]
            blob = b"".join(
                HEADER.pack(MAGIC, len(p), hashlib.sha256(p).digest()) + p
                for p in (canonical_bytes(r) for r in keep)
            )
            self._fh.close()
            atomic_write(self.path, blob)
            self._records = keep
            self._fh = open(self.path, "ab")

    def close(self) -> None:
        self._fh.close()


class SnapshotStore:
    def __init__(self, directory: Path, *, keep: int = 3):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.keep = keep

    def _paths(self) -> list[tuple[int, Path]]:
        out = []
        for p in self.dir.glob("snapshot-*.json"):
            try:
                out.append((int(p.stem.split("-")[1]), p))
            except (IndexError, ValueError):
                continue
        return sorted(out)

    def write(self, generation: int, wal_seq: int, state: dict) -> Path:
        body = {"format": SNAPSHOT_FORMAT, "generation": generation, "wal_seq": wal_seq, "state": state}
        doc = {"body": body, "sha256": hashlib.sha256(canonical_bytes(body)).hexdigest()}
        path = self.dir / f"snapshot-{generation:012d}.json"
        atomic_write(path, canonical_bytes(doc))
        for _gen, old in self._paths()[: -self.keep]:
            old.unlink()
        fsync_dir(self.dir)
        return path

    @staticmethod
    def validate(path: Path) -> dict:
        try:
            doc = json.loads(Path(path).read_bytes())
            body = doc["body"]
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise IntegrityError(f"unreadable snapshot {path}: {exc}", code="CORR_SNAPSHOT_UNREADABLE") from exc
        if hashlib.sha256(canonical_bytes(body)).hexdigest() != doc.get("sha256"):
            raise IntegrityError(f"snapshot checksum mismatch {path}", code="CORR_SNAPSHOT_CHECKSUM")
        if body.get("format") != SNAPSHOT_FORMAT:
            raise IntegrityError(f"unknown snapshot format {body.get('format')}", code="CORR_SNAPSHOT_FORMAT")
        return body

    def latest_valid(self) -> tuple[dict | None, list[dict]]:
        rejected = []
        for gen, path in reversed(self._paths()):
            try:
                return self.validate(path), rejected
            except IntegrityError as exc:
                rejected.append({"generation": gen, "error": exc.as_record()})
        return None, rejected
