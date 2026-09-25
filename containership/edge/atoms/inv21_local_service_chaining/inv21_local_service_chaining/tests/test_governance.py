"""GAP-015/017/021/036/037 governance artefacts are present, parseable and consistent."""
import json, pathlib, unittest
import _support  # noqa: F401
from inv21_local_service_chaining.tools import traceability as T

PKG = pathlib.Path(__file__).resolve().parents[1]


class GovernanceTest(unittest.TestCase):
    def test_traceability_covers_all_items_and_gaps(self):
        t = T.build()
        self.assertEqual(len(t["items"]), 100)
        self.assertEqual([g["id"] for g in t["gaps"]], [f"GAP-{i:03d}" for i in range(1, 43)])
        self.assertEqual(t["unmapped"], [])
        self.assertEqual(t["summary_checklist"]["verified"], 0)  # nothing self-certified

    def test_blocked_gaps_are_named(self):
        for g in T.build()["gaps"]:
            if g["status"] in ("blocked", "partial"):
                self.assertTrue(g["residual"], g["id"])

    def test_waivers_have_owner_and_approval_flag(self):
        w = json.loads((PKG / "governance/waivers.json").read_text())["entries"]
        for e in w:
            self.assertTrue(e["owner"]); self.assertIn("approved", e)

    def test_alert_rules_reference_exported_metrics(self):
        import re
        rules = (PKG / "ops/alerts.yaml").read_text()
        names = set(re.findall(r"inv21_[a-z_]+", rules))
        from _support import build, ctx
        ch, res, prov, v = build(grants=[("acme", "s", "invoke")])
        res.place("s", "acme", lambda hop, r: 1, abi="hop")
        ch.invoke("s", 0, ctx(v))
        try:
            ch.invoke("x", 0, ctx(v))
        except Exception:
            pass
        exported = ch.export_metrics()
        base = {n.rsplit("_bucket", 1)[0] for n in names}
        missing = [n for n in base if n not in exported and not n.endswith(("_total",)) and "remote_failures" not in n
                   and "handler_stalls" not in n]
        self.assertEqual(missing, [])
        json.loads((PKG / "ops/dashboard.grafana.json").read_text())

    def test_gate_tool_refuses_skip_opt_out(self):
        src = (PKG / "tools/release_gate.py").read_text()
        self.assertIn('k != "INV21_ALLOW_PK_CORE_SKIP"', src)
        self.assertIn('t["skipped"] == 0', src)


class BenchSmokeTest(unittest.TestCase):
    def test_bench_harness_runs(self):
        # subprocess: test_runtime.py (the unchanged 4.2 suite) stubs the package in sys.modules
        import subprocess, sys
        r = subprocess.run([sys.executable, "-B", "-m", "inv21_local_service_chaining.tools.bench", "--n", "60"],
                           cwd=str(PKG.parent), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        rep = json.loads(r.stdout)
        self.assertEqual(rep["schema"], "INV21_BENCH/1")
        self.assertTrue(rep["results"]["serialization"]["local_path_passes_same_object"])


if __name__ == "__main__":
    unittest.main()
