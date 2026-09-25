"""MC-03/09/11 hardware-backed probe.  Always runs the real probe on this host and checks
its invariants; with INV23_MATRIX_ROW=<id> it also asserts the row's expected outcome
from compatibility.json (used by the hardware-conformance workflow on lab runners)."""

import json
import os
import unittest

from tests._boot import PKG_DIR, mod

probe = mod("probe")
schema = mod("schema")


class HostProbeTest(unittest.TestCase):
    def test_real_probe_invariants(self):
        r = probe.probe_host()
        schema.validate_probe_report(r.to_report())
        if r.state == "usable":
            self.assertTrue(r.facility_usable)
        if r.virtualized:
            self.assertFalse(r.to_report()["bare_metal"])
            self.assertNotEqual(r.nesting_depth, 0)

    def test_matrix_row_expectation(self):
        row_id = os.environ.get("INV23_MATRIX_ROW")
        if not row_id:
            self.skipTest("INV23_MATRIX_ROW not set (lab runners only)")
        rows = {x["id"]: x for x in json.loads((PKG_DIR / "compatibility.json").read_text())["rows"]}
        row = rows[row_id]
        r = probe.probe_host()
        exp = row["expected"]
        self.assertEqual(r.state, exp["state"])
        if "reason" in exp:
            self.assertEqual(r.reason, exp["reason"])
        self.assertEqual(r.to_report()["bare_metal"], exp["bare_metal"])
        if "nesting_depth" in exp:
            self.assertEqual(r.nesting_depth, exp["nesting_depth"])


if __name__ == "__main__":
    unittest.main()
