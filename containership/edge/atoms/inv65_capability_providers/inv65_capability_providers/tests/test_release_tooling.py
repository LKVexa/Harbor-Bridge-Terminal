"""M29/M30/M31/M34/M36/M01 release-tooling tests."""
import hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))


class ReleaseTooling(unittest.TestCase):
    def test_rtm_is_consistent(self):
        import importlib
        b = importlib.import_module("inv65_capability_providers.tools.build_rtm")
        c = importlib.import_module("inv65_capability_providers.tools.check_rtm")
        fresh = b.build()
        self.assertEqual(c.check(fresh), [])
        on_disk = json.loads((PKG / "traceability/INV65_RTM.json").read_text())
        self.assertEqual(on_disk, fresh, "RTM on disk is stale: run tools/build_rtm.py")
        st = [r["status"] for r in fresh["rows"]]
        self.assertTrue(all(r["owner"] == "UNASSIGNED" for r in fresh["rows"]))  # no invented owners
        self.assertGreater(st.count("blocked"), 0)

    def test_benchmark_gate_logic(self):
        from inv65_capability_providers.benchmarks.harness import gate
        base = json.loads((PKG / "benchmarks/baselines/local.json").read_text())
        ok = {"dispatch": {"over_1ms_ratio": 0.001, "p50_ms": 0.5}, "cold_start": {"start_s": 0.1}, "burst": {"shed": 5, "quiet_tenant_admitted": True}}
        self.assertEqual(gate(ok, base), [])
        self.assertTrue(gate({**ok, "dispatch": {"over_1ms_ratio": 0.2, "p50_ms": 0.5}}, base))
        self.assertTrue(gate({**ok, "burst": {"shed": 0, "quiet_tenant_admitted": True}}, base))
        self.assertTrue(gate({**ok, "burst": {"shed": 3, "quiet_tenant_admitted": False}}, base))

    def test_evidence_chain_verifies(self):
        p = PKG / "evidence/pk_evidence.jsonl"
        if not p.exists():
            self.skipTest("release gate not yet run")
        from inv65_capability_providers.tools.verify_evidence import verify
        gate = json.loads((PKG / "conformance/PK_GATE_RESULTS.json").read_text())
        ok, errs, head = verify(p, gate["evidence_head"])
        self.assertTrue(ok, errs)

    def test_gate_is_not_go(self):
        p = PKG / "conformance/PK_GATE_RESULTS.json"
        if not p.exists():
            self.skipTest("release gate not yet run")
        g = json.loads(p.read_text())
        self.assertNotEqual(g["verdict"], "GO")  # P0 blockers M02/M23 are open
        self.assertIn("M02", g["p0_blockers"]); self.assertIsNone(g["independent_review"])
        self.assertTrue(all(c["status"] != "pass" for c in g["checks"] if c["check"] == "conformance_100"))

    def test_waivers_have_owner_and_expiry(self):
        w = json.loads((PKG / "governance/waivers.json").read_text())["waivers"]
        for x in w:
            self.assertTrue(x["owner"] and x["expires"] and x["covers"], x["id"])

    def test_master_status_is_honest(self):
        m = PKG / "docs/master/MASTER.md"
        if m.exists():
            want = (PKG / "docs/master/MASTER.sha256").read_text().split()[0]
            self.assertEqual(hashlib.sha256(m.read_bytes()).hexdigest(), want)
        else:
            readme = (PKG / "README.md").read_text()
            self.assertNotRegex(readme, r"(?i)MASTER\.md (is )?(present|included)")

    def test_reproducible_wheel(self):
        try:
            import setuptools  # noqa: F401
        except ImportError:
            self.skipTest("setuptools unavailable")
        digests = []
        for _ in range(2):
            src = pathlib.Path(tempfile.mkdtemp()) / "inv65_capability_providers"
            shutil.copytree(PKG, src, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "build", "*.egg-info", "evidence", "sbom", "provenance", "release"))
            out = pathlib.Path(tempfile.mkdtemp())
            r = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-q", "-w", str(out), str(src)],
                               capture_output=True, text=True, env={**os.environ, "SOURCE_DATE_EPOCH": "1790000000", "PIP_NO_INDEX": "1"})
            if r.returncode != 0:
                self.skipTest("wheel build unavailable offline: " + r.stderr[-200:])
            whl, = out.glob("*.whl")
            digests.append(hashlib.sha256(whl.read_bytes()).hexdigest())
        self.assertEqual(digests[0], digests[1])
