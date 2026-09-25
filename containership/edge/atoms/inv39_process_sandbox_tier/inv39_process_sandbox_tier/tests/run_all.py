"""Run every INV-39 test module; exit non-zero on any failure. Reports skips explicitly."""
import pathlib, sys, unittest
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py", top_level_dir=str(HERE))
res = unittest.TextTestRunner(verbosity=1).run(suite)
for t, why in res.skipped:
    print(f"SKIPPED {t.id()}: {why}")
sys.exit(0 if res.wasSuccessful() else 1)
