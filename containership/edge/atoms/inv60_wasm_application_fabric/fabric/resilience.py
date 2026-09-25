"""M19/M43/M44 - deadlines, cancellation, retries, idempotency, circuit breaking.

- Deadline: absolute monotonic expiry propagated hop to hop (remaining budget).
- CancelToken: cooperative cancellation; post-commit operations are uncancellable.
- RetryPolicy: capped exponential backoff with full jitter and a shared retry
  budget (ratio of retries to requests) to prevent retry storms; only
  operations classified idempotent (or carrying an idempotency key) are retried.
- IdempotencyStore: key -> (request fingerprint, result); reuse with a different
  request is IDEMPOTENCY_MISMATCH; entries expire after retention.
- CircuitBreaker: closed/open/half-open with failure threshold and cool-down.
"""
from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from dataclasses import dataclass, field

from .errors import FabricError

RETRY_SAFE = {"call.idempotent": True, "status": True, "start": False, "stop": True,
              "link": True, "unlink": True, "push": True, "call": False}


@dataclass
class Deadline:
    expires_at: float
    clock: object = time.monotonic

    @classmethod
    def after(cls, seconds: float, clock=time.monotonic) -> "Deadline":
        return cls(clock() + seconds, clock)

    def remaining(self) -> float:
        return self.expires_at - self.clock()

    def check(self, hop: str = "") -> None:
        if self.remaining() <= 0:
            raise FabricError("DEADLINE_EXCEEDED", f"deadline expired at hop {hop!r}", detail={"hop": hop})

    def child(self, reserve_s: float = 0.0) -> "Deadline":
        return Deadline(self.expires_at - reserve_s, self.clock)


class CancelToken:
    def __init__(self) -> None:
        self._ev = threading.Event()
        self.committed = False

    def cancel(self) -> bool:
        if self.committed:
            return False  # cannot cancel after commit
        self._ev.set()
        return True

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def check(self) -> None:
        if self._ev.is_set() and not self.committed:
            raise FabricError("CANCELLED", "operation cancelled")


@dataclass
class RetryBudget:
    ratio: float = 0.2
    min_retries: int = 10
    requests: int = 0
    retries: int = 0

    def record_request(self) -> None:
        self.requests += 1

    def can_retry(self) -> bool:
        return self.retries < max(self.min_retries, self.ratio * self.requests)

    def spend(self) -> None:
        self.retries += 1


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_s: float = 0.01
    cap_s: float = 1.0
    budget: RetryBudget = field(default_factory=RetryBudget)
    rng: random.Random = field(default_factory=lambda: random.Random(0))
    sleep: object = time.sleep

    def backoff(self, attempt: int) -> float:
        return self.rng.uniform(0, min(self.cap_s, self.base_s * (2 ** attempt)))

    def run(self, fn, *, op_class: str, deadline: Deadline | None = None,
            idempotency_key: str | None = None, cancel: CancelToken | None = None):
        safe = RETRY_SAFE.get(op_class, False) or idempotency_key is not None
        self.budget.record_request()
        attempt = 0
        while True:
            if deadline:
                deadline.check(f"attempt-{attempt}")
            if cancel:
                cancel.check()
            try:
                return fn()
            except FabricError as e:
                retryable = e.code in ("UNAVAILABLE", "CIRCUIT_OPEN", "OVERLOADED", "RATE_LIMITED", "PROVIDER_ERROR")
                attempt += 1
                if not (safe and retryable) or attempt >= self.max_attempts or not self.budget.can_retry():
                    raise
                self.budget.spend()
                delay = max(self.backoff(attempt), e.retry_after_s or 0.0)
                if deadline and delay >= deadline.remaining():
                    raise FabricError("DEADLINE_EXCEEDED", "retry backoff exceeds remaining deadline") from e
                self.sleep(delay)


def fingerprint(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True, default=str).encode()).hexdigest()


class IdempotencyStore:
    def __init__(self, retention_s: float = 86400.0, max_entries: int = 100_000, clock=time.time) -> None:
        self.retention_s, self.max_entries, self.clock = retention_s, max_entries, clock
        self._d: dict[str, tuple[str, object, float]] = {}

    def lookup(self, key: str, request: dict):
        self._gc()
        if not isinstance(key, str) or not (8 <= len(key) <= 128):
            raise FabricError("INVALID_ARGUMENT", "idempotency key must be 8..128 chars")
        hit = self._d.get(key)
        if hit is None:
            return None
        if hit[0] != fingerprint(request):
            raise FabricError("IDEMPOTENCY_MISMATCH", "idempotency key reused with different request")
        return hit[1]

    def store(self, key: str, request: dict, result) -> None:
        if len(self._d) >= self.max_entries:
            oldest = min(self._d, key=lambda k: self._d[k][2])
            del self._d[oldest]
        self._d[key] = (fingerprint(request), result, self.clock())

    def _gc(self) -> None:
        now = self.clock()
        for k in [k for k, v in self._d.items() if now - v[2] > self.retention_s]:
            del self._d[k]


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, cooldown_s: float = 5.0, clock=time.monotonic) -> None:
        self.failure_threshold, self.cooldown_s, self.clock = failure_threshold, cooldown_s, clock
        self.state, self.failures, self.opened_at = "closed", 0, 0.0

    def before(self) -> None:
        if self.state == "open":
            if self.clock() - self.opened_at >= self.cooldown_s:
                self.state = "half_open"
            else:
                raise FabricError("CIRCUIT_OPEN", "circuit open",
                                  retry_after_s=round(self.cooldown_s - (self.clock() - self.opened_at), 3))

    def success(self) -> None:
        self.state, self.failures = "closed", 0

    def failure(self) -> None:
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.failure_threshold:
            self.state, self.opened_at = "open", self.clock()
