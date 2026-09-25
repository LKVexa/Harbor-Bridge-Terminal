"""Component 09 - deployment topology validator (PK_DYN_TOPOLOGY/1).

Rules enforced (see docs/09_topology.md):
  T1 every instance's service is allowed on its site's tier
  T2 a site hosting a lease_store spans >= the tier's min_failure_domains
  T3 per tenant per site at most one pool_controller (no global singleton, no
     split brain inside a site); instances must name a failure domain of the site
  T4 far-edge sites without a local lease_store must name an upstream site that
     hosts one for the same tenant
  T5 tenants never share a lease_store instance (one lease_store per tenant/site)
  T6 shared services must declare their tenant isolation mechanism
  T7 every dependency declares plane (control|data), interface and on_failure
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

PATH = Path(__file__).resolve().parent / "topology.json"


def load(path: Path = PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(doc: dict) -> list[str]:
    p: list[str] = []
    tiers = doc.get("tiers", {})
    sites = {s["id"]: s for s in doc.get("sites", [])}
    for sid, s in sites.items():
        tier = tiers.get(s.get("tier"))
        if tier is None:
            p.append(f"T1 {sid}: unknown tier {s.get('tier')}")
            continue
        fds = set(s.get("failure_domains", []))
        ctrl = Counter()
        stores = Counter()
        for inst in s.get("instances", []):
            if inst["service"] not in tier["allowed"]:
                p.append(f"T1 {sid}: {inst['service']} not allowed on {s['tier']}")
            if inst.get("failure_domain") not in fds:
                p.append(f"T3 {sid}: instance {inst['service']} has unknown failure domain")
            if inst["service"] == "pool_controller":
                ctrl[inst.get("tenant")] += 1
            if inst["service"] == "lease_store":
                stores[inst.get("tenant")] += 1
                if not inst.get("tenant"):
                    p.append(f"T5 {sid}: lease_store without tenant (shared store forbidden)")
        if stores and len(fds) < tier.get("min_failure_domains", 1):
            p.append(f"T2 {sid}: lease_store needs >= {tier['min_failure_domains']} failure domains")
        for t, n in ctrl.items():
            if n > 1:
                p.append(f"T3 {sid}: {n} pool_controllers for tenant {t}")
        for t, n in stores.items():
            if n > 1:
                p.append(f"T5 {sid}: {n} lease_stores for tenant {t}")
        if tier.get("requires_upstream_lease_store"):
            for t in ctrl:
                if stores.get(t):
                    continue
                up = sites.get(s.get("upstream", ""))
                if not up or not any(i["service"] == "lease_store" and i.get("tenant") == t
                                     for i in up.get("instances", [])):
                    p.append(f"T4 {sid}: tenant {t} has no upstream lease_store")
    for sh in doc.get("shared_services", []):
        if not sh.get("tenant_isolation"):
            p.append(f"T6 shared {sh.get('service')} lacks tenant_isolation")
    for d in doc.get("dependencies", []):
        if d.get("plane") not in {"control", "data"} or not d.get("interface") or not d.get("on_failure"):
            p.append(f"T7 dependency {d.get('from')}->{d.get('to')} incomplete")
    return p
