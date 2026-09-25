"""INV-69 release gate (C090, C100, C070, C099; global completion gates).

    python -m inv69_agentic_workload_layer.tools.release_gate [--pk-gate FILE] [--approval FILE]
        [--skip-perf-run] [--quick-perf] [--today YYYY-MM-DD] [--out evidence/RELEASE_EVIDENCE.json]

Runs (or reads) every mandatory lane and writes machine-readable release evidence.  Verdict GO only when:
  * test profile passes in normal AND `python -O` mode with no undeclared skips
  * SPEC drift check, RTM validation, dependency check pass
  * performance gate passes on non-quick results
  * governance check passes (owners named, waivers approved and unexpired, reviews not overdue)
  * every RTM control is `present` or carries an APPROVED, unexpired waiver
  * a PASSing pk_core PK_GATE_RESULTS file is supplied (--pk-gate)
  * a human release approval (--approval) naming a non-service approver, distinct from the security owner
Exit 0 = GO, 3 = NO_GO.  Nothing in this repository can mint the last two inputs; the falsifier test proves GO
is reachable when they (and the rest) are supplied.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
SERVICE = re.compile(r"(?i)\b(bot|ci|service|automation|pipeline|claude)\b")


def _run(args: list[str], timeout=1800) -> tuple[int, str]:
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=str(PARENT), timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)[-4000:]


def _result_line(text: str) -> dict:
    for line in reversed(text.splitlines()):
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    return {}


def evaluate(lanes: dict, rtm: dict, waivers: dict, governance: dict, perf: dict | None, pk_gate: dict | None,
             approval: dict | None, owners: dict, today: dt.date) -> dict:
    blockers: list[str] = []
    for name, lane in lanes.items():
        if not lane["pass"]:
            blockers.append(f"lane {name} failed")
    if not perf or perf.get("verdict") != "PASS":
        blockers.append("performance gate not PASS" + (f": {perf['failures'][:3]}" if perf else " (not run)"))
    if perf and perf.get("quick"):
        blockers.append("performance results are quick-mode; not valid for gating")
    if not governance.get("pass"):
        blockers.append(f"governance check failed ({sum(len(governance[k]) for k in ('owners', 'waivers', 'reviews', 'versions'))} findings)")
    approved = {}
    for w in waivers["entries"]:
        if w["status"] == "approved" and w.get("approver") and dt.date.fromisoformat(w["expires"]) >= today:
            for c in w["controls"]:
                approved[c] = w["id"]
    nonpresent = [r for r in rtm["rows"] if r["status"] != "present"]
    ungoverned = [r["check_id"] for r in nonpresent if r["check_id"] not in approved]
    if ungoverned:
        blockers.append(f"{len(ungoverned)} controls neither present nor covered by an approved waiver")
    if not pk_gate or pk_gate.get("verdict") != "PASS":
        blockers.append("no PASSing pk_core PK_GATE_RESULTS supplied (W-001)")
    approver = str((approval or {}).get("approver", ""))
    sec_owner = next((r["holder"] for r in owners["roles"] if r["alias"] == "inv69-security-owner"), None)
    if not approval or approval.get("decision") != "APPROVE":
        blockers.append("no human release approval supplied")
    elif not approver or SERVICE.search(approver):
        blockers.append("release approval names a service identity or no approver")
    elif approver == sec_owner:
        blockers.append("release approver must differ from the security owner (separation of duties)")
    return {"verdict": "GO" if not blockers else "NO_GO", "blockers": blockers,
            "controls_nonpresent": len(nonpresent), "controls_ungoverned": ungoverned}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pk-gate")
    ap.add_argument("--approval")
    ap.add_argument("--skip-perf-run", action="store_true")
    ap.add_argument("--quick-perf", action="store_true")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--out", default=str(ROOT / "evidence" / "RELEASE_EVIDENCE.json"))
    a = ap.parse_args(argv)
    pkg = ROOT.name
    lanes = {}
    for name, args in (("tests_normal", ["-B", f"{pkg}/tests/run_all.py"]),
                       ("tests_optimized", ["-O", "-B", f"{pkg}/tests/run_all.py"]),
                       ("spec_drift", ["-B", "-m", f"{pkg}.tools.gen_spec", "--check"]),
                       ("rtm", ["-B", "-m", f"{pkg}.tools.rtm", "--check"]),
                       ("deps", ["-B", "-m", f"{pkg}.tools.deps_check"])):
        t = time.time()
        code, out = _run(args)
        lanes[name] = {"pass": code == 0, "exit": code, "seconds": round(time.time() - t, 2),
                       "result": _result_line(out), "tail": out[-600:]}
    if not a.skip_perf_run:
        _run(["-B", f"{pkg}/bench/perf_suite.py"] + (["--quick"] if a.quick_perf else []))
    code, _ = _run(["-B", "-m", f"{pkg}.tools.perf_gate"])
    perf_path = ROOT / "evidence" / "PERF_GATE.json"
    perf = json.loads(perf_path.read_text()) if perf_path.exists() else None
    if perf is not None:
        res = json.loads((ROOT / "evidence" / "PERF_RESULTS.json").read_text())
        perf["quick"] = res.get("quick", False)
    gcode, gout = _run(["-B", "-m", f"{pkg}.tools.governance_check", "--json", "--today", a.today])
    governance = json.loads(gout[gout.index("{"):]) if "{" in gout else {"pass": False, "owners": ["unreadable"],
                                                                        "waivers": [], "reviews": [], "versions": []}
    (ROOT / "evidence" / "GOVERNANCE_CHECK.json").write_text(json.dumps(governance, indent=1))
    _run(["-B", "-m", f"{pkg}.tools.rtm"])
    rtm = json.loads((ROOT / "evidence" / "RTM.json").read_text())
    load = lambda p: json.loads(Path(p).read_text()) if p else None
    result = evaluate(lanes, rtm, json.loads((ROOT / "ops" / "WAIVERS.json").read_text()), governance, perf,
                      load(a.pk_gate), load(a.approval), json.loads((ROOT / "ops" / "OWNERS.json").read_text()),
                      dt.date.fromisoformat(a.today))
    manifest = ROOT / "SHA256SUMS.txt"
    evidence = {
        "schema": "PK_RELEASE_EVIDENCE/1", "element": "INV-69", "version": (ROOT / "VERSION").read_text().strip(),
        "generated_at": time.time(), "today": a.today,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.exists() else None,
        "lanes": lanes, "perf_gate": perf and {k: perf[k] for k in ("verdict", "failures", "thresholds_status", "baseline_used")},
        "governance": {k: governance.get(k) for k in ("pass", "owners", "waivers", "reviews", "versions")},
        "rtm_summary": rtm["summary"], **result,
    }
    Path(a.out).write_text(json.dumps(evidence, indent=1), encoding="utf-8")
    print(f"RELEASE {result['verdict']}")
    for b in result["blockers"]:
        print("BLOCKER", b)
    return 0 if result["verdict"] == "GO" else 3


if __name__ == "__main__":
    sys.exit(main())
