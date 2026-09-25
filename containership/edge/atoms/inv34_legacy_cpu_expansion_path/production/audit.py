"""Tamper-evident audit chain (MC-034). SPDX-License-Identifier: NOASSERTION

Append-only JSONL; each record carries ``prev`` (sha256 of the previous line)
and an HMAC over its canonical body with a key the writer holds.  ``verify``
detects edits, deletions in the middle, reordering and forged records.  Tail
truncation is only detectable against an externally recorded head, so
``head()`` is exported for anchoring elsewhere (known blind spot, stated).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

EVENTS = ("request.received", "authn.failed", "authz.denied", "request.accepted", "request.rejected",
          "adapter.action", "adapter.outcome", "observation.accepted", "observation.rejected",
          "ops.disable", "ops.enable", "config.activated", "config.rolled_back", "lease.acquired",
          "reconcile.ambiguous")
GENESIS = "0" * 64


class AuditChain:
    def __init__(self, path: str | os.PathLike, key: bytes) -> None:
        self.path = Path(path)
        self._key = key
        self._lock = threading.Lock()
        self._prev = self._tail_hash()

    def _tail_hash(self) -> str:
        if not self.path.exists():
            return GENESIS
        last = None
        with open(self.path, "rb") as fh:
            for line in fh:
                if line.strip():
                    last = line.rstrip(b"\n")
        return hashlib.sha256(last).hexdigest() if last else GENESIS

    def append(self, event: str, **fields: Any) -> dict:
        if event not in EVENTS:
            raise ValueError(f"unknown audit event {event}")
        with self._lock:
            body = {"event": event, "ts": time.time(), "prev": self._prev, **fields}
            canon = json.dumps(body, sort_keys=True, separators=(",", ":"))
            body["mac"] = hmac.new(self._key, canon.encode(), hashlib.sha256).hexdigest()
            line = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            with open(self.path, "ab") as fh:
                fh.write(line + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._prev = hashlib.sha256(line).hexdigest()
            return body

    def head(self) -> str:
        return self._prev

    @staticmethod
    def verify(path: str | os.PathLike, key: bytes, expected_head: str | None = None) -> tuple[bool, str]:
        prev, n = GENESIS, 0
        p = Path(path)
        if not p.exists():
            return (expected_head in (None, GENESIS), "empty")
        for raw in p.read_bytes().splitlines():
            if not raw.strip():
                continue
            n += 1
            try:
                rec = json.loads(raw)
            except ValueError:
                return False, f"record {n}: not JSON"
            mac = rec.pop("mac", None)
            if rec.get("prev") != prev:
                return False, f"record {n}: chain break"
            canon = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            if not isinstance(mac, str) or not hmac.compare_digest(
                    mac, hmac.new(key, canon.encode(), hashlib.sha256).hexdigest()):
                return False, f"record {n}: bad MAC"
            prev = hashlib.sha256(raw).hexdigest()
        if expected_head is not None and prev != expected_head:
            return False, "head mismatch (tail truncated or extended)"
        return True, f"{n} records verified"
