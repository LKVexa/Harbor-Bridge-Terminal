"""One-command conformance/evidence run (INV-68 MC-32, MC-40, MC-41; C090, C100).

    python -m inv68_resource_packing.tools.run_evidence [--out evidence/] [--release DIR] [--quick]
           [--certification] [--soak-seconds N] [--pk-gate FILE] [--approval FILE] [--today YYYY-MM-DD]

Runs every producer named in ``ops/GATE_POLICY.json`` as a subprocess, captures
stdout/stderr/exit/duration into ``<out>/logs/`` and ``<out>/RUN.json``, builds and
verifies the release, regenerates the item ledger / component status /
requirements matrix, then runs the exit gate.  A producer that crashes leaves a
FAIL evidence file, never a missing one.  Exit status is the gate's
(0 GO, 2 CONDITIONAL_GO, 3 NO_GO).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from .common import PARENT, PKG, machine, revision, source_digest, write

M = "inv68_resource_packing"


def run(name: str, args: list[str], logs: Path) -> dict:
    t0 = time.time()
    p = subprocess.run([sys.executable, *args], cwd=str(PARENT), capture_output=True, text=True)
    (logs / f"{name}.log").write_text(f"$ python {' '.join(args)}\nexit={p.returncode}\n--- stdout\n{p.stdout}"
                                      f"\n--- stderr\n{p.stderr}", encoding="utf-8")
    return {"step": name, "exit": p.returncode, "seconds": round(time.time() - t0, 2), "stdout": p.stdout, "stderr": p.stderr}


def ensure(path: Path, schema: str, step: dict) -> None:
    if not path.is_file():
        write(path, {"schema": schema, "result": "FAIL", "reason": f"producer exited {step['exit']} without evidence",
                     "log": f"logs/{step['step']}.log"})


def tests(out: Path, logs: Path, optimized: bool) -> dict:
    args = (["-O"] if optimized else []) + ["-m", "unittest", "discover", "-s", f"{M}/tests", "-v"]
    step = run("tests_O" if optimized else "tests", args, logs)
    text = step["stderr"]
    ran = int(m.group(1)) if (m := re.search(r"Ran (\d+) tests?", text)) else 0
    skipped = int(m.group(1)) if (m := re.search(r"skipped=(\d+)", text)) else 0
    failures = int(m.group(1)) if (m := re.search(r"failures=(\d+)", text)) else 0
    errors = int(m.group(1)) if (m := re.search(r"errors=(\d+)", text)) else 0
    skip_reasons = sorted(set(re.findall(r"skipped '([^']+)'", text)))
    ok = step["exit"] == 0 and ran > 0
    doc = {"schema": "PK_PACK_TESTS/1", "mode": "python -O" if optimized else "normal", "ran": ran,
           "passed": ran - skipped - failures - errors, "failures": failures, "errors": errors, "skipped": skipped,
           "skip_reasons": skip_reasons,
           "result": "PASS" if ok and skipped == 0 else "FAIL",
           "reason": None if ok and skipped == 0 else (f"{skipped} skipped (pk_core conformance tests cannot run: "
                                                       "MC-02); skips never satisfy the gate" if ok else "test failures")}
    write(out / ("TESTS_O.json" if optimized else "TESTS.json"), doc)
    return step


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    ap.add_argument("--release", default=str(PKG.parent / "inv68_release"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--certification", action="store_true")
    ap.add_argument("--soak-seconds", type=float, default=20.0)
    ap.add_argument("--pk-gate")
    ap.add_argument("--approval")
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    logs = out / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    o = ["--out", str(out)]
    steps = [tests(out, logs, False), tests(out, logs, True)]
    producers = [
        ("schemas", [f"{M}.tools.schemas_check", *o], "SCHEMAS.json", "PK_PACK_SCHEMAS/1"),
        ("fuzz", [f"{M}.tools.fuzz", "--cases", "600" if a.quick else "3000", *o], "FUZZ.json", "PK_PACK_FUZZ/1"),
        ("faults", [f"{M}.tools.faults", *o], "FAULTS.json", "PK_PACK_FAULTS/1"),
        ("stress", [f"{M}.tools.stress", "--soak-seconds", str(3 if a.quick else a.soak_seconds), *o], "STRESS.json",
         "PK_PACK_STRESS/1"),
        ("bench", [f"{M}.tools.bench", *(["--quick"] if a.quick else []), *o], "PERF.json", "PK_PACK_PERF/1"),
        ("integration", [f"{M}.tools.integration", *o], "INTEGRATION.json", "PK_PACK_INTEGRATION/1"),
        ("secret_scan", [f"{M}.tools.secret_scan", *o], "SECRET_SCAN.json", "PK_PACK_SECRET_SCAN/1"),
        ("source", [f"{M}.tools.source_integrity", *o], "SOURCE_CHECK.json", "PK_PACK_SOURCE_CHECK/1"),
        ("preflight", [f"{M}.tools.preflight", *o], "PREFLIGHT.json", "PK_PACK_PREFLIGHT/1"),
        ("preflight_cert", [f"{M}.tools.preflight", "--certification", *o], "PREFLIGHT_CERT.json", "PK_PACK_PREFLIGHT/1"),
        ("drills", [f"{M}.tools.drills", *o], "ROLLBACK_DRILL.json", "PK_PACK_ROLLBACK_DRILL/1"),
        ("governance", [f"{M}.tools.governance_check", *o, *(["--today", a.today] if a.today else [])],
         "GOVERNANCE.json", "PK_PACK_GOVERNANCE/1"),
    ]
    for name, args, file, schema in producers:
        step = run(name, ["-m", *args], logs)
        ensure(out / file, schema, step)
        steps.append(step)
    for extra, schema in (("SOAK.json", "PK_PACK_SOAK/1"), ("PERF_GATE.json", "PK_PACK_PERF_GATE/1"),
                          ("INTEGRATION_REAL.json", "PK_PACK_INTEGRATION_REAL/1"),
                          ("EMERGENCY_DISABLE.json", "PK_PACK_EMERGENCY_DISABLE/1"),
                          ("BACKUP_RESTORE.json", "PK_PACK_BACKUP_RESTORE/1"), ("ALERTS.json", "PK_PACK_ALERTS_CHECK/1")):
        ensure(out / extra, schema, {"step": "(companion)", "exit": "n/a"})
    steps.append(run("slo", ["-m", f"{M}.tools.slo_report", "--evidence", str(out)], logs))
    ensure(out / "SLO.json", "PK_PACK_SLO/1", steps[-1])
    rel = Path(a.release).resolve()
    steps.append(run("release_build", ["-m", f"{M}.tools.release", "build", "--out", str(rel), "--evidence", str(out)], logs))
    ensure(out / "BUILD.json", "PK_PACK_BUILD/1", steps[-1])
    steps.append(run("install_check", ["-m", f"{M}.tools.release", "install-check", "--release", str(rel),
                                       "--evidence-out", str(out)], logs))
    ensure(out / "INSTALL.json", "PK_PACK_INSTALL/1", steps[-1])
    steps.append(run("release_verify", ["-m", f"{M}.tools.release", "verify", "--release", str(rel),
                                        "--evidence-out", str(out)], logs))
    ensure(out / "RELEASE_VERIFY.json", "PK_PACK_RELEASE_VERIFY/1", steps[-1])
    steps.append(run("ledger", ["-m", f"{M}.tools.build_ledger", "--evidence", str(out)], logs))
    gate_args = ["-m", f"{M}.release_gate", "--evidence", str(out)]
    for flag, val in (("--pk-gate", a.pk_gate), ("--approval", a.approval), ("--today", a.today)):
        if val:
            gate_args += [flag, val]
    gate = run("gate", gate_args, logs)
    steps.append(gate)
    write(out / "RUN.json", {"schema": "PK_PACK_RUN/1", "mode": "certification" if a.certification else
                             ("quick" if a.quick else "standard"), "machine": machine(), "revision": revision(),
                             "source_digest": source_digest(), "release_dir": str(rel),
                             "steps": [{k: s[k] for k in ("step", "exit", "seconds")} for s in steps],
                             "gate_exit": gate["exit"], "result": "RECORDED"})
    print(gate["stdout"])
    return gate["exit"]


if __name__ == "__main__":
    raise SystemExit(main())
