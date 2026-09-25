"""Tenant quota, fairness and contention policy (WS 18).

Model: **strict quota with borrowing**.  Each tenant has a memory guarantee, a hard cap and a vCPU cap.
Host reserve is removed *before* any tenant distribution.  A tenant may grow above its guarantee
(borrow) only from memory that is not needed to keep every *other* tenant's guarantee satisfiable;
it may never exceed its hard cap.  Reclaim under pressure picks borrowers first, largest borrow first,
tie-broken by tenant ID (deterministic), and never below any guest floor (floors are enforced by the
model/controller, fairness never overrides them).  Request-rate fairness is a per-tenant token bucket
in ``resilience.AdmissionController``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from . import errors as E


@dataclass(frozen=True)
class TenantQuota:
    guarantee_mib: int
    hard_cap_mib: int
    vcpu_cap: int = 1 << 16

    def __post_init__(self) -> None:
        if not 0 <= self.guarantee_mib <= self.hard_cap_mib or self.vcpu_cap < 1:
            raise ValueError("quota requires 0 <= guarantee <= hard_cap and vcpu_cap >= 1")


class QuotaPolicy:
    def __init__(self, quotas: Mapping[str, TenantQuota] | None = None, *, default: TenantQuota | None = None) -> None:
        self.quotas = dict(quotas or {})
        self.default = default

    def quota(self, tenant: str) -> TenantQuota | None:
        return self.quotas.get(tenant, self.default)

    def check_growth(self, *, tenant: str, delta_mib: int, delta_vcpus: int, usage: Mapping[str, tuple[int, int]],
                     allocatable_mib: int) -> None:
        """Raise QuotaExceeded if the change breaks this tenant's cap or another tenant's guarantee."""
        q = self.quota(tenant)
        if q is None:
            return
        mem, cpu = usage.get(tenant, (0, 0))
        if delta_mib > 0 and mem + delta_mib > q.hard_cap_mib:
            raise E.QuotaExceeded("tenant memory hard cap", cap_mib=q.hard_cap_mib)
        if delta_vcpus > 0 and cpu + delta_vcpus > q.vcpu_cap:
            raise E.QuotaExceeded("tenant vCPU cap", cap=q.vcpu_cap)
        if delta_mib > 0 and mem + delta_mib > q.guarantee_mib:
            # Borrowing: keep enough allocatable memory to honour every other tenant's unmet guarantee.
            owed = 0
            for other, (omem, _) in usage.items():
                oq = self.quota(other)
                if other != tenant and oq is not None:
                    owed += max(0, oq.guarantee_mib - omem)
            used = sum(m for m, _ in usage.values())
            if used + delta_mib + owed > allocatable_mib:
                raise E.QuotaExceeded("borrow would make another tenant's guarantee unsatisfiable")

    def reclaim_order(self, usage: Mapping[str, tuple[int, int]]) -> list[tuple[str, int]]:
        borrowers = []
        for tenant, (mem, _) in usage.items():
            q = self.quota(tenant)
            borrow = mem - q.guarantee_mib if q else 0
            if borrow > 0:
                borrowers.append((tenant, borrow))
        return sorted(borrowers, key=lambda t: (-t[1], t[0]))

    def unsatisfiable_guarantees(self, allocatable_mib: int) -> bool:
        return sum(q.guarantee_mib for q in self.quotas.values()) > allocatable_mib
