"""MC-017 - tamper-evident security audit sink for INV-42.

Events from :class:`descriptors.DescriptorTable` are appended to a hash chain:
``entry_hash = SHA-256(prev_hash || canonical_json(event))``.  Optionally each
entry is additionally MACed with an audit key held by the sink operator, so an
attacker who can rewrite the file but not read the key cannot re-forge the
chain.  ``verify()`` detects modification, deletion, reordering and truncation
beyond the recorded head.

Privacy: only fields on an allow-list are kept; bearer material (auth tags,
table ids, keys, resources, wire payloads) is never accepted.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from typing import Iterable

GENESIS = "0" * 64
ALLOWED_FIELDS = frozenset({"schema", "op", "table_fp", "outcome", "number", "type", "duration_ns", "ts",
                            "trace_id", "span_id", "actor", "detail"})
FORBIDDEN_FIELDS = frozenset({"auth", "auth_tag", "table", "table_id", "key", "resource", "wire"})


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sanitize(event: dict) -> dict:
    bad = FORBIDDEN_FIELDS & set(event)
    if bad:
        raise ValueError(f"audit event carries forbidden bearer fields: {sorted(bad)}")
    return {k: v for k, v in event.items() if k in ALLOWED_FIELDS}


class AuditLog:
    """Append-only JSONL hash chain.  Usable directly as a table observer."""

    def __init__(self, path: str, *, mac_key: bytes | None = None, fsync: bool = False):
        self.path = path
        self._mac_key = mac_key
        self._fsync = fsync
        self._lock = threading.Lock()
        self._seq, self._head = 0, GENESIS
        if os.path.exists(path):
            result = verify(path, mac_key=mac_key)
            if not result["ok"]:
                raise ValueError(f"refusing to append to a broken audit chain: {result['error']}")
            self._seq, self._head = result["count"], result["head"]

    @property
    def head(self) -> str:
        return self._head

    def __call__(self, event: dict) -> None:
        self.append(event)

    def append(self, event: dict) -> str:
        body = sanitize(event)
        with self._lock:
            seq = self._seq + 1
            entry_hash = hashlib.sha256(self._head.encode() + _canon({"seq": seq, "event": body})).hexdigest()
            record = {"seq": seq, "prev": self._head, "hash": entry_hash, "event": body}
            if self._mac_key is not None:
                record["mac"] = hmac.new(self._mac_key, entry_hash.encode(), hashlib.sha256).hexdigest()
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
                if self._fsync:
                    fh.flush()
                    os.fsync(fh.fileno())
            self._seq, self._head = seq, entry_hash
            return entry_hash


def verify(path: str, *, mac_key: bytes | None = None, expected_head: str | None = None) -> dict:
    prev, count = GENESIS, 0
    try:
        with open(path, encoding="utf-8") as fh:
            lines: Iterable[str] = fh.read().splitlines()
    except FileNotFoundError:
        return {"ok": expected_head in (None, GENESIS), "count": 0, "head": GENESIS, "error": None}
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            return {"ok": False, "count": count, "head": prev, "error": f"unparseable record after seq {count}"}
        count += 1
        if rec.get("seq") != count or rec.get("prev") != prev:
            return {"ok": False, "count": count, "head": prev, "error": f"chain break at seq {count}"}
        expect = hashlib.sha256(prev.encode() + _canon({"seq": count, "event": rec.get("event")})).hexdigest()
        if not hmac.compare_digest(expect, rec.get("hash", "")):
            return {"ok": False, "count": count, "head": prev, "error": f"hash mismatch at seq {count}"}
        if mac_key is not None:
            mac = hmac.new(mac_key, expect.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, rec.get("mac", "")):
                return {"ok": False, "count": count, "head": prev, "error": f"MAC mismatch at seq {count}"}
        prev = expect
    if expected_head is not None and not hmac.compare_digest(prev, expected_head):
        return {"ok": False, "count": count, "head": prev, "error": "head does not match anchored head (truncation?)"}
    return {"ok": True, "count": count, "head": prev, "error": None}
