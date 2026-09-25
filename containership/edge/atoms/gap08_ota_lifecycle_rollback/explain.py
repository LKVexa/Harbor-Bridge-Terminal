"""Operator explain view (component 23).

Answers, from the durable state + sealed audit trail alone: why each gate
passed or failed and on what evidence, which topology constraints applied,
why nodes are deferred or quarantined, who did what, and whether the local
history is fully sealed externally.  Output is redacted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .secrets_boundary import redact


def _ts(t: float | None) -> str:
    return "-" if t is None else datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def explain(state: Mapping[str, Any]) -> dict[str, Any]:
    core = state["core"]
    gates, policy, operator, other = [], [], [], []
    for ev in core["audit_log"]:
        p = ev.get("payload", {})
        kind = ev["event"]
        if kind in ("wave_gate", "deferred_gate"):
            e = p.get("evidence") or {}
            gates.append({"seq": ev["sequence"], "gate": p.get("gate_id"), "healthy": p.get("healthy"),
                          "touched": p.get("touched"), "deferred": p.get("deferred"),
                          "evidence_id": e.get("evidence_id"), "evidence_source": e.get("source"),
                          "evidence_detail": e.get("detail"), "install_failures": e.get("install_failures"),
                          "unknown_outcomes": e.get("unknown_outcomes"),
                          "why": ("health evidence verdict healthy with required coverage" if p.get("healthy") else
                                  "gate failed: " + (e.get("detail") or e.get("reason") or "operator/installation"))})
        elif kind == "policy_admitted":
            policy.append({"seq": ev["sequence"], "nodes": p.get("nodes"), "topology": p.get("topology"),
                           "by": p.get("by")})
        elif kind in ("paused", "resumed", "cancelled", "abandoned", "quarantine_released", "rollback"):
            operator.append({"seq": ev["sequence"], "event": kind, **{k: v for k, v in p.items()
                                                                    if k in ("by", "reason", "node", "approver",
                                                                             "failed", "reverted")}})
        else:
            other.append({"seq": ev["sequence"], "event": kind})
    dq = state.get("deferred_queue", {})
    deferred = {n: {"reason": e["last_reason"], "attempts": e["attempts"], "status": e["status"],
                    "next_attempt": _ts(e["next_attempt_at"]), "expires": _ts(e["expires_at"])} for n, e in dq.items()}
    quarantine = {n: q for n, q in state.get("quarantine", {}).items()}
    sealed = state.get("sealed_count", 0)
    return redact({
        "rollout_id": state["rollout_id"], "phase": state["phase"], "paused": state.get("paused"),
        "bundle": core["bundle"], "pinned_target": core["pinned_target"],
        "artifact_digest": state.get("artifact", {}).get("digest"),
        "progress": f"wave {core['wave_index']}/{len(core['waves'])}",
        "gates": gates, "policy_decisions": policy, "operator_actions": operator, "deferred": deferred,
        "quarantine": quarantine, "needs_reconcile": state.get("needs_reconcile", []),
        "audit": {"local_events": len(core["audit_log"]), "sealed": sealed,
                  "fully_sealed": sealed == len(core["audit_log"]), "head": state.get("audit_head")},
    })


def render_text(view: Mapping[str, Any]) -> str:
    lines = [f"Rollout {view['rollout_id']}  {view['bundle']} (rollback target {view['pinned_target']})",
             f"Phase: {view['phase']}{' [PAUSED]' if view['paused'] else ''}   Progress: {view['progress']}",
             f"Audit: {view['audit']['sealed']}/{view['audit']['local_events']} events sealed externally"]
    for g in view["gates"]:
        lines.append(f"  gate {g['gate']}: {'PASS' if g['healthy'] else 'FAIL'} - {g['why']}; touched={g['touched']}")
    for n, d in sorted(view["deferred"].items()):
        lines.append(f"  deferred {n}: {d['reason']} (attempts {d['attempts']}, {d['status']})")
    for n, q in sorted(view["quarantine"].items()):
        lines.append(f"  quarantine {n}: {q.get('reason')} [{q.get('status')}]")
    if view["needs_reconcile"]:
        lines.append(f"  needs reconciliation: {view['needs_reconcile']}")
    return "\n".join(lines)
