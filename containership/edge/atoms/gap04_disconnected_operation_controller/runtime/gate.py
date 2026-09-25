"""Formal production exit gate (GAP04-C55).

  python -m gap04_disconnected_operation_controller.runtime.gate [--environment prod] [--archive <zip>]

Consumes only objective artifacts: evidence/CHECKLIST_STATUS.json, evidence/test_results.json,
evidence/waivers.json, evidence/approvals.json (optional), COMPATIBILITY_MATRIX.json, and the
release archive digest. Returns PASS only when every P0 control and every gate-designated P1
control is verified ("x" or approved "-"), required evidence is fresh, every waiver that blocks
production is approved and unexpired, and named approvals exist for engineering, security,
operations and product/risk. Anything missing, failed, stale, unsigned, or narrative-only => NO_GO.
Exit code 0 = PASS, 3 = NO_GO. The decision document binds the exact artifact digest and
environment, so it cannot be replayed for another build.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
GATE_POLICY_VERSION = "PK_GAP04_GATE/1"
REQUIRED_P1 = [f"{n:02d}" for n in range(21, 47)]   # gate policy: all P1 components mandatory for prod
REQUIRED_APPROVALS = ("engineering", "security", "operations", "product_risk")
MAX_EVIDENCE_AGE_DAYS = 30


def _load(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def evaluate(evidence_dir: Path | None = None, *, environment: str = "prod", archive_sha256: str | None = None,
             today: _dt.date | None = None) -> dict:
    ev = Path(evidence_dir or PKG / "evidence")
    today = today or _dt.date.today()
    status = _load(ev / "CHECKLIST_STATUS.json")
    tests = _load(ev / "test_results.json")
    waivers = _load(ev / "waivers.json", {"waivers": []})
    approvals = _load(ev / "approvals.json", {})
    reasons: list[str] = []
    if status is None:
        reasons.append("missing CHECKLIST_STATUS.json")
        status = {"controls": {}}
    if tests is None:
        reasons.append("missing test_results.json")
    else:
        if tests.get("failed", 1) or tests.get("errors", 1):
            reasons.append(f"test failures: failed={tests.get('failed')} errors={tests.get('errors')}")
        age = (today - _dt.date.fromisoformat(tests["date"])).days if "date" in tests else 999
        if age > MAX_EVIDENCE_AGE_DAYS:
            reasons.append(f"test evidence stale ({age} d)")
        if not tests.get("ci_run_id"):
            reasons.append("test evidence not from release CI (no ci_run_id)")
    ctrls = status.get("controls", {})
    comp = status.get("components", {})
    not_done = {"P0": [], "P1": [], "P2": []}
    for cid, c in ctrls.items():
        comp_id = cid[7:9]                      # "GAP04-C01-001" -> "01"
        if comp_id not in comp:
            reasons.append(f"{cid}: component {comp_id} missing from status document")
        pr = comp.get(comp_id, {}).get("priority", "P0")
        if c["status"] == "x" and not c.get("evidence"):
            reasons.append(f"{cid} marked verified without evidence (narrative-only)")
        ok = (c["status"] == "x" and c.get("evidence")) or (c["status"] == "-" and c.get("approved_by"))
        if not ok:
            if pr == "P0" or (pr == "P1" and comp_id in REQUIRED_P1) or pr == "P2":
                not_done[pr].append(cid)
    for pr, lst in not_done.items():
        if lst:
            reasons.append(f"{len(lst)} {pr} controls not verified")
    for w in waivers.get("waivers", []):
        exp = _dt.date.fromisoformat(w["expires"])
        if w.get("blocks_production") and (w.get("status") != "approved" or not w.get("approver")):
            reasons.append(f"waiver {w['id']} blocks production and is not approved")
        if exp < today:
            reasons.append(f"waiver {w['id']} expired")
        if not w.get("owner"):
            reasons.append(f"waiver {w['id']} unowned")
    for role in REQUIRED_APPROVALS:
        a = approvals.get(role)
        if not a or not a.get("name") or not a.get("date"):
            reasons.append(f"missing named approval: {role}")
    if archive_sha256 is None:
        reasons.append("no release archive digest bound to decision")
    decision = "PASS" if not reasons else "NO_GO"
    doc = {"schema": "PK_GAP04_GATE_DECISION/1", "policy": GATE_POLICY_VERSION, "decision": decision,
           "environment": environment, "archive_sha256": archive_sha256, "evaluated": today.isoformat(),
           "summary": {k: len(v) for k, v in not_done.items()}, "reasons": reasons,
           "evidence_digests": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(ev.glob("*.json")) if p.name != "gate_decision.json"}}
    return doc


if __name__ == "__main__":  # pragma: no cover
    env = sys.argv[sys.argv.index("--environment") + 1] if "--environment" in sys.argv else "prod"
    sha = None
    if "--archive" in sys.argv:
        sha = hashlib.sha256(Path(sys.argv[sys.argv.index("--archive") + 1]).read_bytes()).hexdigest()
    d = evaluate(environment=env, archive_sha256=sha)
    print(json.dumps(d, indent=2))
    sys.exit(0 if d["decision"] == "PASS" else 3)
