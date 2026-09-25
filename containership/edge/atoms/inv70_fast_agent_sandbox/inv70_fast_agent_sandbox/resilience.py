"""Resilience primitives for INV-70.

C025  deadlines, cancellation, idempotency keys, backpressure
C053  bounded safe-retry with capped exponential backoff and full jitter
C054  admission control (concurrency + token bucket + per-tenant quota), circuit breaker
C055  failover selection that never crosses tenant isolation / residency constraints
C056  explicit degraded-operation modes
C058  duplicate-execution protection and stale-controller fencing
"""
from __future__ import annotations

import hashlib
import random
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum


# ------------------------------------------------------------------ C025
class Deadline:
    def __init__(self, timeout_s: float, clock=time.monotonic):
        if not 0 < timeout_s <= 300:
            raise ValueError("timeout must be in (0, 300] seconds")
        self.clock = clock
        self.expires = clock() + timeout_s

    def remaining(self) -> float:
        return max(0.0, self.expires - self.clock())

    @property
    def expired(self) -> bool:
        return self.remaining() <= 0


class CancelToken:
    def __init__(self):
        self._ev = threading.Event()
        self.reason = None

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()


class IdempotencyCache:
    """Key -> (request fingerprint, result).  Same key + same request returns the
    stored result without re-executing; same key + different request is a conflict.
    In-flight keys reject duplicates (C058)."""

    def __init__(self, capacity: int = 10_000, ttl_s: float = 3600, clock=time.monotonic):
        self._d: OrderedDict = OrderedDict()
        self._inflight: dict[str, str] = {}
        self.capacity, self.ttl, self.clock = capacity, ttl_s, clock
        self._lock = threading.Lock()

    @staticmethod
    def fingerprint(request: bytes) -> str:
        return hashlib.sha256(request).hexdigest()

    def begin(self, key: str, fp: str):
        """Return ('new', None) | ('replay', result) | ('conflict', None) | ('inflight', None)."""
        now = self.clock()
        with self._lock:
            hit = self._d.get(key)
            if hit and now - hit[2] > self.ttl:
                del self._d[key]
                hit = None
            if hit:
                return ("replay", hit[1]) if hit[0] == fp else ("conflict", None)
            if key in self._inflight:
                return ("inflight", None) if self._inflight[key] == fp else ("conflict", None)
            self._inflight[key] = fp
            return ("new", None)

    def finish(self, key: str, fp: str, result, cacheable: bool = True) -> None:
        with self._lock:
            self._inflight.pop(key, None)
            if cacheable:
                self._d[key] = (fp, result, self.clock())
                self._d.move_to_end(key)
                while len(self._d) > self.capacity:
                    self._d.popitem(last=False)


# ------------------------------------------------------------------ C053
RETRYABLE_REASONS = frozenset({"overloaded", "circuit open", "backend unavailable", "worker crashed"})
NEVER_RETRY = frozenset({"out of fuel", "out of memory", "unauthenticated", "capability denied",
                         "invalid instruction", "deadline exceeded"})


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_s: float = 0.05
    cap_s: float = 1.0
    budget_ratio: float = 0.1       # retries may add at most 10% extra load
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self):
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be 1..5")
        self._tokens = 10.0

    def retryable(self, reason: str, idempotent: bool) -> bool:
        base = reason.split(":")[0]
        return idempotent and base in RETRYABLE_REASONS and base not in NEVER_RETRY

    def backoff(self, attempt: int) -> float:
        """Full jitter: uniform(0, min(cap, base * 2**attempt))."""
        return self.rng.uniform(0, min(self.cap_s, self.base_s * (2 ** attempt)))

    def note_request(self) -> None:
        self._tokens = min(10.0, self._tokens + self.budget_ratio)

    def take_retry_token(self) -> bool:
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False

    def call(self, fn, *, idempotent: bool, deadline: Deadline | None = None, sleep=time.sleep):
        attempt = 0
        while True:
            self.note_request()
            result = fn()
            reason = result.get("trap") if isinstance(result, dict) else None
            attempt += 1
            if reason is None or not self.retryable(reason, idempotent) or attempt >= self.max_attempts:
                return result
            if not self.take_retry_token():
                return result
            delay = self.backoff(attempt)
            if deadline is not None and delay >= deadline.remaining():
                return result
            sleep(delay)


