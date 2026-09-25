"""Tamper-evident, hash-chained security audit events (MC-034).

Each event carries ``prev`` (hash of the previous event) and ``hash`` (SHA-256 of
its canonical body).  An optional HMAC seal key makes the chain unforgeable by a
party without the key.  Sinks are append-only JSON-lines files or memory.
Payloads and secret values are never recorded - only structural metadata.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from collections import deque
from typing import Callable, Iterable

GENESIS = "0" * 64
EVENT_SCHEMA = "pk.audit-event/1"
ACTIONS = {"state.read", "state.write", "state.delete", "state.transact", "message.publish",
           "message.subscribe", "secret.access", "invoke", "deny", "lifecycle", "config.activate",
           "config.rollback", "quarantine", "failover", "artifact.verify"}


class AuditLog:
    def __init__(self, path: str | None = None, seal_key: bytes | None = None, max_memory: int = 100_000,
                 clock: Callable[[], float] = time.time):
        self.path, self.seal_key, self.clock = path, seal_key, clock
        self.events: deque[dict] = deque(maxlen=max_memory)
        self._prev = GENESIS
        self._seq = 0
        self._lock = threading.Lock()
        if path and os.path.exists(path):
            for ev in read_jsonl(path):
                self._prev, self._seq = ev["hash"], ev["seq"]

    def emit(self, action: str, *, workload: str, tenant: str | None, outcome: str, **meta: object) -> dict:
        if action not in ACTIONS:
            raise ValueError(f"unknown audit action {action}")
        with self._lock:
            self._seq += 1
            body = {"schema": EVENT_SCHEMA, "seq": self._seq, "ts": round(self.clock(), 6), "action": action,
                    "workload": workload, "tenant": tenant, "outcome": outcome,
                    "meta": {k: str(v)[:256] for k, v in sorted(meta.items())}, "prev": self._prev}
            raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            body["hash"] = hashlib.sha256(raw).hexdigest()
            if self.seal_key:
                body["seal"] = hmac.new(self.seal_key, raw, hashlib.sha256).hexdigest()
            self._prev = body["hash"]
            self.events.append(body)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(body, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return body


def read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def verify_chain(events: Iterable[dict], seal_key: bytes | None = None) -> tuple[bool, str]:
    prev, seq = GENESIS, 0
    for ev in events:
        ev = dict(ev)
        h, seal = ev.pop("hash", None), ev.pop("seal", None)
        raw = json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()
        if ev.get("prev") != prev:
            return False, f"chain break at seq {ev.get('seq')}"
        if ev.get("seq") != seq + 1:
            return False, f"sequence gap at seq {ev.get('seq')}"
        if hashlib.sha256(raw).hexdigest() != h:
            return False, f"hash mismatch at seq {ev.get('seq')}"
        if seal_key is not None and not (seal and hmac.compare_digest(
                hmac.new(seal_key, raw, hashlib.sha256).hexdigest(), seal)):
            return False, f"seal mismatch at seq {ev.get('seq')}"
        prev, seq = h, ev["seq"]
    return True, "ok"
