"""Bounded retry/backoff/jitter, deadlines/cancellation, admission control,
load shedding, circuit breaking and idempotency (MC-015, MC-043, MC-044).
"""
from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, TypeVar
from collections.abc import Callable

from . import errors

T = TypeVar("T")


# --------------------------------------------------------------- deadlines
class Deadline:
    """Absolute monotonic deadline with cooperative cancellation."""

    def __init__(self, budget_ms: int, clock: Callable[[], float] = time.monotonic):
        if budget_ms <= 0:
            raise ValueError("deadline budget must be positive")
        self._clock = clock
        self.expires = clock() + budget_ms / 1000.0
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def remaining_ms(self) -> float:
        return max(0.0, (self.expires - self._clock()) * 1000.0)

    def check(self) -> None:
        if self._cancelled.is_set():
            raise errors.TopoError(errors.CANCELLED, "request cancelled")
        if self._clock() >= self.expires:
            raise errors.TopoError(errors.DEADLINE_EXCEEDED, "deadline exceeded")


# ------------------------------------------------------------------- retry
@dataclass(frozen=True)
class RetryPolicy:
    """Capped exponential backoff with full jitter and a total time budget."""

    max_attempts: int = 4
    base_ms: float = 25.0
    cap_ms: float = 1_000.0
    budget_ms: float = 3_000.0

    def __post_init__(self) -> None:
        if not (1 <= self.max_attempts <= 10):
            raise ValueError("max_attempts must be 1..10")
        if not (0 < self.base_ms <= self.cap_ms <= self.budget_ms):
            raise ValueError("require 0 < base_ms <= cap_ms <= budget_ms")

    def delays(self, rng: random.Random) -> list[float]:
        out, spent = [], 0.0
        for attempt in range(1, self.max_attempts):
            d = rng.uniform(0, min(self.cap_ms, self.base_ms * (2 ** (attempt - 1))))
            if spent + d > self.budget_ms:
                break
            spent += d
            out.append(d)
        return out


def retry_call(fn: Callable[[], T], policy: RetryPolicy, *, rng: random.Random | None = None,
               sleep: Callable[[float], None] = time.sleep, deadline: Deadline | None = None) -> T:
    """Retry only RETRYABLE outcomes; terminal errors propagate immediately."""
    rng = rng or random.Random()  # noqa: S311 - jitter, not cryptography
    delays = policy.delays(rng)
    attempt = 0
    while True:
        if deadline:
            deadline.check()
        try:
            return fn()
        except errors.TopoError as exc:
            if exc.outcome is not errors.Outcome.RETRYABLE or attempt >= len(delays):
                raise
            wait = delays[attempt]
            if exc.retry_after_ms:
                wait = max(wait, float(exc.retry_after_ms))
            if deadline and wait >= deadline.remaining_ms():
                raise
            attempt += 1
            sleep(wait / 1000.0)


# --------------------------------------------------------------- admission
class TokenBucket:
    def __init__(self, rate_per_s: float, burst: int, clock: Callable[[], float] = time.monotonic):
        if rate_per_s <= 0 or burst < 1:
            raise ValueError("rate must be > 0 and burst >= 1")
        self.rate, self.burst, self._clock = rate_per_s, burst, clock
        self._tokens = float(burst)
        self._t = clock()
        self._lock = threading.Lock()

    def try_take(self, n: float = 1.0) -> bool:
        with self._lock:
            now = self._clock()
            # max(0, ...): a clock step backwards must never drain the bucket
            self._tokens = min(self.burst, self._tokens + max(0.0, now - self._t) * self.rate)
            self._t = now
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False


