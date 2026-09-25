"""Release/evidence machinery tests (components 03, 04, 11, 62, 71, 82, 89, 99)."""
from __future__ import annotations

import importlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, str(PKG / "tools"))
P = PKG.name
config = importlib.import_module(f"{P}.config")
storage = importlib.import_module(f"{P}.storage")
ge = importlib.import_module("gen_evidence")


class Release(unittest.TestCase):
    def test_c03_deployment_contexts_validate(self):
        base = json.loads((PKG / "config" / "base.json").read_text())
        ctx = {"cloud": ["production-kafka.json", "cloud-sqs.json"], "dc": ["datacenter-rabbitmq.json"],
               "near-edge": ["near-edge-durable.json"], "far-edge": ["edge-durable.json"]}
        for name, files in ctx.items():
            for f in files:
                cfg = config.apply_overlays(base, json.loads((PKG / "config" / "overlays" / f).read_text()))
                self.assertEqual(config.validate(cfg), [], f"{name}/{f}")
                self.assertEqual(cfg["profile"], "production")
        # far-edge requires encryption at rest; stripping it must break the key_ref rule only if enabled
        cfg = config.apply_overlays(base, json.loads((PKG / "config" / "overlays" / "edge-durable.json").read_text()),
                                    {"storage": {"key_ref": None}})
        self.assertTrue(config.validate(cfg))

    def test_c04_startup_under_one_second(self):
        sys.path.insert(0, str(PKG / "tests"))
        from test_production_layer import make_service
        t0 = time.perf_counter()
        d = tempfile.mkdtemp()
        storage.DurableLog(d, 4).close()
        make_service()
        self.assertLess(time.perf_counter() - t0, 1.0)

    def test_c62_c71_benchmark_harness_and_gate(self):
        out = pathlib.Path(tempfile.mkdtemp()) / "b.json"
        r = subprocess.run([sys.executable, "-B", str(PKG / "bench" / "harness.py"), "--n", "3000", "--out", str(out),
                            "--gate"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-500:] + r.stderr[-500:])
        res = json.loads(out.read_text())
        self.assertIn("environment", res)
        self.assertTrue(all(x["p99_ms"] >= x["p50_ms"] for x in res["results"]))

    def test_c82_public_api_surface_stable(self):
        pkg = importlib.import_module(P)
        for name in ("FanoutBroker", "PartitionedLog", "BrokerError", "Outcome", "build_contract", "__version__"):
            self.assertTrue(hasattr(pkg, name), name)

    def test_c89_c99_gate_never_passes_without_review(self):
        comps = [{"id": "01", "priority": "P0", "status": "LOCAL_VERIFIED", "independent_review": None}]
        self.assertEqual(ge.compute_gate(comps, {"FAIL": 0, "ERROR": 0})[0], "NO_GO")
        comps[0]["independent_review"] = {"reviewer": "someone-else"}
        self.assertEqual(ge.compute_gate(comps, {"FAIL": 0, "ERROR": 0})[0], "GO")
        self.assertEqual(ge.compute_gate(comps, {"FAIL": 1, "ERROR": 0})[0], "NO_GO")
        comps[0]["status"] = "PARTIAL"
        self.assertEqual(ge.compute_gate(comps, {})[0], "NO_GO")

    def test_c11_c89_artifact_claims_are_checked(self):
        self.assertTrue(ge.artifact_exists("CODEOWNERS"))
        self.assertTrue(ge.artifact_exists("config.HARD_LIMITS"))
        self.assertTrue(ge.artifact_exists("storage.py::DurableLog"))
        self.assertFalse(ge.artifact_exists("nonexistent.py"))
        self.assertFalse(ge.artifact_exists("config.NO_SUCH_SYMBOL"))


if __name__ == "__main__":
    unittest.main()
