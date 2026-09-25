"""Backpressure and load shedding (GAP04-C30).

``Admission``: bounded concurrency + bounded wait queue; excess requests are
shed immediately with GAP04-E0700 (never unbounded buffering). ``RetryBudget``:
retries are limited to a percentage of recent first attempts so retry storms
cannot amplify an outage. ``CircuitBreaker``: closed -> open after N
consecutive failures, half-open probe after a cool-down, per dependency.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Callable

from .errors import Gap04Error, Overloaded


class Admission:
    def __init__(self, max_concurrency: int, max_queue: int, wait_s: float = 0.5):
        self._sem = threading.BoundedSemaphore(max_concurrency)
        self._q = threading.Semaphore(max_concurrency + max_queue)
        self.wait_s = wait_s
        self.rejected = 0

    @contextmanager
    def slot(self):
        if not self._q.acquire(blocking=False):
            self.rejected += 1
            raise Overloaded("admission queue full")
        try:
            if not self._sem.acquire(timeout=self.wait_s):
                self.rejected += 1
                raise Overloaded("concurrency limit wait exceeded")
            try:
                yield
            finally:
                self._sem.release()
        finally:
            self._q.release()


class RetryBudget:
    def __init__(self, percent: int = 10, window_s: float = 60.0, min_retries: int = 3, clock=time.monotonic):
        self.percent, self.window, self.min = percent, window_s, min_retries
        self.clock = clock
        self._first: deque[float] = deque()
        self._retry: deque[float] = deque()
        self._lock = threading.Lock()

    def _trim(self, now):
        for d in (self._first, self._retry):
            while d and d[0] < now - self.window:
                d.popleft()

    def record_attempt(self) -> None:
        with self._lock:
            now = self.clock(); self._trim(now); self._first.append(now)

    def try_retry(self) -> bool:
        with self._lock:
            now = self.clock(); self._trim(now)
            allowed = max(self.min, len(self._first) * self.percent // 100)
            if len(self._retry) >= allowed:
                return False
            self._retry.append(now)
            return True


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, reset_after_s: float = 30.0, clock=time.monotonic):
        self.name, self.threshold, self.reset_after, self.clock = name, failure_threshold, reset_after_s, clock
        self.state, self.failures, self.opened_at = "closed", 0, 0.0
        self._lock = threading.Lock()

    def call(self, fn: Callable, *a, **kw):
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_after:
                    self.state = "half-open"
                else:
                    raise Gap04Error(f"circuit open for {self.name}", code="GAP04-E0701", details={"dependency": self.name})
        try:
            r = fn(*a, **kw)
        except Exception:
            with self._lock:
                self.failures += 1
                if self.state == "half-open" or self.failures >= self.threshold:
                    self.state, self.opened_at = "open", self.clock()
            raise
        with self._lock:
            self.state, self.failures = "closed", 0
        return r
