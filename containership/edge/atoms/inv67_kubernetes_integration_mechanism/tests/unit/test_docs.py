"""Machine checks over design/process artifacts so doc-only components have
automated, failing-when-wrong evidence (items 1, 2, 9, 23, 38, 46-47, 56-62)."""
import json
import re
import unittest

import _support as S

D = S.PKG_DIR / "docs"


class Docs(unittest.TestCase):
    def test_ownership_roles_defined(self):
        o = json.loads((D / "governance/ownership.json").read_text())
        self.assertEqual(set(o["roles"]), {"primary_owner", "secondary_owner", "platform_reviewer", "security_reviewer",
                                           "sre_operations", "downstream_owner", "release_authority"})
        md = (D / "OWNERSHIP.md").read_text()
        for h in ("Responsibility boundaries", "Approval rights", "escalation", "Ownership transfer"):
            self.assertIn(h, md)
        self.assertIn("/translator.py", (S.PKG_DIR / ".github/CODEOWNERS").read_text())

    def test_adr_sections(self):
        adr = (D / "architecture/ADR-001-integration-pattern.md").read_text()
        for h in ("## Decision", "## Host-Wasm lifecycle mapping", "## State ownership", "## Deletion semantics",
                  "## Upgrade strategy", "## Rejected alternatives", "## Trust boundaries", "flowchart"):
            self.assertIn(h, adr)
        self.assertIn(S.kube.GROUP, adr)

    def test_requirements_link_to_real_tests(self):
        reqs = json.loads((D / "requirements.json").read_text())["requirements"]
        ids = [r["id"] for r in reqs]
        self.assertEqual(len(ids), len(set(ids)))
        import unittest as u
        suite = u.defaultTestLoader.discover(str(S.PKG_DIR / "tests"), pattern="test_*.py", top_level_dir=str(S.PKG_DIR / "tests"))
        known = set()

        def walk(s):
            for t in s:
                walk(t) if isinstance(t, u.TestSuite) else known.add(t.id())
        walk(suite)
        for r in reqs:
            self.assertIn("SHALL", r["text"], r["id"])
            self.assertTrue(r["tests"], r["id"])
            for t in r["tests"]:
                self.assertIn(t, known, f"{r['id']} references unknown test {t}")
        md = (D / "REQUIREMENTS.md").read_text()
        for i in ids:
            self.assertIn(i, md)

    def test_threat_model_covers_mitigations(self):
        tm = (D / "architecture/THREAT_MODEL.md").read_text()
        rows = re.findall(r"^\| T(\d+) ", tm, re.M)
        self.assertGreaterEqual(len(rows), 12)
        for mod in ("adversarial", "fuzz", "audit", "failover"):
            self.assertIn(mod, tm)

    def test_slo_doc_matches_benchmark(self):
        slo = (D / "architecture/SLO.md").read_text()
        self.assertIn("< 5 ms", slo)
        base = json.loads((S.PKG_DIR / "evidence/perf_baseline.json").read_text())["results"]
        self.assertLess(base["translate_p99_ms"], 5.0)

    def test_telemetry_artifacts(self):
        alerts = (D / "telemetry/alerts.yaml").read_text()
        dash = json.loads((D / "telemetry/dashboard.json").read_text())
        h = S.Harness()
        h.kube.apply(S.workload()); h.kube.apply(S.workload(name="bad", hostNetwork=True))
        h.settle(3)
        emitted = set(re.findall(r"^(inv67_[a-z_]+?)(?:_bucket|_sum|_count)?[{ ]", h.ctrl.metrics.render(), re.M))
        used = set(re.findall(r"inv67_[a-z_]+", alerts + json.dumps(dash)))
        used = {re.sub(r"_(bucket|sum|count)$", "", m) for m in used}
        self.assertTrue(used, "no metrics referenced")
        self.assertEqual(used - emitted, set(), "alerts/dashboards reference metrics the controller never emits")

    def test_supported_versions_match_matrix(self):
        sv = (D / "SUPPORTED_VERSIONS.md").read_text()
        m = S.compat.SUPPORTED_MATRIX
        self.assertIn(f"{m['kubernetes'][0]}–{m['kubernetes'][-1]}", sv)
        self.assertIn(f"{m['python'][0]}–{m['python'][-1]}", sv)
        self.assertIn((S.PKG_DIR / "VERSION").read_text().strip()[:3], sv)

    def test_policies_present(self):
        for f, words in [("VULNERABILITY_POLICY.md", ["critical", "regression test"]),
                         ("INCIDENT_RESPONSE.md", ["SEV1", "freeze", "audit"]),
                         ("REVIEW_PROGRAM.md", ["quarterly", "Game day"])]:
            t = (D / f).read_text()
            for w in words:
                self.assertIn(w, t, f)

    def test_runbooks_complete(self):
        rb = {p.name for p in (D / "runbooks").glob("*.md")}
        self.assertTrue({"install.md", "upgrade-rollback.md", "emergency-freeze.md", "degraded-mode.md",
                         "orphan-cleanup.md", "backup-restore.md"} <= rb)
        for p in (D / "runbooks").glob("*.md"):
            for ref in re.findall(r"docs/runbooks/([a-z-]+\.md)", p.read_text()):
                self.assertIn(ref, rb)
        alerts = (D / "telemetry/alerts.yaml").read_text()
        for ref in re.findall(r"runbook: docs/runbooks/([a-z-]+\.md)", alerts):
            self.assertIn(ref, rb)

    def test_exceptions_ledger_valid(self):
        led = json.loads((D / "governance/exceptions.json").read_text())
        ids = [e["id"] for e in led["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        for e in led["entries"]:
            self.assertIn(e["kind"], ("blocker", "debt", "waiver"))
            if e["kind"] == "waiver":
                self.assertTrue(e["approver"] and e["expires"], "a waiver needs an approver and an expiry")
        reg = S.PKG.__name__
        import importlib
        R = importlib.import_module(reg + ".governance.registry")
        used = {x for c in R.components() for x in c["exceptions"]}
        self.assertTrue(used <= set(ids), used - set(ids))


if __name__ == "__main__":
    unittest.main()
