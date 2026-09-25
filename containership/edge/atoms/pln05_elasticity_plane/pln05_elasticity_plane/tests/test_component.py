"""Framework conformance tests for PLN-05 (stdlib ``unittest``; no network).

The metadata checks always run.  The full checklist/gate adapter checks require
``pk_core`` and are skipped only when that external framework is not available.
"""
from __future__ import annotations

import importlib
import os
import pathlib
import re
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    pk_core = None


def _load():
    name = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
    return importlib.import_module(name)


class MetadataTest(unittest.TestCase):
    def test_version_files_are_consistent(self):
        expected = "4.2.0"
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), expected)
        init_text = (PKG_DIR / "__init__.py").read_text(encoding="utf-8")
        match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), expected)

    def test_readme_does_not_reference_absent_master_file(self):
        readme = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        if "`MASTER.md`" in readme:  # 4.2.0 restored MASTER.md (MC-32); a reference must resolve
            self.assertTrue((PKG_DIR / "MASTER.md").exists())


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_all_100_requirements_are_assessed(self):
        comp = _load().COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        # Partial findings are legitimate when the repository lacks required
        # production evidence.  A blocked item, however, must remain a hard gate.
        self.assertFalse([f for f in findings if f.status.value == "blocked"])

    def test_checks_survive_optimised_mode(self):
        """Behavioural checks must not depend on stripped ``assert`` statements."""
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([p for p in sys.path[:3]], _load().__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT)
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
