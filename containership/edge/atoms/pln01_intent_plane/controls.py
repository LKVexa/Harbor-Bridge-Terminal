"""Flow control, overload protection, and operator safety controls.

MC-007 per-tenant quotas and fairness; MC-012 deadlines, cancellation, bounded
retries with full jitter, rate admission, bulkhead backpressure, load shedding,
and circuit breaking; MC-029 quarantine / freeze / disable controls.

All clocks are injectable so every behaviour is deterministic under test.
"""
from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from .errors import (CancelledError, CircuitOpenError, DeadlineExceededError, OverloadedError,
                     QuotaExceededError, ScopeFrozenError, code_for, ERROR_CODES)

T = TypeVar("T")
Clock = Callable[[], float]


class Deadline:
    """Absolute deadline plus cooperative cancellation token."""

    def __init__(self, seconds: float, *, clock: Clock = time.monotonic) -> None:
        if not seconds > 0:
            raise ValueError("deadline must be positive")
        self._clock = clock
        self.expires_at = clock() + seconds
        self._cancelled = threading.Event()

    def remaining(self) -> float:
        return self.expires_at - self._clock()

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def check(self) -> None:
        if self._cancelled.is_set():
            raise CancelledError("operation cancelled")
        if self.remaining() <= 0:
            raise DeadlineExceededError("deadline exceeded")


