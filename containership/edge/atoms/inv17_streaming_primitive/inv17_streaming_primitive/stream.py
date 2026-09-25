"""Runtime implementation for INV-17's typed, credit-limited stream primitive.

This module intentionally has no ``pk_core`` dependency so the data-plane primitive can
be embedded and tested independently from its certification/assessment adapter.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Condition, Event, RLock
import itertools
import time
from types import MappingProxyType
from typing import Generic, Mapping, TypeVar

T = TypeVar("T")
NOT_READY = Ellipsis

#: Wire/protocol identity of the three public interfaces (see ``schemas/``).
PROTOCOL_VERSIONS: Mapping[str, int] = MappingProxyType({"PK_STREAM": 1, "PK_STREAM_CREDIT": 1, "PK_STREAM_CLOSE": 1})
_IDS = itertools.count(1)


class StreamError(RuntimeError):
    """Base class carrying a stable machine-readable error code and details."""

    code = "PK_STREAM_ERROR"

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.details: Mapping[str, object] = MappingProxyType(dict(details))

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class CreditExhausted(StreamError):
    """Writer attempted to send without reader-granted credit."""

    code = "PK_STREAM_CREDIT_EXHAUSTED"


class CreditLimitExceeded(StreamError, ValueError):
    """A credit grant would exceed the configured outstanding-credit ceiling."""

    code = "PK_STREAM_CREDIT_LIMIT"


class BufferLimitExceeded(StreamError):
    """The configured in-flight buffer ceiling was reached."""

    code = "PK_STREAM_BUFFER_LIMIT"


class EndDropped(StreamError):
    """An operation targeted an endpoint that has been dropped."""

    code = "PK_STREAM_END_DROPPED"


class StreamClosed(StreamError):
    """An operation is invalid after graceful end-of-stream."""

    code = "PK_STREAM_CLOSED"


class ElementTypeMismatch(StreamError, TypeError):
    """An element does not satisfy the stream's declared runtime type."""

    code = "PK_STREAM_TYPE_MISMATCH"


class StreamTimeout(StreamError, TimeoutError):
    """A bounded wait elapsed. Timeouts never imply end-of-stream (non-goal)."""

    code = "PK_STREAM_TIMEOUT"


class StreamCancelled(StreamError):
    """A wait was cancelled by its caller's cancellation token."""

    code = "PK_STREAM_CANCELLED"


class StreamFrozen(StreamError):
    """The stream (or its tenant/workload) is quarantined by an emergency control."""

    code = "PK_STREAM_FROZEN"


