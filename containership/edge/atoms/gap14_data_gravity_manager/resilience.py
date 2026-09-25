"""Deadlines, cancellation, retry, circuit breaking, admission and freshness.

Covers G14-P1-13 (timeout/cancellation/backpressure), P1-14 (retry/circuit
breaker, idempotent reads only), P1-15 (freshness/TTL), P1-16 (stale-data
fail-safe) and P1-21 (admission control/resource bounds).
"""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, TypeVar

from .errors import G14Error
from .trust import Clock, SystemClock

T = TypeVar("T")


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()
        self.reason: str | None = None

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise G14Error("G14_CANCELLED", self.reason or "cancelled")


class Deadline:
    """Absolute monotonic deadline propagated to every dependency call."""

    def __init__(self, budget_s: float, clock: Clock | None = None, token: CancellationToken | None = None):
        if not (0 < budget_s <= 60):
            raise G14Error("G14_INVALID_REQUEST", "deadline budget must be in (0, 60] seconds")
        self.clock = clock or SystemClock()
        self.expires = self.clock.monotonic() + budget_s
        self.token = token or CancellationToken()

    def remaining(self) -> float:
        return self.expires - self.clock.monotonic()

    def check(self, stage: str) -> None:
        self.token.raise_if_cancelled()
        if self.remaining() <= 0:
            raise G14Error("G14_DEADLINE_EXCEEDED", f"deadline exceeded at {stage}", details={"stage": stage})

    def child(self, cap_s: float) -> float:
        """Timeout for one dependency call: min(cap, remaining)."""
        self.check("dependency-dispatch")
        return max(0.0, min(cap_s, self.remaining()))


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_s: float = 0.02
    max_delay_s: float = 0.25
    jitter: float = 0.5
    retry_codes: frozenset[str] = frozenset({"G14_DEPENDENCY_TIMEOUT", "G14_DEPENDENCY_UNAVAILABLE"})

    def __post_init__(self) -> None:
        if not (1 <= self.max_attempts <= 5):
            raise ValueError("max_attempts must be 1..5 (bounded retry amplification)")

    def delay(self, attempt: int, rng: random.Random) -> float:
        d = min(self.max_delay_s, self.base_delay_s * (2 ** attempt))
        return d * (1 - self.jitter + rng.random() * self.jitter)


class CircuitBreaker:
    """closed -> open after N consecutive failures; half-open after cool-down."""

    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half-open"

    def __init__(self, name: str, failure_threshold: int = 5, reset_after_s: float = 10.0, clock: Clock | None = None):
        self.name, self.failure_threshold, self.reset_after_s = name, failure_threshold, reset_after_s
        self.clock = clock or SystemClock()
        self._state, self._failures, self._opened_at = self.CLOSED, 0, 0.0
        self._probe_inflight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN and self.clock.monotonic() - self._opened_at >= self.reset_after_s:
                self._state = self.HALF_OPEN
            return self._state

    def before(self) -> None:
        st = self.state
        with self._lock:
            if st == self.OPEN or (st == self.HALF_OPEN and self._probe_inflight):
                raise G14Error("G14_CIRCUIT_OPEN", f"circuit open for {self.name}", details={"dependency": self.name})
            if st == self.HALF_OPEN:
                self._probe_inflight = True

    def success(self) -> None:
        with self._lock:
            self._state, self._failures, self._probe_inflight = self.CLOSED, 0, False

    def failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._probe_inflight = False
            if self._state == self.HALF_OPEN or self._failures >= self.failure_threshold:
                self._state, self._opened_at = self.OPEN, self.clock.monotonic()


def call_with_resilience(fn: Callable[[float], T], *, dependency: str, deadline: Deadline, timeout_cap_s: float,
                         breaker: CircuitBreaker, retry: RetryPolicy, idempotent: bool,
                         rng: random.Random | None = None, sleep: Callable[[float], None] | None = None,
                         on_attempt: Callable[[str, str], None] | None = None) -> T:
    """Invoke ``fn(timeout)`` under deadline, breaker and (idempotent-only) retry."""
    rng = rng or random.Random()
    sleep = sleep or (lambda s: threading.Event().wait(s))
    attempts = retry.max_attempts if idempotent else 1
    last: G14Error | None = None
    first: str | None = None
    tried = 0
    for attempt in range(attempts):
        tried = attempt + 1
        timeout = deadline.child(timeout_cap_s)
        breaker.before()
        try:
            result = fn(timeout)
        except G14Error as exc:
            if exc.code in retry.retry_codes:
                breaker.failure()
                last = exc
                first = first or exc.code
                if on_attempt:
                    on_attempt(dependency, exc.code)
                if attempt + 1 < attempts:
                    pause = retry.delay(attempt, rng)
                    if pause >= deadline.remaining():
                        break
                    sleep(pause)
                continue
            breaker.success() if exc.reason.category != "dependency" else breaker.failure()
            raise
        except TimeoutError as exc:
            breaker.failure()
            last = G14Error("G14_DEPENDENCY_TIMEOUT", f"{dependency} timed out", details={"dependency": dependency})
            continue
        except Exception as exc:  # unexpected adapter fault -> dependency unavailable
            breaker.failure()
            last = G14Error("G14_DEPENDENCY_UNAVAILABLE", f"{dependency} failed: {type(exc).__name__}", details={"dependency": dependency})
            if attempt + 1 < attempts:
                continue
            break
        breaker.success()
        return result
    assert last is not None
    last.details.setdefault("dependency", dependency)
    last.details["attempts"] = tried
    last.details["first_error"] = first or last.code
    raise last


