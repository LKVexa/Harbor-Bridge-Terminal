"""Tamper-evident security audit ledger (component 14).

Append-only JSON-lines file; each entry carries ``prev`` (hash of the previous
entry) and ``hash`` = sha256(canonical(entry-without-hash)).  ``verify``
recomputes the chain.  A hash chain alone cannot detect *tail truncation*, so
``head()`` returns (count, last_hash) which operators must anchor externally
(evidence ledger / release record); ``verify(expected_head=...)`` then detects
truncation too.  Payloads are filtered through ``policy.scrub`` so secrets and
raw credentials never land in the ledger.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any

from .canonical import canonicalize
from .errors import Corrupted

GENESIS = "0" * 64
_SECRET_KEYS = ("secret", "password", "token", "private", "credential", "key_material", "signature")


def _scrub(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "<depth-limit>"
    if isinstance(obj, dict):
        return {k: ("<redacted>" if any(s in k.lower() for s in _SECRET_KEYS) else _scrub(v, depth + 1))
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub(v, depth + 1) for v in obj]
    if isinstance(obj, float):
        return obj
    return obj


class AuditLedger:
    def __init__(self, path: str | None = None, *, clock=None) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._entries: list[dict] = []
        self._clock = clock or (lambda: 0)
        if path and os.path.exists(path):
            self._entries = self._load(path)

    @staticmethod
    def _load(path: str) -> list[dict]:
        out = []
        with open(path, "r", encoding="utf-8") as fh:
            for n, line in enumerate(fh):
                if not line.endswith("\n"):
                    raise Corrupted("audit ledger has a torn final line", line=n)
                try:
                    out.append(json.loads(line))
                except ValueError as exc:
                    raise Corrupted("audit ledger line is not JSON", line=n) from exc
        return out

    def append(self, kind: str, payload: dict, *, actor: str) -> dict:
        with self._lock:
            prev = self._entries[-1]["hash"] if self._entries else GENESIS
            entry = {"seq": len(self._entries), "kind": kind, "actor": actor, "at": self._clock(),
                     "payload": _scrub(payload), "prev": prev}
            entry["hash"] = hashlib.sha256(canonicalize(entry).encode()).hexdigest()
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            self._entries.append(entry)
            return entry

    def entries(self) -> list[dict]:
        with self._lock:
            return list(self._entries)

    def head(self) -> tuple[int, str]:
        with self._lock:
            return len(self._entries), (self._entries[-1]["hash"] if self._entries else GENESIS)

    @staticmethod
    def verify_entries(entries: list[dict], expected_head: tuple[int, str] | None = None) -> None:
        prev = GENESIS
        for i, e in enumerate(entries):
            if e.get("seq") != i or e.get("prev") != prev:
                raise Corrupted("audit chain broken", seq=i)
            body = {k: v for k, v in e.items() if k != "hash"}
            h = hashlib.sha256(canonicalize(body).encode()).hexdigest()
            if h != e.get("hash"):
                raise Corrupted("audit entry hash mismatch", seq=i)
            prev = h
        if expected_head is not None and (len(entries), prev) != tuple(expected_head):
            raise Corrupted("audit ledger head does not match the external anchor (truncation or fork)")

    def verify(self, expected_head=None) -> None:
        if self.path:
            self.verify_entries(self._load(self.path), expected_head)
        else:
            self.verify_entries(self.entries(), expected_head)
