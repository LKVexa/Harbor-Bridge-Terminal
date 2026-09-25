"""Data-residency/locality/failover constraint engine (M40).

Policies (schema residency_policy/v1) are per tenant.  No policy => deny
(fail closed) unless the engine is built with ``default_allow=True`` for
explicitly non-regulated deployments.  Failover may use only
``failover_regions`` (or allowed_regions if none declared)."""
from __future__ import annotations

import threading

from ..errors.mapping import ProviderFault
from ..schemas import SchemaError, check


class ResidencyEngine:
    def __init__(self, *, default_allow: bool = False):
        self._p: dict[str, dict] = {}
        self.default_allow = default_allow
        self._lock = threading.Lock()

    def set_policy(self, policy: dict) -> None:
        try:
            check(policy, "residency_policy")
        except SchemaError as e:
            raise ProviderFault("PK_PROVIDER_INVALID_LINK", f"bad residency policy: {e}") from None
        with self._lock:
            self._p[policy["tenant"]] = dict(policy)

    def check_placement(self, tenant: str, *, region: str, environment: str, failover: bool = False) -> None:
        with self._lock:
            p = self._p.get(tenant)
        if p is None:
            if self.default_allow:
                return
            raise ProviderFault("PK_PROVIDER_RESIDENCY", "no residency policy for tenant")
        envs = p.get("allowed_environments")
        if envs and environment not in envs:
            raise ProviderFault("PK_PROVIDER_RESIDENCY", "environment not permitted for tenant")
        allowed = p.get("failover_regions") or p["allowed_regions"] if failover else p["allowed_regions"]
        if region not in allowed:
            raise ProviderFault("PK_PROVIDER_RESIDENCY", f"region {region!r} not permitted" + (" for failover" if failover else ""))
