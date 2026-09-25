"""Packaging, documentation, traceability, evidence and gate tests (G13-MC-027/028/039/040/041/044/049/051)."""
import copy
import importlib
import json
import pathlib
import re
import unittest

import testkit as k

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_documents_claimed_are_present(self):
        text = "\n".join(p.read_text(encoding="utf-8") for p in [ROOT / "README.md", *ROOT.glob("docs/*.md")])
        refs = set(re.findall(r"`((?:docs|ops|schemas|fixtures|ci|tests)/[A-Za-z0-9_./-]+\.[a-z]+)`", text))
        refs |= set(re.findall(r"`([A-Z_]+\.(?:md|json|yaml))`", text))
        refs.discard("MASTER.md")      # documented as absent/superseded (docs/MASTER_SOURCE.md)
        missing = [r for r in sorted(refs) if not (ROOT / r).exists() and not (ROOT / "docs" / r).exists()]
        self.assertEqual(missing, [])

    def test_no_dangling_master_reference(self):
        for p in ROOT.rglob("*.md"):
            if p.name in ("MASTER_SOURCE.md", "CHANGELOG.md", "AUDIT_REPORT.md", "MISSING_COMPONENTS.md"):
                continue
            self.assertNotRegex(p.read_text(encoding="utf-8"), r"MASTER\.md` (is|are) bundled", p.name)
        self.assertFalse((ROOT / "MASTER.md").exists() and "superseded" not in (ROOT / "docs/MASTER_SOURCE.md").read_text())

    def test_internal_anchors_resolve(self):
        docs = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "docs").glob("*.md")}
        for name, anchor in re.findall(r"docs/([A-Z_0-9-]+\.md)#([a-z0-9-]+)", json.dumps(json.loads((ROOT / "COMPONENT_STATUS.json").read_text()))
                                       + (ROOT / "ops/alerts/gap13_alerts.yaml").read_text()):
            self.assertIn("{#" + anchor + "}", docs[name], f"{name}#{anchor}")

    def test_version_consistency(self):
        from gap13_policy_engine import __version__, compat
        self.assertEqual((ROOT / "VERSION").read_text().strip(), __version__)
        self.assertIn(f"## {__version__}", (ROOT / "CHANGELOG.md").read_text())
        self.assertIn(__version__, (ROOT / "README.md").read_text())
        self.assertEqual(json.loads((ROOT / "COMPONENT_STATUS.json").read_text())["engine_release"], __version__)
        self.assertEqual(compat.MATRIX["engine_release"], __version__)

    def test_component_status_complete(self):
        st = json.loads((ROOT / "COMPONENT_STATUS.json").read_text())
        ids = [c["id"] for c in st["components"]]
        self.assertEqual(ids, [f"G13-MC-{i:03}" for i in range(1, 52)])
        self.assertEqual([c["id"] for c in st["external_contracts"]], [f"EXT-0{i}" for i in range(1, 6)])
        for c in st["components"]:
            self.assertIn(c["status"], ("NOT STARTED", "DESIGN", "IMPLEMENTING", "VERIFYING", "BLOCKED", "DONE", "WAIVED"))
            self.assertIn(c["priority"], range(5))
            if c["status"] == "BLOCKED":
                self.assertTrue(c["open_items"], c["id"])
            self.assertNotEqual(c["status"], "DONE", "acceptance cannot be self-granted in this package")

    def test_traceability_complete(self):
        reqs = set(re.findall(r"\| (REQ-[A-Z]{3}-\d{3}) \|", (ROOT / "docs/REQUIREMENTS.md").read_text()))
        tr = json.loads((ROOT / "docs/TRACEABILITY.json").read_text())
        self.assertEqual(reqs, {r["requirement"] for r in tr["rows"]})
        for row in tr["rows"]:
            for t in row["tests"]:
                if t.startswith("bench:"):
                    continue
                mod, cls, meth = t.split(".")
                self.assertTrue(hasattr(getattr(importlib.import_module(mod), cls), meth), t)

    def test_owners_file_shape(self):
        txt = (ROOT / "docs/OWNERS.yaml").read_text()
        for role in ("service_owner", "operations_oncall", "security_owner", "architecture_authority", "escalation"):
            self.assertIn(role, txt)

    def test_waivers_shape(self):
        w = json.loads((ROOT / "WAIVERS.json").read_text())["waivers"]
        for x in w:
            for f in ("id", "component", "rationale", "compensating_controls", "owner", "approver", "status", "expires"):
                self.assertIn(f, x)
            self.assertRegex(x["expires"], r"^\d{4}-\d{2}-\d{2}$")
            if x["status"] == "APPROVED":
                self.assertTrue(x["approver"])

    def test_alerts_reference_real_metrics(self):
        from gap13_policy_engine import service  # noqa: F401  (metric names emitted there)
        src = "".join(p.read_text() for p in ROOT.glob("*.py"))
        alerts = (ROOT / "ops/alerts/gap13_alerts.yaml").read_text() + (ROOT / "ops/dashboards/gap13_overview.json").read_text()
        for m in set(re.findall(r"g13_([a-z_]+?)(?:_total|_bucket|_sum|_count)?\b", alerts)):
            self.assertIn(f'"{m}"', src, m)

    def test_runbooks_reference_current_interfaces(self):
        rb = (ROOT / "docs/RUNBOOKS.md").read_text()
        from gap13_policy_engine.service import CONTROL_STATES, PolicyService
        for s in CONTROL_STATES:
            self.assertIn(s, rb)
        for meth in re.findall(r"svc\.([a-z_]+)\(", rb):
            self.assertTrue(hasattr(PolicyService, meth) or meth == "audit", meth)
        from gap13_policy_engine.authz import Capability
        for cap in re.findall(r"\[(policy\.[a-z._]+)\]", rb):
            self.assertIn(cap, {c.value for c in Capability})

    def test_error_codes_doc_current(self):
        from gap13_policy_engine import errors
        doc = (ROOT / "docs/ERROR_CODES.md").read_text()
        for code in errors.registry():
            self.assertIn(code, doc)

    def test_selftest_loader(self):
        from gap13_policy_engine.selftest import selftest_load
        e = k.g.PolicyEngine("prod")
        selftest_load(e, [k.g.Rule("a", "allow", (("action", "read"),))], "v1")
        self.assertEqual(e.evaluate({"action": "read"})["effect"], "allow")

    def _fake_manifest(self):
        from gap13_policy_engine import certify, __version__
        m = {"schema": "PK_POLICY_EVIDENCE/1", "release": __version__, "artifacts": certify.artifact_digests(),
             "tests": {"summary": {"pass": 1, "fail": 0, "error": 0, "skip": 0, "total": 1},
                       "results": {"test_bundle_schema.GoldenTests.test_goldens_reproduce_exactly": {"status": "pass"}}},
             "benchmark": json.loads((ROOT / "ops/perf_baseline.json").read_text()) | {"overload": {"shed": 5, "hung_threads": 0}},
             "benchmark_profile": "full",
             "requirements": {"REQ-X": {"status": "pass"}}, "components": {}, "waivers": [], "secret_scan": []}
        m["manifest_digest"] = certify.manifest_digest(m)
        return m

    def test_certify_manifest_roundtrip(self):
        from gap13_policy_engine import certify
        m = self._fake_manifest()
        seed = bytes(range(32))
        certify.sign_manifest(m, seed, "ev")
        p = pathlib.Path(k.tmpdir()) / "manifest.json"
        p.write_text(json.dumps(m))
        ok, probs = certify.verify_manifest(p, public_key=k.pub(seed))
        self.assertTrue(ok, probs)
        bad = copy.deepcopy(m)
        bad["tests"]["summary"]["fail"] = 0
        bad["artifacts"]["engine.py"] = "sha256:" + "0" * 64
        p.write_text(json.dumps(bad))
        ok, probs = certify.verify_manifest(p, public_key=k.pub(seed))
        self.assertFalse(ok)
        self.assertTrue(any("digest mismatch" in x for x in probs))
        self.assertTrue(certify.scan_secrets("-----BEGIN PRIVATE KEY-----"))

    def test_release_gate_blocks_on_failures(self):
        from gap13_policy_engine import release_gate as rg
        m = self._fake_manifest()
        self.assertEqual(rg.evaluate(m)["verdict"], "GO", rg.evaluate(m)["blocking"])
        for mutate, expect in [
            (lambda x: x["tests"]["summary"].__setitem__("fail", 1), "no failing tests"),
            (lambda x: x["tests"]["results"].__setitem__("t.A.b", {"status": "skip"}), "no unexplained skips"),
            (lambda x: x["requirements"].__setitem__("REQ-Y", {"status": "fail"}), "every SHALL requirement"),
            (lambda x: x["benchmark"]["sizes"]["10000"]["engine_ms"].__setitem__("p99", 50.0), "perf ceiling"),
            (lambda x: x["benchmark"].__setitem__("overload", {"shed": 0, "hung_threads": 3}), "overload"),
            (lambda x: x.__setitem__("release", "4.2.0"), "release version"),
        ]:
            mm = copy.deepcopy(m)
            mutate(mm)
            mm["manifest_digest"] = __import__("gap13_policy_engine.certify", fromlist=["x"]).manifest_digest(mm)
            r = rg.evaluate(mm)
            self.assertEqual(r["verdict"], "NO_GO")
            self.assertTrue(any(expect in b for b in r["blocking"]), (expect, r["blocking"]))
        prod = rg.evaluate(m, profile="production")
        self.assertEqual(prod["verdict"], "NO_GO")
        self.assertIn("owners assigned", prod["blocking"])


if __name__ == "__main__":
    unittest.main()
