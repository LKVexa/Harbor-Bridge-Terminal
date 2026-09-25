"""Tamper-evident audit events for INV-72 (C049).

Each event is a PK_ACCEL_AUDIT_EVENT/1 record whose ``hash`` covers its body and the previous event's
hash.  ``verify()`` detects any edit, deletion, insertion or reordering inside the chain.  Truncation of
the *tail* is not detectable from the chain alone, so ``head()`` returns (seq, hash) for the caller to
anchor externally (the release evidence and operator exports record it).  Optional HMAC sealing with a
key supplied by the host binds the chain to a key the attacker must also hold.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from .redaction import redact

GENESIS = "0" * 64
SCHEMA = "PK_ACCEL_AUDIT_EVENT/1"


def _digest(prev: str, body: dict, key: bytes | None) -> str:
    raw = (prev + json.dumps(body, sort_keys=True, separators=(",", ":"))).encode()
    if key:
        return hmac.new(key, raw, hashlib.sha256).hexdigest()
    return hashlib.sha256(raw).hexdigest()


@dataclass
class AuditLog:
    key: bytes | None = None
    clock: Callable[[], float] = time.time
    max_events: int = 100_000
    events: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    dropped_head: int = 0
    _anchor: str = GENESIS

    def emit(self, actor: str, action: str, subject: str, outcome: str, detail: dict | None = None) -> dict:
        with self._lock:
            if len(self.events) >= self.max_events:
                raise OverflowError("audit buffer full; export before continuing")
            prev = self.events[-1]["hash"] if self.events else self._anchor
            seq = (self.events[-1]["seq"] + 1) if self.events else self.dropped_head
            body = {"schema": SCHEMA, "seq": seq, "ts": self.clock(), "actor": str(actor)[:128],
                    "action": action, "subject": str(subject)[:256], "outcome": outcome,
                    "detail": redact(detail or {}), "prev": prev}
            ev = {**body, "hash": _digest(prev, body, self.key)}
            self.events.append(ev)
            return ev

    def head(self) -> tuple[int, str]:
        return (self.events[-1]["seq"], self.events[-1]["hash"]) if self.events else (self.dropped_head - 1, self._anchor)

    def export(self) -> list[dict]:
        """Hand events to durable storage and keep only the head as the new chain anchor."""
        with self._lock:
            out, last = list(self.events), (self.events[-1] if self.events else None)
            self.events.clear()
            if last:
                self.dropped_head = last["seq"] + 1
                self._anchor = last["hash"]
            return out

    @staticmethod
    def verify(events: list[dict], key: bytes | None = None, anchor: str = GENESIS,
               expect_head: tuple[int, str] | None = None) -> list[str]:
        errs, prev = [], anchor
        last_seq = None
        for i, ev in enumerate(events):
            body = {k: v for k, v in ev.items() if k != "hash"}
            if ev.get("prev") != prev:
                errs.append(f"event {i}: prev link broken")
            if _digest(ev.get("prev", ""), body, key) != ev.get("hash"):
                errs.append(f"event {i}: hash mismatch (edited or wrong key)")
            if last_seq is not None and ev.get("seq") != last_seq + 1:
                errs.append(f"event {i}: sequence gap/reorder")
            last_seq, prev = ev.get("seq"), ev.get("hash")
        if expect_head is not None:
            got = (events[-1]["seq"], events[-1]["hash"]) if events else (-1, anchor)
            if tuple(got) != tuple(expect_head):
                errs.append(f"head mismatch: chain ends at {got[0]}, anchor says {expect_head[0]} (tail truncated?)")
        return errs
