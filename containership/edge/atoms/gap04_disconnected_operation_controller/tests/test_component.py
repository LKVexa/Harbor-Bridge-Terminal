"""Conformance test for GAP-04 (gap04_disconnected_operation_controller) -- stdlib unittest, no network.

Run from the folder that contains this package (and ``pk_core``), e.g.::

    python gap04_disconnected_operation_controller/tests/test_component.py

Set PK_CORE_PATH if ``pk_core`` lives elsewhere (e.g. ``<project>/pk``).
"""
import importlib, os, pathlib, subprocess, sys, unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    pk_core = None

KNOWN_PARTIAL = []


def _load():
    pkg = importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)
    return pkg


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(_load().__version__, "4.2.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.2.0")

    def test_all_100_requirements_assessed(self):
        comp = _load().COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        # Do not equate "answered by the conformance framework" with independent
        # production readiness. Remaining implementation gaps are tracked in
        # MISSING_COMPONENTS.md and must be closed by the release gate.

    def test_checks_survive_optimised_mode(self):
        """Behavioural checks must not depend on assert statements (python -O)."""
        code = ("import sys; sys.path[:0]=%r; import importlib; "
                "m=importlib.import_module(%r); c=m.COMPONENT(); "
                "print(sum(len(v) for v in c.assess_all().values()))") % (
            [p for p in sys.path[:3]], _load().__name__)
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
