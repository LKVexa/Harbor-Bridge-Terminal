"""Repository-local verification entry point for INV-43 (4.3.0).

    python verify.py            standalone verification
    python -O verify.py         same, with asserts stripped (must still pass)

Environment:
    PK_REQUIRE_CORE=1            missing pk_core becomes a hard failure (release CI)
    INV43_REQUIRE_JSONSCHEMA=1   missing jsonschema becomes a hard failure (release CI)
    INV43_FUZZ_SEED / INV43_FUZZ_N / INV43_SOAK_NODES / INV43_SOAK_DECISIONS  scale knobs
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import os
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True  # verification must not mutate the package it verifies
ROOT = pathlib.Path(__file__).resolve().parent
PARENT = ROOT.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

EXPECTED_VERSION = "4.3.0"


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if version != EXPECTED_VERSION:
        print(f"FAIL: VERSION is {version!r}, expected {EXPECTED_VERSION!r}", file=sys.stderr)
        return 2

    for p in sorted(ROOT.rglob("*.py")):  # in-memory compile: no __pycache__ written
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as exc:
            print(f"FAIL: compile {p.relative_to(ROOT)}: {exc}", file=sys.stderr)
            return 3

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py",
                                                top_level_dir=str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        return 4

    spec = importlib.util.spec_from_file_location("verify_governance", ROOT / "tools" / "verify_governance.py")
    gov = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gov)
    rep = gov.check(ROOT, dt.date.today())
    if rep["failures"]:
        print(f"FAIL: governance artifacts inconsistent: {rep['failures']}", file=sys.stderr)
        return 5

    strict = os.environ.get("PK_REQUIRE_CORE") == "1"
    print(f"PASS: INV-43 {version} standalone verification - {result.testsRun} tests, "
          f"{len(result.skipped)} skipped; governance consistent with {len(rep['blockers'])} open production "
          f"blockers (not production-ready)" + (" (strict core requested)" if strict else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
