"""Tamper-evident, append-only security audit log (MC-025).

Each JSON line carries ``prev`` (hash of the previous record) and ``mac``
(HMAC over the canonical record with the audit key).  ``verify`` detects
modification, deletion, reordering and truncation-with-forgery.  Records are
size-bounded and pass through the redactor, so secrets never reach disk.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time

from ..errors import Inv24Error
from .keys import Keyring
from .secrets import redact

GENESIS = "0" * 64
MAX_RECORD = 8192


class AuditLog:
    def __init__(self, path: str, keyring: Keyring, *, clock=time.time) -> None:
        self.path, self.keyring, self.clock = path, keyring, clock
        self._lock = threading.Lock()
        self._head, self._seq = self._recover()

    def _recover(self) -> tuple[str, int]:
        if not os.path.exists(self.path):
            return GENESIS, 0
        head, seq = self.verify()
        return head, seq

    def append(self, event: str, actor: str, outcome: str, **fields: object) -> dict:
        with self._lock:
            rec = {"seq": self._seq + 1, "ts": round(self.clock(), 3), "event": event[:64], "actor": actor[:128],
                   "outcome": outcome[:32], "fields": redact(fields), "prev": self._head}
            canon = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            if len(canon) > MAX_RECORD:
                rec["fields"] = {"truncated": True}
                canon = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            kid, mac = self.keyring.sign(canon.encode())
            rec["kid"], rec["mac"] = kid, mac
            line = json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n"
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line.encode())
                os.fsync(fd)
            finally:
                os.close(fd)
            self._head = hashlib.sha256(canon.encode()).hexdigest()
            self._seq += 1
            return rec

    def verify(self) -> tuple[str, int]:
        head, seq = GENESIS, 0
        with open(self.path, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                try:
                    rec = json.loads(line)
                    kid, mac = rec.pop("kid"), rec.pop("mac")
                except (ValueError, KeyError):
                    raise Inv24Error("INTEGRITY_VIOLATION", f"audit line {n} malformed") from None
                if rec.get("prev") != head or rec.get("seq") != seq + 1:
                    raise Inv24Error("INTEGRITY_VIOLATION", f"audit chain broken at line {n}")
                canon = json.dumps(rec, sort_keys=True, separators=(",", ":"))
                if not self.keyring.verify(kid, canon.encode(), mac):
                    raise Inv24Error("INTEGRITY_VIOLATION", f"audit MAC invalid at line {n}")
                head, seq = hashlib.sha256(canon.encode()).hexdigest(), seq + 1
        return head, seq

    @property
    def head(self) -> str:
        return self._head
