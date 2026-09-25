"""Circuit breaker per backend (M15): closed -> open after N consecutive
failures; open rejects fast for cooldown; half-open admits one probe."""
from __future__ import annotations

import threading
import time

from ..errors.mapping import ProviderFault


class CircuitBreaker:
    def __init__(self, failure_threshold=5, cooldown_s=5.0, *, clock=time.monotonic):
        self.threshold, self.cooldown, self._clock = failure_threshold, cooldown_s, clock
        self.state, self.failures, self._opened, self._probe = "closed", 0, 0.0, False
        self._lock = threading.Lock()

    def before(self) -> None:
        with self._lock:
            if self.state == "open":
                if self._clock() - self._opened < self.cooldown:
                    raise ProviderFault("PK_PROVIDER_CIRCUIT_OPEN", "backend circuit open",
                                        retry_after_ms=int((self.cooldown - (self._clock() - self._opened)) * 1000))
                self.state, self._probe = "half_open", False
            if self.state == "half_open":
                if self._probe:
                    raise ProviderFault("PK_PROVIDER_CIRCUIT_OPEN", "half-open probe in flight", retry_after_ms=100)
                self._probe = True

    def success(self) -> None:
        with self._lock:
            self.state, self.failures, self._probe = "closed", 0, False

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == "half_open" or self.failures >= self.threshold:
                self.state, self._opened, self._probe = "open", self._clock(), False
