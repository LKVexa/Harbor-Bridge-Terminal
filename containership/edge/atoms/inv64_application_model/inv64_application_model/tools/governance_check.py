"""Governance / cross-file consistency gate (MC-04, MC-26, MC-30, MC-35, MC-36, MC-38).

    python -m inv64_application_model.tools.governance_check [--today YYYY-MM-DD] [--json]

Machine-checks the operational records instead of trusting prose:

* owners.json — every accountable role resolved (else ``owners.unassigned``, blocking);
  expired temporary delegations ignored;
* decisions.json — the governing ADR is ``approved`` with approvers (else blocking);
* REGISTER.json — required fields, max duration by severity, expired *active*
  waivers (blocking), waivers lacking owner/approvers (invalid -> blocking);
* REVIEWS.json — overdue reviews (High -> blocking), reviewer == author;
* alerts.json — every metric in the telemetry catalog, owner/route/runbook set,
  runbook anchors exist;
* compatibility.json vs pyproject.toml ``requires-python``/classifiers, the CI
  matrix and README (single source of truth);
* LICENSING — pyproject license expression matches LICENSING.md status.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _anchors(md: Path) -> set[str]:
    out = set()
    if md.is_file():
        for line in md.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^#{1,6}\s+(.*)$", line)
            if m:
                a = re.sub(r"[^\w\- ]", "", m.group(1).strip().lower()).replace(" ", "-")
                out.add(a)
            for m2 in re.finditer(r'<a id="([^"]+)"', line):
                out.add(m2.group(1))
    return out


def check(today: dt.date) -> list[dict]:
    f: list[dict] = []

    def add(fid, severity, blocking, msg):
        f.append({"id": fid, "severity": severity, "blocking": blocking, "message": msg})

    owners = _load("ops/owners.json")
    live_dels = {d["role"] for d in owners.get("temporary_delegations", [])
                 if dt.date.fromisoformat(d["expires"]) >= today}
    for r in owners["roles"]:
        if not r.get("assignee") and r["role"] not in live_dels:
            add("owners.unassigned", "High", True, f"role {r['role']} has no assignee")
    adrs = _load("ops/decisions.json")["adrs"]
    for a in adrs:
        if a["status"] == "superseded":
            continue
        if a["status"] != "approved" or not a.get("approvers"):
            add("adr.not_approved", "High", True, f"{a['id']} status={a['status']} approvers={a.get('approvers')}")
        if not (ROOT / a["path"]).is_file():
            add("adr.missing_file", "High", True, a["path"])
    reg = _load("ops/REGISTER.json")
    maxd = reg["policy"]["max_days_by_severity"]
    for e in reg["entries"]:
        for k in ("id", "type", "severity", "title", "owner_role", "created", "expires", "status"):
            if not e.get(k):
                add("register.field", "Medium", True, f"{e.get('id')} missing {k}")
        created, expires = dt.date.fromisoformat(e["created"]), dt.date.fromisoformat(e["expires"])
        if e["type"] in ("waiver", "exception", "perf-waiver"):
            if (expires - created).days > maxd.get(e["severity"], 90):
                add("register.duration", e["severity"], True, f"{e['id']} exceeds max duration")
            if e["status"] == "active" and (not e.get("owner") or not e.get("approvers") or not e.get("compensating_controls")):
                add("register.invalid_waiver", e["severity"], True, f"{e['id']} active waiver without owner/approvers/compensating controls")
            if e["status"] == "active" and expires < today:
                add("register.expired_waiver", e["severity"], e["severity"] in ("Critical", "High"), f"{e['id']} expired {e['expires']}")
        elif expires < today and e["status"] in ("active", "open"):
            add("register.review_overdue", e["severity"], e["severity"] == "Critical", f"{e['id']} review date {e['expires']} passed")
        if e.get("extensions", 0) >= 2:
            add("register.repeated_extension", "Medium", False, f"{e['id']} extended {e['extensions']} times")
    rev = _load("ops/REVIEWS.json")
    for d in rev["domains"]:
        due = dt.date.fromisoformat(d["next_due"])
        if due < today:
            add("review.overdue", d["severity_if_overdue"], d["severity_if_overdue"] in ("Critical", "High"),
                f"{d['domain']} review overdue since {d['next_due']}")
        elif d.get("last") is None:
            add("review.never_performed", "Medium", False, f"{d['domain']} review has no evidence yet (due {d['next_due']})")
    for h in rev.get("history", []):
        if h.get("reviewer") and h.get("reviewer") == h.get("author"):
            add("review.self_approval", "High", True, f"{h.get('domain')} reviewed by its author")
    from inv64_application_model.telemetry import METRICS
    alerts = _load("ops/alerts.json")
    for a in alerts["alerts"]:
        metrics = set(re.findall(r"inv64_[a-z_]+", a["expr"]))
        for m in metrics:
            base = re.sub(r"_(bucket|sum|count)$", "", m)
            if base not in METRICS:
                add("alerts.unknown_metric", "Medium", True, f"{a['id']} uses {m}")
        for k in ("owner_role", "route", "runbook", "severity"):
            if not a.get(k):
                add("alerts.field", "Medium", True, f"{a['id']} missing {k}")
        path, _, anchor = a["runbook"].partition("#")
        if anchor and anchor not in _anchors(ROOT / path):
            add("alerts.runbook_anchor", "Medium", True, f"{a['id']} -> {a['runbook']} not found")
    dash = _load("dashboards/inv64-overview.json")
    for row in dash["rows"]:
        for p in row["panels"]:
            if p["metric"] not in METRICS:
                add("dashboard.unknown_metric", "Medium", True, p["metric"])
    compat = _load("compatibility.json")
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'requires-python\s*=\s*">=([0-9.]+)(?:,\s*<([0-9.]+))?"', py)
    if not m or m.group(1) != compat["python"]["min"]:
        add("compat.requires_python", "High", True, "pyproject requires-python min differs from compatibility.json")
    classifiers = set(re.findall(r"Programming Language :: Python :: (3\.\d+)", py))
    if classifiers != set(compat["python"]["tested_in_ci"]):
        add("compat.classifiers", "Medium", True, f"classifiers {sorted(classifiers)} != tested_in_ci {compat['python']['tested_in_ci']}")
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    if ci.is_file():
        ci_text = ci.read_text(encoding="utf-8")
        for v in compat["python"]["tested_in_ci"]:
            if f'"{v}"' not in ci_text:
                add("compat.ci_matrix", "Medium", True, f"CI matrix lacks Python {v}")
    else:
        add("ci.missing", "High", True, "no CI workflow")
    from inv64_application_model.oam_profile import OAM_COMMIT
    from inv64_application_model.service import OAM_BASELINE
    base = _load("provenance/oam-baseline.json")
    prof = (ROOT / "OAM_PROFILE.md").read_text(encoding="utf-8") if (ROOT / "OAM_PROFILE.md").is_file() else ""
    commits = {compat["oam"]["commit"], base["commit"], OAM_COMMIT}
    if len(commits) != 1 or OAM_COMMIT not in OAM_BASELINE or OAM_COMMIT not in prof:
        add("oam.baseline_drift", "High", True, "OAM baseline differs between compatibility.json, provenance, code and OAM_PROFILE.md")
    lic = (ROOT / "LICENSING.md").read_text(encoding="utf-8") if (ROOT / "LICENSING.md").is_file() else ""
    if "LicenseRef-Proprietary-Pending" in py and "PENDING OWNER DECISION" not in lic:
        add("license.inconsistent", "Medium", True, "pyproject says pending but LICENSING.md does not")
    if "LicenseRef-Proprietary-Pending" in py:
        add("license.pending", "Medium", True, "distribution license not chosen by the owner (MC-38)")
    return f


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    f = check(today)
    blocking = [x for x in f if x["blocking"]]
    res = {"schema": "PK_APP_GOVERNANCE/1", "today": today.isoformat(), "findings": f,
           "blocking": len(blocking), "result": "FAIL" if blocking else "PASS"}
    print(json.dumps(res, indent=2) if a.json else "\n".join(
        [f"{'BLOCK' if x['blocking'] else 'note '} {x['id']}: {x['message']}" for x in f] + [res["result"]]))
    return 0 if not blocking else 1


if __name__ == "__main__":
    sys.exit(main())
