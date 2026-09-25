"""Health, retry, backpressure and failure control (MC-09).

All time measurements use monotonic clocks (MC-09.003).  Components:

* :class:`HealthMonitor` - liveness / readiness / degradation as separate
  states with hysteresis and machine-readable reason codes (MC-09.001-.006).
* :class:`RetryPolicy` + :class:`RetryBudget` - classified, bounded, jittered,
  deadline-aware retries with a shared anti-storm budget (MC-09.007-.013).
* :class:`CircuitBreaker` - closed / open / half-open with bounded probes
  (MC-09.018).
* :class:`AdmissionController` - bounded queues with high/low water marks,
  per-tenant limits and priority-based shedding (MC-09.014-.017/.019).
* :class:`FailoverSelector` - residency/tenant-preserving alternate selection
  guarded by fencing tokens so two owners cannot be active (MC-09.021-.025).
"""
from __future__ import annotations

import collections
import enum
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Iterable, TypeVar

from .errors import ErrorCode, Inv36Error

T = TypeVar("T")


class OverloadError(Inv36Error, RuntimeError):
    code = ErrorCode.OVERLOADED


class HealthState(str, enum.Enum):
    READY = "ready"
    DEGRADED = "degraded"
    NOT_READY = "not_ready"


class DepKind(str, enum.Enum):
    REQUIRED = "required"   # identity, key, policy, integrity: failure => not ready, stop sensitive ops
    OPTIONAL = "optional"   # telemetry, config service: failure => degraded, keep serving


@dataclass
class HealthMonitor:
    stall_threshold_s: float = 20.0
    hysteresis: int = 3
    clock: Callable[[], float] = time.monotonic
    on_transition: Callable[[str, str, list[str]], None] | None = None
    deps: dict[str, tuple[DepKind, bool]] = field(default_factory=dict)
    started: float = field(default=0.0, init=False)
    last_progress: float = field(default=0.0, init=False)
    last_peer_exchange: float | None = field(default=None, init=False)
    errors: Deque[tuple[float, str]] = field(default_factory=lambda: collections.deque(maxlen=256), init=False)
    _state: HealthState = field(default=HealthState.NOT_READY, init=False)
    _pending: tuple[HealthState, int] | None = field(default=None, init=False)
    queue_saturation: float = field(default=0.0, init=False)
    alive: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        self.started = self.last_progress = self.clock()

    def set_dependency(self, name: str, kind: DepKind, healthy: bool) -> None:
        self.deps[name] = (kind, healthy)

    def progress(self, *, peer: bool = True) -> None:
        now = self.clock()
        self.last_progress = now
        if peer:
            self.last_peer_exchange = now

    def error(self, reason: str) -> None:
        self.errors.append((self.clock(), reason[:64]))

    def error_rate(self, window_s: float = 60.0) -> float:
        now = self.clock()
        return sum(1 for t, _ in self.errors if now - t <= window_s) / window_s

    def _target(self) -> tuple[HealthState, list[str]]:
        reasons: list[str] = []
        now = self.clock()
        for name, (kind, ok) in sorted(self.deps.items()):
            if not ok:
                reasons.append(f"{'required' if kind is DepKind.REQUIRED else 'optional'}_dependency_down:{name}")
        if any(r.startswith("required") for r in reasons):
            return HealthState.NOT_READY, reasons
        if now - self.last_progress > self.stall_threshold_s:
            reasons.append("stalled")
        if self.queue_saturation >= 0.9:
            reasons.append("queue_saturated")
        if self.error_rate() > 1.0:
            reasons.append("error_rate_high")
        return (HealthState.DEGRADED if reasons else HealthState.READY), reasons

    def evaluate(self) -> dict[str, Any]:
        target, reasons = self._target()
        if target is HealthState.NOT_READY and self._state is not HealthState.NOT_READY:
            self._transition(target, reasons)  # losing a required dependency is immediate
        elif target is not self._state:
            state, n = self._pending if self._pending and self._pending[0] is target else (target, 0)
            n += 1
            if n >= self.hysteresis:
                self._transition(target, reasons)
            else:
                self._pending = (state, n)
        else:
            self._pending = None
        return self.report(reasons)

    def _transition(self, new: HealthState, reasons: list[str]) -> None:
        old = self._state
        self._state = new
        self._pending = None
        if self.on_transition:
            self.on_transition(old.value, new.value, reasons)

    @property
    def state(self) -> HealthState:
        return self._state

    def report(self, reasons: list[str] | None = None) -> dict[str, Any]:
        now = self.clock()
        return {
            "schema": "inv36.health/1", "live": self.alive, "state": self._state.value,
            "ready": self._state is not HealthState.NOT_READY, "reasons": reasons or [],
            "dependencies": {k: {"kind": v[0].value, "healthy": v[1]} for k, v in sorted(self.deps.items())},
            "seconds_since_progress": round(now - self.last_progress, 3),
            "seconds_since_peer_exchange": None if self.last_peer_exchange is None
            else round(now - self.last_peer_exchange, 3),
            "queue_saturation": round(self.queue_saturation, 3),
        }


