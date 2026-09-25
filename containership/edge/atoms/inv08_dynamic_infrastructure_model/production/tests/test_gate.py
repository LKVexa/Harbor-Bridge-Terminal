"""Component 66 exit gate + status ledger tests."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from inv08_dynamic_infrastructure_model.production import exitgate, status, waivers as W
from inv08_dynamic_infrastructure_model.production.core import TrustRoot

PROD = Path(status.__file__).resolve().parent
KEY = b"k" * 32
DAY = 86400.0


def synthetic_status(state="LOCALLY_VERIFIED"):
    rows = []
    for c in range(1, 67):
        pr = "P2" if c in (6, 50) else ("P1" if c % 3 == 0 else "P0")
        for n in range(1, 37):
            rows.append({"component": c, "priority": pr, "check": n, "state": state})
    return {"schema": "PK_DYN_CHECKSTATUS/1", "checks": rows}


def trust():
    t = TrustRoot()
    t.add("g", KEY)
    return t


def env(t):
    p = {"x": 1}
    return {"payload": p, "signature": t.sign("g", p)}


class GateTest(unittest.TestCase):
    def test_definition_is_machine_readable(self):
        self.assertEqual(exitgate.DEFINITION["schema"], "PK_DYN_EXITGATE/1")
        self.assertEqual(len(exitgate.DEFINITION["domains"]), 10)
        json.dumps(exitgate.DEFINITION)

    def test_evidence_inputs_required(self):
        t = trust()
        self.assertEqual(exitgate.evaluate({"schema": "x"}, [], [], env(t), t, now=0)["decision"], "NO_GO")
        s = synthetic_status(); s["checks"].pop()
        self.assertEqual(exitgate.evaluate(s, [], [], env(t), t, now=0)["failed"], ["INPUT"])

    def test_nonproduction_evidence_fails_D5(self):
        t = trust()
        d = exitgate.evaluate(synthetic_status(), [], [], env(t), t, now=0)
        self.assertEqual(d["decision"], "NO_GO")
        self.assertEqual(d["failed"], ["D5"])

    def test_falsifier_gate_is_a_gate_not_a_wall(self):
        """With SYNTHETIC all-verified inputs and a SYNTHETIC production verifier,
        GO is reachable - and each single omission flips it back to NO_GO."""
        t = trust()
        ok = lambda e: True
        self.assertEqual(exitgate.evaluate(synthetic_status(), [], [], env(t), t, now=0, verifier=ok)["decision"], "GO")
        s = synthetic_status(); s["checks"][0]["state"] = "PARTIAL"
        self.assertEqual(exitgate.evaluate(s, [], [], env(t), t, now=0, verifier=ok)["failed"], ["D1/D2/D3"])
        self.assertEqual(exitgate.evaluate(synthetic_status(), [], ["owner"], env(t), t, now=0, verifier=ok)["failed"], ["D4"])
        self.assertEqual(exitgate.evaluate(synthetic_status(), [], [], {}, t, now=0, verifier=ok)["failed"], ["D5"])

    def test_p2_open_is_nonblocking(self):
        t = trust()
        s = synthetic_status()
        for r in s["checks"]:
            if r["component"] == 6:
                r["state"] = "BLOCKED"
        d = exitgate.evaluate(s, [], [], env(t), t, now=0, verifier=lambda e: True)
        self.assertEqual(d["decision"], "GO")
        self.assertEqual(d["p2_open_nonblocking"], 36)

    def _waiver(self, comp, check, **kw):
        w = {"id": "WVR-0001", "component": comp, "check": check, "kind": "waiver", "owner": "Alice Example",
             "approver": "Bob Example", "created": 0.0, "expires": 30 * DAY, "review_by": 20 * DAY,
             "compensating_controls": ["manual review"], "residual_risk": "low", "rationale": "test"}
        w.update(kw)
        return w

    def test_waiver_integration(self):
        t = trust(); ok = lambda e: True
        s = synthetic_status()
        row = next(r for r in s["checks"] if r["priority"] == "P0" and r["check"] == 34)
        row["state"] = "BLOCKED"
        w = self._waiver(row["component"], 34)
        self.assertEqual(exitgate.evaluate(s, [w], [], env(t), t, now=DAY, verifier=ok)["decision"], "GO")
        # expired waiver -> blocking
        self.assertEqual(exitgate.evaluate(s, [w], [], env(t), t, now=31 * DAY, verifier=ok)["decision"], "NO_GO")

    def test_p0_implementation_checks_unwaivable(self):
        t = trust(); ok = lambda e: True
        s = synthetic_status()
        row = next(r for r in s["checks"] if r["priority"] == "P0" and r["check"] == 6)
        row["state"] = "BLOCKED"
        d = exitgate.evaluate(s, [self._waiver(row["component"], 6)], [], env(t), t, now=DAY, verifier=ok)
        self.assertEqual(d["decision"], "NO_GO")
        self.assertTrue(d["invalid_waivers"])

    def test_waiver_cannot_suppress_ownership_or_evidence(self):
        t = trust()
        d = exitgate.evaluate(synthetic_status(), [self._waiver(1, 1)], ["x"], {}, t, now=DAY)
        self.assertEqual(sorted(d["failed"]), ["D4", "D5"])

    def test_signed_decision_replays(self):
        t = trust()
        args = (synthetic_status(), [], ["x"], env(t))
        d = exitgate.evaluate(*args, t, now=5.0)
        signed = exitgate.sign_decision(d, t, "g")
        self.assertEqual(exitgate.replay(signed, *args, t), (True, "replayed identically"))
        bad = copy.deepcopy(signed); bad["decision"]["decision"] = "GO"
        self.assertFalse(exitgate.replay(bad, *args, t)[0])
        changed = (synthetic_status("PARTIAL"), [], ["x"], env(t))
        self.assertEqual(exitgate.replay(signed, *changed, t)[1], "replay disagrees with recorded decision")


class StatusTest(unittest.TestCase):
    def test_checklist_parse_2376(self):
        titles = status.checklist_titles(PROD / "docs" / "COMPONENT_CHECKLISTS.md")
        self.assertEqual(len(titles), 66)
        self.assertEqual(sum(len(v["checks"]) for v in titles.values()), 2376)

    def test_derivation_rules(self):
        titles = status.checklist_titles(PROD / "docs" / "COMPONENT_CHECKLISTS.md")
        comps = {1: {"subparts": [
            {"name": "a", "state": "IMPLEMENTED", "spec": "production/core.py", "tests": ["t.ok"]},
            {"name": "b", "state": "IMPLEMENTED", "spec": "production/core.py", "tests": ["t.bad"]},
            {"name": "c", "state": "PARTIAL", "spec": "production/core.py", "tests": ["t.ok"], "blocker": "x"},
            {"name": "d", "state": "BLOCKED", "spec": "nope/missing.md", "tests": [], "blocker": "y"},
            {"name": "e", "state": "IMPLEMENTED", "spec": "production/core.py", "tests": []}]}}
        rows = status.derive(comps, titles, {"t.ok": True, "t.bad": False}, set())
        st = {r["check"]: r["state"] for r in rows if r["component"] == 1}
        self.assertEqual(len(rows), 2376)
        self.assertEqual((st[5], st[6], st[7]), ("LOCALLY_VERIFIED",) * 3)
        self.assertEqual(st[10], "BLOCKED")                      # failing test never verifies
        self.assertEqual((st[12], st[13]), ("PARTIAL", "PARTIAL"))
        self.assertEqual((st[14], st[15], st[16]), ("BLOCKED",) * 3)
        self.assertEqual(st[19], "BLOCKED")                      # no tests -> not verified
        self.assertEqual((st[1], st[36]), ("BLOCKED", "BLOCKED"))
        self.assertTrue(all(r["state"] == "BLOCKED" for r in rows if r["component"] == 2 and 5 <= r["check"] <= 19))

    def test_no_complete_state_exists(self):
        self.assertFalse(hasattr(status, "COMPLETE"))
        self.assertEqual(status.GENERIC[36][0], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
