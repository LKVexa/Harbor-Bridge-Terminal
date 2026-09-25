"""pk_core conformance for INV-23 (MC-01).

Modes (``INV23_CONFORMANCE``):
  dev (default)  - missing pk_core => tests SKIP with a diagnostic (developer convenience).
  release        - missing/incompatible pk_core => tests FAIL; CI release job uses this and
                   additionally fails if anything in this module was skipped.
Resolution precedence is defined in ``pkcore_compat.py``.
"""

import importlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests._boot import PKG_DIR, pkg

compat = importlib.import_module(pkg.__name__ + ".pkcore_compat")
RES = compat.resolve()
RELEASE = compat.mode() == "release"
KNOWN_PARTIAL = []


def _need_pk(tc):
    if RES.status != "ok":
        msg = f"pk_core {RES.status}: " + "; ".join(RES.diagnostics)
        if RELEASE:
            tc.fail(msg)
        tc.skipTest(msg)


class PreflightTest(unittest.TestCase):
    def test_preflight_resolution(self):
        out = os.environ.get("INV23_PKCORE_EVIDENCE")
        if out:
            pathlib.Path(out).write_text(json.dumps(RES.as_evidence(), indent=1))
        if RELEASE:
            self.assertEqual(RES.status, "ok", RES.diagnostics)
        else:
            self.assertIn(RES.status, ("ok", "dependency_missing", "dependency_incompatible"))


class ConformanceTest(unittest.TestCase):
    def setUp(self):
        _need_pk(self)

    def test_version(self):
        self.assertEqual(pkg.__version__, (PKG_DIR / "VERSION").read_text().strip())

    def test_component_smoke(self):
        c = pkg.COMPONENT()
        self.assertEqual(c.element_id, "INV-23")

    def test_all_100_requirements_answered(self):
        findings = [f for fs in pkg.COMPONENT().assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        unexpected = sorted(
            f.check_id for f in findings if not f.status.passing and f.check_id not in KNOWN_PARTIAL and "not installed" not in f.note
        )
        self.assertEqual(unexpected, [])
        self.assertFalse([f for f in findings if f.status.value == "blocked"])
        out = os.environ.get("INV23_CONFORMANCE_OUT")
        if out:
            pathlib.Path(out).write_text(
                json.dumps([{"check_id": f.check_id, "status": f.status.value, "note": f.note} for f in findings], indent=1)
            )

    def _run(self, *flags, cwd):
        code = (
            "import importlib,sys; m=importlib.import_module(%r); print(sum(len(v) for v in m.COMPONENT().assess_all().values()))"
        ) % pkg.__name__
        paths = [str(PKG_DIR.parent), RES.location and str(pathlib.Path(RES.location).parent)]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(p for p in paths if p))
        return subprocess.run([sys.executable, *flags, "-c", code], capture_output=True, text=True, cwd=cwd, env=env)

    def test_checks_survive_optimised_mode(self):
        out = self._run("-O", cwd=str(PKG_DIR.parent))
        self.assertEqual((out.returncode, out.stdout.strip()), (0, "100"), out.stderr)

    def test_runs_outside_repository_root(self):
        out = self._run(cwd=tempfile.mkdtemp())
        self.assertEqual((out.returncode, out.stdout.strip()), (0, "100"), out.stderr)


if __name__ == "__main__":
    unittest.main()
