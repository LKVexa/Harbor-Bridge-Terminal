"""Run the full suite and write ``test-report.json`` with one outcome per test id.

Test ids look like ``tests.test_store::StoreTests.test_live_lease_blocks_second_owner``.
Outcomes: passed | failed | error | skipped.  The acceptance gate (MC-57) counts
only ``passed``; a skip is never evidence.

    python3 tools/run_tests.py [--out test-report.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unittest

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(PKG))


class _Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.outcomes: dict[str, str] = {}

    @staticmethod
    def _id(test) -> str:
        parts = test.id().split(".")
        # <pkg>.tests.<module>.<Class>.<method>
        return f"tests.{parts[-3]}::{parts[-2]}.{parts[-1]}"

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.setdefault(self._id(test), "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[self._id(test)] = "failed"

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes[self._id(test)] = "error"

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[self._id(test)] = "skipped"

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.outcomes[self._id(test)] = "failed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(PKG, "test-report.json"))
    a = ap.parse_args()
    name = os.path.basename(PKG)
    suite = unittest.defaultTestLoader.discover(os.path.join(PKG, "tests"), top_level_dir=os.path.dirname(PKG),
                                                pattern="test_*.py")
    t0 = time.time()
    runner = unittest.TextTestRunner(resultclass=_Result, verbosity=1)
    res = runner.run(suite)
    counts: dict[str, int] = {}
    for v in res.outcomes.values():
        counts[v] = counts.get(v, 0) + 1
    report = {"schema": "INV57_TEST_REPORT/1", "package": name, "python": sys.version.split()[0],
              "optimized": bool(sys.flags.optimize), "duration_s": round(time.time() - t0, 2),
              "counts": counts, "tests": dict(sorted(res.outcomes.items()))}
    with open(a.out, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
