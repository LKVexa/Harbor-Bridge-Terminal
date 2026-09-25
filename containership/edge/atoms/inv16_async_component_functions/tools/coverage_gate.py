"""Stdlib line + arc coverage gate (closure #34).

Traces the full unittest suite in-process (all threads) and reports, per
production module, executable-line coverage and observed branch arcs.  Lines
marked ``pragma: no cover`` are excluded and listed for review.  Gate:
``--min-line`` (default 90) over production modules, plus every function in
``CRITICAL`` must be fully line-covered.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading
import types
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
PROD = ["runtime.py", "bridge.py", "abi.py", "declare.py", "lowering.py", "observability.py", "preflight.py"]
CRITICAL = {"runtime.py": ["invoke", "complete", "cancel", "cancel_all", "trap_all", "_classify_missing",
                           "_bury", "_release_slot", "_drop_nonterminal", "add_terminal_listener"],
            "bridge.py": ["_call", "call"]}


def executable(code: types.CodeType, out: dict):
    for _s, _e, ln in code.co_lines():
        if ln and ln != code.co_firstlineno:
            out.setdefault(code.co_name, set()).add(ln)
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            executable(c, out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-line", type=float, default=90.0)
    ap.add_argument("--out", default=str(PKG / "evidence" / "coverage.json"))
    a = ap.parse_args(argv)
    files = {str((PKG / p).resolve()): p for p in PROD}
    hits: dict[str, set] = {p: set() for p in PROD}
    arcs: dict[str, set] = {p: set() for p in PROD}

    def tracer(frame, event, arg):
        fn = files.get(frame.f_code.co_filename)
        if fn is None:
            return None
        last = [frame.f_lineno]

        def local(fr, ev, ar):
            if ev == "line":
                hits[fn].add(fr.f_lineno)
                arcs[fn].add((last[0], fr.f_lineno))
                last[0] = fr.f_lineno
            return local
        return local

    sys.path.insert(0, str(PKG / "tests"))
    sys.path.insert(0, str(PKG.parent))
    threading.settrace(tracer)
    sys.settrace(tracer)          # before discovery so module-level lines are traced too
    try:
        suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), top_level_dir=str(PKG / "tests"))
        result = unittest.TextTestRunner(stream=open("/dev/null", "w"), verbosity=0).run(suite)
    finally:
        sys.settrace(None)
        threading.settrace(None)
    report = {"schema": "inv16.coverage/1", "tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors),
              "failed_tests": [str(t) for t, _ in result.failures + result.errors],
              "modules": {}, "critical_gaps": {}, "excluded": {}}
    tot_exec = tot_hit = 0
    for p in PROD:
        src = (PKG / p).read_text().splitlines()
        code = compile("\n".join(src), str((PKG / p).resolve()), "exec")
        per_fn: dict[str, set] = {}
        executable(code, per_fn)
        excl = {i for i, line in enumerate(src, 1) if "pragma: no cover" in line}
        ex = set().union(*per_fn.values()) - excl
        hit = hits[p] & ex
        tot_exec += len(ex)
        tot_hit += len(hit)
        report["modules"][p] = {"lines": len(ex), "covered": len(hit),
                                "pct": round(100 * len(hit) / max(1, len(ex)), 1),
                                "missing": sorted(ex - hit), "arcs_observed": len(arcs[p])}
        report["excluded"][p] = sorted(excl)
        for fn in CRITICAL.get(p, []):
            miss = sorted((per_fn.get(fn, set()) - excl) - hits[p])
            if miss:
                report["critical_gaps"][f"{p}::{fn}"] = miss
    report["total_pct"] = round(100 * tot_hit / max(1, tot_exec), 1)
    report["pass"] = (report["total_pct"] >= a.min_line and not report["critical_gaps"]
                      and report["failures"] == report["errors"] == 0)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    for p, m in report["modules"].items():
        print(f"{p:18} {m['pct']:5.1f}%  missing={m['missing'][:12]}{'...' if len(m['missing']) > 12 else ''}")
    print("critical gaps:", report["critical_gaps"] or "none")
    print(f"TOTAL {report['total_pct']}%  gate>={a.min_line}  {'PASS' if report['pass'] else 'FAIL'}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
