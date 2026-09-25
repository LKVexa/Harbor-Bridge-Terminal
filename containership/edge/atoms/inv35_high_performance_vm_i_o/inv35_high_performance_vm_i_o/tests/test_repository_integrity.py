"""Repository metadata/integrity tests that require no external framework."""
from __future__ import annotations

import json
import pathlib
import re
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]


class RepositoryIntegrityTest(unittest.TestCase):
    def test_version_is_consistent(self):
        version = (PKG_DIR / "VERSION").read_text(encoding="utf-8").strip()
        init_text = (PKG_DIR / "__init__.py").read_text(encoding="utf-8")
        readme = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertIn(f'__version__ = "{version}"', init_text)
        self.assertIn(f"**Version:** {version}", readme)

    def test_checklist_is_complete_and_unique(self):
        data = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        items = data["items"]
        self.assertEqual(data["item_count"], 100)
        self.assertEqual(len(items), 100)
        self.assertEqual([item["ordinal"] for item in items], list(range(1, 101)))
        ids = [item["check_id"] for item in items]
        self.assertEqual(len(set(ids)), 100)
        self.assertTrue(all(re.fullmatch(r"INV-35-C\d{3}", check_id) for check_id in ids))

    def test_readme_does_not_claim_absent_master_file(self):
        readme = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        if "`MASTER.md`" in readme:
            self.assertTrue((PKG_DIR / "MASTER.md").is_file())

    def test_audit_artifacts_exist(self):
        self.assertTrue((PKG_DIR / "AUDIT_REPORT.md").is_file())
        self.assertTrue((PKG_DIR / "MISSING_COMPONENTS.md").is_file())

    def test_audit_matrix_covers_every_check_once(self):
        checklist = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        matrix = json.loads((PKG_DIR / "AUDIT_MATRIX.json").read_text(encoding="utf-8"))
        rows = matrix["requirements"]
        self.assertEqual(len(rows), 100)
        self.assertEqual(
            {row["check_id"] for row in rows},
            {item["check_id"] for item in checklist["items"]},
        )
        actual = {
            status: sum(row["status"] == status for row in rows)
            for status in ("present", "partial", "missing")
        }
        self.assertEqual(matrix["counts"], actual)


if __name__ == "__main__":
    unittest.main()
