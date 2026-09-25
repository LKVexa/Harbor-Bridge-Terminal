"""Operator-readable explain view (C076, C077, C078).

Renders one retained decision: what was asked, what was effectively evaluated after policy, which
inventory generation and config generation were used, every device-level reason code, the selection
rationale, and the release lineage.  Tenant names appear only as the caller supplied them to an operator
holding ``accel.read``; secrets never appear (inputs pass through ``redact``).
"""
from __future__ import annotations

from .errors import REGISTRY
from .redaction import redact


def render(rec: dict) -> str:
    d = rec["decision"]
    req = redact(rec["request"])
    eff = redact(rec["effective"])
    inv = rec["inventory"]
    lines = [
        f"DECISION {d['decision_id']}  outcome={d['outcome']}  code={d['code'] or '-'}",
        f"  principal        : {rec['principal']}",
        f"  requested        : {req}",
        f"  evaluated as     : {eff}",
        f"  inventory        : generation={inv.get('generation')} source={inv.get('source')} "
        f"state={inv.get('state')} age_s={None if inv.get('age_s') is None else round(inv['age_s'], 1)} "
        f"devices={inv.get('devices')}",
        f"  configuration    : generation={d['config_generation']} digest={rec['config_digest'][:16]}…",
        f"  tenant quota     : {rec['quota']} device(s)",
        f"  selected         : {d['selected'] or 'none'}   reservation={d['reservation_id'] or '-'}",
        "  rationale        :",
    ]
    lines += [f"    - {r}" for r in d["rationale"]] or ["    - (none)"]
    lines.append("  device reasons   :")
    for r in d["reasons"]:
        lines.append(f"    - [{r['code']}] ({REGISTRY[r['code']].outcome}) {r['text']}")
    if not d["reasons"]:
        lines.append("    - (none)")
    if d["degraded"]:
        lines.append(f"  DEGRADED         : {', '.join(d['degraded'])}")
    lin = rec.get("lineage", {})
    lines.append(f"  lineage          : component={lin.get('component_version')} "
                 f"manifest={str(lin.get('release_manifest_sha256'))[:16]} workload_release={lin.get('workload_release')}")
    lines.append(f"  trace            : {d['trace_id']}")
    return "\n".join(lines) + "\n"
