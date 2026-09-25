"""Components 13 (schemas), 14 (error model), 29 (configuration), 42
(contract tests with valid/invalid fixtures and an optional jsonschema lane)."""
from __future__ import annotations

import copy
import json
import os
import unittest

import fixtures as F
from inv07_gitops_transition_layer.components import config as C, errors as E, schemas as S

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas")
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract_fixtures.json")

# Frozen at 5.0.0: a code may never change meaning.  Adding codes is allowed
# (extend this table); editing or removing a row is a breaking change.
FROZEN_CODES = {
    "PKG-INPUT-001": ("Malformed", "input", "terminal"), "PKG-TRUST-001": ("Unsigned", "trust", "terminal"),
    "PKG-TRUST-002": ("Untrusted", "trust", "terminal"), "PKG-TRUST-003": ("Revoked", "trust", "terminal"),
    "PKG-TRUST-005": ("ProvenanceFailed", "trust", "terminal"), "PKG-REF-002": ("NonFastForward", "ref_policy", "terminal"),
    "PKG-REPO-002": ("RepositoryUnavailable", "repository", "retryable"),
    "PKG-APPLY-002": ("PartialApply", "apply", "operator"), "PKG-OPS-001": ("Quarantined", "operations", "operator"),
    "PKG-POLICY-001": ("PolicyDenied", "policy", "terminal"), "PKG-INTERNAL-001": ("GitOpsError", "internal", "terminal"),
}


