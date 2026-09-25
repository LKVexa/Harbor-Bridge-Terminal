"""Release gate falsifiers (MC-041, MC-086, MC-040): GO is reachable when every input is supplied, and
each single omission yields NO_GO."""
import copy
import datetime as dt
import importlib
import json
import unittest

from harness import PKG, PKGNAME

gate = importlib.import_module(f"{PKGNAME}.tools.release_gate")
TODAY = dt.date(2026, 9, 23)


def load(n):
    return json.loads((PKG / n).read_text())


def perfect():
    mc = load("ops/MC_STATUS_SOURCE.json")
    for c in mc["components"].values():
        c["status"], c["blockers"] = "verified_local", []
    owners = load("ops/OWNERS.json")
    for i, r in enumerate(owners["roles"]):
        r["holder"] = f"Person {i}"
    return dict(lanes={k: {"pass": True} for k in gate.LANES}, mc=mc, waivers={"entries": []},
                governance={"pass": True}, perf={"verdict": "PASS"},
                approval={"decision": "APPROVE", "approver": "Person 2", "sha256sums": "abc"},
                owners=owners, reviews={"mc_reviews": [{"mc": k, "reviewer": "Person 4"} for k in mc["components"]]},
                today=TODAY, digest="abc")


class Gate(unittest.TestCase):
    def test_go_is_reachable(self):
        self.assertEqual(gate.evaluate(**perfect())["verdict"], "GO")

    def test_each_single_omission_is_no_go(self):
        muts = {
            "lane": lambda k: k["lanes"].update(tests_optimized={"pass": False}),
            "governance": lambda k: k.update(governance={"pass": False}),
            "perf": lambda k: k.update(perf=None),
            "p0_partial": lambda k: k["mc"]["components"]["MC-001"].update(status="partial", blockers=["W-TOOLCHAIN"]),
            "p0_unreviewed": lambda k: k["reviews"]["mc_reviews"].pop(0),
            "p1_unapproved_waiver": lambda k: k["mc"]["components"]["MC-090"].update(status="partial", blockers=["W-CI"]),
            "no_approval": lambda k: k.update(approval=None),
            "service_approver": lambda k: k["approval"].update(approver="release-bot"),
            "approver_is_sec_owner": lambda k: k["approval"].update(approver="Person 1"),
            "stale_digest": lambda k: k.update(digest="def"),
            "claude_reviewer": lambda k: k["reviews"]["mc_reviews"].__setitem__(0, {"mc": "MC-001", "reviewer": "claude"}),
        }
        for name, m in muts.items():
            k = copy.deepcopy(perfect())
            m(k)
            with self.subTest(name=name):
                self.assertEqual(gate.evaluate(**k)["verdict"], "NO_GO")

    def test_approved_waiver_can_cover_a_p1_but_never_a_p0(self):
        k = perfect()
        k["mc"]["components"]["MC-090"].update(status="partial", blockers=["W-CI"])
        k["waivers"] = {"entries": [{"id": "W-CI", "status": "approved", "approver": "Person 3", "expires": "2027-01-01"}]}
        self.assertEqual(gate.evaluate(**k)["verdict"], "GO")
        k["mc"]["components"]["MC-001"].update(status="partial", blockers=["W-CI"])
        self.assertEqual(gate.evaluate(**k)["verdict"], "NO_GO")

    def test_real_repository_state_is_no_go(self):
        r = gate.evaluate({k: {"pass": True} for k in gate.LANES}, load("ops/MC_STATUS_SOURCE.json"), load("ops/WAIVERS.json"),
                          {"pass": False}, None, None, load("ops/OWNERS.json"), load("ops/REVIEWS.json"), TODAY, "")
        self.assertEqual(r["verdict"], "NO_GO")
        self.assertEqual(r["per_mc_pass"], 0)


if __name__ == "__main__":
    unittest.main()
