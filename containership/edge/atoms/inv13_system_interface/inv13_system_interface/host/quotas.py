"""MC-017 -- per-tenant/per-workload quotas and admission control.

Hierarchical counters (tenant -> workload) for named resources.  ``acquire``
is all-or-nothing across both levels; ``Admission`` sheds new work when the
node-wide concurrency ceiling is reached and gives each tenant a fair share
(no tenant may hold more than ``fair_share`` of node slots while others wait).
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

from .errors import ErrorCode, Inv13Error

DEFAULT_LIMITS = {"descriptors": 1024, "preopens": 64, "sockets": 16, "streams": 64,
                  "buffer_bytes": 64 << 20, "concurrent_ops": 32, "provider_fanout": 8}


class QuotaLedger:
    def __init__(self, tenant_limits: dict[str, dict[str, int]], workload_limits: dict[str, int] | None = None):
        self._tl = {t: {**DEFAULT_LIMITS, **l} for t, l in tenant_limits.items()}
        self._wl = {**DEFAULT_LIMITS, **(workload_limits or {})}
        self._use: dict[tuple[str, str | None, str], int] = {}
        self._lock = threading.Lock()

    def usage(self, tenant: str, resource: str, workload: str | None = None) -> int:
        return self._use.get((tenant, workload, resource), 0)

    def acquire(self, tenant: str, workload: str, resource: str, n: int = 1) -> None:
        if n <= 0:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT)
        with self._lock:
            tl = self._tl.get(tenant)
            if tl is None or resource not in tl:
                raise Inv13Error(ErrorCode.POLICY_DENIED, "no quota for tenant/resource")
            tk, wk = (tenant, None, resource), (tenant, workload, resource)
            if self._use.get(tk, 0) + n > tl[resource] or self._use.get(wk, 0) + n > self._wl[resource]:
                raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, resource)
            self._use[tk] = self._use.get(tk, 0) + n
            self._use[wk] = self._use.get(wk, 0) + n

    def release(self, tenant: str, workload: str, resource: str, n: int = 1) -> None:
        with self._lock:
            for k in ((tenant, None, resource), (tenant, workload, resource)):
                cur = self._use.get(k, 0)
                if cur < n:
                    raise Inv13Error(ErrorCode.INTERNAL, "quota underflow")
                self._use[k] = cur - n

    @contextmanager
    def hold(self, tenant: str, workload: str, resource: str, n: int = 1) -> Iterator[None]:
        self.acquire(tenant, workload, resource, n)
        try:
            yield
        finally:
            self.release(tenant, workload, resource, n)


class Admission:
    def __init__(self, node_slots: int, fair_share: float = 0.5) -> None:
        self.node_slots, self.fair_share = node_slots, fair_share
        self._held: dict[str, int] = {}
        self._lock = threading.Lock()
        self.shed = 0

    def try_admit(self, tenant: str) -> bool:
        with self._lock:
            total = sum(self._held.values())
            mine = self._held.get(tenant, 0)
            others_active = any(v for t, v in self._held.items() if t != tenant)
            cap = int(self.node_slots * self.fair_share) if others_active else self.node_slots
            if total >= self.node_slots or mine >= max(1, cap):
                self.shed += 1
                return False
            self._held[tenant] = mine + 1
            return True

    def done(self, tenant: str) -> None:
        with self._lock:
            self._held[tenant] -= 1
