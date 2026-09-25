"""Tamper-evident security audit log (MC-038).

Append-only JSON-lines file.  Each entry carries ``seq``, ``prev`` (hash of the
previous entry) and ``mac`` = HMAC-SHA256(audit_key, canonical entry without
``mac``).  Any edit, deletion, reordering or truncation in the middle of the
file breaks the chain; truncation of the tail is detected by comparing the
last ``(seq, mac)`` against an externally anchored checkpoint
(:meth:`AuditLog.anchor`), which operators ship to WORM storage.

Audit writes are separated from data writes: the service holds only the
``append`` capability; reading requires ``admin.audit_read``; there is no
delete API (retention is enforced by archival rotation, see
``docs/operations/AUDIT_RETENTION.md``) (MC-038-04/05).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from typing import Any, Callable, Iterator

from .security import redact

AUDIT_CLASSES = frozenset({"authn", "authz", "mutation", "compaction", "config", "membership", "key",
                           "admin", "lease", "backup", "policy", "recovery"})
GENESIS = "0" * 64


def _canon(d: dict[str, Any]) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), default=str).encode()


class AuditLog:
    def __init__(self, path: str | None, key: bytes, *, clock: Callable[[], float] = time.time,
                 fsync: bool = True, source: str = "inv05") -> None:
        if len(key) < 32:
            raise ValueError("audit key must be >= 32 bytes")
        self.path, self._key, self.clock, self.fsync, self.source = path, key, clock, fsync, source
        self._lock = threading.Lock()
        self._mem: list[dict[str, Any]] = []
        self._seq, self._prev = 0, GENESIS
        if path and os.path.exists(path):
            last = None
            for last in self._iter_file():
                pass
            if last:
                self._seq, self._prev = last["seq"], last["mac"]

    def _iter_file(self) -> Iterator[dict[str, Any]]:
        with open(self.path, "r", encoding="utf-8") as fh:  # type: ignore[arg-type]
            for line in fh:
                if line.strip():
                    yield json.loads(line)

    def record(self, cls: str, action: str, *, actor: str, target: str = "", outcome: str = "ok",
               request_id: str = "", revision: int = 0, source_identity: str = "", **extra: Any) -> dict[str, Any]:
        if cls not in AUDIT_CLASSES:
            raise ValueError(f"unknown audit class {cls}")
        with self._lock:
            entry = {"seq": self._seq + 1, "ts": round(self.clock(), 6), "class": cls, "action": action,
                     "actor": actor, "target": target, "outcome": outcome, "request_id": request_id,
                     "revision": revision, "source": source_identity or self.source,
                     "extra": redact(extra), "prev": self._prev}
            entry["mac"] = hmac.new(self._key, _canon(entry), hashlib.sha256).hexdigest()
            if self.path:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                try:
                    os.write(fd, _canon(entry) + b"\n")
                    if self.fsync:
                        os.fsync(fd)
                finally:
                    os.close(fd)
            else:
                self._mem.append(entry)
            self._seq, self._prev = entry["seq"], entry["mac"]
            return entry

    def entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._iter_file()) if self.path and os.path.exists(self.path) else list(self._mem)

    def anchor(self) -> dict[str, Any]:
        with self._lock:
            return {"seq": self._seq, "mac": self._prev}

    @staticmethod
    def verify(entries: list[dict[str, Any]], key: bytes, anchor: dict[str, Any] | None = None) -> list[str]:
        """Return a list of integrity problems (empty == intact)."""
        problems: list[str] = []
        prev, seq = GENESIS, 0
        for e in entries:
            body = {k: v for k, v in e.items() if k != "mac"}
            if e.get("seq") != seq + 1:
                problems.append(f"sequence gap/reorder at seq {e.get('seq')} (expected {seq + 1})")
            if e.get("prev") != prev:
                problems.append(f"chain break at seq {e.get('seq')}")
            if not hmac.compare_digest(hmac.new(key, _canon(body), hashlib.sha256).hexdigest(), str(e.get("mac"))):
                problems.append(f"MAC mismatch at seq {e.get('seq')}")
            prev, seq = str(e.get("mac")), int(e.get("seq", seq + 1))
        if anchor and (anchor.get("seq", 0) > seq or
                       (anchor.get("seq") == seq and anchor.get("mac") != prev)):
            problems.append("log truncated or rewritten relative to anchor")
        return problems


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m inv05_current_control_state_system.audit <file> <key-hex> [anchor.json]``."""
    import sys
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print("usage: audit.py FILE KEY_HEX [ANCHOR_JSON]")
        return 2
    with open(args[0], encoding="utf-8") as fh:
        entries = [json.loads(l) for l in fh if l.strip()]
    anchor = json.load(open(args[2])) if len(args) > 2 else None
    problems = AuditLog.verify(entries, bytes.fromhex(args[1]), anchor)
    print(json.dumps({"entries": len(entries), "ok": not problems, "problems": problems}))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
