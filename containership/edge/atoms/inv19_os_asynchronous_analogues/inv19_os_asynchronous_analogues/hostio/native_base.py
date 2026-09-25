"""Shared types for native host backends (PK_ASYNC_BACKEND/1 shapes)."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from enum import IntFlag

from .errors import CanonicalError


class Interest(IntFlag):
    READ = 1
    WRITE = 2


@dataclass(frozen=True)
class ReadinessEvent:
    token: int          # (generation << 32) | fd  - stale-safe identity
    fd: int
    readable: bool
    writable: bool
    error: bool
    hup: bool
    kind: str = "readiness"


@dataclass(frozen=True)
class CompletionEvent:
    op_id: int
    result: int | None          # >=0 success value (bytes); None on error
    error: CanonicalError | None
    flags: int = 0
    kind: str = "completion"


class BackendUnavailable(RuntimeError):
    def __init__(self, backend: str, reason: str, detail: str = "") -> None:
        super().__init__(f"{backend}: {reason} {detail}".strip())
        self.backend, self.reason, self.detail = backend, reason, detail


class BackendClosed(RuntimeError):
    pass


def set_nonblocking(fd: int) -> None:
    os.set_blocking(fd, False)


def require_nonblocking(fd: int) -> None:
    if os.get_blocking(fd):
        raise ValueError(f"descriptor {fd} must be non-blocking for readiness backends")


@dataclass
class Registrations:
    """fd -> generation bookkeeping so a reused fd number cannot receive an
    event belonging to its previous incarnation."""
    limit: int
    _gen: dict[int, int] = field(default_factory=dict)
    _live: dict[int, tuple[int, int, object]] = field(default_factory=dict)  # fd -> (gen, interest, owner)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    stale_events: int = 0

    def add(self, fd: int, interest: int, owner: object) -> int:
        with self._lock:
            if fd in self._live:
                raise ValueError(f"fd {fd} already registered")
            if len(self._live) >= self.limit:
                raise OverflowError(f"registration limit {self.limit}")
            g = (self._gen.get(fd, 0) + 1) & 0xFFFFFFFF or 1
            self._gen[fd] = g
            self._live[fd] = (g, interest, owner)
            return (g << 32) | fd

    def modify(self, fd: int, interest: int) -> int:
        with self._lock:
            g, _, owner = self._live[fd]
            self._live[fd] = (g, interest, owner)
            return (g << 32) | fd

    def remove(self, fd: int) -> None:
        with self._lock:
            self._live.pop(fd, None)

    def token_live(self, token: int) -> bool:
        fd, g = token & 0xFFFFFFFF, token >> 32
        with self._lock:
            ok = fd in self._live and self._live[fd][0] == g
            if not ok:
                self.stale_events += 1
            return ok

    def current_token(self, fd: int) -> int | None:
        with self._lock:
            if fd not in self._live:
                return None
            return (self._live[fd][0] << 32) | fd

    def owner(self, fd: int) -> object:
        with self._lock:
            return self._live[fd][2] if fd in self._live else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._live)

    def fds(self) -> list[int]:
        with self._lock:
            return list(self._live)
