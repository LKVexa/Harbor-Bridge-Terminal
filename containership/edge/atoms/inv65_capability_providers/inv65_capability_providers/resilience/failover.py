"""Failover and degraded mode (M17).  Target selection honours residency (M40)
and health; takeover requires acquiring the slot lease (new epoch), which
fences the previous owner.  Degraded mode serves only operations in the
declared degraded capability set (reads by default)."""
from __future__ import annotations

from ..errors.mapping import ProviderFault

DEFAULT_DEGRADED_OPS = frozenset({"get", "head", "list", "exists"})


def choose_target(candidates: list[dict], *, tenant: str, residency, healthy) -> dict:
    """candidates: [{instance_id, site, region, environment}] -- first healthy & residency-allowed wins."""
    reasons = []
    for c in candidates:
        try:
            residency.check_placement(tenant, region=c["region"], environment=c["environment"], failover=True)
        except ProviderFault as e:
            reasons.append(f"{c['instance_id']}:{e.code}")
            continue
        if healthy(c):
            return c
        reasons.append(f"{c['instance_id']}:unhealthy")
    raise ProviderFault("PK_PROVIDER_UNAVAILABLE", "no eligible failover target: " + ",".join(reasons)[:400])


def takeover(leases, slot: str, new_holder: str) -> int:
    return leases.acquire(slot, new_holder)


def degraded_allows(op: str, allowed=DEFAULT_DEGRADED_OPS) -> bool:
    return op in allowed
