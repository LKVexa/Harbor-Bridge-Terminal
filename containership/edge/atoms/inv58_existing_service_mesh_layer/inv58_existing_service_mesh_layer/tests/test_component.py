"""Conformance test for INV-58 (inv58_existing_service_mesh_layer) -- stdlib unittest, no network.

Run from the folder that contains this package (and ``pk_core``), e.g.::

    python inv58_existing_service_mesh_layer/tests/test_component.py

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

def _load():
    pkg = importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)
    return pkg


class VersionTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(_load().__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_all_100_requirements_reported(self):
        """Framework assessment must report every checklist item exactly once.

        This intentionally does not force every finding to pass: repository evidence
        gaps are tracked in POST_AUDIT_MISSING_COMPONENTS.md/MISSING_COMPONENTS.json
        and must not be hidden by a conformance smoke test.
        """
        comp = _load().COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)

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
