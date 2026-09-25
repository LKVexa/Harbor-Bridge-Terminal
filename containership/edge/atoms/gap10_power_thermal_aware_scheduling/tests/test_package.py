"""Package-integrity tests that do not require the external pk_core estate."""
import hashlib
import json
import pathlib
import re
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]


class PackageIntegrityTests(unittest.TestCase):
    def test_version_is_consistent(self):
        version = (PKG_DIR / "VERSION").read_text(encoding="utf-8").strip()
        init_text = (PKG_DIR / "__init__.py").read_text(encoding="utf-8")
        match = re.search(r'^__version__\s*=\s*"([^"]+)"', init_text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(version, match.group(1))
        self.assertEqual(version, "4.3.0")

    def test_checklist_has_100_unique_ordered_items(self):
        data = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        items = data["items"]
        self.assertEqual(data["item_count"], 100)
        self.assertEqual(len(items), 100)
        self.assertEqual(len({item["check_id"] for item in items}), 100)
        self.assertEqual([item["ordinal"] for item in items], list(range(1, 101)))

    def test_documented_schema_files_exist(self):
        expected = {
            "PK_THERMAL_STATE-1.schema.json",
            "PK_POWER_CEILING-1.schema.json",
            "PK_THERMAL_POLICY-1.schema.json",
            "PK_TELEMETRY_ENVELOPE-1.schema.json",
            "PK_GAP10_HEALTH-1.schema.json",
        }
        self.assertEqual({p.name for p in (PKG_DIR / "schemas").glob("*.json")}, expected)

    def test_manifest_matches_package_files(self):
        manifest_path = PKG_DIR / "MANIFEST.sha256"
        rows = {}
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            digest, rel = line.split("  ", 1)
            rows[rel] = digest
        expected = {
            p.relative_to(PKG_DIR).as_posix(): p
            for p in PKG_DIR.rglob("*")
            if p.is_file() and p.name != "MANIFEST.sha256" and "__pycache__" not in p.parts
            and "evidence" not in p.relative_to(PKG_DIR).parts
        }
        self.assertEqual(set(rows), set(expected))
        for rel, path in expected.items():
            with self.subTest(path=rel):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), rows[rel])

    def test_readme_does_not_claim_missing_master_file(self):
        readme = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("**Master prompts:**", readme)


if __name__ == "__main__":
    unittest.main()
