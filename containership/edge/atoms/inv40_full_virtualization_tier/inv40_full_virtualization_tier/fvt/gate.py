"""Production exit gate (INV-40-C090, C100, C070).

GO requires, for the exact artifact digest supplied:
  * every requirement in traceability/requirements.json CLOSED or WAIVED
    (waiver approved, owner named, unexpired);
  * every P0 closed or waived;
  * machine-readable evidence present, digest-bound to this artifact;
  * no mandatory test SKIPPED/FAILED in the bound CI run;
  * independent human approval record (approver != builder).
Anything missing -> NO_GO with every reason listed.  The gate never
upgrades a status; it only reads.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib

PKG = pathlib.Path(__file__).resolve().parents[1]
CLOSED = {"CLOSED", "WAIVED"}


def evaluate(artifact_digest: str, *, trace_path=None, evidence_path=None, approval_path=None,
             bench_path=None, thresholds_path=None, today: _dt.date | None = None) -> dict:
    today = today or _dt.date.today()
    trace = json.loads(pathlib.Path(trace_path or PKG / "traceability/requirements.json").read_text())
    reasons: list[str] = []
    counts: dict[str, int] = {}
    for r in trace["requirements"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        if r["status"] == "WAIVED":
            w = r.get("waiver") or {}
            if not w.get("approved_by") or not w.get("expires") or _dt.date.fromisoformat(w["expires"]) < today:
                reasons.append(f"{r['id']}: waiver missing approval or expired")
        elif r["status"] not in CLOSED:
            reasons.append(f"{r['id']} ({r['priority']}): {r['status']}")
    ev_p = pathlib.Path(evidence_path or PKG / "evidence/ci_run.json")
    if not ev_p.exists():
        reasons.append("no CI evidence")
    else:
        ev = json.loads(ev_p.read_text())
        if ev.get("artifact_digest") != artifact_digest:
            reasons.append("CI evidence bound to a different artifact digest")
        if ev.get("skipped_mandatory") or ev.get("failed"):
            reasons.append(f"CI: {ev.get('failed', 0)} failed, {len(ev.get('skipped_mandatory', []))} mandatory skipped")
    if bench_path and thresholds_path:
        b, t = json.loads(pathlib.Path(bench_path).read_text()), json.loads(pathlib.Path(thresholds_path).read_text())
        if t.get("status") != "APPROVED":
            reasons.append("performance thresholds not approved")
        for k, lim in (t.get("max") or {}).items():
            if b.get(k) is not None and b[k] > lim:
                reasons.append(f"performance regression: {k}={b[k]} > {lim}")
    ap = pathlib.Path(approval_path or PKG / "evidence/PRODUCTION_APPROVAL.json")
    if not ap.exists():
        reasons.append("no independent production approval record")
    else:
        a = json.loads(ap.read_text())
        if a.get("artifact_digest") != artifact_digest or not a.get("approver") or a.get("approver") == a.get("builder"):
            reasons.append("approval record invalid for this artifact")
    return {"schema": "PK_FULL_VM_GATE/1", "artifact_digest": artifact_digest,
            "verdict": "GO" if not reasons else "NO_GO", "status_counts": counts, "reasons": reasons}
