"""Governance, traceability, schemas-as-executable, manifests and gate behaviour (C009, C020, C022, C090, C100)."""
import ast
import datetime as dt
import json
import pathlib
import re
import shutil
import tempfile
import unittest
from unittest import mock

from _support import PKG_DIR, env
from inv52_messaging_abstraction import config as cfgm
from inv52_messaging_abstraction import gate
from inv52_messaging_abstraction import resilience as res
from inv52_messaging_abstraction import runtime as rt
from inv52_messaging_abstraction import schemas as sc

GOV = PKG_DIR / "governance"


def load(p):
    return json.loads((PKG_DIR / p).read_text(encoding="utf-8"))


class GovernanceTest(unittest.TestCase):
    def test_owners_schema_and_roles(self):
        o = load("governance/owners.json")
        self.assertEqual(o["component"], "INV-52")
        for role in ("accountable_owner", "security_owner", "release_owner", "oncall_escalation"):
            self.assertIn(role, o["roles"])
        for act, raci in o["raci"].items():
            self.assertIn(raci["A"], o["roles"], act)
            self.assertIn(raci["R"], o["roles"], act)

    def test_waivers_have_owner_risk_expiry(self):
        for w in load("governance/waivers.json")["waivers"]:
            for k in ("id", "kind", "requirement", "risk", "summary", "compensating", "owner", "expires"):
                self.assertIn(k, w)
            dt.date.fromisoformat(w["expires"])
            self.assertIn(w["kind"], ("exception", "technical-debt", "deprecation"))

    def test_threat_map_tests_exist(self):
        names = set()
        for f in (PKG_DIR / "tests").glob("test_*.py"):
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for fn in node.body:
                        if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_"):
                            names.add(f"{f.name}::{fn.name}")
                            names.add(f"{f.name}::{node.name}::{fn.name}")
        th = load("governance/threats.json")["threats"]
        for t in th:
            if t["external"]:
                self.assertEqual(t["tests"], [], t["id"])
            else:
                self.assertTrue(t["tests"], t["id"])
            for ref in t["tests"]:
                self.assertIn(ref, names, f"{t['id']} -> {ref}")

    def test_rtm_consistent_and_covers_all_91_unresolved(self):
        r = gate.check_rtm()
        self.assertEqual(r["result"], "PASS", r["problems"])
        ids = [x["id"] for x in load("governance/requirements.json")["requirements"]]
        audit = load("POST_UPDATE_AUDIT_4.2.0.json")["records"]
        unresolved = [x["check_id"] for x in audit if x["status"] in ("missing", "partial")]
        self.assertEqual(len(unresolved), 91)
        self.assertEqual(sorted(ids), sorted(unresolved))
        self.assertEqual(len(ids), len(set(ids)))

    def test_nothing_claims_implemented_without_approval(self):
        approvals = GOV / "approvals.json"
        self.assertFalse(approvals.exists(), "no approval exists; the build must not create one")
        for r in load("governance/requirements.json")["requirements"]:
            self.assertNotEqual(r["status"], "IMPLEMENTED", r["id"])

    def test_gate_governance_blocks_and_refuses_self_approval(self):
        today = dt.date(2026, 9, 22)
        self.assertEqual(gate.check_governance(today)["result"], "BLOCKED")
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            shutil.copytree(GOV, root / "governance")
            owners = json.loads((root / "governance/owners.json").read_text())
            owners["roles"] = {k: f"person-{k}" for k in owners["roles"]}
            (root / "governance/owners.json").write_text(json.dumps(owners))
            wv = json.loads((root / "governance/waivers.json").read_text())
            for w in wv["waivers"]:
                w["owner"] = "person-x"
            (root / "governance/waivers.json").write_text(json.dumps(wv))
            for approver, want in (("claude", "BLOCKED"), ("CI", "BLOCKED"), ("Dana Reviewer", "PASS")):
                (root / "governance/approvals.json").write_text(json.dumps(
                    {"approvals": [{"approver": approver, "decision": "APPROVE"}]}))
                with mock.patch.object(gate, "ROOT", root):
                    self.assertEqual(gate.check_governance(today)["result"], want, approver)
            with mock.patch.object(gate, "ROOT", root):
                self.assertEqual(gate.check_governance(dt.date(2030, 1, 1))["result"], "BLOCKED")  # expired waivers


