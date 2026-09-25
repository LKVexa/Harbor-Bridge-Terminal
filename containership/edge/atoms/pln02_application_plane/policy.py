"""MC-07 / MC-12 / MC-28 - Entitlements, constraint precedence, explainable selection.

Precedence (highest first) is fixed and versioned::

    security > residency > consistency > slo > locality > cost

The first four are *hard* filters; locality and cost are *soft* rankers and can
never admit a candidate that a hard constraint rejected. Constraints may come
from three sources, ``platform > tenant > application``; for hard constraints
a lower source may only *narrow* a higher one - a contradiction is refused as
``POLICY_CONFLICT`` instead of silently merged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .errors import PlaneError

PRECEDENCE = ("security", "residency", "consistency", "slo", "locality", "cost")
POLICY_VERSION = "PLN02-POLICY/1"
TIER_ORDER = {"standard": 0, "hardened": 1, "confidential": 2}
CONSISTENCY_ORDER = {"eventual": 0, "bounded": 1, "strong": 2}


@dataclass(frozen=True)
class Constraints:
    min_tier: str | None = None          # security
    residency: frozenset[str] | None = None  # allowed regions
    min_consistency: str | None = None
    max_slo_ms: int | None = None
    prefer_region: str | None = None     # locality (soft)
    optimise_cost: bool = True           # cost (soft)

    @staticmethod
    def from_doc(doc: Mapping[str, Any] | None) -> "Constraints":
        doc = dict(doc or {})
        allowed = {"min_tier", "residency", "min_consistency", "max_slo_ms", "prefer_region", "optimise_cost"}
        if set(doc) - allowed:
            raise PlaneError("unknown constraint", code="POLICY_CONFLICT",
                             details={"constraint": sorted(set(doc) - allowed)[0], "reason": "unknown"})
        if doc.get("min_tier") is not None and doc["min_tier"] not in TIER_ORDER:
            raise PlaneError("unknown tier", code="POLICY_CONFLICT", details={"constraint": "security", "reason": "unknown_tier"})
        if doc.get("min_consistency") is not None and doc["min_consistency"] not in CONSISTENCY_ORDER:
            raise PlaneError("unknown consistency", code="POLICY_CONFLICT", details={"constraint": "consistency", "reason": "unknown"})
        res = doc.get("residency")
        return Constraints(doc.get("min_tier"), frozenset(res) if res is not None else None, doc.get("min_consistency"),
                           doc.get("max_slo_ms"), doc.get("prefer_region"), bool(doc.get("optimise_cost", True)))


def merge(platform: Constraints, tenant: Constraints, application: Constraints, capability: str = "*") -> Constraints:
    """Merge by precedence of source. Lower sources may narrow, never widen or contradict."""
    out = platform
    for layer in (tenant, application):
        # security / consistency: take the stricter
        tier = out.min_tier
        if layer.min_tier is not None:
            tier = layer.min_tier if tier is None or TIER_ORDER[layer.min_tier] >= TIER_ORDER[tier] else tier
        cons = out.min_consistency
        if layer.min_consistency is not None:
            cons = (layer.min_consistency if cons is None
                    or CONSISTENCY_ORDER[layer.min_consistency] >= CONSISTENCY_ORDER[cons] else cons)
        # residency: intersection; empty intersection is a conflict, not "anywhere"
        res = out.residency
        if layer.residency is not None:
            res = layer.residency if res is None else (res & layer.residency)
            if not res:
                raise PlaneError("residency constraints contradict", code="POLICY_CONFLICT",
                                 details={"capability": capability, "constraint": "residency", "reason": "empty_intersection"})
        slo = out.max_slo_ms
        if layer.max_slo_ms is not None:
            slo = layer.max_slo_ms if slo is None else min(slo, layer.max_slo_ms)
        out = Constraints(tier, res, cons, slo, layer.prefer_region or out.prefer_region,
                          layer.optimise_cost and out.optimise_cost)
    return out


def _hard_reject(c: Mapping[str, Any], k: Constraints) -> str | None:
    if not c.get("healthy", False):
        return "unhealthy"
    if k.min_tier is not None and TIER_ORDER.get(c["tier"], -1) < TIER_ORDER[k.min_tier]:
        return "security"
    if k.residency is not None and not set(c["residency"]) <= k.residency:
        return "residency"
    if k.min_consistency is not None and CONSISTENCY_ORDER.get(c["consistency"], -1) < CONSISTENCY_ORDER[k.min_consistency]:
        return "consistency"
    if k.max_slo_ms is not None and c["slo_ms"] > k.max_slo_ms:
        return "slo"
    return None


def select(capability: str, candidates: Iterable[Mapping[str, Any]], k: Constraints) -> tuple[str, dict]:
    """Deterministically pick a provider and return (provider_id, explain_record)."""
    rejected, eligible = [], []
    for c in candidates:
        reason = _hard_reject(c, k)
        (rejected.append({"id": c["id"], "reason": reason}) if reason else eligible.append(c))
    rejected.sort(key=lambda r: r["id"])
    if not eligible:
        raise PlaneError(f"no eligible provider for {capability}", code="NO_ELIGIBLE_PROVIDER",
                         details={"capability": capability, "rejected": [f"{r['id']}:{r['reason']}" for r in rejected]})

    def rank(c: Mapping[str, Any]) -> tuple:
        locality = 0 if k.prefer_region and c["region"] == k.prefer_region else 1
        cost = c["cost"] if k.optimise_cost else 0
        return (locality, cost, c["latency_ms"], c["id"])  # id = deterministic tie-break
    eligible.sort(key=rank)
    chosen = eligible[0]
    return chosen["id"], {
        "capability": capability, "chosen": chosen["id"], "policy_version": POLICY_VERSION,
        "precedence": list(PRECEDENCE), "rank_key": list(rank(chosen)[:3]),
        "eligible": [c["id"] for c in eligible], "rejected": rejected,
    }


# ----------------------------------------------------------------- MC-12
@dataclass
class EntitlementPolicy:
    """tenant -> capabilities the tenant may request; role gates for admin actions."""
    grants: dict[str, frozenset[str]] = field(default_factory=dict)
    admin_roles: frozenset[str] = frozenset({"plane-admin"})
    resolve_roles: frozenset[str] = frozenset({"app-deployer", "plane-admin"})
    version: str = "ENTITLEMENTS/1"

    def authorize_resolve(self, principal: Any, tenant: str, components: Iterable[Mapping[str, Any]]) -> None:
        if principal.tenant != tenant:
            raise PlaneError("principal not in tenant", code="PERMISSION_DENIED", details={"reason": "cross_tenant"})
        if not set(principal.roles) & self.resolve_roles:
            raise PlaneError("role may not resolve", code="PERMISSION_DENIED", details={"reason": "role"})
        allowed = self.grants.get(tenant, frozenset())
        for comp in components:
            for cap in (comp.get("requires") or {}):
                if cap not in allowed:
                    raise PlaneError(f"tenant not entitled to {cap}", code="PERMISSION_DENIED",
                                     details={"capability": cap, "reason": "not_entitled"})

    def authorize_admin(self, principal: Any) -> None:
        if not set(principal.roles) & self.admin_roles:
            raise PlaneError("admin role required", code="PERMISSION_DENIED", details={"reason": "role"})
