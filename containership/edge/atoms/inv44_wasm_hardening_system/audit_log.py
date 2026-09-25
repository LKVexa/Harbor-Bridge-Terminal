"""Tamper-evident security audit log for INV-44 (missing component 14; C049).

Append-only JSON-lines file. Each record carries ``seq``, ``prev`` (the
previous record's hash) and ``hash`` = SHA-256 over the canonical record
without ``hash``. Optionally each record is HMAC-authenticated.

A hash chain alone cannot detect *tail truncation* (dropping the last N
records leaves a valid shorter chain). ``head()`` returns ``(seq, hash)`` for
the caller to anchor externally; ``verify(expected_head=...)`` then detects
truncation. Where the anchor lives is an operations decision (RUNBOOK.md).

Records must not carry secrets: keys matching ``REDACT_KEYS`` are replaced by
``"[REDACTED]"`` before hashing, so the chain never commits to secret bytes.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path
from typing import Mapping

from .errors import HardeningError

GENESIS = "0" * 64
REDACT_KEYS = frozenset({"secret", "token", "key", "password", "mac_key", "credential"})


class AuditChainBroken(HardeningError):
    code = "WH-AUDIT-CHAIN-BROKEN"


def _canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _redact(value: object) -> object:
    if isinstance(value, Mapping):
        return {k: ("[REDACTED]" if str(k).lower() in REDACT_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    return value


class AuditLog:
    def __init__(self, path: str | os.PathLike, *, mac_key: bytes | None = None,
                 clock=time.time) -> None:
        self.path = Path(path)
        self._mac_key = mac_key
        self._clock = clock
        self._lock = threading.Lock()
        self._seq, self._prev = self._scan_tail()

    def _scan_tail(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, GENESIS
        seq, prev = 0, GENESIS
        for rec in self._records():
            seq, prev = rec["seq"], rec["hash"]
        return seq, prev

    def _records(self):
        with self.path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AuditChainBroken("unparseable audit record", line=lineno) from exc

    def append(self, event: str, *, actor: str, tenant: str | None = None,
               outcome: str, **detail: object) -> dict:
        with self._lock:
            rec = {
                "seq": self._seq + 1,
                "ts": round(float(self._clock()), 6),
                "event": event,
                "actor": actor,
                "tenant": tenant,
                "outcome": outcome,
                "detail": _redact(detail),
                "prev": self._prev,
            }
            if self._mac_key is not None:
                rec["mac"] = hmac.new(self._mac_key, _canon(rec), hashlib.sha256).hexdigest()
            rec["hash"] = hashlib.sha256(_canon(rec)).hexdigest()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._seq, self._prev = rec["seq"], rec["hash"]
            return rec

    def head(self) -> tuple[int, str]:
        with self._lock:
            return self._seq, self._prev

    def verify(self, *, expected_head: tuple[int, str] | None = None) -> int:
        """Return the record count, or raise :class:`AuditChainBroken`."""
        prev, seq = GENESIS, 0
        if self.path.exists():
            for rec in self._records():
                claimed = rec.get("hash")
                body = {k: v for k, v in rec.items() if k != "hash"}
                if rec.get("seq") != seq + 1:
                    raise AuditChainBroken("sequence gap or reorder", at=seq + 1)
                if rec.get("prev") != prev:
                    raise AuditChainBroken("prev-hash mismatch", at=rec.get("seq"))
                if hashlib.sha256(_canon(body)).hexdigest() != claimed:
                    raise AuditChainBroken("record hash mismatch", at=rec.get("seq"))
                if self._mac_key is not None:
                    mac = body.pop("mac", None)
                    want = hmac.new(self._mac_key, _canon(body), hashlib.sha256).hexdigest()
                    if mac is None or not hmac.compare_digest(mac, want):
                        raise AuditChainBroken("record MAC mismatch", at=rec.get("seq"))
                prev, seq = claimed, rec["seq"]
        if expected_head is not None and (seq, prev) != tuple(expected_head):
            raise AuditChainBroken("chain head does not match external anchor (truncation?)",
                                   have=seq, want=expected_head[0])
        return seq
