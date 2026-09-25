"""Tests for P2 tooling: MC-47 bench, MC-48 gate, MC-51 runbooks, MC-52 build, MC-53 pk_core contract."""
import hashlib, json, os, pathlib, re, sys, tempfile, unittest
PKG = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(PKG.parent))
from gap02_hardware_capability_discovery.tools import bench, build, release_gate
from gap02_hardware_capability_discovery.production.errors import RUNBOOK


class TestTools_MC47(unittest.TestCase):
    def test_bench(self):
        r = bench.run(5); self.assertEqual(r["iterations"], 5); self.assertTrue(r["slo_met"])


class TestTools_MC48(unittest.TestCase):
    def test_gate_fails_closed(self):
        r = release_gate.run(skip_tests=True)
        self.assertEqual(r["verdict"], "NO_GO")  # MASTER.md absent, components incomplete, tests skipped
        ids = {c["id"]: c["result"] for c in r["checks"]}
        self.assertEqual(ids["present:MASTER.md"], "FAIL")   # MC-54 CI presence check
        self.assertEqual(ids["unit-tests"], "NOT_RUN")


class TestTools_MC51(unittest.TestCase):
    def test_every_code_has_runbook_anchor(self):
        text = (PKG / "RUNBOOKS.md").read_text()
        anchors = set(re.findall(r"^## (\S+)", text, re.M))
        for code, link in RUNBOOK.items():
            self.assertIn(link.split("#")[1], anchors, code)
        for r in json.load(open(PKG / "ops" / "alerts.json"))["rules"]:
            self.assertIn(r["runbook"].split("#")[1], anchors)


class TestTools_MC52(unittest.TestCase):
    def test_reproducible(self):
        d = tempfile.mkdtemp()
        a = build.build(os.path.join(d, "a.zip")); b = build.build(os.path.join(d, "b.zip"))
        self.assertEqual(a, b)
        sb = json.load(open(PKG / "SBOM.cdx.json")); self.assertEqual(sb["bomFormat"], "CycloneDX")


class TestTools_MC53(unittest.TestCase):
    def test_contract_matches_package(self):
        c = json.load(open(PKG / "PK_CORE_CONTRACT.json"))
        src = (PKG / "contract.py").read_text()
        for api in c["required_api"]:
            self.assertIn(api.rsplit(".", 1)[1], src)
        import gap02_hardware_capability_discovery as g
        self.assertIsInstance(g.PK_CORE_AVAILABLE, bool)


if __name__ == "__main__":
    unittest.main()
