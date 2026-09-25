"""pk_core integration tests for INV-36.

The transport security tests are in ``test_transport.py`` and always run.
These tests exercise the external estate gate only when ``pk_core`` is present.
"""
from __future__ import annotations

import importlib
import os
import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

import inv36_control_transport as package

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - estate dependency is optional here
    pk_core = None


class PackageTest(unittest.TestCase):
    """REQ: INV36-REQ-043 | KIND: unit"""

    def test_version(self):
        version = (PKG_DIR / "VERSION").read_text().strip()
        self.assertEqual(package.__version__, version)
        pyproject = (PKG_DIR / "pyproject.toml").read_text()
        self.assertIn(f'version = "{version}"', pyproject)

    def test_transport_import_does_not_require_pk_core(self):
        self.assertIsNotNone(package.Session)


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH for estate conformance tests")
class EstateConformanceTest(unittest.TestCase):
    """REQ: INV36-REQ-043 | KIND: integration"""

    def _load_component(self):
        module = importlib.import_module("inv36_control_transport.component")
        return module.COMPONENT()

    def test_all_100_requirements_are_addressed(self):
        findings = [f for fs in self._load_component().assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        # Passing status is deliberately not asserted here: production readiness
        # requires evidence from sibling components and the external estate.

    def test_component_checks_survive_optimized_mode(self):
        code = (
            "import sys; sys.path.insert(0,%r); "
            "from inv36_control_transport.component import COMPONENT; "
            "c=COMPONENT(); print(sum(len(v) for v in c.assess_all().values()))"
        ) % str(ROOT)
        proc = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
