"""#13 timeouts/retry, #25 failure model + stall detection, #26 residency-safe failover, #28 fault injection."""
from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from .data_plane import _StructuredError

T = TypeVar("T")


class RetryExhausted(_StructuredError, RuntimeError):
    code = "PK_RETRY_EXHAUSTED"


class CircuitOpen(_StructuredError, RuntimeError):
    code = "PK_CIRCUIT_OPEN"
    retryable = True


class FailoverRefused(_StructuredError, PermissionError):
    code = "PK_FAILOVER_REFUSED"


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry: attempt ceiling, exponential backoff, full jitter, overall deadline."""

    max_attempts: int = 4
    base_delay: float = 0.05
    max_delay: float = 2.0
    multiplier: float = 2.0
    deadline_s: float = 30.0
    per_attempt_timeout_s: float = 10.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be in [1, 10]")
        if self.base_delay < 0 or self.max_delay < self.base_delay or self.multiplier < 1:
            raise ValueError("invalid backoff parameters")
        if self.deadline_s <= 0 or self.per_attempt_timeout_s <= 0:
            raise ValueError("timeouts must be positive")

    def backoff(self, attempt: int, rng: random.Random) -> float:
        cap = min(self.max_delay, self.base_delay * (self.multiplier ** attempt))
        return rng.uniform(0, cap)  # full jitter


def is_retryable(exc: BaseException) -> bool:
    """Retry only errors that declare themselves retryable. Unknown errors are terminal."""
    return bool(getattr(exc, "retryable", False))


def call_with_retry(fn: Callable[[float], T], policy: RetryPolicy, *, cancel: threading.Event | None = None,
                    rng: random.Random | None = None, sleep: Callable[[float], None] = time.sleep,
                    clock: Callable[[], float] = time.monotonic,
                    on_attempt: Callable[[int, BaseException | None], None] | None = None) -> T:
    """Invoke ``fn(attempt_deadline)`` under ``policy``.  Cancellation propagates immediately."""
    rng = rng or random.Random()  # noqa: S311 - jitter, not security
    overall = clock() + policy.deadline_s
    last: BaseException | None = None
    for attempt in range(policy.max_attempts):
        if cancel is not None and cancel.is_set():
            raise RetryExhausted("cancelled", attempts=attempt, retryable=False)
        now = clock()
        if now >= overall:
            break
        try:
            result = fn(min(overall, now + policy.per_attempt_timeout_s))
            if on_attempt:
                on_attempt(attempt, None)
            return result
        except Exception as exc:  # noqa: BLE001
            last = exc
            if on_attempt:
                on_attempt(attempt, exc)
            if not is_retryable(exc):
                raise
            if attempt + 1 < policy.max_attempts:
                delay = min(policy.backoff(attempt, rng), max(0.0, overall - clock()))
                if cancel is not None:
                    if cancel.wait(delay):
                        raise RetryExhausted("cancelled", attempts=attempt + 1, retryable=False) from exc
                else:
                    sleep(delay)
    raise RetryExhausted("retry budget exhausted", attempts=policy.max_attempts,
                         last=None if last is None else type(last).__name__) from last


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive failures; half-open after ``cooldown``."""

    def __init__(self, threshold: int = 5, cooldown: float = 10.0, clock: Callable[[], float] = time.monotonic):
        self._threshold = threshold
        self._cooldown = cooldown
        self._clock = clock
        self._fails = 0
        self._opened: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._opened is None:
                return "closed"
            return "half_open" if self._clock() - self._opened >= self._cooldown else "open"

    def before(self) -> None:
        if self.state == "open":
            raise CircuitOpen("circuit open")

    def success(self) -> None:
        with self._lock:
            self._fails, self._opened = 0, None

    def failure(self) -> None:
        with self._lock:
            self._fails += 1
            if self._fails >= self._threshold:
                self._opened = self._clock()


# --------------------------------------------------------------------------
# #25 failure model catalog and stall detection
# --------------------------------------------------------------------------

