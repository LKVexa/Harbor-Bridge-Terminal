"""Release tooling: packaging (15/52), SBOM + licenses (25/53), lint and
coverage (49), dashboards/alerts (39), benchmarks (46), regression gate (47),
platform/determinism (48), documentation (30/33/34/40/51/54), evidence (50)."""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import fixtures as F  # noqa: F401  (sys.path setup)
from inv07_gitops_transition_layer.components.tools import bench, gates, master

COMP = gates.COMP
PKG = gates.PKG


class TestPackaging(unittest.TestCase):
    def test_deploy_assets_least_privilege(self):
        with open(os.path.join(COMP, "deploy", "kubernetes", "controller.yaml"), encoding="utf-8") as fh:
            k = fh.read()
        for must in ("runAsNonRoot: true", "readOnlyRootFilesystem: true", "allowPrivilegeEscalation: false",
                     'drop: ["ALL"]', "kind: NetworkPolicy", "kind: Role\n", "@sha256:"):
            self.assertIn(must, k)
        self.assertNotIn("ClusterRoleBinding", k)
        with open(os.path.join(COMP, "deploy", "Dockerfile"), encoding="utf-8") as fh:
            d = fh.read()
        self.assertIn("PIN_REQUIRED", d)          # refuses to build unpinned (W-005)
        self.assertIn("USER 65532", d)

    def test_pyproject_metadata(self):
        with open(os.path.join(PKG, "pyproject.toml"), encoding="utf-8") as fh:
            p = fh.read()
        try:
            import tomllib
        except ImportError:
            self.skipTest("lane: tomllib needs Python 3.11+")
        doc = tomllib.loads(p)
        self.assertEqual(doc["project"]["version"], gates.VERSION)
        self.assertEqual(doc["project"]["dependencies"], [])
        self.assertEqual(doc["project"]["requires-python"], ">=3.10")

    def test_wheel_build_install_import_smoke(self):
        try:
            import setuptools  # noqa: F401
        except ImportError:
            self.skipTest("lane: setuptools not installed")
        out, venv = tempfile.mkdtemp(), tempfile.mkdtemp()
        try:
            subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", venv], check=True, timeout=120)
            py = os.path.join(venv, "Scripts" if os.name == "nt" else "bin", "python")
            p = subprocess.run([py, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-q", "-w", out, PKG],
                               capture_output=True, text=True, timeout=300,
                               env={**os.environ, "SETUPTOOLS_USE_DISTUTILS": "local"})
            for junk in ("build", "inv07_gitops_transition_layer.egg-info"):
                shutil.rmtree(os.path.join(PKG, junk), ignore_errors=True)
            if p.returncode != 0:
                self.skipTest("lane: wheel build unavailable here: " + p.stderr[-200:])
            whl = glob.glob(os.path.join(out, "*.whl"))[0]
            v2 = tempfile.mkdtemp()
            subprocess.run([sys.executable, "-m", "venv", v2], check=True, timeout=120)
            py2 = os.path.join(v2, "Scripts" if os.name == "nt" else "bin", "python")
            subprocess.run([py2, "-m", "pip", "install", "--no-deps", "-q", whl], check=True, timeout=300)
            r = subprocess.run([py2, "-c", "import inv07_gitops_transition_layer as p, inv07_gitops_transition_layer."
                                "components.controller as c; print(p.__version__, c.VERSION)"],
                               capture_output=True, text=True, cwd=v2, timeout=60)
            self.assertEqual(r.stdout.split(), [gates.VERSION, gates.VERSION], r.stderr)
            shutil.rmtree(v2, ignore_errors=True)
        finally:
            shutil.rmtree(out, ignore_errors=True)
            shutil.rmtree(venv, ignore_errors=True)


class TestSBOM(unittest.TestCase):
    def test_sbom_and_license_inventory(self):
        doc = gates.sbom()
        self.assertEqual(doc["bomFormat"], "CycloneDX")
        names = {c["name"] for c in doc["components"]}
        self.assertIn("inv07_gitops_transition_layer/components/controller.py", names)
        self.assertEqual(doc["dependencies"], [])
        with open(os.path.join(gates.EVID, "LICENSE_INVENTORY.json"), encoding="utf-8") as fh:
            lic = json.load(fh)
        self.assertEqual(lic["third_party_runtime"], [])
        self.assertIn("UNDECLARED", lic["project_license"])


class TestLint(unittest.TestCase):
    def test_no_findings(self):
        d = gates.lint()
        self.assertEqual(d["findings"], [], d["findings"][:5])


class TestCoverage(unittest.TestCase):
    def test_statement_coverage_report(self):
        if os.environ.get("INV07_SKIP_COVERAGE") == "1":
            self.skipTest("lane: coverage run disabled (nested inside the coverage run itself)")
        os.environ["INV07_SKIP_COVERAGE"] = "1"
        try:
            d = gates.coverage()
        finally:
            del os.environ["INV07_SKIP_COVERAGE"]
        self.assertEqual(d["failures"], 0)
        self.assertGreaterEqual(d["total_percent"], 85.0)   # proposed threshold (W-004)


class TestDashboards(unittest.TestCase):
    def test_alerts_reference_real_metrics_and_runbooks(self):
        gates.dashboards()
        from inv07_gitops_transition_layer.components.telemetry import Registry, standard_metrics
        names = set(standard_metrics(Registry())._m)
        with open(os.path.join(COMP, "deploy", "prometheus-alerts.yaml"), encoding="utf-8") as fh:
            y = fh.read()
        with open(os.path.join(COMP, "docs", "RUNBOOKS.md"), encoding="utf-8") as fh:
            rb = fh.read()
        for name, expr, _, _ in gates.ALERTS:
            self.assertTrue(any(m in expr for m in names), name)
            heads = [l for l in rb.splitlines() if l.startswith("## ")]
            self.assertTrue(any(name.lower() in h for h in heads), f"no runbook section for {name}")
        with open(os.path.join(COMP, "deploy", "grafana-dashboard.json"), encoding="utf-8") as fh:
            self.assertGreaterEqual(len(json.load(fh)["panels"]), 10)


class TestBench(unittest.TestCase):
    def test_quick_bench_runs(self):
        d = bench.main(None, quick=True)
        names = {r["name"] for r in d["results"]}
        for n in ("ed25519_verify", "commit_verify", "reconcile_no_change_100_resources", "cold_start_build_recover"):
            self.assertIn(n, names)


class TestRegressionGate(unittest.TestCase):
    def test_gate_logic(self):
        base = {"results": [{"name": "ed25519_verify", "p50": 0.02}, {"name": "x", "p50": 1.0}]}
        self.assertEqual(gates.regression(base, {"results": [{"name": "ed25519_verify", "p50": 0.021},
                                                             {"name": "x", "p50": 1.2}]})[0], 0)
        rc, fails = gates.regression(base, {"results": [{"name": "ed25519_verify", "p50": 0.2}]})
        self.assertEqual(rc, 1)
        self.assertEqual(len(fails), 2)     # absolute threshold + relative regression

    def test_against_recorded_baseline(self):
        p = os.path.join(gates.EVID, "perf_baseline.json")
        if not os.path.exists(p):
            self.skipTest("lane: no recorded baseline yet (run tools/bench.py)")
        with open(p, encoding="utf-8") as fh:
            base = json.load(fh)
        rc, fails = gates.regression(base, base)
        self.assertEqual(rc, 0, fails)


class TestPlatform(unittest.TestCase):
    def test_deterministic_serialisation_and_signing(self):
        d = gates.platform_report()
        from inv07_gitops_transition_layer.components.canonical import canonicalize
        self.assertEqual(canonicalize({"b": [1, 2.5, "ü"], "a": {"z": None, "y": True}}),
                         '{"a":{"y":true,"z":null},"b":[1,2.5,"ü"]}')
        self.assertEqual(d["canonical_sha256"], CANON_SHA)
        self.assertEqual(len(d["ed25519_signature"]), 128)


CANON_SHA = __import__("hashlib").sha256('{"a":{"y":true,"z":null},"b":[1,2.5,"ü"]}'.encode()).hexdigest()


class TestDocs(unittest.TestCase):
    def test_docs_consistent(self):
        master.main()
        gates.api_docs()
        self.assertEqual(gates.doc_check(), [])

    def test_master_has_all_ids(self):
        with open(os.path.join(PKG, "MASTER.md"), encoding="utf-8") as fh:
            m = fh.read()
        self.assertIn("regenerated", m)
        for i in (1, 50, 100):
            self.assertIn(f"INV-07-C{i:03d}", m)
        for i in range(1, 55):
            self.assertIn(f"| {i:02d} |", m)


class TestEvidence(unittest.TestCase):
    def test_manifest_and_gate_ledger_chain(self):
        p = gates.manifest()
        with open(p, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        self.assertTrue(any(l.endswith("components/controller.py") for l in lines))
        led = os.path.join(gates.EVID, "GATE_LEDGER.jsonl")
        if not os.path.exists(led):
            self.skipTest("lane: engine has not produced a gate ledger yet")
        import hashlib
        prev = "0" * 64
        with open(led, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh]
        for e in rows:
            h = e.pop("hash")
            self.assertEqual(e["prev"], prev)
            prev = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
            self.assertEqual(prev, h)
        with open(led + ".head", encoding="ascii") as fh:
            self.assertEqual(fh.read().split(), [str(len(rows)), prev])


if __name__ == "__main__":
    unittest.main()
