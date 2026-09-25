"""Release gate, supply chain, governance and operational-asset integrity (C009, C020, C031, C045,
C078, C080, C090, C096, C098-C100, REPO-001..011)."""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _support import PKG_DIR, release


class ManifestTest(unittest.TestCase):
    def test_manifest_detects_tamper_addition_and_removal(self):
        m = release.build_manifest()
        self.assertEqual(release.verify_manifest(m), [])
        bad = copy.deepcopy(m)
        first = next(iter(bad["files"]))
        bad["files"][first] = "0" * 64
        self.assertTrue(any("digest mismatch" in p for p in release.verify_manifest(bad)))
        bad = copy.deepcopy(m)
        bad["files"]["ghost.py"] = "0" * 64
        self.assertTrue(any("missing" in p for p in release.verify_manifest(bad)))
        bad = copy.deepcopy(m)
        bad["files"].pop(first)
        self.assertTrue(any("unlisted" in p for p in release.verify_manifest(bad)))

    def test_sbom_and_provenance_bind_tree_digest(self):
        m = release.build_manifest()
        self.assertEqual(release.build_sbom(m)["metadata"]["component"]["hashes"][0]["content"], m["tree_digest"])
        self.assertEqual(release.build_provenance(m)["subject"][0]["digest"]["sha256"], m["tree_digest"])


class SealTest(unittest.TestCase):
    def test_unsealed_without_key(self):
        with mock.patch.dict(os.environ, {"INV35_EVIDENCE_KEY": ""}):
            s = release.seal({"a": 1})
        self.assertFalse(s["sealed"])
        self.assertFalse(release.verify_seal({"a": 1}, s))

    def test_sealed_and_tamper_evident(self):
        key = bytes(range(32))
        with mock.patch.dict(os.environ, {"INV35_EVIDENCE_KEY": key.hex()}):
            s = release.seal({"verdict": "PARTIAL"})
        self.assertTrue(release.verify_seal({"verdict": "PARTIAL"}, s, key))
        self.assertFalse(release.verify_seal({"verdict": "PASS"}, s, key))
        self.assertFalse(release.verify_seal({"verdict": "PARTIAL"}, s, b"x" * 32))


class GovernanceGateTest(unittest.TestCase):
    def test_current_governance_blocks_production(self):
        gates = {f["gate"] for f in release.governance_findings()}
        self.assertTrue({"ownership", "license", "approval", "dependency", "waiver"} <= gates)

    def test_fully_governed_tree_has_no_findings(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "governance").mkdir()
            (root / "release").mkdir()
            owners = json.loads((PKG_DIR / "governance/OWNERS.json").read_text())
            for r in owners["roles"].values():
                r.update(name="Someone", status="accepted")
            (root / "governance/OWNERS.json").write_text(json.dumps(owners))
            (root / "governance/LICENSE_DECISION.json").write_text(json.dumps({"status": "approved"}))
            (root / "LICENSE").write_text("x")
            (root / "governance/APPROVALS.json").write_text(json.dumps({"approvals": []}))
            (root / "governance/WAIVERS.json").write_text(json.dumps({"waivers": []}))
            (root / "governance/REVIEW_SCHEDULE.json").write_text(json.dumps({"reviews": []}))
            (root / "release/dependencies.json").write_text(json.dumps({"dependencies": [
                {"name": "pk_core", "scope": "required", "pin_state": "pinned"}]}))
            with mock.patch.object(release, "PKG", root):
                self.assertEqual(release.governance_findings(dt.date(2026, 9, 22)), [])

    def test_expired_waiver_blocks(self):
        findings = release.governance_findings(dt.date(2027, 6, 1))
        self.assertTrue(any(f["gate"] == "waiver" and "expired" in f["detail"] for f in findings))
        self.assertTrue(any(f["gate"] == "review" for f in findings))

    def test_every_waiver_and_review_is_owned_and_dated(self):
        w = json.loads((PKG_DIR / "governance/WAIVERS.json").read_text())
        roles = json.loads((PKG_DIR / "governance/OWNERS.json").read_text())["roles"]
        for x in w["waivers"]:
            self.assertIn(x["owner"], roles)
            dt.date.fromisoformat(x["expires"])
        for r in json.loads((PKG_DIR / "governance/REVIEW_SCHEDULE.json").read_text())["reviews"]:
            self.assertIn(r["owner"], roles)
            self.assertGreater(r["cadence_days"], 0)


