"""Atomic, integrity-checked durable JSON records shared by the cache,
anti-replay state and emergency-control state (G13-MC-008/012/020).

Writes go to a temp file in the same directory, are fsynced, then renamed over
the target (atomic on POSIX and on Windows via ``os.replace``).  Every record
carries a SHA-256 of its canonical body; a mismatch raises instead of silently
resetting state.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, sha256_hex
from .errors import CacheCorrupt


Corrupt = CacheCorrupt   # alias; integrity failure of any durable record


def write_record(path: str | os.PathLike, body: dict[str, Any], *, kind: str, fault: Any = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"kind": kind, "body": body, "sha256": sha256_hex(canonical_bytes(body))}
    data = canonical_bytes(rec)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            if fault == "partial":             # fault-injection hook: simulate crash mid-write
                fh.write(data[: len(data) // 2])
                fh.flush()
                raise OSError("injected partial write")
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_record(path: str | os.PathLike, *, kind: str) -> dict[str, Any] | None:
    path = Path(path)
    if not path.exists():
        return None
    try:
        rec = json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise Corrupt(f"{path.name}: unreadable ({type(exc).__name__})") from exc
    if not isinstance(rec, dict) or rec.get("kind") != kind or not isinstance(rec.get("body"), dict):
        raise Corrupt(f"{path.name}: wrong record kind/shape")
    if sha256_hex(canonical_bytes(rec["body"])) != rec.get("sha256"):
        raise Corrupt(f"{path.name}: integrity check failed")
    return rec["body"]
