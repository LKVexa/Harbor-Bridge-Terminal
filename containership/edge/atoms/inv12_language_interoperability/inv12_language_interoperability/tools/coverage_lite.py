"""Stdlib line + arc coverage for ``canon/`` (no coverage.py available offline).

Executable lines are taken from compiled code objects (``co_lines``); executed
lines/arcs are recorded with ``sys.settrace`` (and ``threading.settrace``) while
the unit suite runs.  Output: per-file line coverage, arcs observed, and the
list of never-executed lines so error/lifecycle branches can be audited.

Usage: python tools/coverage_lite.py [--min 85] [--out evidence/coverage.json]
"""
import argparse
import json
import pathlib
import sys
import threading
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANON = ROOT / "canon"


def executable_lines(path):
    code = compile(path.read_text(), str(path), "exec")
    lines = set()
    stack = [code]
    while stack:
        c = stack.pop()
        for _, _, ln in c.co_lines():
            if ln is not None:
                lines.add(ln)
        stack += [k for k in c.co_consts if isinstance(k, types.CodeType)]
    # drop docstring/def header-only artefacts: keep lines with real statements
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=90.0)
    ap.add_argument("--out", default=str(ROOT / "evidence/coverage.json"))
    a = ap.parse_args()
    hits, arcs, last = {}, set(), {}
    prefix = str(CANON)

    def tracer(frame, event, arg):
        fn = frame.f_code.co_filename
        if not fn.startswith(prefix):
            return None

        def local(fr, ev, _a):
            if ev == "line":
                hits.setdefault(fr.f_code.co_filename, set()).add(fr.f_lineno)
                k = id(fr)
                arcs.add((fr.f_code.co_filename, last.get(k, -1), fr.f_lineno))
                last[k] = fr.f_lineno
            return local
        return local

    import os
    os.environ["INV12_COVERAGE"] = "1"
    sys.path.insert(0, str(ROOT.parent))
    for m in [m for m in sys.modules if m.startswith(ROOT.name)]:
        del sys.modules[m]
    threading.settrace(tracer)
    sys.settrace(tracer)
    suite = unittest.defaultTestLoader.loadTestsFromName(f"{ROOT.name}.tests.test_canon")
    threading.settrace(tracer)
    sys.settrace(tracer)
    import io
    buf = io.StringIO()
    result = unittest.TextTestRunner(verbosity=0, stream=buf).run(suite)
    sys.settrace(None)
    threading.settrace(None)
    files, tot_e, tot_h = {}, 0, 0
    for p in sorted(CANON.glob("*.py")):
        ex = executable_lines(p)
        h = hits.get(str(p), set()) & ex
        # ``from __future__``/module docstring line 1 is always "executed" on import
        files[p.name] = {"lines": len(ex), "hit": len(h),
                         "percent": round(100 * len(h) / max(1, len(ex)), 1),
                         "missed": sorted(ex - h)}
        tot_e += len(ex)
        tot_h += len(h)
    total = round(100 * tot_h / max(1, tot_e), 1)
    failures = [str(t) + " :: " + tb[-1500:] for t, tb in result.failures + result.errors]
    rep = {"failures": failures, "tests_run": result.testsRun, "tests_failed": len(result.failures) + len(result.errors),
           "total_line_percent": total, "arcs_observed": len(arcs), "files": files,
           "threshold": a.min, "verdict": "PASS" if total >= a.min and result.wasSuccessful() else "FAIL"}
    pathlib.Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("failures", "tests_run", "tests_failed", "total_line_percent", "arcs_observed", "verdict")}))
    for n, f in files.items():
        print(f"  {n:18s} {f['percent']:5.1f}%  ({f['hit']}/{f['lines']})")
    sys.exit(0 if rep["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
