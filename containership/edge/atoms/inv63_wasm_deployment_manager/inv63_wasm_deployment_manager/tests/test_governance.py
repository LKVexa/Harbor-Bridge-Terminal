"""Governance, gate, bootstrap, ownership and doc-consistency tests
(C005, C009, C010, C020, C040, C090, C093, C096-C100)."""
import datetime as dt
import importlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
import unittest

from _support import PKG_DIR, covers, mod

evidence = mod("evidence")
gate = importlib.import_module(f"{PKG_DIR.name}.gate") if False else None
sys.path.insert(0, str(PKG_DIR))
import gate as gate_mod  # noqa: E402
sys.path.insert(0, str(PKG_DIR / "tools"))
import requirements_src  # noqa: E402

TODAY = dt.date(2026, 9, 23)


def green_root():
    """A copy of the package with synthetic, fully-approved evidence (tests the GO path only)."""
    tmp = pathlib.Path(tempfile.mkdtemp()) / PKG_DIR.name
    shutil.copytree(PKG_DIR, tmp, ignore=shutil.ignore_patterns("__pycache__", "evidence"))
    txt = (tmp / "OWNERS.yaml").read_text().replace("UNASSIGNED", "team-x").replace("review_date: team-x", "review_date: 2026-09-01")
    (tmp / "OWNERS.yaml").write_text(txt)
    pins = json.loads((tmp / "pins.json").read_text())
    for v in pins.values():
        if isinstance(v, dict):
            v["approved"] = True
            if v.get("version") == "UNPINNED":
                v["version"] = "1.0.0"
    (tmp / "pins.json").write_text(json.dumps(pins))
    th = json.loads((tmp / "perf/thresholds.json").read_text()); th["status"] = "APPROVED"
    (tmp / "perf/thresholds.json").write_text(json.dumps(th))
    rv = json.loads((tmp / "governance/REVIEWS.json").read_text())
    rv["completed"] = [{"kind": k, "date": "2026-09-20", "reviewer": "r"} for k in rv["cadence_days"]]
    (tmp / "governance/REVIEWS.json").write_text(json.dumps(rv))
    return tmp


def write_evidence(root, *, failed=0, skipped=0, partial=0, digest=None):
    d = digest or evidence.source_digest(root)
    (root / "evidence").mkdir(exist_ok=True)
    tests = {"test_component.X.test_a": {"status": "PASS", "cids": []}}
    (root / "evidence/test_results.json").write_text(json.dumps(
        {"source_digest": d, "total": 10, "passed": 10 - failed - skipped, "failed": failed, "skipped": skipped, "tests": tests}))
    (root / "AUDIT_RESULTS.json").write_text(json.dumps({"summary": {"SATISFIED": 100 - partial, "PARTIAL": partial, "MISSING": 0}}))
    (root / "evidence/audit_bundle.json").write_text(json.dumps({"source_digest": d, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                                               "audit_results_sha256": "x"}))
    (root / "perf/results.json").write_text(json.dumps({"source_digest": d, "gate_failures": []}))
    (root / "governance/APPROVALS.json").write_text(json.dumps({"approvals": [
        {"key": "revision-signoff", "role": "release-approver", "approver": "a", "revision": d,
         "expires": "2027-01-01", "signature": "ab"}]}))


