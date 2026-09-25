"""Governance/evidence tests: M01 M21 M22 M23 M25 M28 M29 M32 M33 M41 M42 M46 M47."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

from helpers import PKG_DIR, pkg

PY = sys.executable
TOOLS = PKG_DIR / "tools"


def tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, *args], cwd=PKG_DIR, capture_output=True, text=True, timeout=600)


class GovernanceTest(unittest.TestCase):
    def test_version_and_python_floor(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")
        self.assertIn('version = "4.3.0"', (PKG_DIR / "pyproject.toml").read_text())
        self.assertGreaterEqual(sys.version_info[:2], (3, 10))

    def test_master_is_labelled_replacement_and_indexed(self):
        text = (PKG_DIR / "MASTER.md").read_text()
        self.assertIn("REPLACEMENT", text)
        self.assertIn("Original recovered? | **No.**", text)
        self.assertEqual(len(set(__import__("re").findall(r"MR-\d{3}", text))), 30)

    def test_rtm_is_complete_and_docs_current(self):
        res = tool("tools/rtm.py", "--check")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual(tool("tools/gen_error_doc.py", "--check").returncode, 0)

    def test_stdlib_only_and_sbom(self):
        res = tool("tools/sbom.py", "--check-imports")
        self.assertEqual(res.returncode, 0, res.stdout)
        sys.path.insert(0, str(TOOLS))
        import sbom  # noqa: E402
        doc = sbom.sbom()
        self.assertEqual(doc["bomFormat"], "CycloneDX")
        self.assertTrue(any(c["name"] == "pk_core" and c["version"] == "UNPINNED" for c in doc["components"]))

    def test_build_digest_is_deterministic(self):
        sys.path.insert(0, str(TOOLS))
        import build_info  # noqa: E402
        self.assertEqual(build_info.tree_digest()[0], build_info.tree_digest()[0])
        self.assertEqual(build_info.build_info()["runtime_dependencies"], [])

    def test_release_gate_falsifier_and_blockers(self):
        res = tool("tools/release_gate.py", "--self-test")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        sys.path.insert(0, str(TOOLS))
        import release_gate  # noqa: E402
        blockers = release_gate.blockers()
        for needle in ("OWNERS", "waivers", "ADR-0001", "LICENSE", "pk_core", "release approval"):
            self.assertTrue(any(needle in b for b in blockers), needle)

    def test_human_fields_are_not_fabricated(self):
        owners = json.loads((PKG_DIR / "ops" / "OWNERS.json").read_text())
        self.assertEqual(owners["engineering_owner"], "UNASSIGNED")
        for w in json.loads((PKG_DIR / "ops" / "WAIVERS.json").read_text())["waivers"]:
            self.assertIsNone(w["approved_by"])
        for f in ("ops/PERF_THRESHOLDS.json", "ops/SLO.json"):
            self.assertEqual(json.loads((PKG_DIR / f).read_text())["status"], "PROPOSED")
        self.assertIn("Status: PROPOSED", (PKG_DIR / "docs" / "ADR-0001-execution-tier-semantics.md").read_text())
        self.assertFalse((PKG_DIR / "LICENSE").exists())

    def test_ops_definitions_parse(self):
        for f in ("alerts.json", "dashboard.json", "EXTERNAL_DEPENDENCIES.json"):
            json.loads((PKG_DIR / "ops" / f).read_text())
        for doc in ("RUNBOOK.md", "THREAT_MODEL.md", "PATCH_EOL_POLICY.md", "COMPATIBILITY.md", "TELEMETRY.md"):
            self.assertTrue((PKG_DIR / "docs" / doc).read_text().strip())

    def test_quick_fuzz_run(self):
        res = tool("tools/fuzz.py", "--iterations", "200", "--seed", "3")
        self.assertEqual(res.returncode, 0, res.stderr[-2000:])
        self.assertIn('"result": "PASS"', res.stdout)

    def test_corrupt_complete_final_wal_record_is_not_silently_dropped(self):
        import os, shutil, tempfile
        from pln04_execution_plane import store
        from pln04_execution_plane.errors import PlaneError
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        s = store.FileStateStore(d, fsync=False)
        s.cas("a", 0, {"v": 1})
        s.cas("b", 0, {"v": 2})
        s.close()
        p = os.path.join(d, "state.wal.jsonl")
        lines = open(p).read().splitlines()
        lines[-1] = lines[-1].replace('"v":2', '"v":3')
        open(p, "w").write("\n".join(lines) + "\n")
        with self.assertRaises(PlaneError):
            store.FileStateStore(d, fsync=False)


if __name__ == "__main__":
    unittest.main()
