"""Retry, circuit breaker, admission/load-shedding, dependency health (MC-022, MC-023, MC-025).

SPDX-License-Identifier: NOASSERTION
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RetryPolicy:
    base_s: float = 0.5
    cap_s: float = 30.0
    max_attempts: int = 6
    budget_ratio: float = 0.2      # retries may be at most 20% of first attempts (token bucket)

    def backoff(self, attempt: int, rng: random.Random) -> float:
        """Full-jitter exponential backoff (AWS architecture-blog formulation)."""
        if attempt < 1:
            raise ValueError("attempt starts at 1")
        return rng.uniform(0, min(self.cap_s, self.base_s * (2 ** (attempt - 1))))


class RetryBudget:
    def __init__(self, ratio: float, min_tokens: float = 3.0, cap: float = 50.0) -> None:
        self.ratio, self.tokens, self.cap = ratio, min_tokens, cap
        self._lock = threading.Lock()

    def on_first_attempt(self) -> None:
        with self._lock:
            self.tokens = min(self.cap, self.tokens + self.ratio)

    def try_spend(self) -> bool:
        with self._lock:
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


class CircuitOpen(RuntimeError):
    code = "DEPENDENCY_CIRCUIT_OPEN"


class CircuitBreaker:
    """closed -> open after N consecutive failures -> half_open after cool-down -> one probe."""

    def __init__(self, name: str, failure_threshold: int = 5, cooldown_s: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.name, self.threshold, self.cooldown = name, failure_threshold, cooldown_s
        self.state, self.failures, self.opened_at = "closed", 0, 0.0
        self._probe_in_flight = False
        self._clock = clock
        self._lock = threading.Lock()

    def before_call(self) -> None:
        with self._lock:
            if self.state == "open":
                if self._clock() - self.opened_at >= self.cooldown:
                    self.state = "half_open"
                else:
                    raise CircuitOpen(f"{self.name} circuit open")
            if self.state == "half_open":
                if self._probe_in_flight:
                    raise CircuitOpen(f"{self.name} half-open probe already in flight")
                self._probe_in_flight = True

    def record(self, success: bool) -> None:
        with self._lock:
            self._probe_in_flight = False
            if success:
                self.state, self.failures = "closed", 0
                return
            self.failures += 1
            if self.state == "half_open" or self.failures >= self.threshold:
                self.state, self.opened_at = "open", self._clock()


class Overloaded(RuntimeError):
    code = "OVERLOADED"
    retryable = True


class AdmissionController:
    """Bounded in-flight work with a bounded queue; beyond it requests are shed with 429."""

    def __init__(self, max_in_flight: int = 32, max_queue: int = 128) -> None:
        self.max_in_flight, self.max_queue = max_in_flight, max_queue
        self.in_flight = 0
        self.queued = 0
        self.shed = 0
        self._cv = threading.Condition()

    def acquire(self, timeout_s: float) -> None:
        with self._cv:
            if self.in_flight >= self.max_in_flight:
                if self.queued >= self.max_queue:
                    self.shed += 1
                    raise Overloaded("admission queue full")
                self.queued += 1
                try:
                    if not self._cv.wait_for(lambda: self.in_flight < self.max_in_flight, timeout_s):
                        self.shed += 1
                        raise Overloaded("admission wait timed out")
                finally:
                    self.queued -= 1
            self.in_flight += 1

    def release(self) -> None:
        with self._cv:
            self.in_flight -= 1
            self._cv.notify()


class DependencyHealth:
    """Tracks dependency state; new expansion is refused (degraded mode) when a
    mandatory dependency is unhealthy, while status/observation stay available."""

    MANDATORY = ("state_store", "hypervisor_adapter", "observation", "authorization")

    def __init__(self) -> None:
        self.status: dict[str, str] = {d: "unknown" for d in self.MANDATORY}

    def set(self, dep: str, status: str) -> None:
        if status not in ("healthy", "degraded", "down", "unknown"):
            raise ValueError(status)
        self.status[dep] = status

    def mode(self) -> str:
        if all(v == "healthy" for v in self.status.values()):
            return "normal"
        return "degraded"

    def expansion_allowed(self) -> tuple[bool, list[str]]:
        bad = [k for k, v in self.status.items() if v != "healthy"]
        return (not bad, bad)
