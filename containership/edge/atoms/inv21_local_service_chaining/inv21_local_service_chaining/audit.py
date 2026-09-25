"""Tamper-evident security audit stream (PK_CHAIN_AUDIT/1) -- GAP-018.

Each record is canonical JSON carrying ``seq``, ``prev`` (hash of the prior
record) and ``mac`` = HMAC-SHA256(key, canonical(record without mac)). The
first record is a genesis record binding the release/config lineage. Any
edit, deletion, reorder or truncation-with-append breaks :func:`verify`.
Tail truncation alone is detectable only against an externally recorded
head (``head()``), which operators export to their SIEM -- documented in
docs/OPERATIONS.md.

Sinks: in-memory bounded ring (for tests) and append-only JSONL file with
fsync. A sink failure is surfaced (``sink_errors``) and, in ``fail_closed``
mode, raises so security decisions are never taken unaudited.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from collections import deque
from typing import Iterable, Optional

from .errors import InternalError

AUDIT_SCHEMA = "PK_CHAIN_AUDIT/1"
GENESIS = "0" * 64


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


class AuditLog:
    def __init__(self, key: bytes, *, lineage: Optional[dict] = None, path: Optional[str] = None,
                 memory_max: int = 4096, fail_closed: bool = True) -> None:
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("audit key must be >= 32 bytes")
        self._key = key
        self._lock = threading.Lock()
        self._mem: deque = deque(maxlen=memory_max)
        self._hashes: deque = deque(maxlen=memory_max)  # sha256 of each retained record line
        self._path = path
        self.fail_closed = fail_closed
        self.sink_errors = 0
        self._seq = 0
        self._prev = GENESIS
        self._evicted_tail = (GENESIS, 0)  # (prev-hash, seq) anchoring the oldest retained record
        self._fh = None
        if path:
            self._fh = open(path, "a", encoding="utf-8")
        self.append("genesis", lineage=lineage or {})

    def _mac(self, rec: dict) -> str:
        return hmac.new(self._key, _canon(rec), hashlib.sha256).hexdigest()

    def append(self, kind: str, **fields) -> dict:
        with self._lock:
            rec = {"schema": AUDIT_SCHEMA, "seq": self._seq, "ts": round(time.time(), 6),
                   "kind": kind, "prev": self._prev, **fields}
            rec["mac"] = self._mac(rec)
            line = _canon(rec)
            if self._fh is not None:
                try:
                    self._fh.write(line.decode() + "\n"); self._fh.flush(); os.fsync(self._fh.fileno())
                except OSError:
                    self.sink_errors += 1
                    if self.fail_closed:
                        raise InternalError("audit sink failure; refusing unaudited decision")
            if self._mem.maxlen is not None and len(self._mem) == self._mem.maxlen:
                self._evicted_tail = (self._hashes[0], self._mem[0]["seq"] + 1)
            digest = hashlib.sha256(line).hexdigest()
            self._mem.append(rec)
            self._hashes.append(digest)
            self._prev = digest
            self._seq += 1
            return rec

    def head(self) -> dict:
        with self._lock:
            return {"seq": self._seq - 1, "hash": self._prev}

    def records(self) -> list:
        with self._lock:
            return list(self._mem)

    def window(self) -> tuple:
        """(anchor, records) for verifying the retained in-memory window after it wrapped."""
        with self._lock:
            return {"prev": self._evicted_tail[0], "seq": self._evicted_tail[1]}, list(self._mem)

    def close(self) -> None:
        if self._fh:
            self._fh.close(); self._fh = None


def verify(records: Iterable[dict], key: bytes, *, expected_head: Optional[dict] = None,
           anchor: Optional[dict] = None) -> dict:
    """Verify a full log (from genesis) or a window starting at ``anchor``.

    An empty input never verifies: deletion of everything must not pass.
    """
    prev, seq = (GENESIS, 0) if anchor is None else (anchor["prev"], anchor["seq"])
    n = 0
    records = list(records)
    if not records:
        return {"ok": False, "at": seq, "why": "empty"}
    if anchor is None and records[0].get("kind") != "genesis":
        return {"ok": False, "at": 0, "why": "missing_genesis"}
    for rec in records:
        body = {k: v for k, v in rec.items() if k != "mac"}
        if rec.get("schema") != AUDIT_SCHEMA:
            return {"ok": False, "at": seq, "why": "schema"}
        if rec.get("seq") != seq:
            return {"ok": False, "at": seq, "why": "sequence_gap"}
        if rec.get("prev") != prev:
            return {"ok": False, "at": seq, "why": "chain_break"}
        if not hmac.compare_digest(hmac.new(key, _canon(body), hashlib.sha256).hexdigest(), str(rec.get("mac"))):
            return {"ok": False, "at": seq, "why": "mac"}
        prev = hashlib.sha256(_canon(rec)).hexdigest()
        seq += 1; n += 1
    if expected_head is not None and (expected_head.get("seq") != seq - 1 or expected_head.get("hash") != prev):
        return {"ok": False, "at": seq, "why": "head_mismatch_truncation"}
    return {"ok": True, "records": n, "head": prev}


def read_jsonl(path: str) -> list:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
