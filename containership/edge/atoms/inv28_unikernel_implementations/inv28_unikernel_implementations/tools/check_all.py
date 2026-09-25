"""Every local gate lane in one command - what CI runs (MC-081).

    python -B -m inv28_unikernel_implementations.tools.check_all [--ci] [--with-slow]

Lanes: bootstrap, lint, SAST, secret scan, deps, SBOM, MASTER.md, tests (python), tests (python -O),
coverage, pk_core gate, MC-status traceability, review-due (report only), optional ruff/mypy when installed
(recorded as not_run otherwise - never as passed).  ``--with-slow`` adds bench, soak and mutation.
Writes evidence/CHECK_ALL.json and evidence/TEST_RESULTS.json.  Exit 0 only if every mandatory lane passes.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time

from ._common import EVIDENCE, PARENT, PKG, write_json


def run(args, timeout=1800):
    t = time.time()
    p = subprocess.run(args, capture_output=True, text=True, cwd=str(PARENT), timeout=timeout)
    return p.returncode, p.stdout + p.stderr, round(time.time() - t, 2)


def result_line(out: str) -> dict:
    for line in reversed(out.splitlines()):
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    return {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true")
    ap.add_argument("--with-slow", action="store_true")
    a = ap.parse_args(argv)
    py = [sys.executable, "-B"]
    m = lambda tool, *x: py + ["-m", f"{PKG}.tools.{tool}", *x]  # noqa: E731
    lanes = [("bootstrap", m("bootstrap")), ("lint", m("lint")), ("sast", m("sast")), ("secrets", m("secret_scan")),
             ("deps", m("deps_check")), ("sbom", m("sbom")), ("master", m("master", "--check")),
             ("tests", py + [f"{PKG}/tests/run_all.py"]), ("tests_optimized", py + ["-O", f"{PKG}/tests/run_all.py"]),
             ("coverage", m("coverage")), ("pk_gate", m("pk_gate")), ("review_due", m("review_due"))]
    if a.with_slow:
        lanes += [("bench", m("bench")), ("soak", m("soak")), ("mutation", m("mutation"))]
    report, tests = {}, {}
    for name, args in lanes:
        code, out, secs = run(args)
        report[name] = {"pass": code == 0, "exit": code, "seconds": secs, "tail": out[-300:]}
        if name.startswith("tests"):
            tests[name] = result_line(out)
            write_json(EVIDENCE / "TEST_RESULTS.json", {"schema": "PK_TEST_RESULTS/1", "profiles": tests})
        print(f"{'PASS' if code == 0 else 'FAIL'} {name:16} {secs:7.2f}s")
    optional = {}
    for name, tool, args in (("ruff", "ruff", ["check", "."]), ("mypy", "mypy", ["--config-file", "pyproject.toml", "."])):
        exe = shutil.which(tool)
        if exe:
            t = time.time()
            p = subprocess.run([exe, *args], capture_output=True, text=True, cwd=str(PARENT / PKG), timeout=600)
            ver = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.strip()
            optional[name] = {"pass": p.returncode == 0, "exit": p.returncode, "version": ver,
                              "seconds": round(time.time() - t, 2), "tail": (p.stdout + p.stderr)[-300:]}
        else:
            optional[name] = {"pass": None, "status": "not_run", "reason": f"{tool} not installed"}
        report[name] = {**optional[name], "optional": True}
        print(f"{str(optional[name]['pass']).upper():5} {name:16} (optional)")
    write_json(EVIDENCE / "OPTIONAL_LINTERS.json", {"schema": "PK_OPTIONAL_LINTERS/1", "lanes": optional})
    run(m("manifest"))          # SHA256SUMS/RELEASE_MANIFEST must exist before the traceability check reads them
    code, out, secs = run(m("rtm"))
    report["mc_status"] = {"pass": code == 0, "exit": code, "seconds": secs, "tail": out[-300:]}
    print(f"{'PASS' if code == 0 else 'FAIL'} {'mc_status':16} {secs:7.2f}s")
    mandatory = {k: v for k, v in report.items() if not v.get("optional") and k != "review_due"}
    ok = all(v["pass"] for v in mandatory.values())
    write_json(EVIDENCE / "CHECK_ALL.json", {"schema": "PK_CHECK_ALL/1", "python": sys.version.split()[0],
                                             "lanes": report, "mandatory_pass": ok})
    print("CHECK_ALL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
