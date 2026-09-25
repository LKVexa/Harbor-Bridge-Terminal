"""Dependency circuit breaker (MC-029)."""
from __future__ import annotations

import threading
import time

from ..errors import Inv24Error


class CircuitBreaker:
    def __init__(self, name: str, *, failure_threshold: int = 5, reset_s: float = 10.0,
                 half_open_max: int = 1, clock=time.monotonic) -> None:
        self.name, self.threshold, self.reset_s, self.half_open_max, self.clock = name, failure_threshold, reset_s, half_open_max, clock
        self.state, self.failures, self.opened_at, self._probes = "closed", 0, 0.0, 0
        self._lock = threading.Lock()

    def before(self) -> None:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_s:
                    self.state, self._probes = "half_open", 0
                else:
                    raise Inv24Error("CIRCUIT_OPEN", f"{self.name} breaker open")
            if self.state == "half_open":
                if self._probes >= self.half_open_max:
                    raise Inv24Error("CIRCUIT_OPEN", f"{self.name} half-open probe in flight")
                self._probes += 1

    def success(self) -> None:
        with self._lock:
            self.state, self.failures = "closed", 0

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == "half_open" or self.failures >= self.threshold:
                self.state, self.opened_at = "open", self.clock()

    def call(self, fn):
        self.before()
        try:
            out = fn()
        except Exception:
            self.failure()
            raise
        self.success()
        return out
