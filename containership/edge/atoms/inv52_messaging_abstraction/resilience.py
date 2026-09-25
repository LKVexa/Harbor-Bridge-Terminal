"""Resilience primitives for INV-52 (C017, C025, C053, C054, C056, C058, C067).

Every primitive is bounded, deterministic under an injected clock/RNG, and
fails closed.  Retry is applied only to operations the caller declares
idempotent; a message publish is idempotent because the envelope ``id`` is the
de-duplication key at the receiver (PubSub ``dedup_window`` / broker).
"""
from __future__ import annotations

import random
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable

from .runtime import MessagingError, Overloaded

Clock = Callable[[], float]


class DeadlineExceeded(MessagingError, TimeoutError):
    code = "PK_MSG_DEADLINE_EXCEEDED"
    retryable = True


class Cancelled(MessagingError, RuntimeError):
    code = "PK_MSG_CANCELLED"


class CircuitOpen(MessagingError, RuntimeError):
    code = "PK_MSG_CIRCUIT_OPEN"
    retryable = True


class StaleOwner(MessagingError, PermissionError):
    code = "PK_MSG_STALE_FENCING_TOKEN"


# ---------------------------------------------------------------- deadlines
@dataclass
class CallContext:
    """Deadline + cooperative cancellation for one publish/delivery."""

    deadline: float | None = None
    clock: Clock = time.monotonic
    _cancelled: threading.Event = field(default_factory=threading.Event)

    @classmethod
    def with_timeout(cls, seconds: float, clock: Clock = time.monotonic) -> "CallContext":
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 0 < seconds <= 3600:
            raise ValueError("timeout must be in (0, 3600] seconds")
        return cls(deadline=clock() + float(seconds), clock=clock)

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def remaining(self) -> float | None:
        return None if self.deadline is None else self.deadline - self.clock()

    def check(self) -> None:
        if self.cancelled:
            raise Cancelled("operation cancelled by caller")
        rem = self.remaining()
        if rem is not None and rem <= 0:
            raise DeadlineExceeded("deadline exceeded")


