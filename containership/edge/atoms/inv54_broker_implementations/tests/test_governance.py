"""Repository-governance checks (components 01, 11, 16-18, 34, 35, 45, 46, 81, 100)."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tomllib
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
DOCS = PKG / "docs"


class Governance(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, cwd=PKG.parent)

    def test_c01_every_path_owned(self):
        r = self.run_tool(str(PKG / "tools" / "check_owners.py"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_c18_schemas_have_no_drift(self):
        r = self.run_tool(str(PKG / "tools" / "gen_schemas.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        for f in (PKG / "schemas").glob("*.json"):
            json.loads(f.read_text())

    def test_c34_pyproject_metadata(self):
        py = tomllib.loads((PKG / "pyproject.toml").read_text())
        self.assertEqual(py["project"]["version"], (PKG / "VERSION").read_text().strip())
        self.assertEqual(py["project"]["dependencies"], [])
        self.assertIn("requires-python", py["project"])

    def test_c35_c17_extras_are_exactly_pinned_and_match_lock(self):
        py = tomllib.loads((PKG / "pyproject.toml").read_text())
        lock = {l.split()[0] for l in (PKG / "requirements-lock.txt").read_text().splitlines()
                if l and not l.startswith("#")}
        for extra, reqs in py["project"]["optional-dependencies"].items():
            for r in reqs:
                self.assertIn("==", r, r)
                self.assertIn(r, lock, r)

    def test_c02_c03_c36_normative_docs_present_with_ids(self):
        need = {"adr/ADR-0001-broker-technologies.md": "Status:", "REQUIREMENTS.md": "REQ-CTX-FAR-EDGE",
                "THREAT_MODEL.md": "T14", "FAILURE_SEMANTICS.md": "retryable", "OWNERSHIP.md": "Escalation",
                "PRECEDENCE.md": "Security", "OFFLINE.md": "idempotency", "RUNBOOKS.md": "Day 0",
                "INCIDENT_RESPONSE.md": "Contain", "WAIVERS.md": "TD-01"}
        for f, marker in need.items():
            self.assertIn(marker, (DOCS / f).read_text(), f)

    def test_c45_c46_security_policy_and_license_status_explicit(self):
        self.assertIn("vulnerability", (PKG / "SECURITY.md").read_text().lower())
        self.assertIn("NOT YET DECIDED", (PKG / "LICENSE-PENDING.md").read_text())

    def test_c81_alert_rules_reference_emitted_metrics(self):
        import re
        emitted = {"published", "appended", "replays", "consumer_lag", "authz_denied", "backlog_rejects",
                   "lifecycle_transitions"}
        text = (PKG / "ops" / "alerts.yaml").read_text() + (PKG / "ops" / "dashboard.json").read_text()
        used = set(re.findall(r"inv54_([a-z_]+)", text))
        self.assertTrue(used <= emitted, used - emitted)

    def test_c100_ci_workflow_runs_every_gate(self):
        ci = (PKG / ".github" / "workflows" / "ci.yml").read_text()
        for step in ("gen_schemas.py --check", "check_owners.py", "unittest discover", "harness.py", "--gate",
                     "gen_evidence.py", "certify_providers.py"):
            self.assertIn(step, ci)


if __name__ == "__main__":
    unittest.main()
