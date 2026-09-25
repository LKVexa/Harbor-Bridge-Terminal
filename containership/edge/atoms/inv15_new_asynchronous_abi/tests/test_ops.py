"""Components 46, 53, 62, 65-72: release metadata, CI, rollback hook, docs."""
import ast
import json
import pathlib
import subprocess
import sys
import unittest

from _util import ROOT, mk

sys.path.insert(0, str(ROOT / "ops"))
import rollback_hook  # noqa: E402


class TestRollbackHook(unittest.TestCase):
    def _prom(self, foreign=0, refusals=0):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        for _ in range(20):
            v.cancel(v.call()[1])
        if foreign:
            from inv15_new_asynchronous_abi import handles as H
            try:
                v.wait([H.Handle(1, 999, 0, bytes(16))])
            except Exception:
                pass
        return h.metrics.render_prometheus()

    def test_verdicts(self):
        base = self._prom()
        self.assertEqual(rollback_hook.evaluate(base, self._prom())[0], "PROCEED")
        self.assertEqual(rollback_hook.evaluate(base, self._prom(foreign=1))[0], "ROLLBACK")
        self.assertEqual(rollback_hook.evaluate(base, "")[0], "INCOMPLETE")


class TestBench(unittest.TestCase):
    def test_bench_runs_and_reports_all_ops(self):
        import os
        import tempfile
        out = os.path.join(tempfile.mkdtemp(), "b.json")
        env = dict(os.environ, INV15_BENCH_N="800", INV15_BENCH_OUT=out, PYTHONDONTWRITEBYTECODE="1")
        subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "bench.py")], check=True, env=env, capture_output=True)
        rep = json.loads(open(out).read())
        self.assertEqual(set(rep["latency_ns"]), {"call", "complete", "wait", "take", "cancel", "teardown"})
        for v in rep["latency_ns"].values():
            self.assertTrue(v["p50"] <= v["p95"] <= v["p99"] <= v["max"])
        baseline = json.loads((ROOT / "certification" / "BENCHMARK_BASELINE.json").read_text())
        self.assertIn("environment", baseline)


class TestRelease(unittest.TestCase):
    def test_stdlib_only(self):
        std = set(sys.stdlib_module_names)
        for p in ROOT.rglob("*.py"):
            for node in ast.walk(ast.parse(p.read_text())):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module]
                else:
                    continue
                for n in names:
                    top = n.split(".")[0]
                    self.assertTrue(top in std or top in ("inv15_new_asynchronous_abi", "pk_core", "_util", "rollback_hook"),
                                    f"{p.name}: third-party import {n}")

    def test_provenance_is_honestly_unsigned(self):
        prov = json.loads((ROOT / "certification" / "provenance.json").read_text())
        self.assertIsNone(prov["signature"])
        self.assertIn("UNSIGNED", prov["status"])

    def test_artifacts_present(self):
        for rel in ("pyproject.toml", "ci.sh", "ops/alerts.rules.yaml", "ops/dashboard.json", "docs/SPEC.md",
                    "docs/THREAT_MODEL.md", "docs/OPERATIONS.md", "docs/COMPATIBILITY.md", "docs/LIFECYCLE_POLICY.md",
                    "docs/REDACTION_POLICY.md", "docs/RETRY_CONTRACT.md", "docs/MEMORY_MODEL.md",
                    "docs/TELEMETRY_POLICY.md", "idl/pk_async.wit", "conformance/vectors.json"):
            self.assertTrue((ROOT / rel).is_file(), rel)
        dash = json.loads((ROOT / "ops" / "dashboard.json").read_text())
        exprs = " ".join(t["expr"] for p in dash["panels"] for t in p["targets"])
        text = (ROOT / "ops" / "alerts.rules.yaml").read_text()
        emitted = set()
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        v.cancel(v.call()[1])
        h.refresh_gauges()
        for line in h.metrics.render_prometheus().splitlines():
            emitted.add(line.split("{")[0].split(" ")[0].replace("_bucket", "").replace("_count", "").replace("_sum", ""))
        import re
        referenced = set(re.findall(r"pk_async_[a-z_]+", exprs + text))
        referenced = {r.replace("_bucket", "").replace("_count", "") for r in referenced}
        undefined = {r for r in referenced if r not in emitted and r + "_total" not in emitted}
        undefined -= {"pk_async_foreign_handle_total", "pk_async_late_completions_total",
                      "pk_async_memory_refusals_total", "pk_async_memory_soft_limit_total", "pk_async_refusals_total"}  # emitted on first occurrence
        self.assertEqual(undefined, set(), "dashboard/alerts reference metrics the host never emits")

    def test_spec_references_real_tests(self):
        import re
        spec = (ROOT / "docs" / "SPEC.md").read_text()
        names = set(re.findall(r"\b(test_[a-z_0-9]+|Test[A-Za-z]+)\b", spec))
        corpus = "".join(p.read_text() for p in (ROOT / "tests").glob("test_*.py"))
        missing = {n for n in names if n not in corpus and n not in ("test_host", "test_wire", "test_adapters", "test_certification", "test_security_telemetry")}
        self.assertEqual(missing, set())


if __name__ == "__main__":
    unittest.main()
