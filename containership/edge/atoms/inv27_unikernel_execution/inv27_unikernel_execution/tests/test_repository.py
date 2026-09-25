"""Repository integrity: MASTER.md, vendored pk_core, fixtures, docs, governance artifacts, evidence
generators, packaging, lint/deps/coverage tools (MC-011, 015, 021, 022, 034, 036, 039, 042, 060, 064,
077, 078, 088..094)."""
import hashlib
import importlib
import json
import re
import subprocess
import sys
import unittest

from harness import PKG, PKGNAME, image

tools = {n: importlib.import_module(f"{PKGNAME}.tools.{n}") for n in
         ("rtm", "mc_status", "governance_check", "lint", "deps_check", "sbom", "manifest", "perf_gate")}


class Artifacts(unittest.TestCase):
    def test_master_md_restored_and_matches_checklist(self):
        text = (PKG / "MASTER.md").read_text(encoding="utf-8")
        ids = {i["check_id"] for i in json.loads((PKG / "CHECKLIST.json").read_text())["items"]}
        self.assertEqual({m for m in re.findall(r"INV-27-C\d{3}", text)} & ids, ids)

    def test_vendored_pk_core_is_unmodified(self):
        prov = json.loads((PKG / "_vendor" / "PK_CORE_PROVENANCE.json").read_text())
        self.assertFalse(prov["modified"])
        for f, h in prov["files_sha256"].items():
            self.assertEqual(hashlib.sha256((PKG / "_vendor" / "pk_core" / f).read_bytes()).hexdigest(), h, f)

    def test_fixture_bytes_pinned(self):
        fx = json.loads((PKG / "tests" / "fixtures" / "FIXTURES.json").read_text())
        for f, h in fx["sha256"].items():
            self.assertEqual(hashlib.sha256(image(f)).hexdigest(), h, f)

    def test_required_documents_exist_and_are_linked(self):
        need = ["docs/ADR-0001-unikernel-seal-verification.md", "docs/SPEC.md", "docs/THREAT_MODEL.md",
                "docs/FORMATS.md", "docs/VERSIONING.md", "docs/CAPACITY.md", "docs/DISCONNECTED.md",
                "docs/INTERFACES.md", "docs/COPY_ANALYSIS.md", "docs/LIFECYCLE.md", "ops/OWNERS.md", "ops/RUNBOOK.md",
                "ops/INCIDENT.md", "ops/BACKUP_RESTORE.md", "ops/ROLLOUT.md", "ops/BOUNDARIES.md", "SECURITY.md",
                "CONTRIBUTING.md", "NOTICE", "THIRD-PARTY-NOTICES.md", "pyproject.toml", "requirements.lock",
                ".github/workflows/ci.yml", ".github/CODEOWNERS"]
        for n in need:
            self.assertTrue((PKG / n).is_file(), n)
        self.assertIn("Proposed", (PKG / "docs/ADR-0001-unikernel-seal-verification.md").read_text())

    def test_threat_model_names_every_threat_in_the_contract_and_the_residual(self):
        tm = (PKG / "docs/THREAT_MODEL.md").read_text()
        self.assertIn("T-11", tm)
        self.assertIn("Residual", tm)

    def test_policy_json_documents_are_well_formed(self):
        for n in ("OWNERS", "WAIVERS", "REVIEWS", "EOL", "TELEMETRY_POLICY", "alerts", "dashboards", "PERF_THRESHOLDS",
                  "COMPATIBILITY_MATRIX", "IDENTITY_INVENTORY", "ERROR_CODES", "MC_STATUS_SOURCE", "RTM_BASELINE"):
            json.loads((PKG / "ops" / f"{n}.json").read_text())
        alerts = json.loads((PKG / "ops/alerts.json").read_text())["alerts"]
        for a in alerts:
            self.assertTrue((PKG / a["runbook"].split("#")[0]).exists())

    def test_version_synchronised(self):
        v = (PKG / "VERSION").read_text().strip()
        self.assertEqual(v, "4.3.0")
        self.assertIn(f'version = "{v}"', (PKG / "pyproject.toml").read_text())
        self.assertIn(f'__version__ = "{v}"', (PKG / "__init__.py").read_text())