class Retryability(str, enum.Enum):
    NON_RETRYABLE = "non_retryable"
    IDEMPOTENT = "idempotent"
    DEDUP_TOKEN = "retry_with_dedup_token"  # noqa: S105 - enum label, not a credential


OPERATION_RETRY_CLASS = {
    "connect": Retryability.IDEMPOTENT, "handshake": Retryability.IDEMPOTENT,
    "HEARTBEAT": Retryability.IDEMPOTENT, "STATUS_QUERY": Retryability.IDEMPOTENT,
    "LEASE_RENEW": Retryability.DEDUP_TOKEN, "LEASE_GRANT": Retryability.DEDUP_TOKEN,
    "LEASE_REVOKE": Retryability.DEDUP_TOKEN, "PLACEMENT": Retryability.DEDUP_TOKEN,
    "DRAIN": Retryability.DEDUP_TOKEN, "ERROR_REPORT": Retryability.NON_RETRYABLE,
}

TIMEOUTS_MS = {"connect": 2000, "handshake": 5000, "read": 30000, "write": 10000, "drain": 15000,
               "dependency": 3000}


@dataclass
class RetryBudget:
    """Shared token bucket: retries cost tokens; successes refund (anti retry-storm, MC-09.013)."""

    ratio: float = 0.2
    min_tokens: float = 10.0
    max_tokens: float = 100.0
    tokens: float = 10.0
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def success(self) -> None:
        with self._lock:
            self.tokens = min(self.max_tokens, self.tokens + self.ratio)

    def try_spend(self) -> bool:
        with self._lock:
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


class RetryExhausted(Inv36Error, RuntimeError):
    code = ErrorCode.RETRY_EXHAUSTED


class DeadlineExceeded(Inv36Error, TimeoutError):
    code = ErrorCode.DEADLINE_EXCEEDED


@dataclass
class RetryPolicy:
    max_attempts: int = 5
    base_s: float = 0.05
    cap_s: float = 5.0
    jitter: str = "full"   # full | decorrelated
    budget: RetryBudget | None = None
    rng: random.Random = field(default_factory=random.Random)
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic

    def delays(self) -> Iterable[float]:
        prev = self.base_s
        for i in range(self.max_attempts - 1):
            if self.jitter == "decorrelated":
                prev = min(self.cap_s, self.rng.uniform(self.base_s, prev * 3))
                yield prev
            else:
                yield self.rng.uniform(0, min(self.cap_s, self.base_s * (2 ** i)))

    def run(self, fn: Callable[[], T], *, operation: str = "", deadline_s: float | None = None,
            cancelled: Callable[[], bool] = lambda: False) -> T:
        if OPERATION_RETRY_CLASS.get(operation) is Retryability.NON_RETRYABLE:
            return fn()
        end = None if deadline_s is None else self.clock() + deadline_s
        delays = iter(self.delays())
        attempt = 0
        while True:
            attempt += 1
            if cancelled():
                raise DeadlineExceeded("cancelled by caller")
            try:
                result = fn()
                if self.budget:
                    self.budget.success()
                return result
            except Inv36Error as exc:
                # Terminal authentication/authorization/protocol/integrity errors never retry (MC-09.012).
                if not exc.code.retryable:
                    raise
                delay = next(delays, None)
                if delay is None:
                    raise RetryExhausted(f"{operation or 'operation'} failed after {attempt} attempts",
                                         detail={"last": exc.code.name}) from exc
                if self.budget and not self.budget.try_spend():
                    raise RetryExhausted("shared retry budget exhausted", detail={"last": exc.code.name}) from exc
                hint = exc.retry_after_s or 0.0
                delay = max(delay, hint)
                if end is not None and self.clock() + delay > end:
                    raise DeadlineExceeded("retry would exceed deadline") from exc
                self.sleep(delay)


