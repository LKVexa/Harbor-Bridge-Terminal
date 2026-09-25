"""Run every INV-64 test suite and emit PK_APP_TESTS/1 (MC-29/MC-37 evidence).

    python inv64_application_model/tests/run_all.py [--json OUT] [--standalone-only]

Suites: test_manifest (core, stdlib), test_v43 (4.3.0 controls), test_component
(pk_core integration). A missing pk_core makes test_component FAIL (by design,
4.2.0 fix) and its conformance cases SKIP; skips are counted and the gate
treats any skip in the certification run as a failure.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
SUITES = ["test_manifest", "test_v43", "test_component"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--standalone-only", action="store_true")
    a = ap.parse_args(argv)
    suites = SUITES[:2] if a.standalone_only else SUITES
    per, total = [], {"run": 0, "failures": 0, "errors": 0, "skipped": 0}
    t0 = time.time()
    for name in suites:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(f"inv64_application_model.tests.{name}")
        res = unittest.TextTestRunner(stream=open("/dev/null" if sys.platform != "win32" else "NUL", "w"), verbosity=0).run(suite)
        row = {"suite": name, "run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors),
               "skipped": len(res.skipped),
               "problems": [f"{t.id()}: {tb.strip().splitlines()[-1]}" for t, tb in res.failures + res.errors][:20],
               "skips": [f"{t.id()}: {why}" for t, why in res.skipped][:20]}
        per.append(row)
        for k in total:
            total[k] += row[k]
    ok = total["failures"] == 0 and total["errors"] == 0
    out = {"schema": "PK_APP_TESTS/1", "python": sys.version.split()[0], "optimize": sys.flags.optimize,
           "suites": per, **total, "duration_s": round(time.time() - t0, 2),
           "result": "PASS" if ok and total["skipped"] == 0 else "FAIL",
           "note": "standalone-only run" if a.standalone_only else "full run (includes pk_core integration)"}
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    for r in per:
        print(f"{r['suite']:16} run={r['run']:3} fail={r['failures']} err={r['errors']} skip={r['skipped']}")
        for p in r["problems"]:
            print("   !", p)
    print(out["result"], {k: out[k] for k in total})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
