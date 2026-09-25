"""Durable, crash-consistent checkpoint store (INV-37-C018, C057, C058, C059, C095).

Layout under the configured directory (never inside the package):

    <root>/transfers/<transfer_id>/data.bin     preallocated object bytes
    <root>/transfers/<transfer_id>/state.json   sealed checkpoint record
    <root>/transfers/<transfer_id>/lease.json   fencing epoch + owner
    <root>/quarantine/<transfer_id>-<ts>/       frozen evidence

Write ordering (write-ahead of data before state):
    1. pwrite chunk bytes into data.bin, fsync(data.bin)
    2. atomically replace state.json (tmp + fsync + rename + dir fsync)
A crash between 1 and 2 loses only the un-acknowledged chunk; the chunk is
reported as missing on restart and re-sent.  On load every chunk claimed in
state.json is re-hashed from data.bin; a claimed-but-unverifiable chunk is
dropped (never trusted), and a broken seal quarantines the transfer.

Seal: HMAC-SHA256 when a key is supplied (tamper-evident), otherwise SHA-256
(torn-write detection only).  Format id ``INV37_CHECKPOINT/1``.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import atomic_write_json
from .errors import CodedError

CHECKPOINT_SCHEMA = "INV37_CHECKPOINT/1"
LEASE_SCHEMA = "INV37_LEASE/1"
_ID = re.compile(r"^[A-Za-z0-9_-]{1,96}$")


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def check_id(transfer_id: str) -> str:
    if not isinstance(transfer_id, str) or not _ID.match(transfer_id):
        raise CodedError("invalid_manifest", "transfer id must match [A-Za-z0-9_-]{1,96}")
    return transfer_id


@dataclass
class Lease:
    transfer_id: str
    owner: str
    epoch: int


class CheckpointStore:
    def __init__(self, root: str | os.PathLike[str], *, seal_key: bytes | None = None,
                 fsync: bool = True, max_bytes: int | None = None) -> None:
        self.root = Path(root)
        pkg = Path(__file__).resolve().parent
        r = self.root.resolve()
        if r == pkg or pkg in r.parents:
            raise CodedError("invalid_config", "checkpoint root must not be inside the installed package")
        (self.root / "transfers").mkdir(parents=True, exist_ok=True)
        (self.root / "quarantine").mkdir(parents=True, exist_ok=True)
        self._key = seal_key
        self._fsync = fsync
        self._max_bytes = max_bytes
        self._lock = threading.RLock()

    # -- paths ---------------------------------------------------------------
    def _dir(self, tid: str) -> Path:
        return self.root / "transfers" / check_id(tid)

    @contextmanager
    def _xlock(self, tid: str):
        """Cross-process exclusive lock per transfer (flock on POSIX) so that
        lease acquisition and check-then-write are atomic across processes."""
        with self._lock:
            d = self._dir(tid)
            d.mkdir(parents=True, exist_ok=True)
            if os.name != "posix":  # pragma: no cover - Windows: in-process lock only (documented)
                yield
                return
            import fcntl

            fd = os.open(d / ".lock", os.O_RDWR | os.O_CREAT, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def _seal(self, body: Mapping[str, Any]) -> str:
        blob = _canon(body)
        if self._key:
            return "hmac-sha256:" + hmac.new(self._key, blob, hashlib.sha256).hexdigest()
        return "sha256:" + hashlib.sha256(blob).hexdigest()

    # -- fencing -------------------------------------------------------------
    def acquire(self, tid: str, owner: str) -> Lease:
        """Take ownership, bumping the fencing epoch.  Any holder of an older
        epoch is fenced out on its next write (split-brain protection)."""
        with self._xlock(tid):
            d = self._dir(tid)
            lp = d / "lease.json"
            epoch = 0
            if lp.exists():
                try:
                    epoch = int(json.loads(lp.read_text())["epoch"])
                except (OSError, ValueError, KeyError, json.JSONDecodeError):
                    epoch = 0
            lease = Lease(tid, owner, epoch + 1)
            atomic_write_json(lp, {"schema": LEASE_SCHEMA, "owner": owner, "epoch": lease.epoch,
                                   "acquired_at": time.time()}, fsync=self._fsync)
            return lease

    def _check_lease(self, lease: Lease) -> None:
        try:
            cur = json.loads((self._dir(lease.transfer_id) / "lease.json").read_text())
        except (OSError, json.JSONDecodeError):
            raise CodedError("stale_owner", "lease missing") from None
        if cur.get("epoch") != lease.epoch or cur.get("owner") != lease.owner:
            raise CodedError("stale_owner", "fencing epoch superseded", held=lease.epoch, current=cur.get("epoch"))

    # -- lifecycle -----------------------------------------------------------
    def used_bytes(self) -> int:
        total = 0
        for p in (self.root / "transfers").glob("*/data.bin"):
            try:
                total += p.stat().st_size
            except OSError:
                pass
        return total

    def create(self, lease: Lease, manifest: Mapping[str, Any], *, tenant: str, meta: Mapping[str, Any] | None = None) -> None:
        with self._xlock(lease.transfer_id):
            self._check_lease(lease)
            size = int(manifest["size"])
            if self._max_bytes is not None and self.used_bytes() + size > self._max_bytes:
                raise CodedError("quota_exceeded", "checkpoint storage quota exhausted", limit=self._max_bytes)
            d = self._dir(lease.transfer_id)
            data = d / "data.bin"
            if not data.exists():
                with open(data, "wb") as fh:
                    fh.truncate(size)
                    if self._fsync:
                        os.fsync(fh.fileno())
            if not (d / "state.json").exists():
                self._write_state(lease, {"manifest": dict(manifest), "tenant": tenant, "verified": [],
                                          "lifecycle": "ready", "meta": dict(meta or {}), "created_at": time.time()})

    def _write_state(self, lease: Lease, body: dict[str, Any]) -> None:
        body = dict(body)
        body.update({"schema": CHECKPOINT_SCHEMA, "transfer_id": lease.transfer_id, "epoch": lease.epoch,
                     "updated_at": time.time()})
        body.pop("seal", None)
        body["seal"] = self._seal(body)
        atomic_write_json(self._dir(lease.transfer_id) / "state.json", body, fsync=self._fsync)

    def write_chunk(self, lease: Lease, index: int, offset: int, payload: memoryview | bytes,
                    verified: Iterable[int], lifecycle: str) -> None:
        """Persist a verified chunk and the new verified set (data first, then state)."""
        with self._xlock(lease.transfer_id):
            self._check_lease(lease)
            d = self._dir(lease.transfer_id)
            fd = os.open(d / "data.bin", os.O_RDWR)
            try:
                os.pwrite(fd, payload, offset) if hasattr(os, "pwrite") else _seek_write(fd, payload, offset)
                if self._fsync:
                    os.fsync(fd)
            finally:
                os.close(fd)
            st = self._read_state_raw(lease.transfer_id)
            st["verified"] = sorted(set(verified))
            st["lifecycle"] = lifecycle
            self._write_state(lease, st)

    def set_lifecycle(self, lease: Lease, lifecycle: str) -> None:
        with self._xlock(lease.transfer_id):
            self._check_lease(lease)
            st = self._read_state_raw(lease.transfer_id)
            st["lifecycle"] = lifecycle
            self._write_state(lease, st)

    def _read_state_raw(self, tid: str) -> dict[str, Any]:
        p = self._dir(tid) / "state.json"
        try:
            body = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise CodedError("checkpoint_corrupt", "checkpoint unreadable", transfer_id=tid) from None
        seal = body.pop("seal", None)
        if body.get("schema") != CHECKPOINT_SCHEMA:
            raise CodedError("version_incompatible", "unsupported checkpoint schema", schema=body.get("schema"))
        if not isinstance(seal, str) or not hmac.compare_digest(seal, self._seal(body)):
            raise CodedError("checkpoint_corrupt", "checkpoint seal invalid", transfer_id=tid)
        return body

    def load(self, tid: str) -> dict[str, Any]:
        """Reconstruct state after restart; re-verifies every claimed chunk."""
        with self._lock:
            try:
                st = self._read_state_raw(tid)
            except CodedError as exc:
                if exc.code == "checkpoint_corrupt":
                    self.quarantine(tid, reason=exc.message)
                raise
            m = st["manifest"]
            good: list[int] = []
            dropped: list[int] = []
            with open(self._dir(tid) / "data.bin", "rb") as fh:
                for i in st["verified"]:
                    if type(i) is not int or not 0 <= i < m["chunk_count"]:
                        dropped.append(i)
                        continue
                    off = i * m["chunk"]
                    ln = min(m["chunk"], m["size"] - off)
                    fh.seek(off)
                    if hashlib.sha256(fh.read(ln)).hexdigest() == m["chunks"][i]:
                        good.append(i)
                    else:
                        dropped.append(i)
            st["verified"] = good
            st["dropped_on_load"] = dropped
            return st

    def read_object(self, tid: str) -> bytes:
        return (self._dir(tid) / "data.bin").read_bytes()

    def data_path(self, tid: str) -> Path:
        return self._dir(tid) / "data.bin"

    def list(self) -> list[str]:
        return sorted(p.name for p in (self.root / "transfers").iterdir() if p.is_dir())

    def quarantine(self, tid: str, *, reason: str) -> Path:
        with self._lock:
            src = self._dir(tid)
            dst = self.root / "quarantine" / f"{tid}-{int(time.time() * 1000)}"
            if src.exists():
                shutil.move(str(src), dst)
            else:
                dst.mkdir(parents=True)
            (dst / "REASON.txt").write_text(reason + "\n", encoding="utf-8")
            return dst

    def delete(self, tid: str) -> None:
        with self._lock:
            shutil.rmtree(self._dir(tid), ignore_errors=True)

    def gc(self, *, retention_seconds: float, now: float | None = None) -> list[str]:
        """Remove abandoned transfers whose state is older than retention."""
        now = time.time() if now is None else now
        removed = []
        for tid in self.list():
            p = self._dir(tid) / "state.json"
            try:
                age = now - p.stat().st_mtime
            except OSError:
                age = now - self._dir(tid).stat().st_mtime
            if age > retention_seconds:
                self.delete(tid)
                removed.append(tid)
        return removed

    def export_inventory(self) -> list[dict[str, Any]]:
        """Operator view for stranded-state inspection (no payload bytes)."""
        out = []
        for tid in self.list():
            try:
                st = self._read_state_raw(tid)
                out.append({"transfer_id": tid, "tenant": st.get("tenant"), "lifecycle": st.get("lifecycle"),
                            "verified": len(st.get("verified", [])), "chunks": st["manifest"]["chunk_count"],
                            "epoch": st.get("epoch"), "updated_at": st.get("updated_at")})
            except CodedError as exc:
                out.append({"transfer_id": tid, "error": exc.code})
        return out


def _seek_write(fd: int, payload: Any, offset: int) -> None:  # pragma: no cover - non-POSIX
    os.lseek(fd, offset, os.SEEK_SET)
    os.write(fd, payload)
