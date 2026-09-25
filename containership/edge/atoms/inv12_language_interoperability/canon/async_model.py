"""MC-017 async / future / stream boundary semantics (reference model).

Future<T> state machine::

    PENDING --resolve(v)--> READY --read--> CONSUMED
    PENDING --cancel------> CANCELLED      (reader gets PK_INTEROP_CANCELLED)
    PENDING --writer drop--> DROPPED       (reader gets PK_INTEROP_ASYNC)
    any other transition -> PK_INTEROP_ASYNC

Stream<T> has a bounded window (backpressure): ``write`` blocks until space is
available or the timeout elapses (``PK_INTEROP_LIMIT``, retryable); ``read``
blocks until an element, close or cancel.  Every written element is validated
against ``T`` and copied (no alias) *before* it is enqueued, and the element is
owned by the reader once read (exactly-once delivery, FIFO).  ``cancel`` wakes
all waiters deterministically and discards buffered elements; the number
discarded is reported for accounting.
"""
from __future__ import annotations

import collections
import threading
import time

from .errors import AsyncError, InteropError, LimitError
from .limits import HARD_CEILING
from .validate import validate


def _cancelled():
    return InteropError("operation was cancelled", code="PK_INTEROP_CANCELLED")


class Future:
    def __init__(self, elem_type=None, *, limits=HARD_CEILING):
        self.elem_type = elem_type
        self.limits = limits
        self.state = "PENDING"
        self._value = None
        self._cv = threading.Condition()

    def resolve(self, value):
        v = validate(value, self.elem_type, limits=self.limits) if self.elem_type else None
        with self._cv:
            if self.state != "PENDING":
                raise AsyncError(f"cannot resolve a future in state {self.state}")
            self._value, self.state = v, "READY"
            self._cv.notify_all()

    def cancel(self):
        with self._cv:
            if self.state == "PENDING":
                self.state = "CANCELLED"
                self._cv.notify_all()
                return True
            return False

    def drop_writer(self):
        with self._cv:
            if self.state == "PENDING":
                self.state = "DROPPED"
                self._cv.notify_all()

    def read(self, timeout: float | None = None):
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._cv:
            while self.state == "PENDING":
                rem = None if deadline is None else deadline - time.monotonic()
                if rem is not None and rem <= 0:
                    raise LimitError("future read timed out")
                self._cv.wait(rem)
            if self.state == "READY":
                v, self._value, self.state = self._value, None, "CONSUMED"
                return v
            if self.state == "CANCELLED":
                raise _cancelled()
            raise AsyncError(f"future is {self.state}")


class Stream:
    def __init__(self, elem_type=None, *, window: int = 64, limits=HARD_CEILING):
        if type(window) is not int or not 0 < window <= limits.max_stream_window:
            raise LimitError("stream window outside the configured limit")
        self.elem_type = elem_type
        self.limits = limits
        self.window = window
        self._buf = collections.deque()
        self._cv = threading.Condition()
        self.state = "OPEN"
        self.written = 0
        self.read_count = 0
        self.discarded = 0

    def write(self, value, timeout: float | None = None):
        v = validate(value, self.elem_type, limits=self.limits) if self.elem_type else None
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._cv:
            while self.state == "OPEN" and len(self._buf) >= self.window:
                rem = None if deadline is None else deadline - time.monotonic()
                if rem is not None and rem <= 0:
                    raise LimitError("stream backpressure: window full", retryable=True)
                self._cv.wait(rem)
            if self.state == "CANCELLED":
                raise _cancelled()
            if self.state != "OPEN":
                raise AsyncError(f"write to a stream in state {self.state}")
            self._buf.append(v)
            self.written += 1
            self._cv.notify_all()

    def close(self):
        with self._cv:
            if self.state != "OPEN":
                raise AsyncError(f"close of a stream in state {self.state}")
            self.state = "CLOSED"
            self._cv.notify_all()

    def cancel(self):
        with self._cv:
            if self.state in ("OPEN", "CLOSED"):
                self.discarded += len(self._buf)
                self._buf.clear()
                self.state = "CANCELLED"
                self._cv.notify_all()

    def read(self, timeout: float | None = None):
        """Return the next element, or raise StopIteration at end of stream."""
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._cv:
            while not self._buf and self.state == "OPEN":
                rem = None if deadline is None else deadline - time.monotonic()
                if rem is not None and rem <= 0:
                    raise LimitError("stream read timed out", retryable=True)
                self._cv.wait(rem)
            if self._buf:
                v = self._buf.popleft()
                self.read_count += 1
                self._cv.notify_all()
                return v
            if self.state == "CANCELLED":
                raise _cancelled()
            raise StopIteration
