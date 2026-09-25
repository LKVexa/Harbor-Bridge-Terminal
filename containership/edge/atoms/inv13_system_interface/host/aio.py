"""MC-013 -- async polling, cancellation, timeout and backpressure.

``BoundedStream`` is a pollable byte-message stream with a hard capacity: a
full stream refuses writes with BACKPRESSURE (never grows).  ``CancelScope``
propagates cancellation to children.  ``call_with_deadline`` runs a coroutine
under a deadline and maps expiry / cancellation to TIMED_OUT / CANCELLED.
Operations are marked idempotent-or-not so a retry helper refuses to retry
non-idempotent ones.
"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Awaitable, Callable

from .errors import ErrorCode, Inv13Error


class CancelScope:
    def __init__(self, parent: "CancelScope | None" = None) -> None:
        self._cancelled = False
        self._children: list[CancelScope] = []
        self._waiters: list[asyncio.Future] = []
        if parent is not None:
            parent._children.append(self)
            if parent.cancelled:
                self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        if self._cancelled:
            return
        self._cancelled = True
        for w in self._waiters:
            if not w.done():
                w.cancel()
        for c in self._children:
            c.cancel()

    def check(self) -> None:
        if self._cancelled:
            raise Inv13Error(ErrorCode.CANCELLED)


class BoundedStream:
    def __init__(self, capacity: int = 64, max_item: int = 65536) -> None:
        self.capacity, self.max_item = capacity, max_item
        self._q: deque[bytes] = deque()
        self._closed = False
        self._readable: asyncio.Event | None = None

    def _ev(self) -> asyncio.Event:
        if self._readable is None:
            self._readable = asyncio.Event()
        return self._readable

    def poll_writable(self) -> bool:
        return not self._closed and len(self._q) < self.capacity

    def poll_readable(self) -> bool:
        return bool(self._q) or self._closed

    def write(self, item: bytes) -> None:
        if self._closed:
            raise Inv13Error(ErrorCode.INVALID_HANDLE, "closed")
        if len(item) > self.max_item:
            raise Inv13Error(ErrorCode.TOO_LONG)
        if len(self._q) >= self.capacity:
            raise Inv13Error(ErrorCode.BACKPRESSURE)
        self._q.append(bytes(item))
        self._ev().set()

    def close(self) -> None:
        self._closed = True
        self._ev().set()

    async def read(self, scope: CancelScope | None = None) -> bytes | None:
        while not self._q:
            if self._closed:
                return None
            if scope:
                scope.check()
            ev = self._ev()
            ev.clear()
            fut = asyncio.ensure_future(ev.wait())
            if scope:
                scope._waiters.append(fut)
            try:
                await fut
            except asyncio.CancelledError:
                if scope and scope.cancelled:
                    raise Inv13Error(ErrorCode.CANCELLED) from None
                raise
            finally:
                if scope and fut in scope._waiters:
                    scope._waiters.remove(fut)
        return self._q.popleft()


async def call_with_deadline(coro: Awaitable[Any], timeout: float) -> Any:
    if timeout <= 0:
        raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "timeout")
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        raise Inv13Error(ErrorCode.TIMED_OUT) from None


async def retry(op: Callable[[], Awaitable[Any]], *, idempotent: bool, attempts: int = 3,
                backoff: float = 0.01) -> Any:
    last: Inv13Error | None = None
    for i in range(attempts if idempotent else 1):
        try:
            return await op()
        except Inv13Error as e:
            last = e
            if not e.retryable or not idempotent:
                raise
            await asyncio.sleep(backoff * (2 ** i))
    assert last is not None
    raise last