class GateTest(unittest.TestCase):
    KEY = {"K": "11" * 32, "INV63_GATE_SIGNING_KEY": "env:K"}

    @covers(90, 100)
    def test_go_requires_everything_and_is_signed(self):
        root = green_root(); write_evidence(root)
        res = gate_mod.evaluate(root, TODAY, self.KEY)
        self.assertEqual(res["verdict"], "GO", res["criteria"])
        self.assertTrue(gate_mod.verify_signature(res))
        res["verdict"] = "NO_GO"
        self.assertFalse(gate_mod.verify_signature(res))            # tamper-evident

    @covers(90, 100, 20)
    def test_revision_signoff_required_for_go(self):
        root = green_root(); write_evidence(root)
        (root / "governance/APPROVALS.json").write_text(json.dumps({"approvals": []}))
        r = gate_mod.evaluate(root, TODAY, self.KEY)
        self.assertEqual([c for c in r["criteria"] if c["id"] == "G-02"][0]["status"], "BLOCKED")

    @covers(90, 100)
    def test_unsigned_can_never_promote(self):
        root = green_root(); write_evidence(root)
        self.assertEqual(gate_mod.evaluate(root, TODAY, {})["verdict"], "BLOCKED")

    @covers(90, 100)
    def test_skipped_or_failed_tests_block(self):
        root = green_root(); write_evidence(root, skipped=3)
        r = gate_mod.evaluate(root, TODAY, self.KEY)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual([c for c in r["criteria"] if c["id"] == "G-01"][0]["status"], "SKIPPED")
        write_evidence(root, failed=1)
        self.assertEqual(gate_mod.evaluate(root, TODAY, self.KEY)["verdict"], "NO_GO")

    @covers(90, 100)
    def test_stale_or_foreign_evidence_rejected(self):
        root = green_root(); write_evidence(root, digest="sha256:" + "0" * 64)
        r = gate_mod.evaluate(root, TODAY, self.KEY)
        self.assertEqual(r["verdict"], "NO_GO")
        write_evidence(root)
        (root / "README.md").write_text("changed after evidence was produced")
        self.assertEqual(gate_mod.evaluate(root, TODAY, self.KEY)["verdict"], "NO_GO")

    @covers(90, 100)
    def test_missing_pk_core_is_blocked_not_skipped(self):
        root = green_root(); write_evidence(root)
        tr = json.loads((root / "evidence/test_results.json").read_text()); tr["tests"] = {}
        (root / "evidence/test_results.json").write_text(json.dumps(tr))
        r = gate_mod.evaluate(root, TODAY, self.KEY)
        self.assertEqual([c for c in r["criteria"] if c["id"] == "G-09"][0]["status"], "BLOCKED")
        self.assertEqual(r["verdict"], "BLOCKED")

    @covers(99, 100)
    def test_waivers_expiry_and_conditional_go(self):
        root = green_root(); write_evidence(root, partial=2)
        w = {"waivers": [{"id": "W-1", "criterion": "G-02", "risk_owner": "o", "compensating_control": "c", "expires": "2026-10-01"}]}
        (root / "governance/WAIVERS.json").write_text(json.dumps(w))
        write_evidence(root, partial=2)
        self.assertEqual(gate_mod.evaluate(root, TODAY, self.KEY)["verdict"], "CONDITIONAL_GO")
        self.assertEqual(gate_mod.evaluate(root, dt.date(2026, 10, 2), self.KEY)["verdict"], "NO_GO")
        w["waivers"][0]["risk_owner"] = ""
        (root / "governance/WAIVERS.json").write_text(json.dumps(w)); write_evidence(root, partial=2)
        self.assertEqual(gate_mod.evaluate(root, TODAY, self.KEY)["verdict"], "NO_GO")

    @covers(9, 100)
    def test_unassigned_or_stale_ownership_blocks(self):
        root = green_root()
        (root / "OWNERS.yaml").write_text((root / "OWNERS.yaml").read_text().replace("security_contact: team-x", "security_contact: UNASSIGNED"))
        write_evidence(root)
        self.assertEqual(gate_mod.check_owners(root, TODAY)[0], "BLOCKED")
        self.assertEqual(gate_mod.check_owners(root, dt.date(2027, 6, 1))[0], "BLOCKED")
        root2 = green_root()
        self.assertEqual(gate_mod.check_owners(root2, dt.date(2027, 6, 1))[0], "FAIL")

    @covers(98)
    def test_overdue_reviews_block(self):
        root = green_root()
        self.assertEqual(gate_mod.check_reviews(root, TODAY)[0], "PASS")
        self.assertEqual(gate_mod.check_reviews(root, dt.date(2026, 11, 30))[0], "BLOCKED")   # dependency: 30d

    @covers(100)
    def test_real_repository_is_not_go(self):
        """Honesty guard: with pending external evidence the real package must not certify."""
        r = gate_mod.evaluate(PKG_DIR, TODAY, {})
        self.assertIn(r["verdict"], ("BLOCKED", "NO_GO"))


