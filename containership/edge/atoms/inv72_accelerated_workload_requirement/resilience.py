"""Deadlines, cancellation, admission control, retry and circuit breaking (C025, C053, C054).

* ``Deadline`` - absolute monotonic deadline; ``check()`` raises ``ACCEL_DEADLINE_EXCEEDED``.
* ``CancelToken`` - cooperative cancellation; ``check()`` raises ``ACCEL_CANCELLED``.
* ``Admission`` - token bucket (rate/burst) per tenant plus a global in-flight cap; excess is shed
  with ``ACCEL_OVERLOADED`` before any work is done, and one tenant's burst cannot starve another
  (per-tenant buckets = fairness, C017).
* ``retry`` - bounded attempts, exponential backoff with full jitter, deadline-aware; retries only
  errors whose registered outcome is ``retryable`` and only operations the caller declares idempotent.
* ``CircuitBreaker`` - closed -> open after N consecutive failures -> half-open after a cool-down ->
  closed on success.  Used around discovery (GAP-02) and telemetry export.
"""
from __future__ import annotations

import random
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from .errors import AccelError

T = TypeVar("T")


@dataclass
class Deadline:
    at: float
    clock: Callable[[], float] = time.monotonic

    @classmethod
    def after(cls, ms: int, clock: Callable[[], float] = time.monotonic) -> "Deadline":
        if isinstance(ms, bool) or not isinstance(ms, int) or not 1 <= ms <= 60_000:
            raise AccelError("ACCEL_INVALID_REQUIREMENT", "deadline_ms must be an integer in 1..60000")
        return cls(clock() + ms / 1000.0, clock)

    def remaining(self) -> float:
        return self.at - self.clock()

    def check(self) -> None:
        if self.remaining() <= 0:
            raise AccelError("ACCEL_DEADLINE_EXCEEDED")


@dataclass
class CancelToken:
    _event: threading.Event = field(default_factory=threading.Event)

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        if self._event.is_set():
            raise AccelError("ACCEL_CANCELLED")


@dataclass
class _Bucket:
    tokens: float
    stamp: float


@dataclass
class Admission:
    rate_per_s: float
    burst: int
    max_inflight: int
    clock: Callable[[], float] = time.monotonic
    max_tenants: int = 10_000
    _buckets: dict = field(default_factory=dict)
    _inflight: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    shed: int = 0

    def _take(self, tenant: str) -> bool:
        now = self.clock()
        b = self._buckets.get(tenant)
        if b is None:
            if len(self._buckets) >= self.max_tenants:
                # evict the fullest (idle) bucket; bounded memory (C067)
                idle = max(self._buckets, key=lambda k: self._buckets[k].tokens)
                del self._buckets[idle]
            b = self._buckets[tenant] = _Bucket(float(self.burst), now)
        b.tokens = min(float(self.burst), b.tokens + (now - b.stamp) * self.rate_per_s)
        b.stamp = now
        if b.tokens >= 1.0:
            b.tokens -= 1.0
            return True
        return False

    @contextmanager
    def admit(self, tenant: str):
        with self._lock:
            if self._inflight >= self.max_inflight:
                self.shed += 1
                raise AccelError("ACCEL_OVERLOADED", "in-flight cap reached", reason="inflight")
            if not self._take(tenant):
                self.shed += 1
                raise AccelError("ACCEL_OVERLOADED", "tenant rate exceeded", reason="rate")
            self._inflight += 1
        try:
            yield
        finally:
            with self._lock:
                self._inflight -= 1

    @property
    def inflight(self) -> int:
        return self._inflight


def backoff_delays(attempts: int, base: float, cap: float, rng: random.Random) -> list[float]:
    return [rng.uniform(0, min(cap, base * (2 ** i))) for i in range(attempts - 1)]


def retry(fn: Callable[[], T], *, idempotent: bool, attempts: int = 3, base: float = 0.05, cap: float = 1.0,
          deadline: Deadline | None = None, sleep: Callable[[float], None] = time.sleep,
          rng: random.Random | None = None) -> T:
    if not 1 <= attempts <= 5:
        raise ValueError("attempts must be in 1..5")
    delays = backoff_delays(attempts, base, cap, rng or random.Random())
    for i in range(attempts):
        try:
            return fn()
        except AccelError as e:
            last = i == attempts - 1
            if not (e.retryable and idempotent) or last:
                raise
            d = delays[i]
            if deadline is not None and deadline.remaining() <= d:
                raise AccelError("ACCEL_DEADLINE_EXCEEDED", "no time left to retry", cause=e.code)
            sleep(d)
    raise AssertionError("unreachable")  # pragma: no cover


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    reset_after_s: float = 30.0
    clock: Callable[[], float] = time.monotonic
    state: str = "closed"
    failures: int = 0
    opened_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_after_s:
                    self.state = "half_open"
                else:
                    raise AccelError("ACCEL_CIRCUIT_OPEN", f"{self.name} circuit open", dependency=self.name)
        try:
            out = fn()
        except Exception:
            with self._lock:
                self.failures += 1
                if self.state == "half_open" or self.failures >= self.failure_threshold:
                    self.state, self.opened_at = "open", self.clock()
            raise
        with self._lock:
            self.state, self.failures = "closed", 0
        return out
