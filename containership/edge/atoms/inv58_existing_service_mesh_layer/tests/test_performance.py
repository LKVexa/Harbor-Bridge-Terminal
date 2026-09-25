"""MC-021 / MC-023: quick benchmark run must meet absolute SLO ceilings; gate logic blocks regressions."""
from __future__ import annotations

import importlib.util
import json
import unittest

from _support import PKG_DIR

spec = importlib.util.spec_from_file_location("inv58_bench", PKG_DIR / "tools" / "bench.py")
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class PerformanceGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = bench.run_best(quick=True, repeats=3)

    def test_absolute_ceilings(self):
        g = bench.gate(self.res, None)
        self.assertTrue(g["pass"], g["failures"])

    def test_identity_handoff_slo_p99_under_100us(self):
        self.assertLess(self.res["metrics"]["mesh.map_identity.p99_us"], 100.0)

    def test_gate_blocks_a_regression(self):
        base = json.loads((PKG_DIR / "perf" / "baseline.json").read_text())
        worse = {"metrics": {k: v * 10 + 1000 for k, v in base["metrics"].items()}}
        g = bench.gate(worse, base)
        self.assertFalse(g["pass"])
        self.assertEqual(len(g["failures"]), len(bench.GATE))

    def test_gate_rejects_missing_metrics(self):
        self.assertFalse(bench.gate({"metrics": {}}, None)["pass"])

    def test_power_thermal_is_reported_blocked_not_estimated(self):
        self.assertTrue(self.res["blocked"]["power_thermal"].startswith("BLOCKED"))


if __name__ == "__main__":
    unittest.main()