# ---------------------------------------------------------------- retry
@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential backoff with full jitter (C053)."""

    max_attempts: int = 4
    base_delay: float = 0.05
    max_delay: float = 2.0
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be 1..10")
        if not 0 < self.base_delay <= self.max_delay <= 60:
            raise ValueError("delays must satisfy 0 < base <= max <= 60")
        if not 1 <= self.multiplier <= 10:
            raise ValueError("multiplier must be 1..10")

    def delay(self, attempt: int, rng: random.Random) -> float:
        cap = min(self.max_delay, self.base_delay * self.multiplier ** (attempt - 1))
        return rng.uniform(0, cap)

    def run(self, op: Callable[[], Any], *, idempotent: bool, ctx: CallContext | None = None,
            sleep: Callable[[float], None] = time.sleep, rng: random.Random | None = None,
            on_retry: Callable[[int, BaseException], None] | None = None) -> Any:
        """Run ``op``; retry only retryable failures and only if ``idempotent``."""
        rng = rng or random.Random()
        attempt = 0
        while True:
            attempt += 1
            if ctx:
                ctx.check()
            try:
                return op()
            except Exception as exc:  # noqa: BLE001
                retryable = bool(getattr(exc, "retryable", isinstance(exc, (ConnectionError, TimeoutError))))
                if not idempotent or not retryable or attempt >= self.max_attempts:
                    raise
                d = self.delay(attempt, rng)
                if ctx and ctx.remaining() is not None and ctx.remaining() <= d:
                    raise DeadlineExceeded("deadline would expire during backoff") from exc
                if on_retry:
                    on_retry(attempt, exc)
                sleep(d)


# ---------------------------------------------------------------- admission
class TokenBucket:
    """Rate limiter; ``take`` returns False instead of blocking (load shedding)."""

    def __init__(self, rate: float, burst: int, clock: Clock = time.monotonic):
        if not (rate > 0 and burst >= 1):
            raise ValueError("rate must be > 0 and burst >= 1")
        self.rate, self.burst, self.clock = float(rate), int(burst), clock
        self.tokens = float(burst)
        self.stamp = clock()
        self._lock = threading.Lock()

    def take(self, n: float = 1.0) -> bool:
        with self._lock:
            now = self.clock()
            self.tokens = min(self.burst, self.tokens + (now - self.stamp) * self.rate)
            self.stamp = now
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False


class QuotaAdmission:
    """Per-(tenant/app) and per-topic token buckets plus a global in-flight cap.

    Fairness: each key has its own bucket, so one noisy publisher exhausts only
    its own allowance (C017).  The set of tracked keys is bounded (C067).
    Usable directly as ``PubSub(admission=QuotaAdmission(...))``.
    """

    def __init__(self, *, per_app_rate: float = 1000.0, per_app_burst: int = 2000,
                 per_topic_rate: float | None = None, per_topic_burst: int = 0,
                 max_keys: int = 10_000, clock: Clock = time.monotonic):
        self.per_app = (per_app_rate, per_app_burst)
        self.per_topic = (per_topic_rate, per_topic_burst) if per_topic_rate else None
        self.max_keys = max_keys
        self.clock = clock
        self._buckets: OrderedDict[str, TokenBucket] = OrderedDict()
        self._lock = threading.Lock()
        self.shed: dict[str, int] = {}

    def _bucket(self, key: str, rate: float, burst: int) -> TokenBucket:
        with self._lock:
            b = self._buckets.get(key)
            if b is None:
                if len(self._buckets) >= self.max_keys:
                    raise Overloaded("admission key table full", details={"limit": self.max_keys})
                b = self._buckets[key] = TokenBucket(rate, burst, self.clock)
            self._buckets.move_to_end(key)
            return b

    def __call__(self, app: str, topic: str) -> None:
        if not self._bucket(f"app:{app}", *self.per_app).take():
            self.shed[app] = self.shed.get(app, 0) + 1
            raise Overloaded(f"publish rate for {app} exceeded", details={"app": app, "scope": "app"})
        if self.per_topic and not self._bucket(f"topic:{topic}", *self.per_topic).take():
            self.shed[app] = self.shed.get(app, 0) + 1
            raise Overloaded(f"publish rate for topic {topic} exceeded", details={"topic": topic, "scope": "topic"})


# ---------------------------------------------------------------- circuit
class CircuitBreaker:
    """closed -> open after N consecutive failures -> half-open after cool-down."""

    def __init__(self, failure_threshold: int = 5, reset_after: float = 30.0, clock: Clock = time.monotonic):
        if failure_threshold < 1 or reset_after <= 0:
            raise ValueError("invalid breaker settings")
        self.threshold, self.reset_after, self.clock = failure_threshold, reset_after, clock
        self.failures = 0
        self.opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self.opened_at is None:
                return "closed"
            return "half_open" if self.clock() - self.opened_at >= self.reset_after else "open"

    def call(self, op: Callable[[], Any]) -> Any:
        if self.state == "open":
            raise CircuitOpen("circuit open")
        try:
            out = op()
        except Exception:
            with self._lock:
                self.failures += 1
                if self.failures >= self.threshold or self.opened_at is not None:
                    self.opened_at = self.clock()
            raise
        with self._lock:
            self.failures, self.opened_at = 0, None
        return out


class GuardedSink:
    """Wrap a subscriber sink with a circuit breaker so a failing consumer is
    isolated quickly (its messages dead-letter with ``PK_MSG_CIRCUIT_OPEN``)
    instead of being invoked on every publish (C054, C056)."""

    def __init__(self, sink: Any, breaker: CircuitBreaker):
        if not callable(getattr(sink, "append", None)):
            raise ValueError("sink must expose append")
        self.sink, self.breaker = sink, breaker

    def append(self, message: Any) -> None:
        self.breaker.call(lambda: self.sink.append(message))


# ---------------------------------------------------------------- ownership
class FencedOwnership:
    """Monotonic fencing tokens for exclusive subscription/consumer ownership.

    A controller that lost its lease (split brain, stale controller) holds an
    old token; every mutation presents its token and stale ones are refused
    (C058).  Lease expiry uses the injected clock.
    """

    def __init__(self, lease_s: float = 15.0, clock: Clock = time.monotonic):
        self.lease_s, self.clock = lease_s, clock
        self._owner: dict[str, tuple[str, int, float]] = {}
        self._epoch: dict[str, int] = {}
        self._lock = threading.Lock()

    def acquire(self, resource: str, holder: str) -> int:
        with self._lock:
            cur = self._owner.get(resource)
            now = self.clock()
            if cur and cur[0] != holder and cur[2] > now:
                raise StaleOwner(f"{resource} is owned by another holder until lease expiry",
                                 details={"resource": resource})
            epoch = self._epoch.get(resource, 0) + (0 if cur and cur[0] == holder and cur[2] > now else 1)
            self._epoch[resource] = epoch
            self._owner[resource] = (holder, epoch, now + self.lease_s)
            return epoch

    def check(self, resource: str, token: int) -> None:
        with self._lock:
            cur = self._owner.get(resource)
            if not cur or cur[1] != token or cur[2] <= self.clock():
                raise StaleOwner("stale or expired fencing token", details={"resource": resource})
