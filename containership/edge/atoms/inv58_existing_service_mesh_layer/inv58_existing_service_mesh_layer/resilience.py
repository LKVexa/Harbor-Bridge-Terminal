"""Retry timing safety, overload protection, lifecycle, fencing, quarantine.

MC-018 (INV-58-C053/C054), MC-019 (C055–C059), MC-003 lifecycle (C014/C015),
MC-006 timeout/cancel/backpressure (C025).
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable, Iterable

from .errors import MeshError

# ---------------------------------------------------------------- retry safety
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE", "TRACE"})
RETRYABLE_OUTCOMES = frozenset({"connect_failure", "refused_stream", "unavailable", "reset_before_request"})


def retry_safe(method: str, *, idempotency_key: str | None = None, outcome: str = "unavailable") -> bool:
    """A call may be retried only when replay cannot duplicate side effects:
    idempotent method, or a non-idempotent method carrying an idempotency key,
    *and* a failure class that is known safe to retry."""
    m = str(method).upper()
    if outcome not in RETRYABLE_OUTCOMES:
        return False
    return m in IDEMPOTENT_METHODS or bool(idempotency_key)


@dataclass(frozen=True)
class BackoffPolicy:
    base_delay_ms: int = 25
    max_delay_ms: int = 2_000
    max_elapsed_ms: int = 10_000

    def delays(self, attempts: int, rng: random.Random | None = None) -> list[float]:
        """Full-jitter exponential delays (seconds) between ``attempts`` tries,
        capped per-delay and in total."""
        rng = rng or random.Random()
        out, total = [], 0.0
        for i in range(max(0, attempts - 1)):
            cap = min(self.max_delay_ms, self.base_delay_ms * (2 ** i))
            d = rng.uniform(0, cap)
            if total + d > self.max_elapsed_ms:
                break
            total += d
            out.append(d / 1000.0)
        return out


class CancelToken:
    def __init__(self):
        self._ev = threading.Event()

    def cancel(self):
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def wait(self, seconds: float) -> bool:
        return self._ev.wait(seconds)


def execute_with_retry(fn: Callable[[], object], *, attempts: int, method: str, idempotency_key: str | None = None,
                       backoff: BackoffPolicy = BackoffPolicy(), deadline_s: float = 1.0,
                       cancel: CancelToken | None = None, classify: Callable[[Exception], str] = lambda e: "unavailable",
                       clock: Callable[[], float] = time.monotonic, rng: random.Random | None = None,
                       breaker: "CircuitBreaker | None" = None):
    """Run ``fn`` at most ``attempts`` times (the reconciled app-layer budget).

    No hidden loop: attempts, per-delay cap, elapsed cap, deadline and
    cancellation all bound the work.  Non-retry-safe calls get one attempt."""
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise MeshError("E_INVALID_ARGUMENT", "attempts must be a positive integer")
    cancel = cancel or CancelToken()
    start = clock()
    delays = backoff.delays(attempts, rng)
    last: Exception | None = None
    for i in range(attempts):
        if cancel.cancelled:
            raise MeshError("E_CANCELLED", "operation cancelled")
        if clock() - start >= deadline_s:
            raise MeshError("E_DEADLINE_EXCEEDED", "deadline elapsed", {"attempt": i})
        if breaker is not None and not breaker.allow():
            raise MeshError("E_CIRCUIT_OPEN", "circuit open")
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 - classified below
            last = exc
            if breaker is not None:
                breaker.record(False)
            outcome = classify(exc)
            if not retry_safe(method, idempotency_key=idempotency_key, outcome=outcome) or i == len(delays):
                break
            remaining = deadline_s - (clock() - start)
            if delays[i] >= remaining:
                raise MeshError("E_DEADLINE_EXCEEDED", "next backoff would exceed deadline", {"attempt": i + 1})
            if cancel.wait(delays[i]):
                raise MeshError("E_CANCELLED", "operation cancelled during backoff")
            continue
        if breaker is not None:
            breaker.record(True)
        return result
    raise MeshError("E_DEPENDENCY_UNAVAILABLE", "attempt budget exhausted",
                    {"last_error": type(last).__name__ if last else None})


# ------------------------------------------------------------ circuit breaker
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold: int = 5, reset_timeout_s: float = 30.0, half_open_max: int = 1,
                 clock: Callable[[], float] = time.monotonic):
        if failure_threshold < 1 or half_open_max < 1 or reset_timeout_s <= 0:
            raise ValueError("invalid breaker parameters")
        self.failure_threshold, self.reset_timeout_s, self.half_open_max = failure_threshold, reset_timeout_s, half_open_max
        self.clock = clock
        self._state, self._failures, self._opened_at, self._probes = self.CLOSED, 0, 0.0, 0
        self._lock = RLock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN and self.clock() - self._opened_at >= self.reset_timeout_s:
                self._state, self._probes = self.HALF_OPEN, 0
            return self._state

    def allow(self) -> bool:
        with self._lock:
            s = self.state
            if s == self.CLOSED:
                return True
            if s == self.HALF_OPEN and self._probes < self.half_open_max:
                self._probes += 1
                return True
            return False

    def record(self, success: bool) -> None:
        with self._lock:
            s = self.state
            if success:
                if s == self.HALF_OPEN or s == self.CLOSED:
                    self._state, self._failures = self.CLOSED, 0
                return
            self._failures += 1
            if s == self.HALF_OPEN or self._failures >= self.failure_threshold:
                self._state, self._opened_at, self._failures = self.OPEN, self.clock(), 0


# ----------------------------------------------------------- admission control
class AdmissionController:
    """Token bucket + in-flight ceiling + per-tenant fair share (C054, C017)."""

    def __init__(self, rate_per_s: float, burst: int, max_inflight: int, tenant_share: float = 0.5,
                 clock: Callable[[], float] = time.monotonic, max_tenants: int = 10_000):
        if rate_per_s <= 0 or burst < 1 or max_inflight < 1 or not 0 < tenant_share <= 1:
            raise ValueError("invalid admission parameters")
        self.rate, self.burst, self.max_inflight, self.share = rate_per_s, burst, max_inflight, tenant_share
        self.clock = clock
        self._tokens, self._last = float(burst), clock()
        self._inflight = 0
        self._per_tenant: dict[str, int] = {}
        self._max_tenants = max_tenants
        self.shed = 0
        self._lock = RLock()

    def reconfigure(self, rate_per_s: float, burst: int, max_inflight: int, tenant_share: float) -> None:
        """Change limits in place so in-flight acquisitions stay accounted (found by
        test_config_swap_during_traffic: replacing the controller lost releases)."""
        if rate_per_s <= 0 or burst < 1 or max_inflight < 1 or not 0 < tenant_share <= 1:
            raise ValueError("invalid admission parameters")
        with self._lock:
            self.rate, self.burst, self.max_inflight, self.share = rate_per_s, burst, max_inflight, tenant_share
            self._tokens = min(self._tokens, float(burst))

    def try_acquire(self, tenant: str) -> bool:
        with self._lock:
            now = self.clock()
            self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
            self._last = now
            tenant_cap = max(1, int(self.max_inflight * self.share))
            t_in = self._per_tenant.get(tenant, 0)
            if (self._tokens < 1 or self._inflight >= self.max_inflight or t_in >= tenant_cap
                    or (t_in == 0 and len(self._per_tenant) >= self._max_tenants)):
                self.shed += 1
                return False
            self._tokens -= 1
            self._inflight += 1
            self._per_tenant[tenant] = t_in + 1
            return True

    def release(self, tenant: str) -> None:
        with self._lock:
            n = self._per_tenant.get(tenant, 0)
            if n <= 0:
                raise RuntimeError("release without acquire")
            if n == 1:
                del self._per_tenant[tenant]
            else:
                self._per_tenant[tenant] = n - 1
            self._inflight -= 1

    def saturation(self) -> float:
        with self._lock:
            return self._inflight / self.max_inflight


# -------------------------------------------------------------- lifecycle FSM
LIFECYCLE_STATES = ("created", "bootstrapping", "ready", "degraded", "draining", "frozen", "stopped", "failed")
LEGAL_TRANSITIONS: dict[str, frozenset] = {
    "created": frozenset({"bootstrapping", "stopped"}),
    "bootstrapping": frozenset({"ready", "failed", "stopped"}),
    "ready": frozenset({"degraded", "draining", "frozen", "failed"}),
    "degraded": frozenset({"ready", "draining", "frozen", "failed"}),
    "frozen": frozenset({"ready", "degraded", "draining", "stopped"}),
    "draining": frozenset({"stopped", "failed"}),
    "failed": frozenset({"bootstrapping", "stopped"}),
    "stopped": frozenset(),
}
# which operation classes each state accepts
STATE_ACCEPTS = {
    "created": frozenset({"status"}),
    "bootstrapping": frozenset({"status", "config"}),
    "ready": frozenset({"status", "read", "mutate", "data", "config", "control"}),
    "degraded": frozenset({"status", "read", "data", "config", "control"}),  # no route mutation while degraded
    "frozen": frozenset({"status", "read", "data", "control", "config"}),     # data plane keeps last-known-good
    "draining": frozenset({"status", "read"}),
    "failed": frozenset({"status", "control"}),
    "stopped": frozenset(),
}


class Lifecycle:
    def __init__(self, on_transition: Callable[[str, str, str], None] | None = None):
        self._state = "created"
        self._lock = RLock()
        self._cb = on_transition
        self.history: list[tuple[str, str, str]] = []

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def to(self, new: str, reason: str) -> None:
        with self._lock:
            if new not in LEGAL_TRANSITIONS.get(self._state, ()):
                raise MeshError("E_NOT_READY", f"illegal lifecycle transition {self._state}->{new}")
            old, self._state = self._state, new
            self.history.append((old, new, reason))
            del self.history[:-256]
        if self._cb:
            self._cb(old, new, reason)

    def accepts(self, op_class: str) -> bool:
        return op_class in STATE_ACCEPTS[self.state]


# -------------------------------------------------------------------- fencing
class FencingGuard:
    """Monotonic fencing tokens reject stale controllers / split brain (C058)."""

    def __init__(self):
        self._highest: dict[str, int] = {}
        self._lock = RLock()

    def check_and_advance(self, scope: str, token: int) -> None:
        if isinstance(token, bool) or not isinstance(token, int) or token < 0:
            raise MeshError("E_INVALID_ARGUMENT", "fencing token must be a non-negative integer")
        with self._lock:
            hi = self._highest.get(scope, -1)
            if token < hi:
                raise MeshError("E_STALE_FENCE", "stale fencing token", {"scope": scope, "token": token, "highest": hi})
            self._highest[scope] = token

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._highest)

    def restore(self, data: dict[str, int]) -> None:
        with self._lock:
            for k, v in data.items():
                self._highest[k] = max(self._highest.get(k, -1), int(v))


# ---------------------------------------------------------------- quarantine
class ControlSwitches:
    """Global freeze, per-tenant/per-route quarantine (C059)."""

    def __init__(self, max_entries: int = 10_000):
        self._frozen = False
        self._quarantined: set[str] = set()
        self._max = max_entries
        self._lock = RLock()

    def freeze(self, on: bool) -> None:
        with self._lock:
            self._frozen = bool(on)

    @property
    def frozen(self) -> bool:
        with self._lock:
            return self._frozen

    def quarantine(self, key: str, on: bool) -> None:
        with self._lock:
            if on:
                if key not in self._quarantined and len(self._quarantined) >= self._max:
                    raise MeshError("E_CAPACITY", "quarantine table full")
                self._quarantined.add(key)
            else:
                self._quarantined.discard(key)

    def is_quarantined(self, *keys: Iterable[str]) -> bool:
        with self._lock:
            return any(k in self._quarantined for k in keys)

    def snapshot(self) -> dict:
        with self._lock:
            return {"frozen": self._frozen, "quarantined": sorted(self._quarantined)}
