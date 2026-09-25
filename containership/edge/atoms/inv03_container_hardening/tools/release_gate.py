"""Item 54: machine-readable release gate for INV-03.

Runs every check as a real subprocess, records argv + exit code, reads
CHECKLIST_STATUS.json, and writes RELEASE_GATE.json. Rules:
  * a skipped or not-run mandatory check is never a PASS;
  * an item may read complete only with a human approval record whose approver
    is not this tool, CI, or the model that built the package;
  * the verdict is GO only if every P0 and P1 item is complete and every
    check passed. Exit 0 = GO, 3 = NO_GO (evidence recorded), 1 = gate error.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(PKG, "tests")
FORBIDDEN_APPROVERS = ("claude", "release_gate", "ci", "github-actions", "bot", "automation")
CHECKS = [
    ("unit_normal", [sys.executable, "-B", "-W", "ignore", "-m", "unittest", "-q", "test_h_controls",
                     "test_h_integrity", "test_h_engine", "test_h_certification", "test_h_schemas", "test_h_gate", "test_policy"], TESTS),
    ("unit_optimized", [sys.executable, "-B", "-O", "-W", "ignore", "-m", "unittest", "-q", "test_h_controls",
                        "test_h_integrity", "test_h_engine", "test_h_certification", "test_policy"], TESTS),
    ("framework_conformance", [sys.executable, "-B", "-m", "unittest", "-q", "test_component"], TESTS),
    ("mutation_probe", [sys.executable, "-B", os.path.join("tools", "mutation_probe.py")], PKG),
    ("lint", ["ruff", "check", "hardening", "tools", "tests"], PKG),
    ("typecheck", ["mypy"], PKG),
]


def run(name, argv, cwd):
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=900)
        rc, out = p.returncode, (p.stdout + p.stderr)[-2000:]
    except FileNotFoundError as e:
        rc, out = None, f"NOT_RUN: {e}"
    skipped = "skipped=" in out or "SKIP" in out
    status = "NOT_RUN" if rc is None else ("PASS" if rc == 0 and not skipped else ("SKIPPED" if rc == 0 else "FAIL"))
    # never embed the generating host's interpreter path or package location (shop convention)
    shown = [os.path.basename(argv[0])] + [a.replace(PKG, ".") for a in argv[1:]]
    return {"check": name, "argv": shown, "exit_code": rc, "status": status,
            "seconds": round(time.time() - t0, 2), "tail": out.replace(PKG, ".")}


def approved(item) -> bool:
    appr = item.get("approval") or {}
    who = str(appr.get("approver", "")).lower()
    return bool(who) and appr.get("kind") == "human" and not any(f in who for f in FORBIDDEN_APPROVERS)


def main() -> int:
    with open(os.path.join(PKG, "CHECKLIST_STATUS.json")) as fh:
        status = json.load(fh)
    checks = [run(*c) for c in CHECKS]
    forged = [i["n"] for i in status["items"] if i.get("complete") and not approved(i)]
    open_items = [i["n"] for i in status["items"] if i["priority"] in ("P0", "P1") and not (i.get("complete") and approved(i))]
    failed = [c["check"] for c in checks if c["status"] != "PASS"]
    verdict = "GO" if not open_items and not failed and not forged else "NO_GO"
    gate = {"schema": "INV03_RELEASE_GATE/1", "package_version": status["package_version"],
            "generated_by": "tools/release_gate.py (not an approval)", "verdict": verdict,
            "checks": checks, "check_summary": {c["check"]: c["status"] for c in checks},
            "items_total": len(status["items"]), "items_complete": sum(1 for i in status["items"] if i.get("complete") and approved(i)),
            "status_counts": status["counts"], "open_p0_p1_items": open_items, "forged_completions": forged,
            "human_signature": None,
            "reasons": ([f"{len(open_items)} P0/P1 items not complete with a human approval"] if open_items else [])
            + ([f"checks not PASS: {failed}"] if failed else [])
            + ([f"items claimed complete without a human approval: {forged}"] if forged else [])}
    with open(os.path.join(PKG, "RELEASE_GATE.json"), "w") as fh:
        json.dump(gate, fh, indent=1)
    print(json.dumps({k: gate[k] for k in ("verdict", "check_summary", "items_complete", "reasons")}, indent=1))
    return 0 if verdict == "GO" else 3


if __name__ == "__main__":
    sys.exit(main())
