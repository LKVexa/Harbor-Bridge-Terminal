"""Structural quotas (M15): max links per tenant and per workload, and max
config bytes per link, enforced at link creation so state cannot be exhausted."""
from __future__ import annotations

import json

from ..errors.mapping import ProviderFault


class LinkQuotas:
    def __init__(self, max_links_per_tenant=1000, max_links_per_workload=100, max_config_bytes=16_384):
        self.per_tenant, self.per_workload, self.max_bytes = max_links_per_tenant, max_links_per_workload, max_config_bytes

    def check(self, existing_keys: list, identity, config: dict, *, is_update: bool) -> None:
        if len(json.dumps(config, sort_keys=True)) > self.max_bytes:
            raise ProviderFault("PK_PROVIDER_INVALID_LINK", "link config exceeds size quota")
        if is_update:
            return
        t = sum(1 for k in existing_keys if k[0] == identity.tenant)
        w = sum(1 for k in existing_keys if k[0] == identity.tenant and k[3] == identity.workload)
        if t >= self.per_tenant or w >= self.per_workload:
            raise ProviderFault("PK_PROVIDER_OVERLOADED", "link count quota reached")
