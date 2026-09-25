"""Component 16 - tenant/workload quota and fairness engine.

Model (QUOTA_SPEC):
* ``Quota(tenant, limit, reserved, burst, weight, priority)`` - all non-negative
  ints except weight (> 0).  reserved <= limit; burst is extra nodes allowed
  above limit only while the pool has idle capacity.  Sum of reservations must
  not exceed pool capacity (checked in ``QuotaEngine``).
* Priority: higher integer served first *after* reservations are honoured.
  Reservations are guaranteed irrespective of priority.
* Fair share: within one priority tier, weighted max-min fairness
  (water-filling) over remaining capacity, capped by each tenant's
  limit(+burst when idle), ties broken by tenant id - fully deterministic.
* Starvation: a tenant with unmet demand that receives 0 for
  ``starvation_rounds`` consecutive rounds is flagged and its effective priority
  is aged up by one tier per further starved round until served.
* Telemetry: per-round counters (admitted, rejected, burst_used, starved) are
  kept in ``telemetry``.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .errors_catalog import error


@dataclass(frozen=True)
class Quota:
    tenant: str
    limit: int
    reserved: int = 0
    burst: int = 0
    weight: int = 1
    priority: int = 0

    def __post_init__(self) -> None:
        for f in ("limit", "reserved", "burst", "priority"):
            v = getattr(self, f)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise error("INV08.QUOTA.INVALID", f"{self.tenant}.{f} must be a non-negative int")
        if isinstance(self.weight, bool) or not isinstance(self.weight, int) or self.weight <= 0:
            raise error("INV08.QUOTA.INVALID", f"{self.tenant}.weight must be a positive int")
        if self.reserved > self.limit:
            raise error("INV08.QUOTA.INVALID", f"{self.tenant}: reserved > limit")
        if not self.tenant:
            raise error("INV08.QUOTA.INVALID", "tenant id required")


class QuotaEngine:
    def __init__(self, capacity: int, quotas: list[Quota], *, starvation_rounds: int = 3) -> None:
        if capacity < 0:
            raise error("INV08.QUOTA.INVALID", "capacity must be >= 0")
        self.capacity = capacity
        self.quotas = {q.tenant: q for q in quotas}
        if len(self.quotas) != len(quotas):
            raise error("INV08.QUOTA.INVALID", "duplicate tenant")
        if sum(q.reserved for q in quotas) > capacity:
            raise error("INV08.QUOTA.INVALID", "reservations exceed capacity")
        self.starvation_rounds = starvation_rounds
        self.usage = {t: 0 for t in self.quotas}
        self.starved = {t: 0 for t in self.quotas}
        self.telemetry = {"admitted": 0, "rejected": 0, "burst_used": 0, "starved_flags": 0, "rounds": 0}

    # -- single-request admission against the current usage
    def admit(self, tenant: str, n: int) -> dict:
        q = self.quotas.get(tenant)
        if q is None:
            raise error("INV08.QUOTA.UNKNOWN_TENANT", tenant)
        if n <= 0:
            raise error("INV08.QUOTA.INVALID", "request must be positive")
        used = sum(self.usage.values())
        # capacity others are entitled to via unused reservations
        held = sum(max(0, o.reserved - self.usage[o.tenant]) for o in self.quotas.values() if o.tenant != tenant)
        free = self.capacity - used - held
        want = self.usage[tenant] + n
        idle = free >= n
        cap = q.limit + (q.burst if idle else 0)
        if want > cap or n > free:
            self.telemetry["rejected"] += 1
            raise error("INV08.QUOTA.EXCEEDED", f"{tenant} requested {n}",
                        details={"tenant": tenant, "usage": self.usage[tenant], "limit": q.limit,
                                 "burst": q.burst, "free": free})
        if want > q.limit:
            self.telemetry["burst_used"] += want - max(q.limit, self.usage[tenant])
        self.usage[tenant] = want
        self.telemetry["admitted"] += 1
        return {"tenant": tenant, "granted": n, "usage": want, "burst": want > q.limit}

    def release(self, tenant: str, n: int) -> None:
        if tenant not in self.usage:
            raise error("INV08.QUOTA.UNKNOWN_TENANT", tenant)
        self.usage[tenant] = max(0, self.usage[tenant] - n)

    # -- batch fair allocation of the whole pool for one round
    def allocate(self, demand: dict[str, int]) -> dict[str, int]:
        for t in demand:
            if t not in self.quotas:
                raise error("INV08.QUOTA.UNKNOWN_TENANT", t)
        self.telemetry["rounds"] += 1
        total_demand = sum(demand.values())
        idle = total_demand < self.capacity
        cap = {t: min(demand.get(t, 0), q.limit + (q.burst if idle else 0))
               for t, q in self.quotas.items()}
        alloc = {t: min(cap[t], q.reserved) for t, q in self.quotas.items()}
        left = self.capacity - sum(alloc.values())
        eff = {t: q.priority + max(0, self.starved[t] - self.starvation_rounds + 1)
               for t, q in self.quotas.items()}
        for prio in sorted(set(eff.values()), reverse=True):
            tier = sorted(t for t in self.quotas if eff[t] == prio)
            left = self._waterfill(tier, alloc, cap, left)
        for t in self.quotas:
            unmet = demand.get(t, 0) > 0 and alloc[t] == 0
            self.starved[t] = self.starved[t] + 1 if unmet else 0
            if self.starved[t] == self.starvation_rounds:
                self.telemetry["starved_flags"] += 1
        return alloc

    def _waterfill(self, tier: list[str], alloc: dict, cap: dict, left: int) -> int:
        active = [t for t in tier if alloc[t] < cap[t]]
        while left > 0 and active:
            wsum = sum(self.quotas[t].weight for t in active)
            # exact fractional shares, then integerise by largest remainder
            shares = {t: Fraction(left * self.quotas[t].weight, wsum) for t in active}
            give = {t: min(int(shares[t]), cap[t] - alloc[t]) for t in active}
            if sum(give.values()) == 0:
                # fewer units than tenants: hand out one by one by remainder, weight, id
                order = sorted(active, key=lambda t: (-(shares[t] - int(shares[t])), -self.quotas[t].weight, t))
                for t in order[:left]:
                    give[t] = 1
            for t, g in give.items():
                alloc[t] += g
                left -= g
            active = [t for t in active if alloc[t] < cap[t]]
        return left

    def starving(self) -> list[str]:
        return sorted(t for t, n in self.starved.items() if n >= self.starvation_rounds)
