"""Tamper-evident audit event sink (component P1-08; C049, C073, C079).

Each record is canonical JSON carrying ``prev`` (hash of the previous record) and
``mac`` = HMAC-SHA256(key, canonical record without mac).  ``verify_chain`` detects
edits, deletions, reordering and insertion; truncation of the tail is detected by
comparing against an externally stored head (``expected_head``) -- a chain alone
cannot see its own tail being cut, so callers MUST persist the head elsewhere.

Fail-closed: if the sink cannot write, ``append`` raises ``PK_AUDIT_UNAVAILABLE``
and the service refuses the security-relevant operation instead of proceeding
unaudited.  Records never carry secrets: details pass through ``redaction``.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time

try:
    from .errors import Inv14Error
    from .redaction import redact
except ImportError:
    from errors import Inv14Error
    from redaction import redact

AUDIT_SCHEMA = "PK_POLL_AUDIT/1"
GENESIS = "0" * 64
EVENT_TYPES = {"poll.refused.foreign_owner", "poll.refused.identity", "poll.refused.policy",
               "poll.refused.admission", "poll.refused.invalid", "poll.deprecated_use",
               "lifecycle.transition", "config.applied", "config.rejected", "migration.transition",
               "poll.cancelled"}
MAX_RECORD_BYTES = 4096


class AuditError(Inv14Error):
    default_code = "PK_AUDIT_UNAVAILABLE"


def _canon(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


class AuditSink:
    def __init__(self, path: str, key: bytes, *, clock=time.time, fsync: bool = False):
        if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
            raise AuditError("audit key must be >= 32 bytes", code="PK_AUDIT_WEAK_KEY")
        self.path, self._key, self._clock, self._fsync = path, bytes(key), clock, fsync
        self._lock = threading.Lock()
        self._head, self._seq = GENESIS, 0
        if os.path.exists(path):
            res = verify_chain(path, key)
            if not res["ok"]:
                raise AuditError("existing audit log fails verification", code="PK_AUDIT_CORRUPT",
                                 details={"error": res["error"], "line": res.get("line")})
            self._head, self._seq = res["head"], res["count"]

    @property
    def head(self) -> str:
        with self._lock:
            return self._head

    def append(self, event: str, *, correlation_id: str, details: dict | None = None) -> dict:
        if event not in EVENT_TYPES:
            raise AuditError("unknown audit event type", code="PK_AUDIT_EVENT_TYPE", details={"event": event})
        with self._lock:
            rec = {"schema": AUDIT_SCHEMA, "seq": self._seq + 1, "ts": round(self._clock(), 6),
                   "event": event, "correlation_id": str(correlation_id)[:64],
                   "details": redact(details or {}), "prev": self._head}
            body = _canon(rec)
            rec["mac"] = hmac.new(self._key, body, hashlib.sha256).hexdigest()
            line = _canon(rec)
            if len(line) > MAX_RECORD_BYTES:
                raise AuditError("audit record too large", code="PK_AUDIT_RECORD_SIZE")
            try:
                with open(self.path, "ab") as fh:
                    fh.write(line + b"\n")
                    if self._fsync:
                        fh.flush()
                        os.fsync(fh.fileno())
            except OSError as exc:
                raise AuditError("audit sink write failed", details={"errno": exc.errno}) from None
            self._head = hashlib.sha256(line).hexdigest()
            self._seq += 1
            return {"seq": rec["seq"], "head": self._head}


def verify_chain(path: str, key: bytes, *, expected_head: str | None = None) -> dict:
    prev, count = GENESIS, 0
    try:
        with open(path, "rb") as fh:
            lines = fh.read().split(b"\n")
    except OSError:
        return {"ok": False, "error": "unreadable", "count": 0, "head": GENESIS}
    if lines and lines[-1] == b"":
        lines.pop()
    for i, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
            mac = rec.pop("mac")
        except Exception:
            return {"ok": False, "error": "malformed", "line": i, "count": count, "head": prev}
        if rec.get("prev") != prev:
            return {"ok": False, "error": "chain_break", "line": i, "count": count, "head": prev}
        if rec.get("seq") != i:
            return {"ok": False, "error": "sequence", "line": i, "count": count, "head": prev}
        if not hmac.compare_digest(hmac.new(key, _canon(rec), hashlib.sha256).hexdigest(), str(mac)):
            return {"ok": False, "error": "mac", "line": i, "count": count, "head": prev}
        prev, count = hashlib.sha256(line).hexdigest(), count + 1
    if expected_head is not None and prev != expected_head:
        return {"ok": False, "error": "head_mismatch", "count": count, "head": prev}
    return {"ok": True, "count": count, "head": prev}
