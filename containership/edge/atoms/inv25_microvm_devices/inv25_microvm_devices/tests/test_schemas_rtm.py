"""Schemas/fixtures (C022, C029, C082), RTM linkage (C020) and governance registers (C094, C098, C099)."""
import datetime
import json
import subprocess
import sys
import unittest

from _support import PKG_DIR, model, schema, schemavalidate, spec

FIX = PKG_DIR / "conformance" / "fixtures"


class SchemaTest(unittest.TestCase):
    def test_all_schemas_use_supported_subset(self):
        for p in (PKG_DIR / "schemas").glob("*.json"):
            with self.subTest(p.name):
                s = json.loads(p.read_text())
                schemavalidate.validate({}, s)  # raises on unsupported keywords

    def test_fixtures(self):
        cat, diff, err = (schema(n) for n in ("PK_DEVICE_CATALOGUE_1.schema.json",
                                             "PK_DEVICE_SURFACE_DIFF_1.schema.json", "PK_DEVICE_ERROR_1.schema.json"))
        valid = json.loads((FIX / "catalogue.valid.json").read_text())
        self.assertEqual(schemavalidate.validate(valid, cat), [])
        model.catalogue_from_export(valid)
        self.assertEqual(schemavalidate.validate(json.loads((FIX / "diff.widened.json").read_text()), diff), [])
        self.assertEqual(schemavalidate.validate(json.loads((FIX / "error.forbidden.json").read_text()), err), [])
        bad = json.loads((FIX / "catalogue.invalid.host-passthrough.json").read_text())
        self.assertNotEqual(schemavalidate.validate(bad, cat), [])
        with self.assertRaises(model.DeviceRejected):
            model.catalogue_from_export(bad)

    def test_live_outputs_match_schemas(self):
        c = model.DeviceCatalogue("prod")
        c.register(spec())
        self.assertEqual(schemavalidate.validate(c.export(), schema("PK_DEVICE_CATALOGUE_1.schema.json")), [])
        d = c.replace(spec(version="2.0", regs=("status", "x")))
        self.assertEqual(schemavalidate.validate(d, schema("PK_DEVICE_SURFACE_DIFF_1.schema.json")), [])


class RtmTest(unittest.TestCase):
    def test_rtm_complete_and_linked(self):
        out = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "rtm.py"), "check"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        rtm = json.loads((PKG_DIR / "governance" / "RTM.json").read_text())
        self.assertEqual(len(rtm["rows"]), 100)


class GovernanceTest(unittest.TestCase):
    def test_waiver_register(self):
        reg = json.loads((PKG_DIR / "governance" / "waivers.json").read_text())
        ids = [w["id"] for w in reg["waivers"]]
        self.assertEqual(len(ids), len(set(ids)))
        for w in reg["waivers"]:
            with self.subTest(w["id"]):
                for k in ("checks", "scope", "risk", "compensating_controls", "owner", "approvers", "issued",
                          "expires", "remediation", "status"):
                    self.assertIn(k, w)
                self.assertLess(datetime.date.fromisoformat(w["issued"]), datetime.date.fromisoformat(w["expires"]))
                if w["status"] == "approved":
                    self.assertTrue(w["approvers"])

    def test_review_register(self):
        reg = json.loads((PKG_DIR / "governance" / "reviews.json").read_text())
        today = datetime.date.today()
        for kind, days in reg["cadence_days"].items():
            done = [r for r in reg["reviews"] if r["kind"] == kind]
            if done:
                last = max(datetime.date.fromisoformat(r["date"]) for r in done)
                self.assertLessEqual((today - last).days, days, f"{kind} review overdue")

    def test_security_policy_present(self):
        self.assertIn("Supported versions", (PKG_DIR / "SECURITY.md").read_text())

    def test_master_md_not_required(self):
        for p in list(PKG_DIR.glob("*.py")) + list((PKG_DIR / "tools").glob("*.py")):
            self.assertNotIn("open(\"MASTER.md", p.read_text())


if __name__ == "__main__":
    unittest.main()
