"""MC-048/MC-090 — the security suite is derived mechanically from docs/THREAT_MODEL.json:
every threat must name tests, every named test must exist, and all of them run here."""
from __future__ import annotations

import json
import unittest

from _support import PKG_DIR

TM = json.loads((PKG_DIR / "docs" / "THREAT_MODEL.json").read_text())


class ThreatModelDerivedSuite(unittest.TestCase):
    def test_every_threat_has_mitigation_and_tests(self):
        for t in TM["threats"]:
            self.assertTrue(t["mitigations"], t["id"])
            self.assertTrue(t["tests"], t["id"])

    def test_named_tests_exist_and_pass(self):
        loader = unittest.defaultTestLoader
        names = sorted({n for t in TM["threats"] for n in t["tests"]})
        suite = loader.loadTestsFromNames(names)
        self.assertEqual(suite.countTestCases(), len(names))
        res = unittest.TestResult()
        suite.run(res)
        self.assertEqual([str(f[0]) for f in res.failures + res.errors], [])
        # skips are allowed off-target, but reported; on a cert target _support turns them into failures
        self.skipped_threat_tests = [str(s[0]) for s in res.skipped]


if __name__ == "__main__":
    unittest.main()
