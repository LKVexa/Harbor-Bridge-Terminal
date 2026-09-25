"""Gate tooling (MC-052, MC-076, MC-032..MC-036, MC-049, MC-053, MC-054, MC-074, MC-082, MC-084..MC-087,
MC-089) including the release-gate falsifier: GO must be *reachable* when every input is genuinely supplied,
and each single omission must give NO_GO - otherwise "it cannot pass" would be asserted, not checked."""
import copy
import datetime as dt
import json
import tempfile
import unittest
from importlib import import_module
from pathlib import Path

from harness import PKG_DIR

T = {n: import_module(f"{PKG_DIR.name}.tools.{n}") for n in (
    "release_gate", "governance_check", "rtm", "deps_check", "manifest", "bootstrap", "lint", "sast", "secret_scan",
    "sbom", "master", "bench", "coverage", "mutation", "review_due", "package_release", "check_all")}
TODAY = dt.date(2026, 9, 23)


def good():
    lanes = {k: {"pass": True} for k in ("tests_normal", "tests_optimized", "lint", "sast", "mc_status")}
    mc = {"rows": [{"mc": "MC-001", "status": "implemented_unreviewed"}, {"mc": "MC-007", "status": "decision_pending"}]}
    waivers = {"entries": [{"id": "W-1", "status": "approved", "approver": "Dana Human", "owner": "Ola Owner",
                            "expires": "2026-12-01", "controls": ["MC-007"]}]}
    gov = {"pass": True}
    bench = {"verdict": "PASS", "quick": False}
    soak = {"verdict": "PASS"}
    pk = {"verdict": "GO"}
    review = {"reviewer": "Rae Reviewer", "items": {"MC-001": "accepted"}}
    approval = {"decision": "APPROVE", "approver": "Riley Human"}
    owners = {"roles": [{"alias": "inv28-security-owner", "holder": "Sam Human"}]}
    return [lanes, mc, waivers, gov, bench, soak, pk, review, approval, owners]


class ReleaseGateFalsifier(unittest.TestCase):
    def ev(self, args):
        return T["release_gate"].evaluate(*args, today=TODAY)

    def test_go_reachable_with_every_input_real(self):
        r = self.ev(good())
        self.assertEqual(r["verdict"], "GO", r["blockers"])

    def test_each_single_omission_is_no_go(self):
        muts = {
            "lane": lambda x: x[0]["lint"].update({"pass": False}),
            "unreviewed_item": lambda x: x[7]["items"].clear(),
            "review_rejected": lambda x: x[7]["items"].update({"MC-001": "rejected"}),
            "review_by_bot": lambda x: x[7].update({"reviewer": "review-bot"}),
            "review_by_claude": lambda x: x[7].update({"reviewer": "Claude"}),
            "reviewer_is_approver": lambda x: x[7].update({"reviewer": "Riley Human"}),
            "partial_needs_waiver": lambda x: x[1]["rows"].append({"mc": "MC-044", "status": "partial"}),
            "waiver_expired": lambda x: x[2]["entries"][0].update({"expires": "2026-01-01"}),
            "waiver_unapproved": lambda x: x[2]["entries"][0].update({"status": "proposed"}),
            "waiver_self_approved": lambda x: x[2]["entries"][0].update({"approver": "Ola Owner"}),
            "governance": lambda x: x[3].update({"pass": False}),
            "bench_fail": lambda x: x[4].update({"verdict": "FAIL"}),
            "bench_quick": lambda x: x[4].update({"quick": True}),
            "soak_missing": lambda x: x.__setitem__(5, None),
            "pk_gate": lambda x: x[6].update({"verdict": "NO_GO"}),
            "no_approval": lambda x: x.__setitem__(8, None),
            "service_approver": lambda x: x[8].update({"approver": "release-pipeline"}),
            "sod": lambda x: x[8].update({"approver": "Sam Human"}),
        }
        for name, mut in muts.items():
            with self.subTest(name):
                args = copy.deepcopy(good())
                mut(args)
                self.assertEqual(self.ev(args)["verdict"], "NO_GO", name)

    def test_complete_status_refused_by_rtm(self):
        src = json.loads((PKG_DIR / "ops" / "MC_STATUS.json").read_text())
        src["items"]["MC-001"]["status"] = "complete"
        self.assertTrue(any("independent review" in e for e in T["rtm"].validate(src, evidence_required=False)))


