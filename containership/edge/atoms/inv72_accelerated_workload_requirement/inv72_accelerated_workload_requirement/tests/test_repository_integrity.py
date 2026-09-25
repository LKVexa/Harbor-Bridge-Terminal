"""Repository-local integrity tests for INV-72."""
import ast
import json
import pathlib
import re
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]


class RepositoryIntegrityTest(unittest.TestCase):
    def test_checklist_is_complete_and_sequential(self):
        data = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        items = data["items"]
        self.assertEqual(data["item_count"], 100)
        self.assertEqual(len(items), 100)
        expected = [f"INV-72-C{i:03d}" for i in range(1, 101)]
        self.assertEqual([item["check_id"] for item in items], expected)
        self.assertEqual(len({item["requirement"] for item in items}), 100)

    def test_version_is_synchronized(self):
        version = (PKG_DIR / "VERSION").read_text(encoding="utf-8").strip()
        init_tree = ast.parse((PKG_DIR / "__init__.py").read_text(encoding="utf-8"))
        init_version = None
        for node in init_tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__version__":
                        init_version = ast.literal_eval(node.value)
        self.assertEqual(version, init_version)
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertIn(f"## {version} - ", (PKG_DIR / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn(f"**Version:** {version}", (PKG_DIR / "README.md").read_text(encoding="utf-8"))

    def test_readme_has_no_reference_to_missing_master_file(self):
        readme = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotRegex(readme, r"`MASTER\.md`")

    def test_no_bare_assert_in_runtime_modules(self):
        for path in sorted(PKG_DIR.glob("*.py")) + sorted((PKG_DIR / "tools").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            assertions = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
            self.assertEqual(assertions, [], f"bare assert in {path.name}: {assertions}")


if __name__ == "__main__":
    unittest.main()
