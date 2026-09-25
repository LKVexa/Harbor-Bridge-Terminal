"""Per-tenant admission quotas (MC-009; C017, C028, C067, C069).

Token bucket per tenant (``rate_per_s``, ``burst``) from the active config
generation (``quotas.default`` overridden by ``quotas.tenants[<t>]``).  Exhaustion
returns ``ECP_QUOTA_EXCEEDED`` with ``retry_after_ms`` — a client-visible,
retryable signal, not a silent drop.  The bucket map is bounded: idle full
buckets are evicted when it exceeds ``max_tenants`` (they would refill to full
anyway, so eviction changes no decision).
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from .errors import EcpError
from .util import now


class Quotas:
    def __init__(self, clock: Callable[[], float] = now, max_tenants: int = 100_000):
        self.clock = clock
        self.max_tenants = max_tenants
        self._b: dict[str, list[float]] = {}  # tenant -> [tokens, last_ts]
        self._lock = threading.Lock()

    @staticmethod
    def spec(quotas: dict[str, Any], tenant: str) -> dict[str, Any]:
        return {**quotas["default"], **quotas.get("tenants", {}).get(tenant, {})}

    def take(self, quotas: dict[str, Any], tenant: str) -> None:
        q = self.spec(quotas, tenant)
        rate, burst = float(q["rate_per_s"]), float(q["burst"])
        t = self.clock()
        with self._lock:
            b = self._b.get(tenant)
            if b is None:
                if len(self._b) >= self.max_tenants:
                    self._evict(t, quotas)
                b = self._b[tenant] = [burst, t]
            b[0] = min(burst, b[0] + (t - b[1]) * rate)
            b[1] = t
            if b[0] < 1.0:
                wait = (1.0 - b[0]) / rate
                raise EcpError("ECP_QUOTA_EXCEEDED", "tenant admission quota exhausted", tenant=tenant,
                               retry_after_ms=int(wait * 1000) + 1, limit=int(burst))
            b[0] -= 1.0

    def _evict(self, t: float, quotas: dict[str, Any]) -> None:
        for k in list(self._b):
            q = self.spec(quotas, k)
            if self._b[k][0] + (t - self._b[k][1]) * float(q["rate_per_s"]) >= float(q["burst"]):
                del self._b[k]

    def __len__(self) -> int:
        return len(self._b)
