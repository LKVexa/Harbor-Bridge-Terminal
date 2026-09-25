"""Bounded retry, circuit breaking, admission control, deadlines, stall
detection and quarantine (INV-63-C025, C052, C053, C054, C059, C067)."""
from __future__ import annotations

import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from .errors import DeploymentError, ErrorCode

T = TypeVar("T")


# ---------------------------------------------------------------- deadlines / cancellation
class Deadline:
    def __init__(self, timeout_s: float, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.expires = clock() + timeout_s
        self.cancelled = False

    def remaining(self) -> float:
        return self.expires - self.clock()

    def cancel(self) -> None:
        self.cancelled = True

    def check(self) -> None:
        if self.cancelled:
            raise DeploymentError(ErrorCode.CANCELLED, "operation cancelled")
        if self.remaining() <= 0:
            raise DeploymentError(ErrorCode.DEADLINE_EXCEEDED, "deadline exceeded")


# ---------------------------------------------------------------- retry
@dataclass
class RetryPolicy:
    """Exponential backoff with full jitter; only for idempotent ops and retryable errors."""

    max_attempts: int = 4
    base_s: float = 0.05
    cap_s: float = 2.0
    rng: random.Random = field(default_factory=lambda: random.Random(0x1263))
    sleep: Callable[[float], None] = time.sleep

    def delays(self) -> list[float]:
        return [self.rng.uniform(0, min(self.cap_s, self.base_s * (2 ** i))) for i in range(self.max_attempts - 1)]

    def run(self, fn: Callable[[], T], *, idempotent: bool, deadline: Deadline | None = None,
            on_retry: Callable[[int, DeploymentError], None] | None = None) -> T:
        if not idempotent:
            return fn()   # never retry non-idempotent operations
        attempt = 0
        while True:
            attempt += 1
            if deadline:
                deadline.check()
            try:
                return fn()
            except DeploymentError as exc:
                if not exc.retryable or attempt >= self.max_attempts:
                    raise
                delay = self.rng.uniform(0, min(self.cap_s, self.base_s * (2 ** (attempt - 1))))
                if deadline and delay >= deadline.remaining():
                    raise DeploymentError(ErrorCode.DEADLINE_EXCEEDED, "retry budget exceeds deadline",
                                          {"attempts": attempt}) from exc
                if on_retry:
                    on_retry(attempt, exc)
                self.sleep(delay)


# ---------------------------------------------------------------- circuit breaker
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold: int = 5, reset_after_s: float = 10.0,
                 clock: Callable[[], float] = time.monotonic):
        self.failure_threshold, self.reset_after_s, self.clock = failure_threshold, reset_after_s, clock
        self.state = self.CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == self.OPEN:
                if self.clock() - self.opened_at >= self.reset_after_s:
                    self.state = self.HALF_OPEN
                else:
                    raise DeploymentError(ErrorCode.CIRCUIT_OPEN, "dependency circuit open",
                                          retry_after_s=max(0.0, self.reset_after_s - (self.clock() - self.opened_at)))
        try:
            result = fn()
        except DeploymentError as exc:
            if exc.retryable:
                self._failure()
            raise
        except Exception:
            self._failure()
            raise
        with self._lock:
            self.state, self.failures = self.CLOSED, 0
        return result

    def _failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == self.HALF_OPEN or self.failures >= self.failure_threshold:
                self.state = self.OPEN
                self.opened_at = self.clock()


# ---------------------------------------------------------------- admission / backpressure
class Admission:
    """Global in-flight cap + per-tenant token buckets + bounded queue with priority shedding."""

    PRIORITY = {"critical": 0, "standard": 1, "batch": 2}

    def __init__(self, max_inflight: int = 64, tenant_rate: float = 50.0, tenant_burst: int = 100,
                 queue_depth: int = 1024, clock: Callable[[], float] = time.monotonic):
        self.max_inflight, self.rate, self.burst, self.clock = max_inflight, tenant_rate, tenant_burst, clock
        self.inflight = 0
        self.queue: deque[tuple[str, Any]] = deque()
        self.queue_depth = queue_depth
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()
        self.shed = 0

    def _take(self, tenant: str) -> bool:
        now = self.clock()
        tokens, last = self._buckets.get(tenant, (float(self.burst), now))
        tokens = min(float(self.burst), tokens + (now - last) * self.rate)
        if tokens < 1:
            self._buckets[tenant] = (tokens, now)
            return False
        self._buckets[tenant] = (tokens - 1, now)
        return True

    def enter(self, tenant: str, priority: str = "standard") -> None:
        with self._lock:
            # shed batch work first when above 80% utilisation
            hot = self.inflight >= int(self.max_inflight * 0.8)
            if hot and self.PRIORITY.get(priority, 1) >= 2:
                self.shed += 1
                raise DeploymentError(ErrorCode.OVERLOADED, "shedding batch-priority work", retry_after_s=1.0)
            if self.inflight >= self.max_inflight and priority != "critical":
                self.shed += 1
                raise DeploymentError(ErrorCode.OVERLOADED, "in-flight limit reached", {"limit": self.max_inflight},
                                      retry_after_s=0.5)
            if not self._take(tenant):
                self.shed += 1
                raise DeploymentError(ErrorCode.QUOTA_EXCEEDED, "tenant request rate exceeded",
                                      {"tenant": tenant}, retry_after_s=1.0 / max(self.rate, 1e-9))
            self.inflight += 1

    def leave(self) -> None:
        with self._lock:
            self.inflight = max(0, self.inflight - 1)

    def enqueue(self, item: tuple[str, Any]) -> None:
        with self._lock:
            if len(self.queue) >= self.queue_depth:
                raise DeploymentError(ErrorCode.OVERLOADED, "queue full", {"depth": self.queue_depth})
            self.queue.append(item)


# ---------------------------------------------------------------- health / stall
class HealthMonitor:
    def __init__(self, stall_threshold_s: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.stall_threshold_s, self.clock = stall_threshold_s, clock
        self.last_progress: dict[str, float] = {}
        self.pending: dict[str, float] = {}

    def begin(self, key: str) -> None:
        self.pending.setdefault(key, self.clock())

    def progress(self, key: str) -> None:
        self.last_progress[key] = self.clock()
        self.pending.pop(key, None)

    def stalled(self) -> list[str]:
        now = self.clock()
        return sorted(k for k, since in self.pending.items() if now - since > self.stall_threshold_s)


# ---------------------------------------------------------------- quarantine / freeze
class Controls:
    """Operator safety switches (INV-63-C059).  Checked before every automated action."""

    def __init__(self) -> None:
        self.global_disabled = False
        self.frozen: set[str] = set()        # namespaced component or tenant ("tenant/*")
        self.quarantined: set[str] = set()
        self.quarantined_hosts: set[str] = set()   # node-level isolation

    def check(self, ns_component: str) -> None:
        tenant = ns_component.split("/", 1)[0]
        if self.global_disabled:
            raise DeploymentError(ErrorCode.FROZEN, "emergency disable is active")
        if ns_component in self.quarantined or f"{tenant}/*" in self.quarantined:
            raise DeploymentError(ErrorCode.QUARANTINED, f"{ns_component} is quarantined")
        if ns_component in self.frozen or f"{tenant}/*" in self.frozen:
            raise DeploymentError(ErrorCode.FROZEN, f"{ns_component} is frozen")
