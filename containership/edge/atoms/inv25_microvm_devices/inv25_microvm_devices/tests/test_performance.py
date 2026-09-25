"""Item 22 quick benchmark run against proposed thresholds (C061-C070, C088)."""
import json
import subprocess
import sys
import unittest

from _support import PKG_DIR


class PerformanceTest(unittest.TestCase):
    def test_quick_bench_within_budget(self):
        out = subprocess.run([sys.executable, str(PKG_DIR / "conformance" / "performance" / "bench.py"), "--quick"],
                             capture_output=True, text=True, timeout=300)
        self.assertEqual(out.returncode, 0, out.stdout[-2000:] + out.stderr[-2000:])
        self.assertTrue(json.loads(out.stdout)["pass"])


if __name__ == "__main__":
    unittest.main()
