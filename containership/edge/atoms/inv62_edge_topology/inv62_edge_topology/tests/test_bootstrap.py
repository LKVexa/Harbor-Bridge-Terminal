"""Deterministic bootstrap from an empty environment (MC-030) using the
shipped example config, overlays and seed (validates the docs' commands)."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
EX = PKG / "examples"


def write_secrets(root: pathlib.Path) -> None:
    for rel, val in {"inv62/token/k2026-09": b"t" * 48, "inv62/audit": b"a" * 48, "inv62/state": b"s" * 48}.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(val)
        os.chmod(p, 0o600)


class BootstrapTest(unittest.TestCase):
    def run_cli(self, secrets, state, report, *extra):
        cmd = [sys.executable, "-m", "inv62_edge_topology.production.bootstrap", "--config", str(EX / "config.base.json"),
               "--overlay", str(EX / "overlays" / "prod.json"), "--overlay", str(EX / "overlays" / "site-s1.json"),
               "--secrets-dir", str(secrets), "--seed", str(EX / "seed.topology.json"), "--tenant", "tenant-a",
               "--state-dir", str(state), "--report", str(report), *extra]
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(PKG.parent))

    @unittest.skipUnless(os.name == "posix", "secret file permission check is POSIX")
    def test_clean_bootstrap_is_deterministic_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            write_secrets(root / "secrets")
            r1 = self.run_cli(root / "secrets", root / "state", root / "r1.json")
            self.assertEqual(r1.returncode, 0, r1.stderr)
            rep1 = json.loads((root / "r1.json").read_text())
            self.assertEqual((rep1["nodes"], rep1["links"], rep1["config_generation"]), (6, 6, 1))
            r2 = self.run_cli(root / "secrets", root / "state", root / "r2.json")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            rep2 = json.loads((root / "r2.json").read_text())
            self.assertEqual(rep1["snapshot_sha256"], rep2["snapshot_sha256"])
            self.assertEqual(rep1["config_digest"], rep2["config_digest"])
            with tempfile.TemporaryDirectory() as d2:
                write_secrets(pathlib.Path(d2) / "secrets")
                self.run_cli(pathlib.Path(d2) / "secrets", pathlib.Path(d2) / "state", pathlib.Path(d2) / "r.json")
                self.assertEqual(json.loads((pathlib.Path(d2) / "r.json").read_text())["snapshot_sha256"], rep1["snapshot_sha256"])

    def test_missing_secret_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "secrets").mkdir()
            r = self.run_cli(root / "secrets", root / "state", root / "r.json")
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse((root / "r.json").exists())


if __name__ == "__main__":
    unittest.main()
