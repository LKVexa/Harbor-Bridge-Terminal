"""Checklists 28, 29, 30: failure taxonomy, health/stall detection, retry
policy, admission control, load shedding and circuit breaking.

Everything here is deterministic under an injected clock/RNG so the
fault-injection tests (checklist 33) can drive it exactly.
"""
from __future__ import annotations

import enum
import random
import threading
import time
from dataclasses import dataclass, field

from .defense import MitigationMissing


class FailureClass(str, enum.Enum):
    """Stable failure taxonomy; every refusal code maps to exactly one class."""

    POLICY_REJECTION = "policy_rejection"      # the system worked; the answer is no
    DEGRADED_INPUT = "degraded_input"          # stale / unknown / unattested posture
    DEPENDENCY_FAILURE = "dependency_failure"  # collector, GAP-02, audit sink unavailable
    OVERLOAD = "overload"                      # admission control shed the request
    ATTACK_SUSPECTED = "attack_suspected"      # bad MAC, replay, authz probing
    CLIENT_ERROR = "client_error"              # malformed request / version mismatch
    SOFTWARE_DEFECT = "software_defect"        # unexpected exception - page someone


CODE_CLASS: dict[str, FailureClass] = {
    "required_mitigation_missing": FailureClass.POLICY_REJECTION,
    "unsafe_smt": FailureClass.POLICY_REJECTION,
    "cross_tenant_forbidden_by_policy": FailureClass.POLICY_REJECTION,
    "node_quarantined": FailureClass.POLICY_REJECTION,
    "placement_frozen": FailureClass.POLICY_REJECTION,
    "cross_tenant_disabled": FailureClass.POLICY_REJECTION,
    "posture_stale": FailureClass.DEGRADED_INPUT,
    "posture_absent": FailureClass.DEGRADED_INPUT,
    "posture_stale_epoch": FailureClass.DEGRADED_INPUT,
    "gap02_readback_contradiction": FailureClass.DEGRADED_INPUT,
    "dependency_unavailable": FailureClass.DEPENDENCY_FAILURE,
    "circuit_open": FailureClass.DEPENDENCY_FAILURE,
    "deadline_exceeded": FailureClass.DEPENDENCY_FAILURE,
    "overloaded": FailureClass.OVERLOAD,
    "rate_limited": FailureClass.OVERLOAD,
    "attestation_bad_mac": FailureClass.ATTACK_SUSPECTED,
    "attestation_replay": FailureClass.ATTACK_SUSPECTED,
    "attestation_node_mismatch": FailureClass.ATTACK_SUSPECTED,
    "attestation_unknown_key": FailureClass.ATTACK_SUSPECTED,
    "attestation_revoked_key": FailureClass.ATTACK_SUSPECTED,
    "attestation_payload_mismatch": FailureClass.ATTACK_SUSPECTED,
    "authz_denied": FailureClass.ATTACK_SUSPECTED,
    "authn_failed": FailureClass.ATTACK_SUSPECTED,
    "attestation_expired": FailureClass.DEGRADED_INPUT,
    "attestation_expired_key": FailureClass.DEGRADED_INPUT,
    "attestation_clock_skew": FailureClass.DEGRADED_INPUT,
    "attestation_malformed": FailureClass.CLIENT_ERROR,
    "attestation_oversize": FailureClass.CLIENT_ERROR,
    "attestation_schema": FailureClass.CLIENT_ERROR,
    "schema_version_unrepresentable": FailureClass.CLIENT_ERROR,
    "version_unsupported": FailureClass.CLIENT_ERROR,
    "bad_request": FailureClass.CLIENT_ERROR,
    "not_found": FailureClass.CLIENT_ERROR,
    "payload_too_large": FailureClass.CLIENT_ERROR,
    "idempotency_conflict": FailureClass.CLIENT_ERROR,
    "internal_error": FailureClass.SOFTWARE_DEFECT,
}


def classify_code(code: str) -> FailureClass:
    # unknown codes are treated as defects: they mean the taxonomy is incomplete
    return CODE_CLASS.get(code, FailureClass.SOFTWARE_DEFECT)


class Health(str, enum.Enum):
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"   # serving, but every cross-tenant answer is a refusal
    STALLED = "stalled"     # a dependency heartbeat is overdue
    FROZEN = "frozen"       # operator emergency control engaged


