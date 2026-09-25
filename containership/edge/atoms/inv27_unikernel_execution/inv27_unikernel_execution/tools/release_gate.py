"""INV-27 formal production exit gate (MC-041, MC-086; C090, C100).

    python -B -m inv27_unikernel_execution.tools.release_gate [--approval FILE] [--skip-lanes] [--today YYYY-MM-DD]

Runs (or, with --skip-lanes, reads the recorded) mandatory lanes, then decides.  GO only when ALL hold:
  1. lanes pass: tests under python AND python -O (no undeclared skips), lint, deps, coverage, RTM,
     MC registry, pk_core gate, manifest verification
  2. governance passes (owners named, waivers approved/unexpired, reviews current)
  3. performance gate PASS on non-quick results
  4. every P0 component is verified_local AND independently reviewed; no waiver covers a P0 component
  5. every other non-verified component is covered only by APPROVED, unexpired waivers
  6. a human release approval (APPROVE) from a non-service identity distinct from the security owner,
     bound to the current SHA256SUMS digest
Per-MC results are written for every component: PASS requires verified_local + an independent review
record in ops/REVIEWS.json ``mc_reviews``.  Exit 0 = GO, 3 = NO_GO.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys

from ._refs import ROOT, load

SERVICE = re.compile(r"(?i)\b(bot|ci|service|automation|pipeline|claude)\b")
PKG = ROOT.name
LANES = {
    "tests": ["-B", f"{PKG}/tests/run_all.py"],
    "tests_optimized": ["-O", "-B", f"{PKG}/tests/run_all.py"],
    "lint": ["-B", "-m", f"{PKG}.tools.lint"],
    "deps": ["-B", "-m", f"{PKG}.tools.deps_check"],
    "coverage": ["-B", "-m", f"{PKG}.tools.coverage_check", "--check"],
    "rtm": ["-B", "-m", f"{PKG}.tools.rtm", "--check"],
    "mc_status": ["-B", "-m", f"{PKG}.tools.mc_status", "--check"],
    "pk_gate": ["-B", "-m", f"{PKG}.tools.pk_gate", "--check"],
    "pk_gate_optimized": ["-O", "-B", "-m", f"{PKG}.tools.pk_gate", "--check"],
    "manifest": ["-B", "-m", f"{PKG}.tools.manifest", "--verify"],
}


def run_lanes() -> dict:
    out = {}
    for name, args in LANES.items():
        p = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=str(ROOT.parent), timeout=1800)
        out[name] = {"pass": p.returncode == 0, "rc": p.returncode, "tail": (p.stdout + p.stderr)[-600:]}
    return out


def sums_digest() -> str:
    p = ROOT / "SHA256SUMS.txt"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def evaluate(lanes: dict, mc: dict, waivers: dict, governance: dict, perf: dict | None, approval: dict | None,
             owners: dict, reviews: dict, today: dt.date, digest: str) -> dict:
    blockers = [f"lane {n} failed" for n, l in lanes.items() if not l["pass"]]
    if not governance.get("pass"):
        blockers.append("governance check failed")
    if not perf or perf.get("verdict") != "PASS":
        blockers.append("performance gate not PASS")
    approved = {w["id"] for w in waivers["entries"] if w["status"] == "approved" and w.get("approver")
                and not SERVICE.search(str(w["approver"])) and dt.date.fromisoformat(w["expires"]) >= today}
    reviewed = {r["mc"] for r in reviews.get("mc_reviews", []) if r.get("reviewer") and not SERVICE.search(str(r["reviewer"]))}
    per_mc = {}
    for k, c in mc["components"].items():
        ok = c["status"] == "verified_local" and k in reviewed
        per_mc[k] = {"priority": c["priority"], "status": c["status"], "reviewed": k in reviewed,
                     "result": "PASS" if ok else "NOT_PASS", "waivers": c["blockers"]}
        if c["priority"] == "P0" and not ok:
            blockers.append(f"{k} (P0) is {c['status']}{'' if k in reviewed else ', unreviewed'}")
        elif c["status"] != "verified_local" and not set(c["blockers"]) <= approved:
            blockers.append(f"{k} ({c['priority']}) {c['status']} with unapproved waivers {sorted(set(c['blockers']) - approved)}")
    sec = next((r["holder"] for r in owners["roles"] if r["alias"] == "inv27-security-owner"), None)
    who = str((approval or {}).get("approver", ""))
    if not approval or approval.get("decision") != "APPROVE":
        blockers.append("no human release approval supplied")
    elif not who or SERVICE.search(who):
        blockers.append("release approval names a service identity or nobody")
    elif who == sec:
        blockers.append("release approver must differ from the security owner")
    elif approval.get("sha256sums") != digest:
        blockers.append("release approval is not bound to the current SHA256SUMS digest")
    return {"verdict": "GO" if not blockers else "NO_GO", "blockers": blockers, "per_mc": per_mc,
            "per_mc_pass": sum(1 for v in per_mc.values() if v["result"] == "PASS")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approval")
    ap.add_argument("--skip-lanes", action="store_true")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args(argv)
    ev_path = ROOT / "evidence" / "RELEASE_EVIDENCE.json"
    if a.skip_lanes:
        lanes = json.loads(ev_path.read_text())["lanes"] if ev_path.exists() else {"recorded": {"pass": False}}
    else:
        lanes = run_lanes()
    from .governance_check import check as gov
    today = dt.date.fromisoformat(a.today)
    governance = gov(today)
    perf_p = ROOT / "evidence" / "PERF_GATE.json"
    perf = json.loads(perf_p.read_text()) if perf_p.exists() else None
    approval = json.loads(open(a.approval).read()) if a.approval else None
    r = evaluate(lanes, load("ops/MC_STATUS_SOURCE.json"), load("ops/WAIVERS.json"), governance, perf, approval,
                 load("ops/OWNERS.json"), load("ops/REVIEWS.json"), today, sums_digest())
    mcs = load("evidence/MC_STATUS.json")["summary"] if (ROOT / "evidence" / "MC_STATUS.json").exists() else {}
    rtm = load("evidence/RTM.json")["summary"] if (ROOT / "evidence" / "RTM.json").exists() else {}
    doc = {"schema": "PK_UNIKERNEL_RELEASE_EVIDENCE/1", "component": "INV-27", "version": (ROOT / "VERSION").read_text().strip(),
           "date": a.today, "python": sys.version.split()[0], "sha256sums_digest": sums_digest(),
           "lanes": {k: {"pass": v["pass"], "rc": v.get("rc")} for k, v in lanes.items()},
           "governance": governance, "perf_gate": perf, "mc_summary": mcs, "rtm_summary": rtm, **r}
    ev_path.write_text(json.dumps(doc, indent=1))
    for b in r["blockers"][:40]:
        print("BLOCKER", b)
    print("RELEASE_GATE", r["verdict"], f"({len(r['blockers'])} blockers, {r['per_mc_pass']}/94 MC PASS)")
    return 0 if r["verdict"] == "GO" else 3


if __name__ == "__main__":
    sys.exit(main())
