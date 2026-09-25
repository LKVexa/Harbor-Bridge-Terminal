"""Capacity and resource controls (component 32).

Token-bucket rate limits keyed per principal / partition / producer plus a
global bucket, with ``retry_after`` (MC-32-02); bounded queues that shed load
predictably (MC-32-03); weighted fair share across partitions (MC-32-07); a
priority lane that keeps health / admin / revocation working while ordinary
traffic is saturated (MC-32-08).
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

LIMITS = {
    "max_body_bytes": 256 * 1024,
    "max_batch_items": 100,
    "max_identifier_length": 512,
    "max_history_page": 1000,
    "max_matrix_rows_per_partition": 1_000_000,
    "max_concurrent_requests": 64,
    "max_queued_jobs": 10_000,
    "max_nesting_depth": 16,
}
PRIORITY_OPS = {"health", "ready", "revocation", "quarantine", "emergency", "metrics"}


class CapacityError(RuntimeError):
    def __init__(self, code: str, retry_after: float = 0.0) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


@dataclass
class TokenBucket:
    rate: float
    burst: float
    clock: Callable[[], float] = time.monotonic
    tokens: float = -1.0
    stamp: float = 0.0

    def take(self, cost: float = 1.0) -> float:
        """Return 0 when admitted, else seconds until enough tokens exist."""
        now = self.clock()
        if self.tokens < 0:
            self.tokens, self.stamp = self.burst, now
        self.tokens = min(self.burst, self.tokens + (now - self.stamp) * self.rate)
        self.stamp = now
        if self.tokens >= cost:
            self.tokens -= cost
            return 0.0
        return (cost - self.tokens) / self.rate


class RateLimiter:
    def __init__(self, *, per_key_rate: float, per_key_burst: float, global_rate: float, global_burst: float,
                 clock: Callable[[], float] = time.monotonic, max_keys: int = 100_000) -> None:
        self._lock = threading.Lock()
        self._buckets: dict = {}
        self._clock = clock
        self._cfg = (per_key_rate, per_key_burst)
        self._global = TokenBucket(global_rate, global_burst, clock)
        self._max_keys = max_keys

    def check(self, *keys: str, cost: float = 1.0, op: str = "") -> None:
        if op in PRIORITY_OPS:
            return  # overload mode keeps priority paths open
        with self._lock:
            waits = []
            for k in keys:
                b = self._buckets.get(k)
                if b is None:
                    if len(self._buckets) >= self._max_keys:
                        raise CapacityError("E_CAPACITY_KEYSPACE", 1.0)
                    b = self._buckets[k] = TokenBucket(*self._cfg, self._clock)
                waits.append(b.take(cost))
            waits.append(self._global.take(cost))
            if any(waits):
                raise CapacityError("E_RATE_LIMITED", max(waits))


@dataclass
class FairQueue:
    """Bounded multi-tenant queue with weighted round robin (per-partition quota)."""

    capacity: int = LIMITS["max_queued_jobs"]
    per_partition: int = 1000
    weights: dict = field(default_factory=dict)
    _queues: dict = field(default_factory=dict)
    _order: deque = field(default_factory=deque)
    _credit: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __len__(self) -> int:
        return sum(len(q) for q in self._queues.values())

    def put(self, partition: str, item) -> None:
        with self._lock:
            if len(self) >= self.capacity:
                raise CapacityError("E_QUEUE_FULL", 1.0)
            q = self._queues.setdefault(partition, deque())
            if len(q) >= self.per_partition:
                raise CapacityError("E_PARTITION_QUOTA", 1.0)
            if partition not in self._order:
                self._order.append(partition)
            q.append(item)

    def get(self) -> Optional[tuple]:
        with self._lock:
            for _ in range(len(self._order)):
                p = self._order[0]
                q = self._queues.get(p)
                if not q:
                    self._order.popleft()
                    continue
                credit = self._credit.get(p, self.weights.get(p, 1))
                item = q.popleft()
                credit -= 1
                if credit <= 0 or not q:
                    self._order.rotate(-1)
                    credit = self.weights.get(p, 1)
                self._credit[p] = credit
                return p, item
            return None


class ConcurrencyGate:
    def __init__(self, limit: int = LIMITS["max_concurrent_requests"]) -> None:
        self._sem = threading.BoundedSemaphore(limit)
        self.limit = limit

    def __enter__(self):
        if not self._sem.acquire(blocking=False):
            raise CapacityError("E_OVERLOADED", 0.5)
        return self

    def __exit__(self, *exc):
        self._sem.release()
        return False
