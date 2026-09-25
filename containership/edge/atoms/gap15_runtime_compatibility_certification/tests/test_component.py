"""Conformance tests for GAP-15 -- stdlib unittest, no network.

Run from the folder that contains this package (and ``pk_core``), e.g.::

    python gap15_runtime_compatibility_certification/tests/test_component.py

Set PK_CORE_PATH if ``pk_core`` lives elsewhere (e.g. ``<project>/pk``).
"""
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
except ModuleNotFoundError:  # pragma: no cover
    pk_core = None

KNOWN_PARTIAL = []


def _load():
    package_name = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
    return importlib.import_module(package_name)


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class ConformanceTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(_load().__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")

    def test_all_100_requirements_answered(self):
        comp = _load().COMPONENT()
        findings = [finding for group in comp.assess_all().values() for finding in group]
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
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([path for path in sys.path[:3]], _load().__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")

    def test_future_dated_negative_evidence_fails_closed(self):
        module = _load().component
        matrix = module.CompatibilityMatrix("prod")
        triple = module.Triple("svc:1", "wasmtime-21", "arm64-sev")
        matrix.record(triple, compatible=False, at=100)
        verdict = matrix.certify(triple, now=99)
        self.assertEqual(verdict["verdict"], module.UNTESTED)
        self.assertFalse(verdict["deployable"])

    def test_replay_and_conflict_protection(self):
        module = _load().component
        matrix = module.CompatibilityMatrix("prod")
        triple = module.Triple("svc:1", "wasmtime-21", "arm64-sev")
        matrix.record(triple, compatible=True, at=10)
        revision = matrix.revision
        matrix.record(triple, compatible=True, at=10)
        self.assertEqual(matrix.revision, revision)
        with self.assertRaises(ValueError):
            matrix.record(triple, compatible=False, at=10)
        with self.assertRaises(ValueError):
            matrix.record(triple, compatible=True, at=9)

    def test_lifecycle_regression_requires_explicit_override(self):
        module = _load().component
        matrix = module.CompatibilityMatrix("prod")
        matrix.set_lifecycle("wasmtime-21", module.EOL)
        with self.assertRaises(ValueError):
            matrix.set_lifecycle("wasmtime-21", module.SUPPORTED)
        matrix.set_lifecycle("wasmtime-21", module.SUPPORTED, allow_reactivation=True)
        self.assertEqual(matrix.lifecycle["wasmtime-21"], module.SUPPORTED)

    def test_typed_revisioned_exports_are_deterministic(self):
        module = _load().component
        matrix = module.CompatibilityMatrix("prod")
        b = module.Triple("b", "runtime", "profile")
        a = module.Triple("a", "runtime", "profile")
        matrix.record(b, compatible=True, at=2)
        matrix.record(a, compatible=False, at=1)
        matrix.set_lifecycle("runtime", module.DEPRECATED)
        view = matrix.matrix_view()
        self.assertEqual(view["schema"], "PK_COMPATIBILITY_MATRIX/1")
        self.assertEqual(view["revision"], 3)
        self.assertEqual([row["artifact"] for row in view["results"]], ["a", "b"])
        self.assertEqual(matrix.lifecycle_view()["schema"], "PK_RUNTIME_LIFECYCLE/1")

    def test_invalid_identifiers_and_times_are_rejected(self):
        module = _load().component
        with self.assertRaises(ValueError):
            module.Triple(" ", "runtime", "profile")
        matrix = module.CompatibilityMatrix("prod")
        triple = module.Triple("svc:1", "runtime", "profile")
        with self.assertRaises(TypeError):
            matrix.record(triple, compatible=True, at=True)
        with self.assertRaises(TypeError):
            matrix.certify(triple, now=True)


if __name__ == "__main__":
    unittest.main()
