"""Run the whole stdlib unittest suite (tests/test_*.py); exit non-zero on any failure or error."""
import sys, unittest
from _tools_pkg import ROOT

sys.path.insert(0, str(ROOT / "tests"))
suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT / "tests"))
res = unittest.TextTestRunner(verbosity=1 if "-v" not in sys.argv else 2).run(suite)
sys.exit(0 if res.wasSuccessful() else 1)
