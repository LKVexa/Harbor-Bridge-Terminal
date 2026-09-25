"""Policy precedence conflict vectors (C019)."""
from __future__ import annotations

import unittest

from _support import pkg
from inv37_bulk_data_plane import precedence as P


class PrecedenceTest(unittest.TestCase):
    def test_cheaper_cross_region_vs_residency(self):
        r = P.resolve([{"name": "cheap_cross_region", "violates": ["residency"], "score": 9},
                       {"name": "local_expensive", "violates": ["cost"], "score": 1}])
        self.assertEqual(r["selected"], "local_expensive")
        self.assertEqual(r["rejected"][0]["reason_code"], "residency_violation")

    def test_faster_unencrypted_vs_security(self):
        r = P.resolve([{"name": "plaintext_fast", "violates": ["security"], "score": 10}])
        self.assertEqual((r["decision"], r["reason_code"]), ("reject", "authorization_denied"))

    def test_slo_vs_memory_ceiling(self):
        r = P.resolve([{"name": "more_parallel", "violates": ["safety_limit"], "score": 5},
                       {"name": "respect_ceiling", "violates": ["availability_slo"], "score": 1}])
        self.assertEqual(r["selected"], "respect_ceiling")

    def test_emergency_override_rules(self):
        r = P.resolve([{"name": "burst", "violates": ["safety_limit"]}],
                      override={"dimensions": ["safety_limit"], "approver_role": "service_owner"})
        self.assertEqual(r["selected"], "burst")
        self.assertRaises(pkg.CodedError, P.resolve, [{"name": "x", "violates": ["security"]}],
                          override={"dimensions": ["security"], "approver_role": "service_owner"})
        self.assertRaises(pkg.CodedError, P.resolve, [{"name": "x", "violates": ["safety_limit"]}],
                          override={"dimensions": ["safety_limit"], "approver_role": "intern"})

    def test_policy_is_versioned(self):
        p = P.load()
        self.assertTrue(p["digest"].startswith("sha256:"))
        self.assertEqual(p["order"][0], "security")


if __name__ == "__main__":
    unittest.main()
