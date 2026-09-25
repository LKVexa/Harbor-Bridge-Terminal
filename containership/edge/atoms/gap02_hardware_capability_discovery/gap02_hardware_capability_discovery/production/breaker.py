"""GAP02-MC-37 — Load shedding / circuit breaker (per probe backend)."""
from __future__ import annotations

from dataclasses import dataclass
import threading


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 3
    cooldown: float = 60.0
    state: str = "closed"         # closed | open | half-open
    failures: int = 0
    opened_at: float = 0.0

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def allow(self, now: float) -> bool:
        with self._lock:
            if self.state == "open" and now - self.opened_at >= self.cooldown:
                self.state = "half-open"
            return self.state != "open"

    def record(self, ok: bool, now: float) -> None:
        with self._lock:
            if ok:
                self.state, self.failures = "closed", 0
                return
            self.failures += 1
            if self.state == "half-open" or self.failures >= self.failure_threshold:
                self.state, self.opened_at = "open", now


class LoadShedder:
    """Bounded admission for on-demand (forced) probe requests."""

    def __init__(self, max_inflight: int = 2):
        self._sem = threading.BoundedSemaphore(max_inflight)

    def try_acquire(self) -> bool:
        return self._sem.acquire(blocking=False)

    def release(self) -> None:
        self._sem.release()
