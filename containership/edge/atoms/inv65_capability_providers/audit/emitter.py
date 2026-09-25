"""Tamper-evident security audit events (M18).

Append-only, SHA-256 hash-chained PK_AUDIT_EVENT/1 records, optionally mirrored
to a JSONL file (fsync per event).  Fields are bounded and scrubbed: secret
values never appear (only refs).  ``audit/verification.py`` re-derives the chain.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time

from ..schemas import check

GENESIS = "0" * 64


def _digest(ev: dict) -> str:
    body = {k: v for k, v in ev.items() if k != "digest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AuditLog:
    def __init__(self, path: str | None = None):
        self._events: list[dict] = []
        self._lock = threading.Lock()
        self._path = path
        if path and os.path.exists(path):
            from .verification import verify_file
            ok, events, err = verify_file(path)
            if not ok:
                raise RuntimeError(f"existing audit log failed verification: {err}")
            self._events = events

    @property
    def head(self) -> str:
        return self._events[-1]["digest"] if self._events else GENESIS

    def emit(self, action: str, outcome: str, actor: str, subject: str, reason: str = "") -> dict:
        with self._lock:
            ev = {"schema": "PK_AUDIT_EVENT/1", "seq": len(self._events), "ts": round(time.time(), 6),
                  "action": action, "outcome": outcome, "actor": actor[:512], "subject": subject[:512],
                  "prev": self.head}
            if reason:
                ev["reason"] = reason[:256]
            ev["digest"] = _digest(ev)
            check(ev, "audit_event")
            if self._path:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(ev, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            self._events.append(ev)
            return ev

    def events(self) -> list[dict]:
        with self._lock:
            return [dict(e) for e in self._events]