class BreakerState(str, enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpen(Inv36Error, RuntimeError):
    code = ErrorCode.CIRCUIT_OPEN


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    reset_s: float = 10.0
    half_open_probes: int = 1
    clock: Callable[[], float] = time.monotonic
    on_change: Callable[[str, str], None] | None = None
    state: BreakerState = field(default=BreakerState.CLOSED, init=False)
    failures: int = field(default=0, init=False)
    opened_at: float = field(default=0.0, init=False)
    probes: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _set(self, s: BreakerState) -> None:
        if s is not self.state:
            self.state = s
            if self.on_change:
                self.on_change(self.name, s.value)

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state is BreakerState.OPEN:
                if self.clock() - self.opened_at >= self.reset_s:
                    self._set(BreakerState.HALF_OPEN)
                    self.probes = 0
                else:
                    raise CircuitOpen(f"circuit {self.name} open",
                                      retry_after_s=self.reset_s - (self.clock() - self.opened_at))
            if self.state is BreakerState.HALF_OPEN:
                if self.probes >= self.half_open_probes:
                    raise CircuitOpen(f"circuit {self.name} probing")
                self.probes += 1
        try:
            result = fn()
        except Exception:
            with self._lock:
                self.failures += 1
                if self.state is BreakerState.HALF_OPEN or self.failures >= self.failure_threshold:
                    self.opened_at = self.clock()
                    self._set(BreakerState.OPEN)
            raise
        with self._lock:
            self.failures = 0
            self._set(BreakerState.CLOSED)
        return result


class Priority(enum.IntEnum):
    CRITICAL = 0   # LEASE_REVOKE, DRAIN, PLACEMENT - authoritative control
    NORMAL = 1     # LEASE_GRANT/RENEW, ERROR_REPORT
    OPTIONAL = 2   # STATUS_QUERY, HEARTBEAT


PRIORITY_OF = {"LEASE_REVOKE": Priority.CRITICAL, "DRAIN": Priority.CRITICAL, "PLACEMENT": Priority.CRITICAL,
               "LEASE_GRANT": Priority.NORMAL, "LEASE_RENEW": Priority.NORMAL, "ERROR_REPORT": Priority.NORMAL,
               "STATUS_QUERY": Priority.OPTIONAL, "HEARTBEAT": Priority.OPTIONAL}


@dataclass
class AdmissionController:
    """Bounded work admission with HWM/LWM hysteresis and per-tenant quotas.

    Admission happens *after* authentication and authorization, so overload
    handling can never bypass either (MC-09.020).
    """

    high_water: int = 256
    low_water: int = 64
    per_tenant: int = 64
    depth: int = field(default=0, init=False)
    shedding: bool = field(default=False, init=False)
    tenant_depth: dict[str, int] = field(default_factory=lambda: collections.defaultdict(int), init=False)
    shed_count: dict[str, int] = field(default_factory=lambda: collections.defaultdict(int), init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not 0 < self.low_water < self.high_water:
            raise ValueError("require 0 < low_water < high_water")

    @property
    def saturation(self) -> float:
        return self.depth / self.high_water

    def admit(self, tenant: str, priority: Priority) -> None:
        with self._lock:
            if self.depth >= self.high_water:
                self.shedding = True
            elif self.depth <= self.low_water:
                self.shedding = False
            hard_full = self.depth >= self.high_water
            reject = hard_full and priority is not Priority.CRITICAL
            reject = reject or (self.shedding and priority is Priority.OPTIONAL)
            reject = reject or self.depth >= self.high_water + 16  # absolute bound even for CRITICAL
            reject = reject or self.tenant_depth[tenant] >= self.per_tenant
            if reject:
                self.shed_count[priority.name] += 1
                raise OverloadError("admission refused", detail={"priority": priority.name, "depth": self.depth},
                                    retry_after_s=0.05 * (1 + priority))
            self.depth += 1
            self.tenant_depth[tenant] += 1

    def release(self, tenant: str) -> None:
        with self._lock:
            self.depth = max(0, self.depth - 1)
            self.tenant_depth[tenant] = max(0, self.tenant_depth[tenant] - 1)
            if self.tenant_depth[tenant] == 0:
                del self.tenant_depth[tenant]


@dataclass(frozen=True)
class Alternate:
    endpoint: str
    region: str
    tenants: frozenset[str]


@dataclass
class FailoverSelector:
    """Pick a failover target that preserves residency and tenant isolation.

    Ownership of a control role is held by a fencing token that increases on
    every failover; a stale owner presenting an old token is rejected, so two
    endpoints cannot be simultaneously authoritative (MC-09.025).
    """

    region: str
    alternates: list[Alternate]
    token: int = 0
    owner: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def select(self, tenant: str, exclude: Iterable[str] = ()) -> Alternate:
        ex = set(exclude)
        for a in self.alternates:
            if a.endpoint not in ex and a.region == self.region and tenant in a.tenants:
                return a
        raise OverloadError("no residency-preserving alternate available", code=ErrorCode.NOT_READY)

    def take_ownership(self, endpoint: str) -> int:
        with self._lock:
            self.token += 1
            self.owner = endpoint
            return self.token

    def validate(self, endpoint: str, token: int) -> None:
        with self._lock:
            if endpoint != self.owner or token != self.token:
                raise OverloadError("stale owner fenced", code=ErrorCode.NOT_READY,
                                    detail={"presented": token, "current": self.token})


DEGRADED_MODE = {
    "telemetry_exporter_down": "continue; buffer bounded, drop oldest, count drops",
    "config_service_down": "continue on last known-good snapshot; refuse new activations",
    "policy_service_down": "continue on cached policy until its expires_at; then deny all (fail closed)",
    "identity_or_attestation_down": "existing sessions continue until max age; new handshakes fail closed",
    "key_service_down": "no new identity signatures; existing sessions continue until max age",
    "audit_sink_down": "buffer non-critical events (bounded); security-critical actions fail closed",
    "reentry": "ready again after `hysteresis` consecutive healthy evaluations; reconnects use jittered backoff",
}
