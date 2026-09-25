"""Durable operation journal, idempotency registry and audit trail
(components 21, 22, 50; foundation for 7).

The journal is an append-only JSONL file.  Each record carries the SHA-256 of
the previous record, so truncation in the middle or tampering is detected on
open (``JournalCorrupt``); a torn *final* line from a crash is tolerated and
discarded, which is the only loss a crash can cause.  Every write is flushed
and fsynced before the side effect it describes is attempted (write-ahead).
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from .errors import IdempotencyMismatch, JournalCorrupt

GENESIS = "0" * 64
REDACT_KEYS = frozenset({"token", "password", "secret", "authorization", "credential", "private_key", "bearer"})


def redact(value: Any) -> Any:
    """Recursively replace values of secret-bearing keys (component 43)."""
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if any(s in str(k).lower() for s in REDACT_KEYS) else redact(v))
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


@dataclass(frozen=True)
class Entry:
    seq: int
    ts: float
    op_id: str
    kind: str
    phase: str
    data: dict
    prev: str
    hash: str


class Journal:
    def __init__(self, path: str | None = None, *, clock: Callable[[], float] = time.time, fsync: bool = True):
        self.path, self.clock, self.fsync = path, clock, fsync
        self._lock = threading.Lock()
        self.entries: list[Entry] = []
        self.torn_tail = False
        if path and os.path.exists(path):
            self._load()

    def _load(self) -> None:
        prev = GENESIS
        with open(self.path, "r", encoding="utf-8") as fh:  # type: ignore[arg-type]
            lines = fh.read().split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        for i, line in enumerate(lines):
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                if i == len(lines) - 1:
                    self.torn_tail = True
                    break
                raise JournalCorrupt(f"journal line {i + 1} is not JSON") from None
            body = {k: raw[k] for k in ("seq", "ts", "op_id", "kind", "phase", "data", "prev")}
            if raw["prev"] != prev or digest(body) != raw["hash"] or raw["seq"] != i + 1:
                raise JournalCorrupt(f"journal hash chain broken at line {i + 1}", details={"line": i + 1})
            self.entries.append(Entry(**body, hash=raw["hash"]))
            prev = raw["hash"]
        if self.torn_tail:
            self._rewrite()

    def _rewrite(self) -> None:
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for e in self.entries:
                fh.write(canonical(e.__dict__) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)  # type: ignore[arg-type]

    def append(self, op_id: str, kind: str, phase: str, data: dict | None = None) -> Entry:
        with self._lock:
            prev = self.entries[-1].hash if self.entries else GENESIS
            body = {"seq": len(self.entries) + 1, "ts": self.clock(), "op_id": op_id, "kind": kind,
                    "phase": phase, "data": redact(data or {}), "prev": prev}
            entry = Entry(**body, hash=digest(body))
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(canonical(entry.__dict__) + "\n")
                    fh.flush()
                    if self.fsync:
                        os.fsync(fh.fileno())
            self.entries.append(entry)
            return entry

    def for_op(self, op_id: str) -> list[Entry]:
        return [e for e in self.entries if e.op_id == op_id]

    def last_phase(self, op_id: str) -> str | None:
        ops = self.for_op(op_id)
        return ops[-1].phase if ops else None

    def open_operations(self, terminal: frozenset[str]) -> list[str]:
        latest: dict[str, str] = {}
        for e in self.entries:
            latest[e.op_id] = e.phase
        return sorted(op for op, ph in latest.items() if ph not in terminal)

    def verify(self) -> bool:
        prev = GENESIS
        for e in self.entries:
            body = {k: getattr(e, k) for k in ("seq", "ts", "op_id", "kind", "phase", "data", "prev")}
            if e.prev != prev or digest(body) != e.hash:
                return False
            prev = e.hash
        return True

    def __iter__(self) -> Iterator[Entry]:
        return iter(list(self.entries))


class IdempotencyRegistry:
    """Maps client idempotency keys to (request digest, result) (component 22).

    Replaying a key with the same request returns the recorded result without
    re-executing; the same key with a *different* request is refused.
    Records are journaled so they survive restart.
    """

    def __init__(self, journal: Journal, *, ttl: float = 24 * 3600):
        self.journal, self.ttl = journal, ttl
        self._lock = threading.Lock()
        self._results: dict[str, tuple[str, Any, float]] = {}
        for e in journal:
            if e.kind == "idempotency" and e.phase == "recorded":
                self._results[e.op_id] = (e.data["request"], e.data.get("result"), e.ts)

    def execute(self, key: str, request: Any, fn: Callable[[], Any]) -> tuple[Any, bool]:
        """Return (result, replayed)."""
        if not isinstance(key, str) or not (8 <= len(key) <= 128):
            raise IdempotencyMismatch("idempotency key must be a string of 8..128 characters")
        req = digest(request)
        with self._lock:
            hit = self._results.get(key)
            if hit and self.journal.clock() - hit[2] <= self.ttl:
                if hit[0] != req:
                    raise IdempotencyMismatch("idempotency key reused with a different request",
                                              details={"key_prefix": key[:8]})
                return hit[1], True
            result = fn()
            self.journal.append(key, "idempotency", "recorded", {"request": req, "result": result})
            self._results[key] = (req, result, self.journal.clock())
            return result, False


class AuditTrail:
    """Authenticated operator/action ledger (component 50) on the hash-chained journal."""

    def __init__(self, journal: Journal):
        self.journal = journal

    def record(self, *, actor: str, action: str, target: str, outcome: str, reason: str = "",
               tenant: str = "", extra: dict | None = None) -> Entry:
        if not actor:
            raise JournalCorrupt("audit records require an authenticated actor")
        return self.journal.append(f"audit:{action}:{target}", "audit", outcome,
                                   {"actor": actor, "action": action, "target": target, "reason": reason,
                                    "tenant": tenant, **(extra or {})})

    def query(self, *, actor: str | None = None, action: str | None = None) -> list[Entry]:
        return [e for e in self.journal if e.kind == "audit"
                and (actor is None or e.data.get("actor") == actor)
                and (action is None or e.data.get("action") == action)]