class TestSchemas(unittest.TestCase):
    def test_files_match_generated(self):
        for n in S.SCHEMAS:
            with open(os.path.join(SCHEMA_DIR, n + ".schema.json"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), S.render(n), f"{n} stale: run python -m ...components.schemas --write")

    def test_all_named_interfaces_present(self):
        for n in ("PK_GITOPS_SYNC_1", "PK_GITOPS_DRIFT_1", "PK_GITOPS_VERIFY_1", "PK_GITOPS_STATUS_1",
                  "PK_GITOPS_ERROR_1"):
            self.assertIn(n, S.SCHEMAS)

    def test_live_documents_validate(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            r = c.reconcile("refs/heads/main")
            self.assertEqual(S.validate(r, S.SCHEMAS["PK_GITOPS_SYNC_1"]), [])
            self.assertEqual(S.validate(c.status(), S.SCHEMAS["PK_GITOPS_STATUS_1"]), [])
            ex = c.explain.get(r["decision_id"])
            self.assertEqual(S.validate(ex, S.SCHEMAS["PK_GITOPS_EXPLAIN_1"]), [])
            for line in e.events:
                self.assertEqual(S.validate(json.loads(line), S.SCHEMAS["PK_GITOPS_EVENT_1"]), [])
        finally:
            e.cleanup()


class TestErrors(unittest.TestCase):
    def test_frozen_code_meanings(self):
        for code, meaning in FROZEN_CODES.items():
            self.assertEqual(E.REGISTRY[code], meaning, code)

    def test_codes_unique_and_envelopes_valid(self):
        codes = [c.code for c in E.ALL]
        self.assertEqual(len(codes), len(set(codes)))
        for cls in E.ALL:
            env = cls("m", correlation_id="c1", detail="d").envelope()
            self.assertEqual(S.validate(env, S.SCHEMAS["PK_GITOPS_ERROR_1"]), [], cls.__name__)
            self.assertIn(env["retry"], ("terminal", "retryable", "operator"))
        self.assertEqual(E.from_exception(E.Unsigned("x"), "cid")["correlation_id"], "cid")


class TestConfig(unittest.TestCase):
    def good(self):
        return C.merge(C.DEFAULTS, {"repository": {"url": "https://git.example/r"},
                                    "tenancy": {"tenant": "acme", "site": "s1", "region": "local"}})

    def test_defaults_are_secure_and_valid(self):
        d = C.validate(self.good())
        self.assertTrue(d["trust"]["require_signed"])
        self.assertTrue(d["network"]["verify_tls"])
        self.assertEqual(d["controller"]["offline_mode"], "fail_closed")
        self.assertFalse(d["controller"]["prune"])

    def test_rejections(self):
        cases = [("unknown section", lambda d: d.update(x={})),
                 ("unknown key", lambda d: d["limits"].update(zzz=1)),
                 ("wrong type", lambda d: d["limits"].update(max_queue="10")),
                 ("bool as int", lambda d: d["limits"].update(max_queue=True)),
                 ("range", lambda d: d["controller"].update(sync_interval_seconds=1)),
                 ("dangerous", lambda d: d["trust"].update(require_signed=False)),
                 ("tls off", lambda d: d["network"].update(verify_tls=False)),
                 ("enum", lambda d: d["controller"].update(offline_mode="yolo")),
                 ("inline secret", lambda d: d["repository"].update(credential_ref="hunter2")),
                 ("url creds", lambda d: d["repository"].update(url="https://u:p@git.example/r")),
                 ("short ref", lambda d: d["repository"].update(approved_refs=["main"])),
                 ("region", lambda d: d["tenancy"].update(region="mars")),
                 ("schema", lambda d: d.update(schema="PK_GITOPS_CONFIG/9")),
                 ("retry", lambda d: d["limits"].update(retry_cap_seconds=0.1, retry_base_seconds=1.0))]
        for name, mut in cases:
            d = self.good()
            mut(d)
            with self.subTest(name), self.assertRaises(E.ConfigRejected):
                C.validate(d)

    def test_env_precedence_and_types(self):
        layer = C.from_env({"INV07_CONTROLLER__PRUNE": "true", "INV07_LIMITS__MAX_QUEUE": "7",
                            "INV07_TENANCY__ALLOWED_NAMESPACES": "a,b", "OTHER": "x"})
        d = C.merge(self.good(), layer)
        self.assertEqual((d["controller"]["prune"], d["limits"]["max_queue"]), (True, 7))
        self.assertEqual(d["tenancy"]["allowed_namespaces"], ["a", "b"])
        with self.assertRaises(E.ConfigRejected):
            C.from_env({"INV07_CONTROLLER__PRUNE": "yes"})
        with self.assertRaises(E.ConfigRejected):
            C.from_env({"INV07_NOPE__X": "1"})

    def test_hot_reload_boundaries_and_rollback(self):
        from inv07_gitops_transition_layer.components.audit import AuditLedger
        a = AuditLedger()
        m = C.ConfigManager(self.good(), author="ops", audit=a)
        d2 = self.good()
        d2["limits"]["max_queue"] = 5
        self.assertEqual(m.reload(d2, author="ops", at=1, reason="tune")["version"], 2)
        d3 = copy.deepcopy(d2)
        d3["tenancy"]["tenant"] = "globex"
        with self.assertRaises(E.ConfigRejected):
            m.reload(d3, author="ops", at=2, reason="bad")
        d4 = copy.deepcopy(d2)
        d4["limits"]["max_queue"] = -1
        with self.assertRaises(E.ConfigRejected):
            m.reload(d4, author="ops", at=2, reason="bad")
        self.assertEqual(m.active["config"]["limits"]["max_queue"], 5)       # last known good kept
        self.assertEqual(m.rollback(author="ops", at=3)["config"]["limits"]["max_queue"], 1000)
        self.assertEqual(len([e for e in a.entries() if e["kind"] == "config.activate"]), 3)


class TestContractFixtures(unittest.TestCase):
    """Schema-derived valid/invalid fixtures, run by the stdlib validator and --
    when installed -- by the reference ``jsonschema`` implementation."""

    def test_fixtures(self):
        with open(FIX, encoding="utf-8") as fh:
            fx = json.load(fh)
        for name, cases in fx.items():
            for doc in cases["valid"]:
                self.assertEqual(S.validate(doc, S.SCHEMAS[name]), [], (name, doc))
            for doc in cases["invalid"]:
                self.assertNotEqual(S.validate(doc, S.SCHEMAS[name]), [], (name, doc))

    def test_reference_validator_lane(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("lane: jsonschema not installed")
        with open(FIX, encoding="utf-8") as fh:
            fx = json.load(fh)
        for name, cases in fx.items():
            with open(os.path.join(SCHEMA_DIR, name + ".schema.json"), encoding="utf-8") as fh:
                schema = json.load(fh)
            v = jsonschema.Draft202012Validator(schema)
            for doc in cases["valid"]:
                self.assertEqual(list(v.iter_errors(doc)), [], (name, doc))
            for doc in cases["invalid"]:
                self.assertTrue(list(v.iter_errors(doc)), (name, doc))


if __name__ == "__main__":
    unittest.main()
