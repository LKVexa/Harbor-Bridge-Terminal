"""Single-authority ownership and generation fencing (GAP04-C16, C17).

* ``OwnershipLock`` takes an exclusive, non-blocking OS lock on the state
  directory (duplicate local instances are detected -> E0501) and increments a
  persisted controller generation on every acquisition. The generation is the
  fencing token carried on every journal frame and every downstream command.
* ``FencingValidator`` is used by downstream adapters (e.g. GAP-01) to reject
  commands from a stale controller: it keeps the highest (authority_epoch,
  generation) seen and refuses anything lower.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .errors import Fenced, Gap04Error
from .storage import atomic_write

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows: msvcrt fallback
    fcntl = None
    import msvcrt  # type: ignore


class OwnershipLock:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.dir / "owner.lock"
        self.gen_path = self.dir / "generation.json"
        self._fd: int | None = None
        self.generation = 0

    def acquire(self, owner_id: str) -> int:
        fd = os.open(str(self.lock_path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:  # pragma: no cover
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            os.close(fd)
            raise Gap04Error("another controller instance owns this state directory", code="GAP04-E0501",
                             details={"path": str(self.lock_path)}) from None
        self._fd = fd
        gen = self.current_generation() + 1
        atomic_write(self.gen_path, json.dumps({"generation": gen, "owner": owner_id}).encode())
        self.generation = gen
        return gen

    def current_generation(self) -> int:
        try:
            return int(json.loads(self.gen_path.read_text())["generation"])
        except FileNotFoundError:
            return 0

    def check(self) -> None:
        cur = self.current_generation()
        if cur != self.generation:
            raise Fenced("controller generation superseded", details={"mine": self.generation, "current": cur})

    def release(self) -> None:
        if self._fd is not None:
            if fcntl is not None:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


class FencingValidator:
    def __init__(self) -> None:
        self._max = (0, 0)
        self._lock = threading.Lock()

    def admit(self, authority_epoch: int, generation: int) -> None:
        tok = (int(authority_epoch), int(generation))
        with self._lock:
            if tok < self._max:
                raise Fenced("stale fencing token", details={"token": list(tok), "max": list(self._max)})
            self._max = tok
