"""Artifact integrity tests that do not require pk_core or network access."""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv04_current_orchestration as pkg  # noqa: E402


class ArtifactIntegrityTest(unittest.TestCase):
    def test_version_is_synchronized(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")
        self.assertIn("## 4.3.0", (PKG_DIR / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn('version = "4.3.0"', (PKG_DIR / "pyproject.toml").read_text(encoding="utf-8"))
        from inv04_current_orchestration.runtime import RUNTIME_VERSION
        self.assertEqual(RUNTIME_VERSION, "4.3.0")

    def test_checklist_has_exactly_100_unique_items(self):
        data = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        self.assertEqual(data["item_count"], 100)
        self.assertEqual(len(data["items"]), 100)
        self.assertEqual(len({item["check_id"] for item in data["items"]}), 100)

    def test_interface_schemas_are_valid_json_and_versioned(self):
        expected = {
            "PK_ORCH_RECONCILE_v1.schema.json": "PK_ORCH_RECONCILE/1",
            "PK_ORCH_DRAIN_v1.schema.json": "PK_ORCH_DRAIN/1",
            "PK_ORCH_INVENTORY_v1.schema.json": "PK_ORCH_INVENTORY/1",
            "PK_ORCH_ERROR_v1.schema.json": "PK_ORCH_ERROR/1",
        }
        for filename, title in expected.items():
            data = json.loads((PKG_DIR / "schemas" / filename).read_text(encoding="utf-8"))
            self.assertEqual(data["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(data["title"], title)

    def test_evidence_gate_passes_and_status_is_generated(self):
        """Component 77: the evidence-quality gate must accept the shipped status."""
        import subprocess
        proc = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "evidence_gate.py")], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        status = json.loads((PKG_DIR / "COMPONENT_STATUS.json").read_text(encoding="utf-8"))
        self.assertEqual(len(status["components"]), 80)
        self.assertNotIn("PASS", {c["exit_gate"] for c in status["components"]})

    def test_manifest_matches_shipped_files(self):
        manifest = PKG_DIR / "MANIFEST.sha256"
        import hashlib
        for line in manifest.read_text(encoding="utf-8").splitlines():
            digest, rel = line.split("  ", 1)
            path = PKG_DIR / rel
            self.assertTrue(path.is_file(), rel)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest, rel)

    def test_audit_artifacts_exist(self):
        self.assertTrue((PKG_DIR / "AUDIT_REPORT.md").is_file())
        self.assertTrue((PKG_DIR / "MISSING_COMPONENTS.md").is_file())


if __name__ == "__main__":
    unittest.main()
