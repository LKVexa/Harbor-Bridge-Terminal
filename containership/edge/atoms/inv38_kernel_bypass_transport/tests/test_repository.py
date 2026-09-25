"""Repository-integrity tests that do not require pk_core."""
from __future__ import annotations

import ast
import importlib
import json
import pathlib
import re
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]


class RepositoryIntegrityTest(unittest.TestCase):
    def test_checklist_has_exactly_100_unique_items(self):
        data = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        items = data["items"]
        ids = [item.get("id") or item.get("check_id") for item in items]
        self.assertEqual(data["item_count"], 100)
        self.assertEqual(len(items), 100)
        self.assertEqual(len(set(ids)), 100)

    def test_versions_are_synchronized(self):
        version = (PKG_DIR / "VERSION").read_text(encoding="utf-8").strip()
        init_text = (PKG_DIR / "__init__.py").read_text(encoding="utf-8")
        readme = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        changelog = (PKG_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), version)
        self.assertIn(f"**Version:** {version}", readme)
        self.assertIn(f"## {version} -", changelog)


    def test_package_degrades_explicitly_without_external_core(self):
        parent = str(PKG_DIR.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        pkg = importlib.import_module(PKG_DIR.name)
        self.assertTrue(hasattr(pkg, "PK_CORE_AVAILABLE"))
        self.assertIs(pkg.BypassQueue.__module__.endswith("transport"), True)
        if not pkg.PK_CORE_AVAILABLE:
            self.assertIsNone(pkg.COMPONENT)
            with self.assertRaises(pkg.CoreUnavailableError):
                pkg.build_contract()

    def test_python_sources_have_no_bare_asserts_outside_tests(self):
        offenders = []
        for path in PKG_DIR.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if any(isinstance(node, ast.Assert) for node in ast.walk(tree)):
                offenders.append(path.name)
        self.assertEqual(offenders, [])

    def test_readme_does_not_claim_missing_master_document(self):
        readme = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("**Master prompts:** `MASTER.md`", readme)
        self.assertIn("not included in this standalone archive", readme)


if __name__ == "__main__":
    unittest.main()
