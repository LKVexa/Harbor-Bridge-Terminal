"""Shared primitives: canonical JSON, digests, clocks, atomic file writes."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable

Clock = Callable[[], float]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_of(value: Any) -> str:
    return sha256_hex(canonical_json(value))


def new_id(prefix: str = "") -> str:
    return prefix + uuid.uuid4().hex


def now() -> float:
    return time.time()


def atomic_write(path: Path, data: bytes, *, fsync: bool = True) -> None:
    """Write-temp, fsync, rename, fsync-dir: readers see old or new bytes, never a mix."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            if fsync:
                os.fsync(fh.fileno())
        os.replace(tmp, path)
        if fsync and hasattr(os, "O_DIRECTORY"):
            dfd = os.open(str(path.parent), os.O_DIRECTORY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
