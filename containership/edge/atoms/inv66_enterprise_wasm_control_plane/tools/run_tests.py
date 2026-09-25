"""Run unittest discovery and emit per-test machine-readable results (used by tools/ci.py).

    python tools/run_tests.py --start tests/unit --out result.json
Exit 0 only if nothing failed or errored.  Skips are reported with their reason and never counted as passes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows: dict[str, dict] = {}
        self._t0 = {}

    def startTest(self, test):
        self._t0[test.id()] = time.perf_counter()
        super().startTest(test)

    def _row(self, test, outcome, detail=None):
        self.rows[test.id()] = {"outcome": outcome, "seconds": round(time.perf_counter() - self._t0.get(test.id(), time.perf_counter()), 4),
                                **({"detail": detail[:2000]} if detail else {})}

    def addSuccess(self, test):
        super().addSuccess(test); self._row(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err); self._row(test, "fail", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err); self._row(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._row(test, "skip", reason)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", action="append", default=[])
    ap.add_argument("--module", action="append", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT.parent))
    suite = unittest.TestSuite()
    for s in a.start:
        suite.addTests(unittest.defaultTestLoader.discover(s, top_level_dir=str(ROOT)))
    for m in a.module:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(m))
    runner = unittest.TextTestRunner(stream=open(os.devnull, "w"), resultclass=Collect, verbosity=0)  # noqa: SIM115
    res = runner.run(suite)
    rows = res.rows
    summary = {k: sum(1 for r in rows.values() if r["outcome"] == k) for k in ("pass", "fail", "error", "skip")}
    Path(a.out).write_text(json.dumps({"summary": summary, "optimize": sys.flags.optimize, "tests": rows}, indent=1))
    print(json.dumps(summary))
    return 0 if not (summary["fail"] or summary["error"]) else 1


if __name__ == "__main__":
    sys.exit(main())
