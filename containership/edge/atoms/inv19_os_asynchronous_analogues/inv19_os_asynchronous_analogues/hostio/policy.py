"""MC-13 - Deadlines, bounded retry with jitter, admission control, circuit breaker."""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypeVar

from .errors import CanonicalError, Code, canonical

T = TypeVar("T")
MAX_DEADLINE_S = 7 * 86400.0


class InvalidDeadline(ValueError):
    pass


class Overloaded(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.error = canonical(Code.OVERLOADED)


class NotIdempotent(RuntimeError):
    pass


def deadline_after(seconds: float | None, clock=time.monotonic) -> float | None:
    """Monotonic deadline. ``None`` = no deadline (explicit)."""
    if seconds is None:
        return None
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds != seconds:
        raise InvalidDeadline("deadline must be a real number of seconds")
    if seconds <= 0 or seconds > MAX_DEADLINE_S:
        raise InvalidDeadline(f"deadline {seconds}s outside (0, {MAX_DEADLINE_S}]")
    return clock() + float(seconds)


def expired(deadline: float | None, clock=time.monotonic) -> bool:
    return deadline is not None and clock() >= deadline


IDEMPOTENT_OPS = frozenset({"nop", "poll", "read_at", "stat", "arm", "reap"})


@dataclass
class RetryPolicy:
    max_attempts: int = 5
    budget_s: float = 10.0
    base_s: float = 0.005
    cap_s: float = 1.0
    jitter: float = 0.5
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        if not (0 <= self.max_attempts <= 32):
            raise ValueError("max_attempts must be in [0, 32]")
        if self.base_s <= 0 or self.cap_s < self.base_s or self.budget_s < 0:
            raise ValueError("invalid backoff parameters")
        if not (0 <= self.jitter <= 1):
            raise ValueError("jitter in [0,1]")

    def backoff(self, attempt: int) -> float:
        exp = min(attempt, 30)  # no overflow
        d = min(self.cap_s, self.base_s * (2 ** exp))
        return d * (1 - self.jitter * self.rng.random())

    def run(self, op: str, fn: Callable[[], T], *, sleep=time.sleep, clock=time.monotonic,
            on_retry: Callable[[CanonicalError], None] | None = None) -> T:
        """Retry ``fn`` only for retryable CanonicalErrors on idempotent ops."""
        start = clock()
        attempt = 0
        while True:
            try:
                return fn()
            except RetryableFailure as f:
                err = f.error
                if not err.retryable:
                    raise
                if op not in IDEMPOTENT_OPS:
                    raise NotIdempotent(f"{op} is not classified idempotent; refusing retry") from f
                if attempt >= self.max_attempts:
                    raise
                d = self.backoff(attempt)
                if clock() - start + d > self.budget_s:
                    raise
                attempt += 1
                if on_retry:
                    on_retry(err)
                sleep(d)


class RetryableFailure(Exception):
    def __init__(self, error: CanonicalError) -> None:
        super().__init__(error.code)
        self.error = error


@dataclass
class Admission:
    """Bounds in-flight, pending-submission and completion-backlog counts."""
    max_inflight: int
    max_pending: int
    max_backlog: int
    per_tenant_inflight: int
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    inflight: int = 0
    pending: int = 0
    backlog: int = 0
    tenant_inflight: dict[str, int] = field(default_factory=dict)
    shed: dict[str, int] = field(default_factory=dict)

    def admit(self, tenant: str) -> None:
        with self._lock:
            reason = None
            if self.inflight >= self.max_inflight:
                reason = "OVERLOAD_INFLIGHT"
            elif self.backlog >= self.max_backlog:
                reason = "OVERLOAD_BACKLOG"
            elif self.tenant_inflight.get(tenant, 0) >= self.per_tenant_inflight:
                reason = "OVERLOAD_TENANT"
            if reason:
                self.shed[reason] = self.shed.get(reason, 0) + 1
                raise Overloaded(reason)
            self.inflight += 1
            self.tenant_inflight[tenant] = self.tenant_inflight.get(tenant, 0) + 1

    def done(self, tenant: str) -> None:
        with self._lock:
            if self.inflight <= 0 or self.tenant_inflight.get(tenant, 0) <= 0:
                raise RuntimeError("admission underflow")
            self.inflight -= 1
            self.tenant_inflight[tenant] -= 1


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 20
    open_s: float = 5.0
    clock: Callable[[], float] = time.monotonic
    state: BreakerState = BreakerState.CLOSED
    failures: int = 0
    opened_at: float = 0.0
    transitions: list[tuple[str, str, float]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _to(self, s: BreakerState) -> None:
        self.transitions.append((self.state.value, s.value, self.clock()))
        del self.transitions[:-256]
        self.state = s

    def allow(self) -> bool:
        with self._lock:
            if self.state is BreakerState.OPEN:
                if self.clock() - self.opened_at >= self.open_s:
                    self._to(BreakerState.HALF_OPEN)  # recovery probe
                    return True
                return False
            return True

    def success(self) -> None:
        with self._lock:
            self.failures = 0
            if self.state is not BreakerState.CLOSED:
                self._to(BreakerState.CLOSED)

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state is BreakerState.HALF_OPEN or self.failures >= self.failure_threshold:
                self.opened_at = self.clock()
                if self.state is not BreakerState.OPEN:
                    self._to(BreakerState.OPEN)
