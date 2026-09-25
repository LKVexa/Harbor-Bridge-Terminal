"""Governance, documentation-drift, inventory, plan-hygiene and gate tests."""
import datetime as dt
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import tempfile
import unittest

from _harness import FAKE_ARTIFACTS

from inv71_heavy_agent_sandbox.control.config import merge
from inv71_heavy_agent_sandbox.control.runtime_plan import plan_session

PKG = pathlib.Path(__file__).resolve().parents[1]


def load(rel):
    spec = importlib.util.spec_from_file_location(rel.replace("/", "_"), PKG / rel)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


class DocDriftTest(unittest.TestCase):
    """[C020][C021-IMP-05][C010-IMP-05] generated docs match code; ADR cannot silently become Accepted."""

    def test_generated_docs_current(self):
        rd = load("tools/render_docs.py")
        for name, text in rd.render().items():
            self.assertEqual((PKG / "docs" / "generated" / name).read_text(encoding="utf-8"), text,
                             f"{name} is stale: run tools/render_docs.py")

    def test_adr_status_needs_approval_records(self):
        adr = (PKG / "docs" / "ADR-0001-heavy-agent-sandbox.md").read_text()
        status = re.search(r"\*\*Status:\*\* (\w+)", adr).group(1)
        approvals = [json.loads(p.read_text()) for p in (PKG / "governance" / "approvals").glob("*.json")]
        adr_approvals = {a["role"] for a in approvals if a.get("subject") == "adr" and a.get("decision") == "approve"}
        if status != "Proposed":
            self.assertTrue({"service_owner", "network_security_owner", "sre_oncall_owner", "release_authority",
                             "microvm_runtime_owner"} <= adr_approvals, "ADR Accepted without approval records")


class InventoryTest(unittest.TestCase):
    """[INV71-X002][C020] documents never claim a bundled file that is absent; evidence paths exist."""

    def test_backticked_paths_exist(self):
        missing = []
        for doc in list((PKG / "docs").rglob("*.md")) + [PKG / "README.md", PKG / "MISSING_COMPONENTS.md",
                                                           PKG / "LICENSE_STATUS.md", PKG / "THIRD-PARTY-NOTICES.md"]:
            for ref in re.findall(r"`((?:docs|governance|control|tools|tests|schemas|fixtures|artifacts|deps)/[A-Za-z0-9_./-]+\.(?:md|py|json|yaml|jsonl))`", doc.read_text()):
                if not (PKG / ref).exists() and "*" not in ref:
                    missing.append(f"{doc.name}: {ref}")
        self.assertEqual(missing, [])

    def test_master_md_not_claimed(self):
        self.assertFalse((PKG / "MASTER.md").exists())
        readme = (PKG / "README.md").read_text()
        self.assertNotRegex(readme, r"(?i)(contains|includes|ships|bundles)\s+`?MASTER\.md")

    def test_checklist_status_complete_and_cited_paths_exist(self):
        cs = load("governance/checklist_status.py")
        text = (PKG / "governance" / "INV71_v4.2.0_PRODUCTION_REMEDIATION_MASTER_CHECKLIST.md").read_text()
        for ctl in sorted(set(re.findall(r"\*\*(?:INV-71-)?(C\d{3}|INV71-X\d{3})-IMP-\d{2}\*\*", text))):
            n = len(re.findall(rf"\*\*(?:INV-71-)?{ctl}-IMP-\d{{2}}\*\*", text))
            self.assertEqual(len(cs.IMP[ctl]), n, ctl)
            for s in cs.IMP[ctl]:
                code, _, note = s.partition(":")
                self.assertIn(code, cs.STATUS, ctl)
                if code != "I":
                    self.assertTrue(note.strip(), f"{ctl}: {code} needs a note")
            for rel in cs.E[ctl]:
                if not rel.startswith("evidence/"):
                    self.assertTrue((PKG / rel).exists(), f"{ctl}: {rel}")

    def test_requirement_tests_exist(self):
        req = json.loads((PKG / "governance" / "requirements.json").read_text())
        for r in req["requirements"]:
            for t in r["tests"]:
                mod, cls, meth = t.split(".")
                src = (PKG / "tests" / f"{mod}.py").read_text()
                self.assertIn(f"class {cls}", src, t)
                self.assertIn(f"def {meth}", src, t)


class PlanHygieneTest(unittest.TestCase):
    """[C043][C039][C046][C021] no secrets in argv/config; no console/vsock; locked fields locked."""

    def test_no_secret_material_or_debug_channels(self):
        p = plan_session("s1", merge({}), FAKE_ARTIFACTS)
        blob = json.dumps(p.vm_config) + " ".join(p.jailer_argv)
        for word in ("password", "secret", "token", "BEGIN PRIVATE", "AWS_", "--no-seccomp"):
            self.assertNotIn(word, blob)
        self.assertNotIn("vsock", p.vm_config)
        self.assertIn("console=off", p.vm_config["boot-source"]["boot_args"])
        self.assertEqual([d for d in p.vm_config["drives"] if d["is_root_device"]][0]["is_read_only"], True)


