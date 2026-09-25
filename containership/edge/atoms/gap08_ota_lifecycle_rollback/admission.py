"""Backpressure and admission control (component 17).

Bounded everything: concurrent rollouts, wave fan-out, deferred-queue depth,
API request rate (token bucket per principal) and per-site bandwidth (see
``distribution``).  Rollback/quarantine/freeze use a **reserved priority lane**
that normal rollout traffic can never consume, so recovery is not starved
under overload.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .common import Clock, SystemClock
from .errors import Overloaded


@dataclass
class TokenBucket:
    rate_per_s: float
    burst: float
    clock: Clock = field(default_factory=SystemClock)
    _tokens: float = -1.0
    _t: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def take(self, n: float = 1.0) -> float:
        """Take ``n`` tokens; return 0 on success or the seconds to wait."""
        with self._lock:
            now = self.clock.monotonic()
            if self._tokens < 0:
                self._tokens, self._t = self.burst, now
            self._tokens = min(self.burst, self._tokens + (now - self._t) * self.rate_per_s)
            self._t = now
            if self._tokens >= n:
                self._tokens -= n
                return 0.0
            return (n - self._tokens) / self.rate_per_s


@dataclass
class AdmissionLimits:
    max_active_rollouts: int = 8
    max_wave_fanout: int = 500
    max_deferred_per_rollout: int = 1000
    api_rate_per_s: float = 20.0
    api_burst: float = 40.0
    reserved_recovery_slots: int = 4
    max_inflight_commands: int = 2000


@dataclass
class AdmissionController:
    limits: AdmissionLimits = field(default_factory=AdmissionLimits)
    clock: Clock = field(default_factory=SystemClock)
    _active: set[str] = field(default_factory=set)
    _inflight_normal: int = 0
    _inflight_recovery: int = 0
    _buckets: dict[str, TokenBucket] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def api(self, principal: str) -> None:
        with self._lock:
            b = self._buckets.setdefault(principal, TokenBucket(self.limits.api_rate_per_s, self.limits.api_burst,
                                                                self.clock))
        wait = b.take()
        if wait:
            raise Overloaded(f"rate limit for {principal}", resource=principal, retry_after_s=round(wait, 3))

    def admit_rollout(self, rollout_id: str) -> None:
        with self._lock:
            if rollout_id in self._active:
                return
            if len(self._active) >= self.limits.max_active_rollouts:
                raise Overloaded("too many active rollouts", resource=rollout_id, retry_after_s=60)
            self._active.add(rollout_id)

    def finish_rollout(self, rollout_id: str) -> None:
        with self._lock:
            self._active.discard(rollout_id)

    def check_wave(self, size: int) -> None:
        if size > self.limits.max_wave_fanout:
            raise Overloaded(f"wave fan-out {size} exceeds {self.limits.max_wave_fanout}")

    def check_deferred(self, depth: int) -> None:
        if depth > self.limits.max_deferred_per_rollout:
            raise Overloaded(f"deferred queue depth {depth} exceeds {self.limits.max_deferred_per_rollout}")

    def acquire_commands(self, n: int, *, recovery: bool) -> None:
        with self._lock:
            total = self._inflight_normal + self._inflight_recovery
            cap = self.limits.max_inflight_commands
            if recovery:
                if total + n > cap + self.limits.reserved_recovery_slots and self._inflight_recovery > 0:
                    raise Overloaded("recovery lane saturated", retry_after_s=1)
                self._inflight_recovery += n
            else:
                if self._inflight_normal + n > cap - self.limits.reserved_recovery_slots:
                    raise Overloaded("command fan-out saturated", retry_after_s=5)
                self._inflight_normal += n

    def release_commands(self, n: int, *, recovery: bool) -> None:
        with self._lock:
            if recovery:
                self._inflight_recovery = max(0, self._inflight_recovery - n)
            else:
                self._inflight_normal = max(0, self._inflight_normal - n)
