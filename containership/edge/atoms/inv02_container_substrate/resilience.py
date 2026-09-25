"""MC41 / MC42 / MC43 — quotas, admission/backpressure, retry and circuit breaking."""
from __future__ import annotations

import random
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Iterator, TypeVar

from .timeutil import Clock, Deadline, DeadlineExceeded, SystemClock

T = TypeVar("T")


class RateLimited(RuntimeError):
    code = "RATE_LIMITED"

    def __init__(self, msg: str, retry_after: float) -> None:
        super().__init__(msg)
        self.retry_after = retry_after


class Overloaded(RuntimeError):
    code = "OVERLOADED"


class CircuitOpen(RuntimeError):
    code = "CIRCUIT_OPEN"


# --- MC41: token-bucket rate limits and per-tenant quotas ---------------------------
class TokenBucket:
    def __init__(self, rate_per_s: float, burst: float, clock: Clock | None = None) -> None:
        if rate_per_s <= 0 or burst <= 0:
            raise ValueError("rate and burst must be positive")
        self.rate, self.burst = rate_per_s, burst
        self.clock = clock or SystemClock()
        self._tokens, self._last = burst, self.clock.monotonic()
        self._lock = threading.Lock()

    def try_take(self, n: float = 1.0) -> float:
        """Take ``n`` tokens; return 0 on success or the seconds until they'd be available."""
        with self._lock:
            now = self.clock.monotonic()
            self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
            self._last = now
            if n > self.burst:
                return float("inf")
            if self._tokens >= n:
                self._tokens -= n
                return 0.0
            return (n - self._tokens) / self.rate


class QuotaManager:
    """Per-tenant rate limit + byte quota.  Unknown tenants get the default policy."""

    def __init__(self, rate_per_s: float, burst: float, byte_quota: int, clock: Clock | None = None) -> None:
        self._cfg = (rate_per_s, burst, byte_quota)
        self._clock = clock or SystemClock()
        self._buckets: dict[str, TokenBucket] = {}
        self._usage: dict[str, int] = {}
        self._lock = threading.Lock()

    def admit(self, tenant: str, nbytes: int = 0) -> None:
        with self._lock:
            b = self._buckets.setdefault(tenant, TokenBucket(self._cfg[0], self._cfg[1], self._clock))
            used = self._usage.get(tenant, 0)
            if used + nbytes > self._cfg[2]:
                raise RateLimited(f"tenant {tenant!r} byte quota exhausted", float("inf"))
        wait = b.try_take()
        if wait:
            raise RateLimited(f"tenant {tenant!r} rate limited", wait)
        with self._lock:
            self._usage[tenant] = used + nbytes

    def release_bytes(self, tenant: str, nbytes: int) -> None:
        with self._lock:
            self._usage[tenant] = max(0, self._usage.get(tenant, 0) - nbytes)

    def usage(self) -> dict[str, int]:
        with self._lock:
            return dict(self._usage)


# --- MC42: bounded admission control ---------------------------------------------
class AdmissionController:
    """Bounded concurrency + bounded queue.  Beyond both, requests are shed immediately
    (fail fast) instead of piling up until the host is exhausted."""

    def __init__(self, max_inflight: int, max_queue: int) -> None:
        if max_inflight <= 0 or max_queue < 0:
            raise ValueError("invalid admission limits")
        self.max_inflight, self.max_queue = max_inflight, max_queue
        self._cv = threading.Condition()
        self.inflight = 0
        self.waiting = 0
        self.shed = 0

    @contextmanager
    def slot(self, deadline: Deadline | None = None) -> Iterator[None]:
        with self._cv:
            if self.inflight >= self.max_inflight:
                if self.waiting >= self.max_queue:
                    self.shed += 1
                    raise Overloaded("admission queue full")
                self.waiting += 1
                try:
                    while self.inflight >= self.max_inflight:
                        timeout = deadline.remaining() if deadline else None
                        if timeout == 0.0:
                            self.shed += 1
                            raise DeadlineExceeded("admission wait exceeded deadline")
                        self._cv.wait(timeout)
                finally:
                    self.waiting -= 1
            self.inflight += 1
        try:
            yield
        finally:
            with self._cv:
                self.inflight -= 1
                self._cv.notify()


# --- MC43: retry with jittered backoff and circuit breaker ------------------------
@dataclass
class RetryPolicy:
    max_attempts: int = 5
    base_delay_s: float = 0.1
    max_delay_s: float = 10.0
    retry_on: tuple[type[BaseException], ...] = (ConnectionError, TimeoutError, OSError)
    give_up_on: tuple[type[BaseException], ...] = ()
    rng: random.Random = field(default_factory=random.Random)

    def delay(self, attempt: int) -> float:
        """Full-jitter exponential backoff (attempt is 1-based)."""
        cap = min(self.max_delay_s, self.base_delay_s * (2 ** (attempt - 1)))
        return self.rng.uniform(0, cap)


def retry(fn: Callable[[], T], policy: RetryPolicy, *, clock: Clock | None = None,
          deadline: Deadline | None = None, on_retry: Callable[[int, BaseException], None] | None = None) -> T:
    clock = clock or SystemClock()
    last: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        if deadline:
            deadline.check("retry")
        try:
            return fn()
        except policy.give_up_on:
            raise
        except policy.retry_on as exc:
            if isinstance(exc, RateLimited) and exc.retry_after == float("inf"):
                raise
            last = exc
            if attempt == policy.max_attempts:
                break
            wait = policy.delay(attempt)
            if isinstance(exc, RateLimited):
                wait = max(wait, exc.retry_after)
            if deadline and wait >= deadline.remaining():
                raise DeadlineExceeded("retry budget exceeds deadline") from exc
            if on_retry:
                on_retry(attempt, exc)
            clock.sleep(wait)
    assert last is not None
    raise last


class CircuitBreaker:
    """closed -> open after ``failure_threshold`` consecutive failures; open -> half_open
    after ``reset_after_s``; a half-open probe success closes it, failure re-opens it."""

    def __init__(self, failure_threshold: int = 5, reset_after_s: float = 30.0, clock: Clock | None = None) -> None:
        self.threshold, self.reset_after = failure_threshold, reset_after_s
        self.clock = clock or SystemClock()
        self.state = "closed"
        self.failures = 0
        self._opened_at = 0.0
        self._probe = False
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                if self.clock.monotonic() - self._opened_at >= self.reset_after:
                    self.state = "half_open"
                else:
                    raise CircuitOpen("circuit open")
            if self.state == "half_open":
                if self._probe:
                    raise CircuitOpen("half-open probe in flight")
                self._probe = True
        try:
            result = fn()
        except Exception:
            with self._lock:
                self._probe = False
                self.failures += 1
                if self.state == "half_open" or self.failures >= self.threshold:
                    self.state, self._opened_at = "open", self.clock.monotonic()
            raise
        with self._lock:
            self._probe = False
            self.failures = 0
            self.state = "closed"
        return result