class TokenBucket:
    def __init__(self, rate: float, burst: int, *, clock: Clock = time.monotonic) -> None:
        self.rate, self.burst, self._clock = rate, burst, clock
        self.tokens = float(burst)
        self.updated = clock()

    def take(self, n: float = 1.0) -> bool:
        now = self._clock()
        self.tokens = min(self.burst, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


class TenantQuotas:
    """Per-tenant rate, node-count quota, and fair share of concurrency."""

    def __init__(self, *, rate: float, burst: int, max_nodes: int, clock: Clock = time.monotonic) -> None:
        self.rate, self.burst, self.max_nodes, self._clock = rate, burst, max_nodes, clock
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self.overrides: dict[str, dict[str, float]] = {}

    def admit(self, tenant: str, current_nodes: int, adding: int = 0) -> None:
        with self._lock:
            o = self.overrides.get(tenant, {})
            bucket = self._buckets.get(tenant)
            if bucket is None:
                bucket = self._buckets[tenant] = TokenBucket(o.get("rate", self.rate), int(o.get("burst", self.burst)),
                                                             clock=self._clock)
            if not bucket.take():
                raise QuotaExceededError(f"tenant {tenant} exceeded request rate", tenant=tenant)
        limit = int(o.get("max_nodes", self.max_nodes))
        if current_nodes + adding > limit:
            raise QuotaExceededError(f"tenant {tenant} node quota {limit} reached", tenant=tenant)


class Bulkhead:
    """Bounded concurrency with a bounded wait queue; excess load is shed."""

    def __init__(self, max_concurrent: int, max_queue: int) -> None:
        self.max_concurrent, self.max_queue = max_concurrent, max_queue
        self._sem = threading.BoundedSemaphore(max_concurrent)
        self._lock = threading.Lock()
        self.waiting = 0
        self.in_flight = 0
        self.shed = 0

    def run(self, fn: Callable[[], T], deadline: Deadline | None = None) -> T:
        with self._lock:
            if self.in_flight >= self.max_concurrent and self.waiting >= self.max_queue:
                self.shed += 1
                raise OverloadedError("request shed: bulkhead and queue full")
            self.waiting += 1
        timeout = None if deadline is None else max(0.0, deadline.remaining())
        acquired = self._sem.acquire(timeout=timeout)
        with self._lock:
            self.waiting -= 1
            if acquired:
                self.in_flight += 1
        if not acquired:
            raise DeadlineExceededError("deadline exceeded waiting for capacity")
        try:
            if deadline is not None:
                deadline.check()
            return fn()
        finally:
            with self._lock:
                self.in_flight -= 1
            self._sem.release()

    @property
    def saturation(self) -> float:
        return (self.in_flight + self.waiting) / float(self.max_concurrent + self.max_queue or 1)


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_seconds: float = 30.0
    clock: Clock = time.monotonic
    state: str = "closed"
    failures: int = 0
    opened_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_seconds:
                    self.state = "half_open"
                else:
                    raise CircuitOpenError("circuit open")
        try:
            result = fn()
        except Exception:
            with self._lock:
                self.failures += 1
                if self.state == "half_open" or self.failures >= self.failure_threshold:
                    self.state, self.opened_at = "open", self.clock()
            raise
        with self._lock:
            self.state, self.failures = "closed", 0
        return result


def retry(fn: Callable[[], T], *, attempts: int, base: float, cap: float,
          deadline: Deadline | None = None, sleep: Callable[[float], None] = time.sleep,
          rng: random.Random | None = None) -> T:
    """Retry only errors whose code is marked retryable, with full-jitter backoff."""
    rng = rng or random.Random()
    last: BaseException | None = None
    for attempt in range(attempts):
        if deadline is not None:
            deadline.check()
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - classified below
            last = exc
            if not ERROR_CODES[code_for(exc)].retryable or attempt == attempts - 1:
                raise
            delay = rng.uniform(0, min(cap, base * (2 ** attempt)))
            if deadline is not None and delay >= deadline.remaining():
                raise DeadlineExceededError("retry budget exceeds deadline") from exc
            sleep(delay)
    raise last  # pragma: no cover


class SafetyControls:
    """Quarantine / freeze / disable switches (MC-029).

    * ``freeze(scope)``  - refuse mutations for the scope; reads and plans continue.
    * ``quarantine(scope)`` - refuse mutations *and* exclude the scope from released plans.
    * ``disable()`` - global emergency stop for all mutations and plan release.
    Scopes are ``"*"``, ``"tenant"``, or ``"tenant/environment"``.  Every change
    records actor, reason, and time.
    """

    def __init__(self, clock: Clock = time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self.frozen: dict[str, dict[str, Any]] = {}
        self.quarantined: dict[str, dict[str, Any]] = {}
        self.disabled: dict[str, Any] | None = None
        self.log: list[dict[str, Any]] = []

    def _rec(self, action: str, scope: str, actor: str, reason: str) -> dict[str, Any]:
        if not actor or not reason:
            raise ValueError("safety control changes require actor and reason")
        entry = {"action": action, "scope": scope, "actor": actor, "reason": reason, "at": self._clock()}
        self.log.append(entry)
        return entry

    def freeze(self, scope: str, *, actor: str, reason: str) -> None:
        with self._lock:
            self.frozen[scope] = self._rec("freeze", scope, actor, reason)

    def unfreeze(self, scope: str, *, actor: str, reason: str) -> None:
        with self._lock:
            self._rec("unfreeze", scope, actor, reason)
            self.frozen.pop(scope, None)

    def quarantine(self, scope: str, *, actor: str, reason: str) -> None:
        with self._lock:
            self.quarantined[scope] = self._rec("quarantine", scope, actor, reason)

    def release(self, scope: str, *, actor: str, reason: str) -> None:
        with self._lock:
            self._rec("release", scope, actor, reason)
            self.quarantined.pop(scope, None)

    def disable(self, *, actor: str, reason: str) -> None:
        with self._lock:
            self.disabled = self._rec("disable", "*", actor, reason)

    def enable(self, *, actor: str, reason: str) -> None:
        with self._lock:
            self._rec("enable", "*", actor, reason)
            self.disabled = None

    @staticmethod
    def _scopes(tenant: str, environment: str) -> tuple[str, ...]:
        return ("*", tenant, f"{tenant}/{environment}")

    def is_quarantined(self, tenant: str, environment: str) -> bool:
        return any(s in self.quarantined for s in self._scopes(tenant, environment))

    def check_mutation(self, tenant: str, environment: str) -> None:
        if self.disabled is not None:
            raise ScopeFrozenError("intent plane mutations are disabled", scope="*")
        for s in self._scopes(tenant, environment):
            if s in self.frozen or s in self.quarantined:
                raise ScopeFrozenError(f"scope {s} is frozen or quarantined", scope=s)
