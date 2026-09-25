"""MC-27 tamper-evident audit ledger: append-only, hash-chained, HMAC-sealed JSONL."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from pathlib import Path
from typing import Any, Iterable

from .security import SecretProvider, canonical

GENESIS = "0" * 64
REDACT = {"token", "mac", "secret", "key", "password"}


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if k.lower() in REDACT else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


class AuditLedger:
    def __init__(self, path: str | os.PathLike | None, secrets: SecretProvider, key_id: str = "audit"):
        self.path = Path(path) if path else None
        self.secrets, self.key_id = secrets, key_id
        self._lock = threading.Lock()
        self._mem: list[dict[str, Any]] = []
        self.head, self.seq = GENESIS, 0
        if self.path and self.path.exists():
            recs = list(self.read())
            ok, why = verify_chain(recs, secrets, key_id)
            if not ok:
                from .errors import SchedulerError
                raise SchedulerError("STATE_CORRUPT", f"audit ledger failed verification: {why}")
            self._mem = recs
            if recs:
                self.head, self.seq = recs[-1]["hash"], recs[-1]["seq"]

    def append(self, action: str, actor: str, subject: dict[str, Any], at: int) -> dict[str, Any]:
        with self._lock:
            body = {"seq": self.seq + 1, "prev": self.head, "at": at, "action": action,
                    "actor": actor, "subject": _redact(subject)}
            h = hashlib.sha256(canonical(body)).hexdigest()
            rec = dict(body, hash=h, seal=hmac.new(self.secrets.get(self.key_id), h.encode(), hashlib.sha256).hexdigest())
            if self.path:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, sort_keys=True) + "\n")
                    f.flush(); os.fsync(f.fileno())
            self._mem.append(rec)
            self.head, self.seq = h, body["seq"]
            return rec

    def read(self) -> Iterable[dict[str, Any]]:
        if self.path and self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)
        else:
            yield from list(self._mem)


def verify_chain(records: list[dict[str, Any]], secrets: SecretProvider, key_id: str = "audit",
                 expected_head: str | None = None) -> tuple[bool, str]:
    prev, seq = GENESIS, 0
    key = secrets.get(key_id)
    for r in records:
        body = {k: r[k] for k in ("seq", "prev", "at", "action", "actor", "subject") if k in r}
        if r.get("seq") != seq + 1:
            return False, f"sequence gap at {seq + 1}"
        if r.get("prev") != prev:
            return False, f"chain break at seq {r.get('seq')}"
        h = hashlib.sha256(canonical(body)).hexdigest()
        if h != r.get("hash"):
            return False, f"hash mismatch at seq {r.get('seq')}"
        if not hmac.compare_digest(hmac.new(key, h.encode(), hashlib.sha256).hexdigest(), str(r.get("seal"))):
            return False, f"seal invalid at seq {r.get('seq')}"
        prev, seq = h, r["seq"]
    if expected_head is not None and prev != expected_head:
        return False, "head mismatch (tail truncated or ledger substituted)"
    return True, "ok"
