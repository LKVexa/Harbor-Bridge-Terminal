"""WS 11, 15, 16, 17, 20 -- benchmark gate, RTM integrity, evidence manifest, waivers, exit gate, SAST."""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
import time
import unittest

from _support import pkg
from inv32_elastic_virtualization import bench, release


class BenchGateTest(unittest.TestCase):
    def test_small_run_emits_reproducible_schema(self):
        res = bench.run(iterations=5, guests=4, seed=3)
        self.assertEqual(res["schema"], "PK_INV32_BENCH/1")
        for k in ("memory_grow", "memory_reclaim", "snapshot", "audit_append", "decision_only"):
            self.assertIn(k, res["ops"])
            self.assertLessEqual(res["ops"][k]["p50"], res["ops"][k]["p99"])
        for k in ("python", "platform", "cpu_count", "package_version"):
            self.assertIn(k, res["env"])

    def test_gate_regression_and_waiver_expiry(self):
        base = {"ops": {"memory_grow": {"p50": 0.001, "p95": 0.002, "p99": 0.003}}}
        cur = {"ops": {"memory_grow": {"p50": 0.002, "p95": 0.002, "p99": 0.003}}, "slo": {}}
        self.assertFalse(bench.gate(base, cur)["pass"])
        w = [{"metric": "memory_grow.p50", "owner": "x", "expires_at": time.time() + 60}]
        self.assertTrue(bench.gate(base, cur, waivers=w)["pass"])
        w[0]["expires_at"] = time.time() - 1
        self.assertFalse(bench.gate(base, cur, waivers=w)["pass"])


class ReleaseToolsTest(unittest.TestCase):
    SRC = pathlib.Path(__file__).resolve().parents[1]  # source tree, even when the wheel is installed

    def test_rtm_is_complete_and_consistent(self):
        res = release.rtm_check(self.SRC / "RTM.json", source_pkg=self.SRC)
        self.assertTrue(res["pass"], res["errors"][:10])
        rtm = json.loads((self.SRC / "RTM.json").read_text())
        self.assertGreater(len(rtm["rows"]), 600)
        controls = {c for r in rtm["rows"] for c in r.get("controls", [])}
        for n in (9, 10, 11, 20, 23, 31, 40, 57, 60, 90, 100):
            self.assertIn(f"INV-32-C{n:03d}", controls)

    def test_rtm_check_catches_defects(self):
        with tempfile.TemporaryDirectory() as d:
            bad = {"rows": [{"id": "X", "status": "IMPLEMENTED", "priority": "P0"},
                            {"id": "X", "status": "BLOCKED", "priority": "P0"},
                            {"id": "Y", "status": "IMPLEMENTED", "priority": "P0", "implementation": ["nope.py"],
                             "tests": ["test_x::test_missing"]}]}
            p = pathlib.Path(d) / "rtm.json"
            p.write_text(json.dumps(bad))
            errs = " ".join(release.rtm_check(p, source_pkg=self.SRC)["errors"])
            for needle in ("duplicate", "without implementation", "without automated", "BLOCKED without blocker",
                           "file missing", "test missing"):
                self.assertIn(needle, errs)

    def test_sast_and_sbom(self):
        self.assertTrue(release.sast()["pass"])
        sb = release.sbom()
        self.assertEqual(sb["bomFormat"], "CycloneDX")
        self.assertTrue(any(c["name"] == "controller.py" for c in sb["components"]))

    def test_evidence_sign_verify_and_gate_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "manifest.json"
            os.environ["INV32_RELEASE_KEY"] = "r" * 40
            try:
                release.evidence(out, tests=None, bench=None, artifacts=[])
                self.assertTrue(release.verify_evidence(out))
                doc = json.loads(out.read_text())
                doc["release_version"] = "9.9.9"
                out.write_text(json.dumps(doc))
                self.assertFalse(release.verify_evidence(out))
                release.evidence(out, tests=None, bench=None, artifacts=[])
                g = release.gate(out)
            finally:
                del os.environ["INV32_RELEASE_KEY"]
            self.assertEqual(g["result"], "FAIL")
            joined = " ".join(g["reasons"])
            for needle in ("ownership", "provenance", "tests", "compatibility", "approvals"):
                self.assertIn(needle, joined)

    def test_version_single_source(self):
        root = release.ROOT
        py = (root / "pyproject.toml").read_text() if (root / "pyproject.toml").exists() else ""
        self.assertEqual((release.PKG / "VERSION").read_text().strip(), pkg.__version__)
        if py:
            self.assertIn('version = { file = "inv32_elastic_virtualization/VERSION" }', py)

    def test_compat_matrix_and_governance_shape(self):
        m = json.loads((release.PKG / "compat_matrix.json").read_text())
        for row in m["rows"]:
            self.assertIn(row["status"], m["status_values"])
            self.assertTrue(set(m["columns"]) <= set(row))
        g = json.loads((release.PKG / "governance.json").read_text())
        for k in ("owners", "escalation", "severity", "paging", "review_cadence"):
            self.assertIn(k, g)


if __name__ == "__main__":
    unittest.main()
