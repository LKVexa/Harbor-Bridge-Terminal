"""Conformance test for INV-20 (inv20_http_component_worlds) -- stdlib unittest, no network.

``pk_core`` must be *installed* (``pip install .[conformance]``); v4.3.0 removed the
PK_CORE_PATH / parent-directory sys.path injection so an unintended copy cannot be loaded.
This suite is MANDATORY in the production profile: VERIFY.py never runs it under a skip.
"""
import importlib, pathlib, subprocess, sys, unittest

try:
    from . import _path  # noqa: F401
except ImportError:
    import _path  # type: ignore # noqa: F401

from inv20_http_component_worlds.pk_compat import probe

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
pk_core = object() if probe()["status"] == "PASS" else None

KNOWN_PARTIAL = []


def _load():
    pkg = importlib.import_module(PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name)
    return pkg


@unittest.skipIf(pk_core is None, "pk_core not installed in an approved version (VERIFY.py treats this as BLOCKED)")
class ConformanceTest(unittest.TestCase):
    def test_version(self):
        v = _load().__version__
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), v)

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
