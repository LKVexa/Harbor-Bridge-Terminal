"""Retry/backoff/jitter (16) and circuit breaking / admission control (17).
Breaker and token bucket adapted from the shop's GAP-09 v5.1.0 ``controls.py``.

``RetryPolicy.call``
  retries only errors whose ``retry`` class is ``retryable`` (trust, policy
  and input errors are never retried); exponential backoff with *full jitter*
  ``sleep = U(0, min(cap, base * 2**n))``; a hard ``deadline`` (absolute,
  monotonic) and a cooperative ``cancel`` event; a shared ``RetryBudget``
  (token bucket of retries per second) prevents retry storms.

``IdempotencyCache``
  remembers completed operation keys for ``ttl`` so a replayed request
  returns the stored result instead of re-executing (replay suppression).

``CircuitBreaker``
  closed -> open after ``threshold`` consecutive failures; open rejects with
  ``CircuitOpen`` until ``cooldown``; half-open admits one probe.

``AdmissionQueue``
  bounded, per-tenant fair (round-robin across tenants), priority-ordered
  within a tenant; when full, the lowest-priority item is shed (or the new
  one refused if it is lowest).  ``saturation()`` is exported as a metric.
"""
from __future__ import annotations

import collections
import heapq
import itertools
import random
import threading
import time
from typing import Any, Callable

from .errors import RETRYABLE, Cancelled, CircuitOpen, DeadlineExceeded, GitOpsError, Throttled


class TokenBucket:
    def __init__(self, rate: float, burst: float, clock=time.monotonic) -> None:
        self.rate, self.burst, self.clock = rate, burst, clock
        self.tokens, self.t = burst, clock()
        self._lock = threading.Lock()

    def take(self, n: float = 1.0) -> bool:
        with self._lock:
            now = self.clock()
            self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
            self.t = now
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False


class RetryBudget(TokenBucket):
    pass


class RetryPolicy:
    def __init__(self, *, max_attempts: int = 5, base: float = 0.2, cap: float = 30.0,
                 budget: RetryBudget | None = None, sleep=time.sleep, rng: random.Random | None = None,
                 clock=time.monotonic) -> None:
        self.max_attempts, self.base, self.cap = max_attempts, base, cap
        self.budget, self.sleep, self.rng, self.clock = budget, sleep, rng or random.Random(), clock
        self.attempts_made = 0

    def backoff(self, n: int) -> float:
        return self.rng.uniform(0, min(self.cap, self.base * (2 ** n)))

    def call(self, fn: Callable[[], Any], *, deadline: float | None = None,
             cancel: threading.Event | None = None) -> Any:
        n = 0
        while True:
            if cancel is not None and cancel.is_set():
                raise Cancelled("operation cancelled")
            if deadline is not None and self.clock() >= deadline:
                raise DeadlineExceeded("deadline exceeded before attempt", attempts=n)
            n += 1
            self.attempts_made = n
            try:
                return fn()
            except GitOpsError as exc:
                if exc.retry != RETRYABLE or n >= self.max_attempts:
                    raise
                if self.budget is not None and not self.budget.take():
                    raise Throttled("retry budget exhausted", cause=exc.code) from exc
                d = self.backoff(n - 1)
                if deadline is not None and self.clock() + d >= deadline:
                    raise DeadlineExceeded("deadline would pass during backoff", attempts=n, cause=exc.code) from exc
                if cancel is not None:
                    if cancel.wait(d):
                        raise Cancelled("operation cancelled during backoff") from exc
                else:
                    self.sleep(d)


class IdempotencyCache:
    def __init__(self, ttl: float, *, capacity: int = 10_000, clock=time.monotonic) -> None:
        self.ttl, self.cap, self.clock = ttl, capacity, clock
        self._d: collections.OrderedDict = collections.OrderedDict()
        self._lock = threading.Lock()

    def run(self, key: str, fn: Callable[[], Any]) -> tuple[Any, bool]:
        """Return (result, replayed)."""
        with self._lock:
            now = self.clock()
            for k in [k for k, (t, _) in self._d.items() if now - t > self.ttl]:
                del self._d[k]
            if key in self._d:
                return self._d[key][1], True
        res = fn()
        with self._lock:
            self._d[key] = (self.clock(), res)
            while len(self._d) > self.cap:
                self._d.popitem(last=False)
        return res, False


class CircuitBreaker:
    def __init__(self, name: str, *, threshold: int, cooldown: float, clock=time.monotonic) -> None:
        self.name, self.threshold, self.cooldown, self.clock = name, threshold, cooldown, clock
        self.failures, self.state, self.opened_at = 0, "closed", 0.0
        self._lock = threading.Lock()
        self._probe = False

    def call(self, fn: Callable[[], Any]) -> Any:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at < self.cooldown:
                    raise CircuitOpen("dependency circuit open", dependency=self.name)
                self.state = "half_open"
                self._probe = False
            if self.state == "half_open":
                if self._probe:
                    raise CircuitOpen("half-open probe in flight", dependency=self.name)
                self._probe = True
        try:
            res = fn()
        except GitOpsError as exc:
            with self._lock:
                if exc.retry == RETRYABLE or self.state == "half_open":
                    self.failures += 1
                    if self.state == "half_open" or self.failures >= self.threshold:
                        self.state, self.opened_at = "open", self.clock()
                self._probe = False
            raise
        with self._lock:
            self.failures, self.state, self._probe = 0, "closed", False
        return res


class AdmissionQueue:
    def __init__(self, capacity: int, *, tenant_rate: float = 1e9, tenant_burst: float = 1e9) -> None:
        self.cap = capacity
        self._q: dict[str, list] = collections.defaultdict(list)
        self._rr: collections.deque = collections.deque()
        self._n = 0
        self._seq = itertools.count()
        self._buckets: dict[str, TokenBucket] = {}
        self._rate, self._burst = tenant_rate, tenant_burst
        self._lock = threading.Lock()
        self.shed = 0

    def put(self, tenant: str, item: Any, priority: int = 5) -> None:
        with self._lock:
            b = self._buckets.setdefault(tenant, TokenBucket(self._rate, self._burst))
            if not b.take():
                raise Throttled("tenant rate limit", tenant=tenant, retry_after=1.0 / max(self._rate, 1e-9))
            if self._n >= self.cap:
                worst_t, worst = None, None
                for t, h in self._q.items():
                    for e in h:
                        if worst is None or (e[0], -e[1]) > (worst[0], -worst[1]):
                            worst_t, worst = t, e
                if worst is None or worst[0] <= -priority:
                    raise Throttled("admission queue full", retry_after=1.0)
                self._q[worst_t].remove(worst)
                heapq.heapify(self._q[worst_t])
                self._n -= 1
                self.shed += 1
            heapq.heappush(self._q[tenant], (-priority, next(self._seq), item))
            if tenant not in self._rr:
                self._rr.append(tenant)
            self._n += 1

    def get(self) -> tuple[str, Any] | None:
        with self._lock:
            for _ in range(len(self._rr)):
                t = self._rr[0]
                self._rr.rotate(-1)
                if self._q[t]:
                    _, _, item = heapq.heappop(self._q[t])
                    self._n -= 1
                    return t, item
            return None

    def saturation(self) -> float:
        return self._n / self.cap if self.cap else 1.0