FAILURE_MODEL = {
    "process_crash": {"detect": "journal replay at start", "recover": "replay; expire stalled", "rto_s": 5},
    "vm_crash": {"detect": "vsock control health timeout", "recover": "refuse control verbs; bulk unaffected", "rto_s": 30},
    "node_loss": {"detect": "peer heartbeat > 3x interval", "recover": "residency-safe failover", "rto_s": 60},
    "site_loss": {"detect": "all peers in site unhealthy", "recover": "failover only to residency-legal sites", "rto_s": 300},
    "provider_outage": {"detect": "circuit breaker open", "recover": "alternate adapter per preference", "rto_s": 60},
    "control_plane_loss": {"detect": "policy age > max_policy_age", "recover": "serve last verified policy then refuse", "rto_s": 0},
    "network_partition": {"detect": "deadline exceeded + breaker", "recover": "fenced epoch; no dual ownership", "rto_s": 120},
    "stall": {"detect": "no progress for stall_timeout", "recover": "cancel + expire + release capacity", "rto_s": 0},
    "integrity_mismatch": {"detect": "manifest verification", "recover": "quarantine; never auto-retry", "rto_s": 0},
    "key_service_outage": {"detect": "KeyUnavailable", "recover": "fail closed until restored", "rto_s": 0},
}


class StallDetector:
    """Tracks per-transfer progress heartbeats and reports those idle beyond ``timeout``."""

    def __init__(self, timeout: float, clock: Callable[[], float] = time.monotonic, limit: int = 100_000):
        self._timeout = timeout
        self._clock = clock
        self._last: dict[str, float] = {}
        self._limit = limit
        self._lock = threading.Lock()

    def progress(self, transfer_id: str) -> None:
        with self._lock:
            if transfer_id not in self._last and len(self._last) >= self._limit:
                raise RetryExhausted("stall tracker full", retryable=True)
            self._last[transfer_id] = self._clock()

    def done(self, transfer_id: str) -> None:
        with self._lock:
            self._last.pop(transfer_id, None)

    def stalled(self) -> list[str]:
        now = self._clock()
        with self._lock:
            return [t for t, ts in self._last.items() if now - ts > self._timeout]


# --------------------------------------------------------------------------
# #26 residency-safe failover
# --------------------------------------------------------------------------


class FailoverController:
    """Choose an alternate destination that is never weaker than the original.

    A candidate must (1) be residency-legal for the classification, (2) be in
    the same or a stricter isolation class, (3) be healthy, and (4) not be
    quarantined.  If none qualifies the transfer fails; it is never moved to a
    weaker site.
    """

    ISOLATION_RANK = {"shared": 0, "dedicated": 1, "sovereign": 2}

    def __init__(self, residency: Callable[[], Mapping[str, frozenset[str]]],
                 site_isolation: Mapping[str, str], health: Callable[[str], bool],
                 quarantined: Callable[[], Iterable[str]] = lambda: ()):
        self._residency = residency
        self._iso = dict(site_isolation)
        self._health = health
        self._quarantined = quarantined

    def choose(self, *, classification: str, original: str, candidates: Iterable[str]) -> dict[str, object]:
        policy = self._residency()
        need = self.ISOLATION_RANK.get(self._iso.get(original, "shared"), 0)
        blocked = set(self._quarantined())
        rejected = []
        for site in candidates:
            if site == original:
                continue
            if classification not in policy.get(site, frozenset()):
                rejected.append((site, "residency"))
            elif self.ISOLATION_RANK.get(self._iso.get(site, "shared"), 0) < need:
                rejected.append((site, "weaker_isolation"))
            elif site in blocked:
                rejected.append((site, "quarantined"))
            elif not self._health(site):
                rejected.append((site, "unhealthy"))
            else:
                return {"destination": site, "rejected": rejected}
        raise FailoverRefused("no residency-safe failover destination", original=original, rejected=rejected)


# --------------------------------------------------------------------------
# #28 deterministic fault injection
# --------------------------------------------------------------------------


class FaultInjector:
    """Seeded, scriptable fault plan.  ``hit(point)`` raises the scheduled fault."""

    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)  # noqa: S311
        self._plan: dict[str, list[BaseException | None]] = {}
        self._rates: dict[str, tuple[float, Callable[[], BaseException]]] = {}
        self.log: list[tuple[str, str]] = []

    def script(self, point: str, *faults: BaseException | None) -> None:
        self._plan.setdefault(point, []).extend(faults)

    def rate(self, point: str, probability: float, factory: Callable[[], BaseException]) -> None:
        self._rates[point] = (probability, factory)

    def hit(self, point: str) -> None:
        queue = self._plan.get(point)
        fault: BaseException | None = None
        if queue:
            fault = queue.pop(0)
        elif point in self._rates and self._rng.random() < self._rates[point][0]:
            fault = self._rates[point][1]()
        if fault is not None:
            self.log.append((point, type(fault).__name__))
            raise fault
