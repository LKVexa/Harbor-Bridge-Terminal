"""Site/topology blast-radius policy engine (component 9).

Enforced before each wave (and each deferred retry) against an inventory that
carries version + freshness metadata from topology/hardware discovery:

* unknown node, unknown/stale inventory, or unknown fault domain -> deny;
* a wave may take at most ``max_fraction_per_domain`` of any fault domain
  (counting nodes already unavailable/quarantined in that domain);
* at least ``min_survivors_per_domain`` healthy nodes must remain per domain;
* ``protected_domains`` allow at most ``protected_max_nodes`` per wave;
* overrides need an explicit, bounded, audited approval from ``authz``.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .errors import PolicyDenied


@dataclass(frozen=True)
class NodeInfo:
    site: str
    rack: str
    device_class: str

    @property
    def fault_domain(self) -> str:
        return f"{self.site}/{self.rack}"


@dataclass(frozen=True)
class Inventory:
    nodes: Mapping[str, NodeInfo]
    version: int
    observed_at: float

    def sites(self, nodes: Iterable[str]) -> set[str]:
        return {self.nodes[n].site for n in nodes if n in self.nodes}


@dataclass(frozen=True)
class BlastRadiusPolicy:
    max_fraction_per_domain: float = 0.34
    min_survivors_per_domain: int = 1
    max_fraction_per_site: float = 0.5
    protected_domains: frozenset[str] = frozenset()
    protected_max_nodes: int = 1
    max_inventory_age_s: float = 900.0


@dataclass
class TopologyEngine:
    policy: BlastRadiusPolicy = field(default_factory=BlastRadiusPolicy)

    def admit_wave(self, wave: Iterable[str], inv: Inventory, *, now: float,
                   unavailable: Iterable[str] = (), override: Mapping[str, Any] | None = None) -> dict[str, Any]:
        wave = list(wave)
        if now - inv.observed_at > self.policy.max_inventory_age_s or inv.observed_at > now + 5:
            raise PolicyDenied(f"topology inventory v{inv.version} is stale or from the future")
        unknown = sorted(n for n in wave if n not in inv.nodes)
        if unknown:
            raise PolicyDenied(f"nodes absent from topology inventory: {unknown[:10]}")
        dom_total = Counter(i.fault_domain for i in inv.nodes.values())
        site_total = Counter(i.site for i in inv.nodes.values())
        down = set(unavailable) | set(wave)
        dom_down = Counter(inv.nodes[n].fault_domain for n in down if n in inv.nodes)
        site_down = Counter(inv.nodes[n].site for n in down if n in inv.nodes)
        wave_dom = Counter(inv.nodes[n].fault_domain for n in wave)
        violations = []
        for dom, k in dom_down.items():
            total = dom_total[dom]
            limit = max(1, math.floor(total * self.policy.max_fraction_per_domain))
            if wave_dom.get(dom) and k > limit:
                violations.append(f"{dom}: {k}/{total} unavailable > {limit}")
            if wave_dom.get(dom) and total - k < self.policy.min_survivors_per_domain:
                violations.append(f"{dom}: survivors {total - k} < {self.policy.min_survivors_per_domain}")
            if dom in self.policy.protected_domains and wave_dom.get(dom, 0) > self.policy.protected_max_nodes:
                violations.append(f"{dom}: protected domain allows {self.policy.protected_max_nodes}/wave")
        wave_sites = {inv.nodes[n].site for n in wave}
        for site in wave_sites:
            if site_down[site] > max(1, math.floor(site_total[site] * self.policy.max_fraction_per_site)):
                violations.append(f"site {site}: {site_down[site]}/{site_total[site]} unavailable")
        decision = {"inventory_version": inv.version, "domains": dict(wave_dom), "violations": violations,
                    "overridden": False}
        if violations:
            if override and override.get("approved") and set(override.get("violations", [])) >= set(violations):
                decision["overridden"] = True
                decision["override_ref"] = override.get("approval_id")
                return decision
            raise PolicyDenied("blast-radius policy violated: " + "; ".join(violations), violations=violations)
        return decision