# ------------------------------------------------------------------ C054
class Admission:
    """Concurrency cap + global token bucket + per-tenant in-flight quota.  Sheds
    with ``overloaded`` rather than queueing unboundedly (backpressure, C025)."""

    def __init__(self, max_concurrent: int = 64, rate_per_s: float = 1000, burst: int = 200,
                 per_tenant_concurrent: int = 16, clock=time.monotonic):
        self.max_concurrent, self.rate, self.burst = max_concurrent, rate_per_s, burst
        self.per_tenant = per_tenant_concurrent
        self.clock = clock
        self._tokens, self._last = float(burst), clock()
        self._inflight = 0
        self._tenant: dict[str, int] = {}
        self._lock = threading.Lock()
        self.shed = 0

    def try_acquire(self, tenant: str) -> str | None:
        """Return None on admit, else the shed reason."""
        with self._lock:
            now = self.clock()
            self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
            self._last = now
            if self._inflight >= self.max_concurrent:
                reason = "overloaded: concurrency"
            elif self._tenant.get(tenant, 0) >= self.per_tenant:
                reason = "overloaded: tenant quota"
            elif self._tokens < 1:
                reason = "overloaded: rate"
            else:
                self._tokens -= 1
                self._inflight += 1
                self._tenant[tenant] = self._tenant.get(tenant, 0) + 1
                return None
            self.shed += 1
            return reason

    def release(self, tenant: str) -> None:
        with self._lock:
            self._inflight -= 1
            n = self._tenant.get(tenant, 1) - 1
            if n:
                self._tenant[tenant] = n
            else:
                self._tenant.pop(tenant, None)


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive failures; half-open after
    ``cooldown_s`` admits one probe."""

    def __init__(self, threshold: int = 5, cooldown_s: float = 10.0, clock=time.monotonic):
        self.threshold, self.cooldown, self.clock = threshold, cooldown_s, clock
        self.state, self.failures, self.opened_at = "closed", 0, 0.0
        self._probe = False
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self.state == "open" and self.clock() - self.opened_at >= self.cooldown:
                self.state, self._probe = "half-open", False
            if self.state == "closed":
                return True
            if self.state == "half-open" and not self._probe:
                self._probe = True
                return True
            return False

    def record(self, success: bool) -> None:
        with self._lock:
            if success:
                self.state, self.failures = "closed", 0
            else:
                self.failures += 1
                if self.state == "half-open" or self.failures >= self.threshold:
                    self.state, self.opened_at = "open", self.clock()


# ------------------------------------------------------------------ C055
@dataclass(frozen=True)
class Site:
    name: str
    region: str
    tenants: frozenset       # tenants this site is authorized to serve
    healthy: bool = True
    config_digest: str = ""


def select_failover(sites, *, tenant: str, residency: set[str], config_digest: str, exclude=()):
    """Pick a healthy site that keeps tenant isolation, residency and config consistency.
    Returns None (fail closed) rather than violating any of them."""
    for s in sorted(sites, key=lambda s: s.name):
        if s.name in exclude or not s.healthy:
            continue
        if tenant not in s.tenants or s.region not in residency:
            continue
        if s.config_digest != config_digest:
            continue
        return s
    return None


# ------------------------------------------------------------------ C056
class Mode(str, Enum):
    NORMAL = "normal"
    REDUCED = "reduced"           # host calls off except allow-listed; smaller budgets
    READ_ONLY_CONTROL = "control-plane-degraded"  # last-known-good config, no activations
    DRAIN = "drain"               # no new admissions, finish in-flight
    HALT = "halt"                 # trust/time/audit lost: reject everything


DEGRADED_RULES = {
    Mode.NORMAL: {"admit": True, "host_calls": True, "config_changes": True, "budget_scale": 1.0},
    Mode.REDUCED: {"admit": True, "host_calls": False, "config_changes": True, "budget_scale": 0.5},
    Mode.READ_ONLY_CONTROL: {"admit": True, "host_calls": True, "config_changes": False, "budget_scale": 1.0},
    Mode.DRAIN: {"admit": False, "host_calls": True, "config_changes": False, "budget_scale": 1.0},
    Mode.HALT: {"admit": False, "host_calls": False, "config_changes": False, "budget_scale": 0.0},
}


def derive_mode(*, trust_ok: bool, time_ok: bool, audit_ok: bool, control_plane_ok: bool,
                overload: bool, draining: bool) -> Mode:
    """Deterministic mode selection. Security loss always wins (C019 precedence)."""
    if not (trust_ok and time_ok and audit_ok):
        return Mode.HALT
    if draining:
        return Mode.DRAIN
    if not control_plane_ok:
        return Mode.READ_ONLY_CONTROL
    if overload:
        return Mode.REDUCED
    return Mode.NORMAL


# ------------------------------------------------------------------ C058
class FencedLease:
    """Monotonic fencing epochs.  A controller holding a stale epoch cannot commit."""

    def __init__(self):
        self.epoch = 0
        self.holder = None
        self._lock = threading.Lock()

    def acquire(self, holder: str) -> int:
        with self._lock:
            self.epoch += 1
            self.holder = holder
            return self.epoch

    def check(self, holder: str, epoch: int) -> bool:
        with self._lock:
            return holder == self.holder and epoch == self.epoch
