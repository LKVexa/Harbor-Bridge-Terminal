"""Admission control, load shedding, circuit breaking, retry policy, deadlines.

INV-68 MC-18 (C053, C054), MC-07 (C025), MC-19 (C056).

Applicability (the MC-18 N/A question, answered with evidence): the *engine*
is a synchronous pure function and owns none of these boundaries.  The
*service boundary* (``service.py``) does -- it is where concurrent callers,
queues, deadlines and a remote capacity source meet -- so the mechanisms live
here and are exercised by ``tests/test_v43.py`` and ``tools/faults.py``.

* :class:`Admission` -- ``max_concurrency`` in-flight requests plus a bounded
  wait queue of ``max_queue``; anything beyond is shed immediately with
  ``OVERLOADED`` (no unbounded buffering).  Queue waits honour the request
  deadline.
* :class:`CircuitBreaker` -- closed -> open after ``failure_threshold``
  consecutive failures, open -> half-open after ``reset_after_s``, one probe in
  half-open; ``CIRCUIT_OPEN`` while open.
* :class:`Deadline` -- absolute monotonic deadline + cooperative cancellation;
  the service checks it between phases and raises ``DEADLINE_EXCEEDED`` or
  ``CANCELLED``.
* :func:`backoff_schedule` -- the *client* retry policy published in
  ``INTERFACES.md``: bounded exponential backoff with full jitter, only for
  codes whose registry entry says ``retryable``.
"""
from __future__ import annotations

import random
import threading
import time
from typing import Callable

from .errors import REGISTRY, PackError


class Deadline:
    def __init__(self, timeout_ms: float, *, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self.expires = clock() + max(0.0, timeout_ms) / 1000.0
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def remaining_s(self) -> float:
        return self.expires - self._clock()

    def check(self, phase: str = "") -> None:
        if self._cancelled.is_set():
            raise PackError("CANCELLED", details={"phase": phase})
        if self._clock() >= self.expires:
            raise PackError("DEADLINE_EXCEEDED", details={"phase": phase})


class Admission:
    def __init__(self, max_concurrency: int, max_queue: int):
        self.max_concurrency = max_concurrency
        self.max_queue = max_queue
        self._cv = threading.Condition()
        self.in_flight = 0
        self.waiting = 0
        self.shed = 0
        self.peak_in_flight = 0

    def reconfigure(self, max_concurrency: int, max_queue: int) -> None:
        with self._cv:
            self.max_concurrency, self.max_queue = max_concurrency, max_queue
            self._cv.notify_all()

    def acquire(self, deadline: Deadline) -> None:
        with self._cv:
            if self.in_flight < self.max_concurrency and self.waiting == 0:
                self.in_flight += 1
                self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
                return
            if self.waiting >= self.max_queue:
                self.shed += 1
                raise PackError("OVERLOADED", details={"in_flight": self.in_flight, "queued": self.waiting})
            self.waiting += 1
            try:
                while self.in_flight >= self.max_concurrency:
                    remaining = deadline.remaining_s()
                    if remaining <= 0 or deadline.cancelled:
                        self.shed += 1
                        deadline.check("admission")
                    self._cv.wait(timeout=min(max(remaining, 0.0), 0.05))
                self.in_flight += 1
                self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
            finally:
                self.waiting -= 1

    def release(self) -> None:
        with self._cv:
            self.in_flight -= 1
            self._cv.notify()


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, name: str, *, failure_threshold: int = 3, reset_after_s: float = 5.0,
                 clock: Callable[[], float] = time.monotonic):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_after_s = reset_after_s
        self._clock = clock
        self._lock = threading.Lock()
        self.state = self.CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self._probe_out = False

    def before(self) -> None:
        with self._lock:
            if self.state == self.OPEN:
                if self._clock() - self.opened_at >= self.reset_after_s:
                    self.state, self._probe_out = self.HALF_OPEN, False
                else:
                    raise PackError("CIRCUIT_OPEN", details={"dependency": self.name})
            if self.state == self.HALF_OPEN:
                if self._probe_out:
                    raise PackError("CIRCUIT_OPEN", details={"dependency": self.name, "probe": "in_flight"})
                self._probe_out = True

    def success(self) -> None:
        with self._lock:
            self.state, self.failures, self._probe_out = self.CLOSED, 0, False

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == self.HALF_OPEN or self.failures >= self.failure_threshold:
                self.state, self.opened_at, self._probe_out = self.OPEN, self._clock(), False

    def call(self, fn: Callable[[], object]) -> object:
        self.before()
        try:
            out = fn()
        except PackError:
            self.failure()
            raise
        except Exception as exc:
            self.failure()
            raise PackError("CIRCUIT_OPEN" if self.state == self.OPEN else "DEPENDENCY_UNAVAILABLE",
                            f"{self.name} dependency failed", details={"error": type(exc).__name__}) from exc
        self.success()
        return out


def backoff_schedule(attempts: int = 5, *, base_ms: float = 50, cap_ms: float = 2_000,
                     rng: random.Random | None = None) -> list[float]:
    """Full-jitter exponential backoff delays (ms) for ``attempts`` retries."""
    rng = rng or random.Random()
    return [rng.uniform(0, min(cap_ms, base_ms * (2 ** i))) for i in range(max(0, min(attempts, 10)))]


def should_retry(code: str) -> bool:
    spec = REGISTRY.get(code)
    return bool(spec and spec.retryable)