@dataclass
class HealthMonitor:
    """Heartbeat-based stall detector per named dependency."""

    stall_after_s: float = 30.0
    clock: callable = time.monotonic
    _beats: dict = field(default_factory=dict)
    _frozen: bool = False
    _ready: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def beat(self, dependency: str) -> None:
        with self._lock:
            self._beats[dependency] = self.clock()

    def mark_ready(self) -> None:
        with self._lock:
            self._ready = True

    def set_frozen(self, frozen: bool) -> None:
        with self._lock:
            self._frozen = frozen

    def stalled(self) -> list[str]:
        now = self.clock()
        with self._lock:
            return sorted(d for d, t in self._beats.items() if now - t > self.stall_after_s)

    def state(self, *, degraded_nodes: int = 0) -> Health:
        with self._lock:
            frozen, ready = self._frozen, self._ready
        if frozen:
            return Health.FROZEN
        if not ready:
            return Health.STARTING
        if self.stalled():
            return Health.STALLED
        if degraded_nodes:
            return Health.DEGRADED
        return Health.READY


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential backoff with full jitter and an overall deadline.

    Only DEPENDENCY_FAILURE / OVERLOAD are retryable.  Policy rejections and
    attack signals are never retried (retrying cannot change the answer and
    retrying an attack signal amplifies it).
    """

    max_attempts: int = 4
    base_s: float = 0.05
    cap_s: float = 1.0
    deadline_s: float = 3.0

    RETRYABLE = frozenset({FailureClass.DEPENDENCY_FAILURE, FailureClass.OVERLOAD})

    def delays(self, rng: random.Random) -> list[float]:
        return [rng.uniform(0, min(self.cap_s, self.base_s * (2 ** i))) for i in range(self.max_attempts - 1)]

    def run(self, fn, *, rng: random.Random | None = None, sleep=time.sleep, clock=time.monotonic):
        rng = rng or random.Random()
        start = clock()
        delays = self.delays(rng)
        attempt = 0
        while True:
            try:
                return fn()
            except MitigationMissing as exc:
                cls = classify_code(exc.code)
                if cls not in self.RETRYABLE or attempt >= len(delays):
                    raise
                d = delays[attempt]
                if clock() - start + d > self.deadline_s:
                    raise MitigationMissing("retry deadline exceeded", code="deadline_exceeded",
                                            details={"attempts": attempt + 1, "last": exc.code}) from exc
                sleep(d)
                attempt += 1


class TokenBucket:
    def __init__(self, rate_per_s: float, burst: int, clock=time.monotonic) -> None:
        self.rate, self.burst, self.clock = rate_per_s, burst, clock
        self._tokens, self._t = float(burst), clock()
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            now = self.clock()
            self._tokens = min(self.burst, self._tokens + (now - self._t) * self.rate)
            self._t = now
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False


class ConcurrencyLimiter:
    """Non-blocking in-flight bound; excess load is shed immediately."""

    def __init__(self, limit: int) -> None:
        self._sem = threading.BoundedSemaphore(limit)
        self.limit = limit

    def __enter__(self):
        if not self._sem.acquire(blocking=False):
            raise MitigationMissing("too many in-flight requests", code="overloaded",
                                    details={"limit": self.limit})
        return self

    def __exit__(self, *exc):
        self._sem.release()
        return False


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive failures; half-open
    after ``reset_s``; one trial call decides."""

    def __init__(self, threshold: int = 5, reset_s: float = 10.0, clock=time.monotonic) -> None:
        self.threshold, self.reset_s, self.clock = threshold, reset_s, clock
        self._fails = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._opened_at is None:
                return "closed"
            return "half_open" if self.clock() - self._opened_at >= self.reset_s else "open"

    def call(self, fn):
        if self.state == "open":
            raise MitigationMissing("dependency circuit open", code="circuit_open", details={})
        try:
            out = fn()
        except Exception:
            with self._lock:
                self._fails += 1
                if self._fails >= self.threshold or self._opened_at is not None:
                    self._opened_at = self.clock()
            raise
        with self._lock:
            self._fails = 0
            self._opened_at = None
        return out