class SchemaExecutableTest(unittest.TestCase):
    def test_config_defaults_and_examples_match_schema(self):
        s = sc.load_schema("PK_MSG_CONFIG/1")
        self.assertEqual(sc.check_against_schema(cfgm.layered(), s), [])
        ex = PKG_DIR / "examples" / "config"
        layers = [json.loads((ex / n).read_text()) for n in ("base.json", "env.prod.json", "site.edge-1.json")]
        cfg = cfgm.layered(*layers)
        self.assertEqual(cfgm.validate(cfg), [])
        self.assertEqual(sc.check_against_schema(cfg, s), [])
        self.assertEqual(cfg["limits"]["max_payload_bytes"], 65536)

    def test_decisions_and_health_match_schema(self):
        b = rt.PubSub()
        b.allow("t", "a")
        b.subscribe("t", lambda m: 1 / 0, [])
        b.subscribe("t", lambda m: True, [])
        b.publish("a", "t", env())
        with self.assertRaises(rt.TopicDenied):
            b.publish("x", "t", env("x"))
        ds = sc.load_schema("PK_MSG_DECISION/1")
        for d in b.decisions():
            self.assertEqual(sc.check_against_schema(d, ds), [], d)
        self.assertEqual(sc.check_against_schema(b.health(), sc.load_schema("PK_MSG_HEALTH/1")), [])

    def test_publish_request_and_envelope_schema(self):
        req = {"contract": "PK_MSG_PUBLISH/1", "app": "a", "topic": "t", "message": env()}
        self.assertEqual(sc.check_against_schema(req, sc.load_schema("PK_MSG_PUBLISH/1")), [])
        self.assertEqual(sc.parse_publish_request(json.dumps(req))["topic"], "t")
        self.assertEqual(sc.check_against_schema(env(), sc.load_schema("PK_MSG_ENVELOPE/1")), [])
        self.assertTrue(sc.check_against_schema({"contract": "PK_MSG_PUBLISH/1"}, sc.load_schema("PK_MSG_PUBLISH/1")))

    def test_every_supported_contract_has_a_schema_file(self):
        for name, majors in sc.SUPPORTED.items():
            for m in majors:
                self.assertIsInstance(sc.load_schema(f"{name}/{m}"), dict)


class RepositoryTest(unittest.TestCase):
    def test_version_consistency(self):
        v = (PKG_DIR / "VERSION").read_text().strip()
        self.assertEqual(v, "4.3.0")
        self.assertIn(f'version = "{v}"', (PKG_DIR / "pyproject.toml").read_text())
        self.assertIn(f"## {v}", (PKG_DIR / "CHANGELOG.md").read_text())

    def test_core_has_no_ambient_authority(self):
        forbidden = {"socket", "subprocess", "urllib", "http", "ctypes", "multiprocessing", "shutil"}
        for mod in ("runtime", "resilience", "lifecycle", "security", "config", "observability", "schemas"):
            tree = ast.parse((PKG_DIR / f"{mod}.py").read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                for n in names:
                    self.assertNotIn(n.split(".")[0], forbidden, f"{mod} imports {n}")
        for mod in ("runtime", "resilience", "lifecycle"):
            self.assertNotRegex((PKG_DIR / f"{mod}.py").read_text(), r"\bopen\(", mod)

    def test_deploy_manifests_have_no_inline_secrets_and_match_library_defaults(self):
        comp = (PKG_DIR / "deploy/dapr/pubsub-component.yaml").read_text()
        self.assertRegex(comp, r"redisPassword\s*\n\s*secretKeyRef")
        self.assertIn('enableTLS\n      value: "true"', comp)
        resil = (PKG_DIR / "deploy/dapr/resiliency.yaml").read_text()
        p = res.RetryPolicy()
        self.assertIn(f"maxRetries: {p.max_attempts - 1}", resil)
        self.assertIn(f"initialInterval: {int(p.base_delay * 1000)}ms", resil)
        self.assertIn(f"maxInterval: {int(p.max_delay)}s", resil)

    def test_documented_limits_match_code(self):
        doc = (PKG_DIR / "docs/INTERFACES.md").read_text()
        self.assertEqual(rt.DEFAULT_MAX_PAYLOAD_BYTES, 1_048_576)
        self.assertIn("| payload (canonical JSON bytes) | 1 MiB |", doc)
        for k, (lo, hi) in cfgm.LIMIT_RANGES.items():
            self.assertLessEqual(lo, cfgm.DEFAULTS["limits"][k])
            self.assertGreaterEqual(hi, cfgm.DEFAULTS["limits"][k])
        self.assertIn(f"| routes per topic (fan-out) | {rt.DEFAULT_MAX_ROUTES_PER_TOPIC} |", doc)

    def test_every_error_code_is_documented(self):
        doc = (PKG_DIR / "docs/INTERFACES.md").read_text()
        codes = set()
        for f in PKG_DIR.glob("*.py"):
            codes |= set(re.findall(r'code = "(PK_MSG_[A-Z_]+)"', f.read_text()))
        codes.discard("PK_MSG_ERROR")
        for c in sorted(codes):
            self.assertIn(c, doc)


if __name__ == "__main__":
    unittest.main()
