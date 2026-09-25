"""Gate tooling fails closed (C009, C070, C090, C099, C100)."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from _support import PKG_DIR


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, PKG_DIR / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class GovernanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(PKG_DIR / "governance", self.root / "governance")
        self.g = load_tool("check_governance")

    def tearDown(self):
        self.tmp.cleanup()

    def owners(self, fn):
        p = self.root / "governance" / "OWNERS.json"
        d = json.loads(p.read_text()); fn(d); p.write_text(json.dumps(d))

    def test_repo_metadata_valid_but_blocked_until_assigned(self):
        r = self.g.check(PKG_DIR)
        self.assertEqual(r["invalid"], [])
        self.assertEqual(r["status"], "BLOCKED")

    def test_all_assigned_passes(self):
        def fill(d):
            for r in d["roles"].values():
                r["assignee"] = "someone"
            d["tabletop"]["last_exercised"] = "2026-09-01"
        self.owners(fill)
        self.assertEqual(self.g.check(self.root, today=dt.date(2026, 9, 22))["status"], "PASS")
        self.assertEqual(self.g.check(self.root, today=dt.date(2028, 1, 1))["status"], "BLOCKED")  # review overdue

    def test_missing_role_and_bad_raci_invalid(self):
        self.owners(lambda d: d["roles"].pop("security_owner"))
        self.assertEqual(self.g.check(self.root)["status"], "INVALID")

    def test_waiver_rules(self):
        p = self.root / "governance" / "WAIVERS.json"
        base = {"requirement": "INV-37-C068", "justification": "x", "compensating_controls": "y",
                "approver_role": "architecture_approver", "approver": "a"}
        p.write_text(json.dumps({"waivers": [dict(base, created="2026-01-01", expires="2026-12-31")]}))
        self.assertIn("exceeds", " ".join(self.g.check(self.root)["invalid"]))
        p.write_text(json.dumps({"waivers": [dict(base, created="2026-01-01", expires="2026-02-01")]}))
        self.assertIn("expired", " ".join(self.g.check(self.root, today=dt.date(2026, 9, 22))["blocked"]))
        p.write_text(json.dumps({"waivers": [{"requirement": "INV-37-C001"}]}))
        self.assertEqual(self.g.check(self.root)["status"], "INVALID")


class PerfGateTest(unittest.TestCase):
    def test_missing_metrics_block_and_regressions_fail(self):
        pg = load_tool("perf_gate")
        th = json.loads((PKG_DIR / "PERF_THRESHOLDS.json").read_text())
        self.assertEqual(pg.evaluate({}, None, th)["status"], "BLOCKED")
        base = json.loads((PKG_DIR / "artifacts" / "benchmarks" / "baseline.json").read_text())
        self.assertEqual(pg.evaluate(base, base, th)["status"], "PASS")
        worse = json.loads(json.dumps(base))
        worse["shm_zero_copy_receiver"]["data_plane_copies"] = 1
        self.assertEqual(pg.evaluate(worse, base, th)["status"], "REGRESSION")
        slow = json.loads(json.dumps(base))
        slow["manifest_mib_s"] = base["manifest_mib_s"] * 0.5
        self.assertEqual(pg.evaluate(slow, base, th)["status"], "REGRESSION")


class ProductionGateTest(unittest.TestCase):
    def test_gate_cannot_pass_without_external_evidence_and_approvals(self):
        gate = load_tool("production_gate")
        r = gate.evaluate("sha256:" + "0" * 64)
        self.assertEqual(r["decision"], "NO_GO")
        self.assertIn("evidence_unsigned", r["blockers"])
        self.assertTrue(any(b.startswith("approvals_missing") for b in r["blockers"]))
        statuses = {c["status"] for c in r["criteria"]}
        self.assertTrue(statuses <= {"PASS", "BLOCKED", "WAIVED", "NOT_APPLICABLE"})
        self.assertEqual({c["criterion"]: c["status"] for c in r["criteria"]}["host_guest_zero_copy"], "BLOCKED")

    def test_pins(self):
        self.assertEqual(load_tool("check_pins").check()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()


class CertificationRunnerTest(unittest.TestCase):
    def test_unexpected_skip_fails_certification(self):
        rc = load_tool("run_certification")
        import unittest as u

        class T(u.TestCase):
            def test_x(self):
                self.skipTest("some optional thing")

        res = rc.Collect(open("/dev/null", "w"), True, 0)
        u.TestSuite([T("test_x")]).run(res)
        self.assertEqual(res.records[0]["status"], "FAIL_UNEXPECTED_SKIP")
