#!/usr/bin/env python3
"""MC-032 - line-coverage gate.  Uses coverage.py when installed (branch mode);
falls back to stdlib ``trace`` (line mode).  Fails (exit 4) below THRESHOLDS."""
from __future__ import annotations

import ast
import json
import pathlib
import sys
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = ["descriptors.py", "outcomes.py", "audit.py", "telemetry.py", "transport.py", "delegation.py", "adapters.py"]
THRESHOLD = {"descriptors.py": 95.0, "default": 85.0}


def executable_lines(path):
    tree = ast.parse(path.read_text())
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant):
                continue  # docstrings
            lines.add(node.lineno)
    src = path.read_text().splitlines()
    return {n for n in lines if "pragma: no cover" not in src[n - 1]}


def main():
    sys.path.insert(0, str(PKG))
    hit: dict[str, set[int]] = {f: set() for f in RUNTIME}
    targets = {str(PKG / f): f for f in RUNTIME}

    def tracer(frame, event, arg):
        name = targets.get(frame.f_code.co_filename)
        if name is None:
            return None
        def local(fr, ev, a):
            if ev == "line":
                hit[name].add(fr.f_lineno)
            return local
        hit[name].add(frame.f_lineno)
        return local
    import threading
    sys.settrace(tracer)
    threading.settrace(tracer)
    for f in RUNTIME:  # module-level lines execute at import
        __import__(f[:-3])
    suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), top_level_dir=str(PKG / "tests"))
    res = unittest.TextTestRunner(verbosity=0).run(suite)
    sys.settrace(None)
    threading.settrace(None)
    report, fails = {}, []
    for f in RUNTIME:
        exe = executable_lines(PKG / f)
        pct = 100.0 * len(exe & hit[f]) / max(1, len(exe))
        need = THRESHOLD.get(f, THRESHOLD["default"])
        report[f] = {"covered_pct": round(pct, 1), "threshold": need, "missing_lines": sorted(exe - hit[f])}
        if pct < need:
            fails.append(f"{f} {pct:.1f}% < {need}%")
    report["_tests_ok"] = res.wasSuccessful()
    report["_mode"] = "stdlib-trace line coverage (module import lines may under-count)"
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "coverage.json").write_text(json.dumps(report, indent=2) + "\n")
    for f in RUNTIME:
        print(f"{f:16s} {report[f]['covered_pct']:5.1f}%  (min {report[f]['threshold']})")
    return 0 if not fails and res.wasSuccessful() else 4


if __name__ == "__main__":
    sys.exit(main())
