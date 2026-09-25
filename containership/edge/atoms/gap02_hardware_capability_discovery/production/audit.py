"""GAP02-MC-34 — Tamper-evident audit stream (hash chain, append-only JSONL).

Each record carries ``prev`` (hash of previous record) and ``hash``. The head
hash must be exported (e.g. into each signed envelope or to GAP-07) because a
hash chain alone cannot detect tail truncation.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time

GENESIS = "0" * 64


def _h(rec: dict) -> str:
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AuditLog:
    def __init__(self, path: str, clock=lambda: int(time.time())):
        self.path, self.clock = path, clock
        self._lock = threading.Lock()
        self.head, self.count = GENESIS, 0
        if os.path.exists(path):
            ok, head, n, _ = verify(path)
            if not ok:
                raise RuntimeError("audit log failed verification on open")
            self.head, self.count = head, n

    def append(self, kind: str, data: dict) -> str:
        with self._lock:
            rec = {"seq": self.count + 1, "ts": self.clock(), "kind": kind, "data": data, "prev": self.head}
            rec["hash"] = _h(rec)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
            self.head, self.count = rec["hash"], rec["seq"]
            return rec["hash"]

    def __call__(self, kind: str, data: dict) -> None:
        self.append(kind, data)


def verify(path: str, expected_head: str | None = None) -> tuple[bool, str, int, str]:
    prev, n = GENESIS, 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                return False, prev, n, f"line {n + 1} not JSON"
            h = rec.pop("hash", None)
            if rec.get("prev") != prev or _h(rec) != h or rec.get("seq") != n + 1:
                return False, prev, n, f"chain broken at seq {n + 1}"
            prev, n = h, n + 1
    if expected_head is not None and prev != expected_head:
        return False, prev, n, "head mismatch (truncation or rewrite)"
    return True, prev, n, ""
