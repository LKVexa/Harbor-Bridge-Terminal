"""INV-28 formal production exit gate (MC-052, MC-076; checklist "Final repository-wide closure gate").

    python -B -m inv28_unikernel_implementations.tools.release_gate [--approval FILE] [--review FILE]
        [--today YYYY-MM-DD] [--skip-slow] [--out evidence/RELEASE_EVIDENCE.json]

GO only when ALL hold:
  * lanes pass: tests (python and python -O, no undeclared skips), lint, SAST, secrets, deps, MASTER.md,
    MC-status traceability, coverage >= threshold, mutation >= threshold
  * benchmark and soak verdict PASS on non-quick runs
  * governance passes (owners named, waivers approved/unexpired, reviews done, decisions accepted)
  * vendored pk_core gate GO (necessary, never sufficient)
  * every MC-001..MC-100 item is either (a) implemented_unreviewed AND accepted in an independent review
    record (--review) by a named human who is not a service identity and not the release approver, or
    (b) covered by an approved, unexpired waiver
  * a human release approval (--approval) that is not a service identity and differs from the security owner
Exit 0 = GO, 3 = NO_GO.  Nothing in this repository can mint the review or approval files; tests/test_gates.py
proves GO is reachable when they (and everything else) are genuinely supplied.
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

from ._common import EVIDENCE, PARENT, PKG, ROOT, read_json, write_json

SERVICE = re.compile(r"(?i)\b(bot|ci|service|automation|pipeline|claude)\b")


def _human(name) -> bool:
    return bool(name) and not SERVICE.search(str(name))


def evaluate(lanes: dict, mc: dict, waivers: dict, governance: dict, bench: dict | None, soak: dict | None,
             pk_gate: dict | None, review: dict | None, approval: dict | None, owners: dict, today: dt.date) -> dict:
    blockers: list[str] = []
    for name, lane in sorted(lanes.items()):
        if not lane.get("pass"):
            blockers.append(f"lane {name} failed")
    for label, doc in (("benchmark", bench), ("soak", soak)):
        if not doc or doc.get("verdict") != "PASS" or doc.get("quick"):
            blockers.append(f"{label} not PASS on a full run" + (f": {doc.get('failures', [])[:3]}" if doc else " (missing)"))
    if not governance.get("pass"):
        n = sum(len(governance.get(k, [])) for k in ("owners", "waivers", "reviews", "decisions"))
        blockers.append(f"governance failed ({n} findings)")
    if not pk_gate or pk_gate.get("verdict") != "GO":
        blockers.append("vendored pk_core gate not GO")
    approver = (approval or {}).get("approver")
    reviewed = set()
    if review:
        rv = review.get("reviewer")
        if not _human(rv):
            blockers.append("review record names a service identity or no reviewer")
        elif rv == approver:
            blockers.append("reviewer must differ from the release approver")
        else:
            reviewed = {i for i, v in review.get("items", {}).items() if v == "accepted"}
    waived = {}
    for w in waivers.get("entries", []):
        if w.get("status") == "approved" and _human(w.get("approver")) and w.get("approver") != w.get("owner") \
                and dt.date.fromisoformat(w["expires"]) >= today:
            for c in w["controls"]:
                waived[c] = w["id"]
    open_items = []
    for row in mc["rows"]:
        ok = (row["status"] == "implemented_unreviewed" and row["mc"] in reviewed) or row["mc"] in waived
        if not ok:
            open_items.append(row["mc"])
    if open_items:
        blockers.append(f"{len(open_items)} MC items neither independently accepted nor covered by an approved waiver")
    sec = next((r.get("holder") for r in owners["roles"] if r["alias"] == "inv28-security-owner"), None)
    if not approval or approval.get("decision") != "APPROVE":
        blockers.append("no human release approval supplied")
    elif not _human(approver):
        blockers.append("release approval names a service identity or no approver")
    elif approver == sec:
        blockers.append("release approver must differ from the security owner (separation of duties)")
    return {"verdict": "GO" if not blockers else "NO_GO", "blockers": blockers, "open_mc_items": open_items,
            "reviewed_items": len(reviewed), "waived_items": sorted(waived)}


def _run(args, timeout=1800):
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=str(PARENT), timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approval")
    ap.add_argument("--review")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--skip-slow", action="store_true", help="reuse existing bench/soak/mutation evidence")
    ap.add_argument("--out", default=str(EVIDENCE / "RELEASE_EVIDENCE.json"))
    a = ap.parse_args(argv)
    lanes = {}
    plan = [("tests_normal", ["-B", f"{PKG}/tests/run_all.py"]),
            ("tests_optimized", ["-B", "-O", f"{PKG}/tests/run_all.py"]),
            ("lint", ["-B", "-m", f"{PKG}.tools.lint"]), ("sast", ["-B", "-m", f"{PKG}.tools.sast"]),
            ("secrets", ["-B", "-m", f"{PKG}.tools.secret_scan"]), ("deps", ["-B", "-m", f"{PKG}.tools.deps_check"]),
            ("sbom", ["-B", "-m", f"{PKG}.tools.sbom"]), ("master", ["-B", "-m", f"{PKG}.tools.master", "--check"]),
            ("coverage", ["-B", "-m", f"{PKG}.tools.coverage"]), ("pk_gate", ["-B", "-m", f"{PKG}.tools.pk_gate"])]
    if not a.skip_slow:
        plan += [("mutation", ["-B", "-m", f"{PKG}.tools.mutation"])]
        _run(["-B", "-m", f"{PKG}.tools.bench"])
        _run(["-B", "-m", f"{PKG}.tools.soak"])
    for name, args in plan:
        t = time.time()
        code, out = _run(args)
        lanes[name] = {"pass": code == 0, "exit": code, "seconds": round(time.time() - t, 2), "tail": out[-400:]}
    if a.skip_slow:
        m = EVIDENCE / "MUTATION.json"
        lanes["mutation"] = {"pass": m.exists() and read_json(m)["pass"], "reused": True}
    code, out = _run(["-B", "-m", f"{PKG}.tools.rtm"])
    lanes["mc_status"] = {"pass": code == 0, "exit": code, "tail": out[-400:]}
    code, out = _run(["-B", "-m", f"{PKG}.tools.governance_check", "--json", "--today", a.today])
    governance = json.loads(out[out.index("{"):]) if "{" in out else {"pass": False}
    write_json(EVIDENCE / "GOVERNANCE_CHECK.json", governance)
    load = lambda p: read_json(Path(p)) if p else None  # noqa: E731
    opt = lambda p: read_json(p) if p.exists() else None  # noqa: E731
    mc = read_json(EVIDENCE / "MC_STATUS.json")
    result = evaluate(lanes, mc, read_json(ROOT / "ops" / "WAIVERS.json"), governance, opt(EVIDENCE / "BENCH_RESULTS.json"),
                      opt(EVIDENCE / "SOAK_RESULTS.json"), opt(EVIDENCE / "PK_GATE_RESULTS.json"), load(a.review),
                      load(a.approval), read_json(ROOT / "ops" / "OWNERS.json"), dt.date.fromisoformat(a.today))
    sums = ROOT / "SHA256SUMS.txt"
    evidence = {"schema": "PK_RELEASE_EVIDENCE/1", "element": "INV-28", "version": (ROOT / "VERSION").read_text().strip(),
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "today": a.today,
                "sha256sums_digest_at_gate": hashlib.sha256(sums.read_bytes()).hexdigest() if sums.exists() else None,
                "lanes": {k: {kk: vv for kk, vv in v.items() if kk != "tail"} for k, v in lanes.items()},
                "governance": governance, "mc_summary": mc["summary"], **result}
    write_json(Path(a.out), evidence)
    print(f"RELEASE {result['verdict']}")
    for b in result["blockers"]:
        print("BLOCKER", b)
    return 0 if result["verdict"] == "GO" else 3


if __name__ == "__main__":
    sys.exit(main())
