"""Run a unittest selection and print a JSON summary (used by tools/ci.py).

    python tests/run_suite.py <pattern> [<pattern> ...]
Exit status: 0 only if every test passed AND no test outside the external
pk_core adapter (test_component.py) was skipped - skips never count as passes.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ALLOWED_SKIP_MODULES = {"test_component"}


def main(patterns: list[str]) -> int:
    sys.path.insert(0, str(HERE))
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for pat in patterns or ["test_*.py"]:
        suite.addTests(loader.discover(str(HERE), pattern=pat, top_level_dir=str(HERE)))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    skipped = [str(t.id()) for t, _ in result.skipped]
    bad_skips = [s for s in skipped if s.split(".")[0] not in ALLOWED_SKIP_MODULES]
    summary = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "skipped": skipped, "disallowed_skips": bad_skips,
               "failed_ids": [t.id() for t, _ in result.failures + result.errors]}
    print(json.dumps(summary))
    if result.failures or result.errors:
        sys.stderr.write(stream.getvalue())
    return 0 if result.wasSuccessful() and not bad_skips else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
