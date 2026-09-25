"""Runtime implementation for INV-17's typed, credit-limited stream primitive.

This module intentionally has no ``pk_core`` dependency so the data-plane primitive can
be embedded and tested independently from its certification/assessment adapter.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import RLock
from types import MappingProxyType
from typing import Deque, Generic, Mapping, TypeVar, cast

T = TypeVar("T")
NOT_READY = Ellipsis


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


@dataclass(frozen=True, slots=True)
class StreamConfig:
    """Immutable resource limits for one stream instance."""

    max_credit: int = 1024
    max_buffer: int = 1024

    def __post_init__(self) -> None:
        for name, value in (("max_credit", self.max_credit), ("max_buffer", self.max_buffer)):
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


class Stream(Generic[T]):
    """A typed, thread-safe, credit-limited, explicitly terminated stream.

    ``write`` is non-blocking. If no credit is available it raises
    :class:`CreditExhausted`; the scheduler/ABI owns waiting and wake-up policy.
    ``read`` returns ``NOT_READY`` while the writer is live and no item is buffered,
    and returns ``None`` only after graceful end-of-stream has been observed.
    """

    def __init__(self, element_type: type[T], *, config: StreamConfig | None = None) -> None:
        if not isinstance(element_type, type):
            raise TypeError("element_type must be a runtime type")
        self.element_type = element_type
        self.config = config or StreamConfig()
        self.credit = 0
        self.buffer: Deque[T] = deque()
        self.ended = False
        self.reader_dropped = False
        self.writer_dropped = False
        self.credit_stalls = 0
        self.transferred = 0
        self.reads = 0
        self.dropped_items = 0
        self._lock = RLock()

    def grant(self, n: int) -> None:
        """Reader-side: allow the writer ``n`` additional elements."""
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError(f"credit must be a positive integer, got {n!r}")
        with self._lock:
            if self.reader_dropped:
                raise EndDropped("reader end has been dropped", end="reader")
            if self.ended or self.writer_dropped:
                raise StreamClosed("cannot grant credit after writer termination")
            new_credit = self.credit + n
            if new_credit > self.config.max_credit:
                raise CreditLimitExceeded(
                    "credit grant exceeds configured outstanding-credit limit",
                    requested=n,
                    current=self.credit,
                    max_credit=self.config.max_credit,
                )
            self.credit = new_credit

    def write(self, element: T) -> None:
        """Writer-side: enqueue one typed element when both credit and capacity exist."""
        with self._lock:
            if self.reader_dropped:
                raise EndDropped("reader end has been dropped", end="reader")
            if self.writer_dropped:
                raise EndDropped("writer end has been dropped", end="writer")
            if self.ended:
                raise StreamClosed("stream already ended")
            if not isinstance(element, self.element_type) or (
                isinstance(element, bool) and self.element_type is not bool
            ):
                raise ElementTypeMismatch(
                    f"{type(element).__name__} on a stream of {self.element_type.__name__}",
                    expected=self.element_type.__name__,
                    actual=type(element).__name__,
                )
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

    def read(self) -> T | None | object:
        """Reader-side: return a value, ``NOT_READY``, graceful EOF, or a drop error."""
        with self._lock:
            if self.reader_dropped:
                raise EndDropped("reader end has been dropped", end="reader")
            if self.buffer:
                self.reads += 1
                return self.buffer.popleft()
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

    def drop_reader(self) -> None:
        """Drop the reader and eagerly release any now-undeliverable buffered values."""
        with self._lock:
            if self.reader_dropped:
                return
            self.reader_dropped = True
            self.dropped_items += len(self.buffer)
            self.buffer.clear()
            self.credit = 0

    def drop_writer(self) -> None:
        """Drop the writer abruptly. Buffered values may still be drained first."""
        with self._lock:
            if self.writer_dropped:
                return
            self.writer_dropped = True
            self.credit = 0

    @property
    def state(self) -> str:
        with self._lock:
            if self.reader_dropped:
                return "reader_dropped"
            if self.writer_dropped:
                return "writer_dropped"
            if self.ended:
                return "ended"
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
            )
