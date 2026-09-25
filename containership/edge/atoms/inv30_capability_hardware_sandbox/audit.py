# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Tamper-evident security audit ledger (GAP-029).

Each event is canonical JSON chained by SHA-256 over (prev_hash, body) and,
when a key is configured, authenticated with HMAC-SHA256. ``verify`` detects
edits, deletions, reordering and truncation-with-reappend. File sink is
append-only JSON Lines, fsynced per event.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path

GENESIS = "0" * 64
SCHEMA = "INV30_AUDIT/1"


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


class AuditLedger:
    def __init__(self, path: str | Path | None = None, *, key: bytes | None = None, clock=time.time):
        self.path = Path(path) if path else None
        self.key = key
        self.clock = clock
        self._lock = threading.Lock()
        self.events: list[dict] = []
        if self.path and self.path.exists():
            self.events = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    @property
    def head(self) -> str:
        return self.events[-1]["hash"] if self.events else GENESIS

    def append(self, action: str, outcome: str, **fields) -> dict:
        with self._lock:
            body = {"schema": SCHEMA, "seq": len(self.events), "ts": round(self.clock(), 6),
                    "action": action, "outcome": outcome, "fields": fields, "prev": self.head}
            h = hashlib.sha256(_canon(body)).hexdigest()
            event = dict(body, hash=h)
            if self.key:
                event["mac"] = hmac.new(self.key, h.encode(), hashlib.sha256).hexdigest()
            self.events.append(event)
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return event

    def verify(self, *, expected_head: str | None = None) -> list[str]:
        defects, prev = [], GENESIS
        for i, ev in enumerate(self.events):
            body = {k: v for k, v in ev.items() if k not in ("hash", "mac")}
            if ev.get("seq") != i:
                defects.append(f"event {i}: sequence {ev.get('seq')} out of order")
            if ev.get("prev") != prev:
                defects.append(f"event {i}: chain break")
            h = hashlib.sha256(_canon(body)).hexdigest()
            if h != ev.get("hash"):
                defects.append(f"event {i}: hash mismatch (edited)")
            if self.key:
                mac = hmac.new(self.key, ev.get("hash", "").encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(mac, ev.get("mac", "")):
                    defects.append(f"event {i}: MAC invalid")
            prev = ev.get("hash")
        if expected_head is not None and self.head != expected_head:
            defects.append("head does not match the externally anchored head (truncation or fork)")
        return defects
