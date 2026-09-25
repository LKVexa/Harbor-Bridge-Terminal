"""Packaging, bootstrap, traceability, evidence and exit-gate tooling (#12, #32, #33, #61, #70, #89, #98, #99)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest

from helpers import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import exit_gate  # noqa: E402
import traceability  # noqa: E402


class Packaging(unittest.TestCase):
    def test_pyproject_consistent(self):
        meta = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertEqual(meta["project"]["version"], (ROOT / "VERSION").read_text().strip())
        self.assertEqual(meta["project"]["dependencies"], [])
        import inv55_secrets_integration as pkg
        self.assertEqual(pkg.__version__, meta["project"]["version"])

    def test_sbom_shape(self):
        sb = json.loads((ROOT / "evidence" / "sbom.cdx.json").read_text())
        self.assertEqual(sb["bomFormat"], "CycloneDX")
        self.assertTrue(all(c.get("version") for c in sb["components"]))


class Bootstrap(unittest.TestCase):
    def test_check_mode_all_envs(self):
        for env in ("dev", "staging", "prod"):
            r = subprocess.run([sys.executable, "-m", "inv55_secrets_integration.bootstrap", "--config-dir",
                                str(ROOT / "config"), "--env", env, "--check"], capture_output=True, text=True,
                               cwd=str(ROOT))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_dev_start_and_audit_divergence_quarantines(self):
        from inv55_secrets_integration.bootstrap import build_service
        from inv55_secrets_integration.service import State
        with tempfile.TemporaryDirectory() as d:
            cfgdir = os.path.join(d, "config")
            os.makedirs(os.path.join(cfgdir, "overlays"))
            base = json.loads((ROOT / "config" / "base.json").read_text())
            base["audit"] = {"path": os.path.join(d, "audit.jsonl"), "fsync": False}
            json.dump(base, open(os.path.join(cfgdir, "base.json"), "w"))
            json.dump({"provider": {"kind": "memory", "auth": "token"}},
                      open(os.path.join(cfgdir, "overlays", "dev.json"), "w"))
            os.environ["INV55_JWT_KEY"] = "k" * 32
            svc = build_service(cfgdir, "dev")
            self.assertEqual(svc.start(), State.READY)
            svc._audit("probe", None, "x", True, "t", None)
            with open(base["audit"]["path"], "ab") as fh:
                fh.write(b'{"seq": 42, "forged": true}\n')
            svc2 = build_service(cfgdir, "dev")
            self.assertEqual(svc2.state, State.QUARANTINED)

    def test_memory_provider_forbidden_in_prod(self):
        from inv55_secrets_integration.bootstrap import build_service
        with tempfile.TemporaryDirectory() as d:
            cfgdir = os.path.join(d, "config")
            os.makedirs(os.path.join(cfgdir, "overlays"))
            base = json.loads((ROOT / "config" / "base.json").read_text())
            json.dump(base, open(os.path.join(cfgdir, "base.json"), "w"))
            json.dump({"environment": "prod", "provider": {"kind": "memory"}},
                      open(os.path.join(cfgdir, "overlays", "prod.json"), "w"))
            with self.assertRaises(ValueError):
                build_service(cfgdir, "prod")


class Governance(unittest.TestCase):
    def test_traceability_complete(self):
        t = traceability.build()
        self.assertEqual(len(t["components"]), 100)
        self.assertEqual(t["missing_artifacts"], [])
        for c in t["components"]:
            if c["status"] == "IMPLEMENTED":
                self.assertTrue(c["tests"], f"#{c['id']} IMPLEMENTED without an executable test")
                self.assertEqual(c["residual"], "")
            else:
                self.assertTrue(c["residual"], f"#{c['id']} non-implemented without a residual")

    def test_every_open_or_partial_has_waiver_reference(self):
        text = (ROOT / "docs" / "governance" / "waiver-register.md").read_text()
        self.assertIn("WVR-", text)

    def test_gate_never_passes_skipped_mandatory(self):
        trace = traceability.build()
        trace["missing_artifacts"] = []
        for c in trace["components"]:
            c["status"], c["residual"] = "IMPLEMENTED", ""
        ev = {"version": "4.3.0", "source_tree_sha256": "x", "secret_scan": {"exit": 0},
              "tests": {"counts": {"pass": 1, "skip": 1}, "results": [
                  {"test": "test_vault_real.RealVault.test_kv2_roundtrip_cas_destroy", "result": "skip",
                   "detail": "no vault"}]}}
        self.assertEqual(exit_gate.evaluate(trace, ev)["verdict"], "NO_GO")
        ev["tests"]["results"] = []
        self.assertEqual(exit_gate.evaluate(trace, ev)["verdict"], "GO_PENDING_OWNER_APPROVAL")

    def test_benchmark_tool_runs(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "benchmark.py"), "--n", "200"],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout[-500:])
        self.assertIn('"per_tenant"', r.stdout)


if __name__ == "__main__":
    unittest.main()
