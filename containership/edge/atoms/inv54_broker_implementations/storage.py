"""Durable partition log (components 41, 47, 48, 57, 61).

On-disk format, one file per partition ``p<N>.log``, append-only records::

    MAGIC(4)=b"I54R" | LEN(4,be) | CRC32(4,be) | PAYLOAD(LEN)

PAYLOAD is JSON ``{"o": offset, "k": key, "v": value, "t": ts}``; when at-rest encryption
is enabled it is AES-256-GCM(nonce(12) || ciphertext) under a key resolved from a secret
reference, with the partition+offset bound as associated data so records cannot be
swapped between positions.  Recovery scans each file, stops at the first torn/corrupt
record *at the tail* and truncates it (crash during append); a corrupt record followed by
valid records is reported as corruption, never silently skipped.

Retention (max_records / max_age) advances a persisted ``low watermark``; compaction
rewrites a partition keeping only the latest value per key, preserving offsets.
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import tarfile
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from .errors import (INVALID_ARGUMENT, OFFSET_OUT_OF_RANGE, SECURITY_SERVICE_UNAVAILABLE, STORAGE_CORRUPTION,
                     STORAGE_IO, BrokerError)

MAGIC = b"I54R"
HDR = struct.Struct(">4sII")
FORMAT_VERSION = 1


class Cipher:
    """AES-256-GCM via the optional ``cryptography`` package. Absent library => fail closed."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise BrokerError(INVALID_ARGUMENT, "at-rest key must be 32 bytes")
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise BrokerError(SECURITY_SERVICE_UNAVAILABLE, "encryption requested but 'cryptography' missing") from exc
        self._aead = AESGCM(key)

    def seal(self, data: bytes, aad: bytes) -> bytes:
        nonce = os.urandom(12)
        return nonce + self._aead.encrypt(nonce, data, aad)

    def open(self, blob: bytes, aad: bytes) -> bytes:
        try:
            return self._aead.decrypt(blob[:12], blob[12:], aad)
        except Exception as exc:
            raise BrokerError(STORAGE_CORRUPTION, "record failed authenticated decryption") from exc


@dataclass
class Record:
    offset: int
    key: str
    value: Any
    ts: float


