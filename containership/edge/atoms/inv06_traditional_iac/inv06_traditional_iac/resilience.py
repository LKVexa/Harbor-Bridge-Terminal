"""Resilience controls (MC-021, MC-026 – MC-031 package-local references).

* ``Deadline`` / ``CancelToken`` / ``retry_call`` — deadlines, cooperative
  cancellation, bounded retry with exponential backoff + full jitter and a
  retry budget; only errors classified retryable are retried.
* ``IdempotencyStore`` — idempotency keys so a replayed apply returns the
  original outcome instead of executing twice.
* ``AdmissionController`` (bounded concurrency + bounded queue, load shedding)
  and ``CircuitBreaker`` (closed/open/half-open).
* ``DegradedMode`` — explicit read-only degradation when non-critical
  dependencies fail; mutation is refused while critical ones are down.
* ``FreezeController`` — quarantine/freeze/emergency-disable with
  authorised, audited re-enable.
* ``Watchdog`` — liveness/readiness/stall detection for in-flight operations.
* ``OfflineQueue`` — edge/disconnected plan queue with bounded staleness and
  serial-checked reconciliation on reconnect.
* ``FailoverController`` — chooses a failover site only if it satisfies the
  residency set and holds a state revision at least as new as the primary's
  last committed serial.
"""
from __future__ import annotations

import random
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .state import IacError, StalePlan


class DeadlineExceeded(IacError):
    code = "PK_IAC_DEADLINE_EXCEEDED"


class Cancelled(IacError):
    code = "PK_IAC_CANCELLED"


class Overloaded(IacError):
    code = "PK_IAC_OVERLOADED"


class CircuitOpen(IacError):
    code = "PK_IAC_CIRCUIT_OPEN"


class Frozen(IacError):
    code = "PK_IAC_FROZEN"


class Degraded(IacError):
    code = "PK_IAC_DEGRADED"


class ResidencyViolation(IacError):
    code = "PK_IAC_RESIDENCY_VIOLATION"


class RetryableError(IacError):
    """Raise (or subclass) for transient failures that are safe to retry."""

    code = "PK_IAC_RETRYABLE"


# ---------------------------------------------------------------- deadlines
class CancelToken:
    def __init__(self) -> None:
        self._ev = threading.Event()
        self.reason = ""

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def check(self) -> None:
        if self.cancelled:
            raise Cancelled("operation cancelled", details={"reason": self.reason})


class Deadline:
    def __init__(self, seconds: float, *, clock: Callable[[], float] = time.monotonic) -> None:
        if seconds <= 0:
            raise DeadlineExceeded("deadline must be positive")
        self.clock = clock
        self.at = clock() + seconds

    def remaining(self) -> float:
        return max(0.0, self.at - self.clock())

    def check(self) -> None:
        if self.remaining() <= 0:
            raise DeadlineExceeded("operation deadline exceeded")