class GateTest(unittest.TestCase):
    """[C100][C090][C099] gate is fail-closed and detects tampering."""

    def make_tree(self):
        d = pathlib.Path(tempfile.mkdtemp())
        for sub in ("evidence/performance", "evidence/security", "governance/approvals", "artifacts"):
            (d / sub).mkdir(parents=True)
        w = lambda rel, obj: (d / rel).write_text(json.dumps(obj))
        w("evidence/tests.json", {"counts": {"PASS": 1, "FAIL": 0, "ERROR": 0, "NOT_RUN": 0}})
        w("AUDIT_AFTER.json", {"controls": [{"check_id": "INV-71-C001", "status": "EVIDENCED"}]})
        w("governance/waivers.json", {"waivers": []})
        w("evidence/checklist_execution.json", {"items": [{"id": "x", "status": "IMPLEMENTED_UNREVIEWED"}]})
        w("evidence/traceability.json", {"problems": []})
        w("artifacts/approved-manifest.json", {"artifacts": {"firecracker": {"version": "1.0.0", "sha256": "a" * 64}}, "signature": "sig"})
        w("evidence/pk_core_probe.json", {"status": "VERIFIED"})
        w("evidence/performance/bench.json", {"gate": {"verdict": "PASS"}})
        w("evidence/security/fuzz.json", {"total_findings": 0})
        w("governance/raci.json", {"roles": {"service_owner": {"primary": "p"}}})
        w("evidence/qualification.json", {"verdict": "ADMIT"})
        (d / "LICENSE").write_text("x")
        return d

    def seal(self, d, signature="sig"):
        files = {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in d.rglob("*") if p.is_file() and p.name not in ("release-manifest.json", "gate-result.json")}
        tree = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        for role in ("service_owner", "network_security_owner", "sre_oncall_owner", "release_authority"):
            (d / "governance" / "approvals" / f"{role}.json").write_text(json.dumps(
                {"subject": "release", "subject_digest": tree, "role": role, "decision": "approve"}))
        files = {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in d.rglob("*") if p.is_file() and p.name not in ("release-manifest.json", "gate-result.json")}
        (d / "evidence" / "release-manifest.json").write_text(json.dumps({"files": files, "tree_sha256": tree, "approval_subject_sha256": tree, "signature": signature}))

    def test_complete_synthetic_tree_is_go(self):
        g = load("tools/production_gate.py")
        d = self.make_tree(); self.seal(d)
        r = g.evaluate(d)
        self.assertEqual(r["verdict"], "GO", r["blockers"])

    def test_each_missing_piece_blocks(self):
        g = load("tools/production_gate.py")
        mutations = [("evidence/pk_core_probe.json", {"status": "NOT_RUN"}),
                     ("evidence/performance/bench.json", {"gate": {"verdict": "INCOMPLETE"}}),
                     ("AUDIT_AFTER.json", {"controls": [{"check_id": "INV-71-C001", "status": "PARTIAL"}]}),
                     ("evidence/checklist_execution.json", {"items": [{"id": "x", "status": "BLOCKED"}]}),
                     ("governance/raci.json", {"roles": {"service_owner": {"primary": "UNASSIGNED"}}}),
                     ("artifacts/approved-manifest.json", {"artifacts": {"firecracker": {"version": "UNPINNED", "sha256": "UNPINNED"}}, "signature": "s"}),
                     ("evidence/qualification.json", {"verdict": "REJECT"})]
        for rel, obj in mutations:
            d = self.make_tree()
            (d / rel).write_text(json.dumps(obj))
            self.seal(d)
            self.assertEqual(g.evaluate(d)["verdict"], "NO_GO", rel)
        d = self.make_tree(); self.seal(d, signature=None)
        self.assertEqual(g.evaluate(d)["verdict"], "NO_GO")

    def test_waiver_rules(self):
        g = load("tools/production_gate.py")
        d = self.make_tree()
        (d / "AUDIT_AFTER.json").write_text(json.dumps({"controls": [{"check_id": "INV-71-C050", "status": "PARTIAL"}]}))
        ok = {"id": "WVR-001", "owner": "o", "approved_by": ["a", "b"], "expires": "2099-01-01", "scope": ["INV-71-C050"]}
        for w, want in ((ok, "GO"), ({**ok, "approved_by": ["o", "b"]}, "NO_GO"), ({**ok, "approved_by": ["x", "x"]}, "NO_GO"), ({**ok, "owner": ""}, "NO_GO"),
                        ({**ok, "expires": "2000-01-01"}, "NO_GO")):
            (d / "governance" / "waivers.json").write_text(json.dumps({"waivers": [w]}))
            self.seal(d)
            self.assertEqual(g.evaluate(d, today=dt.date(2026, 9, 23))["verdict"], want, w)

    def test_tamper_is_evidence_invalid(self):
        g = load("tools/production_gate.py")
        d = self.make_tree(); self.seal(d)
        (d / "evidence" / "tests.json").write_text(json.dumps({"counts": {"PASS": 9, "FAIL": 0, "ERROR": 0, "NOT_RUN": 0}}))
        self.assertEqual(g.evaluate(d)["verdict"], "EVIDENCE_INVALID")
        d = self.make_tree(); self.seal(d)
        (d / "smuggled.py").write_text("x")
        self.assertEqual(g.evaluate(d)["verdict"], "EVIDENCE_INVALID")


if __name__ == "__main__":
    unittest.main()
