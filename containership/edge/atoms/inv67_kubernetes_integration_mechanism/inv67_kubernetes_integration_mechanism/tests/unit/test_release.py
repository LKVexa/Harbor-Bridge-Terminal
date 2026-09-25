"""Packaging, CI, SBOM/NOTICE, static-analysis config, release manifest, gate (items 54, 55, 63-68)."""
import copy
import importlib
import json
import shutil
import tempfile
import tomllib
import pathlib
import unittest

import _support as S

REL = importlib.import_module(S.PKG.__name__ + ".governance.release")
GATE = importlib.import_module(S.PKG.__name__ + ".governance.gate")


class Release(unittest.TestCase):
    def test_pyproject_metadata(self):
        pp = tomllib.loads((S.PKG_DIR / "pyproject.toml").read_text())
        self.assertEqual(pp["project"]["dependencies"], [])
        self.assertEqual(pp["project"]["dynamic"], ["version"])
        self.assertEqual(pp["tool"]["setuptools"]["dynamic"]["version"]["file"], "VERSION")
        for dep in pp["project"]["optional-dependencies"]["dev"]:
            self.assertIn("==", dep, "dev tools must be pinned")
        self.assertEqual(S.PKG.__version__, (S.PKG_DIR / "VERSION").read_text().strip())

    def test_ci_workflow_runs_gate(self):
        ci = (S.PKG_DIR / ".github/workflows/ci.yml").read_text()
        for must in ("python -O -m unittest", "governance.gate", "governance.release verify", "plane.manifests",
                     "ruff check", "mypy", "bandit", "environment: release", '"3.10"', '"3.13"'):
            self.assertIn(must, ci)

    def test_sbom_and_notice(self):
        sb = json.loads((S.PKG_DIR / "sbom.cdx.json").read_text())
        self.assertEqual(sb, REL.sbom())
        self.assertEqual(sb["components"], [])
        self.assertIn("NOT DECLARED", (S.PKG_DIR / "NOTICE").read_text())

    def test_static_analysis_config(self):
        pp = tomllib.loads((S.PKG_DIR / "pyproject.toml").read_text())
        self.assertIn("S", pp["tool"]["ruff"]["lint"]["select"])
        self.assertTrue(pp["tool"]["mypy"]["check_untyped_defs"])
        self.assertIn("bandit", pp["tool"])

    def test_manifest_detects_tamper_missing_extra(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / "pkg"
            shutil.copytree(S.PKG_DIR, root, ignore=shutil.ignore_patterns("__pycache__", "evidence"))
            m = REL.build(root, key=b"k" * 32)
            self.assertEqual(m, REL.build(root, key=b"k" * 32), "manifest must be deterministic")
            self.assertEqual(REL.verify(root, m, key=b"k" * 32), [])
            self.assertTrue(REL.verify(root, m, key=b"x" * 32))
            (root / "README.md").write_text("tampered")
            (root / "EXTRA.txt").write_text("x")
            (root / "NOTICE").unlink()
            probs = REL.verify(root, m)
            self.assertIn("altered: README.md", probs)
            self.assertIn("unexpected: EXTRA.txt", probs)
            self.assertIn("missing: NOTICE", probs)
            m2 = copy.deepcopy(m); m2["files"][0]["sha256"] = "0" * 64
            self.assertIn("manifest digest mismatch (manifest edited)", REL.verify(root, m2))
            unsigned = REL.build(root)
            self.assertEqual(unsigned["seal"]["alg"], "unsigned")

    def test_gate_runs_and_refuses_self_acceptance(self):
        reqs = json.loads((S.PKG_DIR / "docs/requirements.json").read_text())["requirements"]
        fake = {t: "pass" for r in reqs for t in r["tests"]}
        for refs in GATE.DIRECT.values():
            for t in refs:
                fake[t + "x" if t.endswith(".") else t] = "pass"
        ev = GATE.evaluate(fake)
        self.assertEqual(len(ev["components"]), 68)
        self.assertEqual(sum(c["acceptance_gate"] == "MET" for c in ev["components"]), 0,
                         "independent review (EXC-002) is open: nothing may be accepted from here")
        V = S.mod("schema")
        schema = json.loads((S.PKG_DIR / "schemas/INV67_EVIDENCE_v1.schema.json").read_text())
        for c in ev["components"]:
            self.assertEqual(V.errors(schema, c), [], c["item"])
        fake[next(iter(fake))] = "fail"
        self.assertTrue(any(c["result"] == "FAIL" for c in GATE.evaluate(fake)["components"]))
        b = GATE.chain(ev["components"], None)
        self.assertEqual(b["seal"]["alg"], "unsigned")
        self.assertEqual(len(b["links"]), 68)


if __name__ == "__main__":
    unittest.main()
