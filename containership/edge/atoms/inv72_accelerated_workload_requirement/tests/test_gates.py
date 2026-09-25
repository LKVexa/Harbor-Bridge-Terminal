"""Tests for the gate tooling (C020, C070, C090, C098, C099, C100) including the release-gate falsifier:
GO must be *reachable* when every input is genuinely supplied, and each single omission must yield NO_GO.
Without the positive case, "we could not pass" would be an assertion rather than a checked property."""
import copy
import datetime as dt
import json
import unittest

from harness import PKG_DIR
from importlib import import_module

T = {n: import_module(f"{PKG_DIR.name}.tools.{n}") for n in ("release_gate", "governance_check", "perf_gate", "rtm",
                                                              "deps_check", "manifest", "bootstrap")}
TODAY = dt.date(2026, 9, 23)


def good_inputs():
    lanes = {k: {"pass": True} for k in ("tests_normal", "tests_optimized", "manifest", "rtm", "deps")}
    rtm = {"rows": [{"check_id": "INV-72-C001", "status": "present"}, {"check_id": "INV-72-C009", "status": "blocked"}]}
    waivers = {"entries": [{"id": "W-1", "status": "approved", "approver": "Dana Human", "expires": "2026-12-01",
                            "controls": ["INV-72-C009"]}]}
    governance = {"pass": True, "owners": [], "waivers": [], "reviews": [], "versions": []}
    perf = {"verdict": "PASS", "failures": [], "quick": False}
    pk = {"verdict": "GO"}
    approval = {"decision": "APPROVE", "approver": "Riley Human"}
    owners = {"roles": [{"alias": "inv72-security-owner", "holder": "Sam Human"}]}
    return lanes, rtm, waivers, governance, perf, pk, approval, owners


class ReleaseGateFalsifierTest(unittest.TestCase):
    def ev(self, *a):
        return T["release_gate"].evaluate(*a, today=TODAY)

    def test_go_is_reachable_with_every_input_real(self):
        r = self.ev(*good_inputs())
        self.assertEqual(r["verdict"], "GO", r["blockers"])

    def test_each_single_omission_is_no_go(self):
        mutations = {
            "lane": lambda x: x[0]["rtm"].update({"pass": False}),
            "rtm_ungoverned": lambda x: x[2]["entries"].clear(),
            "waiver_expired": lambda x: x[2]["entries"][0].update({"expires": "2026-01-01"}),
            "waiver_unapproved": lambda x: x[2]["entries"][0].update({"status": "pending_approval"}),
            "governance": lambda x: x[3].update({"pass": False}),
            "perf_fail": lambda x: x[4].update({"verdict": "FAIL"}),
            "perf_proposed": lambda x: x[4].update({"verdict": "PASS_UNDER_PROPOSED_THRESHOLDS"}),
            "perf_quick": lambda x: x[4].update({"quick": True}),
            "pk_gate": lambda x: x[5].update({"verdict": "NO_GO"}),
            "no_approval": lambda x: x[6].clear(),
            "service_approver": lambda x: x[6].update({"approver": "release-bot"}),
            "claude_approver": lambda x: x[6].update({"approver": "Claude"}),
            "sod": lambda x: x[6].update({"approver": "Sam Human"}),
        }
        for name, mut in mutations.items():
            with self.subTest(name):
                inp = list(copy.deepcopy(good_inputs()))
                mut(inp)
                self.assertEqual(self.ev(*inp)["verdict"], "NO_GO", name)


class GovernanceCheckTest(unittest.TestCase):
    def test_delivered_repository_fails_on_placeholders(self):
        res = T["governance_check"].run(TODAY)
        self.assertFalse(res["pass"])
        self.assertTrue(any("placeholder holder" in m for m in res["owners"]))
        self.assertTrue(any("not approved" in m for m in res["waivers"]))

    def test_versions_consistent(self):
        self.assertEqual(T["governance_check"].check_versions(), [])

    def test_codeowners_and_links_present(self):
        owners = T["governance_check"].check_owners()
        self.assertFalse([m for m in owners if "CODEOWNERS" in m or "does not link" in m], owners)


