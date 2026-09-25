"""External machine-readable release evidence and exit gate for INV-44
(missing component 19; C090, C100).

``python -m inv44_wasm_hardening_system.release_gate [--out evidence/]`` writes

    RELEASE_EVIDENCE.json   components, matrix summary, test result, digests, blockers, verdict

The verdict is GO only when *all* of the following hold; each unmet one is a
named blocker:

* every one of the 19 missing components is COMPLETE in COMPONENTS_STATUS.json
* every POST_AUDIT_MATRIX row is ``verified`` or ``not_applicable``
* the local test suite passed in this run
* an external ``PK_GATE_RESULTS`` file from pk_core is supplied (``--pk-gate``)
* a human release approval record is supplied (``--approval``) naming an
  approver who is not a service identity

Nothing in this repository can mint the last two; an improved verdict without
them is a defect (see tests/test_v43.py::ReleaseGateTest).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVICE_MARKERS = ("bot", "service", "claude", "ci", "automation", "pipeline")


def evaluate(components: dict, matrix: dict, *, tests_passed: bool,
             pk_gate: dict | None, approval: dict | None) -> dict:
    blockers: list[str] = []
    for c in components["components"]:
        if c["status"] != "COMPLETE":
            blockers.append(f"component {c['id']:>2} {c['name']}: {c['status']}")
    bad = [r["check_id"] for r in matrix["requirements"] if r["status"] not in ("verified", "not_applicable")]
    if bad:
        blockers.append(f"{len(bad)} audit requirements not verified")
    if not tests_passed:
        blockers.append("local test suite did not pass")
    if not pk_gate or pk_gate.get("verdict") != "PASS":
        blockers.append("no PASSing pk_core PK_GATE_RESULTS supplied")
    approver = str((approval or {}).get("approver", ""))
    if not approval or approval.get("decision") != "APPROVE":
        blockers.append("no human release approval supplied")
    elif not approver or set(re.split(r"[^a-z0-9]+", approver.lower())) & set(SERVICE_MARKERS):
        blockers.append("release approval names a service identity or no approver")
    return {"verdict": "GO" if not blockers else "NO_GO", "blockers": blockers}


def _run_tests() -> tuple[bool, str]:
    proc = subprocess.run([sys.executable, "-B", str(ROOT / "tests" / "run_all.py")],
                          capture_output=True, text=True, cwd=str(ROOT), check=False)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
    return proc.returncode == 0, " | ".join(tail)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence"))
    ap.add_argument("--pk-gate")
    ap.add_argument("--approval")
    ap.add_argument("--skip-tests", action="store_true")
    a = ap.parse_args(argv)
    components = json.loads((ROOT / "COMPONENTS_STATUS.json").read_text(encoding="utf-8"))
    matrix = json.loads((ROOT / "POST_AUDIT_MATRIX.json").read_text(encoding="utf-8"))
    passed, summary = (False, "NOT RUN (--skip-tests)") if a.skip_tests else _run_tests()
    load = lambda p: json.loads(Path(p).read_text(encoding="utf-8")) if p else None
    result = evaluate(components, matrix, tests_passed=passed,
                      pk_gate=load(a.pk_gate), approval=load(a.approval))
    manifest = (ROOT / "CHECKSUMS.sha256").read_bytes()
    evidence = {
        "schema": "PK_RELEASE_EVIDENCE/1",
        "element": "INV-44",
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "tests": {"passed": passed, "summary": summary},
        "matrix_summary": matrix["summary"],
        "components": [{k: c[k] for k in ("id", "name", "status")} for c in components["components"]],
        **result,
    }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "RELEASE_EVIDENCE.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    print(f"{result['verdict']}: {len(result['blockers'])} blockers; tests={'PASS' if passed else 'FAIL/NOT RUN'}")
    return 0 if result["verdict"] == "GO" else 3


if __name__ == "__main__":
    raise SystemExit(main())
