"""MC-21 request contract (deadline, cancellation, idempotency, backpressure),
MC-29 failure model + health/stall thresholds, MC-30 retry/load-shed/circuit breaker."""
from __future__ import annotations

import hashlib
import random
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import SchedulerError
from .security import canonical

# MC-29: every failure domain, the detection signal, and the scheduler's response.
FAILURE_MODEL: tuple[dict[str, str], ...] = (
    {"domain": "process", "failure": "scheduler crash", "detect": "supervisor exit", "response": "restart -> RECOVERING -> journal replay"},
    {"domain": "process", "failure": "decision stall", "detect": "inflight age > stall_ms", "response": "health=DEGRADED; shed new load"},
    {"domain": "node", "failure": "report stale", "detect": "report age > freshness bound", "response": "exclude node (STALE_REPORT)"},
    {"domain": "node", "failure": "node lost", "detect": "report missing / disconnected", "response": "exclude; leases expire; no reclamation (INV-33)"},
    {"domain": "node", "failure": "attestation invalid", "detect": "verifier refusal", "response": "exclude node (ATTESTATION_FAILED)"},
    {"domain": "site", "failure": "site partition", "detect": "all reports from site stale", "response": "site-affine workloads refused NO_CANDIDATE"},
    {"domain": "network", "failure": "caller timeout", "detect": "deadline passed", "response": "DEADLINE_EXCEEDED; reservation rolled back"},
    {"domain": "provider", "failure": "secret provider down", "detect": "SECRET_UNAVAILABLE", "response": "fail closed; breaker opens"},
    {"domain": "dependency", "failure": "attestation/discovery repeatedly failing", "detect": "breaker threshold", "response": "CIRCUIT_OPEN; no placements on unverifiable input"},
    {"domain": "control-plane", "failure": "lost ownership", "detect": "fencing token superseded", "response": "FENCED; stop writing"},
    {"domain": "state", "failure": "journal corrupt", "detect": "hash-chain verify", "response": "STATE_CORRUPT; refuse start; restore"},
    {"domain": "clock", "failure": "clock regression", "detect": "now < last decision time", "response": "refuse decision (INVALID_REQUEST)"},
)
HEALTH_THRESHOLDS = {"stall_ms": 1000, "degraded_error_ratio": 0.2, "unhealthy_error_ratio": 0.5, "min_samples": 20}


@dataclass
class RequestContext:
    request_id: str
    idempotency_key: str
    deadline: int                   # absolute tick
    trace_id: str = ""
    parent_span: str = ""
    cancelled: threading.Event = field(default_factory=threading.Event)

    def check(self, now: int) -> None:
        if self.cancelled.is_set():
            raise SchedulerError("CANCELLED", "request cancelled")
        if now > self.deadline:
            raise SchedulerError("DEADLINE_EXCEEDED", "deadline passed", details={"deadline": self.deadline})


class IdempotencyCache:
    """Same key + same body -> same result; same key + different body -> conflict."""

    def __init__(self, capacity: int = 10_000):
        self.capacity = capacity
        self._d: dict[str, tuple[str, Any]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def body_digest(body: Any) -> str:
        return hashlib.sha256(canonical(body)).hexdigest()

    def lookup(self, key: str, body: Any):
        with self._lock:
            hit = self._d.get(key)
        if hit is None:
            return None
        if hit[0] != self.body_digest(body):
            raise SchedulerError("IDEMPOTENCY_CONFLICT", "idempotency key reused with a different request")
        return hit[1]

    def store(self, key: str, body: Any, result: Any) -> None:
        with self._lock:
            if len(self._d) >= self.capacity:
                self._d.pop(next(iter(self._d)))
            self._d[key] = (self.body_digest(body), result)


class AdmissionController:
    """Bounded concurrency; beyond it, shed with OVERLOADED + retry_after_ms."""

    def __init__(self, max_inflight: int):
        self.max_inflight = max_inflight
        self.inflight = 0
        self.shed = 0
        self._lock = threading.Lock()

    def __enter__(self):
        with self._lock:
            if self.inflight >= self.max_inflight:
                self.shed += 1
                raise SchedulerError("OVERLOADED", "scheduler at capacity", retry_after_ms=100)
            self.inflight += 1
        return self

    def __exit__(self, *exc):
        with self._lock:
            self.inflight -= 1
        return False


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int, reset_after: int, clock: Callable[[], int]):
        self.name, self.threshold, self.reset_after, self.clock = name, failure_threshold, reset_after, clock
        self.state, self.failures, self.opened_at = "CLOSED", 0, 0
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], Any]) -> Any:
        with self._lock:
            if self.state == "OPEN":
                if self.clock() - self.opened_at >= self.reset_after:
                    self.state = "HALF_OPEN"
                else:
                    raise SchedulerError("CIRCUIT_OPEN", f"{self.name} breaker open",
                                         retry_after_ms=1000 * (self.reset_after - (self.clock() - self.opened_at)))
        try:
            out = fn()
        except SchedulerError as e:
            if e.spec.category in ("availability", "security") and e.code != "ATTESTATION_FAILED":
                self._fail()
            raise
        except Exception:
            self._fail(); raise
        with self._lock:
            self.state, self.failures = "CLOSED", 0
        return out

    def _fail(self):
        with self._lock:
            self.failures += 1
            if self.state == "HALF_OPEN" or self.failures >= self.threshold:
                self.state, self.opened_at = "OPEN", self.clock()


def backoff_schedule(max_attempts: int, base_ms: int, max_ms: int, seed: int = 0) -> list[int]:
    """Bounded exponential backoff with deterministic (seeded) full jitter."""
    rng = random.Random(seed)
    return [rng.randint(0, min(max_ms, base_ms * 2 ** i)) for i in range(max_attempts - 1)]


def retry(fn: Callable[[], Any], *, max_attempts: int, sleep: Callable[[int], None], base_ms: int = 50,
          max_ms: int = 2000, seed: int = 0) -> Any:
    delays = backoff_schedule(max_attempts, base_ms, max_ms, seed)
    for attempt in range(max_attempts):
        try:
            return fn()
        except SchedulerError as e:
            if not e.spec.retryable or attempt == max_attempts - 1:
                raise
            sleep(e.retry_after_ms if e.retry_after_ms is not None else delays[attempt])