def retry_call(
    fn: Callable[[], Any],
    *,
    attempts: int = 4,
    base_delay: float = 0.05,
    max_delay: float = 2.0,
    deadline: Deadline | None = None,
    cancel: CancelToken | None = None,
    retryable: tuple[type[BaseException], ...] = (RetryableError, TimeoutError, ConnectionError),
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> Any:
    rng = rng or random.Random()
    if attempts < 1 or attempts > 10:
        raise ValueError("attempts must be in 1..10")
    last: BaseException | None = None
    for i in range(attempts):
        if cancel:
            cancel.check()
        if deadline:
            deadline.check()
        try:
            return fn()
        except retryable as exc:
            last = exc
            if i == attempts - 1:
                break
            delay = rng.uniform(0, min(max_delay, base_delay * (2 ** i)))
            if deadline and delay >= deadline.remaining():
                raise DeadlineExceeded("retry budget exceeds deadline", details={"attempt": i + 1}) from exc
            sleep(delay)
    assert last is not None
    raise last


class IdempotencyStore:
    """Bounded LRU of idempotency-key → (request digest, result)."""

    def __init__(self, capacity: int = 10_000) -> None:
        self.capacity = capacity
        self._d: OrderedDict[str, tuple[str, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self._inflight: dict[str, threading.Event] = {}

    def run(self, key: str, request_digest: str, fn: Callable[[], Any]) -> Any:
        if not key or len(key) > 200:
            raise IacError("invalid idempotency key")
        while True:
            with self._lock:
                if key in self._d:
                    digest, result = self._d[key]
                    if digest != request_digest:
                        raise IacError("idempotency key reused for a different request", details={"key": key})
                    self._d.move_to_end(key)
                    return result
                ev = self._inflight.get(key)
                if ev is None:
                    self._inflight[key] = threading.Event()
                    break
            ev.wait()
        try:
            result = fn()
            with self._lock:
                self._d[key] = (request_digest, result)
                if len(self._d) > self.capacity:
                    self._d.popitem(last=False)
            return result
        finally:
            with self._lock:
                self._inflight.pop(key).set()


# -------------------------------------------------------- admission/breaker
class AdmissionController:
    def __init__(self, max_concurrent: int = 4, max_queue: int = 16, queue_timeout: float = 5.0) -> None:
        self._sem = threading.BoundedSemaphore(max_concurrent)
        self._waiting = 0
        self._lock = threading.Lock()
        self.max_queue, self.queue_timeout = max_queue, queue_timeout
        self.shed = 0

    def __enter__(self) -> "AdmissionController":
        if self._sem.acquire(blocking=False):
            return self
        with self._lock:
            if self._waiting >= self.max_queue:
                self.shed += 1
                raise Overloaded("admission queue full; request shed", details={"queue": self._waiting})
            self._waiting += 1
        try:
            if not self._sem.acquire(timeout=self.queue_timeout):
                with self._lock:
                    self.shed += 1
                raise Overloaded("admission wait timed out")
        finally:
            with self._lock:
                self._waiting -= 1
        return self

    def __exit__(self, *exc: Any) -> None:
        self._sem.release()

    @property
    def queue_depth(self) -> int:
        return self._waiting


class CircuitBreaker:
    def __init__(self, name: str, *, failure_threshold: int = 5, reset_after: float = 30.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.name, self.failure_threshold, self.reset_after, self.clock = name, failure_threshold, reset_after, clock
        self.state = "closed"
        self.failures = 0
        self.opened_at = 0.0
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], Any]) -> Any:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_after:
                    self.state = "half-open"
                else:
                    raise CircuitOpen("dependency circuit open", details={"dependency": self.name})
        try:
            result = fn()
        except Exception:
            with self._lock:
                self.failures += 1
                if self.state == "half-open" or self.failures >= self.failure_threshold:
                    self.state, self.opened_at = "open", self.clock()
            raise
        with self._lock:
            self.state, self.failures = "closed", 0
        return result


# ---------------------------------------------------------- degraded mode
class DegradedMode:
    """Tracks dependency health; ``require_mutation()`` fails when a critical one is down."""

    def __init__(self, critical: Iterable[str], noncritical: Iterable[str]) -> None:
        self.critical, self.noncritical = set(critical), set(noncritical)
        self.down: set[str] = set()

    def mark(self, dependency: str, healthy: bool) -> None:
        if dependency not in self.critical | self.noncritical:
            raise Degraded("unknown dependency", details={"dependency": dependency})
        (self.down.discard if healthy else self.down.add)(dependency)

    @property
    def mode(self) -> str:
        if self.down & self.critical:
            return "read-only"
        if self.down:
            return "degraded"
        return "normal"

    def require_mutation(self) -> None:
        if self.mode == "read-only":
            raise Degraded("critical dependency down; mutation refused", details={"down": sorted(self.down & self.critical)})


# ------------------------------------------------------------------ freeze
class FreezeController:
    def __init__(self, audit: Callable[[str, str, Mapping[str, Any]], Any] | None = None) -> None:
        self._frozen: dict[str, dict[str, Any]] = {}  # scope -> record ("*" = global)
        self._audit = audit or (lambda *a: None)
        self._lock = threading.Lock()

    def freeze(self, scope: str, *, actor: str, reason: str) -> None:
        if not actor or not reason:
            raise Frozen("freeze requires actor and reason")
        with self._lock:
            self._frozen[scope] = {"actor": actor, "reason": reason, "at": time.time()}
        self._audit("emergency.freeze", actor, {"scope": scope, "reason": reason})

    def unfreeze(self, scope: str, *, actor: str, reason: str, second_approver: str) -> None:
        if not second_approver or second_approver == actor:
            raise Frozen("unfreeze requires a distinct second approver")
        with self._lock:
            self._frozen.pop(scope, None)
        self._audit("emergency.unfreeze", actor, {"scope": scope, "reason": reason, "second_approver": second_approver})

    def check(self, scope: str) -> None:
        with self._lock:
            hit = self._frozen.get("*") or self._frozen.get(scope)
        if hit:
            raise Frozen("scope is frozen; mutation refused (reads remain available)", details={"scope": scope, **hit})

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._frozen)


