"""Controller work queue (component 3) with rate-limited requeue (34, 35).

Semantics match client-go's workqueue: a key is never processed by two
workers at once; adding a key that is processing marks it dirty so it is
re-queued exactly once when ``done`` is called; ``shutdown`` stops intake and
lets ``get`` drain remaining items then return ``None``.
"""
from __future__ import annotations

import heapq
import threading
import time
from collections import deque
from typing import Callable, Hashable

from .resilience import Backoff


class WorkQueue:
    def __init__(self, *, max_depth: int = 10_000, clock: Callable[[], float] = time.monotonic,
                 backoff: Backoff | None = None, max_retries: int = 15):
        self._cv = threading.Condition()
        self._queue: deque[Hashable] = deque()
        self._dirty: set[Hashable] = set()
        self._processing: set[Hashable] = set()
        self._delayed: list[tuple[float, int, Hashable]] = []
        self._seq = 0
        self._retries: dict[Hashable, int] = {}
        self._shutdown = False
        self.max_depth = max_depth
        self.max_retries = max_retries
        self.clock = clock
        self.backoff = backoff or Backoff(base=0.005, cap=60.0, jitter=0.0)
        self.dropped = 0
        self.added_at: dict[Hashable, float] = {}

    # ----------------------------------------------------------------- intake
    def add(self, key: Hashable) -> bool:
        """Enqueue ``key``; returns False when shut down or shed for backpressure."""
        with self._cv:
            if self._shutdown:
                return False
            if key in self._dirty:
                return True  # deduplicated
            if len(self._queue) >= self.max_depth and key not in self._processing:
                self.dropped += 1
                return False
            self._dirty.add(key)
            self.added_at.setdefault(key, self.clock())
            if key not in self._processing:
                self._queue.append(key)
                self._cv.notify()
            return True

    def add_after(self, key: Hashable, delay: float) -> None:
        with self._cv:
            if self._shutdown:
                return
            self._seq += 1
            heapq.heappush(self._delayed, (self.clock() + max(0.0, delay), self._seq, key))
            self._cv.notify()

    def add_rate_limited(self, key: Hashable) -> bool:
        """Requeue with exponential backoff; returns False once retries are exhausted."""
        with self._cv:
            n = self._retries.get(key, 0)
            if n >= self.max_retries:
                return False
            self._retries[key] = n + 1
        self.add_after(key, self.backoff.delay(n))
        return True

    def forget(self, key: Hashable) -> None:
        with self._cv:
            self._retries.pop(key, None)

    def num_requeues(self, key: Hashable) -> int:
        with self._cv:
            return self._retries.get(key, 0)

    # --------------------------------------------------------------- dispatch
    def _promote(self) -> float | None:
        now = self.clock()
        while self._delayed and self._delayed[0][0] <= now:
            _, _, key = heapq.heappop(self._delayed)
            if key not in self._dirty:
                self._dirty.add(key)
                self.added_at.setdefault(key, now)
                if key not in self._processing:
                    self._queue.append(key)
        return self._delayed[0][0] - now if self._delayed else None

    def get(self, timeout: float | None = None) -> Hashable | None:
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._cv:
            while True:
                wait = self._promote()
                if self._queue:
                    key = self._queue.popleft()
                    self._processing.add(key)
                    self._dirty.discard(key)
                    return key
                if self._shutdown:
                    return None
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return None
                slices = [x for x in (wait, remaining, 0.05) if x is not None]
                self._cv.wait(min(slices))

    def done(self, key: Hashable) -> None:
        with self._cv:
            self._processing.discard(key)
            if key in self._dirty:
                self._queue.append(key)
                self._cv.notify()
            else:
                self.added_at.pop(key, None)

    def shutdown(self) -> None:
        with self._cv:
            self._shutdown = True
            self._cv.notify_all()

    # ---------------------------------------------------------- introspection
    def depth(self) -> int:
        with self._cv:
            return len(self._queue)

    def in_flight(self) -> int:
        with self._cv:
            return len(self._processing)

    def oldest_age(self) -> float:
        with self._cv:
            if not self.added_at:
                return 0.0
            return self.clock() - min(self.added_at.values())


def run_workers(queue: WorkQueue, handler: Callable[[Hashable], None], *, workers: int = 2,
                on_error: Callable[[Hashable, BaseException], None] | None = None) -> list[threading.Thread]:
    """Start bounded worker threads. Handler exceptions requeue with backoff."""

    def loop() -> None:
        while True:
            key = queue.get()
            if key is None:
                return
            try:
                handler(key)
                queue.forget(key)
            except BaseException as exc:  # noqa: BLE001 - worker must survive handler faults
                if on_error:
                    on_error(key, exc)
                queue.add_rate_limited(key)
            finally:
                queue.done(key)

    threads = [threading.Thread(target=loop, name=f"inv04-worker-{i}", daemon=True) for i in range(workers)]
    for t in threads:
        t.start()
    return threads
