"""#9 fairness: weighted deficit-round-robin admission queue with bounded size and starvation bound.

Guarantee: with tenant weights w_i and quantum Q, a backlogged tenant i is
served at least once every ``ceil(max_cost / (Q*w_i))`` rounds, and within a
round every backlogged tenant is visited, so no tenant with pending work can
starve while any other tenant is served.  Queue length is bounded globally and
per tenant; overflow raises retryable backpressure instead of growing memory.
"""
from __future__ import annotations

import threading
from collections import OrderedDict, deque
from collections.abc import Mapping
from dataclasses import dataclass

from .data_plane import Backpressure


@dataclass
class QueuedRequest:
    tenant: str
    cost: int
    payload: object
    seq: int


class FairScheduler:
    def __init__(self, *, quantum: int = 64 * 1024 * 1024, weights: Mapping[str, int] | None = None,
                 max_queue: int = 10_000, max_per_tenant: int = 1_000, max_connections: int = 64):
        if quantum < 1 or max_queue < 1 or max_per_tenant < 1 or max_connections < 1:
            raise ValueError("scheduler limits must be positive")
        self._quantum = quantum
        self._weights = dict(weights or {})
        self._queues: OrderedDict[str, deque[QueuedRequest]] = OrderedDict()
        self._deficit: dict[str, int] = {}
        self._size = 0
        self._max = max_queue
        self._max_tenant = max_per_tenant
        self.max_connections = max_connections
        self._seq = 0
        self._lock = threading.Lock()
        self.served: dict[str, int] = {}

    def weight(self, tenant: str) -> int:
        return max(1, int(self._weights.get(tenant, 1)))

    def __len__(self) -> int:
        return self._size

    def enqueue(self, tenant: str, cost: int, payload: object = None) -> int:
        if cost < 0:
            raise ValueError("cost must be non-negative")
        with self._lock:
            q = self._queues.get(tenant)
            if self._size >= self._max:
                raise Backpressure("scheduler queue full", scope="global", limit=self._max)
            if q is not None and len(q) >= self._max_tenant:
                raise Backpressure("tenant queue full", scope="tenant", tenant=tenant, limit=self._max_tenant)
            if q is None:
                q = self._queues[tenant] = deque()
                self._deficit[tenant] = 0
            self._seq += 1
            q.append(QueuedRequest(tenant, cost, payload, self._seq))
            self._size += 1
            return self._seq

    def dequeue(self) -> QueuedRequest | None:
        """Return the next request under DRR, or None if empty."""
        with self._lock:
            # at most enough passes to accumulate the largest head cost for the lightest weight
            for _ in range(1 + 4 * max(1, len(self._queues)) * 1024):
                if not self._queues:
                    return None
                tenant, q = next(iter(self._queues.items()))
                head = q[0]
                if self._deficit[tenant] >= head.cost:
                    q.popleft()
                    self._deficit[tenant] -= head.cost
                    self._size -= 1
                    self.served[tenant] = self.served.get(tenant, 0) + 1
                    if not q:
                        del self._queues[tenant]
                        del self._deficit[tenant]
                    return head
                self._deficit[tenant] += self._quantum * self.weight(tenant)
                self._queues.move_to_end(tenant)
            raise RuntimeError("DRR failed to make progress")  # pragma: no cover
