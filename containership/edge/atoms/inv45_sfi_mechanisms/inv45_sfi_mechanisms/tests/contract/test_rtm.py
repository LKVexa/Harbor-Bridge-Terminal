"""RTM, performance gate and release exit gate are themselves tested (C020, C062, C070, C090, C099, C100).

Includes the falsifier: an evidence bundle edited to look complete must still be refused while
owners/approvals are missing, and a synthetic fully-approved bundle must reach GO - proving the gate is
a gate and not a wall.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest

from inv45_sfi_mechanisms.tests.support import PKG_DIR

sys.path.insert(0, str(PKG_DIR / "tools"))
import perf_gate  # noqa: E402
import release  # noqa: E402
import rtm  # noqa: E402


class RtmTest(unittest.TestCase):
    def test_rtm_clean(self):
        self.assertEqual(rtm.check(), [])

    def test_rtm_detects_stale_links(self):
        reg = rtm.load()
        orig = rtm.load
        broken = copy.deepcopy(reg)
        broken["requirements"][45]["symbols"].append("production.sfi:does_not_exist")
        broken["requirements"][46]["tests"].append("tests.unit.test_wasm_parser.NoSuchTest")
        broken["requirements"].pop(0)
        rtm.load = lambda: broken
        try:
            errs = rtm.check()
        finally:
            rtm.load = orig
        self.assertTrue(any("stale symbol" in e for e in errs))
        self.assertTrue(any("does not exist" in e for e in errs))
        self.assertTrue(any("exactly INV-45-C001..C100" in e for e in errs))

    def test_generated_audit_matches_registry(self):
        audit = json.loads((PKG_DIR / "CHECKLIST_AUDIT.json").read_text())
        reg = rtm.load()
        self.assertEqual({i["check_id"]: i["status"] for i in audit["items"]},
                         {r["id"]: r["status"] for r in reg["requirements"]})
        self.assertFalse(audit["certified_for_production"])


class PerfGateTest(unittest.TestCase):
    TH = {"status": "PROPOSED", "absolute": [{"id": "X", "metric": "a.b", "op": "<=", "value": 10}],
          "regression": {"tolerance_ratio": 1.5, "metrics": ["a.c"]}}

    def test_verdicts(self):
        self.assertEqual(perf_gate.evaluate({"a": {"b": 11, "c": 1}}, self.TH, {"a": {"c": 1}})["overall"], "FAIL")
        self.assertEqual(perf_gate.evaluate({"a": {"c": 1}}, self.TH, {"a": {"c": 1}})["overall"], "INCOMPLETE")
        self.assertEqual(perf_gate.evaluate({"a": {"b": 9, "c": 1.4}}, self.TH, {"a": {"c": 1}})["overall"],
                         "PASS_UNDER_PROPOSED_THRESHOLDS")
        self.assertEqual(perf_gate.evaluate({"a": {"b": 9, "c": 1.6}}, self.TH, {"a": {"c": 1}})["overall"], "FAIL")
        approved = dict(self.TH, status="APPROVED")
        self.assertEqual(perf_gate.evaluate({"a": {"b": 9, "c": 1}}, approved, {"a": {"c": 1}})["overall"], "PASS")


class ReleaseGateTest(unittest.TestCase):
    def _complete_evidence(self):
        return {"ci": {"overall": "PASS", "source_tree_sha256": "d", "lanes": {}},
                "manifest_source_tree_sha256": "d", "perf_gate": {"overall": "PASS"},
                "signature": {"trust": "PRODUCTION"}, "pk_core": "present"}

    def test_current_state_is_no_go_with_reasons(self):
        g = release.exit_gate(self._complete_evidence())
        self.assertEqual(g["decision"], "NO_GO")
        text = " ".join(g["reasons"])
        for needle in ("not certified implemented", "waivers pending", "owners"):
            self.assertIn(needle, text)

    def test_edited_evidence_claiming_pass_is_still_refused(self):
        ev = self._complete_evidence()
        ev["ci"]["overall"] = "PASS"
        ev["perf_gate"]["overall"] = "PASS"
        self.assertEqual(release.exit_gate(ev)["decision"], "NO_GO")

    def test_digest_mismatch_and_nonproduction_signature_refused(self):
        ev = self._complete_evidence()
        ev["ci"]["source_tree_sha256"] = "other"
        ev["signature"]["trust"] = "NONPRODUCTION-EPHEMERAL"
        reasons = " ".join(release.exit_gate(ev)["reasons"])
        self.assertIn("different source tree", reasons)
        self.assertIn("production key", reasons)

    def test_synthetic_fully_approved_state_reaches_go(self):
        """Gate, not wall: with every condition synthetically satisfied the decision is GO."""
        orig_reg, orig_w, orig_read = release.json.loads, release.check_waivers, release.Path.read_text
        reg = rtm.load()
        for r in reg["requirements"]:
            r["status"] = "implemented"
        release.check_waivers = lambda: {"pending": 0, "effective": 9, "rows": []}

        def fake_read(self, *a, **k):
            if self.name == "OWNERSHIP.md":
                return "all roles bound to SYNTHETIC-NOT-THE-DELIVERED-OWNERS"
            if self.name == "requirements.json":
                return json.dumps(reg)
            return orig_read(self, *a, **k)
        release.Path.read_text = fake_read
        try:
            self.assertEqual(release.exit_gate(self._complete_evidence())["decision"], "GO")
        finally:
            release.Path.read_text = orig_read
            release.check_waivers = orig_w
            release.json.loads = orig_reg

    def test_waivers_without_approver_are_not_effective(self):
        w = release.check_waivers()
        self.assertEqual(w["effective"], 0)
        self.assertGreater(w["pending"], 0)


if __name__ == "__main__":
    unittest.main()
