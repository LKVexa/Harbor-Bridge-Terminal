"""Idempotency, deadlines, cancellation, retry, circuit breaking, load shedding, dependency health.

MC-017 (C025, C028, C053-C054), MC-040 (C052, C056), MC-041.

Retry classification comes from the error registry: only ``retryable`` codes are
retried, with capped exponential backoff and full jitter, never past the caller's
deadline.  A breaker opens after ``failure_threshold`` consecutive failures and
half-opens after ``reset_after_s`` (one probe).  The shedder bounds in-flight work
globally and per tenant (fairness: no tenant may hold more than its share).
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

from .errors import EcpError
from .util import now

T = TypeVar("T")


class Deadline:
    def __init__(self, budget_ms: float, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.expires = clock() + budget_ms / 1000.0
        self._cancelled = threading.Event()

    def remaining(self) -> float:
        return max(0.0, self.expires - self.clock())

    def cancel(self) -> None:
        self._cancelled.set()

    def check(self, where: str = "") -> None:
        if self._cancelled.is_set():
            raise EcpError("ECP_CANCELLED", f"cancelled {where}".strip())
        if self.clock() >= self.expires:
            raise EcpError("ECP_DEADLINE_EXCEEDED", f"deadline exceeded {where}".strip())


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_s: float = 0.02
    cap_s: float = 1.0
    rng: random.Random = field(default_factory=random.Random)
    sleep: Callable[[float], None] = time.sleep

    def run(self, fn: Callable[[], T], deadline: Optional[Deadline] = None) -> T:
        attempt = 0
        while True:
            attempt += 1
            try:
                return fn()
            except EcpError as e:
                if not e.spec.retryable or attempt >= self.max_attempts:
                    raise
                delay = self.rng.uniform(0, min(self.cap_s, self.base_s * 2 ** (attempt - 1)))
                if deadline is not None:
                    if deadline.remaining() <= delay:
                        raise EcpError("ECP_DEADLINE_EXCEEDED", "retry budget exhausted by deadline") from None
                self.sleep(delay)


class CircuitBreaker:
    def __init__(self, name: str, *, failure_threshold: int = 5, reset_after_s: float = 5.0,
                 clock: Callable[[], float] = now):
        self.name = name
        self.threshold = failure_threshold
        self.reset_after = reset_after_s
        self.clock = clock
        self.state = "closed"
        self.failures = 0
        self.opened_at = 0.0
        self._probe = False
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_after and not self._probe:
                    self.state, self._probe = "half_open", True
                else:
                    raise EcpError("ECP_CIRCUIT_OPEN", f"{self.name} circuit open", dependency=self.name,
                                   retry_after_ms=int(max(0, self.reset_after - (self.clock() - self.opened_at)) * 1000))
            elif self.state == "half_open" and self._probe:
                raise EcpError("ECP_CIRCUIT_OPEN", f"{self.name} probe in flight", dependency=self.name)
            elif self.state == "half_open":
                self._probe = True
        try:
            result = fn()
        except EcpError as e:
            if e.spec.category == "dependency":
                self._failure()
            else:
                self._success()
            raise
        except Exception:
            self._failure()
            raise
        self._success()
        return result

    def _failure(self) -> None:
        with self._lock:
            self.failures += 1
            self._probe = False
            if self.state == "half_open" or self.failures >= self.threshold:
                self.state, self.opened_at = "open", self.clock()

    def _success(self) -> None:
        with self._lock:
            self.state, self.failures, self._probe = "closed", 0, False


class LoadShedder:
    """Bounded concurrency with a per-tenant ceiling (fair share)."""

    def __init__(self, max_inflight: int, per_tenant_max: int):
        self.max = max_inflight
        self.per_tenant = per_tenant_max
        self.inflight = 0
        self.by_tenant: dict[str, int] = {}
        self.shed = 0
        self._lock = threading.Lock()

    def acquire(self, tenant: str) -> None:
        with self._lock:
            if self.inflight >= self.max or self.by_tenant.get(tenant, 0) >= self.per_tenant:
                self.shed += 1
                raise EcpError("ECP_OVERLOADED", "admission capacity exhausted", tenant=tenant,
                               retry_after_ms=50, limit=self.max)
            self.inflight += 1
            self.by_tenant[tenant] = self.by_tenant.get(tenant, 0) + 1

    def release(self, tenant: str) -> None:
        with self._lock:
            self.inflight -= 1
            self.by_tenant[tenant] -= 1
            if not self.by_tenant[tenant]:
                del self.by_tenant[tenant]


class DependencyHealth:
    """Tracks dependency state and derives the control-plane mode (MC-040).

    A *required* dependency that is down puts the plane in ``degraded`` mode:
    admissions that need it fail closed with ``ECP_DEPENDENCY_UNAVAILABLE``;
    read paths (inventory, audit query, explain) keep serving.
    """

    def __init__(self, clock: Callable[[], float] = now):
        self.clock = clock
        self.deps: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register(self, name: str, required: bool) -> None:
        with self._lock:
            self.deps.setdefault(name, {"required": required, "status": "unknown", "since": self.clock(),
                                        "last_error": None})

    def report(self, name: str, ok: bool, error: Optional[str] = None) -> None:
        with self._lock:
            d = self.deps.setdefault(name, {"required": False, "status": "unknown", "since": self.clock(),
                                            "last_error": None})
            status = "up" if ok else "down"
            if d["status"] != status:
                d["status"], d["since"] = status, self.clock()
            d["last_error"] = None if ok else (error or "error")[:200]

    def mode(self) -> str:
        with self._lock:
            return "degraded" if any(d["required"] and d["status"] == "down" for d in self.deps.values()) else "normal"

    def require(self, name: str) -> None:
        with self._lock:
            d = self.deps.get(name)
            if d and d["status"] == "down":
                raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", f"{name} unavailable", dependency=name)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {k: dict(v) for k, v in self.deps.items()}


class IdempotencyStore:
    """request key -> (request digest, decision). Reuse with a different body is a conflict."""

    def __init__(self, capacity: int = 100_000):
        self.capacity = capacity
        self._m: dict[str, tuple[str, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, digest: str) -> Optional[dict[str, Any]]:
        with self._lock:
            hit = self._m.get(key)
        if hit is None:
            return None
        if hit[0] != digest:
            raise EcpError("ECP_IDEMPOTENCY_CONFLICT", "idempotency key reused with a different request",
                           request_id=key[:128])
        return hit[1]

    def put(self, key: str, digest: str, decision: dict[str, Any]) -> None:
        with self._lock:
            self._m[key] = (digest, decision)
            while len(self._m) > self.capacity:
                self._m.pop(next(iter(self._m)))

    def __len__(self) -> int:
        return len(self._m)
