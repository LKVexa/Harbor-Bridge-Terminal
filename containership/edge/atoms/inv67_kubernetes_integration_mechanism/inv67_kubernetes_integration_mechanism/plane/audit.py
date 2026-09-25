"""Tamper-evident security audit trail (item 28).

Append-only JSONL, each record chained by SHA-256 over the canonical previous
record; optional HMAC-SHA256 seal when a key is configured. ``verify`` detects
edits, reordering, deletion in the middle and — because the head digest is
exported to a separate sink — tail truncation. Values named like secrets are
redacted before they are written.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from collections.abc import Iterable
from typing import Any

GENESIS = "0" * 64
_SECRETISH = ("token", "secret", "password", "key", "credential", "authorization")


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if any(s in str(k).lower() for s in _SECRETISH) else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


class AuditLog:
    def __init__(self, path: str | None = None, hmac_key: bytes | None = None, clock=time.time):
        self.path, self.key, self.clock = path, hmac_key, clock
        self.records: list[dict] = []
        self.head = GENESIS
        self._lock = threading.Lock()
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        self.records.append(json.loads(line))
            if self.records:
                self.head = self.records[-1]["digest"]

    def append(self, actor: str, action: str, target: str, outcome: str, **detail) -> dict:
        if not actor or not action:
            raise ValueError("audit records need actor and action")
        with self._lock:
            body = {"seq": len(self.records), "ts": round(self.clock(), 6), "actor": actor, "action": action,
                    "target": target, "outcome": outcome, "detail": redact(detail), "prev": self.head}
            digest = hashlib.sha256(canonical(body)).hexdigest()
            rec = dict(body, digest=digest)
            if self.key:
                rec["hmac"] = hmac.new(self.key, digest.encode(), hashlib.sha256).hexdigest()
            self.records.append(rec)
            self.head = digest
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return rec

    @staticmethod
    def verify(records: Iterable[dict], expected_head: str | None = None, hmac_key: bytes | None = None) -> tuple[bool, str]:
        prev, n = GENESIS, 0
        for i, rec in enumerate(records):
            body = {k: v for k, v in rec.items() if k not in ("digest", "hmac")}
            if body.get("seq") != i:
                return False, f"sequence break at {i}"
            if body.get("prev") != prev:
                return False, f"chain break at {i}"
            if hashlib.sha256(canonical(body)).hexdigest() != rec.get("digest"):
                return False, f"digest mismatch at {i}"
            if hmac_key is not None:
                want = hmac.new(hmac_key, rec["digest"].encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(want, rec.get("hmac", "")):
                    return False, f"hmac mismatch at {i}"
            prev, n = rec["digest"], i + 1
        if expected_head is not None and prev != expected_head:
            return False, f"head mismatch after {n} records (truncation?)"
        return True, f"{n} records verified"
