"""Admission control, quotas, fairness, rate limits (M15).

Per-tenant and per-link token buckets (rate) plus per-tenant concurrency caps
(fair share): one noisy tenant exhausts only its own budget.  A global
in-flight ceiling sheds load when the node is saturated.  All rejections are
PK_PROVIDER_OVERLOADED with a retry hint.
"""
from __future__ import annotations

import threading
import time

from ..errors.mapping import ProviderFault


class TokenBucket:
    def __init__(self, rate_per_s: float, burst: int, *, clock=time.monotonic):
        self.rate, self.burst, self._clock = rate_per_s, burst, clock
        self.tokens, self._t = float(burst), clock()
        self._lock = threading.Lock()

    def take(self, n: float = 1.0) -> float:
        """Return 0 if admitted, else seconds until enough tokens."""
        with self._lock:
            now = self._clock()
            self.tokens = min(self.burst, self.tokens + (now - self._t) * self.rate)
            self._t = now
            if self.tokens >= n:
                self.tokens -= n
                return 0.0
            return (n - self.tokens) / self.rate if self.rate > 0 else float("inf")


class AdmissionController:
    def __init__(self, *, tenant_rate=200.0, tenant_burst=400, link_rate=100.0, link_burst=200,
                 tenant_concurrency=16, global_inflight=256, clock=time.monotonic, max_tracked=10_000):
        self.cfg = dict(tenant_rate=tenant_rate, tenant_burst=tenant_burst, link_rate=link_rate, link_burst=link_burst)
        self.tenant_concurrency, self.global_inflight = tenant_concurrency, global_inflight
        self._clock, self._max = clock, max_tracked
        self._tb: dict = {}
        self._lb: dict = {}
        self._inflight: dict = {}
        self._total = 0
        self._lock = threading.Lock()
        self.rejected = {"rate": 0, "concurrency": 0, "global": 0}

    def _bucket(self, table, key, rate, burst):
        b = table.get(key)
        if b is None:
            if len(table) >= self._max:
                raise ProviderFault("PK_PROVIDER_OVERLOADED", "admission table full", retry_after_ms=100)
            b = table[key] = TokenBucket(rate, burst, clock=self._clock)
        return b

    def admit(self, tenant: str, link_key: tuple):
        with self._lock:
            if self._total >= self.global_inflight:
                self.rejected["global"] += 1
                raise ProviderFault("PK_PROVIDER_OVERLOADED", "node saturated", retry_after_ms=50)
            if self._inflight.get(tenant, 0) >= self.tenant_concurrency:
                self.rejected["concurrency"] += 1
                raise ProviderFault("PK_PROVIDER_OVERLOADED", "tenant concurrency quota", retry_after_ms=20)
            tb = self._bucket(self._tb, tenant, self.cfg["tenant_rate"], self.cfg["tenant_burst"])
            lb = self._bucket(self._lb, link_key, self.cfg["link_rate"], self.cfg["link_burst"])
        wait = max(tb.take(), lb.take())
        if wait > 0:
            with self._lock:
                self.rejected["rate"] += 1
            raise ProviderFault("PK_PROVIDER_OVERLOADED", "rate limit", retry_after_ms=int(min(wait, 60) * 1000))
        with self._lock:
            self._inflight[tenant] = self._inflight.get(tenant, 0) + 1
            self._total += 1
        return _Ticket(self, tenant)

    def _release(self, tenant):
        with self._lock:
            self._inflight[tenant] -= 1
            self._total -= 1


class _Ticket:
    def __init__(self, ctl, tenant):
        self._ctl, self._tenant, self._done = ctl, tenant, False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if not self._done:
            self._done = True
            self._ctl._release(self._tenant)
        return False
