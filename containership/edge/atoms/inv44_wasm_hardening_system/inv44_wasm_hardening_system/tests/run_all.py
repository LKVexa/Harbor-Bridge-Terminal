"""Run every INV-44 test module; exit non-zero on any failure (used by CI and release_gate)."""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
suite = unittest.TestSuite()
loader = unittest.TestLoader()
for name in ("test_component", "test_v43", "test_packaging"):
    suite.addTests(loader.loadTestsFromName(name))
result = unittest.TextTestRunner(verbosity=1).run(suite)
print(f"RESULT tests={result.testsRun} failures={len(result.failures)} errors={len(result.errors)} skipped={len(result.skipped)}")
sys.exit(0 if result.wasSuccessful() else 1)
