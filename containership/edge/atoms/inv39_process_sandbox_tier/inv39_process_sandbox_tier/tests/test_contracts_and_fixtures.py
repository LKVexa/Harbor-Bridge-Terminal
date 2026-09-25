"""MC-016/017/019/085 — public-schema contract tests over positive and negative fixtures."""
from __future__ import annotations

import json
import unittest
from importlib import import_module

from _support import PKG_DIR, pkg

sc = import_module(PKG_DIR.name + ".schema_check")
errors = import_module(PKG_DIR.name + ".errors")
ctl = import_module(PKG_DIR.name + ".control")
SCHEMA_OF = {"profile-1": "PK_SANDBOX_PROFILE/1", "applied-1": "PK_SANDBOX_APPLIED/1",
             "applied-2": "PK_SANDBOX_APPLIED/2", "error-1": "PK_SANDBOX_ERROR/1"}
FIX = PKG_DIR / "fixtures"


def sid(path):
    return SCHEMA_OF[path.name.split(".")[0]]


class FixtureContractTest(unittest.TestCase):
    def test_every_schema_has_valid_and_invalid_fixtures(self):
        for s in SCHEMA_OF:
            self.assertTrue(list((FIX / "valid").glob(s + "*.json")), s)
            self.assertTrue(list((FIX / "invalid").glob(s + ".*.json")), s)

    def test_valid_fixtures_validate(self):
        for p in sorted((FIX / "valid").glob("*.json")):
            with self.subTest(p.name):
                self.assertEqual(sc.validate(json.loads(p.read_text()), sid(p)), [])

    def test_invalid_fixtures_are_rejected(self):
        for p in sorted((FIX / "invalid").glob("*.json")):
            with self.subTest(p.name):
                self.assertNotEqual(sc.validate(json.loads(p.read_text()), sid(p)), [])

    def test_live_outputs_match_schemas(self):
        prof = pkg.SandboxProfile("svc", {"read"})
        self.assertEqual(sc.validate(prof.as_dict()), [])
        box = pkg.Sandbox("p", prof)
        self.assertEqual(sc.validate(box.start(readback=box.requested_state())), [])
        for code in errors.ERROR_CODES:
            self.assertEqual(sc.validate(errors.SandboxError(code, "x").payload()), [], code)

    def test_unknown_schema_rejected(self):
        self.assertTrue(sc.validate({"schema": "PK_SANDBOX_PROFILE/9"}))
        self.assertTrue(sc.validate({"schema": "../../etc/passwd"}))


class ErrorTaxonomyTest(unittest.TestCase):
    def test_codes_are_stable_and_classified(self):
        for code, (outcome, retryable, desc) in errors.ERROR_CODES.items():
            self.assertRegex(code, r"^E_[A-Z_]+$")
            self.assertIn(outcome, errors.OUTCOMES)
            self.assertEqual(retryable, outcome == "retryable")
            self.assertTrue(desc)

    def test_unregistered_code_becomes_internal(self):
        self.assertEqual(errors.SandboxError("E_MADE_UP", "x").code, "E_INTERNAL")

    def test_payload_bounded(self):
        p = errors.SandboxError("E_INTERNAL", "x" * 5000, details={str(i): "y" * 999 for i in range(100)}).payload()
        self.assertLessEqual(len(p["message"]), 1024)
        self.assertLessEqual(len(p["details"]), 32)


class NegotiationTest(unittest.TestCase):
    def test_highest_common(self):
        self.assertEqual(ctl.negotiate("PK_SANDBOX_APPLIED", [1, 2, 3]), 2)
        self.assertEqual(ctl.negotiate("PK_SANDBOX_APPLIED", [1]), 1)

    def test_no_overlap_refused(self):
        with self.assertRaises(errors.SandboxError) as c:
            ctl.negotiate("PK_SANDBOX_PROFILE", [2])
        self.assertEqual(c.exception.code, "E_VERSION_UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
