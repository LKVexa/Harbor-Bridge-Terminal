"""pk_core conformance tests for INV-34, plus import/version checks."""
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

pkg = importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)
try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    pk_core = None

KNOWN_PARTIAL = []


class PackageTest(unittest.TestCase):
    def test_version(self):
        expected = (PKG_DIR / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(expected, "5.1.0")
        self.assertEqual(pkg.__version__, expected)

    def test_package_imports_without_pk_core(self):
        self.assertTrue(hasattr(pkg, "CpuExpansionController"))
        self.assertTrue(hasattr(pkg, "VmCpuState"))


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered(self):
        comp = pkg.COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        unexpected = sorted(
            f.check_id
            for f in findings
            if not f.status.passing and f.check_id not in KNOWN_PARTIAL and "not installed" not in f.note
        )
        self.assertEqual(unexpected, [])
        self.assertFalse([f for f in findings if f.status.value == "blocked"])

    def test_checks_survive_optimised_mode(self):
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([p for p in sys.path[:3]], pkg.__name__)
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