class AdmissionController:
    """Bounded concurrency, bounded queue wait, payload size and batch limits."""

    def __init__(self, max_concurrent: int = 4, max_payload_bytes: int = 256 * 1024,
                 max_batch: int = 500, acquire_timeout_s: float = 0.05, max_per_tenant: int | None = None):
        self.max_concurrent, self.max_payload_bytes = max_concurrent, max_payload_bytes
        self.max_batch, self.acquire_timeout_s = max_batch, acquire_timeout_s
        self._sem = threading.BoundedSemaphore(max_concurrent)
        self._inflight = 0
        self._lock = threading.Lock()
        self.rejected = 0
        # fairness: one tenant may hold at most this many slots (0/None = no per-tenant cap)
        self.max_per_tenant = max_per_tenant or max_concurrent
        self._per_tenant: dict[str, int] = {}

    def tenant_slot(self, tenant: str) -> "_TenantSlot":
        return _TenantSlot(self, tenant)

    def check_payload(self, size_bytes: int, batch: int = 1) -> None:
        if size_bytes > self.max_payload_bytes or batch > self.max_batch:
            self.rejected += 1
            raise G14Error("G14_PAYLOAD_TOO_LARGE", "payload/batch exceeds bounds",
                           details={"size_bytes": size_bytes, "batch": batch,
                                    "max_bytes": self.max_payload_bytes, "max_batch": self.max_batch})

    def __enter__(self) -> "AdmissionController":
        if not self._sem.acquire(timeout=self.acquire_timeout_s):
            with self._lock:
                self.rejected += 1
            raise G14Error("G14_OVERLOADED", "concurrency limit reached", details={"max_concurrent": self.max_concurrent})
        with self._lock:
            self._inflight += 1
        return self

    def __exit__(self, *exc: Any) -> None:
        with self._lock:
            self._inflight -= 1
        self._sem.release()

    @property
    def inflight(self) -> int:
        return self._inflight


class _TenantSlot:
    def __init__(self, ac: AdmissionController, tenant: str):
        self.ac, self.tenant = ac, tenant

    def __enter__(self) -> "_TenantSlot":
        with self.ac._lock:
            n = self.ac._per_tenant.get(self.tenant, 0)
            if n >= self.ac.max_per_tenant:
                self.ac.rejected += 1
                raise G14Error("G14_OVERLOADED", "per-tenant concurrency limit reached",
                               details={"max_per_tenant": self.ac.max_per_tenant})
            self.ac._per_tenant[self.tenant] = n + 1
        return self

    def __exit__(self, *exc: Any) -> None:
        with self.ac._lock:
            n = self.ac._per_tenant.get(self.tenant, 1) - 1
            if n <= 0:
                self.ac._per_tenant.pop(self.tenant, None)
            else:
                self.ac._per_tenant[self.tenant] = n


# ---------------------------------------------------------------- freshness/TTL
DEFAULT_TTLS: Mapping[str, float] = {
    "policy_verdict": 300.0,       # residency verdicts: 5 min
    "topology_snapshot": 600.0,    # locality/route: 10 min
    "convergence_proof": 60.0,     # replication state changes quickly
    "placement_snapshot": 120.0,   # capacity changes quickly
    "price_feed": 3600.0,          # egress pricing: hourly
}


@dataclass(frozen=True)
class FreshnessPolicy:
    ttls: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_TTLS))
    max_skew_s: float = 5.0

    def ttl(self, kind: str) -> float:
        if kind not in self.ttls:
            raise G14Error("G14_CONFIG_INVALID", f"no TTL configured for {kind}")
        return self.ttls[kind]


@dataclass(frozen=True)
class StaleDataPolicy:
    """When may a cached/stale input be used?  (P1-16)

    * residency (policy_verdict) and convergence_proof: NEVER beyond TTL.  A stale
      "allow" could move regulated or conflicting data -> fail closed.
    * topology/price may be used up to ``grace_factor`` x TTL *only* in shadow or
      simulation mode, marked ``degraded``; production decisions fail closed.
    """

    never_stale: frozenset[str] = frozenset({"policy_verdict", "convergence_proof", "placement_snapshot"})
    grace_factor: float = 2.0

    def allowed_age(self, kind: str, ttl: float, mode: str) -> float:
        if kind in self.never_stale or mode == "production":
            return ttl
        return ttl * self.grace_factor
