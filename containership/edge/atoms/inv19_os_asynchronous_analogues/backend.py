"""Host asynchronous-backend state machine for INV-19.

This module is intentionally independent of ``pk_core`` so the safety-critical
backend mapping can be imported and tested even when the orchestration/gating
framework is not installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Iterable, Literal, TypeAlias

Semantics: TypeAlias = Literal["completion", "readiness"]
ComponentEvent: TypeAlias = tuple[Literal["value", "error", "retry"], object | None]

BACKENDS: dict[str, Semantics] = {
    "io_uring": "completion",
    "iocp": "completion",
    "epoll": "readiness",
    "kqueue": "readiness",
    "portable": "readiness",
}
BACKEND_PRIORITY: tuple[str, ...] = ("io_uring", "iocp", "epoll", "kqueue", "portable")
FALLBACK = "portable"


class NoBackend(RuntimeError):
    """Raised when a requested/selected backend cannot be represented safely."""


class DescriptorBudget(RuntimeError):
    """Raised when too many descriptors are armed at once."""


class InvalidDescriptor(ValueError):
    """Raised for invalid descriptor identifiers."""


def _validate_fd(fd: int) -> None:
    if isinstance(fd, bool) or not isinstance(fd, int) or fd < 0:
        raise InvalidDescriptor(f"descriptor must be a non-negative int, got {fd!r}")


def select(available: Iterable[str]) -> str:
    """Select a supported backend using an explicit, stable preference order.

    Unknown names are ignored.  If no supported candidate remains, the portable
    backend is selected.  Strings are rejected because treating one as an
    iterable of backend names is almost certainly a caller bug.
    """
    if isinstance(available, (str, bytes)):
        raise TypeError("available must be an iterable of backend names, not a string")
    supported = set(available).intersection(BACKENDS)
    for name in BACKEND_PRIORITY:
        if name in supported:
            return name
    if FALLBACK in BACKENDS:
        return FALLBACK
    raise NoBackend("no asynchronous backend available")


@dataclass
class AsyncBackend:
    """Thread-safe host asynchronous mechanism mapped onto component events.

    A descriptor has exactly three legal states: absent/unarmed, armed without
    an event, and armed with one unreaped event.  A second event may not replace
    an unreaped one, which prevents silent completion/error loss.
    """

    name: str
    max_descriptors: int = 4
    armed: dict[int, tuple[str, object | None, str | None] | None] = field(default_factory=dict)
    fallback_engagements: int = 0
    reaped: int = 0
    cancelled: int = 0
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.name not in BACKENDS:
            raise NoBackend(f"unknown backend {self.name!r}")
        if isinstance(self.max_descriptors, bool) or not isinstance(self.max_descriptors, int) or self.max_descriptors <= 0:
            raise ValueError("max_descriptors must be a positive integer")
        if self.name == FALLBACK:
            self.fallback_engagements = 1

    @property
    def semantics(self) -> Semantics:
        return BACKENDS[self.name]

    @property
    def armed_count(self) -> int:
        with self._lock:
            return len(self.armed)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(event is not None for event in self.armed.values())

    def arm(self, fd: int) -> None:
        _validate_fd(fd)
        with self._lock:
            if fd in self.armed:
                raise ValueError(f"descriptor {fd} is already armed")
            if len(self.armed) >= self.max_descriptors:
                raise DescriptorBudget(
                    f"{len(self.armed)} descriptors armed, budget {self.max_descriptors}"
                )
            self.armed[fd] = None

    def cancel(self, fd: int) -> bool:
        """Release an armed descriptor, including one with an unreaped event.

        Returns ``True`` if state was removed and ``False`` if the descriptor
        was already unarmed.  Cancellation is explicit so callers can release
        descriptor budget without manufacturing an event.
        """
        _validate_fd(fd)
        with self._lock:
            existed = fd in self.armed
            if existed:
                self.armed.pop(fd)
                self.cancelled += 1
            return existed

    def post(self, fd: int, result: object | None, error: str | None = None) -> None:
        """Record one host event for an already-armed descriptor."""
        _validate_fd(fd)
        if error is not None and not isinstance(error, str):
            raise TypeError("error must be a string or None")
        with self._lock:
            if fd not in self.armed:
                raise ValueError(f"descriptor {fd} is not armed")
            if self.armed[fd] is not None:
                raise ValueError(f"descriptor {fd} already has an unreaped event")
            if self.semantics == "completion":
                self.armed[fd] = ("completion", result, error)
            else:
                # Readiness does not prove completion and cannot honestly carry
                # a completion result/error.  The operation must be retried.
                self.armed[fd] = ("readiness", None, None)

    def reap(self, fd: int) -> ComponentEvent | None:
        """Collect one event, or return ``None`` when none is ready."""
        _validate_fd(fd)
        with self._lock:
            event = self.armed.get(fd)
            if event is None:
                return None
            kind, result, error = event
            self.armed.pop(fd)
            self.reaped += 1
        if kind == "completion":
            return ("error", error) if error is not None else ("value", result)
        return ("retry", None)

    def snapshot(self) -> dict[str, object]:
        """Return a bounded, non-secret diagnostic view for health reporting."""
        with self._lock:
            return {
                "backend": self.name,
                "semantics": self.semantics,
                "max_descriptors": self.max_descriptors,
                "armed": len(self.armed),
                "pending": sum(event is not None for event in self.armed.values()),
                "reaped": self.reaped,
                "cancelled": self.cancelled,
                "fallback_engagements": self.fallback_engagements,
            }
