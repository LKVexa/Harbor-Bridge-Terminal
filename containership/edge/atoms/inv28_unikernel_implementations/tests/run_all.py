"""Mandatory release test profile for INV-28 (run under both `python` and `python -O`) (MC-039..MC-055).

Exit non-zero on any failure or any skip that is not a declared lane.  Every skip is printed with its
reason.  With pk_core vendored there are no declared skip lanes, so any skip fails the profile.
"""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
MODULES = ("test_model", "test_selection", "test_registry", "test_integration", "test_interfaces",
           "test_observability", "test_ops", "test_security", "test_resilience", "test_fuzz",
           "test_boundaries", "test_toolchain_domain", "test_component", "test_repository", "test_gates")
DECLARED_SKIP_LANES: dict = {}

if __name__ == "__main__":
    suite = unittest.TestSuite()
    for name in MODULES:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
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