class Tools(unittest.TestCase):
    def test_rtm_and_mc_registry_validate(self):
        doc, errs = tools["rtm"].build()
        self.assertEqual(errs, [])
        self.assertEqual(len(doc["rows"]), 100)
        src = json.loads((PKG / "ops/MC_STATUS_SOURCE.json").read_text())
        self.assertEqual(tools["mc_status"].validate(src, json.loads((PKG / "ops/WAIVERS.json").read_text())), [])

    def test_mc_registry_rejects_unbacked_claims(self):
        src = json.loads((PKG / "ops/MC_STATUS_SOURCE.json").read_text())
        w = json.loads((PKG / "ops/WAIVERS.json").read_text())
        src["components"]["MC-007"]["status"] = "verified_local"          # still has blockers
        src["components"]["MC-004"]["tests"] = []
        src["components"]["MC-006"]["implementation"].append("nope.py::Ghost")
        src["components"]["MC-093"]["blockers"] = ["W-NOT-A-WAIVER"]
        errs = tools["mc_status"].validate(src, w)
        self.assertEqual(len(errs), 4, errs)

    def test_checkbox_rule_blocks_human_items(self):
        boxes = tools["mc_status"].parse_checklist()
        self.assertEqual(sum(len(v) for v in boxes.values()), 1883)
        src = json.loads((PKG / "ops/MC_STATUS_SOURCE.json").read_text())
        rows = tools["mc_status"].classify(src, boxes)
        gate_rows = [r for r in rows if "production-gate result" in r["text"]]
        self.assertEqual(len(gate_rows), 94)
        self.assertTrue(all(r["status"] == "blocked" for r in gate_rows))
        review = [r for r in rows if "record approval identity/date" in r["text"] or r["text"].startswith("Review ")]
        self.assertTrue(review and all(r["status"] == "blocked" for r in review))

    def test_governance_fails_on_placeholders(self):
        import datetime as dt
        r = tools["governance_check"].check(dt.date(2026, 9, 23))
        self.assertFalse(r["pass"])
        self.assertTrue(any("unassigned" in x for x in r["owners"]))

    def test_lint_and_deps_clean_and_lint_catches_bad_code(self):
        self.assertEqual([f for rel in tools["deps_check"].runtime_modules() for f in tools["lint"].lint_file(rel)], [])
        self.assertEqual(tools["deps_check"].check(), [])
        bad = PKG / "tests" / "_lint_probe.py"
        bad.write_text("import pickle, subprocess, os\nassert True\nsubprocess.run('ls', shell=True)\nos.system('x')\n"
                       "try:\n    eval('1')\nexcept:\n    pass\n")
        try:
            self.assertGreaterEqual(len(tools["lint"].lint_file("tests/_lint_probe.py")), 6)
        finally:
            bad.unlink()

    def test_sbom_lists_vendored_and_optional(self):
        s = tools["sbom"].build()
        names = {c["name"] for c in s["components"]}
        self.assertEqual(names, {"pk_core", "cryptography", "CPython"})

    def test_perf_gate_refuses_quick_and_unapproved(self):
        thr = json.loads((PKG / "ops/PERF_THRESHOLDS.json").read_text())
        res = {"quick": True, "results": {k: {"p99_ms": 1} for k in thr["thresholds"]}}
        self.assertEqual(tools["perf_gate"].evaluate(res, thr)["verdict"], "FAIL")
        res["quick"] = False
        thr["reference_hardware"] = "ref-1"
        self.assertEqual(tools["perf_gate"].evaluate(res, thr)["verdict"], "PASS")

    def test_perf_results_recorded_and_copy_analysis_holds(self):
        r = json.loads((PKG / "evidence/PERF_RESULTS.json").read_text())
        self.assertFalse(r["quick"])
        self.assertEqual(r["results"]["copies"]["ImageBlob.of(bytes) copies"], 0)
        self.assertLess(r["results"]["admit_uk_good"]["p99_ms"], 100)

    def test_ci_workflow_runs_both_modes_and_gate(self):
        y = (PKG / ".github/workflows/ci.yml").read_text()
        for s in ("run_all.py", "-O", "release_gate", "coverage_check", "lint", "INV27_FUZZ_ITERS"):
            self.assertIn(s, y)

    def test_clean_checkout_has_no_stray_artifacts(self):
        stray = [p for p in PKG.rglob("*") if p.suffix in (".pyc", ".pem", ".key") or p.name in (".env",)]
        self.assertEqual(stray, [])


if __name__ == "__main__":
    unittest.main()
