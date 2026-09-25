"""INV-35-C084: execute the locally runnable compatibility cells; required cells must be local."""
from __future__ import annotations

import json
import pathlib
import platform
import sys
import unittest

from _support import config, stack, one

MATRIX = json.loads((pathlib.Path(__file__).parent / "matrix.json").read_text())


class CompatibilityMatrixTest(unittest.TestCase):
    def test_required_cells_are_locally_runnable(self):
        for c in MATRIX["cells"]:
            if c["required"]:
                self.assertEqual(c["runner"], "local", c)
            if c["runner"] == "external":
                self.assertTrue(c["evidence"].startswith("WVR-"), "external cells must cite a waiver")

    def test_python_cell(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 11))

    def test_profile_cells_serve_traffic(self):
        for c in MATRIX["cells"]:
            if c["axis"] != "profile":
                continue
            with self.subTest(profile=c["cell"]):
                r, cp, dp, ctl, bulk = stack()
                cp.apply_config(ctl, tenant="t1", queue="q0", profile=c["cell"])
                self.assertTrue(dp.submit(bulk, tenant="t1", queue="q0", chain=one(), head=0)["validated"])

    def test_cpu_cell_recorded(self):
        self.assertIn(platform.machine().lower(), {"x86_64", "amd64", "aarch64", "arm64"})


if __name__ == "__main__":
    unittest.main()
