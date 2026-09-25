"""Mandatory release test profile for INV-69 (normal and `python -O`). Exit non-zero on any failure.

Skips are printed by name with their reason so none is silent; the release gate treats any skip in the
mandatory profile other than the declared pk_core lane (W-001) as a failure.
"""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
MODULES = ("test_runtime", "test_component", "test_v43", "test_fuzz")
DECLARED_SKIP_LANES = {"test_component": "pk_core not importable (W-001)"}

suite = unittest.TestSuite()
loader = unittest.TestLoader()
for name in MODULES:
    suite.addTests(loader.loadTestsFromName(name))
result = unittest.TextTestRunner(verbosity=1).run(suite)
skips = [{"test": t.id(), "reason": r} for t, r in result.skipped]
undeclared = [s for s in skips if s["test"].split(".")[0] not in DECLARED_SKIP_LANES]
for s in skips:
    print(f"SKIP {s['test']}: {s['reason']}")
summary = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
           "skipped": len(skips), "undeclared_skips": len(undeclared), "optimized_mode": not __debug__,
           "python": sys.version.split()[0]}
print("RESULT " + json.dumps(summary))
sys.exit(0 if result.wasSuccessful() and not undeclared else 1)
