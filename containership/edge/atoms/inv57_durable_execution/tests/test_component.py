"""Conformance tests for the optional ``pk_core`` adapter.

Core durable-execution tests live in ``test_durable.py`` and always run.  These
adapter tests run only when the external ``pk_core`` framework is importable.
"""
from __future__ import annotations

import importlib
import os
import pathlib
import subprocess
import sys
import unittest

from . import _path  # noqa: F401

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    pk_core = None

KNOWN_PARTIAL: list[str] = []


def _load():
    return importlib.import_module(
        PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
    )


class PackageMetadataTest(unittest.TestCase):
    def test_version(self):
        # Single version source check (RG-02): module, VERSION file and pyproject agree.
        version = (PKG_DIR / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, "4.3.0")
        self.assertEqual(_load().__version__, version)
        pyproject = PKG_DIR / "pyproject.toml"
        if pyproject.exists():
            self.assertIn(f'version = "{version}"', pyproject.read_text(encoding="utf-8"))


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered_by_framework_adapter(self):
        comp = _load().COMPONENT()
        findings = [f for group in comp.assess_all().values() for f in group]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        unexpected = sorted(
            f.check_id
            for f in findings
            if not f.status.passing
            and f.check_id not in KNOWN_PARTIAL
            and "not installed" not in f.note
        )
        self.assertEqual(unexpected, [])
        self.assertFalse([f for f in findings if f.status.value == "blocked"])

    def test_framework_checks_survive_optimized_mode(self):
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([p for p in sys.path[:3]], _load().__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
