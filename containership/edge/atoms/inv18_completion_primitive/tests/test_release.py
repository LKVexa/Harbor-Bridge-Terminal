"""Governance, requirements, RTM, release gate, integrity, bootstrap and runbooks
(C001-C011, C020, C031, C032, C040, C045, C090, C092-C100)."""
import ast
import copy
import datetime
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

from _util import m, PKG_DIR, ROOT

certify = m("certify")
tv = m("tools_verify")


def _contract_literals():
    """Extract the Contract(...) keyword literals from contract.py without importing pk_core."""
    tree = ast.parse((PKG_DIR / "contract.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Contract":
            out = {}
            for kw in node.keywords:
                try:
                    out[kw.arg] = ast.literal_eval(kw.value)
                except ValueError:
                    out[kw.arg] = ast.unparse(kw.value)
            return out
    raise AssertionError("Contract(...) not found")


def _fake_results(status="pass", extra=()):
    req = json.loads((PKG_DIR / "REQUIREMENTS.json").read_text())
    ids = [s["id"] for s in req["shall"]] + [c["id"] for c in req["checklist"]]
    tests = [{"id": f"tests/test_fake.py::T::t{i}", "status": status, "tags": [rid], "mandatory": True,
              "detail": None} for i, rid in enumerate(ids)]
    tests += list(extra)
    return {"tests": tests, "counts": {status: len(tests)}, "environment": {"python": "x"}}


class ContractDocTest(unittest.TestCase):
    def test_scope_documented_consistently(self):
        """REQ: C001 C002 C007 C008"""
        c = _contract_literals()
        readme = (PKG_DIR / "README.md").read_text()
        self.assertIn(c["responsibility"], readme)
        for item in c["owns"] + c["not_owns"] + c["non_goals"]:
            self.assertIn(item, readme)
        self.assertEqual(len(c["mandatory"]), 5)
        self.assertTrue(set(c["mandatory"]).isdisjoint(c["optional"]))
        self.assertIn("unsupported", (PKG_DIR / "docs/ARCHITECTURE.md").read_text().lower())

    def test_dependencies_truth_assumptions_boundaries(self):
        """REQ: C003 C004 C005 C006"""
        c = _contract_literals()
        deps = c["dependencies"]
        for layer in ("INV-15", "INV-12", "INV-17", "INV-20", "INV-16"):
            self.assertIn(layer, deps)
            self.assertIn(layer, (PKG_DIR / "docs/INTERFACES.md").read_text())
        self.assertIn("immutable", c["source_of_truth"])
        self.assertGreaterEqual(len(c["assumptions"]), 3)
        self.assertEqual(set(c["boundaries"]), {"tenant", "environment", "site", "workload"})
        arch = (PKG_DIR / "docs/ARCHITECTURE.md").read_text()
        for word in ("clock", "network", "storage", "scheduler"):
            self.assertIn(word, arch)


class GovernanceTest(unittest.TestCase):
    def test_owners_file_complete_or_gate_blocks(self):
        """REQ: C009"""
        o = json.loads((PKG_DIR / "governance/OWNERS.json").read_text())
        for r in o["required_roles"]:
            self.assertIn(r, o["roles"])
        self.assertEqual([e["tier"] for e in o["escalation"]], [1, 2, 3, 4])
        for trig in ("concurrency_violation", "schema_incompatibility", "security_issue", "slo_breach",
                     "corrupted_evidence", "release_gate_failure"):
            self.assertIn(trig, o["escalation_triggers"])
        for area in ("future.py", "tests/", "config/", "auth.py", "docs/OPERATIONS.md", "conformance/"):
            self.assertIn(area, o["areas"])
        self.assertTrue((PKG_DIR / "CODEOWNERS").exists())
        vacant = [r for r in o["required_roles"] if o["roles"][r]["team"] == "VACANT"]
        res = certify.resolve_blocker("OWNERS_VACANT", {})
        self.assertEqual(res is None, not vacant)
        if vacant:
            self.assertEqual(res[0], "BLOCKED")

    def test_adr_complete_and_gated(self):
        """REQ: C010"""
        adr = (PKG_DIR / "docs/adr/ADR-001-completion-primitive.md").read_text()
        for sec in ("Problem", "Decision", "Rejected alternatives", "Trade-offs", "Compatibility", "Consequences",
                    "queue.Queue", "Event", "stream-of-one", "callback", "Security", "Performance", "Operations",
                    "Next review", "Supersedes"):
            self.assertIn(sec, adr)
        accepted = "| Status | **ACCEPTED**" in adr
        self.assertEqual(certify.resolve_blocker("ADR_NOT_APPROVED", {}) is None, accepted)

    def test_requirements_source(self):
        """REQ: C011 C020"""
        req = json.loads((PKG_DIR / "REQUIREMENTS.json").read_text())
        ids = [s["id"] for s in req["shall"]]
        self.assertEqual(len(ids), len(set(ids)))
        for s in req["shall"]:
            self.assertRegex(s["id"], r"^INV18-(FR|NFR|SEC|OPS|CMP)-\d{3}$")
            self.assertRegex(s["text"], r"\bSHALL\b")
            self.assertIn(s["class"], ("functional", "security", "performance", "operational", "compatibility"))
            self.assertTrue(s["verification"])
        ck = [c["id"] for c in req["checklist"]]
        self.assertEqual(ck, [f"INV-18-C{i:03d}" for i in range(1, 101)])
        src = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        self.assertEqual([i["requirement"] for i in src["items"]], [c["requirement"] for c in req["checklist"]])

    def test_waiver_register(self):
        """REQ: C099"""
        w = json.loads((PKG_DIR / "governance/WAIVERS.json").read_text())
        ids = set()
        for e in w["entries"]:
            for f in ("id", "requirement", "rationale", "risk", "compensating_controls", "owner",
                      "approval_authority", "created", "expires", "remediation", "target_release"):
                self.assertIn(f, e)
            datetime.date.fromisoformat(e["expires"])
            self.assertNotIn(e["id"], ids); ids.add(e["id"])
        self.assertTrue(w["deprecations"])

    def test_review_register(self):
        """REQ: C098"""
        r = json.loads((PKG_DIR / "governance/REVIEWS.json").read_text())
        for c in r["critical"]:
            self.assertIn(c, r["cadence_days"])
        for k in ("ownership_access", "capabilities", "threat_model", "dependencies_sbom", "vulnerabilities",
                  "config_defaults", "compat_matrix", "performance_baseline", "slo_history", "incidents",
                  "waivers_debt", "architecture_assumptions"):
            self.assertIn(k, r["cadence_days"])

    def test_operations_policies_present(self):
        """REQ: C091 C092 C093 C094 C095 C096 C097"""
        ops = " ".join((PKG_DIR / "docs/OPERATIONS.md").read_text().split())
        for needle in ("SLO policy", "error budget", "burn", "Canary", "Emergency disable", "COMPAT_MATRIX",
                       "Patch SLAs", "EOL", "Backport", "not reconstructable", "RPO", "RB-D0", "RB-D1", "RB-D2",
                       "SEV1", "incident commander", "Preserve evidence", "post-incident review", "Tabletop"):
            self.assertIn(needle.lower(), ops.lower())
        cm = json.loads((PKG_DIR / "conformance/COMPAT_MATRIX.json").read_text())
        for k in ("releases", "python", "pk_core", "contracts", "adjacent", "declared_platforms"):
            self.assertIn(k, cm)


class RTMTest(unittest.TestCase):
    def test_complete_rtm_from_passing_results(self):
        """REQ: C020 C100"""
        rtm = certify.build_rtm(_fake_results())
        self.assertEqual(rtm["requirements"], 136)
        self.assertEqual(rtm["checklist_coverage"], 100)
        self.assertNotIn("blocked", rtm["summary"])
        self.assertEqual(rtm["unknown_tags"], [])

    def test_rtm_detects_gaps(self):
        """REQ: C020 INV18-CMP-003"""
        res = _fake_results()
        res["tests"] = [t for t in res["tests"] if t["tags"] != ["INV-18-C050"]]
        res["tests"].append({"id": "tests/x.py::T::skip", "status": "skip", "tags": ["INV-18-C051"],
                             "mandatory": True, "detail": "no dep"})
        res["tests"].append({"id": "tests/x.py::T::orphan", "status": "pass", "tags": ["INV18-FR-999"],
                             "mandatory": True, "detail": None})
        res["tests"].append({"id": "tests/x.py::T::untagged", "status": "pass", "tags": [], "mandatory": True,
                             "detail": None})
        rtm = certify.build_rtm(res)
        rows = {r["id"]: r for r in rtm["rows"]}
        self.assertEqual(rows["INV-18-C050"]["status"], "blocked")
        self.assertEqual(rows["INV-18-C051"]["status"], "blocked")
        self.assertEqual(rtm["unknown_tags"], ["INV18-FR-999"])
        self.assertIn("tests/x.py::T::untagged", rtm["tests_without_requirements"])
        self.assertIn("RTM", certify.rtm_markdown(rtm))


class GateTest(unittest.TestCase):
    BENCH = None

    @classmethod
    def setUpClass(cls):
        cls.BENCH = json.loads((PKG_DIR / "conformance/BENCH_BASELINE.json").read_text())

    def _gate(self, results, **kw):
        return certify.certify(results=results, bench_result=kw.get("bench", self.BENCH),
                               fault_results=kw.get("faults", [{"scenario": "x", "passed": True}]),
                               compat=kw.get("compat", {"runs": []}),
                               bootstrap_report=kw.get("boot", {"ok": True, "steps": []}), write=False)

    def test_skipped_mandatory_test_blocks(self):
        """REQ: C100 C090 INV18-CMP-003"""
        res = _fake_results(extra=[{"id": "tests/x.py::T::needs_dep", "status": "skip", "tags": ["INV-18-C082"],
                                    "mandatory": True, "detail": "pk_core missing"}])
        ev = self._gate(res)
        chk = {c["check"]: c for c in ev["checks"]}
        self.assertEqual(chk["tests.no_mandatory_skips"]["result"], "BLOCKED")
        self.assertEqual(ev["verdict"], "NO_GO")
        self.assertEqual(ev["exit_code"], 20)

    def test_failures_and_regressions_block(self):
        """REQ: C100 C070"""
        res = _fake_results()
        res["tests"][0]["status"] = "fail"
        slow = json.loads(json.dumps(self.BENCH)); slow["micro"]["resolve"]["p50_us"] *= 10
        ev = self._gate(res, bench=slow, faults=[{"scenario": "x", "passed": False}], boot={"ok": False, "steps": []})
        chk = {c["check"]: c["result"] for c in ev["checks"]}
        for k in ("tests.executed", "performance.regression", "performance.thresholds", "resilience.faults",
                  "bootstrap.clean", "requirements.mandatory"):
            self.assertEqual(chk[k], "FAIL", k)
        self.assertEqual(ev["verdict"], "NO_GO")

    def test_conditions_need_acceptance(self):
        """REQ: C100 C099"""
        ev = self._gate(_fake_results())
        conds = [c for c in ev["checks"] if c["result"] == "CONDITION"]
        if conds:
            self.assertIn(ev["verdict"], ("NO_GO",))           # nothing accepted in the shipped register
            self.assertTrue(ev["unaccepted_conditions"])

    def test_expired_waiver_fails(self):
        """REQ: C099 C100"""
        old = os.environ.get("INV18_TODAY")
        os.environ["INV18_TODAY"] = "2030-01-01"
        try:
            res = certify.resolve_blocker("W-C068", {})
            self.assertEqual(res[0], "FAIL")
            ev = self._gate(_fake_results())
            chk = {c["check"]: c["result"] for c in ev["checks"]}
            self.assertEqual(chk["governance.waivers_unexpired"], "FAIL")
        finally:
            if old is None:
                os.environ.pop("INV18_TODAY", None)
            else:
                os.environ["INV18_TODAY"] = old

    def test_evidence_record_complete_and_sealed(self):
        """REQ: C090 C045 C078"""
        ev = self._gate(_fake_results())
        for k in ("component", "version", "source_commit", "artifact_digest", "build_environment", "checks",
                  "test_summary", "rtm_summary", "input_digests", "verdict", "seal"):
            self.assertIn(k, ev)
        self.assertEqual(len(ev["seal"]["sha256"]), 64)
        names = {c["check"] for c in ev["checks"]}
        for k in ("rtm.complete", "interfaces.schemas", "interfaces.fixtures", "security.threat_coverage",
                  "blocker.OWNERS_VACANT", "blocker.ADR_NOT_APPROVED", "blocker.PK_CORE_MISSING",
                  "integrity.artifact_digests", "governance.reviews_current"):
            self.assertIn(k, names)


class IntegrityTest(unittest.TestCase):
    def _copy(self):
        d = pathlib.Path(tempfile.mkdtemp()) / PKG_DIR.name
        shutil.copytree(PKG_DIR, d, ignore=shutil.ignore_patterns("__pycache__", "evidence"))
        return d

    def test_tampered_artifact_detected(self):
        """REQ: C045 C087 — T10"""
        d = self._copy()
        tv.write_sums(d)
        self.assertEqual(tv.verify_tree(d), [])
        p = d / "future.py"
        p.write_text(p.read_text() + "\n# tampered\n")
        (d / "evil.py").write_text("x = 1\n")
        probs = tv.verify_tree(d)
        self.assertIn("changed: future.py", probs)
        self.assertIn("unlisted: evil.py", probs)
        shutil.rmtree(d.parent)

    def test_tampered_evidence_detected(self):
        """REQ: C090 C045 C087 — T10"""
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "conformance").mkdir()
        ev = {"schema": "INV18_RELEASE_EVIDENCE/1", "verdict": "NO_GO", "exit_code": 20, "input_digests": {}}
        body = json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()
        import hashlib
        ev["seal"] = {"sha256": hashlib.sha256(body).hexdigest(), "hmac_sha256": None}
        p = d / "conformance" / "RELEASE_EVIDENCE.json"
        p.write_text(json.dumps(ev))
        self.assertEqual(certify.verify(p), (True, []))
        ev["verdict"] = "GO"
        p.write_text(json.dumps(ev))
        ok, probs = certify.verify(p)
        self.assertFalse(ok)
        self.assertTrue(any("seal" in x or "inconsistent" in x for x in probs))
        shutil.rmtree(d)

    def test_sbom_and_lock(self):
        """REQ: C031 C045"""
        tmp = pathlib.Path(tempfile.mkdtemp()) / "SBOM.json"
        subprocess.run([sys.executable, str(PKG_DIR / "tools/sbom.py"), str(tmp)], check=True, capture_output=True)
        sb = json.loads((PKG_DIR / "conformance/SBOM.json").read_text())
        self.assertEqual(json.loads(tmp.read_text()), sb, "shipped SBOM is stale")      # never writes into the package
        self.assertEqual(sb["bomFormat"], "CycloneDX")
        names = {c["name"] for c in sb["components"]}
        self.assertIn("pk_core", names)
        lock = json.loads((PKG_DIR / "requirements.lock.json").read_text())
        pk = next(d for d in lock["dependencies"] if d["name"] == "pk_core")
        blocked = certify.resolve_blocker("PK_CORE_MISSING", {})
        self.assertEqual(blocked is None, bool(pk["sha256"]) and certify._pk_core_available())
        self.assertIn("requires-python", (PKG_DIR / "pyproject.toml").read_text())


class BootstrapTest(unittest.TestCase):
    def test_clean_readonly_bootstrap_idempotent(self):
        """REQ: C040 C032 C031"""
        base = pathlib.Path(tempfile.mkdtemp())
        d = base / PKG_DIR.name
        shutil.copytree(PKG_DIR, d, ignore=shutil.ignore_patterns("__pycache__", "evidence"))
        tv.write_sums(d)
        for p in d.rglob("*"):
            p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        d.chmod(d.stat().st_mode & ~stat.S_IWUSR)
        evid = base / "evid"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        outs = []
        try:
            for _ in range(2):
                r = subprocess.run([sys.executable, "-m", PKG_DIR.name, "bootstrap", "--evidence-dir", str(evid)],
                                   cwd=str(base), capture_output=True, text=True, env=env, timeout=300)
                outs.append(r)
                self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            rep = json.loads((evid / "bootstrap_report.json").read_text())
            steps = {s["step"]: s["result"] for s in rep["steps"]}
            self.assertEqual(steps["artifact_digests"], "PASS")
            self.assertEqual(steps["smoke"], "PASS")
            self.assertIn(steps["pk_core_registration"], ("PASS", "BLOCKED"))
            self.assertEqual(tv.verify_tree(d), [])                     # package unchanged by runtime
        finally:
            for p in [d, *d.rglob("*")]:
                p.chmod(p.stat().st_mode | stat.S_IWUSR)
            shutil.rmtree(base)


class RunbookTest(unittest.TestCase):
    def test_runbook_commands_execute(self):
        """REQ: C096 C092 C095 C038 C059"""
        text = (PKG_DIR / "docs/OPERATIONS.md").read_text()
        blocks = re.findall(r"```sh runbook\n(.*?)```", text, re.S)
        self.assertGreaterEqual(len(blocks), 4)
        evid = tempfile.mkdtemp()
        env = {**os.environ, "PY": sys.executable, "EVID": evid, "PYTHONDONTWRITEBYTECODE": "1"}
        for block in blocks:
            for line in block.strip().splitlines():
                cmd = line.replace("$PY", sys.executable).replace('"$EVID"', evid).replace("$EVID", evid)
                cmd = cmd.replace("inv18_completion_primitive", PKG_DIR.name)
                r = subprocess.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True, env=env,
                                   timeout=600)
                self.assertEqual(r.returncode, 0, f"{cmd}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
        for drill in ("canary", "rollback", "disable"):
            self.assertTrue(json.loads(pathlib.Path(evid, f"drill_{drill}.json").read_text())["pass"])
        shutil.rmtree(evid)


class ComponentPinTest(unittest.TestCase):
    def test_pk_core_integration_declared(self):
        """REQ: C031 C084 C093"""
        self.assertIn("pk_core", (PKG_DIR / "component.py").read_text())
        cm = json.loads((PKG_DIR / "conformance/COMPAT_MATRIX.json").read_text())
        self.assertIn("3.11", cm["python"]["supported"])
        res_p = PKG_DIR / "conformance/COMPAT_RESULTS.json"
        if res_p.exists():
            res = json.loads(res_p.read_text())
            self.assertTrue(any(r.get("executed") for r in res["runs"]))


if __name__ == "__main__":
    unittest.main()
