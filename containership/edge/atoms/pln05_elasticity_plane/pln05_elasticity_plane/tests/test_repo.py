"""Repository-level checks as tests (scope drift, versions, governance files, traceability,
ambient authority, threat/fault mapping) and exit-gate behaviour on synthetic evidence."""
from __future__ import annotations

import datetime as dt
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


check_repo, traceability, gate, mc_status = (_mod(n) for n in ("check_repo", "traceability", "gate", "mc_status"))


class RepoTest(unittest.TestCase):
    def test_versions_consistent(self):
        self.assertEqual(check_repo.version_consistency(), [])

    def test_scope_has_no_drift(self):
        self.assertEqual(check_repo.scope_drift(), [])

    def test_required_documents_present(self):
        self.assertEqual(check_repo.required_documents(), [])

    def test_governance_files_present(self):
        self.assertEqual(check_repo.governance(), [])

    def test_runtime_has_no_ambient_authority(self):
        self.assertEqual(check_repo.ambient_authority(), [])
        self.assertEqual(check_repo.code_hygiene(), [])

    def test_doc_references_resolve(self):
        self.assertEqual(check_repo.references(), [])

    def test_every_threat_has_a_test(self):
        self.assertEqual(check_repo.threat_tests(), [])

    def test_failure_matrix_scenarios_exist(self):
        self.assertEqual(check_repo.failure_matrix(), [])

    def test_traceability_is_valid(self):
        res = traceability.validate(traceability.load())
        self.assertEqual(res["errors"], [])
        self.assertEqual(traceability.render(traceability.load()),
                         (ROOT / "traceability" / "REQUIREMENTS_MATRIX.md").read_text())

    def test_mc_status_covers_every_item(self):
        st = mc_status.build()
        self.assertEqual(len(st["components"]), 34)
        self.assertEqual(st["items"], 1438)  # 1468 boxes minus 15 global gates and 15 final-closure boxes
        self.assertNotIn("COMPLETE", st["component_status_counts"])  # nothing closes without owner sign-off

    def test_performance_gate_thresholds(self):
        pg_spec = importlib.util.spec_from_file_location("pg", ROOT / "ci" / "performance_gate.py")
        pg = importlib.util.module_from_spec(pg_spec)
        pg_spec.loader.exec_module(pg)
        import json
        thr = json.loads((ROOT / "benchmarks" / "thresholds.json").read_text())
        base = json.loads((ROOT / "benchmarks" / "baseline.json").read_text())
        res = base["results"]
        today = dt.date(2026, 9, 23)
        self.assertEqual(pg.evaluate(res, base, thr, [], "presubmit", today)["result"], "PASS")
        slow = json.loads(json.dumps(res))
        slow["decision_latency"]["p99_ms"] = 5.0  # breaks the absolute p99 SLO and the relative bound
        out = pg.evaluate(slow, base, thr, [], "presubmit", today)
        self.assertEqual(out["result"], "FAIL")
        self.assertTrue(any("p99" in f for f in out["failures"]))
        self.assertEqual(pg.evaluate(res, base, thr, [], "release", today)["result"], "FAIL")  # baseline not APPROVED
        waived = [{"id": "P1", "kind": "performance", "metric": "decision_latency.p99_ms", "expires": "2027-01-01"}]
        self.assertEqual(pg.evaluate(slow, base, thr, waived, "presubmit", today)["result"], "PASS")
        expired = [dict(waived[0], expires="2026-01-01")]
        self.assertEqual(pg.evaluate(slow, base, thr, expired, "presubmit", today)["result"], "FAIL")

    def test_gate_refuses_skips_and_self_approval(self):
        manifest = {"version": "4.2.0", "source_revision": "a" * 40, "tier": "release",
                    "results": {"unit": {"result": "PASS", "skipped": 0},
                                "framework": {"result": "PASS", "skipped": 2, "mandatory": True}}}
        mc = {"components": [{"id": "MC-01", "status": "COMPLETE"}], "component_status_counts": {}, "item_totals": {}}
        trace = {"requirements": [{"id": "PLN-05-C001", "status": "verified"}]}
        oncall = {"roles": {"pln05.release-approver": {"assignee": "team-a"}}, "last_reviewed": "2026-09-01",
                  "review_cadence_days": 90}
        base = dict(mc=mc, trace=trace, oncall=oncall, scope={"adr_status": "ACCEPTED"},
                    baseline={"status": "APPROVED"}, license_present=True, today=dt.date(2026, 9, 23))
        approvals = [{"role": r, "approver": "person", "version": "4.2.0", "source_revision": "a" * 40}
                     for r in gate.REQUIRED_SIGNERS]
        res = gate.evaluate(manifest, approvals=approvals, waivers=[], **base)
        self.assertEqual(res["verdict"], "NO_GO")
        self.assertTrue(any("skipped" in b["blocker"] for b in res["blockers"]))
        manifest["results"]["framework"]["skipped"] = 0
        self.assertEqual(gate.evaluate(manifest, approvals=approvals, waivers=[], **base)["verdict"], "GO")
        selfish = [dict(a, approver="Claude chop-shop") for a in approvals]
        res = gate.evaluate(manifest, approvals=selfish, waivers=[], **base)
        self.assertEqual(res["verdict"], "NO_GO")
        expired = [{"id": "W-9", "status": "APPROVED", "expires": "2026-01-01"}]
        self.assertEqual(gate.evaluate(manifest, approvals=approvals, waivers=expired, **base)["verdict"], "NO_GO")
        ok = [{"id": "W-9", "status": "APPROVED", "expires": "2027-01-01"}]
        self.assertEqual(gate.evaluate(manifest, approvals=approvals, waivers=ok, **base)["verdict"], "CONDITIONAL_GO")
        stale = [dict(a, source_revision="b" * 40) for a in approvals]
        self.assertEqual(gate.evaluate(manifest, approvals=stale, waivers=[], **base)["verdict"], "NO_GO")


if __name__ == "__main__":
    unittest.main()
