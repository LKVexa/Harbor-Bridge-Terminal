"""Tamper-evident audit log for PLN-05 security-sensitive actions (``PK_AUDIT/1``).

Each record carries ``seq`` and ``prev`` (hash of the previous record) and its
own ``hash``; :meth:`AuditLog.anchor` HMAC-signs the head so truncation of the
tail is also detectable (a hash chain alone cannot see a cut tail).

Sink outage policy: records queue in a bounded buffer while the sink is down.
When the buffer is full the log *refuses* the triggering action
(``E_AUDIT_UNAVAILABLE``) instead of performing it unaudited; data-path demand
events are not security-sensitive and are not blocked by audit pressure.
"""
from __future__ import annotations

from collections import deque
import hashlib
import json
import os
import pathlib
import uuid

from .errors import PlaneError
from .keys import KeyRing

AUDIT_SCHEMA = "PK_AUDIT/1"
GENESIS = "0" * 64
FIELDS = ("schema", "seq", "event_id", "ts", "actor", "actor_class", "tenant", "site",
          "action", "result", "reason_code", "correlation_id", "object_revision", "prev")


def _digest(rec: dict) -> str:
    body = {k: rec.get(k) for k in FIELDS}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AuditLog:
    def __init__(self, ring: KeyRing, path: str | os.PathLike | None = None,
                 buffer_capacity: int = 256, retain: int = 4096) -> None:
        self.ring = ring
        self.path = pathlib.Path(path) if path else None
        # In-memory window is bounded (the soak leak detector found the unbounded list);
        # the durable sink (``path``) holds the full chain.  ``window_start`` lets a
        # verifier check the retained window against the anchor.
        self.records: deque = deque(maxlen=retain)
        self.window_start = (0, GENESIS)
        self.pending: list[dict] = []
        self.buffer_capacity = buffer_capacity
        self.sink_available = True
        self.refused = 0
        self._head = GENESIS
        self._seq = 0

    @property
    def pressure(self) -> float:
        return len(self.pending) / self.buffer_capacity

    def ensure_capacity(self) -> None:
        """Pre-check so an authority change is refused *before* it is applied, never applied unaudited."""
        if not self.sink_available and len(self.pending) >= self.buffer_capacity:
            self.refused += 1
            raise PlaneError("E_AUDIT_UNAVAILABLE", "audit buffer full; action refused")

    def append(self, *, actor: str, actor_class: str, tenant: str, site: str, action: str,
               result: str, reason_code: str, now: float, correlation_id: str | None = None,
               object_revision: str | int | None = None) -> dict:
        if not self.sink_available and len(self.pending) >= self.buffer_capacity:
            self.refused += 1
            raise PlaneError("E_AUDIT_UNAVAILABLE", "audit buffer full; action refused")
        self._seq += 1
        rec = {
            "schema": AUDIT_SCHEMA, "seq": self._seq, "event_id": uuid.uuid4().hex, "ts": now,
            "actor": actor, "actor_class": actor_class, "tenant": tenant, "site": site,
            "action": action, "result": result, "reason_code": reason_code,
            "correlation_id": correlation_id, "object_revision": object_revision,
            "prev": self._head,
        }
        rec["hash"] = _digest(rec)
        self._head = rec["hash"]
        if self.sink_available:
            self._flush()
            self._write(rec)
        else:
            self.pending.append(rec)
        return rec

    def _write(self, rec: dict) -> None:
        if len(self.records) == self.records.maxlen:
            old = self.records[0]
            self.window_start = (old["seq"], old["hash"])
        self.records.append(rec)
        if self.path is not None:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())

    def _flush(self) -> None:
        while self.pending:
            self._write(self.pending.pop(0))

    def set_sink(self, available: bool) -> None:
        self.sink_available = available
        if available:
            self._flush()

    def anchor(self, now: float) -> dict:
        data = f"{self._seq}:{self._head}".encode()
        kid, mac = self.ring.sign(data, now)
        return {"seq": self._seq, "head": self._head, "kid": kid, "mac": mac}

    @staticmethod
    def verify(records, anchor: dict | None, ring: KeyRing, now: float,
               start: tuple = (0, GENESIS)) -> dict:
        """Return ``{"ok": bool, "problems": [...]}``; detects edit, gap, reorder, truncation.

        ``start`` is ``(seq, hash)`` of the record preceding ``records[0]`` (genesis by default)."""
        problems: list[str] = []
        records = list(records)
        prev = start[1]
        for i, rec in enumerate(records, start=start[0] + 1):
            if rec.get("seq") != i:
                problems.append(f"sequence break at position {i}")
                break
            if rec.get("prev") != prev:
                problems.append(f"chain break at seq {i}")
                break
            if _digest(rec) != rec.get("hash"):
                problems.append(f"record {i} altered")
                break
            prev = rec["hash"]
        if anchor is not None and not problems:
            try:
                ring.verify(anchor["kid"], f"{anchor['seq']}:{anchor['head']}".encode(),
                            anchor["mac"], now)
            except PlaneError:
                problems.append("anchor signature invalid")
            else:
                if anchor["seq"] != start[0] + len(records) or anchor["head"] != prev:
                    problems.append("tail truncated or extended relative to anchor")
        return {"ok": not problems, "problems": problems, "records": len(records)}
