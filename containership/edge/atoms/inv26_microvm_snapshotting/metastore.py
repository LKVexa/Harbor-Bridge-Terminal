"""Durable, transactional snapshot metadata store (X011, C057, C058, C036, C095).

Replaces the process-memory ``_snapshots`` dict as the authoritative state.

Storage format (directory ``root``)::

    state.json   compacted image {"schema", "seq", "fence", "records": {key: {"gen", "value"}}}
    wal.jsonl    append-only log of committed mutations since the image, one JSON per line,
                 each carrying seq and a SHA-256 over its own canonical body
    .lock        advisory lock file (fcntl.flock) -- serialises writers across processes

Every mutation: take the cross-process lock -> replay any WAL lines written by
other processes -> check compare-and-swap preconditions (``expect_gen``) ->
append + ``fsync`` the WAL line -> apply in memory. A crash can therefore
leave at most one *torn* trailing line, which replay detects by its checksum
and discards (it was never acknowledged). Compaction writes a new image to a
temp file, fsyncs, atomically replaces, then truncates the WAL.

Leases and fencing (C058): :meth:`acquire_lease` returns a strictly
increasing fencing token; mutations that pass ``fence=(name, token)`` are
rejected with ``SNAP_FENCED`` once a newer holder has the lease, so a paused
or partitioned stale controller cannot write.

``root=None`` gives an in-memory store with identical semantics (tests only).
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterator

from .errors import SnapshotServiceError

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None  # type: ignore

STATE_SCHEMA = "PK_SNAPSHOT_METASTORE/1"
COMPACT_EVERY = 500


def _canon(o: Any) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class MetaStore:
    def __init__(self, root: str | os.PathLike | None = None, *, clock: Callable[[], float] = time.time,
                 fail_after_wal_write: bool = False):
        self.root = Path(root) if root is not None else None
        self.clock = clock
        self._lock = threading.RLock()
        self._records: dict[str, dict] = {}
        self._seq = 0
        self._fence = 0
        self._wal_offset = 0
        self._wal_lines = 0
        self._epoch = 0
        self.torn_lines_discarded = 0
        self._torn_at = -1
        self.fail_after_wal_write = fail_after_wal_write  # fault-injection hook (C060)
        if self.root is not None:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            with self._xlock():
                self._load_image()
                self._replay()

    # ------------------------------------------------------------ persistence
    @contextlib.contextmanager
    def _xlock(self) -> Iterator[None]:
        with self._lock:
            if self.root is None or fcntl is None:
                yield
                return
            fd = os.open(self.root / ".lock", os.O_RDWR | os.O_CREAT, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def _load_image(self) -> None:
        p = self.root / "state.json"
        if p.exists():
            img = json.loads(p.read_text(encoding="utf-8"))
            if img.get("schema") != STATE_SCHEMA:
                raise SnapshotServiceError("SNAP_UNSUPPORTED_VERSION", f"metastore {img.get('schema')}")
            self._records = img["records"]
            self._seq = img["seq"]
            self._fence = img.get("fence", 0)
            self._epoch = img.get("epoch", 0)
        self._wal_offset = 0
        self._wal_lines = 0

    def _replay(self) -> None:
        p = self.root / "wal.jsonl"
        if not p.exists():
            return
        with p.open("rb") as fh:
            header = fh.readline()
            try:
                epoch = json.loads(header)["epoch"] if header.endswith(b"\n") else None
            except (ValueError, KeyError, TypeError):
                epoch = None
            if epoch != self._epoch:  # another process compacted since we loaded
                self._load_image()
            fh.seek(max(self._wal_offset, len(header)))
            if self._wal_offset < len(header):
                self._wal_offset = len(header)
            data = fh.read()
        consumed = 0
        for raw in data.splitlines(keepends=True):
            if not raw.endswith(b"\n"):
                self._note_torn(consumed)  # torn tail: never acknowledged
                break
            try:
                rec = json.loads(raw)
                body = {k: v for k, v in rec.items() if k != "sum"}
                if hashlib.sha256(_canon(body)).hexdigest() != rec["sum"]:
                    raise ValueError("checksum")
            except (ValueError, KeyError):
                self._note_torn(consumed)
                break
            consumed += len(raw)
            if rec["seq"] > self._seq:
                self._apply(rec)
        self._wal_offset += consumed

    def _note_torn(self, consumed: int) -> None:
        at = self._wal_offset + consumed
        if at != self._torn_at:
            self._torn_at = at
            self.torn_lines_discarded += 1

    def _apply(self, rec: dict) -> None:
        self._seq = rec["seq"]
        self._fence = max(self._fence, rec.get("fence", 0))
        for op in rec["ops"]:
            if op["op"] == "put":
                # store a private copy: the caller's dict must never alias committed state
                # (defect MS-1 found by the soak: post-commit mutation leaked into the in-memory view)
                self._records[op["key"]] = {"gen": op["gen"], "value": json.loads(_canon(op["value"]))}
            elif op["op"] == "del":
                self._records.pop(op["key"], None)
        self._wal_lines += 1

    def _append(self, ops: list[dict]) -> None:
        rec = {"seq": self._seq + 1, "ts": int(self.clock() * 1000), "fence": self._fence, "ops": ops}
        rec["sum"] = hashlib.sha256(_canon(rec)).hexdigest()
        if self.root is not None:
            line = _canon(rec) + b"\n"
            wal = self.root / "wal.jsonl"
            if not wal.exists() or wal.stat().st_size == 0:
                self._write_wal_header()
            elif wal.stat().st_size > self._wal_offset:
                # a torn, never-acknowledged tail from a crashed writer: cut it off
                # so the new record starts on a clean line boundary
                os.truncate(wal, self._wal_offset)
            fd = os.open(wal, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line)
                os.fsync(fd)
            finally:
                os.close(fd)
            self._wal_offset += len(line)
            if self.fail_after_wal_write:
                raise OSError("injected crash after WAL fsync")
        self._apply(rec)
        if self.root is not None and self._wal_lines >= COMPACT_EVERY:
            self._compact()

    def _write_wal_header(self) -> None:
        header = _canon({"epoch": self._epoch}) + b"\n"
        with open(self.root / "wal.jsonl", "wb") as fh:
            fh.write(header)
            fh.flush()
            os.fsync(fh.fileno())
        self._wal_offset = len(header)

    def _compact(self) -> None:
        self._epoch += 1
        img = {"schema": STATE_SCHEMA, "seq": self._seq, "fence": self._fence, "epoch": self._epoch,
               "records": self._records}
        tmp = self.root / "state.json.tmp"
        with open(tmp, "wb") as fh:
            fh.write(_canon(img))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.root / "state.json")
        self._write_wal_header()  # truncate in place, new epoch
        self._wal_lines = 0

    # ------------------------------------------------------------------- API
    def get(self, key: str) -> tuple[int, Any] | None:
        with self._xlock():
            if self.root is not None:
                self._replay()
            r = self._records.get(key)
            return (r["gen"], copy.deepcopy(r["value"])) if r else None

    def scan(self, prefix: str) -> dict[str, tuple[int, Any]]:
        with self._xlock():
            if self.root is not None:
                self._replay()
            return {k: (r["gen"], copy.deepcopy(r["value"])) for k, r in self._records.items()
                    if k.startswith(prefix)}

    def transact(self, puts: dict[str, tuple[int | None, Any]] | None = None,
                 deletes: dict[str, int] | None = None, *, fence: tuple[str, int] | None = None) -> dict[str, int]:
        """Atomically apply puts/deletes if every ``expect_gen`` matches.

        ``puts`` maps key -> (expect_gen, value); expect_gen ``0`` means "must not
        exist", ``None`` means unconditional. Returns key -> new generation.
        """
        puts, deletes = puts or {}, deletes or {}
        with self._xlock():
            if self.root is not None:
                self._replay()
            if fence is not None:
                self._check_fence(*fence)
            ops, out = [], {}
            for key, (expect, value) in puts.items():
                cur = self._records.get(key)
                cur_gen = cur["gen"] if cur else 0
                if expect is not None and expect != cur_gen:
                    raise SnapshotServiceError("SNAP_STALE_GENERATION", f"{key}: have {cur_gen}, expected {expect}")
                out[key] = cur_gen + 1
                ops.append({"op": "put", "key": key, "gen": cur_gen + 1, "value": value})
            for key, expect in deletes.items():
                cur = self._records.get(key)
                if cur is None or (expect is not None and cur["gen"] != expect):
                    raise SnapshotServiceError("SNAP_STALE_GENERATION", f"{key}: delete precondition")
                ops.append({"op": "del", "key": key})
            if ops:
                self._append(ops)
            return out

    # --------------------------------------------------------- leases/fences
    def acquire_lease(self, name: str, holder: str, ttl_s: float) -> int:
        with self._xlock():
            if self.root is not None:
                self._replay()
            now = self.clock()
            cur = self._records.get(f"lease/{name}")
            if cur and cur["value"]["holder"] != holder and cur["value"]["expires"] > now:
                raise SnapshotServiceError("SNAP_FENCED", f"lease {name} held by another controller")
            self._fence += 1
            token = self._fence
            gen = (cur["gen"] if cur else 0) + 1
            self._append([{"op": "put", "key": f"lease/{name}", "gen": gen,
                           "value": {"holder": holder, "token": token, "expires": now + ttl_s}}])
            return token

    def _check_fence(self, name: str, token: int) -> None:
        cur = self._records.get(f"lease/{name}")
        if not cur or cur["value"]["token"] != token or cur["value"]["expires"] <= self.clock():
            raise SnapshotServiceError("SNAP_FENCED", f"fencing token {token} for {name} is stale")

    # ------------------------------------------------------------- ops/backup
    @property
    def seq(self) -> int:
        return self._seq

    def export(self) -> dict:
        with self._xlock():
            if self.root is not None:
                self._replay()
            body = {"schema": STATE_SCHEMA, "seq": self._seq, "fence": self._fence,
                    "records": copy.deepcopy(self._records)}
            body["sha256"] = hashlib.sha256(_canon(body)).hexdigest()
            return body

    @classmethod
    def import_backup(cls, root: str | os.PathLike, backup: dict, **kw) -> "MetaStore":
        body = {k: v for k, v in backup.items() if k != "sha256"}
        if hashlib.sha256(_canon(body)).hexdigest() != backup.get("sha256"):
            raise SnapshotServiceError("SNAP_STORAGE_CORRUPT", "metadata backup checksum mismatch")
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if (root / "state.json").exists() or (root / "wal.jsonl").exists():
            raise SnapshotServiceError("SNAP_DUPLICATE", "refusing to restore over existing metadata")
        (root / "state.json").write_bytes(_canon(body))
        return cls(root, **kw)