class PerfGateTest(unittest.TestCase):
    TH = {"status": "PROPOSED", "approver": None, "thresholds": {"s": {"p99_us": 100, "min_ops_per_s": 10}},
          "regression_budget_pct": 20}

    def test_quick_never_passes(self):
        r = T["perf_gate"].evaluate({"quick": True, "scenarios": {"s": {"p99_us": 1, "ops_per_s": 99}}}, self.TH)
        self.assertEqual(r["verdict"], "FAIL")

    def test_proposed_thresholds_cap_the_verdict(self):
        r = T["perf_gate"].evaluate({"quick": False, "scenarios": {"s": {"p99_us": 1, "ops_per_s": 99}}}, self.TH)
        self.assertEqual(r["verdict"], "PASS_UNDER_PROPOSED_THRESHOLDS")
        th = dict(self.TH, status="APPROVED", approver="Dana Human")
        self.assertEqual(T["perf_gate"].evaluate({"quick": False, "scenarios": {"s": {"p99_us": 1, "ops_per_s": 99}}}, th)["verdict"], "PASS")

    def test_threshold_and_regression_failures(self):
        th = dict(self.TH, status="APPROVED", approver="Dana")
        self.assertEqual(T["perf_gate"].evaluate({"quick": False, "scenarios": {"s": {"p99_us": 500, "ops_per_s": 99}}}, th)["verdict"], "FAIL")
        base = {"host": {"m": 1}, "scenarios": {"s": {"p99_us": 50}}}
        r = T["perf_gate"].evaluate({"quick": False, "host": {"m": 1}, "scenarios": {"s": {"p99_us": 90, "ops_per_s": 99}}}, th, base)
        self.assertEqual(r["verdict"], "FAIL")


class RtmTest(unittest.TestCase):
    def test_delivered_rtm_validates(self):
        src = json.loads((PKG_DIR / "ops" / "RTM_SOURCE.json").read_text())
        chk = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        self.assertEqual(T["rtm"].validate(src, chk), [])

    def test_present_without_evidence_is_rejected(self):
        src = json.loads((PKG_DIR / "ops" / "RTM_SOURCE.json").read_text())
        chk = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        s2 = copy.deepcopy(src)
        cid = next(k for k, v in s2["controls"].items() if v["status"] == "present")
        s2["controls"][cid]["tests"], s2["controls"][cid]["evidence"] = [], []
        self.assertTrue(T["rtm"].validate(s2, chk))
        s3 = copy.deepcopy(src)
        s3["controls"][cid]["tests"] = ["tests/test_v43.py::NoSuchTest"]
        self.assertTrue(T["rtm"].validate(s3, chk))

    def test_blocked_without_blocker_is_rejected(self):
        src = json.loads((PKG_DIR / "ops" / "RTM_SOURCE.json").read_text())
        chk = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        cid = next(k for k, v in src["controls"].items() if v["status"] != "present")
        src["controls"][cid]["blockers"] = []
        self.assertTrue(T["rtm"].validate(src, chk))


class DepsTest(unittest.TestCase):
    def test_runtime_is_stdlib_only(self):
        self.assertEqual(T["deps_check"].runtime_imports(), {})


class BootstrapTest(unittest.TestCase):
    def test_empty_environment_to_ready(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            code, st = T["bootstrap"].run("datacenter", journal=os.path.join(td, "j.jsonl"))
            self.assertEqual(code, 0, st)
            self.assertTrue(st["ready"] and st["demo"])
            code2, st2 = T["bootstrap"].run("datacenter", journal=os.path.join(td, "j.jsonl"))
            self.assertEqual(code2, 0)


if __name__ == "__main__":
    unittest.main()
