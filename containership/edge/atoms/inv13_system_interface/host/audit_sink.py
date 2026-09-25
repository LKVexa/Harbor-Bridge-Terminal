"""MC-015 -- durable, tamper-evident audit sink with independent verifier.

Records are JSON lines appended with O_APPEND and fsync.  Each record binds
``node``, ``workload``, ``release`` identity and is chained by SHA-256 over the
canonical body including ``prev``; every ``checkpoint_every`` records an
HMAC-SHA256 checkpoint over the head is appended with a separate key so an
attacker who can rewrite the file but lacks the checkpoint key cannot forge a
consistent tail.  ``verify_file`` is a standalone verifier (also exposed via
``python -m inv13_system_interface.host.audit_sink verify <file>``).
Records pass through a privacy filter (MC-029) before they are written.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import threading
from typing import Any, Callable

from .errors import ErrorCode, Inv13Error


def _canon(o: Any) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class AuditSink:
    def __init__(self, path: str, *, node: str, release: str, checkpoint_key: bytes,
                 checkpoint_every: int = 64, privacy: Callable[[dict], dict] | None = None) -> None:
        if len(checkpoint_key) < 32:
            raise ValueError("checkpoint key too short")
        self.path, self.node, self.release = path, node, release
        self._key, self._every = checkpoint_key, checkpoint_every
        self._privacy = privacy or (lambda d: d)
        self._lock = threading.Lock()
        self._seq, self._head = 0, ""
        if os.path.exists(path):
            ok, info = verify_file(path, checkpoint_key)
            if not ok:
                raise Inv13Error(ErrorCode.INTERNAL, f"existing audit log fails verification: {info}")
            self._seq, self._head = info["seq"], info["head"]
        self._fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_CLOEXEC", 0), 0o600)

    def append(self, workload: str, action: str, outcome: str, detail: dict[str, Any]) -> str:
        with self._lock:
            self._seq += 1
            body = {"t": "rec", "seq": self._seq, "prev": self._head, "node": self.node,
                    "release": self.release, "workload": workload, "action": action,
                    "outcome": outcome, "detail": self._privacy(dict(detail))}
            digest = hashlib.sha256(_canon(body)).hexdigest()
            line = _canon({**body, "digest": digest}) + b"\n"
            if self._seq % self._every == 0:
                cp = {"t": "cp", "seq": self._seq, "head": digest,
                      "mac": hmac.new(self._key, f"{self._seq}:{digest}".encode(), hashlib.sha256).hexdigest()}
                line += _canon(cp) + b"\n"
            os.write(self._fd, line)
            os.fsync(self._fd)
            self._head = digest
            return digest

    def seal(self) -> None:
        """Write a checkpoint for the current head (e.g. at shutdown)."""
        with self._lock:
            cp = {"t": "cp", "seq": self._seq, "head": self._head,
                  "mac": hmac.new(self._key, f"{self._seq}:{self._head}".encode(), hashlib.sha256).hexdigest()}
            os.write(self._fd, _canon(cp) + b"\n")
            os.fsync(self._fd)

    def close(self) -> None:
        os.close(self._fd)


def verify_file(path: str, checkpoint_key: bytes | None = None) -> tuple[bool, dict[str, Any]]:
    seq, head, last_cp = 0, "", 0
    with open(path, "rb") as f:
        for lineno, raw in enumerate(f, 1):
            if not raw.endswith(b"\n"):
                return False, {"error": "truncated line", "line": lineno}
            try:
                rec = json.loads(raw)
            except ValueError:
                return False, {"error": "bad json", "line": lineno}
            if rec.get("t") == "cp":
                if rec.get("seq") != seq or rec.get("head") != head:
                    return False, {"error": "checkpoint mismatch", "line": lineno}
                if checkpoint_key is not None:
                    want = hmac.new(checkpoint_key, f"{seq}:{head}".encode(), hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(want, str(rec.get("mac"))):
                        return False, {"error": "checkpoint mac", "line": lineno}
                last_cp = seq
                continue
            digest = rec.pop("digest", None)
            if rec.get("seq") != seq + 1 or rec.get("prev") != head:
                return False, {"error": "chain break", "line": lineno}
            if hashlib.sha256(_canon(rec)).hexdigest() != digest:
                return False, {"error": "digest mismatch", "line": lineno}
            seq, head = seq + 1, digest
    return True, {"seq": seq, "head": head, "last_checkpoint": last_cp,
                  "unsealed_tail": seq - last_cp}


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) >= 3 and sys.argv[1] == "verify":
        key = os.environ.get("INV13_AUDIT_KEY", "").encode() or None
        ok, info = verify_file(sys.argv[2], key)
        print(json.dumps({"ok": ok, **info}))
        sys.exit(0 if ok else 1)
    print("usage: audit_sink verify <file>  (INV13_AUDIT_KEY for checkpoint MACs)")
    sys.exit(2)
