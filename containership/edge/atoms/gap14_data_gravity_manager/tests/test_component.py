"""Conformance and package-integrity tests for GAP-14 -- stdlib, no network."""
import importlib
import json
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

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    pk_core = None

KNOWN_PARTIAL = []
VERSION = "4.3.0"


def _load():
    package_name = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
    return importlib.import_module(package_name)


class PackageIntegrityTest(unittest.TestCase):
    def test_version_is_consistent(self):
        pkg = _load()
        self.assertEqual(pkg.__version__, VERSION)
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), VERSION)
        self.assertIn(f"**Version:** {VERSION}", (PKG_DIR / "README.md").read_text(encoding="utf-8"))

    def test_checklist_is_exactly_100_unique_ordered_items(self):
        payload = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["element"], "GAP-14")
        self.assertEqual(payload["item_count"], 100)
        self.assertEqual(len(payload["items"]), 100)
        expected = [f"GAP-14-C{i:03d}" for i in range(1, 101)]
        self.assertEqual([item["check_id"] for item in payload["items"]], expected)
        self.assertEqual([item["ordinal"] for item in payload["items"]], list(range(1, 101)))

    def test_release_documents_present(self):
        for name in ("MASTER.md", "MISSING_COMPONENTS.md", "AUDIT_REPORT_v4.3.0.md", "CHANGELOG.md"):
            self.assertTrue((PKG_DIR / name).is_file(), name)


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_all_100_requirements_answered(self):
        comp = _load().COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        unexpected = sorted(
            f.check_id for f in findings
            if not f.status.passing and f.check_id not in KNOWN_PARTIAL
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
