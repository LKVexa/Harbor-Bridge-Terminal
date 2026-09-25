"""INV-35-C062/C070: the benchmark regression gate runs on every verification (quick mode)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from _support import PKG_DIR


class PerfGateTest(unittest.TestCase):
    def test_quick_benchmark_within_thresholds(self):
        r = subprocess.run([sys.executable, str(PKG_DIR / "benchmarks" / "bench.py"), "--quick"],
                           capture_output=True, text=True, timeout=300)
        report = json.loads(r.stdout)
        self.assertEqual(report["breaches"], [], report["breaches"])
        self.assertEqual(r.returncode, 0)
        self.assertTrue(report["results"]["overload_state_intact"])

    def test_baseline_exists_for_this_version(self):
        version = (PKG_DIR / "VERSION").read_text().strip()
        self.assertTrue(list((PKG_DIR / "benchmarks" / "baselines").glob(f"baseline-{version}-*.json")))


if __name__ == "__main__":
    unittest.main()
