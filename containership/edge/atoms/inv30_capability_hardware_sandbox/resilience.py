# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Resilience primitives (GAP-018, GAP-033..GAP-038).

Retry is offered **only** for codes the failure table marks retryable; security
refusals are never retried. Circuit breaker, admission control, deadlines and a
stall detector are deterministic given an injected clock.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass

from .errors import CODES, Cancelled, CircuitOpen, DeadlineExceeded, Overloaded


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_s: float = 0.05
    cap_s: float = 2.0

    def delays(self, rng: random.Random) -> list[float]:
        """Full-jitter exponential backoff (AWS style), bounded."""
        return [rng.uniform(0, min(self.cap_s, self.base_s * 2 ** i)) for i in range(self.max_attempts - 1)]

    def run(self, fn, *, rng: random.Random | None = None, sleep=time.sleep, deadline=None):
        rng = rng or random.Random()
        delays = self.delays(rng)
        for attempt in range(self.max_attempts):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                code = getattr(exc, "code", "INTERNAL")
                retryable = CODES.get(code, CODES["INTERNAL"])[1]
                if not retryable or attempt == self.max_attempts - 1:
                    raise
                if deadline is not None:
                    deadline.check()
                sleep(delays[attempt])


class Deadline:
    def __init__(self, timeout_s: float, *, clock=time.monotonic):
        self.clock, self.expires = clock, clock() + timeout_s
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def check(self):
        if self._cancelled.is_set():
            raise Cancelled("operation cancelled by caller")
        if self.clock() > self.expires:
            raise DeadlineExceeded("deadline exceeded")


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half-open"

    def __init__(self, *, failure_threshold=5, reset_s=10.0, clock=time.monotonic):
        self.threshold, self.reset_s, self.clock = failure_threshold, reset_s, clock
        self.state, self.failures, self.opened_at = self.CLOSED, 0, 0.0
        self._lock = threading.Lock()

    def call(self, fn):
        with self._lock:
            if self.state == self.OPEN:
                if self.clock() - self.opened_at >= self.reset_s:
                    self.state = self.HALF_OPEN
                else:
                    raise CircuitOpen("dependency circuit open")
        try:
            result = fn()
        except Exception as exc:
            if CODES.get(getattr(exc, "code", "INTERNAL"), CODES["INTERNAL"])[0] in ("dependency", "timeout", "internal"):
                with self._lock:
                    self.failures += 1
                    if self.state == self.HALF_OPEN or self.failures >= self.threshold:
                        self.state, self.opened_at = self.OPEN, self.clock()
            raise
        with self._lock:
            self.state, self.failures = self.CLOSED, 0
        return result


class AdmissionController:
    """Bounded in-flight + per-tenant token bucket. Excess load is shed with OVERLOADED."""

    def __init__(self, *, max_inflight: int, tenant_rate: float, tenant_burst: int, clock=time.monotonic):
        self.max_inflight, self.rate, self.burst, self.clock = max_inflight, tenant_rate, tenant_burst, clock
        self.inflight, self.shed = 0, 0
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def __enter__(self):
        return self

    def admit(self, tenant: str):
        with self._lock:
            now = self.clock()
            tokens, last = self._buckets.get(tenant, [float(self.burst), now])
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if self.inflight >= self.max_inflight or tokens < 1:
                self.shed += 1
                self._buckets[tenant] = [tokens, now]
                raise Overloaded("admission refused: capacity or tenant quota exhausted")
            self._buckets[tenant] = [tokens - 1, now]
            self.inflight += 1
        return _Ticket(self)

    def saturation(self) -> float:
        return self.inflight / self.max_inflight


class _Ticket:
    def __init__(self, ac):
        self.ac = ac

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        with self.ac._lock:
            self.ac.inflight -= 1
        return False


class StallDetector:
    """Flags stalled when no progress heartbeat for ``stall_s`` while work is in flight."""

    def __init__(self, *, stall_s: float = 5.0, clock=time.monotonic):
        self.stall_s, self.clock, self.last = stall_s, clock, clock()

    def beat(self):
        self.last = self.clock()

    def stalled(self, inflight: int) -> bool:
        return inflight > 0 and self.clock() - self.last > self.stall_s
