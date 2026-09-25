"""GAP02-MC-43 — contract conformance fixtures run through the real agent wiring."""
import json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from gap02_hardware_capability_discovery.production.agent import build_probes
from gap02_hardware_capability_discovery.production.config import ProbeConfig
from gap02_hardware_capability_discovery.production.evidence import Host, promote

CASES = json.load(open(pathlib.Path(__file__).resolve().parents[1] / "conformance" / "cases.json"))


class TestConformance_MC43(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(CASES["schema"], "GAP02_CONFORMANCE/1")
        for c in CASES["cases"]:
            with self.subTest(c["id"]):
                h = Host(files=c["files"], commands={}, system=c["system"], machine=c["machine"])
                fn, _ = build_probes(ProbeConfig(), h)[c["probe"]]
                got = {e.capability: promote(e) for e in fn()}
                for cap, want in c["expect"].items():
                    self.assertEqual(got.get(cap, "unprobed"), want, f"{c['id']} {cap}")


if __name__ == "__main__":
    unittest.main()
