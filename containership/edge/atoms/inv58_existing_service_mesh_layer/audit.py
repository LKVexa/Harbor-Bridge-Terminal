"""Tamper-evident security audit trail (MC-015, INV-58-C049).

Events are structured (``PK_MESH_AUDIT/1``), hash-chained (each record carries
the SHA-256 of its predecessor) and sealed with HMAC-SHA256 under a key obtained
through a :class:`~.secret_refs.SecretResolver` reference, never from configuration
text.  ``verify_chain`` detects modification, deletion, reordering and
insertion.  Retention in memory is bounded; when the bound is reached the
oldest records are *checkpointed* (their head hash is kept) so verification of
the retained suffix still anchors to a known prior head.  An optional
append-only JSONL sink provides durable retention.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable, Iterable

AUDIT_SCHEMA = "PK_MESH_AUDIT/1"
GENESIS = "0" * 64
DEFAULT_MAX_RECORDS = 10_000
_MAX_FIELD = 512

EVENT_TYPES = frozenset({
    "authz.decision", "identity.mapped", "identity.rejected", "bypass.detected",
    "route.migrated", "route.rejected", "config.validated", "config.rejected",
    "config.activated", "config.rolled_back", "control.freeze", "control.unfreeze",
    "control.quarantine", "control.break_glass", "integrity.failure",
    "lifecycle.transition", "fence.rejected", "state.restored", "audit.export",
})


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _clip(v: Any) -> Any:
    if isinstance(v, str):
        return v[:_MAX_FIELD]
    if isinstance(v, (int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_clip(x) for x in list(v)[:32]]
    if isinstance(v, dict):
        return {str(k)[:64]: _clip(x) for k, x in list(v.items())[:32]}
    return str(v)[:_MAX_FIELD]


@dataclass
class AuditLog:
    key: bytes
    max_records: int = DEFAULT_MAX_RECORDS
    sink_path: str | None = None
    clock: Callable[[], float] = time.time
    _records: list[dict] = field(default_factory=list, init=False, repr=False)
    _head: str = field(default=GENESIS, init=False)
    _anchor: str = field(default=GENESIS, init=False)
    _seq: int = field(default=0, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.key, (bytes, bytearray)) or len(self.key) < 16:
            raise ValueError("audit key must be >= 16 bytes of resolved secret material")
        if isinstance(self.max_records, bool) or not isinstance(self.max_records, int) or self.max_records < 1:
            raise ValueError("max_records must be a positive integer")

    def emit(self, event_type: str, *, actor: str | None, tenant: str | None, target: str | None,
             decision: str, reason: str, correlation_id: str | None = None,
             policy_version: str | None = None, attrs: dict | None = None) -> dict:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown audit event type {event_type!r}")
        with self._lock:
            self._seq += 1
            body = {
                "schema": AUDIT_SCHEMA, "seq": self._seq, "ts": round(self.clock(), 6),
                "type": event_type, "actor": _clip(actor), "tenant": _clip(tenant),
                "target": _clip(target), "decision": _clip(decision), "reason": _clip(reason),
                "correlation_id": _clip(correlation_id), "policy_version": _clip(policy_version),
                "attrs": _clip(attrs or {}), "prev": self._head,
            }
            digest = hashlib.sha256(_canon(body)).hexdigest()
            rec = dict(body, hash=digest, mac=hmac.new(bytes(self.key), digest.encode(), hashlib.sha256).hexdigest())
            self._records.append(rec)
            self._head = digest
            overflow = len(self._records) - self.max_records
            if overflow > 0:
                self._anchor = self._records[overflow - 1]["hash"]
                del self._records[:overflow]
            if self.sink_path:
                fd = os.open(self.sink_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                try:
                    os.write(fd, _canon(rec) + b"\n")
                finally:
                    os.close(fd)
            return dict(rec)

    @property
    def head(self) -> str:
        with self._lock:
            return self._head

    def records(self) -> tuple[dict, ...]:
        with self._lock:
            return tuple(dict(r) for r in self._records)

    def anchor(self) -> str:
        with self._lock:
            return self._anchor

    def verify(self) -> tuple[bool, str]:
        with self._lock:
            return verify_chain(self._records, self.key, anchor=self._anchor)


def verify_chain(records: Iterable[dict], key: bytes, anchor: str = GENESIS) -> tuple[bool, str]:
    """Return (ok, reason).  Detects edits, deletions, insertions and reorders."""
    prev = anchor
    last_seq = None
    for i, rec in enumerate(records):
        rec = dict(rec)
        mac = rec.pop("mac", None)
        digest = rec.pop("hash", None)
        if rec.get("schema") != AUDIT_SCHEMA:
            return False, f"record {i}: wrong schema"
        if rec.get("prev") != prev:
            return False, f"record {i}: chain break"
        if last_seq is not None and rec.get("seq") != last_seq + 1:
            return False, f"record {i}: sequence gap"
        if hashlib.sha256(_canon(rec)).hexdigest() != digest:
            return False, f"record {i}: content hash mismatch"
        expect = hmac.new(bytes(key), str(digest).encode(), hashlib.sha256).hexdigest()
        if not isinstance(mac, str) or not hmac.compare_digest(mac, expect):
            return False, f"record {i}: seal mismatch"
        prev, last_seq = digest, rec["seq"]
    return True, "ok"


def load_jsonl(path: str) -> list[dict]:
    with open(path, "rb") as fh:
        return [json.loads(line) for line in fh if line.strip()]
