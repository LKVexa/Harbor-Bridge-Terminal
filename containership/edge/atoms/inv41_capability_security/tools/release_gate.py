"""Production exit gate (checklist 'Final production exit checklist', REQ-GOV-007).

Evaluates each exit item mechanically from evidence/ and the governance
files.  Verdict is GO only if every item is PASS.  A met item without its
required human attestation is NOT PASS.  Output: evidence/RELEASE_GATE.json.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

import governance_check  # noqa: E402


def _load(name):
    p = PKG / "evidence" / name
    return json.loads(p.read_text()) if p.exists() else None


def evaluate(today: dt.date | None = None) -> dict:
    ci = _load("ci_run.json") or {}
    trace = _load("TRACEABILITY.json")
    estate = _load("estate_gate.json")
    bench = _load("bench.json")
    mut = _load("mutation.json")
    soak = _load("scale_soak_pr.json")
    compat = _load("compat.json")
    blockers = json.loads((PKG / "BLOCKERS.json").read_text())["blockers"]
    gov = governance_check.run(production=True, today=today)
    manifest_p = PKG / "dist" / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_p.read_text()) if manifest_p.exists() else None
    items = []

    def item(i, text, state, detail):
        items.append({"id": i, "item": text, "state": state, "detail": detail})

    skipped = [s for s in ci.get("suites", []) if s.get("skipped")]
    item("EXIT-01", "No requirement VERIFIED solely because a dependency was skipped",
         "PASS" if trace and not any(r["status"] == "VERIFIED" for r in trace["requirements"]) else "FAIL",
         f"requirements never self-report VERIFIED; skipped suites recorded: {[s['name'] for s in skipped]}")
    item("EXIT-02", "C001-C100 have current traceability entries",
         "PASS" if trace and len(trace["audit"]) == 100 and ci.get("traceability_ok") else "FAIL",
         f"{len(trace['audit']) if trace else 0} audit rows; traceability_ok={ci.get('traceability_ok')}")
    open_audit = [a["check_id"] for a in (trace or {}).get("audit", []) if a["status_4_3_0"] not in
                  ("VERIFIED_4.2.0", "IMPLEMENTED_LOCALLY_VERIFIED") and not a["status_4_3_0"].startswith("VERIFIED_4.2.0")]
    item("EXIT-03", "All C009-C099 MISSING/PARTIAL items VERIFIED or under approved unexpired exception",
         "BLOCKED" if open_audit else "PASS", f"{len(open_audit)} audit items still PARTIAL/BLOCKED: {open_audit}")
    item("EXIT-04", "C030/C083/C090/C100 non-skipped estate evidence",
         "PASS" if estate and estate.get("production_ok") else "BLOCKED",
         f"estate states: {sorted({r['state'] for r in (estate or {}).get('results', [])})}")
    sec_ok = ci.get("all_suites_pass") and mut and not mut["survived"] and soak and soak["pass"]
    item("EXIT-05", "Threat, fuzz, concurrency, fault-injection, compatibility, scale/disaster tests pass",
         "BLOCKED" if sec_ok else "FAIL",
         f"local suites pass={ci.get('all_suites_pass')}; mutants killed {mut and mut['killed']}/{mut and mut['mutants']}; "
         f"PR-tier soak pass={soak and soak['pass']}; compat {compat and compat['summary']} — release-tier soak, fleet and full "
         "matrix not run (B-SOAK-01, B-FLEET-01, B-COMPAT-01)")
    g = (bench or {}).get("gate", {})
    item("EXIT-06", "Performance regression gates pass against approved baselines",
         "BLOCKED" if g.get("pass") else "FAIL", f"gate pass={g.get('pass')} mode={g.get('mode')}; baseline/SLO not owner-approved (B-OWN-01)")
    item("EXIT-07", "SBOM, signed manifest, hashes, provenance, config digest, traceability, reports from the same candidate",
         "BLOCKED" if manifest and manifest.get("reproducible_double_build") else "FAIL",
         f"manifest present={bool(manifest)}; reproducible={manifest and manifest.get('reproducible_double_build')}; "
         f"signature={manifest and manifest['signature']['status']}")
    item("EXIT-08", "Rollout/rollback/incident/vuln/reconstruction/operator runbooks reviewed and executable",
         "BLOCKED", "docs/OPERATIONS.md written; no human review recorded (B-OWN-01)")
    item("EXIT-09", "Production canary succeeded for the observation window", "BLOCKED", "no deployment exists (B-DEPLOY-01)")
    item("EXIT-10", "Release approvers attest evidence corresponds to the promoted artifact", "BLOCKED",
         "release_approver UNASSIGNED; the builder cannot attest its own evidence")
    item("GOV", "Production governance check", "PASS" if gov["ok"] else "FAIL", f"{len(gov['errors'])} errors, e.g. {gov['errors'][:3]}")
    verdict = "GO" if all(i["state"] == "PASS" for i in items) else "NO_GO"
    return {"schema": "INV41_RELEASE_GATE/1", "verdict": verdict, "items": items,
            "open_blockers": [b["id"] for b in blockers], "governance_errors": gov["errors"]}


def main() -> int:
    r = evaluate()
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "RELEASE_GATE.json").write_text(json.dumps(r, indent=1))
    print(r["verdict"])
    for i in r["items"]:
        print(f"  {i['id']:8} {i['state']:8} {i['item']}")
    return 0 if r["verdict"] == "GO" else 3


if __name__ == "__main__":
    raise SystemExit(main())
