"""Evidence ledger, waiver register and machine-derived gate (MC040, MC041,
MC100, MC101, MC103) - including the negative acceptance cases the checklist
requires: absent, corrupt, stale and waived-P0 inputs never yield GO."""
import datetime as dt
import json
import pathlib
import tempfile
import unittest

import _fixtures as F  # noqa: F401  (path setup)
from inv29_hybrid_wasm_unikernel import evidence as E

PKG = pathlib.Path(__file__).resolve().parents[1]
TODAY = dt.date(2026, 9, 23)
OK_TESTS = {"passed": 10, "failed": 0, "errors": 0, "certification_critical_skips": 0}


def status(*items):
    return {"components": [{"id": i, "priority": p, "status": s} for i, p, s in items]}


def waiver(comp, **kw):
    w = {"id": "W-1", "component": comp, "requirements": ["INV-29-C070"], "rationale": "r", "risk": "low",
         "compensating_controls": ["c"], "owner": "o", "approvers": ["a"], "created": "2026-09-01",
         "expires": "2026-12-31", "remediation": "ISSUE-1", "status": "approved",
         "applies_to_version": "4.3.0", "applies_to_environment": "production"}
    w.update(kw)
    return w


def gate(st, **kw):
    kw.setdefault("tests", OK_TESTS)
    kw.setdefault("manifest", {"source_digest": "sha256:" + "a" * 64})
    kw.setdefault("source_digest", "sha256:" + "a" * 64)
    return E.derive_gate(st, today=TODAY, version="4.3.0", **kw)


class GateTest(unittest.TestCase):
    def test_all_closed_is_go(self):
        self.assertEqual(gate(status(("MC1", "P0", "CLOSED"), ("MC2", "P2", "NOT_APPLICABLE")))["verdict"], "GO")

    def test_open_p0_is_no_go_and_cannot_be_waived(self):
        st = status(("MC1", "P0", "IMPLEMENTED_LOCAL"))
        self.assertEqual(gate(st)["verdict"], "NO_GO")
        with self.assertRaises(E.EvidenceInvalid):
            gate(st, waivers=[waiver("MC1")])

    def test_p1_p2_waivers(self):
        st = status(("MC1", "P0", "CLOSED"), ("MC2", "P1", "OWNER_ACTION"), ("MC3", "P2", "BLOCKED_EXTERNAL"))
        self.assertEqual(gate(st)["verdict"], "NO_GO")
        g = gate(st, waivers=[waiver("MC2"), waiver("MC3", id="W-2")])
        self.assertEqual(g["verdict"], "CONDITIONAL_GO")
        self.assertEqual(len(g["conditions"]), 2)

    def test_expired_wrong_version_unapproved_waivers_ignored(self):
        st = status(("MC1", "P0", "CLOSED"), ("MC2", "P1", "OWNER_ACTION"))
        for w in (waiver("MC2", expires="2026-09-01"), waiver("MC2", applies_to_version="4.2.0"),
                  waiver("MC2", applies_to_environment="staging"), waiver("MC2", status="proposed")):
            with self.subTest(w=w):
                self.assertEqual(gate(st, waivers=[w])["verdict"], "NO_GO")
        with self.assertRaises(E.EvidenceInvalid):
            gate(st, waivers=[{"id": "incomplete", "component": "MC2"}])
        with self.assertRaises(E.EvidenceInvalid):
            gate(st, waivers=[waiver("MC2", approvers=[])])

    def test_failed_skipped_tests_absent_or_stale_manifest_block(self):
        st = status(("MC1", "P0", "CLOSED"))
        self.assertEqual(gate(st, tests={"failed": 1, "errors": 0})["verdict"], "NO_GO")
        self.assertEqual(gate(st, tests={})["verdict"], "NO_GO")
        self.assertEqual(gate(st, tests=dict(OK_TESTS, certification_critical_skips=3))["verdict"], "NO_GO")
        self.assertEqual(gate(st, manifest=None)["verdict"], "NO_GO")
        self.assertEqual(gate(st, manifest={"source_digest": "sha256:" + "b" * 64})["verdict"], "NO_GO")

    def test_corrupt_status_refused(self):
        with self.assertRaises(E.EvidenceInvalid):
            gate({"components": []})
        with self.assertRaises(E.EvidenceInvalid):
            gate(status(("MC1", "P0", "DONE-ISH")))

    def test_shipped_status_file_is_well_formed_and_complete(self):
        st = json.loads((PKG / "MISSING_COMPONENTS_STATUS.json").read_text())
        ids = [c["id"] for c in st["components"]]
        self.assertEqual(ids, [f"INV29-MC{i:03d}" for i in range(1, 104)])
        for c in st["components"]:
            self.assertIn(c["status"], E.ALL_STATES)
            self.assertTrue(c["evidence"] or c["blocker"], c["id"])
            for path in c["evidence"]:
                self.assertTrue((PKG / path.split("::")[0]).exists(), f"{c['id']}: {path} missing")
        E.derive_gate(st, tests=OK_TESTS, manifest=None, source_digest="x", today=TODAY, version="4.3.0",
                      waivers=json.loads((PKG / "governance" / "WAIVERS.json").read_text())["waivers"])

    def test_ledger_chain_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "ledger.jsonl"
            led = E.Ledger(p)
            for i in range(5):
                led.append("test", {"i": i})
            self.assertEqual(led.verify()["entries"], 5)
            lines = p.read_text().splitlines()
            e = json.loads(lines[2]); e["body"]["i"] = 99; lines[2] = json.dumps(e)
            p.write_text("\n".join(lines) + "\n")
            with self.assertRaises(E.EvidenceInvalid):
                led.verify()
            p.write_text("\n".join(lines[:2] + lines[3:]) + "\n")
            with self.assertRaises(E.EvidenceInvalid):
                led.verify()


if __name__ == "__main__":
    unittest.main()
