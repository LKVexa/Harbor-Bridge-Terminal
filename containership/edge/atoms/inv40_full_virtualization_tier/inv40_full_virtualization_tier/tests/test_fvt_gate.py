"""The production exit gate is a gate, not a wall: NO_GO on the delivered
traceability, GO only on a synthetic fully-closed record bound to the same
digest with an independent approver (the synthetic inputs are never shipped)."""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from _support import PKG_DIR
from fvt import gate

DIG = "sha256:" + "c" * 64


class GateTest(unittest.TestCase):
    def test_delivered_state_is_no_go(self):
        r = gate.evaluate(DIG)
        self.assertEqual(r["verdict"], "NO_GO")
        self.assertTrue(r["reasons"])

    def test_synthetic_complete_record_reaches_go(self):
        trace = json.loads((PKG_DIR / "traceability/requirements.json").read_text())
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            for r in trace["requirements"]:
                r["status"] = "CLOSED"
            (d / "t.json").write_text(json.dumps(trace))
            (d / "ci.json").write_text(json.dumps({"artifact_digest": DIG, "failed": 0, "skipped_mandatory": []}))
            (d / "ap.json").write_text(json.dumps({"artifact_digest": DIG, "approver": "SYNTHETIC-NOT-A-PERSON", "builder": "claude"}))
            ok = gate.evaluate(DIG, trace_path=d / "t.json", evidence_path=d / "ci.json", approval_path=d / "ap.json")
            self.assertEqual(ok["verdict"], "GO")
            # each single omission is NO_GO
            self.assertEqual(gate.evaluate("sha256:" + "d" * 64, trace_path=d / "t.json", evidence_path=d / "ci.json",
                                           approval_path=d / "ap.json")["verdict"], "NO_GO")
            (d / "ap2.json").write_text(json.dumps({"artifact_digest": DIG, "approver": "claude", "builder": "claude"}))
            self.assertEqual(gate.evaluate(DIG, trace_path=d / "t.json", evidence_path=d / "ci.json",
                                           approval_path=d / "ap2.json")["verdict"], "NO_GO")
            trace["requirements"][0]["status"] = "IMPLEMENTED"
            (d / "t2.json").write_text(json.dumps(trace))
            self.assertEqual(gate.evaluate(DIG, trace_path=d / "t2.json", evidence_path=d / "ci.json",
                                           approval_path=d / "ap.json")["verdict"], "NO_GO")


if __name__ == "__main__":
    unittest.main()


class TraceabilityIntegrityTest(unittest.TestCase):
    """Every traceability claim must point at something that exists."""

    def test_all_references_resolve(self):
        import importlib
        trace = json.loads((PKG_DIR / "traceability/requirements.json").read_text())
        self.assertEqual(len(trace["requirements"]), 106)
        missing = []
        for r in trace["requirements"]:
            self.assertEqual(r["owner"], "UNASSIGNED")
            self.assertIn("OWNER", r["blockers"])
            self.assertNotEqual(r["status"], "CLOSED")
            for b in r["blockers"]:
                self.assertIn(b, trace["blocker_catalog"])
            for p in r["implementation"] + r["docs"]:
                if not (PKG_DIR / p.split("::")[0]).exists():
                    missing.append((r["id"], p))
            if r["status"] == "IMPLEMENTED" and r["v420_status"] != "present":
                self.assertTrue(r["implementation"] or r["docs"], r["id"])
            for t in r["tests"]:
                if t.startswith(("evidence/", "tools/")):
                    continue
                mod, _, rest = t.split(" ")[0].partition(".")
                m = importlib.import_module(mod)
                obj = m
                for part in filter(None, rest.split(".")):
                    if not hasattr(obj, part):
                        missing.append((r["id"], t))
                        break
                    obj = getattr(obj, part)
        self.assertEqual(missing, [])
