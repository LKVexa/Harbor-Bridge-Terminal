"""M14/M45 - constraint precedence resolver and residency-aware failover.

Precedence (policy inv60-precedence/1.0.0), hard constraints first, in order:
  1 security   (host attested/active, not quarantined)
  2 isolation  (tenant allowed on host; dedicated hosts only for their tenant)
  3 residency  (host region in component's allowed regions)
  4 capacity   (host below its component ceiling minus reserve)
  5 anti_affinity (hard: replica of same app not already on host)
Soft (optimised, lexicographic): 6 slo (lower latency class), 7 cost (lower cost),
then deterministic tie-break by host id. No eligible host -> NO_ELIGIBLE_TARGET
(fail closed). Emergency override may relax only 'capacity' and requires a
break-glass decision id; it is recorded. Every rule evaluated is recorded.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import FabricError

PRECEDENCE_VERSION = "inv60-precedence/1.0.0"
HARD = ("security", "isolation", "residency", "capacity", "anti_affinity")
SOFT = ("slo", "cost")
RELAXABLE = {"capacity"}


@dataclass
class HostInfo:
    id: str
    region: str = "default"
    state: str = "active"
    attested: bool = True
    dedicated_tenant: str | None = None
    capacity: int = 64
    reserve: int = 0
    latency_class: int = 1
    cost: float = 1.0
    placed: list = field(default_factory=list)   # (tenant, app, component)


@dataclass
class Request:
    component: str
    tenant: str
    app: str = ""
    regions: tuple = ()          # empty = any
    anti_affinity: bool = True


def validate_precedence(order) -> None:
    order = list(order)
    if len(set(order)) != len(order):
        raise FabricError("INVALID_ARGUMENT", "duplicate constraint in precedence")
    if set(order) != set(HARD + SOFT):
        raise FabricError("INVALID_ARGUMENT", "precedence must list every constraint exactly once")
    if any(order.index(h) > order.index(s) for h in HARD for s in SOFT):
        raise FabricError("INVALID_ARGUMENT", "a soft constraint may not precede a hard one")


def _rules(h: HostInfo, r: Request, relax: set) -> list[tuple[str, bool, str]]:
    res = []
    res.append(("security", h.state == "active" and h.attested, f"state={h.state} attested={h.attested}"))
    iso = h.dedicated_tenant in (None, r.tenant)
    res.append(("isolation", iso, f"dedicated={h.dedicated_tenant}"))
    res.append(("residency", (not r.regions) or h.region in r.regions, f"region={h.region} allowed={list(r.regions)}"))
    cap_ok = len(h.placed) < h.capacity - h.reserve
    res.append(("capacity", cap_ok or "capacity" in relax, f"placed={len(h.placed)} limit={h.capacity - h.reserve}"
                + (" RELAXED" if not cap_ok and "capacity" in relax else "")))
    aa = not (r.anti_affinity and r.app and any(t == r.tenant and a == r.app for t, a, _ in h.placed))
    res.append(("anti_affinity", aa, "no co-located replica" if aa else "replica already on host"))
    return res


def resolve(hosts: list[HostInfo], req: Request, *, relax=(), override_decision: str | None = None) -> dict:
    relax = set(relax)
    if relax - RELAXABLE:
        raise FabricError("PERMISSION_DENIED", f"constraints {sorted(relax - RELAXABLE)} are never relaxable")
    if relax and not override_decision:
        raise FabricError("PERMISSION_DENIED", "relaxing a hard constraint requires a break-glass decision id")
    evaluated, eligible = [], []
    for h in sorted(hosts, key=lambda x: x.id):
        rules = _rules(h, req, relax)
        evaluated.append({"host": h.id, "rules": [{"rule": n, "pass": ok, "reason": why} for n, ok, why in rules]})
        if all(ok for _, ok, _ in rules):
            eligible.append(h)
    record = {"policy": PRECEDENCE_VERSION, "component": req.component, "tenant": req.tenant,
              "evaluated": evaluated, "relaxed": sorted(relax), "override": override_decision}
    if not eligible:
        record["chosen"] = None
        raise FabricError("NO_ELIGIBLE_TARGET", f"no host satisfies hard constraints for {req.component}",
                          detail={"evaluated_hosts": len(evaluated)})
    chosen = min(eligible, key=lambda h: (h.latency_class, h.cost, len(h.placed), h.id))
    record["chosen"] = chosen.id
    record["tie_break"] = "latency_class, cost, load, host id"
    return record
