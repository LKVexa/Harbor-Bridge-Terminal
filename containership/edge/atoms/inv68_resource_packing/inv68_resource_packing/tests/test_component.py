"""Conformance tests for the INV-68 ``pk_core`` integration.

The package metadata test always runs. Framework-level checklist tests run when
``pk_core`` is available through the repository or ``PK_CORE_PATH``.
"""
from __future__ import annotations

import ast
import importlib
import json
import os
import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for path in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if path not in sys.path:
        sys.path.insert(0, path)

import inv68_resource_packing as package

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - environment-dependent integration
    pk_core = None

KNOWN_PARTIAL: list[str] = []


class PackageMetadataTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(package.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")

    def test_missing_pk_core_does_not_break_pure_package_import(self):
        self.assertTrue(callable(package.pack))
        self.assertTrue(callable(package.pack_detailed))


    def test_checklist_integrity(self):
        payload = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        items = payload["items"]
        self.assertEqual(payload["item_count"], 100)
        self.assertEqual(len(items), 100)
        self.assertEqual([item["ordinal"] for item in items], list(range(1, 101)))
        self.assertEqual(len({item["check_id"] for item in items}), 100)

    def test_no_bare_asserts_in_runtime_source(self):
        for name in sorted(p.name for p in PKG_DIR.glob("*.py")):
            tree = ast.parse((PKG_DIR / name).read_text(), filename=name)
            assertions = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
            self.assertEqual(assertions, [], f"bare assert found in {name}")


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class CoreConformanceTest(unittest.TestCase):
    def _load_component_package(self):
        return importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)

    def test_all_100_requirements_answered(self):
        comp = self._load_component_package().COMPONENT()
        findings = [finding for group in comp.assess_all().values() for finding in group]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({finding.check_id for finding in findings}), 100)
        unexpected = sorted(
            finding.check_id
            for finding in findings
            if not finding.status.passing
            and finding.check_id not in KNOWN_PARTIAL
            and "not installed" not in finding.note
        )
        self.assertEqual(unexpected, [])
        self.assertFalse([finding for finding in findings if finding.status.value == "blocked"])

    def test_checks_survive_optimised_mode(self):
        module_name = self._load_component_package().__name__
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([p for p in sys.path[:3]], module_name)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
