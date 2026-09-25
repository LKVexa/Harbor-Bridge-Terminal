"""Repository checks for governance/spec artifacts (verification gate V2 of each MC)."""
from __future__ import annotations

import dataclasses
import json
import pathlib
import re
import subprocess
import sys
import unittest

from _helpers import envelope, resilience

PKG = pathlib.Path(__file__).resolve().parents[1]
read = lambda p: (PKG / p).read_text(encoding="utf-8")  # noqa: E731


class Governance(unittest.TestCase):
    def test_mc001_owners_registry_complete_and_enforced(self):
        text = read("OWNERS.yaml")
        for role in ("accountable_owner", "deputy_owner", "oncall_primary", "security_contact", "release_approver",
                     "architecture_board", "review_cadence_days", "recertify_by", "emergency_authority"):
            self.assertIn(role, text)
        for plane in ("PLN-02", "INV-49", "PLN-04", "PLN-06", "PLN-07"):
            self.assertIn(plane, text)
        self.assertIn("*", read(".github/CODEOWNERS"))
        for sev in ("SEV1", "SEV2", "SEV3"):
            self.assertIn(sev, read("docs/ESCALATION.md"))
        self.assertIn("| Release approval |", read("docs/RACI.md"))

    def test_mc002_mc052_adrs_have_status_alternatives_and_approval_slot(self):
        for adr in (PKG / "docs" / "adr").glob("ADR-*.md"):
            t = adr.read_text()
            self.assertRegex(t, r"\*\*Status:\*\* (Proposed|Accepted|Rejected|Superseded)")
            self.assertIn("## Approval record", t)
        self.assertIn("## Alternatives considered", read("docs/adr/ADR-0001-runtime-technology.md"))

    def test_mc003_requirements_have_unique_ids_and_tests(self):
        ids = re.findall(r"^\| (REQ-[A-Z]+-\d+) \|", read("docs/REQUIREMENTS.md"), re.M)
        self.assertGreaterEqual(len(ids), 15)
        self.assertEqual(len(ids), len(set(ids)))
        for line in read("docs/REQUIREMENTS.md").splitlines():
            if line.startswith("| REQ-"):
                self.assertIn("SHALL", line)

    def test_mc004_nfrs_cover_required_dimensions(self):
        t = read("docs/NFR.md")
        for dim in ("LAT", "AVL", "DUR", "CON", "ISO", "DET", "RES", "SEC"):
            self.assertIn(f"NFR-{dim}-", t)

    def test_mc007_mc050_compatibility_policy_matches_code(self):
        t = read("docs/COMPATIBILITY.md")
        self.assertIn(read("VERSION").strip(), t)
        for s in ("N-1", "EOL", "Critical"):
            self.assertIn(s, t)

    def test_mc011_traceability_covers_100_items(self):
        tr = json.loads(read("TRACEABILITY.json"))
        self.assertEqual(len(tr["checklist"]), 100)
        self.assertEqual(len({r["check_id"] for r in tr["checklist"]}), 100)

    def test_mc017_every_limit_is_documented(self):
        t = read("docs/LIMITS.md")
        for f in dataclasses.fields(resilience.Limits):
            self.assertIn(f.name, t)

    def test_mc019_mc028_mc029_mc053_blockers_are_declared_not_claimed(self):
        t = read("docs/INTEGRATION.md")
        for plane in ("PLN-02", "INV-49", "PLN-04", "PLN-06", "PLN-07"):
            self.assertIn(plane, t)
        self.assertIn("not integrated", t)
        self.assertIn("STATUS: specification only", read("wit/pk-runtime.wit"))

    def test_mc020_mc055_dependency_lock_is_honest(self):
        lock = json.loads(read("DEPENDENCIES.lock.json"))
        self.assertEqual(lock["runtime_dependencies"], [])
        pk = [d for d in lock["conformance_dependencies"] if d["name"] == "pk_core"][0]
        self.assertEqual(pk["status"], "UNPINNED")

    def test_mc026_bootstrap_and_package_manifest(self):
        self.assertIn('version = "' + read("VERSION").strip() + '"', read("pyproject.toml"))
        self.assertIn("dependencies = []", read("pyproject.toml"))
        self.assertTrue((PKG / "tools" / "bootstrap.sh").is_file())

    def test_mc027_threat_model_structure(self):
        t = read("docs/THREAT_MODEL.md")
        for s in ("## Assets", "## Trust boundaries", "Residual", "## Security-dependency outage matrix"):
            self.assertIn(s, t)
        self.assertGreaterEqual(len(re.findall(r"^\| T\d+ \|", t, re.M)), 10)

    def test_mc044_bench_gate_runs(self):
        proc = subprocess.run([sys.executable, str(PKG / "tools" / "bench.py"), "--n", "300"],
                              capture_output=True, text=True)
        rep = json.loads(proc.stdout)
        self.assertIn("governed.state_get", rep["results"])
        self.assertIn(rep["status"], {"PASS", "FAIL"})

    def test_mc048_evidence_tool_present(self):
        self.assertTrue((PKG / "tools" / "release_evidence.py").is_file())

    def test_mc049_mc051_operational_artifacts(self):
        for p in ("docs/operations/ROLLOUT.md", "docs/operations/RUNBOOKS.md", "docs/operations/GOVERNANCE.md",
                  "docs/operations/EXCEPTIONS.yaml", "docs/operations/BACKUP_RESTORE.md", "docs/FAILURE_CATALOG.md"):
            self.assertTrue((PKG / p).is_file(), p)
        self.assertIn("RB-01 Emergency disable", read("docs/operations/RUNBOOKS.md"))

    def test_mc054_master_md_absence_is_declared_not_claimed(self):
        if not (PKG / "MASTER.md").exists():
            self.assertNotRegex(read("README.md"), r"`MASTER\.md`.*(included|carried verbatim)")
            st = {i["id"]: i for i in json.loads(read("REMEDIATION_STATUS.json"))["items"]}
            self.assertEqual(st["MC-054"]["status"], "BLOCKED")

    def test_mc056_sbom_ci_notice(self):
        self.assertTrue((PKG / ".github" / "workflows" / "ci.yml").is_file())
        self.assertIn("LICENSE: NOT YET SELECTED", read("NOTICE"))
        bom = json.loads(read("SBOM.cdx.json"))
        self.assertEqual(bom["bomFormat"], "CycloneDX")

    def test_mc015_every_error_code_documented(self):
        docs = read("docs/SEMANTICS.md")
        self.assertEqual([c for c in envelope.CODES if f"`{c}`" not in docs], [])


if __name__ == "__main__":
    unittest.main()