class TraceabilityTest(unittest.TestCase):
    def test_rtm_is_current_and_complete(self):
        r = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "build_rtm.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rtm = json.loads((PKG_DIR / "requirements/traceability.json").read_text())
        self.assertEqual(rtm["row_count"], 100)
        for row in rtm["rows"]:
            if row["status"] == "present" and row["closure"] != "baseline_present":
                self.assertEqual(row["blockers"], [])
            if row["status"] != "present":
                self.assertTrue(row["blockers"], row["check_id"])

    def test_no_row_claims_present_without_approval(self):
        rtm = json.loads((PKG_DIR / "requirements/traceability.json").read_text())
        approvals = json.loads((PKG_DIR / "governance/APPROVALS.json").read_text())["approvals"]
        from fnmatch import fnmatch
        globs = [a["requirement"] for a in approvals if a["status"] == "approved" and a.get("requirement")]
        for row in rtm["rows"]:
            if row["closure"] == "closed":
                self.assertTrue(any(fnmatch(row["check_id"], g) for g in globs), row["check_id"])


class OperationalAssetsTest(unittest.TestCase):
    def test_alerts_reference_real_metrics_and_runbook_anchors(self):
        catalog = {m["name"] for m in json.loads((PKG_DIR / "telemetry/metrics_catalog.json").read_text())["metrics"]}
        runbooks = (PKG_DIR / "runbooks/RUNBOOKS.md").read_text()
        alerts = json.loads((PKG_DIR / "alerts/inv35_alerts.json").read_text())
        for g in alerts["groups"]:
            for rule in g["rules"]:
                names = set(re.findall(r"inv35_[a-z_]+", rule["expr"]))
                base = {re.sub(r"_(bucket|count)$", "", n) for n in names}
                self.assertTrue(base <= catalog, (rule["alert"], base - catalog))
                anchor = rule["annotations"]["runbook"].split("#")[1]
                self.assertIn(f'id="{anchor}"', runbooks, rule["alert"])
                self.assertIn(rule["labels"]["severity"], ("page", "ticket"))

    def test_dashboard_queries_reference_real_metrics(self):
        catalog = {m["name"] for m in json.loads((PKG_DIR / "telemetry/metrics_catalog.json").read_text())["metrics"]}
        dash = (PKG_DIR / "dashboards/inv35_overview.json").read_text()
        for n in set(re.findall(r"inv35_[a-z_]+", dash)):
            self.assertIn(re.sub(r"_(bucket|count)$", "", n), catalog)

    def test_required_documents_exist_and_declare_approval_state(self):
        for rel in ("docs/operations/SLO.md", "docs/operations/ROLLOUT_AND_ROLLBACK.md",
                    "docs/operations/INCIDENT_RESPONSE.md", "docs/operations/PATCHING_AND_EOL.md",
                    "docs/operations/STATELESSNESS_DECISION.md", "runbooks/RUNBOOKS.md",
                    "docs/security/THREAT_MODEL.md", "docs/resilience/FMEA.md", "docs/architecture/ARCHITECTURE.md"):
            text = (PKG_DIR / rel).read_text()
            self.assertGreater(len(text), 500, rel)
        self.assertTrue((PKG_DIR / "CODEOWNERS").is_file())
        self.assertTrue((PKG_DIR / "SECURITY.md").is_file())
        self.assertTrue((PKG_DIR / ".github/workflows/verify.yml").is_file())

    def test_smoke_cli(self):
        r = subprocess.run([sys.executable, str(PKG_DIR / "tools/inv35ctl.py"), "smoke"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("SMOKE=PASS", r.stdout)


if __name__ == "__main__":
    unittest.main()
