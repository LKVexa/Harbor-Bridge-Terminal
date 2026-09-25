"""Formal production exit gate (C090/C100, M32).

Collects machine evidence and emits evidence/EXIT_GATE.json with a verdict:
  NO_GO           any failing gate, or any open waiver lacking owner/approval
  CONDITIONAL_GO  all gates pass; open waivers are owned, approved and unexpired
  GO              all gates pass and no open waivers
The tool never approves a release; it records evidence for a named human approver.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
EV = PKG / "evidence"


def jload(p):
    try:
        return json.loads(p.read_text())
    except FileNotFoundError:
        return None


def main() -> int:
    gates = []

    def gate(gid, ok, detail):
        gates.append({"id": gid, "pass": bool(ok), "detail": detail})

    tests = jload(EV / "test_results.json")
    gate("tier1-tests", tests and tests["failures"] == 0 and tests["errors"] == 0,
         tests and f"{tests['ran']} ran, {tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skipped")
    gate("zero-unexpected-skips", tests and tests["skipped"] == 0,
         tests and (f"{tests['skipped']} skipped: " + "; ".join(tests.get("skip_reasons", []))))
    tr = subprocess.run([sys.executable, str(PKG / "tools" / "build_traceability.py"), "--check"],
                        capture_output=True, text=True)
    gate("traceability", tr.returncode == 0, tr.stdout.strip() + tr.stderr.strip()[-400:])
    fx = subprocess.run([sys.executable, str(PKG / "tools" / "gen_fixtures.py"), "--check"], capture_output=True, text=True)
    gate("conformance-fixtures", fx.returncode == 0, fx.stdout.strip())
    rel = PKG / "dist"
    if (rel / "SHA256SUMS").exists():
        vr = subprocess.run([sys.executable, str(PKG / "tools" / "verify_release.py"), str(rel)], capture_output=True, text=True)
        gate("release-artifacts", vr.returncode == 0, vr.stdout.strip()[-400:])
    else:
        gate("release-artifacts", False, "dist/ not built")
    perf = jload(EV / "perf_gate.json")
    gate("performance", perf and perf["pass"], perf and ", ".join(f"{g['id']}={g['value']}" for g in perf["gates"] if not g["pass"]) or "all within thresholds")
    rm = jload(EV / "runtime_matrix.json")
    gate("runtime-matrix", rm and all(r["status"] in ("pass", "not-available") for r in rm["rows"]),
         rm and ", ".join(f"{r['runtime']}{r.get('flags','').replace('-','') and ' -O'}:{r['status']}" for r in rm["rows"]))

    trace = jload(PKG / "TRACEABILITY.json")
    waivers_md = (PKG / "WAIVERS.md").read_text()
    open_w = []
    for line in waivers_md.splitlines():
        m = re.match(r"\| (W-\d+) \|(.*)", line)
        if m:
            cells = [c.strip() for c in line.strip("|").split("|")]
            wid, owner, approved, expiry = cells[0], cells[5], cells[6], cells[8]
            expired = False
            try:
                expired = dt.date.fromisoformat(expiry) < dt.date.today()
            except ValueError:
                expired = True
            open_w.append({"id": wid, "owner": owner, "approved": approved, "expiry": expiry,
                           "valid": owner not in ("", "—", "-") and approved not in ("", "—", "-") and not expired})
    gates_ok = all(g["pass"] for g in gates)
    if not gates_ok or any(not w["valid"] for w in open_w):
        verdict = "NO_GO"
    elif open_w:
        verdict = "CONDITIONAL_GO"
    else:
        verdict = "GO"
    doc = {"schema": "inv61-exit-gate/1", "component": "INV-61", "version": (PKG / "VERSION").read_text().strip(),
           "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "verdict": verdict, "gates": gates, "traceability_summary": trace and trace["summary"],
           "waivers": open_w, "approver": None,
           "reasons": ([g["id"] for g in gates if not g["pass"]] +
                       [f"{w['id']} lacks owner/approval or expired" for w in open_w if not w["valid"]])}
    EV.mkdir(exist_ok=True)
    (EV / "EXIT_GATE.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(verdict)
    for g in gates:
        print(("PASS " if g["pass"] else "FAIL ") + g["id"] + " - " + str(g["detail"])[:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
