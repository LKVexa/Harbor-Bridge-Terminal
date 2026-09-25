"""Bootstrap from an empty directory to healthy, and fail-closed paths (C040)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import PKG_DIR


class BootstrapTest(unittest.TestCase):
    def run_boot(self, *extra, key_mode=0o600):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            kf = d / "keys.json"
            kf.write_text(json.dumps({"keys": {"k1": os.urandom(32).hex()}, "active": "k1"}))
            os.chmod(kf, key_mode)
            (d / "state").mkdir()
            r = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "bootstrap.py"), "--profile",
                                str(PKG_DIR / "config" / "profiles" / "prod.json"), "--key-file", str(kf),
                                "--state-dir", str(d / "state"), *extra], capture_output=True, text=True, timeout=120)
            hist = (d / "state" / "config-history.json")
            return r, json.loads(r.stdout) if r.stdout.strip().startswith("{") else None, hist.exists()

    def test_empty_to_healthy_and_deterministic(self):
        r1, o1, hist = self.run_boot()
        self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
        self.assertEqual(o1["status"], "healthy")
        self.assertTrue(o1["health"]["ready"])
        self.assertTrue(hist)
        _, o2, _ = self.run_boot("--dry-run")
        self.assertEqual(o2["status"], "dry_run_ok")

    def test_bad_key_permissions_fail_closed(self):
        r, o, hist = self.run_boot(key_mode=0o644)
        self.assertEqual(r.returncode, 2)
        self.assertIn("key_file_permissions", {f["code"] for f in o["findings"]})
        self.assertFalse(hist)


if __name__ == "__main__":
    unittest.main()
