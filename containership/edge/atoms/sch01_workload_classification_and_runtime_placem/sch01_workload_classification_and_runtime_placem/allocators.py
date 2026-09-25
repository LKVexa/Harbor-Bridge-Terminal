"""MC-10 quota / fair-share accounting and MC-15 accelerator allocation."""
from __future__ import annotations

import threading
from typing import Mapping

from .errors import SchedulerError
from .model import Accelerator


class QuotaLedger:
    """Per-tenant slot reservations with a hard quota and a fair-share cap.

    Fair share: while other tenants are waiting (have been refused within the window), no
    tenant may hold more than ``max_fraction`` of the fleet's total slots.  This is the
    starvation guard.
    """

    def __init__(self, quotas: Mapping[str, int], default_quota: int, max_fraction: float):
        self.quotas, self.default, self.max_fraction = dict(quotas), default_quota, max_fraction
        self.used: dict[str, int] = {}
        self.waiting: set[str] = set()
        self._lock = threading.Lock()

    def check(self, tenant: str, slots: int, fleet_slots: int) -> None:
        q = self.quotas.get(tenant, self.default)
        used = self.used.get(tenant, 0)
        if used + slots > q:
            self.waiting.add(tenant)
            raise SchedulerError("QUOTA_EXCEEDED", "tenant quota exhausted",
                                 details={"quota": q, "used": used, "requested": slots})
        others_waiting = self.waiting - {tenant}
        if others_waiting and fleet_slots > 0 and (used + slots) > self.max_fraction * fleet_slots:
            raise SchedulerError("QUOTA_EXCEEDED", "fair-share cap while other tenants wait",
                                 details={"cap_fraction": self.max_fraction})

    def reserve(self, tenant: str, slots: int) -> None:
        self.used[tenant] = self.used.get(tenant, 0) + slots
        self.waiting.discard(tenant)

    def release(self, tenant: str, slots: int) -> None:
        self.used[tenant] = max(0, self.used.get(tenant, 0) - slots)


class AcceleratorPool:
    """Tracks device leases per node.  Exclusive allocation; unhealthy devices are never
    allocated; NUMA-local sets are preferred."""

    def __init__(self):
        self.leased: dict[tuple[str, str], str] = {}   # (node, device) -> lease_id

    def free(self, node: str, devices: tuple[Accelerator, ...]) -> list[Accelerator]:
        return [d for d in devices if d.healthy and (node, d.device_id) not in self.leased]

    def pick(self, node: str, devices: tuple[Accelerator, ...], want: Mapping[str, int]) -> list[Accelerator] | None:
        free = self.free(node, devices)
        chosen: list[Accelerator] = []
        for kind, n in sorted(want.items()):
            pool = [d for d in free if d.kind == kind]
            if len(pool) < n:
                return None
            by_numa: dict[int, list[Accelerator]] = {}
            for d in pool:
                by_numa.setdefault(d.numa, []).append(d)
            local = [v for _, v in sorted(by_numa.items()) if len(v) >= n]
            src = local[0] if local else sorted(pool, key=lambda d: (d.numa, d.device_id))
            chosen += sorted(src, key=lambda d: d.device_id)[:n]
        return chosen

    def lease(self, node: str, devices: list[Accelerator], lease_id: str) -> None:
        for d in devices:
            if (node, d.device_id) in self.leased:
                raise SchedulerError("NO_CANDIDATE", "accelerator already leased")
        for d in devices:
            self.leased[(node, d.device_id)] = lease_id

    def release(self, lease_id: str) -> None:
        for k in [k for k, v in self.leased.items() if v == lease_id]:
            del self.leased[k]
