"""Thread-safe legacy pollable primitive for INV-14.

This module intentionally has no ``pk_core`` dependency so the behavioural core can
be tested in isolation.  It models the retained, pre-composable asynchronous API:
a pollable belongs to exactly one component instance and a poll waits for one or
more pollables to become ready, subject to a hard timeout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import threading
import time
from typing import Callable, Iterable, Sequence

MIGRATION_TARGET = "INV-15 New asynchronous ABI"
POLL_SCHEMA = "PK_POLL/1"
ERROR_SCHEMA = "PK_POLL_ERROR/1"
DEFAULT_TICK_SECONDS = 0.001
DEFAULT_MAX_TIMEOUT_TICKS = 60_000
DEFAULT_MAX_POLLABLES = 4_096
MAX_POLL_DURATION_SECONDS = 60.0


class _StructuredPollError:
    """Mixin that gives poll failures a stable machine-readable representation."""

    default_code = "PK_POLL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.code = code or self.default_code
        self.details = dict(details or {})

    def as_dict(self) -> dict:
        return {
            "schema": ERROR_SCHEMA,
            "code": self.code,
            "message": str(self),
            "details": dict(self.details),
            "deprecated": True,
            "migrate_to": MIGRATION_TARGET,
        }


class PollValidationError(_StructuredPollError, ValueError):
    """Raised when a poll request is malformed or exceeds a safety limit."""

    default_code = "PK_POLL_INVALID_REQUEST"


class ForeignPollable(_StructuredPollError, PermissionError):
    """Raised when a pollable from another instance is polled."""

    default_code = "PK_POLL_FOREIGN_OWNER"


class PollCancelled(_StructuredPollError, RuntimeError):
    """Raised when a caller-supplied cancellation token fires before readiness.

    Readiness wins a tie: if a member is ready at the moment cancellation is
    observed, the poll returns the ready result instead (C025, v4.3.0).
    """

    default_code = "PK_POLL_CANCELLED"


class CancelToken:
    """Caller-driven cancellation for one or more polls (v4.3.0, component P1-05).

    ``cancel()`` is idempotent and latched; a token cannot be un-cancelled.  It uses
    the same durable-event registration as ``Pollable`` so a cancellation that
    races the wait boundary is never lost.
    """

    __slots__ = ("_lock", "_cancelled", "_reason", "_waiters")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled = False
        self._reason = ""
        self._waiters: set[threading.Event] = set()

    def cancel(self, reason: str = "caller") -> bool:
        """Cancel; returns True only for the call that performed the transition."""
        if not isinstance(reason, str):
            reason = "caller"
        with self._lock:
            if self._cancelled:
                return False
            self._cancelled = True
            self._reason = reason[:64]
            waiters = tuple(self._waiters)
        for w in waiters:
            w.set()
        return True

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    @property
    def reason(self) -> str:
        with self._lock:
            return self._reason

    def _register_waiter(self, waiter: threading.Event) -> bool:
        with self._lock:
            self._waiters.add(waiter)
            return self._cancelled

    def _unregister_waiter(self, waiter: threading.Event) -> None:
        with self._lock:
            self._waiters.discard(waiter)

    def _waiter_count(self) -> int:
        with self._lock:
            return len(self._waiters)


@dataclass(eq=False)
class Pollable:
    """A level-triggered readiness handle owned by exactly one instance.

    ``signal()`` latches readiness even if it races a poll.  ``clear()`` is explicit
    and is intended to be called only after the underlying ready operation has been
    consumed.  Object identity, not equality, defines a pollable handle.
    """

    name: str
    owner: str
    ready: bool = False
    pending_signal: bool = False
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _waiters: set[threading.Event] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        _require_nonempty_text(self.name, "pollable name")
        _require_nonempty_text(self.owner, "pollable owner")
        if not isinstance(self.ready, bool) or not isinstance(self.pending_signal, bool):
            raise PollValidationError(
                "pollable readiness fields must be boolean",
                code="PK_POLL_INVALID_STATE",
            )
        if self.ready and self.pending_signal:
            # Ready is already latched, so carrying a second pending bit is ambiguous.
            self.pending_signal = False

    def signal(self) -> None:
        """Latch readiness and wake every currently interested poll set."""
        with self._lock:
            if self.ready or self.pending_signal:
                return
            self.pending_signal = True
            waiters = tuple(self._waiters)
        for waiter in waiters:
            waiter.set()

    def clear(self) -> None:
        """Clear readiness after the underlying operation has been consumed."""
        with self._lock:
            self.ready = False
            self.pending_signal = False

    def is_ready(self) -> bool:
        """Return readiness, atomically promoting a raced signal into ready state."""
        with self._lock:
            if self.pending_signal:
                self.ready = True
                self.pending_signal = False
            return self.ready

    def _register_waiter(self, waiter: threading.Event) -> bool:
        """Register a durable wake event and return the current readiness snapshot."""
        with self._lock:
            self._waiters.add(waiter)
            if self.pending_signal:
                self.ready = True
                self.pending_signal = False
            return self.ready

    def _unregister_waiter(self, waiter: threading.Event) -> None:
        with self._lock:
            self._waiters.discard(waiter)


@dataclass
class PollSet:
    """The retained blocking primitive: bounded, lossless, isolated, and deprecated."""

    owner: str
    tick_seconds: float = DEFAULT_TICK_SECONDS
    max_timeout_ticks: int = DEFAULT_MAX_TIMEOUT_TICKS
    max_pollables: int = DEFAULT_MAX_POLLABLES
    deprecated_uses: int = field(default=0, init=False)
    _ready_polls: int = field(default=0, init=False, repr=False)
    _timeouts: int = field(default=0, init=False, repr=False)
    _cross_instance_refusals: int = field(default=0, init=False, repr=False)
    _invalid_requests: int = field(default=0, init=False, repr=False)
    _total_pollables: int = field(default=0, init=False, repr=False)
    _max_set_size_seen: int = field(default=0, init=False, repr=False)
    _cancelled_polls: int = field(default=0, init=False, repr=False)
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    _metrics_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        _require_nonempty_text(self.owner, "poll set owner")
        if (not isinstance(self.tick_seconds, (int, float))
                or isinstance(self.tick_seconds, bool)
                or not math.isfinite(float(self.tick_seconds))
                or self.tick_seconds <= 0):
            raise PollValidationError(
                "tick_seconds must be a finite positive number",
                code="PK_POLL_INVALID_TICK_DURATION",
            )
        if not callable(self.clock):
            raise PollValidationError("clock must be callable", code="PK_POLL_INVALID_CLOCK")
        if not _positive_int(self.max_timeout_ticks):
            raise PollValidationError(
                "max_timeout_ticks must be a positive integer",
                code="PK_POLL_INVALID_LIMIT",
            )
        if not _positive_int(self.max_pollables):
            raise PollValidationError(
                "max_pollables must be a positive integer",
                code="PK_POLL_INVALID_LIMIT",
            )

    def poll(self, pollables: Sequence[Pollable], *, timeout_ticks: int,
             cancel: "CancelToken | None" = None) -> dict:
        """Wait until at least one pollable is ready or the hard deadline expires.

        The registration/check/wait order uses a durable ``threading.Event``.  A
        signal that lands between readiness inspection and blocking therefore
        remains observable and cannot be lost as a transient condition wakeup.
        """
        try:
            if cancel is not None and not isinstance(cancel, CancelToken):
                raise PollValidationError(
                    "cancel must be a CancelToken or None",
                    code="PK_POLL_INVALID_CANCEL_TOKEN",
                )
            checked = self._validate_request(pollables, timeout_ticks)
        except PollValidationError:
            with self._metrics_lock:
                self._invalid_requests += 1
            raise

        foreign = [p.name for p in checked if p.owner != self.owner]
        if foreign:
            with self._metrics_lock:
                self._cross_instance_refusals += 1
            raise ForeignPollable(
                f"{self.owner}: pollables {foreign!r} belong to another instance and do not compose",
                details={"owner": self.owner, "foreign_pollables": foreign},
            )

        duration = timeout_ticks * float(self.tick_seconds)
        if not math.isfinite(duration) or duration > MAX_POLL_DURATION_SECONDS:
            with self._metrics_lock:
                self._invalid_requests += 1
            raise PollValidationError(
                "poll duration exceeds the hard 60-second safety ceiling",
                code="PK_POLL_DURATION_LIMIT",
                details={"duration_seconds": duration, "max_seconds": MAX_POLL_DURATION_SECONDS},
            )

        with self._metrics_lock:
            self.deprecated_uses += 1
            self._total_pollables += len(checked)
            self._max_set_size_seen = max(self._max_set_size_seen, len(checked))

        wake = threading.Event()
        deadline = self.clock() + duration
        # The real monotonic clock is an independent hard bound: an injected or
        # anomalous clock (fault injection, C089) may only shorten a wait.
        hard_deadline = time.monotonic() + duration
        cancelled = False
        try:
            for p in checked:
                p._register_waiter(wake)
            if cancel is not None:
                cancel._register_waiter(wake)

            # Re-scan every member after all waiter registrations.  This captures
            # readiness that appears while the set is being registered and returns
            # the complete ready set rather than only the first observed member.
            ready = self._ready_now(checked)
            while not ready:
                if cancel is not None and cancel.cancelled:
                    cancelled = True
                    break
                remaining = min(deadline - self.clock(), hard_deadline - time.monotonic())
                if remaining <= 0:
                    break
                wake.wait(remaining)
                wake.clear()
                ready = self._ready_now(checked)

            if cancelled:
                with self._metrics_lock:
                    self._cancelled_polls += 1
                raise PollCancelled(
                    f"{self.owner}: poll cancelled before readiness",
                    details={"owner": self.owner, "reason": cancel.reason, "set_size": len(checked)},
                )
            timed_out = not ready
            with self._metrics_lock:
                if timed_out:
                    self._timeouts += 1
                else:
                    self._ready_polls += 1

            ready_ids = {id(p) for p in ready}
            return {
                "schema": POLL_SCHEMA,
                "owner": self.owner,
                "ready": [p.name for p in ready],
                "ready_indexes": [i for i, p in enumerate(checked) if id(p) in ready_ids],
                "timed_out": timed_out,
                "timeout_ticks": timeout_ticks,
                "set_size": len(checked),
                "deprecated": True,
                "migrate_to": MIGRATION_TARGET,
            }
        finally:
            for p in checked:
                p._unregister_waiter(wake)
            if cancel is not None:
                cancel._unregister_waiter(wake)

    def metrics_snapshot(self) -> dict:
        """Return bounded in-memory counters suitable for an external telemetry adapter."""
        with self._metrics_lock:
            return {
                "schema": "PK_POLL_METRICS/1",
                "owner": self.owner,
                "deprecated_uses": self.deprecated_uses,
                "polls_ready": self._ready_polls,
                "polls_timeout": self._timeouts,
                "polls_cancelled": self._cancelled_polls,
                "cross_instance_refusals": self._cross_instance_refusals,
                "invalid_requests": self._invalid_requests,
                "total_pollables": self._total_pollables,
                "max_set_size_seen": self._max_set_size_seen,
                "max_pollables": self.max_pollables,
                "max_timeout_ticks": self.max_timeout_ticks,
            }

    def _ready_now(self, pollables: Iterable[Pollable]) -> list[Pollable]:
        return [p for p in pollables if p.is_ready()]

    def _validate_request(self, pollables: Sequence[Pollable], timeout_ticks: int) -> tuple[Pollable, ...]:
        if (not isinstance(timeout_ticks, int) or isinstance(timeout_ticks, bool)
                or timeout_ticks <= 0):
            raise PollValidationError(
                "poll requires a positive integer timeout; unbounded blocking is refused",
                code="PK_POLL_INVALID_TIMEOUT",
                details={"timeout_ticks": repr(timeout_ticks)},
            )
        if timeout_ticks > self.max_timeout_ticks:
            raise PollValidationError(
                "poll timeout exceeds the configured safety ceiling",
                code="PK_POLL_TIMEOUT_LIMIT",
                details={"timeout_ticks": timeout_ticks, "max_timeout_ticks": self.max_timeout_ticks},
            )
        if isinstance(pollables, (str, bytes, bytearray)) or not isinstance(pollables, Sequence):
            raise PollValidationError(
                "pollables must be a finite sequence of Pollable objects",
                code="PK_POLL_INVALID_SET",
            )
        checked = tuple(pollables)
        if not checked:
            raise PollValidationError(
                "poll on an empty set would block forever",
                code="PK_POLL_EMPTY_SET",
            )
        if len(checked) > self.max_pollables:
            raise PollValidationError(
                "pollable set exceeds the configured capacity ceiling",
                code="PK_POLL_SET_LIMIT",
                details={"set_size": len(checked), "max_pollables": self.max_pollables},
            )
        if any(not isinstance(p, Pollable) for p in checked):
            raise PollValidationError(
                "every member of a poll set must be a Pollable",
                code="PK_POLL_INVALID_MEMBER",
            )
        if len({id(p) for p in checked}) != len(checked):
            raise PollValidationError(
                "a pollable appears more than once in the set",
                code="PK_POLL_DUPLICATE_HANDLE",
            )
        names = [p.name for p in checked]
        if len(set(names)) != len(names):
            raise PollValidationError(
                "pollable names must be unique within one poll set so ready results are unambiguous",
                code="PK_POLL_DUPLICATE_NAME",
            )
        return checked


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _require_nonempty_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PollValidationError(
            f"{label} must be a non-empty string",
            code="PK_POLL_INVALID_IDENTITY",
        )
