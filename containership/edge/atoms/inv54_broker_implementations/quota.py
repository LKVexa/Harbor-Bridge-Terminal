"""Per-tenant/per-workload quotas, fairness and resource accounting (components 8, 65, 70).

Fairness model: each (tenant, workload) has its own token bucket (rate/burst) and byte
budget, so one tenant exhausting its allowance cannot consume another's.  Accounting is
exact in-process counters exposed as a snapshot for capacity modelling.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable

from .errors import QUOTA_EXCEEDED, BrokerError
from .resilience import TokenBucket


@dataclass
class QuotaSpec:
    publish_rate: float = 1000.0
    publish_burst: float = 2000.0
    max_bytes: int = 256 * 1024 * 1024


@dataclass
class Usage:
    messages: int = 0
    bytes_in: int = 0
    bytes_retained: int = 0
    rejected: int = 0


class QuotaManager:
    def __init__(self, default: QuotaSpec | None = None, overrides: dict[str, QuotaSpec] | None = None,
                 clock: Callable[[], float] = time.monotonic, max_tracked: int = 100_000) -> None:
        self.default = default or QuotaSpec()
        self.overrides = dict(overrides or {})
        self.clock = clock
        self._buckets: dict[tuple[str, str], TokenBucket] = {}
        self.usage: dict[tuple[str, str], Usage] = {}
        self._max = max_tracked
        self._lock = RLock()

    def spec(self, tenant: str) -> QuotaSpec:
        return self.overrides.get(tenant, self.default)

    def charge(self, tenant: str, workload: str, nbytes: int) -> None:
        key = (tenant, workload)
        with self._lock:
            if key not in self._buckets:
                if len(self._buckets) >= self._max:
                    raise BrokerError(QUOTA_EXCEEDED, "tracked (tenant,workload) ceiling reached")
                s = self.spec(tenant)
                self._buckets[key] = TokenBucket(s.publish_rate, s.publish_burst, self.clock)
                self.usage[key] = Usage()
            u = self.usage[key]
            s = self.spec(tenant)
            tenant_retained = sum(v.bytes_retained for (t, _), v in self.usage.items() if t == tenant)
            if tenant_retained + nbytes > s.max_bytes:
                u.rejected += 1
                raise BrokerError(QUOTA_EXCEEDED, "byte budget exhausted", tenant=tenant, limit=s.max_bytes)
            if not self._buckets[key].try_take():
                u.rejected += 1
                raise BrokerError(QUOTA_EXCEEDED, "publish rate exceeded", tenant=tenant, workload=workload)
            u.messages += 1
            u.bytes_in += nbytes
            u.bytes_retained += nbytes

    def release_bytes(self, tenant: str, workload: str, nbytes: int) -> None:
        with self._lock:
            u = self.usage.get((tenant, workload))
            if u:
                u.bytes_retained = max(0, u.bytes_retained - nbytes)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [{"tenant": t, "workload": w, **u.__dict__} for (t, w), u in sorted(self.usage.items())]


def saturation(inflight: int, max_inflight: int, backlog: int, max_backlog: int) -> dict[str, float | str]:
    """Capacity model signal (component 70): the worst normalised utilisation decides the state."""
    u = max(inflight / max_inflight if max_inflight else 1.0, backlog / max_backlog if max_backlog else 1.0)
    state = "ok" if u < 0.7 else "warning" if u < 0.9 else "saturated"
    return {"utilisation": round(u, 4), "state": state}