class CancelToken:
    """Cooperative cancellation shared between a caller and blocking waits."""

    __slots__ = ("_event", "reason")

    def __init__(self) -> None:
        self._event = Event()
        self.reason = ""

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True, slots=True)
class StreamConfig:
    """Immutable resource limits for one stream instance."""

    max_credit: int = 1024
    max_buffer: int = 1024
    idempotency_window: int = 1024

    def __post_init__(self) -> None:
        for name, value in (("max_credit", self.max_credit), ("max_buffer", self.max_buffer),
                            ("idempotency_window", self.idempotency_window)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer, got {value!r}")


@dataclass(frozen=True, slots=True)
class StreamStats:
    """Atomic diagnostic snapshot with bounded-cardinality counters/state."""

    state: str
    credit: int
    buffered: int
    credit_stalls: int
    transferred: int
    reads: int
    dropped_items: int
    reader_dropped: bool
    writer_dropped: bool
    frozen: bool = False
    duplicate_writes: int = 0


class Stream(Generic[T]):
    """A typed, thread-safe, credit-limited, explicitly terminated stream.

    ``write`` is non-blocking. If no credit is available it raises
    :class:`CreditExhausted`; the scheduler/ABI owns waiting and wake-up policy.
    ``read`` returns ``NOT_READY`` while the writer is live and no item is buffered,
    and returns ``None`` only after graceful end-of-stream has been observed.
    """

    def __init__(self, element_type: type[T], *, config: StreamConfig | None = None,
                 tenant: str = "default", workload: str = "default", stream_id: str | None = None) -> None:
        if not isinstance(element_type, type):
            raise TypeError("element_type must be a runtime type")
        if config is not None and not isinstance(config, StreamConfig):
            raise TypeError("config must be a StreamConfig")
        self.element_type = element_type
        self.config = config or StreamConfig()
        self.tenant = tenant
        self.workload = workload
        self.stream_id = stream_id or f"s{next(_IDS)}"
        self.frozen = False
        self.freeze_reason = ""
        self.duplicate_writes = 0
        self._seen_keys: deque[str] = deque()
        self._seen_set: set[str] = set()
        self.credit = 0
        self.buffer: deque[T] = deque()
        self.ended = False
        self.reader_dropped = False
        self.writer_dropped = False
        self.credit_stalls = 0
        self.transferred = 0
        self.reads = 0
        self.dropped_items = 0
        self._lock = RLock()
        self._cond = Condition(self._lock)
        self._waiting = 0  # blocked read_wait/write_wait callers; skip notify when zero (hot path)

    def grant(self, n: int) -> None:
        """Reader-side: allow the writer ``n`` additional elements."""
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError(f"credit must be a positive integer, got {n!r}")
        with self._lock:
            if self.reader_dropped:
                raise EndDropped("reader end has been dropped", end="reader")
            if self.ended or self.writer_dropped:
                raise StreamClosed("cannot grant credit after writer termination")
            self._check_frozen()
            new_credit = self.credit + n
            if new_credit > self.config.max_credit:
                raise CreditLimitExceeded(
                    "credit grant exceeds configured outstanding-credit limit",
                    requested=n,
                    current=self.credit,
                    max_credit=self.config.max_credit,
                )
            self.credit = new_credit
            self._wake()

    def write(self, element: T, *, idempotency_key: str | None = None) -> bool:
        """Writer-side: enqueue one typed element when both credit and capacity exist.

        Returns ``True`` when the element was enqueued. When ``idempotency_key`` repeats a
        key accepted within the configured window the retry is acknowledged with
        ``False`` and consumes no credit (exactly-once enqueue for retried writes).
        """
        with self._lock:
            if self.reader_dropped:
                raise EndDropped("reader end has been dropped", end="reader")
            if self.writer_dropped:
                raise EndDropped("writer end has been dropped", end="writer")
            if self.ended:
                raise StreamClosed("stream already ended")
            self._check_frozen()
            if not isinstance(element, self.element_type) or (
                isinstance(element, bool) and self.element_type is not bool
            ):
                raise ElementTypeMismatch(
                    f"{type(element).__name__} on a stream of {self.element_type.__name__}",
                    expected=self.element_type.__name__,
                    actual=type(element).__name__,
                )
            if idempotency_key is not None:
                if not isinstance(idempotency_key, str) or not idempotency_key:
                    raise ValueError("idempotency_key must be a non-empty string")
                if idempotency_key in self._seen_set:
                    self.duplicate_writes += 1
                    return False
            if self.credit <= 0:
                self.credit_stalls += 1
                raise CreditExhausted("no credit; reader has not asked for more", credit=0)
            if len(self.buffer) >= self.config.max_buffer:
                raise BufferLimitExceeded(
                    "in-flight buffer reached configured limit",
                    buffered=len(self.buffer),
                    max_buffer=self.config.max_buffer,
                )
            self.credit -= 1
            self.buffer.append(element)
            self.transferred += 1
            if idempotency_key is not None:
                self._remember(idempotency_key)
            self._wake()
            return True

    def read(self) -> T | None | object:
        """Reader-side: return a value, ``NOT_READY``, graceful EOF, or a drop error."""
        with self._lock:
            if self.reader_dropped:
                raise EndDropped("reader end has been dropped", end="reader")
            if self.buffer:
                self.reads += 1
                value = self.buffer.popleft()
                self._wake()
                return value
            if self.writer_dropped:
                raise EndDropped("writer end has been dropped", end="writer")
            if self.ended:
                return None
            return NOT_READY

    def end(self) -> None:
        """Writer-side graceful EOF. Buffered values remain drainable before ``None``."""
        with self._lock:
            if self.reader_dropped:
                raise EndDropped("reader end has been dropped", end="reader")
            if self.writer_dropped:
                raise EndDropped("writer end has been dropped", end="writer")
            self.ended = True
            self.credit = 0
            self._wake()

    def drop_reader(self) -> None:
        """Drop the reader and eagerly release any now-undeliverable buffered values."""
        with self._lock:
            if self.reader_dropped:
                return
            self.reader_dropped = True
            self.dropped_items += len(self.buffer)
            self.buffer.clear()
            self.credit = 0
            self._wake()

    def drop_writer(self) -> None:
        """Drop the writer abruptly. Buffered values may still be drained first."""
        with self._lock:
            if self.writer_dropped:
                return
            self.writer_dropped = True
            self.credit = 0
            self._wake()

    @property
    def state(self) -> str:
        with self._lock:
            if self.reader_dropped:
                return "reader_dropped"
            if self.writer_dropped:
                return "writer_dropped"
            if self.ended:
                return "ended"
            if self.frozen:
                return "frozen"
            if self.credit == 0:
                return "credit_stalled"
            return "open"

    def stats(self) -> StreamStats:
        """Return a consistent snapshot suitable for metrics/diagnostics adapters."""
        with self._lock:
            return StreamStats(
                state=self.state,
                credit=self.credit,
                buffered=len(self.buffer),
                credit_stalls=self.credit_stalls,
                transferred=self.transferred,
                reads=self.reads,
                dropped_items=self.dropped_items,
                reader_dropped=self.reader_dropped,
                writer_dropped=self.writer_dropped,
                frozen=self.frozen,
                duplicate_writes=self.duplicate_writes,
            )

    # -- helpers ---------------------------------------------------------------
    def _wake(self) -> None:
        if self._waiting:
            self._cond.notify_all()

    def _check_frozen(self) -> None:
        if self.frozen:
            raise StreamFrozen("stream is quarantined", reason=self.freeze_reason, stream_id=self.stream_id)

    def _remember(self, key: str) -> None:
        self._seen_keys.append(key)
        self._seen_set.add(key)
        while len(self._seen_keys) > self.config.idempotency_window:
            self._seen_set.discard(self._seen_keys.popleft())

    # -- emergency control ----------------------------------------------------
    def freeze(self, reason: str) -> None:
        """Quarantine: refuse new grants/writes; buffered values stay drainable."""
        with self._lock:
            self.frozen = True
            self.freeze_reason = reason
            self._wake()

    def unfreeze(self) -> None:
        with self._lock:
            self.frozen = False
            self.freeze_reason = ""
            self._wake()

    # -- bounded blocking operations (timeout + cancellation) -------------------
    def _wait(self, ready, timeout: float | None, cancel: CancelToken | None, op: str) -> None:
        if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout < 0):
            raise ValueError("timeout must be a non-negative number or None")
        deadline = None if timeout is None else time.monotonic() + timeout
        while not ready():
            if cancel is not None and cancel.cancelled:
                raise StreamCancelled(f"{op} cancelled", reason=cancel.reason, stream_id=self.stream_id)
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                raise StreamTimeout(f"{op} timed out", timeout=timeout, stream_id=self.stream_id)
            # Poll in short slices so cancellation is observed without a separate notifier.
            self._waiting += 1
            try:
                self._cond.wait(0.05 if remaining is None else min(remaining, 0.05))
            finally:
                self._waiting -= 1

    def read_wait(self, timeout: float | None = None, cancel: CancelToken | None = None) -> T | None | object:
        """Block until a value, EOF, or drop is observable; never infers EOF from timeout."""
        with self._lock:
            self._wait(lambda: bool(self.buffer) or self.ended or self.writer_dropped or self.reader_dropped,
                       timeout, cancel, "read")
            return self.read()

    def write_wait(self, element: T, timeout: float | None = None, cancel: CancelToken | None = None,
                   *, idempotency_key: str | None = None) -> bool:
        """Block until credit and capacity exist (or the stream terminates), then write."""
        with self._lock:
            self._wait(lambda: (self.credit > 0 and len(self.buffer) < self.config.max_buffer)
                       or self.ended or self.writer_dropped or self.reader_dropped or self.frozen
                       or (idempotency_key is not None and idempotency_key in self._seen_set),
                       timeout, cancel, "write")
            return self.write(element, idempotency_key=idempotency_key)
