"""PLN-05 production exit gate (MC-30 / C100 / final closure checklist).

    python tools/gate.py [--evidence evidence/<version>] [--out EXIT_GATE.json]

Verdict: GO only when every evidence result is PASS with no skipped mandatory check,
every MC component is COMPLETE, every C001–C100 requirement is verified or covered by an
APPROVED non-expired waiver, and the named human roles have signed governance/approvals.json
for this exact version and source revision.  CONDITIONAL_GO when the only open items are
approved waivers.  Otherwise NO_GO with every blocker listed.  Evidence producers (this
tool, tools/ci.py, the chop-shop pass, any AI assistant) are refused as approvers."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED_SIGNERS = ("pln05.release-approver", "pln05.service-owner")
SELF = re.compile(r"(claude|chop-?shop|assistant|tools/|ci\.py|gate\.py|automation|bot)", re.I)


def _load(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8"))


def evaluate(manifest: dict, mc: dict, trace: dict, approvals: list, waivers: list, oncall: dict,
             scope: dict, baseline: dict, license_present: bool, today: dt.date) -> dict:
    blockers, conditions = [], []

    def block(sev, msg):
        blockers.append({"severity": sev, "blocker": msg})

    tier = manifest.get("tier")
    for name, r in sorted(manifest["results"].items()):
        if r["result"] != "PASS":
            block("Critical", f"evidence {name}: {r['result']}" + (f" ({r.get('reason')})" if r.get("reason") else ""))
        if r.get("skipped", 0) and r.get("mandatory", True):
            if tier == "release":
                block("Critical", f"evidence {name}: {r['skipped']} mandatory check(s) skipped")
            else:
                block("High", f"evidence {name}: {r['skipped']} skipped (presubmit tier; release tier refuses skips)")
    if tier != "release":
        block("High", f"evidence tier is '{tier}'; production acceptance requires the release tier")
    for c in mc["components"]:
        if c["status"] != "COMPLETE":
            block("High" if c["status"] == "IMPLEMENTED_LOCAL" else "Critical", f"{c['id']} {c['status']}")
    ok_waivers = {w["id"] for w in waivers if w.get("status") == "APPROVED"
                  and dt.date.fromisoformat(w["expires"]) >= today}
    for w in waivers:
        if dt.date.fromisoformat(w["expires"]) < today:
            block("Critical", f"waiver {w['id']} expired {w['expires']}")
        elif w.get("status") != "APPROVED":
            block("High", f"waiver {w['id']} not approved ({w.get('status')})")
        else:
            conditions.append(f"waiver {w['id']} accepted until {w['expires']}")
    unverified = [r["id"] for r in trace["requirements"] if r["id"].startswith("PLN-05-C")
                  and r["status"] != "verified" and r.get("waiver") not in ok_waivers]
    if unverified:
        block("Critical", f"{len(unverified)} of 100 PLN-05-C### requirements not verified (first: {unverified[0]})")
    unassigned = [k for k, v in oncall["roles"].items() if v.get("assignee") in (None, "", "UNASSIGNED")]
    if unassigned:
        block("Critical", f"{len(unassigned)} ownership roles UNASSIGNED ({', '.join(sorted(unassigned)[:3])}...)")
    last = dt.date.fromisoformat(oncall["last_reviewed"])
    if (today - last).days > oncall["review_cadence_days"]:
        block("High", "ownership record review overdue")
    if scope.get("adr_status") != "ACCEPTED":
        block("Critical", f"ADR-0001 status {scope.get('adr_status')} (MC-01)")
    if not license_present:
        block("Critical", "no LICENSE file (MC-34)")
    if baseline.get("status") != "APPROVED":
        block("High", f"performance baseline {baseline.get('status')}")
    signed = set()
    for a in approvals:
        if SELF.search(str(a.get("approver", ""))):
            block("Critical", f"approval by evidence producer refused: {a.get('approver')}")
            continue
        if a.get("version") == manifest["version"] and a.get("source_revision") == manifest["source_revision"]:
            signed.add(a.get("role"))
    for role in REQUIRED_SIGNERS:
        if role not in signed:
            block("Critical", f"no human approval by {role} for {manifest['version']}@{manifest['source_revision'][:12]}")
    crit = [b for b in blockers if b["severity"] == "Critical"]
    verdict = "NO_GO" if crit or blockers else ("CONDITIONAL_GO" if conditions else "GO")
    return {"schema": "PLN05_EXIT_GATE/1", "version": manifest["version"],
            "source_revision": manifest["source_revision"], "tier": tier, "verdict": verdict,
            "blockers": blockers, "conditions": conditions,
            "summary": {"blockers": len(blockers), "critical": len(crit),
                        "mc_components": mc["component_status_counts"], "mc_items": mc["item_totals"],
                        "requirements_verified": sum(1 for r in trace["requirements"]
                                                     if r["id"].startswith("PLN-05-C") and r["status"] == "verified")},
            "evaluated_on": today.isoformat()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    v = (ROOT / "VERSION").read_text().strip()
    ap.add_argument("--evidence", default=str(ROOT / "evidence" / v))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    ev = pathlib.Path(a.evidence)
    res = evaluate(_load(ev / "manifest.json"), _load(ev / "MC_STATUS.json"), _load(ROOT / "traceability" / "requirements.json"),
                   _load(ROOT / "governance" / "approvals.json")["approvals"], _load(ROOT / "governance" / "waivers.json")["waivers"],
                   _load(ROOT / "ops" / "oncall.json"), _load(ROOT / "spec" / "pln05_scope.json"),
                   _load(ROOT / "benchmarks" / "baseline.json"), (ROOT / "LICENSE").exists(), dt.date.today())
    out = pathlib.Path(a.out) if a.out else ev / "EXIT_GATE.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"verdict": res["verdict"], **res["summary"]}, indent=1))
    return 0 if res["verdict"] in ("GO", "CONDITIONAL_GO") else 2


if __name__ == "__main__":
    sys.exit(main())
