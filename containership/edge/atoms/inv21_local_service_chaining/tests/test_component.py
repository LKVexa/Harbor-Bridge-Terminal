"""Conformance test for INV-21 (inv21_local_service_chaining) -- stdlib unittest, no network.

Run from the folder that contains this package (and ``pk_core``), e.g.::

    python inv21_local_service_chaining/tests/test_component.py

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


# GAP-001: a missing pk_core is a FAILURE, never a skip. A developer may opt out
# locally with INV21_ALLOW_PK_CORE_SKIP=1; the release gate refuses that variable.
_ALLOW_SKIP = os.environ.get("INV21_ALLOW_PK_CORE_SKIP") == "1"


class PkCorePresenceTest(unittest.TestCase):
    def test_pk_core_importable(self):
        if pk_core is None and _ALLOW_SKIP:
            self.skipTest("pk_core absent; developer opt-out INV21_ALLOW_PK_CORE_SKIP=1 (not valid for release)")
        self.assertIsNotNone(pk_core, "pk_core is not importable: set PK_CORE_PATH or install the pinned "
                             "pk_core (pyproject [tool.inv21.pk_core]). This is a release-blocking failure.")


@unittest.skipIf(pk_core is None, "covered by PkCorePresenceTest failure")
class ConformanceTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(_load().__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")

    def test_all_100_requirements_answered(self):
        comp = _load().COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        # Partials are allowed only for the known KMS condition or for an honest
        # "sibling not installed here" note (partial estate install).
        unexpected = sorted(f.check_id for f in findings if not f.status.passing
                            and f.check_id not in KNOWN_PARTIAL and "not installed" not in f.note)
        self.assertEqual(unexpected, [])
        self.assertFalse([f for f in findings if f.status.value == "blocked"])

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
