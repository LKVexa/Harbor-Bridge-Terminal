"""Bounded retry, circuit breaking, admission control and deadlines
(INV-40-C025, C053, C054, C017, C067).
"""
from __future__ import annotations

import random
import threading
import time
from collections import defaultdict

from .errors import OpError


class Deadline:
    def __init__(self, ms: int, clock=time.monotonic):
        self.clock, self.end = clock, clock() + ms / 1000.0
        self.cancelled = False

    def remaining_ms(self) -> int:
        return max(0, int((self.end - self.clock()) * 1000))

    def check(self) -> None:
        if self.cancelled:
            raise OpError("PK_FULL_VM_CANCELLED", "operation cancelled")
        if self.clock() >= self.end:
            raise OpError("PK_FULL_VM_TIMEOUT", "deadline exceeded")

    def cancel(self) -> None:
        self.cancelled = True


def retry(fn, *, attempts: int, idempotent: bool, deadline: Deadline | None = None,
          base_ms: int = 50, cap_ms: int = 2000, rng: random.Random | None = None, sleep=time.sleep,
          on_retry=None):
    """Retry only retryable errors and only when the operation is idempotent.
    Full-jitter exponential backoff, bounded by attempts and the deadline."""
    rng = rng or random.Random()
    for n in range(1, attempts + 1):
        if deadline:
            deadline.check()
        try:
            return fn()
        except OpError as exc:
            if not exc.retryable or not idempotent or n == attempts:
                raise
            delay = rng.uniform(0, min(cap_ms, base_ms * (2 ** (n - 1)))) / 1000.0
            if deadline and delay * 1000 >= deadline.remaining_ms():
                raise
            if on_retry:
                on_retry(n, exc, delay)
            sleep(delay)
    raise AssertionError("unreachable")


class CircuitBreaker:
    def __init__(self, threshold: int, reset_ms: int, clock=time.monotonic):
        self.threshold, self.reset_s, self.clock = threshold, reset_ms / 1000.0, clock
        self.failures, self.opened_at, self.state = 0, None, "closed"
        self._lock = threading.Lock()

    def before(self) -> None:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_s:
                    self.state = "half_open"
                else:
                    raise OpError("PK_FULL_VM_CIRCUIT_OPEN", "provider circuit open",
                                  retry_after_ms=int((self.reset_s - (self.clock() - self.opened_at)) * 1000))

    def success(self) -> None:
        with self._lock:
            self.failures, self.state, self.opened_at = 0, "closed", None

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == "half_open" or self.failures >= self.threshold:
                self.state, self.opened_at = "open", self.clock()


class Admission:
    """Bounded concurrency + bounded queue + per-tenant quotas (fairness: no
    tenant may hold more than its guest/memory quota, so one tenant cannot
    starve others of admission slots it has not been granted)."""

    def __init__(self, max_concurrent: int, max_queue: int, guest_quota: int, memory_quota_mib: int):
        self.max_concurrent, self.max_queue = max_concurrent, max_queue
        self.guest_quota, self.memory_quota = guest_quota, memory_quota_mib
        self._sem = threading.BoundedSemaphore(max_concurrent)
        self._lock = threading.Lock()
        self.waiting = 0
        self.in_flight = 0
        self.guests = defaultdict(int)
        self.memory = defaultdict(int)
        self.shed = 0

    def acquire(self, timeout_s: float) -> None:
        with self._lock:
            if self.waiting >= self.max_queue and self.in_flight >= self.max_concurrent:
                self.shed += 1
                raise OpError("PK_FULL_VM_OVERLOADED", "queue full; request shed",
                              in_flight=self.in_flight, waiting=self.waiting)
            self.waiting += 1
        got = self._sem.acquire(timeout=timeout_s)
        with self._lock:
            self.waiting -= 1
            if not got:
                self.shed += 1
                raise OpError("PK_FULL_VM_OVERLOADED", "admission wait timed out")
            self.in_flight += 1

    def release(self) -> None:
        with self._lock:
            self.in_flight -= 1
        self._sem.release()

    def reserve(self, tenant: str, memory_mib: int) -> None:
        with self._lock:
            if self.guests[tenant] + 1 > self.guest_quota:
                raise OpError("PK_FULL_VM_QUOTA_EXCEEDED", "tenant guest quota", tenant=tenant, quota=self.guest_quota)
            if self.memory[tenant] + memory_mib > self.memory_quota:
                raise OpError("PK_FULL_VM_QUOTA_EXCEEDED", "tenant memory quota", tenant=tenant, quota_mib=self.memory_quota)
            self.guests[tenant] += 1
            self.memory[tenant] += memory_mib

    def unreserve(self, tenant: str, memory_mib: int) -> None:
        with self._lock:
            self.guests[tenant] = max(0, self.guests[tenant] - 1)
            self.memory[tenant] = max(0, self.memory[tenant] - memory_mib)
