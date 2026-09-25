"""Conformance tests for INV-72.

The version/import checks run without external dependencies. The pk_core-backed
100-item conformance and optimized-mode checks run when pk_core is available.
"""
import importlib
import os
import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(PKG_DIR / "_vendor"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - environment-dependent integration
    pk_core = None

KNOWN_PARTIAL = []


def _load():
    package_name = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
    return importlib.import_module(package_name)


class PackageTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(_load().__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")

    def test_pure_matcher_imports_without_pk_core(self):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "import %s as p; print(p.__version__, p.Device.__name__, callable(p.match))"
        ) % (str(ROOT), PKG_DIR.name)
        env = dict(os.environ)
        env["PYTHONNOUSERSITE"] = "1"
        out = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
        )
        # -I ignores PYTHONPATH but explicit sys.path insertion remains effective.
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "4.3.0 Device True")


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class PkCoreConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered(self):
        comp = _load().COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
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

    def test_checks_survive_optimised_mode(self):
        """Behavioural checks must not depend on assert statements (python -O)."""
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
