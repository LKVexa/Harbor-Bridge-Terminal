"""Tamper-evident security audit trail (MC-039).

Each record carries ``seq``, ``prev`` (hash of the previous record) and
``mac`` = HMAC-SHA256(audit key, canonical record without mac).  Truncation,
reordering, insertion, deletion and edits are detected by :func:`verify`.
Records never contain credentials or secret values (fields are allow-listed).
The sink is append-only JSON Lines; an in-memory sink is used in tests.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from pathlib import Path
from typing import Any
from collections.abc import Iterable

GENESIS = "0" * 64
ALLOWED_FIELDS = frozenset({
    "ts", "event", "subject", "role", "tenant", "op", "outcome", "code", "request_id", "target",
    "revision", "config_generation", "decision_id", "term", "reason", "release",
})


def _canon(record: dict[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode()


class AuditTrail:
    def __init__(self, key: bytes, path: str | os.PathLike[str] | None = None, *, fsync: bool = False):
        if len(key) < 32:
            raise ValueError("audit key must be >= 32 bytes")
        self._key = key
        self._path = Path(path) if path else None
        self._fsync = fsync
        self._lock = threading.Lock()
        self.records: list[dict[str, Any]] = []
        self._seq = 0
        self._prev = GENESIS
        if self._path and self._path.exists():
            existing = [json.loads(line) for line in self._path.read_text().splitlines() if line.strip()]
            ok, problem = verify(existing, key)
            if not ok:
                raise ValueError(f"existing audit trail failed verification: {problem}")
            self.records = existing
            if existing:
                self._seq = existing[-1]["seq"]
                self._prev = _digest(existing[-1])

    def append(self, event: str, **fields: Any) -> dict[str, Any]:
        clean = {k: v for k, v in fields.items() if k in ALLOWED_FIELDS and v is not None}
        dropped = sorted(set(fields) - ALLOWED_FIELDS)
        with self._lock:
            self._seq += 1
            record: dict[str, Any] = {"seq": self._seq, "prev": self._prev, "event": event, **clean}
            if dropped:
                record["dropped_fields"] = dropped
            record["mac"] = hmac.new(self._key, _canon(record), hashlib.sha256).hexdigest()
            self._prev = _digest(record)
            self.records.append(record)
            if self._path:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, sort_keys=True) + "\n")
                    if self._fsync:
                        fh.flush()
                        os.fsync(fh.fileno())
        return record

    def head(self) -> tuple[int, str]:
        with self._lock:
            return self._seq, self._prev


def _digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(_canon(record)).hexdigest()


def verify(records: Iterable[dict[str, Any]], key: bytes, *, expected_head: tuple[int, str] | None = None) -> tuple[bool, str]:
    prev = GENESIS
    seq = 0
    last: dict[str, Any] | None = None
    for record in records:
        seq += 1
        body = {k: v for k, v in record.items() if k != "mac"}
        mac = hmac.new(key, _canon(body), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(mac, str(record.get("mac", ""))):
            return False, f"mac mismatch at seq {record.get('seq')}"
        if record.get("seq") != seq:
            return False, f"sequence gap: expected {seq}, found {record.get('seq')}"
        if record.get("prev") != prev:
            return False, f"chain break at seq {seq}"
        prev = _digest(record)
        last = record
    if expected_head is not None and (seq, prev) != tuple(expected_head):
        return False, f"head mismatch (truncation?): have ({seq}, {prev[:12]}…)"
    del last
    return True, "ok"
