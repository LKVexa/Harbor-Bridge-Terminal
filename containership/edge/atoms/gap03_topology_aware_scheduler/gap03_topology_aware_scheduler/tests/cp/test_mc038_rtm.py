import json
import os
import shutil
import tempfile
import unittest

from gap03_topology_aware_scheduler.certification import run_checklist as rc
from gap03_topology_aware_scheduler.tests.cp._util import covers

CHECKLIST = os.path.join(rc.PKG, "docs", "GAP03_v4.2.0_Missing_Components_Professional_Checklist.md")


class RTM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parsed = rc.parse(CHECKLIST)

    @covers("MC-038", 6, 7, 25)
    def test_mc038_parser_assigns_stable_ids(self):
        """requirement IDs: every one of the 46 x 30 checks gets its stable checklist ID with priority, category and
        source text; PG-001..010, 184 definition-of-done items and 6 final exit items are parsed."""
        p = self.parsed
        self.assertEqual(len(p["checks"]), 1380)
        self.assertEqual(len({c["id"] for c in p["checks"]}), 1380)
        self.assertEqual([g["id"] for g in p["pg"]], [f"PG-{i:03d}" for i in range(1, 11)])
        self.assertEqual(len(p["dod"]), 184)
        self.assertEqual(len(p["final"]), 6)
        self.assertEqual({m["priority"] for m in p["mcs"].values()}, {"P0", "P1", "P2"})

    @covers("MC-038", 8, 9, 10, 11, 12, 25, 26)
    def test_mc038_rtm_bidirectional_and_ci_validation(self):
        """integration/contract against the real checklist schema and real component specs - traceability: synthetic outcomes produce rows mapping requirement -> modules -> tests -> evidence, the
        reverse index maps tests -> requirements, statuses distinguish verified/blocked/failed/weak/unbound, and a
        failing bound test turns its check FAILED (no silent pass)."""
        chk = [c for c in self.parsed["checks"] if c["mc"] == "MC-001"]
        parsed = dict(self.parsed, checks=chk)
        tr = {"outcomes": {"test_mc001_parser_rejects_malformed_and_adversarial": "fail"},
              "covers": {"MC-001-CHK-009": ["test_mc001_parser_rejects_malformed_and_adversarial"]},
              "sources": {"test_mc001_parser_rejects_malformed_and_adversarial": "parsers reject malformed duplicate payloads"}}
        rows = {r["id"]: r for r in rc.evaluate(parsed, tr)}
        self.assertEqual(rows["MC-001-CHK-009"]["status"], "FAILED")
        self.assertEqual(rows["MC-001-CHK-002"]["status"], "BLOCKED")
        self.assertEqual(rows["MC-001-CHK-010"]["status"], "UNBOUND")
        self.assertIn("controlplane/wire.py", rows["MC-001-CHK-009"]["modules"])
        self.assertTrue(set(r["status"] for r in rows.values()) <= set(rc.STATUSES))

    @covers("MC-038", 13, 14, 15, 27)
    def test_mc038_broken_reference_fails_ci_run(self):
        """CI validation (adversarial): a binding naming a non-existent check, an invariant naming a missing test, a
        FAILED check, or (in --ci mode) any UNBOUND/WEAK row makes the runner exit non-zero; the RTM document is
        versioned with the package version; unexplained gaps block while explained BLOCKED rows stay visible."""
        from gap03_topology_aware_scheduler import __version__
        rows = [{"id": "MC-001-CHK-001", "tests": ["test_mc001_a"], "status": "LOCALLY_VERIFIED", "mc": "MC-001", "priority": "P0",
                 "category": "c", "modules": [], "artifacts": [], "blockers": []}]
        tr = {"covers": {"MC-999-CHK-001": ["test_mc001_a"]}, "outcomes": {"test_mc001_a": "pass"}}
        v = rc.rtm_validation(rows, tr)
        self.assertEqual(v["broken_refs"], ["MC-999-CHK-001"])
        self.assertIn("test_mc001_parser_rejects_malformed_and_adversarial", v["missing_invariant_tests"])
        self.assertEqual(rc.ci_exit({"FAILED": 0}, v, ci=False), 1)
        ok = {"broken_refs": [], "missing_invariant_tests": [], "orphan_tests": []}
        self.assertEqual(rc.ci_exit({"BLOCKED": 5}, ok, ci=True), 0)
        self.assertEqual(rc.ci_exit({"UNBOUND": 1}, ok, ci=True), 1)
        self.assertEqual(rc.ci_exit({"UNBOUND": 1}, ok, ci=False), 0)
        self.assertEqual(rc.ci_exit({"FAILED": 1}, ok, ci=False), 1)
        doc = rc.rtm_doc(rows, tr)
        self.assertEqual(doc["version"], __version__)
        self.assertEqual(doc["reverse"]["test_mc001_a"], ["MC-001-CHK-001"])

    @covers("MC-038", 29)
    def test_mc038_weak_binding_guard(self):
        """relevance guard: a binding that shares no content word with its check is reported WEAK, never VERIFIED."""
        chk = [c for c in self.parsed["checks"] if c["id"] == "MC-001-CHK-009"]
        tr = {"outcomes": {"test_x": "pass"}, "covers": {"MC-001-CHK-009": ["test_x"]}, "sources": {"test_x": "def test_x(): pass"}}
        rows = rc.evaluate(dict(self.parsed, checks=chk), tr)
        self.assertEqual(rows[0]["status"], "WEAK_BINDING")
