"""Release-gate test runner: runs the whole suite and FAILS if any test is skipped
(the checklist's 'zero unexpected skips' rule). Local development uses plain unittest."""
import pathlib, sys, unittest
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
suite = unittest.defaultTestLoader.discover(str(root / "tests"))
res = unittest.TextTestRunner(verbosity=1).run(suite)
if res.skipped:
    print(f"GATE FAIL: {len(res.skipped)} skipped test(s):", *[t.id() for t, _ in res.skipped], sep="\n  ")
sys.exit(0 if res.wasSuccessful() and not res.skipped else 1)
