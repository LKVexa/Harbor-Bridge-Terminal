"""Line coverage of the runtime modules with the stdlib ``trace`` module (MC-092, MC-079).

    python -B -m inv27_unikernel_execution.tools.coverage_check [--threshold N]

Runs the seal, parser, service and platform suites in-process under ``trace.Trace`` and reports
executed / executable lines per runtime module (executable lines from ``trace``'s own line finder).
Fails below the threshold in pyproject.toml ``[tool.inv27.lint] coverage_threshold``.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import tomllib
import trace
import unittest

from ._refs import ROOT
from .deps_check import runtime_modules

SUITES = ("test_seal", "test_parser", "test_service", "test_platform", "test_runtime")


def measure() -> dict:
    sys.path.insert(0, str(ROOT / "tests"))
    sys.dont_write_bytecode = True
    tracer = trace.Trace(count=1, trace=0)
    result = unittest.TestResult()
    pkg = ROOT.name
    for name in [m for m in sys.modules if m == pkg or m.startswith(pkg + ".")]:
        if not name.startswith(pkg + ".tools"):
            del sys.modules[name]          # re-import under the tracer so module-level lines count

    def go():
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(s) for s in SUITES)
        suite.run(result)
    threading.settrace(tracer.globaltrace)
    try:
        tracer.runfunc(go)
    finally:
        threading.settrace(None)
    counts = tracer.results().counts
    per = {}
    for rel in runtime_modules():
        path = str((ROOT / rel).resolve())
        exe = set(trace._find_executable_linenos(path))       # noqa: SLF001 - stdlib helper
        hit = {ln for (f, ln), c in counts.items() if f == path and c}
        per[rel] = {"executable": len(exe), "executed": len(exe & hit),
                    "pct": round(100 * len(exe & hit) / len(exe), 1) if exe else 100.0}
    tot_e = sum(v["executable"] for v in per.values())
    tot_h = sum(v["executed"] for v in per.values())
    return {"schema": "PK_COVERAGE/1", "tool": "stdlib trace", "suites": SUITES, "tests_run": result.testsRun,
            "tests_failed": len(result.failures) + len(result.errors), "total_pct": round(100 * tot_h / tot_e, 1),
            "modules": per}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    thr = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["inv27"]["lint"]["coverage_threshold"]
    ap.add_argument("--threshold", type=float, default=thr)
    ap.add_argument("--check", action="store_true", help="do not write evidence")
    a = ap.parse_args(argv)
    r = measure()
    r["threshold"] = a.threshold
    r["pass"] = r["total_pct"] >= a.threshold and r["tests_failed"] == 0
    if not a.check:
        (ROOT / "evidence" / "COVERAGE.json").write_text(json.dumps(r, indent=1))
    for m, v in sorted(r["modules"].items(), key=lambda kv: kv[1]["pct"]):
        print(f"{v['pct']:6.1f}%  {m}")
    print("COVERAGE", "PASS" if r["pass"] else "FAIL", r["total_pct"], "threshold", a.threshold)
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
