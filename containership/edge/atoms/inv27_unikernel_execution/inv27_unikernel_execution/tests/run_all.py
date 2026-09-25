"""Mandatory release test profile for INV-27 (run under both `python` and `python -O`).

Exits non-zero on any failure or any skip outside a declared lane.  Declared lanes: optional
`cryptography` tests only (the runtime is stdlib-only and must pass without it).
"""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
MODULES = ("test_runtime", "test_seal", "test_parser", "test_service", "test_platform", "test_component",
           "test_repository", "test_gates")
DECLARED_SKIPS = {"test_cryptography_backend_agrees_when_installed", "test_roundtrip_rotation_tamper_context"}

suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in MODULES)
result = unittest.TextTestRunner(verbosity=1).run(suite)
skips = [{"test": t.id(), "reason": r} for t, r in result.skipped]
undeclared = [s for s in skips if s["test"].rsplit(".", 1)[-1] not in DECLARED_SKIPS]
for s in skips:
    print(f"SKIP {s['test']}: {s['reason']}")
summary = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
           "skipped": len(skips), "undeclared_skips": len(undeclared), "optimized_mode": not __debug__,
           "python": sys.version.split()[0]}
print("RESULT " + json.dumps(summary))
sys.exit(0 if result.wasSuccessful() and not undeclared else 1)
