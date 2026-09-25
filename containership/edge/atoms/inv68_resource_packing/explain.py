"""Operator explain view (INV-68 MC-27; C077, C078).

Turns a :class:`~inv68_resource_packing.packing.PackingResult` into a
``PK_PACK_EXPLAIN/1`` document an operator can read without the code:

* per workload -- placed/unplaced, host, the reason code, its share of the
  host's *effective* limits, and for refusals which dimension(s) exceeded the
  effective limit and by how much;
* per host -- effective limits, used, remaining, utilisation, the binding
  (tightest) dimension;
* policy and lineage -- config version/digest, headroom, CPU overcommit,
  capacity snapshot, efficiency against the lower bound, and caller-supplied
  lineage (application release, infrastructure/topology identifiers) passed
  through redaction and length caps so it can be correlated with the release
  and infrastructure graph.

:func:`render_text` prints the same content as a fixed-width table for
incident notes.
"""
from __future__ import annotations

from typing import Any, Mapping

from .packing import PackingResult
from .redaction import redact

EXPLAIN_SCHEMA = "PK_PACK_EXPLAIN/1"
_LINEAGE_KEYS = ("app_release", "release_id", "commit", "infrastructure_graph", "cluster", "site", "topology",
                 "change_ref", "pipeline_run")


def _version() -> str:
    from . import __version__
    return __version__


def _lineage(raw: Any) -> dict:
    if not isinstance(raw, Mapping):
        return {}
    return {k: str(redact(raw[k]))[:256] for k in _LINEAGE_KEYS if k in raw}


def explain(result: PackingResult, *, config: Mapping[str, Any] | None = None,
            capacity: Mapping[str, float] | None = None, lower_bound_hosts: int | None = None,
            lineage: Mapping[str, Any] | None = None, tenant: str | None = None,
            capacity_source: Mapping[str, Any] | None = None) -> dict:
    eff = {"cpu": (capacity or {}).get("effective_cpu"), "mem": (capacity or {}).get("effective_mem")}
    hosts = []
    for h in result.hosts:
        row = {"host": h.name, "effective": dict(eff), "used": dict(h.used)}
        if eff["cpu"] and eff["mem"]:
            util = {d: round(h.used[d] / eff[d], 4) for d in ("cpu", "mem")}
            row["utilisation"] = util
            row["remaining"] = {d: round(eff[d] - h.used[d], 6) for d in ("cpu", "mem")}
            row["binding_dimension"] = max(util, key=lambda d: (util[d], d))
        hosts.append(row)
    decisions = []
    for d in result.decisions:
        row = {"workload": d.workload, "status": d.status, "host": d.host, "reason": d.reason,
               "request": {"cpu": d.cpu, "mem": d.mem}}
        if eff["cpu"] and eff["mem"]:
            row["share_of_effective"] = {"cpu": round(d.cpu / eff["cpu"], 4), "mem": round(d.mem / eff["mem"], 4)}
            if d.status == "unplaced":
                row["rejected_constraints"] = [
                    {"dimension": dim, "request": req, "effective_limit": eff[dim], "excess": round(req - eff[dim], 6)}
                    for dim, req in (("cpu", d.cpu), ("mem", d.mem)) if req > eff[dim]
                ]
        decisions.append(row)
    hosts_used = len(result.hosts)
    return {
        "schema": EXPLAIN_SCHEMA,
        "tenant": tenant,
        "policy": {
            "config": dict(config or {}),
            "component_version": _version(),
            "headroom": (capacity or {}).get("headroom"),
            "effective_limits": eff,
            "memory_overcommit": 1.0,
            "capacity_snapshot": dict(capacity_source or {}),
        },
        "summary": {
            "workloads": len(result.decisions),
            "placed": len(result.assignments),
            "unplaced": len(result.unplaced),
            "hosts_used": hosts_used,
            "lower_bound": lower_bound_hosts,
            "efficiency_ratio": round(hosts_used / lower_bound_hosts, 4) if lower_bound_hosts else None,
        },
        "lineage": _lineage(lineage),
        "hosts": hosts,
        "decisions": decisions,
    }


def render_text(doc: Mapping[str, Any]) -> str:
    s = doc["summary"]
    lines = [
        f"INV-68 explain  tenant={doc.get('tenant')}  config={doc['policy']['config'].get('config_version')}"
        f" ({str(doc['policy']['config'].get('config_digest', ''))[:12]})",
        f"placed {s['placed']}/{s['workloads']}  unplaced {s['unplaced']}  hosts {s['hosts_used']}"
        f"  lower-bound {s['lower_bound']}  ratio {s['efficiency_ratio']}",
        f"{'workload':<24} {'status':<9} {'host':<6} {'cpu':>8} {'mem':>8}  reason",
    ]
    for d in doc["decisions"]:
        lines.append(f"{d['workload'][:24]:<24} {d['status']:<9} {str(d['host'] or '-'):<6} "
                     f"{d['request']['cpu']:>8g} {d['request']['mem']:>8g}  {d['reason']}")
        for rc in d.get("rejected_constraints", []):
            lines.append(f"{'':<24}   exceeds {rc['dimension']} limit {rc['effective_limit']:g} by {rc['excess']:g}")
    return "\n".join(lines) + "\n"
