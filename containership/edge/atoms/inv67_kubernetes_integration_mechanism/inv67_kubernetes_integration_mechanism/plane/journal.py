"""Crash consistency / restart / replay (item 34).

An append-only intent journal: ``intent`` is fsynced *before* a side effect,
``done`` after. On restart, intents without ``done`` are replayed; because the
downstream accepts an idempotency key (the attempt id), replay never
double-launches. Torn tail lines (crash mid-write) are detected and ignored.
"""
from __future__ import annotations

import json
import os
import threading


class Journal:
    def __init__(self, path: str | None = None):
        self.path = path
        self._lock = threading.Lock()
        self.entries: list[dict] = []
        self.torn = 0
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        self.entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        self.torn += 1

    def _write(self, rec: dict):
        self.entries.append(rec)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())

    def intent(self, key: str, op: str, payload: dict):
        with self._lock:
            self._write({"t": "intent", "key": key, "op": op, "payload": payload})

    def done(self, key: str, op: str):
        with self._lock:
            self._write({"t": "done", "key": key, "op": op})

    def pending(self) -> list[dict]:
        done = {(e["key"], e["op"]) for e in self.entries if e.get("t") == "done"}
        seen, out = set(), []
        for e in self.entries:
            k = (e.get("key"), e.get("op"))
            if e.get("t") == "intent" and k not in done and k not in seen:
                seen.add(k)
                out.append(e)
        return out
