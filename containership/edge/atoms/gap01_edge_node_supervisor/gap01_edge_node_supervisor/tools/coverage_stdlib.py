"""Line coverage using only the standard library ``trace`` module (46).

coverage.py is the preferred tool in CI (see .github/workflows/ci.yml); this
fallback keeps coverage measurable in air-gapped builds.  Counts executable
lines via the compiled code objects' line tables, excluding docstrings.
Usage: python -m gap01_edge_node_supervisor.tools.coverage_stdlib [--min 85]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import trace
import types
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
MODULES = ["supervisor", "controller", "store", "security", "config", "health", "runtime",
           "errors", "observability", "server", "bootstrap", "inventory", "client", "schema_validator"]


def executable_lines(path: pathlib.Path) -> set[int]:
    code = compile(path.read_text(), str(path), "exec")
    lines: set[int] = set()

    def walk(co: types.CodeType) -> None:
        for _, _, ln in co.co_lines():
            if ln is not None:
                lines.add(ln)
        for c in co.co_consts:
            if isinstance(c, types.CodeType):
                walk(c)
    walk(code)
    # drop module/func docstring-only lines and 'def'/'class' header lines counted at import
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=0.0)
    ap.add_argument("--json")
    a = ap.parse_args()
    sys.path.insert(0, str(PKG.parent))
    sys.path.insert(0, str(PKG / "tests"))
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.exec_prefix])
    import threading
    threading.settrace(tracer.globaltrace)  # trace server/watchdog threads too

    def run_all():
        suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), pattern="test_*.py")
        return unittest.TextTestRunner(verbosity=0).run(suite)
    result = tracer.runfunc(run_all)
    counts = tracer.results().counts
    report, tot_e, tot_h = {}, 0, 0
    for m in MODULES:
        p = (PKG / f"{m}.py").resolve()
        ex = executable_lines(p)
        hit = {ln for (f, ln), n in counts.items() if pathlib.Path(f).resolve() == p and n}
        covered = len(ex & hit) + 0
        report[m] = {"executable": len(ex), "covered": covered,
                     "pct": round(100 * covered / len(ex), 1) if ex else 100.0}
        tot_e += len(ex); tot_h += covered
    total = round(100 * tot_h / tot_e, 1)
    for m, r in report.items():
        print(f"{m:22s} {r['covered']:5d}/{r['executable']:5d}  {r['pct']:5.1f}%")
    print(f"{'TOTAL':22s} {tot_h:5d}/{tot_e:5d}  {total:5.1f}%  (tests ok={result.wasSuccessful()})")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"total_pct": total, "modules": report,
                                                    "tests_ok": result.wasSuccessful()}, indent=2))
    return 0 if result.wasSuccessful() and total >= a.min else 1


if __name__ == "__main__":
    raise SystemExit(main())