class DurableLog:
    def __init__(self, path: str | os.PathLike, partitions: int = 4, *, fsync: str = "always",
                 cipher: Cipher | None = None, max_records_per_partition: int = 1_000_000,
                 clock: Callable[[], float] = time.time) -> None:
        if type(partitions) is not int or partitions < 1:
            raise BrokerError(INVALID_ARGUMENT, "partitions must be int >= 1")
        if fsync not in ("always", "batch", "never"):
            raise BrokerError(INVALID_ARGUMENT, "fsync must be always|batch|never")
        self.root = Path(path)
        self.root.mkdir(parents=True, exist_ok=True)
        self.partitions, self.fsync, self.cipher, self.clock = partitions, fsync, cipher, clock
        self.max_records = max_records_per_partition
        self._lock = RLock()
        self._meta_path = self.root / "meta.json"
        meta = self._load_meta()
        if meta and meta["partitions"] != partitions:
            raise BrokerError(INVALID_ARGUMENT, "partition count differs from on-disk metadata",
                              on_disk=meta["partitions"])
        self.low = list(meta["low"]) if meta else [0] * partitions
        self.encrypted = bool(meta["encrypted"]) if meta else cipher is not None
        if self.encrypted and cipher is None:
            raise BrokerError(SECURITY_SERVICE_UNAVAILABLE, "log is encrypted; key unavailable")
        self._index: list[list[Record]] = [[] for _ in range(partitions)]
        self.recovered_truncations = 0
        self._files = []
        for p in range(partitions):
            self._index[p] = self._recover(p)
            self._files.append(open(self._path(p), "ab"))
        self._save_meta()

    # ---------------------------------------------------------------- internals
    def _path(self, p: int) -> Path:
        return self.root / f"p{p}.log"

    def _load_meta(self) -> dict | None:
        if not self._meta_path.exists():
            return None
        return json.loads(self._meta_path.read_text())

    def _save_meta(self) -> None:
        tmp = self._meta_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"format": FORMAT_VERSION, "partitions": self.partitions, "low": self.low,
                                   "encrypted": self.encrypted}))
        os.replace(tmp, self._meta_path)  # atomic rename

    def _encode(self, p: int, rec: Record) -> bytes:
        payload = json.dumps({"o": rec.offset, "k": rec.key, "v": rec.value, "t": rec.ts},
                             separators=(",", ":")).encode()
        if self.cipher:
            payload = struct.pack(">Q", rec.offset) + self.cipher.seal(payload, f"{p}:{rec.offset}".encode())
        return HDR.pack(MAGIC, len(payload), zlib.crc32(payload)) + payload

    def _decode(self, p: int, payload: bytes) -> Record:
        if self.cipher:
            (off,) = struct.unpack_from(">Q", payload)
            payload = self.cipher.open(payload[8:], f"{p}:{off}".encode())
            d = json.loads(payload)
            if d["o"] != off:
                raise BrokerError(STORAGE_CORRUPTION, "offset binding mismatch", partition=p)
        else:
            d = json.loads(payload)
        return Record(d["o"], d["k"], d["v"], d["t"])

    def _recover(self, p: int) -> list[Record]:
        path = self._path(p)
        if not path.exists():
            return []
        data = path.read_bytes()
        pos, out, good_end = 0, [], 0
        while pos < len(data):
            if len(data) - pos < HDR.size:
                break
            magic, ln, crc = HDR.unpack_from(data, pos)
            end = pos + HDR.size + ln
            if magic != MAGIC or end > len(data) or zlib.crc32(data[pos + HDR.size:end]) != crc:
                break
            rec = self._decode(p, data[pos + HDR.size:end])
            out.append(rec)
            pos = good_end = end
        if good_end < len(data):
            # Is there any valid record *after* the bad spot?  If so this is mid-file corruption.
            if _find_magic_record(data, good_end + 1):
                raise BrokerError(STORAGE_CORRUPTION, "corrupt record before valid data", partition=p,
                                  byte_offset=good_end)
            with open(path, "r+b") as f:
                f.truncate(good_end)
                f.flush()
                os.fsync(f.fileno())
            self.recovered_truncations += 1
        return out

    def _sync(self, f) -> None:
        f.flush()
        if self.fsync == "always":
            os.fsync(f.fileno())

    def _check_p(self, p: int) -> int:
        if type(p) is not int or not 0 <= p < self.partitions:
            raise BrokerError(INVALID_ARGUMENT, "partition out of range", partition=p)
        return p

    # ---------------------------------------------------------------- API
    def partition_for(self, key: str) -> int:
        return zlib.crc32(key.encode()) % self.partitions

    def append(self, key: str, value: Any, partition: int | None = None) -> tuple[int, int]:
        if not isinstance(key, str):
            raise BrokerError(INVALID_ARGUMENT, "key must be str")
        p = self.partition_for(key) if partition is None else self._check_p(partition)
        with self._lock:
            idx = self._index[p]
            if len(idx) >= self.max_records:
                raise BrokerError(INVALID_ARGUMENT, "partition at hard record ceiling; apply retention",
                                  partition=p)
            off = (idx[-1].offset + 1) if idx else self.low[p]
            rec = Record(off, key, value, self.clock())
            try:
                self._files[p].write(self._encode(p, rec))
                self._sync(self._files[p])
            except OSError as exc:
                raise BrokerError(STORAGE_IO, type(exc).__name__) from exc
            idx.append(rec)
            return p, off

    def flush(self) -> None:
        with self._lock:
            for f in self._files:
                f.flush()
                os.fsync(f.fileno())

    def read(self, p: int, offset: int, limit: int = 100) -> list[Record]:
        p = self._check_p(p)
        with self._lock:
            idx = self._index[p]
            end = (idx[-1].offset + 1) if idx else self.low[p]
            if offset < self.low[p] or offset > end:
                raise BrokerError(OFFSET_OUT_OF_RANGE, low=self.low[p], high=end, requested=offset)
            return [r for r in idx if r.offset >= offset][:limit]

    def bounds(self, p: int) -> tuple[int, int]:
        p = self._check_p(p)
        idx = self._index[p]
        return self.low[p], (idx[-1].offset + 1) if idx else self.low[p]

    def apply_retention(self, *, max_records: int | None = None, max_age_s: float | None = None) -> int:
        removed = 0
        with self._lock:
            now = self.clock()
            for p in range(self.partitions):
                idx = self._index[p]
                keep_from = 0
                if max_records is not None and len(idx) > max_records:
                    keep_from = len(idx) - max_records
                if max_age_s is not None:
                    while keep_from < len(idx) and now - idx[keep_from].ts > max_age_s:
                        keep_from += 1
                if keep_from:
                    removed += keep_from
                    self.low[p] = idx[keep_from].offset if keep_from < len(idx) else idx[-1].offset + 1
                    self._rewrite(p, idx[keep_from:])
            self._save_meta()
        return removed

    def compact(self) -> int:
        """Keep the latest record per key; offsets preserved (gaps allowed)."""
        removed = 0
        with self._lock:
            for p in range(self.partitions):
                idx = self._index[p]
                latest = {r.key: r.offset for r in idx}
                kept = [r for r in idx if latest[r.key] == r.offset]
                if len(kept) != len(idx):
                    removed += len(idx) - len(kept)
                    self._rewrite(p, kept)
        return removed

    def _rewrite(self, p: int, recs: list[Record]) -> None:
        tmp = self._path(p).with_suffix(".tmp")
        with open(tmp, "wb") as f:
            for r in recs:
                f.write(self._encode(p, r))
            f.flush()
            os.fsync(f.fileno())
        self._files[p].close()
        os.replace(tmp, self._path(p))
        self._files[p] = open(self._path(p), "ab")
        self._index[p] = list(recs)

    def close(self) -> None:
        with self._lock:
            for f in self._files:
                try:
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    f.close()
            self._files = []

    # ------------------------------------------------------------ backup/restore (61)
    def backup(self, dest: str | os.PathLike) -> Path:
        with self._lock:
            self.flush()
            dest = Path(dest)
            with tarfile.open(dest, "w:gz") as tar:
                for f in sorted(self.root.iterdir()):
                    if f.suffix in (".log", ".json"):
                        tar.add(f, arcname=f.name)
            return dest

    @staticmethod
    def restore(archive: str | os.PathLike, dest: str | os.PathLike) -> Path:
        dest = Path(dest)
        if dest.exists() and any(dest.iterdir()):
            raise BrokerError(INVALID_ARGUMENT, "restore target must be empty")
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tar:
            for m in tar.getmembers():
                if not m.isfile() or "/" in m.name or m.name.startswith(".."):
                    raise BrokerError(STORAGE_CORRUPTION, "unsafe member in backup archive", member=m.name)
            tar.extractall(dest, filter="data")
        return dest


def _find_magic_record(data: bytes, start: int) -> bool:
    i = data.find(MAGIC, start)
    while i != -1:
        if len(data) - i >= HDR.size:
            _, ln, crc = HDR.unpack_from(data, i)
            end = i + HDR.size + ln
            if end <= len(data) and zlib.crc32(data[i + HDR.size:end]) == crc:
                return True
        i = data.find(MAGIC, i + 1)
    return False


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst)
