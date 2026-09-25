"""Run the suite and emit machine-readable results (used by the release gate)."""
from __future__ import annotations

import json
import pathlib
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT / "tests"))
    result = unittest.TestResult()
    t0 = time.time()
    suite.run(result)
    out = {
        "optimized": not __debug__, "python": sys.version.split()[0], "seconds": round(time.time() - t0, 2),
        "run": result.testsRun, "failures": [t.id() for t, _ in result.failures],
        "errors": [t.id() for t, _ in result.errors], "skipped": [{"test": t.id(), "reason": r} for t, r in result.skipped],
        "details": [tb[-800:] for _, tb in result.failures + result.errors][:10],
    }
    print(json.dumps(out))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
