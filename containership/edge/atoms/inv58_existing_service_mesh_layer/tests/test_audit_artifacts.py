"""Consistency checks for INV-58 audit/release artifacts."""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AuditArtifactTest(unittest.TestCase):
    def test_checklist_is_exactly_100_unique_items(self):
        data = json.loads((ROOT / "CHECKLIST.json").read_text(encoding="utf-8"))
        items = data["items"]
        ids = [item["check_id"] for item in items]
        self.assertEqual(len(items), 100)
        self.assertEqual(len(set(ids)), 100)
        self.assertEqual(ids[0], "INV-58-C001")
        self.assertEqual(ids[-1], "INV-58-C100")

    def test_missing_component_registry_covers_every_nonimplemented_check_once(self):
        data = json.loads((ROOT / "MISSING_COMPONENTS.json").read_text(encoding="utf-8"))
        counts = data["coverage_counts"]
        self.assertEqual(sum(counts.values()), 100)
        refs = []
        for component in data["components"]:
            refs.extend(req["check_id"] for req in component["requirements"])
        self.assertEqual(len(refs), counts["partial"] + counts["missing"])
        self.assertEqual(len(set(refs)), len(refs))

    def test_contract_schema_references_exist(self):
        contract = (ROOT / "contract.py").read_text(encoding="utf-8")
        refs = re.findall(r"schemas/(PK_MESH_[A-Z]+-1\.schema\.json)", contract)
        self.assertEqual(len(refs), 3)
        for ref in refs:
            self.assertTrue((ROOT / "schemas" / ref).is_file(), ref)

    def test_version_metadata_is_synchronized(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, "4.3.0")
        self.assertIn(f"**Version:** {version}", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn(f"## {version} -", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn(f'__version__ = "{version}"', (ROOT / "__init__.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
