"""Render docs/CLOSURE_REPORT.md from the machine-readable status, trace and gate result."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
st = json.loads((ROOT / "release/COMPONENT_STATUS.json").read_text())["components"]
tr = json.loads((ROOT / "traceability/TRACEABILITY.json").read_text())["components"]
gate = json.loads((ROOT / "evidence/production-gate.json").read_text())
tests = json.loads((ROOT / "evidence/test-results.json").read_text())
L = ["# INV-24 4.3.0 — missing-component closure report", "",
     f"Generated from `release/COMPONENT_STATUS.json`, `traceability/TRACEABILITY.json` and `evidence/production-gate.json` "
     f"(gate digest `{gate['result_sha256'][:16]}…`, source tree `{gate['source_tree_sha256'][:16]}…`, commit `{gate['source_commit'][:12]}`).", "",
     f"**Production gate verdict: {gate['verdict']}** — failed checks: {', '.join(gate['failed_checks'])}.", "",
     f"Tests: {tests['counts']['PASS']} PASS, {tests['counts']['FAIL']} FAIL, {tests['counts']['NOT_TESTED']} NOT_TESTED (skips are never PASS).", "",
     "Checklist status for every component is `BLOCKED` because the universal definition of done needs a named owner/approver and "
     "verification on an immutable release candidate in the target environment. `Local impl.` and `Local verif.` show what this pass built and proved.", "",
     "| ID | P | Component | Local impl. | Local verif. | Tests | Blocked on |", "|---|---|---|---|---|---|---|"]
for mc in sorted(st):
    s = st[mc]
    L.append(f"| {mc} | {s['priority']} | {s['title']} | {s['local_implementation']} | {s['local_verification']} | {len(tr[mc]['tests'])} | "
             + "; ".join(b for b in s["blocked_on"] if not b.startswith("accountable owner")) + " |")
L += ["", "All rows are additionally blocked on: accountable owner/approver not assigned.", ""]
(ROOT / "docs/CLOSURE_REPORT.md").write_text("\n".join(L) + "\n")
print("rendered", len(st), "components")