class Admission:
    """Per-tenant token buckets plus a global bounded in-flight limit."""

    def __init__(self, *, rate_per_s: float, burst: int, max_in_flight: int, max_tenants: int = 4096,
                 clock: Callable[[], float] = time.monotonic):
        self.rate, self.burst, self.clock = rate_per_s, burst, clock
        self.max_in_flight, self.max_tenants = max_in_flight, max_tenants
        self._buckets: dict[str, TokenBucket] = {}
        self._in_flight = 0
        self._lock = threading.Lock()
        self.shed = 0

    def enter(self, tenant: str, cost: float = 1.0) -> None:
        with self._lock:
            bucket = self._buckets.get(tenant)
            if bucket is None:
                if len(self._buckets) >= self.max_tenants:
                    self.shed += 1
                    raise errors.TopoError(errors.OVERLOADED, "tenant table full", retry_after_ms=1000)
                bucket = self._buckets[tenant] = TokenBucket(self.rate, self.burst, self.clock)
            if self._in_flight >= self.max_in_flight:
                self.shed += 1
                raise errors.TopoError(errors.OVERLOADED, "in-flight limit reached", retry_after_ms=50)
        if not bucket.try_take(cost):
            with self._lock:
                self.shed += 1
            raise errors.TopoError(errors.RATE_LIMITED, "tenant rate limit exceeded",
                                   retry_after_ms=int(1000 * cost / self.rate) + 1)
        with self._lock:
            self._in_flight += 1

    def leave(self) -> None:
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)

    @property
    def in_flight(self) -> int:
        return self._in_flight


class CircuitBreaker:
    """closed -> open after N consecutive failures; half-open after cool-down
    admits one probe; success closes, failure re-opens."""

    def __init__(self, threshold: int = 5, cooldown_s: float = 5.0, clock: Callable[[], float] = time.monotonic):
        self.threshold, self.cooldown, self.clock = threshold, cooldown_s, clock
        self.state = "closed"
        self._failures = 0
        self._opened = 0.0
        self._probe = False
        self._lock = threading.Lock()

    def before(self) -> None:
        with self._lock:
            if self.state == "open":
                if self.clock() - self._opened >= self.cooldown:
                    self.state, self._probe = "half_open", False
                else:
                    raise errors.TopoError(errors.OVERLOADED, "circuit open",
                                           retry_after_ms=int(1000 * self.cooldown))
            if self.state == "half_open":
                if self._probe:
                    raise errors.TopoError(errors.OVERLOADED, "circuit half-open; probe in flight", retry_after_ms=100)
                self._probe = True

    def success(self) -> None:
        with self._lock:
            self.state, self._failures, self._probe = "closed", 0, False

    def failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self.state == "half_open" or self._failures >= self.threshold:
                self.state, self._opened, self._probe = "open", self.clock(), False


# ------------------------------------------------------------- idempotency
@dataclass
class _Entry:
    fingerprint: str
    response: dict[str, Any]
    expires: float


@dataclass
class IdempotencyStore:
    """Bounded store keyed by (tenant, key).  Same key + same payload returns
    the stored response; same key + different payload is refused."""

    ttl_s: float = 600.0
    capacity: int = 50_000
    clock: Callable[[], float] = time.monotonic
    _entries: OrderedDict[tuple[str, str], _Entry] = field(default_factory=OrderedDict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @staticmethod
    def fingerprint(body: Any) -> str:
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def lookup(self, tenant: str, key: str, fingerprint: str) -> dict[str, Any] | None:
        with self._lock:
            self._expire()
            entry = self._entries.get((tenant, key))
            if entry is None:
                return None
            if entry.fingerprint != fingerprint:
                raise errors.TopoError(errors.IDEMPOTENCY_MISMATCH, "idempotency key reused with a different payload")
            return entry.response

    def store(self, tenant: str, key: str, fingerprint: str, response: dict[str, Any]) -> None:
        with self._lock:
            self._expire()
            while len(self._entries) >= self.capacity:
                self._entries.popitem(last=False)
            self._entries[(tenant, key)] = _Entry(fingerprint, response, self.clock() + self.ttl_s)

    def _expire(self) -> None:
        now = self.clock()
        for k in [k for k, e in self._entries.items() if e.expires <= now]:
            del self._entries[k]
