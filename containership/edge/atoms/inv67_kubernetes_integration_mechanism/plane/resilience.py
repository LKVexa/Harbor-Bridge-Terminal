"""Bounded retry/backoff/jitter, admission control, circuit breaking, load
shedding and the quarantine/freeze/emergency-disable switch (items 31, 32, 35).

All primitives take an injectable clock and RNG so tests are deterministic.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from collections.abc import Callable

from .lifecycle import PlaneError

Clock = Callable[[], float]


@dataclass
class Backoff:
    """Full-jitter exponential backoff with a hard cap on attempts and delay."""
    base: float = 0.2
    cap: float = 30.0
    max_attempts: int = 8
    # Jitter only needs to decorrelate retries, not resist prediction.
    rng: random.Random = field(default_factory=lambda: random.Random(0))  # noqa: S311

    def delay(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("attempt starts at 1")
        if attempt > self.max_attempts:
            raise PlaneError("INV67_DOWNSTREAM_UNAVAILABLE", "retry budget exhausted", attempt=attempt)
        ceiling = min(self.cap, self.base * (2 ** (attempt - 1)))
        return self.rng.uniform(0, ceiling)


class RetryBudget:
    """Token budget shared across callers so retries cannot exceed a ratio of
    first attempts (prevents nested retry storms). Integer milli-tokens avoid
    float drift (0.1 added ten times is not 1.0 in binary floating point)."""

    def __init__(self, ratio: float = 0.2, min_tokens: float = 10.0):
        self.ratio_m = int(round(ratio * 1000))
        self.m = int(min_tokens * 1000)
        self.max_m = self.m * 10
        self._lock = threading.Lock()

    @property
    def tokens(self) -> float:
        return self.m / 1000

    def on_request(self):
        with self._lock:
            self.m = min(self.max_m, self.m + self.ratio_m)

    def try_retry(self) -> bool:
        with self._lock:
            if self.m >= 1000:
                self.m -= 1000
                return True
            return False


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half-open"

    def __init__(self, threshold: int = 5, reset_after: float = 30.0, clock: Clock = time.monotonic):
        self.threshold, self.reset_after, self.clock = threshold, reset_after, clock
        self.failures, self.state, self.opened_at = 0, self.CLOSED, 0.0
        self._lock = threading.Lock()
        self._probe_inflight = False

    def allow(self) -> None:
        with self._lock:
            if self.state == self.OPEN:
                if self.clock() - self.opened_at >= self.reset_after:
                    self.state = self.HALF_OPEN
                else:
                    raise PlaneError("INV67_CIRCUIT_OPEN", "downstream circuit open")
            if self.state == self.HALF_OPEN:
                if self._probe_inflight:
                    raise PlaneError("INV67_CIRCUIT_OPEN", "half-open probe in flight")
                self._probe_inflight = True

    def record(self, ok: bool) -> None:
        with self._lock:
            self._probe_inflight = False
            if ok:
                self.failures, self.state = 0, self.CLOSED
                return
            self.failures += 1
            if self.state == self.HALF_OPEN or self.failures >= self.threshold:
                self.state, self.opened_at = self.OPEN, self.clock()

    def call(self, fn, *a, **kw):
        self.allow()
        try:
            out = fn(*a, **kw)
        except Exception:
            self.record(False)
            raise
        self.record(True)
        return out


class TokenBucket:
    def __init__(self, rate: float, burst: float, clock: Clock = time.monotonic):
        self.rate, self.burst, self.clock = rate, burst, clock
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


class Admission:
    """Per-tenant fair admission + global in-flight ceiling (load shedding).

    Security-sensitive uncertainty fails closed: an unknown tenant gets the
    default (smallest) quota, never an unlimited one."""

    def __init__(self, global_inflight: int, per_tenant_inflight: dict[str, int], default_tenant_inflight: int,
                 rate: float, burst: float, clock: Clock = time.monotonic):
        self.global_max = global_inflight
        self.quotas = dict(per_tenant_inflight)
        self.default = default_tenant_inflight
        self.inflight: dict[str, int] = {}
        self.total = 0
        self.buckets: dict[str, TokenBucket] = {}
        self.rate, self.burst, self.clock = rate, burst, clock
        self.shed = 0
        self._lock = threading.Lock()

    def acquire(self, tenant: str) -> None:
        with self._lock:
            b = self.buckets.setdefault(tenant, TokenBucket(self.rate, self.burst, self.clock))
            if self.total >= self.global_max:
                self.shed += 1
                raise PlaneError("INV67_OVERLOADED", "global in-flight ceiling reached", tenant=tenant)
            if self.inflight.get(tenant, 0) >= self.quotas.get(tenant, self.default):
                self.shed += 1
                raise PlaneError("INV67_QUOTA_EXCEEDED", "tenant in-flight quota reached", tenant=tenant)
            if not b.take():
                self.shed += 1
                raise PlaneError("INV67_OVERLOADED", "tenant rate limit", tenant=tenant)
            self.inflight[tenant] = self.inflight.get(tenant, 0) + 1
            self.total += 1

    def release(self, tenant: str) -> None:
        with self._lock:
            if self.inflight.get(tenant, 0) <= 0:
                raise RuntimeError("release without acquire")
            self.inflight[tenant] -= 1
            self.total -= 1


class Switchboard:
    """Quarantine/freeze/emergency-disable controls. Every change is audited by
    the caller; freeze blocks new launches but lets deletes/cancellation proceed."""

    def __init__(self):
        self.frozen = False
        self.freeze_reason = ""
        self.quarantined: dict[str, str] = {}
        self._lock = threading.Lock()

    def freeze(self, reason: str):
        if not reason:
            raise ValueError("freeze requires a reason")
        with self._lock:
            self.frozen, self.freeze_reason = True, reason

    def unfreeze(self):
        with self._lock:
            self.frozen, self.freeze_reason = False, ""

    def quarantine(self, key: str, reason: str):
        if not reason:
            raise ValueError("quarantine requires a reason")
        with self._lock:
            self.quarantined[key] = reason

    def release(self, key: str):
        with self._lock:
            self.quarantined.pop(key, None)

    def check_launch(self, key: str, namespace: str) -> None:
        with self._lock:
            if self.frozen:
                raise PlaneError("INV67_FROZEN", f"launches frozen: {self.freeze_reason}")
            for k in (key, f"ns:{namespace}"):
                if k in self.quarantined:
                    raise PlaneError("INV67_QUARANTINED", f"{k} quarantined: {self.quarantined[k]}")
