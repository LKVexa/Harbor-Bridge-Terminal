"""Run the full suite and emit machine-readable results.  Unexpected skips are failures (WP #61/#64).

    python tools/run_tests.py --out results.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import sys
import time
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
# The only permitted skips, each tied to an approved, unexpired waiver in WAIVERS.json.
ALLOWED_SKIPS = {"test_component.": "W-008"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sys.path[:0] = [str(PKG / "tests"), str(PKG.parent)]
    suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), top_level_dir=str(PKG / "tests"))
    t0 = time.time()
    result = unittest.TextTestRunner(verbosity=0, stream=sys.stderr).run(suite)
    skips = [{"test": t.id(), "reason": r, "waiver": next((w for p, w in ALLOWED_SKIPS.items() if t.id().startswith(p)), None)}
             for t, r in result.skipped]
    unexpected = [s for s in skips if s["waiver"] is None]
    out: dict = {"schema": "PK_TEST_RESULTS/1", "python": platform.python_version(), "optimized": sys.flags.optimize > 0,
           "platform": platform.platform(), "machine": platform.machine(), "duration_s": round(time.time() - t0, 3),
           "run": result.testsRun, "failures": [t.id() for t, _ in result.failures],
           "errors": [t.id() for t, _ in result.errors], "skipped": skips, "unexpected_skips": unexpected}
    out["passed"] = result.testsRun - len(out["failures"]) - len(out["errors"]) - len(skips)
    out["ok"] = result.wasSuccessful() and not unexpected
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("run", "passed", "ok")}))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
