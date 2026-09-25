"""Run a unittest discovery and emit per-test outcomes as JSON (no false greens:
skips are reported as SKIPPED, never PASS)."""
from __future__ import annotations

import json
import sys
import time
import unittest

sys.dont_write_bytecode = True


class Rec(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = []
        self._t = 0.0

    def startTest(self, test):
        self._t = time.perf_counter()
        super().startTest(test)

    def _row(self, test, outcome, detail=""):
        self.rows.append({"id": test.id(), "outcome": outcome, "ms": round((time.perf_counter() - self._t) * 1000, 2), "detail": detail[-2000:]})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._row(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._row(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._row(test, "ERROR", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._row(test, "SKIPPED", reason)

    def addSubTest(self, test, sub, err):
        super().addSubTest(test, sub, err)
        if err is not None:
            self._row(sub, "FAIL", self._exc_info_to_string(err, test))


def main() -> int:
    start, pattern, out = sys.argv[1], sys.argv[2], sys.argv[3]
    suite = unittest.defaultTestLoader.discover(start, pattern=pattern, top_level_dir=start)
    runner = unittest.TextTestRunner(resultclass=Rec, verbosity=0, stream=sys.stderr)
    res = runner.run(suite)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"optimize": sys.flags.optimize, "python": sys.version.split()[0], "tests": res.rows,
                   "summary": {"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped)}},
                  fh, indent=1)
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
