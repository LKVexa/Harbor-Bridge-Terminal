"""Component 18 (evidence-gate hardening) and the engine's falsifiers.

Probe 1: a record hand-edited to PASS is REFUSED.
Probe 2: the same record with a SYNTHETIC named owner and a distinct human
reviewer is ACCEPTED -- proving the gate is a gate, not a wall.  The
synthetic identities exist only inside this test; no delivered record
carries them.
"""
import copy
import json
import os
import unittest

COMP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import fixtures  # noqa: F401,E402  (puts the package root on sys.path)
from gap09_unified_observability.components.checklist import engine  # noqa: E402

CHECKLIST = os.path.join(COMP, "checklist", "GAP09_MISSING_COMPONENTS_CHECKLIST.md")


class TestEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.load(open(os.path.join(COMP, "evidence", "CHECKLIST_STATUS.json")))
        cls.ev = json.load(open(os.path.join(COMP, "evidence", "EVIDENCE_INDEX.json")))["items"]

    def test_parse_1440(self):
        p = engine.parse_checklist(CHECKLIST)
        self.assertEqual(len(p["components"]), 60)
        self.assertEqual(sum(len(c["checks"]) for c in p["components"].values()), 1440)
        self.assertEqual(p["sha256"], self.doc["checklist_sha256"])

    def test_delivered_records_valid_and_no_pass(self):
        self.assertEqual(engine.validate(self.doc, self.ev), [])
        self.assertEqual(self.doc["summary"]["PASS"], 0)
        self.assertEqual(self.doc["summary"]["WAIVED"], 0)
        self.assertEqual(self.doc["problems"], [])

    def test_falsifier_pass_without_owner_refused(self):
        d = copy.deepcopy(self.doc)
        r = next(x for x in d["records"] if x["status"] == "VERIFYING")
        r["status"] = "PASS"
        self.assertTrue(any("owner" in e for e in engine.validate(d, self.ev)))
        r["owner"] = "obs-team"; r["reviewer"] = "claude"
        self.assertTrue(any("independent" in e for e in engine.validate(d, self.ev)))
        r["reviewer"] = "obs-team"
        self.assertTrue(any("independent" in e for e in engine.validate(d, self.ev)))

    def test_synthetic_human_approval_accepted(self):
        d = copy.deepcopy(self.doc)
        r = next(x for x in d["records"] if x["status"] == "VERIFYING")
        r.update(status="PASS", owner="SYNTHETIC-owner-not-a-person", reviewer="SYNTHETIC-reviewer-not-a-person")
        self.assertEqual(engine.validate(d, self.ev), [])

    def test_verifying_requires_passing_evidence(self):
        d = copy.deepcopy(self.doc)
        ev = copy.deepcopy(self.ev)
        r = next(x for x in d["records"] if x["status"] == "VERIFYING")
        for e in ev:
            if e["id"] in r["evidence"] and e["kind"] == "test":
                e["result"] = "not_run"
        self.assertTrue(engine.validate(d, ev))

    def test_gate_ledger_chain(self):
        import hashlib
        prev = "0" * 64
        lines = open(os.path.join(COMP, "evidence", "GATE_LEDGER.jsonl")).read().splitlines()
        for ln in lines:
            e = json.loads(ln); h = e.pop("hash")
            self.assertEqual(e["prev"], prev)
            prev = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
            self.assertEqual(prev, h)
        self.assertEqual(open(os.path.join(COMP, "evidence", "GATE_LEDGER.jsonl.head")).read().split(), [str(len(lines)), prev])


if __name__ == "__main__":
    unittest.main()