class OwnershipAndDocsTest(unittest.TestCase):
    @covers(9)
    def test_owners_manifest_covers_raci_and_escalation(self):
        o = (PKG_DIR / "OWNERS.yaml").read_text()
        for k in ("deploy", "rollback", "emergency_disable", "schema_change", "wadm_upgrade", "security_incident",
                  "production_exception", "sev1", "security"):
            self.assertIn(k, o)
        co = (PKG_DIR / "CODEOWNERS").read_text()
        for path in ("/security.py", "/schemas/", "/store.py", "/release/"):
            self.assertIn(path, co)

    @covers(5, 10, 20, 96, 97)
    def test_every_referenced_artifact_exists(self):
        audit = importlib.import_module("audit")
        missing = []
        for cid, (_, impl, docs, _) in requirements_src.R.items():
            missing += [f"{cid}:{r}" for r in impl + docs if not audit._ref_ok(r)]
        self.assertEqual(missing, [])

    @covers(5, 10)
    def test_architecture_docs_carry_governance_header(self):
        for p in (PKG_DIR / "docs/architecture").glob("*.md"):
            t = p.read_text()
            for field in ("Owner", "Reviewers", "Revision", "Approval"):
                self.assertIn(field, t, p.name)

    @covers(5)
    def test_assumption_catalogue_matches_preflight(self):
        pf = mod("preflight")
        doc = (PKG_DIR / "docs/architecture/ASSUMPTIONS.md").read_text()
        ids = {c.id for c in pf.run(hosts={"h": "z"}, state_dir=tempfile.mkdtemp())}
        for i in ids:
            self.assertIn(i, doc)

    @covers(96, 97, 92, 95)
    def test_runbooks_present_and_marked_unexercised(self):
        for name in ("DAY0_BOOTSTRAP", "DAY1_DEPLOY", "DAY2_OPERATIONS", "CANARY_ROLLBACK", "BACKUP_RESTORE", "INCIDENT"):
            t = (PKG_DIR / f"ops/runbooks/{name}.md").read_text()
            self.assertIn("Last exercised", t, name)
        self.assertIn("SEV1", (PKG_DIR / "ops/runbooks/INCIDENT.md").read_text())

    @covers(93)
    def test_compatibility_matrix_matches_pins(self):
        cm = (PKG_DIR / "governance/COMPATIBILITY_MATRIX.md").read_text()
        pins = json.loads((PKG_DIR / "pins.json").read_text())
        self.assertIn(pins["cryptography"]["version"], cm)
        for name, majors in mod("schema").SUPPORTED.items():
            self.assertIn(name, cm)


class BootstrapTest(unittest.TestCase):
    @covers(40)
    def test_deterministic_bootstrap_and_fail_closed(self):
        sys.path.insert(0, str(PKG_DIR / "tools"))
        import bootstrap
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "hosts.json").write_text(json.dumps({"h1": "z1", "h2": "z2"}))
        (tmp / "tk").write_text(json.dumps({"k1": "aa" * 32}))
        (tmp / "dk").write_text("bb" * 32)
        cfgdir = tmp / "cfg"; shutil.copytree(PKG_DIR / "deploy/config", cfgdir)
        base = json.loads((cfgdir / "base.json").read_text())
        base["secret_refs"] = {"token_keys": f"file:{tmp/'tk'}", "data_key": f"file:{tmp/'dk'}"}
        (cfgdir / "base.json").write_text(json.dumps(base))
        args = ["--state-dir", str(tmp / "state"), "--config-dir", str(cfgdir), "--env", "prod", "--site", "dc-1",
                "--hosts", str(tmp / "hosts.json"), "--reference-time", str(time.time())]
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            first, second = bootstrap.main(args, env={}), bootstrap.main(args, env={})
        self.assertEqual((first, second), (0, 0))                              # idempotent re-run
        self.assertEqual(oct(os.stat(tmp / "state").st_mode & 0o777), "0o700")
        bad = list(args); bad[-1] = str(time.time() - 7200)                  # clock skew -> fail closed
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            skew = bootstrap.main(bad, env={})
            (tmp / "dk").unlink()
            nosecret = bootstrap.main(args, env={})                            # missing secret -> fail closed
        self.assertEqual((skew, nosecret), (3, 3))


if __name__ == "__main__":
    unittest.main()
