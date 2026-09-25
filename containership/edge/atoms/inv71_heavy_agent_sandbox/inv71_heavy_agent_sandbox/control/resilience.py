"""Resilience primitives (C017, C025, C028, C048, C053, C054, C056, C067).

All primitives take an injected clock/sleep/random so behavior is deterministic
under test.  Security-relevant rules:

* denials and integrity failures are never retried (RetryClass.NEVER);
* an open circuit never bypasses a check - it fails the call;
* admission keeps a reserved slice for teardown/quarantine/operator actions so
  overload cannot block containment;
* a security-critical dependency outage fails new trust decisions closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random as _random
import threading
from typing import Callable, Mapping, TypeVar

from .errors import ControlError, RetryClass

T = TypeVar("T")


# ---------------------------------------------------------------- deadlines
@dataclass(frozen=True)
class Deadline:
    at: float
    clock: Callable[[], float]

    @classmethod
    def after(cls, seconds: float, clock: Callable[[], float]) -> "Deadline":
        return cls(clock() + seconds, clock)

    def remaining(self) -> float:
        return self.at - self.clock()

    def check(self) -> None:
        if self.remaining() <= 0:
            raise ControlError("DEPENDENCY.DEADLINE_EXCEEDED")


# Per-operation deadlines and retry classification (C025-IMP-01, C053-IMP-01).
OPERATIONS: Mapping[str, tuple[float, RetryClass, bool]] = {
    # op: (deadline seconds, retry class, cancellable)
    "session.create": (15.0, RetryClass.IDEMPOTENT, True),
    "snapshot.restore": (5.0, RetryClass.WITH_COMPENSATION, True),
    "policy.fetch": (2.0, RetryClass.IDEMPOTENT, True),
    "session.exec": (300.0, RetryClass.NEVER, True),
    "session.stop": (30.0, RetryClass.IDEMPOTENT, False),
    "session.teardown": (45.0, RetryClass.IDEMPOTENT, False),
    "audit.deliver": (5.0, RetryClass.IDEMPOTENT, False),
    "artifact.fetch": (60.0, RetryClass.IDEMPOTENT, True),
    "egress.decide": (0.5, RetryClass.NEVER, False),
}


# ---------------------------------------------------------------- retry
@dataclass(frozen=True)
class RetryPolicy:
    base_s: float = 0.05
    cap_s: float = 2.0
    max_attempts: int = 5
    max_elapsed_s: float = 10.0

    def backoff(self, attempt: int, rnd: Callable[[], float]) -> float:
        """Full jitter: uniform(0, min(cap, base*2^attempt))."""
        return rnd() * min(self.cap_s, self.base_s * (2 ** attempt))


def call_with_retry(fn: Callable[[], T], *, policy: RetryPolicy, clock: Callable[[], float],
                    sleep: Callable[[float], None], rnd: Callable[[], float] = _random.random,
                    deadline: Deadline | None = None) -> T:
    start = clock()
    attempt = 0
    while True:
        try:
            return fn()
        except ControlError as err:
            if err.code.retry is RetryClass.NEVER or err.code.retry is RetryClass.WITH_COMPENSATION:
                raise
            attempt += 1
            if attempt >= policy.max_attempts:
                raise
            delay = policy.backoff(attempt, rnd)
            if clock() - start + delay > policy.max_elapsed_s:
                raise
            if deadline is not None and deadline.remaining() <= delay:
                raise ControlError("DEPENDENCY.DEADLINE_EXCEEDED", "deadline propagated") from err
            sleep(delay)


# ---------------------------------------------------------------- circuit breaker
class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, name: str, *, clock: Callable[[], float], failure_threshold: int = 5,
                 reset_after_s: float = 10.0, half_open_max: int = 1) -> None:
        self.name, self._clock = name, clock
        self.threshold, self.reset_after, self.half_open_max = failure_threshold, reset_after_s, half_open_max
        self.state = BreakerState.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._probes = 0
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state is BreakerState.OPEN:
                if self._clock() - self._opened_at >= self.reset_after:
                    self.state, self._probes = BreakerState.HALF_OPEN, 0
                else:
                    raise ControlError("DEPENDENCY.CIRCUIT_OPEN", self.name)
            if self.state is BreakerState.HALF_OPEN:
                if self._probes >= self.half_open_max:
                    raise ControlError("DEPENDENCY.CIRCUIT_OPEN", self.name)
                self._probes += 1
        try:
            result = fn()
        except ControlError as err:
            if err.code.namespace in ("DEPENDENCY",):
                self._record_failure()
            raise
        except Exception:
            self._record_failure()
            raise
        with self._lock:
            self.state, self._failures = BreakerState.CLOSED, 0
        return result

    def _record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self.state is BreakerState.HALF_OPEN or self._failures >= self.threshold:
                self.state, self._opened_at = BreakerState.OPEN, self._clock()


# ---------------------------------------------------------------- admission
@dataclass
class Shape:
    vcpu: int
    mem_mib: int

    def __post_init__(self) -> None:
        if self.vcpu <= 0 or self.mem_mib <= 0:
            raise ValueError("shape must be positive")


@dataclass
class TenantQuota:
    max_sessions: int
    max_vcpu: int
    max_mem_mib: int
    weight: int = 1


@dataclass
class NodeCapacity:
    vcpu: int
    mem_mib: int
    max_sessions: int
    reserve_fraction: float = 0.10  # held back for teardown/quarantine/operator (C054-IMP-02)


class AdmissionController:
    """Tenant-aware admission with weighted fair share and a reserved slice."""

    def __init__(self, node: NodeCapacity, quotas: Mapping[str, TenantQuota]) -> None:
        self.node, self.quotas = node, dict(quotas)
        self._used: dict[str, list[int]] = {}  # tenant -> [sessions, vcpu, mem]
        self._lock = threading.Lock()
        self.rejections: dict[str, int] = {}
        self.high_water = [0, 0, 0]

    def _tot(self) -> list[int]:
        t = [0, 0, 0]
        for u in self._used.values():
            for i in range(3):
                t[i] += u[i]
        return t

    def _reject(self, reason: str, code: str) -> ControlError:
        self.rejections[reason] = self.rejections.get(reason, 0) + 1
        return ControlError(code, reason)

    def admit(self, tenant: str, shape: Shape, *, priority: str = "normal") -> None:
        with self._lock:
            q = self.quotas.get(tenant)
            if q is None:
                raise self._reject("unknown_tenant", "AUTHZ.DENIED")
            u = self._used.setdefault(tenant, [0, 0, 0])
            if u[0] + 1 > q.max_sessions or u[1] + shape.vcpu > q.max_vcpu or u[2] + shape.mem_mib > q.max_mem_mib:
                raise self._reject("tenant_quota", "CAPACITY.TENANT_QUOTA")
            tot = self._tot()
            usable = 1.0 if priority == "management" else (1.0 - self.node.reserve_fraction)
            if (tot[0] + 1 > self.node.max_sessions * usable or tot[1] + shape.vcpu > self.node.vcpu * usable
                    or tot[2] + shape.mem_mib > self.node.mem_mib * usable):
                raise self._reject("node_saturated", "CAPACITY.ADMISSION_REJECTED")
            # Weighted fair share under contention: when the node is >= 75% used,
            # a tenant above its weighted share is shed first.
            if tot[1] + shape.vcpu > 0.75 * self.node.vcpu and priority != "management":
                wsum = sum(self.quotas[t].weight for t in self._used if self._used[t][0] > 0 or t == tenant)
                share = self.node.vcpu * usable * q.weight / max(wsum, 1)
                if u[1] + shape.vcpu > share:
                    raise self._reject("fair_share", "CAPACITY.ADMISSION_REJECTED")
            u[0] += 1; u[1] += shape.vcpu; u[2] += shape.mem_mib
            tot = self._tot()
            self.high_water = [max(a, b) for a, b in zip(self.high_water, tot)]

    def release(self, tenant: str, shape: Shape) -> None:
        with self._lock:
            u = self._used.get(tenant)
            if u is None or u[0] <= 0 or u[1] < shape.vcpu or u[2] < shape.mem_mib:
                raise ValueError("release without matching admission (negative accounting)")
            u[0] -= 1; u[1] -= shape.vcpu; u[2] -= shape.mem_mib

    def usage(self, tenant: str) -> tuple[int, int, int]:
        with self._lock:
            return tuple(self._used.get(tenant, [0, 0, 0]))  # type: ignore[return-value]


# ---------------------------------------------------------------- idempotency
class IdempotencyStore:
    """Dedupe mutating calls; replay returns the original response verbatim."""

    def __init__(self, *, clock: Callable[[], float], window_s: float = 3600.0, capacity: int = 100_000) -> None:
        self._clock, self.window, self.cap = clock, window_s, capacity
        self._d: dict[str, tuple[str, dict, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, request_digest: str) -> dict | None:
        with self._lock:
            hit = self._d.get(key)
            if not hit or hit[2] < self._clock():
                return None
            if hit[0] != request_digest:
                raise ControlError("VALIDATION.MALFORMED_REQUEST", "idempotency key reused with different request")
            return hit[1]

    def sweep(self) -> int:
        """Drop expired entries (v4.3.0: previously removed only at capacity, so
        expired keys accumulated up to 100k - found by tools/bench.py)."""
        with self._lock:
            now = self._clock()
            dead = [k for k, v in self._d.items() if v[2] < now]
            for k in dead:
                del self._d[k]
            return len(dead)

    def __len__(self) -> int:
        return len(self._d)

    def put(self, key: str, request_digest: str, response: dict) -> None:
        self._puts = getattr(self, "_puts", 0) + 1
        if self._puts % 256 == 0:
            self.sweep()
        with self._lock:
            if len(self._d) >= self.cap:
                now = self._clock()
                for k in [k for k, v in self._d.items() if v[2] < now] or [next(iter(self._d))]:
                    del self._d[k]
            self._d[key] = (request_digest, response, self._clock() + self.window)


# ---------------------------------------------------------------- dependencies
class Criticality(str, Enum):
    SECURITY = "security"      # identity, attestation, policy, keys, trusted time, artifact verify, audit
    NONCRITICAL = "noncritical"  # telemetry export, dashboards, secondary registry


DEPENDENCIES: Mapping[str, Criticality] = {
    "identity": Criticality.SECURITY, "attestation": Criticality.SECURITY, "policy": Criticality.SECURITY,
    "keys": Criticality.SECURITY, "time": Criticality.SECURITY, "artifact_verify": Criticality.SECURITY,
    "audit_sink": Criticality.SECURITY, "dns_resolver": Criticality.SECURITY,
    "telemetry": Criticality.NONCRITICAL, "dashboard": Criticality.NONCRITICAL,
    "secondary_registry": Criticality.NONCRITICAL, "metadata": Criticality.NONCRITICAL,
}
# Bounded cache validity when a security dependency is down (C048-IMP-02).
STALE_TRUST_GRACE_S: Mapping[str, float] = {"identity": 300.0, "policy": 300.0, "keys": 600.0,
                                              "attestation": 0.0, "time": 0.0, "artifact_verify": 0.0,
                                              "audit_sink": 120.0, "dns_resolver": 0.0}


@dataclass
class DependencyHealth:
    clock: Callable[[], float]
    down_since: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str, up: bool) -> None:
        if name not in DEPENDENCIES:
            raise KeyError(name)
        if up:
            self.down_since.pop(name, None)
        else:
            self.down_since.setdefault(name, self.clock())

    def degraded(self) -> list[str]:
        return sorted(n for n in self.down_since if DEPENDENCIES[n] is Criticality.NONCRITICAL)

    def gate_new_trust_decision(self) -> None:
        """Fail closed for new sessions/artifacts/policies once grace is exhausted."""
        now = self.clock()
        for n, since in self.down_since.items():
            if DEPENDENCIES[n] is Criticality.SECURITY and now - since >= STALE_TRUST_GRACE_S.get(n, 0.0):
                raise ControlError("DEPENDENCY.TRUST_UNAVAILABLE", n)

    def existing_sessions_may_continue(self) -> bool:
        """Existing sessions keep running while cached trust is within grace; egress
        decisions needing fresh DNS still fail closed via the resolver."""
        now = self.clock()
        return all(not (DEPENDENCIES[n] is Criticality.SECURITY and now - s >= max(STALE_TRUST_GRACE_S.get(n, 0.0), 0.0)
                        and n in ("identity", "policy", "keys"))
                   for n, s in self.down_since.items())

