"""M52 gate tests: missing/stale/failed evidence must never produce GO."""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from inv09_portable_compute_isa.prod import gate  # noqa: E402
from inv09_portable_compute_isa.prod.waivers import Waiver  # noqa: E402

REL = "sha256:" + "a" * 64
GOOD = {
    "tests": {"runs": [{"returncode": 0, "summary": ["OK"]}, {"returncode": 0, "summary": ["OK"]}]},
    "fuzz_campaign": {"crashes": 0, "nondeterministic": 0, "executions": 10,
                      "differential": {"total": 10, "critical": 0, "disagreements": {}}},
    "perf_gate": {"verdict": "PASS", "breaches": []}, "benchmark": {}, "soak": {"health": "ready", "validations": 1},
    "static_scan": {"high": 0}, "sbom.cdx": {}, "build_metadata": {}, "coverage": {},
}


def make(root: pathlib.Path, docs: dict, release=REL, owners="element: INV-09\nowner: alice\n"):
    (root / "evidence").mkdir()
    for k, v in docs.items():
        (root / "evidence" / f"{k}.json").write_text(json.dumps(dict(v, release_digest=release)))
    (root / "OWNERS.yaml").write_text(owners)


class GateTest(unittest.TestCase):
    def run_gate(self, docs, items=(), waivers=(), release=REL, owners="owner: alice\n"):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            make(root, docs, release, owners)
            return gate.evaluate(root, REL, list(items), list(waivers), dt.date(2026, 9, 22))

    def test_only_two_reference_rule_blocks_go(self):
        r = self.run_gate(GOOD)
        self.assertEqual(r["verdict"], "NO_GO")  # single differential reference + fleet soak are standing blockers
        self.assertIn("differential:two-references", r["blocking"]["controls"])

    def test_each_missing_evidence_blocks(self):
        for k in GOOD:
            docs = {x: v for x, v in GOOD.items() if x != k}
            r = self.run_gate(docs)
            self.assertIn(f"evidence:{k}", r["blocking"]["controls"], k)

    def test_stale_evidence_blocks(self):
        r = self.run_gate(GOOD, release="sha256:" + "b" * 64)
        self.assertTrue(all(c.startswith("evidence:") or c.startswith(("differential", "soak", "governance"))
                            for c in r["blocking"]["controls"]))
        self.assertIn("evidence:tests", r["blocking"]["controls"])

    def test_failures_and_owners(self):
        bad = dict(GOOD, perf_gate={"verdict": "FAIL", "breaches": [1]})
        self.assertIn("perf:M30", self.run_gate(bad)["blocking"]["controls"])
        self.assertIn("governance:owners(M50)", self.run_gate(GOOD, owners="owner: TBD")["blocking"]["controls"])

    def test_waivers(self):
        items = [{"id": "M29-043", "status": "PARTIAL"}]
        w = Waiver("W1", ("M29-043",), "4.3.0", "a", "b", "cache", dt.date(2026, 12, 31), "r")
        r = self.run_gate(GOOD, items, [w])
        self.assertEqual(r["counts"], {"WAIVED": 1})
        expired = Waiver("W2", ("M29-043",), "4.3.0", "a", "b", "cache", dt.date(2026, 1, 1), "r")
        r = self.run_gate(GOOD, items, [expired])
        self.assertEqual(r["counts"], {"PARTIAL": 1})

    def test_deterministic(self):
        self.assertEqual(self.run_gate(GOOD)["controls"], self.run_gate(GOOD)["controls"])


if __name__ == "__main__":
    unittest.main()
