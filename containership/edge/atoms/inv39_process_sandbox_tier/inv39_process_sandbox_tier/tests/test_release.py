"""MC-022/103/105 — reproducible build, SBOM/provenance consistency, exit gate refuses."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from _support import PKG_DIR

TOOLS = PKG_DIR / "tools"


def build(d):
    return json.loads(subprocess.run([sys.executable, str(TOOLS / "build_release.py"), d],
                                     capture_output=True, text=True, check=True,
                                     env={k: v for k, v in os.environ.items() if k != "INV39_RELEASE_KEY"}).stdout)


class ReleaseTest(unittest.TestCase):
    def test_reproducible(self):
        a, b = build(tempfile.mkdtemp()), build(tempfile.mkdtemp())
        self.assertEqual(a["sha256"], b["sha256"])
        self.assertFalse(a["signed"])

    def test_sbom_and_provenance_bind_artifact(self):
        d = tempfile.mkdtemp()
        r = build(d)
        stem = pathlib.Path(r["artifact"]).name[:-4]
        prov = json.loads((pathlib.Path(d) / f"{stem}.provenance.json").read_text())
        sbom = json.loads((pathlib.Path(d) / f"{stem}.sbom.json").read_text())
        self.assertEqual(prov["subject"][0]["digest"]["sha256"], r["sha256"])
        self.assertEqual(sbom["metadata"]["component"]["hashes"][0]["content"], r["sha256"])
        self.assertEqual(len(prov["predicate"]["buildDefinition"]["resolvedDependencies"]), r["files"])

    def test_exit_gate_reports_no_go(self):
        d = tempfile.mkdtemp()
        build(d)
        out = pathlib.Path(d) / "gate.json"
        p = subprocess.run([sys.executable, str(TOOLS / "exit_gate.py"), "--dist", d, "--skip-tests", "--out", str(out)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)["verdict"], "NO_GO")
        rep = json.loads(out.read_text())
        self.assertTrue(any("MC-001" in r for r in rep["reasons"]))
        self.assertTrue(any("unsigned" in r for r in rep["reasons"]))


class TraceabilityTest(unittest.TestCase):
    def test_all_components_and_checks_traced(self):
        tr = json.loads((PKG_DIR / "TRACEABILITY.json").read_text())
        self.assertEqual(len(tr["components"]), 106)
        self.assertEqual(len(tr["checks"]), 100)
        self.assertEqual(sum(tr["summary"].values()), 106)
        self.assertEqual(tr["accepted"], 0)
        for c in tr["components"]:
            with self.subTest(c["id"]):
                self.assertIn(c["status"], ("IMPLEMENTED", "PARTIAL", "BLOCKED"))
                if c["status"] != "IMPLEMENTED":
                    self.assertTrue(c["gap"], "non-implemented items must state their gap")
                for f in c["code"]:
                    path = f.split("::")[0].split(" (")[0].split(" --")[0].split(" EX-")[0]
                    self.assertTrue((PKG_DIR / path).exists(), path)

    def test_named_tests_exist(self):
        import unittest as u
        tr = json.loads((PKG_DIR / "TRACEABILITY.json").read_text())
        names = sorted({t for c in tr["components"] for t in c["tests"]})
        self.assertEqual(u.defaultTestLoader.loadTestsFromNames(names).countTestCases() > 0, True)
        for n in names:
            with self.subTest(n):
                self.assertGreater(u.defaultTestLoader.loadTestsFromName(n).countTestCases(), 0)


if __name__ == "__main__":
    unittest.main()
