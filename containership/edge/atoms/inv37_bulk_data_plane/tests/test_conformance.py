"""Conformance fixtures run in CI and are immutable (C029, C016, C082)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import PKG_DIR


class ConformanceTest(unittest.TestCase):
    def test_all_fixtures_pass(self):
        r = subprocess.run([sys.executable, str(PKG_DIR / "conformance" / "run.py")], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1])["status"], "PASS")

    def test_modified_fixture_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            dst = Path(d) / PKG_DIR.name
            shutil.copytree(PKG_DIR, dst, ignore=shutil.ignore_patterns("__pycache__", "artifacts"))
            f = sorted((dst / "conformance" / "fixtures").glob("*.json"))[0]
            obj = json.loads(f.read_text()); obj["expect"]["ok"] = not obj["expect"]["ok"]
            f.write_text(json.dumps(obj))
            r = subprocess.run([sys.executable, str(dst / "conformance" / "run.py")], capture_output=True, text=True, timeout=120)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("modified:", r.stdout)

    def test_golden_v420_artifacts_still_readable(self):
        """Backward compatibility: v4.2.0-shaped manifest/resume are accepted."""
        golden = json.loads((PKG_DIR / "conformance" / "golden" / "v4.2.0.json").read_text())
        sys.path.insert(0, str(PKG_DIR.parent))
        pkg = __import__(PKG_DIR.name)
        m = pkg.validate_manifest(golden["manifest"])
        self.assertEqual(m["object"], golden["manifest"]["object"])
        legacy = {k: v for k, v in golden["manifest"].items() if k not in ("algorithm", "chunk_count")}
        pkg.validate_manifest(legacy)  # v4.1.0 writers omitted optional fields
        self.assertEqual(golden["resume"]["schema"], "PK_BULK_RESUME/1")


if __name__ == "__main__":
    unittest.main()
