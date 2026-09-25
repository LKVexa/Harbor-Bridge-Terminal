#!/usr/bin/env python3
"""Production exit gate (MC-068): objective checks consumed by digest; subjective approvals isolated.

Verdict GO only if: every control is PASS / NOT_APPLICABLE / WAIVED-with-approved-unexpired waiver;
no release-blocking waiver is unapproved; all test runs passed with only approved skips; the perf gate
passed; required named approvals are recorded.  Otherwise NO_GO with the blocking reasons.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
APPROVAL_ROLES = ["service_owner", "architecture", "security", "operations", "release_authority"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()
    ev_p = ROOT / "governance/ACCEPTANCE_EVIDENCE.json"
    ev = json.loads(ev_p.read_text())
    waivers = {w["id"]: w for w in json.loads((ROOT / "governance/WAIVERS.json").read_text())["waivers"]}
    approvals_p = ROOT / "governance/APPROVALS.json"
    approvals = json.loads(approvals_p.read_text()) if approvals_p.exists() else {}
    sections, blockers = {}, []

    def section(name, ok, detail):
        sections[name] = {"pass": ok, "detail": detail}
        if not ok:
            blockers.append(f"{name}: {detail}")

    tr = ev["test_runs"]
    section("testing", all(r["returncode"] == 0 and not r["failed"] for r in tr.values()),
            f"{tr['unittest']['passed']}/{tr['unittest']['tests']} passed, {len(tr['unittest']['skipped'])} skipped (pk_core, W-003)")
    # skipped pk_core tests are non-evidence: they make the conformance section fail, not this one
    section("performance", ev["performance"]["gate"]["verdict"] == "PASS", f"bench gate {ev['performance']['gate']['verdict']}")
    bad_ctl = [c["id"] for c in ev["controls"] if c["status"] in ("FAIL", "BLOCKED")]
    unapproved = sorted({w for c in ev["controls"] if c["status"] == "WAIVED" for w in c["waivers"]
                         if waivers[w]["release_blocking_for_prod"] and (waivers[w]["approved_by"] is None or waivers[w]["expires"] < a.today)})
    section("controls", not bad_ctl, f"{len(bad_ctl)} FAIL/BLOCKED controls")
    section("waivers", not unapproved, f"unapproved or expired release-blocking waivers: {', '.join(unapproved) or 'none'}")
    section("conformance", False, "pk_core 100-item conformance not executed (W-003)")
    section("security_review", bool(approvals.get("security")), "security review sign-off")
    section("architecture", bool(approvals.get("architecture")), "ADR-0001 approval")
    section("operations", bool(approvals.get("operations")), "runbooks exercised + on-call live")
    missing = [r for r in APPROVAL_ROLES if not approvals.get(r)]
    section("approvals", not missing, f"missing named approvals: {', '.join(missing) or 'none'}")
    totals = ev["checklist_totals"]
    section("remediation_checklist", totals["OPEN"] == 0, f"{totals['OPEN']} OPEN / {totals['PARTIAL']} PARTIAL of 1,420 items")
    verdict = "GO" if not blockers else "NO_GO"
    gate = {"schema": "PK_ECP_EXIT_GATE/1", "element": "INV-66", "version": ev["version"], "date": a.today,
            "verdict": verdict, "inputs": {"acceptance_evidence_sha256": hashlib.sha256(ev_p.read_bytes()).hexdigest(),
                                           "bundle_sha256": ev["bundle_sha256"],
                                           "approvals_sha256": hashlib.sha256(approvals_p.read_bytes()).hexdigest() if approvals_p.exists() else None},
            "sections": sections, "blockers": blockers,
            "break_glass": "Promotion with a non-GO verdict requires an audited break-glass record signed by the service owner and security owner."}
    (ROOT / "governance/PRODUCTION_EXIT_GATE.json").write_text(json.dumps(gate, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "blockers": len(blockers)}))
    return 1 if a.require and verdict != a.require else 0


if __name__ == "__main__":
    sys.exit(main())
