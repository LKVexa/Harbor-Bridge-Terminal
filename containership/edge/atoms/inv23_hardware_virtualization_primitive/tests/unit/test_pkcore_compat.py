"""MC-01 resolver: precedence, shadowing, API and version compatibility.

Uses throw-away *stub* packages written to a temp dir purely to exercise the resolver's
decision logic; they are not a pk_core implementation and never certify anything.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests._boot import PKG_DIR

SNIPPET = (
    "import json,sys; sys.path.insert(0,%r); "
    "from inv23_hardware_virtualization_primitive import pkcore_compat as c; "
    "print(json.dumps(c.resolve().as_evidence()))"
) % str(PKG_DIR.parent)


def stub(version='"4.2.0"', api=True):
    d = pathlib.Path(tempfile.mkdtemp())
    p = d / "pk_core"
    p.mkdir()
    (p / "__init__.py").write_text(f"__version__ = {version}\n" if version else "")
    if api:
        (p / "checklist.py").write_text("class ChecklistItem: pass\nclass Finding: pass\n")
        (p / "component.py").write_text("class Component: pass\n")
        (p / "contract.py").write_text("class Contract: pass\nclass Dependency: pass\nclass Slo: pass\n")
    return str(d)


def run(**env):
    e = {k: v for k, v in os.environ.items() if k not in ("PK_CORE_PATH", "INV23_CONFORMANCE")}
    e.update(env)
    out = subprocess.run([sys.executable, "-c", SNIPPET], capture_output=True, text=True, env=e, cwd=tempfile.mkdtemp())
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


class ResolverTest(unittest.TestCase):
    def test_missing(self):
        r = run(PK_CORE_PATH=tempfile.mkdtemp())
        self.assertEqual(r["status"], "dependency_missing")
        self.assertIn("pk_core/__init__.py", r["diagnostics"][0])

    def test_ok_via_env(self):
        r = run(PK_CORE_PATH=stub())
        self.assertEqual((r["status"], r["source"], r["version"]), ("ok", "env", "4.2.0"))
        self.assertEqual(r["expected_range"], ">=4.0.0,<=4.99.99")

    def test_incompatible_version_and_api(self):
        self.assertEqual(run(PK_CORE_PATH=stub('"3.9.0"'))["status"], "dependency_incompatible")
        self.assertEqual(run(PK_CORE_PATH=stub('"5.0.0"'))["status"], "dependency_incompatible")
        r = run(PK_CORE_PATH=stub(api=False))
        self.assertEqual(r["status"], "dependency_incompatible")
        self.assertIn("pk_core.contract", " ".join(r["diagnostics"]))

    def test_unknown_version_fatal_only_in_release(self):
        self.assertEqual(run(PK_CORE_PATH=stub(None))["status"], "ok")
        self.assertEqual(run(PK_CORE_PATH=stub(None), INV23_CONFORMANCE="release")["status"], "dependency_incompatible")

    def test_unrelated_pk_core_on_sys_path_is_rejected(self):
        # an unrelated pk_core found elsewhere on sys.path must not satisfy an explicit PK_CORE_PATH
        other = stub()
        want = tempfile.mkdtemp()
        e = dict(PYTHONPATH=other, PK_CORE_PATH=want)
        self.assertEqual(run(**e)["status"], "dependency_missing")


if __name__ == "__main__":
    unittest.main()
