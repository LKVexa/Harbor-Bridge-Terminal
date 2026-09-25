"""Component 42 - bounded retry, exponential backoff with full jitter, circuit
breaker and load shedding for every INV-08 dependency call.

Contract ``PK_DYN_RESILIENCE/1``:
* Only ``Inv08Error`` with a retryable outcome is retried; any other exception
  is translated (``wrap_provider_error(retryable=False)``) and never retried.
* Retries are bounded by ``max_attempts`` AND ``max_elapsed`` (seconds on the
  injected clock).  Exhaustion raises ``INV08.RETRY.EXHAUSTED`` chaining the
  last cause.
* Backoff is AWS-style "full jitter": ``uniform(0, min(cap, base*2**n))`` drawn
  from an injected, seedable ``random.Random`` (deterministic in tests).
* A per-dependency ``RetryBudget`` caps retries to a ratio of first attempts so
  a dependency outage cannot amplify into a retry storm.
* ``CircuitBreaker`` states: CLOSED -> OPEN (after ``failure_threshold``
  consecutive failures) -> HALF_OPEN (after ``reset_timeout``) -> CLOSED (after
  ``half_open_successes`` probes succeed) or back to OPEN on a probe failure.
* ``AdmissionController`` is a token bucket plus in-flight concurrency limit;
  low-priority work is shed first (priority reserve).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from .core import Inv08Error, Outcome, wrap_provider_error

T = TypeVar("T")
SCHEMA = "PK_DYN_RESILIENCE/1"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.1
    max_delay: float = 5.0
    max_elapsed: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.max_attempts, int) or not 1 <= self.max_attempts <= 20:
            raise ValueError("max_attempts must be an int in [1, 20]")
        if not (0 < self.base_delay <= self.max_delay) or self.max_elapsed <= 0:
            raise ValueError("need 0 < base_delay <= max_delay and max_elapsed > 0")

    def backoff(self, attempt: int, rng: random.Random) -> float:
        """Full-jitter delay before retry number ``attempt`` (1-based)."""
        if attempt < 1:
            raise ValueError("attempt is 1-based")
        ceiling = min(self.max_delay, self.base_delay * (2 ** min(attempt - 1, 32)))
        return rng.uniform(0.0, ceiling)


DEFAULT_POLICIES = {
    "provider": RetryPolicy(max_attempts=4, base_delay=0.2, max_delay=5.0, max_elapsed=30.0),
    "lease_store": RetryPolicy(max_attempts=3, base_delay=0.05, max_delay=1.0, max_elapsed=5.0),
    "secret_manager": RetryPolicy(max_attempts=3, base_delay=0.1, max_delay=2.0, max_elapsed=10.0),
}


class RetryBudget:
    """Allows at most ``ratio`` retries per first attempt (+ ``min_retries``)."""

    def __init__(self, ratio: float = 0.2, min_retries: int = 3) -> None:
        if not 0 <= ratio <= 1:
            raise ValueError("ratio must be in [0, 1]")
        self.ratio, self.min_retries = ratio, min_retries
        self.requests = 0
        self.retries = 0

    def on_request(self) -> None:
        self.requests += 1

    def try_spend(self) -> bool:
        if self.retries < self.min_retries + self.ratio * self.requests:
            self.retries += 1
            return True
        return False


def call_with_retry(fn: Callable[[], T], *, policy: RetryPolicy, rng: random.Random,
                    clock: Callable[[], float], sleep: Callable[[float], None],
                    dependency: str = "dependency", budget: RetryBudget | None = None,
                    breaker: "CircuitBreaker | None" = None) -> T:
    start = clock()
    if budget is not None:
        budget.on_request()
    last: Inv08Error | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            if breaker is not None:
                return breaker.call(fn)
            return fn()
        except Inv08Error as exc:
            last = exc
        except Exception as exc:  # noqa: BLE001 - translated, never retried
            raise wrap_provider_error(dependency, exc, retryable=False) from exc
        if not last.retryable or attempt == policy.max_attempts:
            break
        if budget is not None and not budget.try_spend():
            raise Inv08Error("INV08.RETRY.BUDGET_EXHAUSTED", f"{dependency}: retry budget exhausted",
                             outcome=Outcome.RETRYABLE_FAILURE, severity="warning",
                             remediation="dependency is failing broadly; wait for recovery",
                             details={"dependency": dependency, "attempt": attempt}, cause=last)
        delay = policy.backoff(attempt, rng)
        if clock() + delay - start > policy.max_elapsed:
            break
        sleep(delay)
    if last is not None and not last.retryable:
        raise last
    raise Inv08Error("INV08.RETRY.EXHAUSTED", f"{dependency}: retries exhausted",
                     outcome=Outcome.RETRYABLE_FAILURE, severity="error",
                     remediation="check dependency health; controller will retry next round",
                     details={"dependency": dependency}, cause=last)


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"

    def __init__(self, name: str, *, clock: Callable[[], float], failure_threshold: int = 5,
                 reset_timeout: float = 30.0, half_open_successes: int = 2) -> None:
        if failure_threshold < 1 or reset_timeout <= 0 or half_open_successes < 1:
            raise ValueError("invalid circuit breaker parameters")
        self.name, self._clock = name, clock
        self.failure_threshold, self.reset_timeout = failure_threshold, reset_timeout
        self.half_open_successes = half_open_successes
        self.state = self.CLOSED
        self._failures = 0
        self._successes = 0
        self._opened_at = 0.0
        self.transitions: list[tuple[str, str]] = []

    def _to(self, state: str) -> None:
        self.transitions.append((self.state, state))
        self.state = state

    def current_state(self) -> str:
        if self.state == self.OPEN and self._clock() - self._opened_at >= self.reset_timeout:
            self._to(self.HALF_OPEN)
            self._successes = 0
        return self.state

    def call(self, fn: Callable[[], T]) -> T:
        if self.current_state() == self.OPEN:
            raise Inv08Error("INV08.CIRCUIT.OPEN", f"circuit {self.name} is open",
                             outcome=Outcome.RETRYABLE_FAILURE, severity="warning",
                             remediation="dependency failing; wait for reset_timeout",
                             details={"dependency": self.name})
        try:
            result = fn()
        except Inv08Error as exc:
            if exc.retryable:
                self._record_failure()
            raise
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    def _record_failure(self) -> None:
        if self.state == self.HALF_OPEN:
            self._open()
            return
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        self._to(self.OPEN)
        self._opened_at = self._clock()
        self._failures = 0

    def _record_success(self) -> None:
        if self.state == self.HALF_OPEN:
            self._successes += 1
            if self._successes >= self.half_open_successes:
                self._to(self.CLOSED)
                self._failures = 0
        else:
            self._failures = 0


@dataclass
class AdmissionController:
    """Token bucket (rate) + concurrency limit.  ``priority`` 0 = critical
    (drain/delete/safety), 1 = normal, 2 = best effort.  The last
    ``reserve`` tokens / slots are kept for priority 0."""
    clock: Callable[[], float]
    rate: float = 10.0
    burst: int = 20
    max_in_flight: int = 16
    reserve: int = 2
    tokens: float = field(init=False)
    in_flight: int = field(init=False, default=0)
    shed: int = field(init=False, default=0)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        if self.rate <= 0 or self.burst < 1 or self.max_in_flight < 1 or not 0 <= self.reserve < self.burst:
            raise ValueError("invalid admission parameters")
        self.tokens = float(self.burst)
        self._last = self.clock()

    def _refill(self) -> None:
        now = self.clock()
        self.tokens = min(float(self.burst), self.tokens + (now - self._last) * self.rate)
        self._last = now

    def admit(self, priority: int = 1) -> None:
        self._refill()
        floor = 0 if priority == 0 else self.reserve
        slot_floor = 0 if priority == 0 else min(self.reserve, self.max_in_flight - 1)
        if self.tokens - 1 < floor or self.in_flight >= self.max_in_flight - slot_floor:
            self.shed += 1
            raise Inv08Error("INV08.ADMISSION.SHED", "request shed by admission control",
                             outcome=Outcome.RETRYABLE_FAILURE, severity="warning",
                             remediation="back off; load exceeds configured capacity",
                             details={"priority": priority, "in_flight": self.in_flight})
        self.tokens -= 1
        self.in_flight += 1

    def release(self) -> None:
        if self.in_flight <= 0:
            raise RuntimeError("release without admit")
        self.in_flight -= 1
