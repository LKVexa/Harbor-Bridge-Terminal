"""Bounded retry, admission control and circuit breaking for PLN-05.

All three are deterministic under an injected clock and a seeded RNG so fault
and overload tests are reproducible.  Hard bounds: attempts, total deadline,
retry budget (retries per first attempt), queue capacity with a reserved slice
for control traffic, and half-open probe count.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import random
import zlib

from .errors import PlaneError

PRIORITY = {"control": 0, "limits": 1, "demand": 2, "telemetry": 3}


@dataclass
class RetryBudget:
    ratio: float
    requests: int = 0
    retries: int = 0

    def first_attempt(self) -> None:
        self.requests += 1

    def try_spend(self) -> bool:
        # Allow a small floor so a cold system can still retry once.
        if self.retries < max(1.0, self.ratio * self.requests):
            self.retries += 1
            return True
        return False


@dataclass
class RetryPolicy:
    max_attempts: int
    base_ms: float
    max_ms: float
    deadline_ms: float
    budget: RetryBudget
    rng: random.Random = field(default_factory=lambda: random.Random(0))

    def delays(self):
        """Decorrelated jitter (AWS architecture blog form), capped at ``max_ms``."""
        sleep = self.base_ms
        while True:
            sleep = min(self.max_ms, self.rng.uniform(self.base_ms, sleep * 3))
            yield sleep

    def run(self, op, *, idempotent: bool, clock, sleep, is_stale=lambda: False,
            cancelled=lambda: False):
        """Run ``op()``; retry only retryable :class:`PlaneError` on idempotent ops."""
        start = clock()
        self.budget.first_attempt()
        delays = self.delays()
        attempt = 0
        while True:
            if cancelled():
                raise PlaneError("E_CANCELLED", "operation cancelled")
            attempt += 1
            try:
                return op()
            except PlaneError as exc:
                if not exc.retryable or not idempotent:
                    raise
                if attempt >= self.max_attempts:
                    raise
                if is_stale():
                    raise PlaneError("E_STALE_INPUT", "input superseded during retry") from None
                d = next(delays)
                if (clock() - start) * 1000.0 + d > self.deadline_ms:
                    raise PlaneError("E_DEADLINE", "retry deadline exhausted") from None
                if not self.budget.try_spend():
                    raise PlaneError("E_RETRY_BUDGET", "retry budget exhausted") from None
                sleep(d / 1000.0)


class AdmissionController:
    """Bounded priority queue; ``control`` may use the reserved slice, others may not."""

    def __init__(self, capacity: int, control_reserve: int) -> None:
        if control_reserve >= capacity:
            raise ValueError("control_reserve must be below capacity")
        self.capacity = capacity
        self.reserve = control_reserve
        self._q: dict[int, deque] = {p: deque() for p in PRIORITY.values()}
        self.rejected: dict[str, int] = {k: 0 for k in PRIORITY}
        self.shed: dict[str, int] = {k: 0 for k in PRIORITY}

    def __len__(self) -> int:
        return sum(len(q) for q in self._q.values())

    def offer(self, klass: str, item) -> None:
        if klass not in PRIORITY:
            raise PlaneError("E_INTERNAL", "unknown priority class")
        depth = len(self)
        limit = self.capacity if klass == "control" else self.capacity - self.reserve
        if depth < limit:
            self._q[PRIORITY[klass]].append(item)
            return
        # Full: shed the lowest-priority queued item if the newcomer outranks it.
        for p in sorted(self._q, reverse=True):
            if p > PRIORITY[klass] and self._q[p]:
                self._q[p].popleft()
                self.shed[[k for k, v in PRIORITY.items() if v == p][0]] += 1
                self._q[PRIORITY[klass]].append(item)
                return
        self.rejected[klass] += 1
        raise PlaneError("E_OVERLOADED", "admission queue full", {"class": klass})

    def check(self, klass: str) -> None:
        """Admission test for synchronous callers (no enqueue)."""
        limit = self.capacity if klass == "control" else self.capacity - self.reserve
        if len(self) >= limit:
            self.rejected[klass] += 1
            raise PlaneError("E_OVERLOADED", "admission queue full", {"class": klass})

    def take(self):
        for p in sorted(self._q):
            if self._q[p]:
                return self._q[p].popleft()
        return None


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half-open"

    def __init__(self, name: str, failure_threshold: int, open_s: float, half_open_probes: int,
                 rng: random.Random | None = None) -> None:
        self.name = name
        self.threshold = failure_threshold
        self.open_s = open_s
        self.probes = half_open_probes
        self.rng = rng or random.Random(zlib.crc32(name.encode()))
        self.state = self.CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self._cooldown = open_s
        self._inflight_probes = 0
        self.transitions: list[tuple[float, str]] = []

    def _to(self, state: str, now: float) -> None:
        self.state = state
        self.transitions.append((now, state))

    def allow(self, now: float) -> None:
        if self.state == self.OPEN:
            if now - self.opened_at >= self._cooldown:
                self._to(self.HALF_OPEN, now)
                self._inflight_probes = 0
            else:
                raise PlaneError("E_CIRCUIT_OPEN", "dependency circuit open", {"dependency": self.name})
        if self.state == self.HALF_OPEN:
            if self._inflight_probes >= self.probes:
                raise PlaneError("E_CIRCUIT_OPEN", "half-open probe slots in use", {"dependency": self.name})
            self._inflight_probes += 1

    def record(self, ok: bool, now: float) -> None:
        if ok:
            self.failures = 0
            if self.state != self.CLOSED:
                self._to(self.CLOSED, now)
            return
        self.failures += 1
        if self.state == self.HALF_OPEN or self.failures >= self.threshold:
            self.opened_at = now
            # Jittered cooldown (0-20%) de-synchronises half-open probes across replicas.
            self._cooldown = self.open_s * (1.0 + 0.2 * self.rng.random())
            self._to(self.OPEN, now)

    def call(self, op, now: float):
        self.allow(now)
        try:
            result = op()
        except PlaneError as exc:
            self.record(not exc.retryable, now)  # non-retryable = caller error, not dependency failure
            raise
        self.record(True, now)
        return result