# ---------------------------------------------------------------- watchdog
class Watchdog:
    def __init__(self, stall_after: float = 300.0, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.stall_after, self.clock = stall_after, clock
        self._ops: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()
        self.started = clock()

    def begin(self, op_id: str) -> None:
        with self._lock:
            self._ops[op_id] = {"start": self.clock(), "progress": self.clock()}

    def progress(self, op_id: str) -> None:
        with self._lock:
            if op_id in self._ops:
                self._ops[op_id]["progress"] = self.clock()

    def end(self, op_id: str) -> None:
        with self._lock:
            self._ops.pop(op_id, None)

    def stalled(self) -> list[str]:
        now = self.clock()
        with self._lock:
            return sorted(k for k, v in self._ops.items() if now - v["progress"] > self.stall_after)

    def status(self) -> dict[str, Any]:
        st = self.stalled()
        with self._lock:
            inflight = len(self._ops)
        return {"live": True, "inflight": inflight, "stalled": st, "healthy": not st}


# ------------------------------------------------------------ edge / offline
@dataclass
class QueuedPlan:
    plan: dict[str, Any]
    queued_at: float


class OfflineQueue:
    """Queue plans while disconnected; reconcile against authoritative state on reconnect."""

    def __init__(self, max_items: int = 100, max_staleness: float = 3600.0, *, clock: Callable[[], float] = time.time) -> None:
        self.max_items, self.max_staleness, self.clock = max_items, max_staleness, clock
        self.items: list[QueuedPlan] = []

    def enqueue(self, plan: Mapping[str, Any]) -> None:
        if len(self.items) >= self.max_items:
            raise Overloaded("offline queue full")
        self.items.append(QueuedPlan(dict(plan), self.clock()))

    def reconcile(self, state: Any) -> dict[str, list[Any]]:
        """Apply in order; stale/expired/conflicting plans are rejected, never forced."""
        out: dict[str, list[Any]] = {"applied": [], "expired": [], "conflicts": []}
        for q in self.items:
            if self.clock() - q.queued_at > self.max_staleness:
                out["expired"].append(q.plan["integrity"]["digest"])
                continue
            try:
                out["applied"].append(state.apply(q.plan))
            except StalePlan as exc:
                out["conflicts"].append(exc.as_dict())
        self.items.clear()
        return out


# ---------------------------------------------------------------- failover
class FailoverController:
    def __init__(self, sites: Mapping[str, Mapping[str, Any]]) -> None:
        # sites: name -> {"region": str, "healthy": bool, "serial": int}
        self.sites = {k: dict(v) for k, v in sites.items()}

    def choose(self, *, primary: str, allowed_regions: set[str], committed_serial: int) -> str:
        cands = []
        for name, s in sorted(self.sites.items()):
            if name == primary or not s.get("healthy"):
                continue
            if s.get("region") not in allowed_regions:
                continue
            if s.get("serial", -1) < committed_serial:
                continue
            cands.append(name)
        if not cands:
            raise ResidencyViolation(
                "no failover site satisfies residency and consistency constraints",
                details={"allowed_regions": sorted(allowed_regions), "committed_serial": committed_serial},
            )
        return cands[0]
