"""Conformance tests for the optional ``pk_core`` registry adapter.

Standalone policy tests live in ``test_defense.py`` and always run.  Set
``PK_CORE_PATH`` when the external registry runtime is checked out elsewhere.
Set ``PK_REQUIRE_CORE=1`` in release CI to turn a missing runtime into a failure
instead of a skip.
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
for path in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    pk_core = None

KNOWN_PARTIAL: list[str] = []


def _load():
    name = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
    return importlib.import_module(name)


class PackageMetadataTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(_load().__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")

    def test_release_ci_can_require_pk_core(self):
        if os.environ.get("PK_REQUIRE_CORE") == "1":
            self.assertIsNotNone(pk_core, "PK_REQUIRE_CORE=1 but pk_core is not importable")


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH (release CI: PK_REQUIRE_CORE=1)")
class ConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered(self):
        comp = _load().COMPONENT()
        findings = [finding for band in comp.assess_all().values() for finding in band]
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
        """Behavioural checks must not depend on assert statements (python -O)."""
        module_name = _load().__name__
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([path for path in sys.path[:3]], module_name)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=30,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
