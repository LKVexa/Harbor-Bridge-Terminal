"""Falsifiers for the checklist engine: it must refuse PASS without a named
owner and an independent human reviewer, refuse WAIVED, refuse VERIFYING
without passing test evidence, and keep A02/G02 BLOCKED."""
from __future__ import annotations

import copy
import unittest

import fixtures  # noqa: F401
from inv07_gitops_transition_layer.components.checklist import engine
from inv07_gitops_transition_layer.components.checklist.bindings import C


def _fake_tests(result="pass"):
    outcomes = {}
    for b in C.values():
        for t in b["tests"]:
            outcomes[t + ".test_x"] = (result, "")
    return {"outcomes": outcomes, "seconds": 0, "ran": len(outcomes)}


class TestEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = tempfile.mkdtemp()
        cls.doc = engine.build(cls.tmp, tests=_fake_tests())
        import json, os
        with open(os.path.join(cls.tmp, "EVIDENCE_INDEX.json")) as fh:
            cls.ev = json.load(fh)["items"]

    def test_counts_and_no_pass(self):
        self.assertEqual(self.doc["checks"], 54 * 40)
        self.assertEqual(self.doc["summary"]["PASS"], 0)
        self.assertEqual(self.doc["summary"]["WAIVED"], 0)
        self.assertEqual(self.doc["problems"], [])

    def test_falsifiers(self):
        d = copy.deepcopy(self.doc)
        r = d["records"][0]
        r["status"] = "PASS"
        self.assertTrue(any("named owner" in e for e in engine.validate(d, self.ev)))
        r["owner"], r["reviewer"] = "alice", "Claude"
        self.assertTrue(any("independent human reviewer" in e for e in engine.validate(d, self.ev)))
        r["reviewer"] = "alice"
        self.assertTrue(any("independent human reviewer" in e for e in engine.validate(d, self.ev)))
        r["status"] = "WAIVED"
        self.assertTrue(any("WAIVED" in e for e in engine.validate(d, self.ev)))
        a02 = next(x for x in d["records"] if x["family"] == "A02")
        a02["status"] = "VERIFYING"
        self.assertTrue(any("owner/review" in e for e in engine.validate(d, self.ev)))

    def test_skips_and_failures_never_verify(self):
        for res in ("not_run", "fail"):
            doc = engine.build(self.tmp, tests=_fake_tests(res))
            self.assertEqual(doc["summary"]["VERIFYING"], 0, res)

    def test_verifying_requires_test_evidence(self):
        d = copy.deepcopy(self.doc)
        ev = [dict(e, result="not_run") if e["kind"] == "test" else e for e in self.ev]
        self.assertTrue(any("VERIFYING without passing" in e for e in engine.validate(d, ev)))


if __name__ == "__main__":
    unittest.main()
