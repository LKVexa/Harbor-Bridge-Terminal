"""Components 50, 52, 53-60 tooling and documents."""
import json
import os
import sys
import unittest

from fixtures import make_stack, sample, signed, tmpdir

COMP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(COMP, "tools"))
import bench, dashboard, doc_check, regression_gate, runbooks, sbom  # noqa: E402
from gap09_unified_observability.components.controls import HealthModel  # noqa: E402


class TestBench(unittest.TestCase):
    def test_quick_run_shape(self):
        d = bench.main(None, quick=True)
        names = {r["name"] for r in d["results"]}
        self.assertEqual(names, {"canonicalize_10_samples", "ed25519_verify", "traceparent_parse", "verified_ingest_1_sample_fsync"})
        for r in d["results"]:
            self.assertLessEqual(r["p50_us"], r["p95_us"]); self.assertLessEqual(r["p95_us"], r["p99_us"])

    def test_committed_baseline_exists(self):
        with open(os.path.join(COMP, "evidence", "perf_baseline.json")) as fh:
            self.assertEqual(json.load(fh)["schema"], "GAP09-PERF/1")


class TestRegressionGate(unittest.TestCase):
    def base(self, p95=10.0):
        return {"host": {"python": "x"}, "results": [{"name": "a", "p95_us": p95, "p99_us": 20.0}]}

    def test_pass_regress_incomplete(self):
        self.assertEqual(regression_gate.compare(self.base(), self.base())[0], 0)
        self.assertEqual(regression_gate.compare(self.base(), self.base(16.0))[0], 1)
        other = self.base(); other["host"] = {"python": "y"}
        self.assertEqual(regression_gate.compare(self.base(), other)[0], 3)
        self.assertEqual(regression_gate.compare(self.base(), {"host": {"python": "x"}, "results": []})[0], 3)


class TestSBOM(unittest.TestCase):
    def test_every_file_hashed_and_stdlib_only(self):
        doc = sbom.build()
        names = {c["name"] for c in doc["components"]}
        self.assertIn("gap09_unified_observability/runtime.py", names)
        self.assertIn("gap09_unified_observability/components/ingest.py", names)
        self.assertTrue(all(len(c["hashes"][0]["content"]) == 64 for c in doc["components"]))
        self.assertIn("stdlib only", doc["metadata"]["properties"][0]["value"])


class TestDocs(unittest.TestCase):
    def test_documents_present_and_nonempty(self):
        for p in ("docs/ADR-001-v5.1-overlay.md", "docs/COMPATIBILITY.md", "docs/VULN_EOL_POLICY.md", "docs/RUNBOOKS.md",
                  "docs/TRUST_BOUNDARY.md", "docs/WAIVERS.json"):
            with open(os.path.join(COMP, p), encoding="utf-8") as fh:
                self.assertGreater(len(fh.read()), 400, p)
        w = json.load(open(os.path.join(COMP, "docs", "WAIVERS.json")))
        self.assertTrue(all(e["status"] == "PROPOSED" and e["owner"] == "UNASSIGNED" for e in w["entries"]))

    def test_runbooks_current(self):
        self.assertEqual(open(os.path.join(COMP, "docs", "RUNBOOKS.md"), encoding="utf-8").read(), runbooks.render())

    def test_doc_check_reports_master_md(self):
        fs = doc_check.check()
        self.assertTrue(fs, "the MASTER.md claim must fail the check until the owner resolves it")
        self.assertEqual({f["ref"] for f in fs}, {"MASTER.md"})
        self.assertFalse([f for f in fs if f["file"].startswith("components/")])   # overlay adds no dangling refs


class TestDashboard(unittest.TestCase):
    def test_render_live_and_no_data(self):
        ingest, *_ = make_stack(tmpdir())
        ingest.submit(**signed([sample()]))
        txt = dashboard.render(ingest, HealthModel("5.1.0", lambda: "a" * 64))
        self.assertIn("accepted submissions", txt)
        self.assertRegex(txt, r"accepted submissions\s+1")
        self.assertIn("no data", dashboard.render(ingest, None))


if __name__ == "__main__":
    unittest.main()
