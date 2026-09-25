"""Line coverage of the runtime modules under the full test profile, stdlib ``trace`` only (MC-053).

    python -B -m inv28_unikernel_implementations.tools.coverage [--threshold 85]

Executable lines come from the compiled code objects (co_lines), so docstrings/blank lines never count.
Threshold applies to the runtime modules (tools/, tests/, fixtures and the deprecated v1 shim excluded
from the denominator are listed in the output, never silently).  evidence/COVERAGE.json.
"""
from __future__ import annotations

import argparse
import io
import sys
import threading
import types
import unittest
import warnings
from contextlib import redirect_stderr

from ._common import EVIDENCE, ROOT, RUNTIME_MODULES, ensure_path, write_json

MEASURED = RUNTIME_MODULES + ("cli", "fixtures")


CO_NEWLOCALS = 0x2


def executable_lines(path) -> set[int]:
    """Lines inside function bodies only.  Module and class bodies execute at import - before the tracer can
    be installed, because importing the tools package imports the runtime - so counting them would report
    import-time lines as missed.  The measure is therefore *function-body* line coverage (stated in output)."""
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    lines: set[int] = set()
    stack = [code]
    while stack:
        co = stack.pop()
        if co.co_flags & CO_NEWLOCALS:
            lines.update(ln for _, _, ln in co.co_lines() if ln is not None and ln != co.co_firstlineno)
        stack.extend(c for c in co.co_consts if isinstance(c, types.CodeType))
    return lines


def run(threshold: float) -> dict:
    ensure_path()
    warnings.simplefilter("ignore", DeprecationWarning)
    files = {str((ROOT / f"{m}.py").resolve()): m for m in MEASURED}
    hit: dict = {f: set() for f in files}

    def tracer(frame, event, arg):
        f = frame.f_code.co_filename
        if f in files:
            if event == "line":
                hit[f].add(frame.f_lineno)
            return tracer
        return None
    sys.settrace(tracer)
    threading.settrace(tracer)
    try:
        sys.path.insert(0, str(ROOT / "tests"))
        import run_all  # noqa: F401  (module import only builds the suite list)
        suite = unittest.TestSuite()
        for name in run_all.MODULES:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
        with redirect_stderr(io.StringIO()):
            res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        sys.settrace(None)
        threading.settrace(None)
    per, tot_e, tot_h = {}, 0, 0
    for f, mod in sorted(files.items(), key=lambda kv: kv[1]):
        ex = executable_lines(ROOT / f"{mod}.py")
        h = hit[f] & ex
        per[mod] = {"lines": len(ex), "hit": len(h), "pct": round(100 * len(h) / max(len(ex), 1), 1),
                    "missed": sorted(ex - h)[:60]}
        if mod in RUNTIME_MODULES:
            tot_e += len(ex)
            tot_h += len(h)
    total = round(100 * tot_h / max(tot_e, 1), 1)
    return {"schema": "PK_COVERAGE/1", "tool": "tools/coverage.py (stdlib settrace, function-body line coverage)",
            "tests_ok": res.wasSuccessful(), "tests_run": res.testsRun, "runtime_total_pct": total,
            "threshold_pct": threshold, "pass": res.wasSuccessful() and total >= threshold,
            "denominator": list(RUNTIME_MODULES), "reported_not_gated": ["cli", "fixtures"],
            "excluded": ["component.py (pk_core lane)", "contract.py (data)", "tools/", "tests/"], "modules": per}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=85.0)
    a = ap.parse_args(argv)
    r = run(a.threshold)
    write_json(EVIDENCE / "COVERAGE.json", r)
    for m, d in r["modules"].items():
        print(f"COVERAGE {m:14} {d['pct']:5}% ({d['hit']}/{d['lines']})")
    print("COVERAGE", "PASS" if r["pass"] else "FAIL", f"runtime={r['runtime_total_pct']}% threshold={a.threshold}%")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
