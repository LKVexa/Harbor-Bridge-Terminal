"""GAP02-MC-35 — Operator explain view: why is capability X in state S?"""
from __future__ import annotations

from .errors import Code, RUNBOOK
from .sweep import Snapshot


def explain(snap: Snapshot | None, capability: str) -> dict:
    if snap is None:
        return {"capability": capability, "state": "unprobed", "why": "no sweep published yet"}
    state = snap.report.state(capability)
    evs = [e for e in snap.evidence if e["capability"] == capability]
    out = {"capability": capability, "state": state, "generation": snap.generation,
           "sequence": snap.sequence, "evidence": evs}
    if state == "present":
        out["why"] = f"proven by {evs[-1]['kind']} from {evs[-1]['source']}" if evs else "?"
    elif state == "absent":
        out["why"] = f"proven absent by {evs[-1]['source']}" if evs else "?"
    else:
        code = evs[-1]["error"] if evs and evs[-1]["error"] else None
        if evs and not code:
            out["why"] = f"evidence kind {evs[-1]['kind']!r} cannot promote to present"
        else:
            code = code or Code.TIMEOUT.value
            name = next((c for c in Code if c.value == code), Code.INTERNAL)
            out["why"] = f"{code} {name.name}"
            out["runbook"] = RUNBOOK[name]
    return out