class Lanes(unittest.TestCase):
    """Each lane runs and produces evidence of the right shape (fast lanes only; slow ones by check_all)."""

    def test_static_lanes_pass(self):
        self.assertEqual(T["lint"].lint(), [])
        self.assertEqual(T["secret_scan"].scan(), [])
        self.assertTrue(T["deps_check"].check()["pass"])
        self.assertEqual(T["master"].check(), [])
        sast = [f for rel, p in T["deps_check"].py_files(include_tests=False)
                for f in T["sast"].scan_file(rel, p.read_text())]
        self.assertEqual(sast, [])

    def test_sast_detects(self):
        bad = "import os, hashlib, subprocess\nos.system('x')\nhashlib.md5(b'')\nsubprocess.run('x', shell=True)\neval('1')\n"
        rules = {f["rule"] for f in T["sast"].scan_file("x.py", bad)}
        self.assertEqual(rules, {"S-SHELL", "S-HASH", "S-EXEC"})

    def test_secret_scan_detects_without_echoing(self):
        rx = T["secret_scan"].RULES
        self.assertTrue(rx["aws-access-key"].search("AKIA" + "ABCDEFGHIJKLMNOP"))
        self.assertTrue(rx["pem-private-key"].search("-----BEGIN RSA " + "PRIVATE KEY-----"))

    def test_sbom_shape(self):
        s = T["sbom"].build()
        self.assertEqual((s["bomFormat"], s["specVersion"]), ("CycloneDX", "1.5"))
        self.assertEqual({c["name"] for c in s["components"]}, {"pk_core", "cpython"})

    def test_bench_compare_flags_regressions(self):
        thr = {"thresholds": {"select_p99_ms_16_entries": 1, "select_p99_ms_1024_entries": 1, "register_1024_total_s": 1,
                              "snapshot_1024_ms": 1, "verify_snapshot_1024_ms": 1}}
        res = {"select_16": {"p99_ms": 2}, "select_1024": {"p99_ms": 0.5}, "build_1024_s": 0.1, "snapshot_1024_ms": 0.1,
               "verify_snapshot_1024_ms": 0.1}
        self.assertEqual(len(T["bench"].compare(res, thr)), 1)

    def test_mutation_operators_generate_sites(self):
        src = (PKG_DIR / "selection.py").read_text()
        import ast
        n = len(T["mutation"].sites(ast.parse(src), T["mutation"].TARGETS["selection.py"]))
        self.assertGreater(n, 40)
        mutated, line, desc = T["mutation"].mutate(src, T["mutation"].TARGETS["selection.py"], 0)
        self.assertNotEqual(mutated, src)

    def test_coverage_counts_executable_lines_only(self):
        lines = T["coverage"].executable_lines(PKG_DIR / "explain.py")
        self.assertTrue(lines)
        self.assertLess(len(lines), len((PKG_DIR / "explain.py").read_text().splitlines()))

    def test_governance_fails_on_placeholders(self):
        r = T["governance_check"].check(TODAY)
        self.assertFalse(r["pass"])
        self.assertTrue(r["owners"] and r["decisions"])

    def test_review_due_lane(self):
        self.assertEqual(T["review_due"].main(["--today", "2026-09-23"]), 0)
        self.assertEqual(T["review_due"].main(["--today", "2026-09-23", "--fail-on-overdue"]), 1)

    def test_bootstrap(self):
        self.assertEqual(T["bootstrap"].main([]), 0)

    def test_package_release_is_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            T["package_release"].main(["--out", a])
            T["package_release"].main(["--out", b])
            da = sorted(Path(a).glob("*.sha256"))[0].read_text().split()[0]
            db = sorted(Path(b).glob("*.sha256"))[0].read_text().split()[0]
            self.assertEqual(da, db)
            stmt = json.loads((Path(a) / "provenance.intoto.json").read_text())
            self.assertEqual(stmt["subject"][0]["digest"]["sha256"], da)
            self.assertIsNone(stmt["signature"])

    def test_requirements_lock_pins_match_ci(self):
        self.assertTrue(T["deps_check"].check()["pass"])


if __name__ == "__main__":
    unittest.main()
