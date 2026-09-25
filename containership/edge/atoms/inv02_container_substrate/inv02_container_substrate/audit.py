"""MC31 — tamper-evident audit ledger.

Append-only JSON-lines file where each record carries ``prev`` (hash of the previous
record) and ``mac`` (HMAC-SHA256 over the canonical record under a ledger key).  Any
edit, deletion, reorder or truncation-with-rewrite breaks :func:`verify_ledger`.
Anchoring the head hash externally (release evidence, remote log) detects tail
truncation as well.  Secret-looking fields are redacted before writing.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from pathlib import Path

from .observability import redact
from .timeutil import Clock, SystemClock

GENESIS = "0" * 64


class AuditTampered(Exception):
    code = "AUDIT_TAMPERED"


def _canon(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


class AuditLedger:
    def __init__(self, path: str | os.PathLike, key: bytes, *, clock: Clock | None = None) -> None:
        if len(key) < 32:
            raise ValueError("audit key must be at least 32 bytes")
        self.path = Path(path)
        self._key = key
        self.clock = clock or SystemClock()
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
            os.close(fd)
        self._head, self._seq = self._scan_head()

    def _scan_head(self) -> tuple[str, int]:
        head, seq = GENESIS, 0
        with open(self.path, "rb") as fh:
            for line in fh:
                rec = json.loads(line)
                head, seq = rec["hash"], rec["seq"]
        return head, seq

    def append(self, event: str, fields: dict, *, actor: str = "system", correlation_id: str | None = None) -> dict:
        with self._lock:
            body = {"seq": self._seq + 1, "at": self.clock.now(), "event": event, "actor": actor,
                    "correlation_id": correlation_id, "fields": redact(fields), "prev": self._head}
            h = hashlib.sha256(_canon(body)).hexdigest()
            rec = dict(body, hash=h, mac=hmac.new(self._key, h.encode(), hashlib.sha256).hexdigest())
            with open(self.path, "ab") as fh:
                fh.write(_canon(rec) + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._head, self._seq = h, body["seq"]
            return rec

    @property
    def head(self) -> str:
        return self._head

    def sink(self):
        """Adapter usable as ``ContentStore(audit=ledger.sink())``."""
        return lambda event, fields: self.append(event, fields)


def verify_ledger(path: str | os.PathLike, key: bytes, *, expected_head: str | None = None) -> int:
    prev, seq = GENESIS, 0
    with open(path, "rb") as fh:
        for n, line in enumerate(fh, 1):
            try:
                rec = json.loads(line)
            except ValueError as exc:
                raise AuditTampered(f"line {n}: not JSON") from exc
            body = {k: rec[k] for k in ("seq", "at", "event", "actor", "correlation_id", "fields", "prev")}
            h = hashlib.sha256(_canon(body)).hexdigest()
            if rec["prev"] != prev or rec["seq"] != seq + 1:
                raise AuditTampered(f"line {n}: chain broken")
            if h != rec["hash"]:
                raise AuditTampered(f"line {n}: content hash mismatch")
            if not hmac.compare_digest(rec["mac"], hmac.new(key, h.encode(), hashlib.sha256).hexdigest()):
                raise AuditTampered(f"line {n}: MAC invalid")
            prev, seq = h, rec["seq"]
    if expected_head is not None and prev != expected_head:
        raise AuditTampered("ledger head does not match anchored head (truncation?)")
    return seq
