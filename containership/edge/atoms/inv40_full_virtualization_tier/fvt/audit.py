"""Tamper-evident, hash-chained audit log (INV-40-C049).

Each record commits to the previous record's hash; ``verify`` recomputes the
chain and reports the first break.  Tail truncation is not detectable from the
chain alone, so ``head()`` is exported for external anchoring (the service
publishes it in health output and evidence).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import threading

GENESIS = "0" * 64
_REDACT = {"token", "credential", "secret", "password", "key"}


def _canon(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def _scrub(d):
    if isinstance(d, dict):
        return {k: ("[REDACTED]" if any(r in k.lower() for r in _REDACT) else _scrub(v)) for k, v in d.items()}
    if isinstance(d, list):
        return [_scrub(x) for x in d]
    return d


class AuditLog:
    def __init__(self, path: str | os.PathLike | None = None):
        self.path = pathlib.Path(path) if path else None
        self._lock = threading.Lock()
        self._records: list[dict] = []
        if self.path and self.path.exists():
            self._records = [json.loads(l) for l in self.path.read_text("utf-8").splitlines() if l.strip()]

    def head(self) -> str:
        return self._records[-1]["hash"] if self._records else GENESIS

    def append(self, *, actor: str, action: str, outcome: str, **fields) -> dict:
        with self._lock:
            rec = {"schema": "PK_FULL_VM_AUDIT/1", "seq": len(self._records),
                   "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds"),
                   "actor": actor, "action": action, "outcome": outcome,
                   "fields": _scrub(fields), "prev": self.head()}
            rec["hash"] = hashlib.sha256(_canon(rec)).hexdigest()
            self._records.append(rec)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return rec

    def records(self) -> list[dict]:
        return list(self._records)

    @staticmethod
    def verify(records: list[dict]) -> tuple[bool, int | None]:
        prev = GENESIS
        for i, r in enumerate(records):
            body = {k: v for k, v in r.items() if k != "hash"}
            if r.get("seq") != i or r.get("prev") != prev or hashlib.sha256(_canon(body)).hexdigest() != r.get("hash"):
                return False, i
            prev = r["hash"]
        return True, None
