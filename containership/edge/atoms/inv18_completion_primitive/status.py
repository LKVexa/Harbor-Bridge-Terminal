"""Structured status and operator explain view (C071, C077, C078)."""
from __future__ import annotations

import json
import pathlib
from typing import Any

from .runtime import POLICY_VERSION, Runtime
from .wire import SUPPORTED_MAJORS

PKG = pathlib.Path(__file__).resolve().parent
CAPABILITIES = ["future", "resolve", "resolve_error", "abandon", "cancel", "take", "wait", "inspect",
                "capabilities", "quotas", "disable", "wire-adapter"]


def lineage() -> dict:
    p = PKG / "conformance" / "LINEAGE.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except ValueError:
            return {"error": "unreadable lineage"}
    return {}


def status(rt: Runtime) -> dict:
    h = rt.health()
    c = rt.config.values()
    return {
        "schema": "PK_FUTURE_STATUS/1", "component": "INV-18", "version": rt.version,
        "state": h["state"], "ready": h["ready"], "reasons": h["reasons"],
        "config_revision": rt.config.active().revision_id,
        "contract_versions": [f"PK_FUTURE/{m}" for m in SUPPORTED_MAJORS],
        "capabilities": CAPABILITIES, "dependencies": h["dependencies"],
        "limits": {k: c[k] for k in ("max_outstanding", "soft_outstanding", "max_per_tenant",
                                     "max_payload_bytes", "max_id_len", "stall_threshold_s")},
        "policy_version": POLICY_VERSION, "lineage": lineage(), "outstanding": h["outstanding"],
        "recent_decisions": rt.decisions.summary(),
    }


def explain(rt: Runtime) -> str:
    s = status(rt)
    h = rt.health()
    rev = rt.config.active()
    lines = [
        f"INV-18 Completion primitive {s['version']}  state={s['state']} ready={s['ready']}",
        f"  config revision : {rev.revision_id} (env={rev.environment}, author={rev.author}, "
        f"approver={rev.approver or 'none'}, rollback_of={rev.rollback_of or '-'})",
        f"  policy          : {s['policy_version']}",
        f"  outstanding     : {h['outstanding']} (pending {h['pending']}, stalled {h['stalled']}, "
        f"oldest pending {h['pending_age_max_s']:.3f}s)",
        "  limits          : " + ", ".join(f"{k}={v}" for k, v in s["limits"].items()),
        "  dependencies    : " + ", ".join(f"{k}={v}" for k, v in s["dependencies"].items()),
    ]
    if s["reasons"]:
        lines.append("  WHY NOT HEALTHY : " + "; ".join(s["reasons"]))
        for r in s["reasons"]:
            lines.append("     -> " + _ADVICE.get(r.split(":")[0], "see docs/OPERATIONS.md"))
    rej = {c["labels"].get("code"): c["value"] for c in rt.metrics.snapshot()["counters"]
           if c["name"] == "inv18_rejections_total"}
    if rej:
        lines.append("  recent rejections by code: " + ", ".join(f"{k}={int(v)}" for k, v in sorted(rej.items())))
    if s["recent_decisions"]:
        lines.append("  automated decisions: " + ", ".join(f"{k}={v}" for k, v in sorted(s["recent_decisions"].items())))
    lines.append(f"  audit head      : {rt.audit.head[:16]} ({len(rt.audit.events)} events)")
    lin = s["lineage"]
    if lin:
        lines.append(f"  lineage         : release={lin.get('release_id')} digest={str(lin.get('artifact_digest'))[:16]}")
    return "\n".join(lines)


_ADVICE = {
    "INVARIANT_VIOLATION": "SEV1: freeze the component (runbook INC-1) and preserve the audit chain",
    "DISABLED": "component/tenant quarantined by an operator; see audit 'component.disable' for reason",
    "SOFT_LIMIT_EXCEEDED": "capacity warning: review workload or raise limits via reviewed config (RB-D2-4)",
    "STALLED_FUTURES": "many producers are slow: application delay, not primitive malfunction (RB-D2-2)",
    "TELEMETRY_SINK_UNAVAILABLE": "noncritical: core correctness unaffected; restore log sink (RB-D2-2)",
}


def to_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)
