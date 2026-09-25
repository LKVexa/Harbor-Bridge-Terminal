"""Run one unittest suite and print a JSON summary (used by tools/gate.py and CI)."""

import json
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(suite: str) -> int:
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)
    t0 = time.time()
    tests = unittest.defaultTestLoader.discover(f"tests/{suite}", top_level_dir=".")
    res = unittest.TextTestRunner(stream=open(os.devnull, "w"), verbosity=0).run(tests)  # noqa: SIM115
    out = {
        "suite": suite,
        "ran": res.testsRun,
        "failures": [t.id() for t, _ in res.failures],
        "errors": [t.id() for t, _ in res.errors],
        "skipped": [{"id": t.id(), "reason": r} for t, r in res.skipped],
        "ok": res.wasSuccessful(),
        "seconds": round(time.time() - t0, 3),
        "optimized": sys.flags.optimize > 0,
    }
    print(json.dumps(out))
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
