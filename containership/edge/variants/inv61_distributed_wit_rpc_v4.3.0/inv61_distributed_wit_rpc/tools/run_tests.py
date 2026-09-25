"""Run the full suite and write evidence/test_results.json (incl. skip reasons)."""
from __future__ import annotations

import json
import pathlib
import sys
import unittest
import warnings

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tests"))
warnings.simplefilter("ignore", ResourceWarning)


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), top_level_dir=str(PKG / "tests"))
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    doc = {"schema": "inv61-tests/1", "python": sys.version.split()[0], "optimize": sys.flags.optimize,
           "ran": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
           "skip_reasons": sorted({f"{t.id().split('.')[0]}: {r}" for t, r in res.skipped}),
           "failed_ids": [t.id() for t, _ in res.failures + res.errors]}
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "test_results.json").write_text(json.dumps(doc, indent=2) + "\n")
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
