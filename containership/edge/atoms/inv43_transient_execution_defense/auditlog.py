"""Checklist 22: tamper-evident, append-only security audit chain.

Each event is a JSON line carrying ``seq``, ``prev`` (the previous entry's
hash), the event body and ``hash = SHA-256(prev || canonical(body+seq))``.
An optional HMAC key adds ``mac`` so an attacker who can rewrite the file
cannot recompute a consistent chain without the key.

Known blind spot of any hash chain: truncation of the tail is
indistinguishable from "fewer events happened".  :meth:`AuditLog.head`
returns ``(seq, hash)`` so the caller can anchor it externally (evidence
bundle, gate result); :func:`verify_file` takes an optional expected head and
detects truncation against it.
"""
from __future__ import annotations

import collections
import hashlib
import hmac
import json
import os
import pathlib
import threading
import time

GENESIS = "0" * 64
MEM_TAIL = 1000


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class AuditChainError(Exception):
    def __init__(self, message: str, code: str, seq: int | None = None):
        super().__init__(message)
        self.code = code
        self.seq = seq


class AuditLog:
    def __init__(self, path: str | os.PathLike | None = None, *, key: bytes | None = None,
                 clock=time.time) -> None:
        self._path = pathlib.Path(path) if path is not None else None
        self._key = key
        self._clock = clock
        self._lock = threading.Lock()
        # File-backed logs keep only a bounded in-memory tail (the file is the record);
        # memory-only logs are for tests/embedding and keep everything.  Found by the
        # 4.3.0 capacity benchmark: an unbounded tail grew ~1 KB per decision forever.
        self._mem = collections.deque(maxlen=MEM_TAIL) if self._path is not None else []
        self._seq = -1
        self._prev = GENESIS
        if self._path is not None and self._path.exists():
            entries = verify_file(self._path, key=key)
            if entries:
                self._seq, self._prev = entries[-1]["seq"], entries[-1]["hash"]

    def append(self, kind: str, **fields) -> dict:
        with self._lock:
            seq = self._seq + 1
            body = {"kind": kind, "at": self._clock(), **fields}
            h = hashlib.sha256(self._prev.encode() + _canon({"seq": seq, "body": body})).hexdigest()
            entry = {"seq": seq, "prev": self._prev, "body": body, "hash": h}
            if self._key is not None:
                entry["mac"] = hmac.new(self._key, h.encode(), hashlib.sha256).hexdigest()
            line = _canon(entry).decode() + "\n"
            if self._path is not None:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.flush()
                    os.fsync(fh.fileno())
            self._mem.append(entry)
            self._seq, self._prev = seq, h
            return entry

    def head(self) -> tuple[int, str]:
        with self._lock:
            return self._seq, self._prev

    def entries(self) -> list[dict]:
        with self._lock:
            return list(self._mem)


def verify_entries(entries: list[dict], *, key: bytes | None = None,
                   expected_head: tuple[int, str] | None = None) -> list[dict]:
    prev = GENESIS
    for i, e in enumerate(entries):
        if e.get("seq") != i:
            raise AuditChainError(f"sequence gap at {i}", "audit_sequence_gap", i)
        if e.get("prev") != prev:
            raise AuditChainError(f"broken link at {i}", "audit_broken_link", i)
        h = hashlib.sha256(prev.encode() + _canon({"seq": i, "body": e.get("body")})).hexdigest()
        if h != e.get("hash"):
            raise AuditChainError(f"hash mismatch at {i}", "audit_hash_mismatch", i)
        if key is not None:
            mac = hmac.new(key, h.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, str(e.get("mac", ""))):
                raise AuditChainError(f"mac mismatch at {i}", "audit_mac_mismatch", i)
        prev = h
    if expected_head is not None:
        seq = len(entries) - 1
        if (seq, prev) != tuple(expected_head):
            raise AuditChainError("chain head differs from anchored head (truncation or fork)",
                                  "audit_head_mismatch", seq)
    return entries


def verify_file(path, *, key: bytes | None = None, expected_head=None) -> list[dict]:
    entries = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                raise AuditChainError(f"unparseable line {n}", "audit_unparseable", n) from None
    return verify_entries(entries, key=key, expected_head=expected_head)
