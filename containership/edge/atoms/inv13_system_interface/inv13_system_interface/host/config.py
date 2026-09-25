"""MC-014 -- atomic, versioned configuration and policy activation.

A configuration bundle (policy document + worlds + metadata) is validated,
staged under its content digest, and activated by atomically swapping a
single ``ACTIVE`` pointer file (write-temp + fsync + ``os.replace`` + dir
fsync).  Activation is compare-and-swap on the expected previous digest, so
two control-plane writers cannot interleave.  A crash at any point leaves the
old or the new pointer -- never a partial one -- and ``recover()`` discards
orphan temp files.  Rollback re-points to any previously staged digest.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any, Callable

from .errors import ErrorCode, Inv13Error
from .policy import PolicyEngine


def _fsync_dir(p: Path) -> None:
    try:
        fd = os.open(p, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{threading.get_ident()}")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class ConfigStore:
    def __init__(self, root: str | os.PathLike, *, validator: Callable[[dict], None] | None = None,
                 fault: Callable[[str], None] | None = None) -> None:
        self.root = Path(root)
        (self.root / "staged").mkdir(parents=True, exist_ok=True)
        self._validator = validator or self.default_validator
        self._fault = fault or (lambda stage: None)
        self._lock = threading.Lock()

    @staticmethod
    def default_validator(bundle: dict) -> None:
        if not isinstance(bundle, dict) or bundle.get("schema") != "INV13_CONFIG/1":
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "schema")
        for k in ("version", "author", "policy"):
            if k not in bundle:
                raise Inv13Error(ErrorCode.INVALID_ARGUMENT, f"missing {k}")
        PolicyEngine(bundle["policy"])  # full policy validation

    def stage(self, bundle: dict) -> str:
        self._validator(bundle)
        data = canonical(bundle)
        digest = hashlib.sha256(data).hexdigest()
        target = self.root / "staged" / f"{digest}.json"
        if not target.exists():
            atomic_write(target, data)
        return digest

    def active(self) -> str | None:
        p = self.root / "ACTIVE"
        if not p.exists():
            return None
        rec = json.loads(p.read_text())
        return rec["digest"]

    def load(self, digest: str | None = None) -> dict:
        digest = digest or self.active()
        if digest is None:
            raise Inv13Error(ErrorCode.CONFIG_STALE, "no active config")
        data = (self.root / "staged" / f"{digest}.json").read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise Inv13Error(ErrorCode.INTERNAL, "staged config corrupted")
        return json.loads(data)

    def activate(self, digest: str, *, expected_previous: str | None, actor: str, reason: str) -> None:
        with self._lock:
            self.load(digest)  # must exist and verify
            cur = self.active()
            if cur != expected_previous:
                raise Inv13Error(ErrorCode.ALREADY_EXISTS, f"CAS failed: active={cur}")
            self._fault("before-pointer-swap")
            hist = self.history()
            hist.append({"digest": digest, "previous": cur, "actor": actor, "reason": reason})
            atomic_write(self.root / "HISTORY.json", canonical(hist))
            self._fault("before-active-replace")
            atomic_write(self.root / "ACTIVE", canonical({"digest": digest, "previous": cur}))

    def history(self) -> list[dict]:
        p = self.root / "HISTORY.json"
        return json.loads(p.read_text()) if p.exists() else []

    def rollback(self, *, actor: str, reason: str) -> str:
        cur = self.active()
        prev = json.loads((self.root / "ACTIVE").read_text()).get("previous") if cur else None
        if not prev:
            raise Inv13Error(ErrorCode.NOT_FOUND, "nothing to roll back to")
        self.activate(prev, expected_previous=cur, actor=actor, reason=f"rollback: {reason}")
        return prev

    def recover(self) -> int:
        n = 0
        for p in list(self.root.rglob(".*.tmp-*")):
            p.unlink()
            n += 1
        return n
