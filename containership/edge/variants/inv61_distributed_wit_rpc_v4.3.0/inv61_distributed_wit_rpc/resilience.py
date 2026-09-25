"""M10/M11 - cancellation, idempotency, retry/backoff, admission control,
token-bucket rate limiting and circuit breaking.

Everything here is clock-injectable so behaviour is deterministic under test.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import random
import threading
import time
from typing import Any, Callable

# Status codes shared with server.py; the retryable set is the single source
# of truth for client retry classification (M10).
RETRYABLE = frozenset({"overloaded", "circuit-open", "unavailable", "draining", "rate-limited"})
NON_RETRYABLE = frozenset({
    "malformed-frame", "unauthenticated", "permission-denied", "replay", "version-mismatch",
    "signature-mismatch", "unknown-interface", "unknown-function", "invalid-args",
    "deadline-exceeded", "callee-trap", "cancelled", "disabled", "fenced", "idempotency-conflict",
    "internal",
})


class CancellationToken:
    def __init__(self) -> None:
        self._ev = threading.Event()
        self.reason: str | None = None

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def wait(self, timeout: float) -> bool:
        return self._ev.wait(timeout)


# --------------------------------------------------------------- retry (M10)
@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_s: float = 0.05
    cap_s: float = 2.0
    rng: random.Random = field(default_factory=random.Random)

    def backoff(self, attempt: int) -> float:
        """Full-jitter exponential backoff (attempt starts at 1)."""
        return self.rng.uniform(0, min(self.cap_s, self.base_s * (2 ** (attempt - 1))))

    def should_retry(self, status: str, attempt: int, idempotent: bool, remaining_s: float) -> bool:
        if attempt >= self.max_attempts or remaining_s <= 0:
            return False
        if status not in RETRYABLE:
            return False
        # Only idempotent (or idempotency-keyed) calls may be retried; an
        # ambiguous failure of a non-idempotent call is surfaced, never replayed.
        return idempotent


# --------------------------------------------------------- idempotency (M10/M19)
class IdempotencyCache:
    """Bounded TTL cache of completed results keyed by (tenant, sender, key).

    A duplicate that arrives while the original is in flight gets
    ``in-progress`` (caller retries later) rather than a second execution.
    A reused key with a different request digest is ``idempotency-conflict``.
    """

    def __init__(self, ttl_s: float = 600.0, capacity: int = 50_000, clock: Callable[[], float] = time.monotonic):
        self.ttl_s, self.capacity, self.clock = ttl_s, capacity, clock
        self._d: "OrderedDict[tuple, tuple[str, str, Any, float]]" = OrderedDict()
        self._lock = threading.Lock()

    def begin(self, key: tuple, digest: str) -> tuple[str, Any]:
        now = self.clock()
        with self._lock:
            self._evict(now)
            hit = self._d.get(key)
            if hit is not None:
                state, dg, value, _ = hit
                if dg != digest:
                    return "conflict", None
                return state, value  # "done" -> cached value, "running" -> in progress
            if len(self._d) >= self.capacity:
                return "full", None
            self._d[key] = ("running", digest, None, now)
            return "new", None

    def complete(self, key: tuple, value: Any) -> None:
        with self._lock:
            if key in self._d:
                _, dg, _, _ = self._d[key]
                self._d[key] = ("done", dg, value, self.clock())
                self._d.move_to_end(key)

    def abort(self, key: tuple) -> None:
        with self._lock:
            self._d.pop(key, None)

    def _evict(self, now: float) -> None:
        while self._d:
            k, (state, _, _, ts) = next(iter(self._d.items()))
            if now - ts > self.ttl_s and state == "done":
                self._d.popitem(last=False)
            else:
                break

    def snapshot(self) -> list[list[Any]]:
        with self._lock:
            return [[list(k), s, d, v.hex() if isinstance(v, (bytes, bytearray)) else v, t]
                    for k, (s, d, v, t) in self._d.items() if s == "done"]

    def restore(self, rows: list[list[Any]]) -> None:
        with self._lock:
            for k, s, d, v, t in rows:
                self._d[tuple(k)] = (s, d, bytes.fromhex(v) if isinstance(v, str) else v, self.clock())

    def __len__(self) -> int:
        return len(self._d)


# ----------------------------------------------------------- rate limit (M11)
class TokenBucket:
    def __init__(self, rate_per_s: float, burst: float, clock: Callable[[], float] = time.monotonic):
        if rate_per_s <= 0 or burst <= 0:
            raise ValueError("rate and burst must be positive")
        self.rate, self.burst, self.clock = rate_per_s, burst, clock
        self.tokens, self.t = burst, clock()
        self._lock = threading.Lock()

    def take(self, n: float = 1.0) -> bool:
        with self._lock:
            now = self.clock()
            self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
            self.t = now
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False


# -------------------------------------------------------- admission (M11)
class AdmissionController:
    """Global and per-tenant in-flight ceilings plus per-tenant token buckets.

    ``admit`` returns a status string; callers MUST call ``release`` exactly
    once for every admitted call (use as a context manager via ``slot``).
    """

    def __init__(self, max_inflight: int = 256, per_tenant_inflight: int = 64,
                 tenant_rate: float = 500.0, tenant_burst: float = 1000.0,
                 clock: Callable[[], float] = time.monotonic):
        self.max_inflight, self.per_tenant = max_inflight, per_tenant_inflight
        self.tenant_rate, self.tenant_burst, self.clock = tenant_rate, tenant_burst, clock
        self.inflight = 0
        self._tenant: dict[str, int] = {}
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self.shed = 0

    def admit(self, tenant: str) -> str:
        with self._lock:
            bucket = self._buckets.get(tenant)
            if bucket is None:
                if len(self._buckets) >= 10_000:
                    self.shed += 1
                    return "overloaded"  # tenant-table exhaustion is itself shed
                bucket = self._buckets[tenant] = TokenBucket(self.tenant_rate, self.tenant_burst, self.clock)
            if self.inflight >= self.max_inflight:
                self.shed += 1
                return "overloaded"
            if self._tenant.get(tenant, 0) >= self.per_tenant:
                self.shed += 1
                return "overloaded"
            if not bucket.take():
                self.shed += 1
                return "rate-limited"
            self.inflight += 1
            self._tenant[tenant] = self._tenant.get(tenant, 0) + 1
            return "ok"

    def release(self, tenant: str) -> None:
        with self._lock:
            if self._tenant.get(tenant, 0) <= 0:
                raise RuntimeError("release without admit")
            self.inflight -= 1
            self._tenant[tenant] -= 1
            if self._tenant[tenant] == 0:
                del self._tenant[tenant]


# ------------------------------------------------------- circuit breaker (M11)
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half-open"

    def __init__(self, failure_threshold: int = 5, reset_after_s: float = 5.0,
                 clock: Callable[[], float] = time.monotonic):
        self.threshold, self.reset_after, self.clock = failure_threshold, reset_after_s, clock
        self.state, self.failures, self.opened_at = self.CLOSED, 0, 0.0
        self._probe = False
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self.state == self.OPEN and self.clock() - self.opened_at >= self.reset_after:
                self.state, self._probe = self.HALF_OPEN, False
            if self.state == self.CLOSED:
                return True
            if self.state == self.HALF_OPEN and not self._probe:
                self._probe = True  # exactly one probe in half-open
                return True
            return False

    def record(self, success: bool) -> None:
        with self._lock:
            if success:
                self.state, self.failures, self._probe = self.CLOSED, 0, False
                return
            self.failures += 1
            if self.state == self.HALF_OPEN or self.failures >= self.threshold:
                self.state, self.opened_at, self._probe = self.OPEN, self.clock(), False
