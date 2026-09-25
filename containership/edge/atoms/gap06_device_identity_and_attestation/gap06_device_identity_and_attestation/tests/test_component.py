"""Framework conformance tests for GAP-06.

The version/import checks run without ``pk_core``. Framework-specific 100-item
conformance checks run when ``pk_core`` is available (set PK_CORE_PATH if it is
stored elsewhere).
"""
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

PKG_NAME = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name


def _load():
    return importlib.import_module(PKG_NAME)


class PackageTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(_load().__version__, "5.0.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "5.0.0")

    def test_security_primitives_import_without_pk_core(self):
        pkg = _load()
        self.assertTrue(callable(pkg.Attestor))
        self.assertTrue(callable(pkg.Evidence))


try:
    import pk_core  # noqa: F401,E402
except ModuleNotFoundError:  # pragma: no cover
    pk_core = None

KNOWN_PARTIAL = []


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered(self):
        comp = _load().COMPONENT()
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
        ) % ([p for p in sys.path[:3]], _load().__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT), check=False
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
