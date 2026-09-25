"""MC-17 / MC-20: per-principal token buckets, a global admission ceiling and a
bounded principal table (hostile principal churn cannot grow memory)."""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field

from .errors import fail


@dataclass
class Admission:
    rate: float = 5.0          # tokens/s per principal
    burst: float = 10.0
    global_rate: float = 500.0
    global_burst: float = 1000.0
    max_principals: int = 10_000
    _b: OrderedDict = field(default_factory=OrderedDict)
    _g: list = field(default_factory=lambda: [None, 0.0])
    _lock: threading.Lock = field(default_factory=threading.Lock)
    rejected: int = 0

    def admit(self, principal: str, now: float, cost: float = 1.0) -> None:
        with self._lock:
            if self._g[0] is None:
                self._g = [self.global_burst, now]
            g, gt = self._g
            g = min(self.global_burst, g + (now - gt) * self.global_rate)
            b = self._b.pop(principal, None) or [self.burst, now]
            tok = min(self.burst, b[0] + max(0.0, now - b[1]) * self.rate)
            if g < cost:
                self._g = [g, now]
                self._store(principal, tok, now)
                self.rejected += 1
                raise fail("E_OVERLOADED", "global admission ceiling reached", retry_after=cost / self.global_rate)
            if tok < cost:
                self._g = [g, now]
                self._store(principal, tok, now)
                self.rejected += 1
                raise fail("E_RATE_LIMITED", "per-principal rate exceeded", retry_after=(cost - tok) / self.rate)
            self._g = [g - cost, now]
            self._store(principal, tok - cost, now)

    def _store(self, principal, tok, now):
        """Every path (admit or reject) goes through here so the table stays bounded.
        An evicted principal restarts at ``burst`` -- bounded by max_principals."""
        self._b[principal] = [tok, now]
        while len(self._b) > self.max_principals:
            self._b.popitem(last=False)
