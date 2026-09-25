"""Public-interface contract suite (MC-012/013/014/016/018/055; C021-C027, C082, C093)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests.support import EcpError, Estate, PKG_DIR
from inv66_enterprise_wasm_control_plane.production import errors, schema

try:
    import jsonschema  # reference implementation, test-only
except ImportError:  # pragma: no cover
    jsonschema = None

FIX = PKG_DIR / "fixtures" / "compat"


class SchemaContractTest(unittest.TestCase):
    def test_all_schemas_load_with_supported_keywords_only(self):
        names = sorted(p.name[:-12] for p in schema.SCHEMA_DIR.glob("*.schema.json"))
        self.assertGreaterEqual(len(names), 10)
        for n in names:
            s = schema.load(n)
            self.assertIn("x-version", s)
            self.assertIn("x-compat", s)

    def test_generated_schemas_have_no_drift(self):
        r = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "gen_schemas.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipIf(jsonschema is None, "reference jsonschema not installed")
    def test_stdlib_validator_agrees_with_reference(self):
        e = Estate()
        good = e.request("api", "web")
        cases = [("PK_ECP_ADMIT_REQUEST_1", good)]
        mutants = [dict(good, protocol="PK_ECP_ADMIT/9"), dict(good, tenant=""), dict(good, extra=1),
                   dict(good, manifest={"components": []}), dict(good, deadline_ms=0),
                   dict(good, manifest={"components": [{"name": "a", "image": "noslash", "signer": "s"}]}),
                   dict(good, traceparent="bad"), {k: v for k, v in good.items() if k != "tenant"}, [], "x", None]
        cases += [("PK_ECP_ADMIT_REQUEST_1", m) for m in mutants]
        cases += [("PK_ECP_CONFIG_1", e.config()), ("PK_ECP_CONFIG_1", e.config(registries=[])),
                  ("PK_ECP_CONFIG_1", e.config(environment="qa"))]
        cases += [("PK_ECP_RBAC_REQUEST_1", {"protocol": "PK_ECP_RBAC/1", "op": "list", "request_id": "r"}),
                  ("PK_ECP_RBAC_REQUEST_1", {"protocol": "PK_ECP_RBAC/1", "op": "bind", "request_id": "r"})]
        for name, inst in cases:
            ours = not schema.errors(inst, schema.load(name))
            ref = jsonschema.Draft202012Validator(schema.load(name)).is_valid(inst)
            self.assertEqual(ours, ref, f"{name}: {json.dumps(inst)[:200]}")

    def test_outputs_conform(self):
        e = Estate()
        d = e.service.admit(e.request("api"), e.token("ops"))
        schema.validate(d, "PK_ECP_ADMIT_DECISION_1")
        d2 = e.service.admit(e.request("api", registry="registry.estate.local"), e.token("ops"))
        schema.validate(d2, "PK_ECP_ADMIT_DECISION_1")
        self.assertFalse(d2["admitted"])
        schema.validate(e.service.health(), "PK_ECP_HEALTH_1")
        schema.validate(e.service.inventory_view(e.principal("auditor")), "PK_ECP_INVENTORY_1")
        for rec in e.service.journal.records():
            schema.validate(rec, "PK_ECP_AUDIT_RECORD_2")
        for code in errors.REGISTRY:
            schema.validate(errors.EcpError(code, "m").envelope("rid"), "PK_ECP_ERROR_1")

    def test_every_denial_reason_uses_registered_code(self):
        e = Estate()
        bad = e.request("api", registry="evil.example")
        bad["manifest"]["components"].append({"name": "api", "image": "x/y", "signer": "nobody"})
        d = e.service.admit(bad, e.token("ops"))
        self.assertTrue(d["reasons"])
        for r in d["reasons"]:
            self.assertIn(r["code"], errors.REGISTRY)

    def test_rbac_api_contract(self):
        e = Estate()
        ta = e.principal("tadmin")
        r = e.service.rbac({"protocol": "PK_ECP_RBAC/1", "op": "bind", "request_id": "r1",
                            "binding": {"subject": "newdev", "role": "deployer", "scope": "acme/payments/dev", "effect": "allow"}}, ta)
        self.assertTrue(r["ok"])
        lst = e.service.rbac({"protocol": "PK_ECP_RBAC/1", "op": "list", "request_id": "r2", "scope": "acme/payments"}, ta)
        self.assertIn({"subject": "newdev", "role": "deployer", "scope": "acme/payments/dev", "effect": "allow"}, lst["bindings"])
        chk = e.service.rbac({"protocol": "PK_ECP_RBAC/1", "op": "check", "request_id": "r3", "subject": "newdev",
                              "capability": "admit", "scope": "acme/payments/dev"}, ta)
        self.assertTrue(chk["allowed"])
        self.assertTrue(e.service.admit(e.request("api", lattice="dev"), e.token("newdev"))["admitted"])
        e.service.rbac({"protocol": "PK_ECP_RBAC/1", "op": "unbind", "request_id": "r4",
                        "binding": {"subject": "newdev", "role": "deployer", "scope": "acme/payments/dev", "effect": "allow"}}, ta)
        with self.assertRaises(EcpError):
            e.service.admit(e.request("api", lattice="dev"), e.token("newdev"))
        self.assertEqual(len(e.open().overlay), 0)  # persisted through replay

    def test_audit_api_contract(self):
        e = Estate()
        e.service.admit(e.request("api"), e.token("ops"))
        q = e.service.audit_query({"protocol": "PK_ECP_AUDIT/1", "request_id": "q", "kind": "admit.decision",
                                   "tenant": "payments"}, e.principal("auditor"))
        self.assertEqual(len(q["records"]), 1)
        self.assertNotIn("manifest", q["records"][0]["body"])
        with self.assertRaises(EcpError):
            e.service.audit_query({"protocol": "PK_ECP_AUDIT/1", "request_id": "q"}, e.principal("ops"))


class CompatibilityTest(unittest.TestCase):
    """MC-018: frozen v1 wire fixtures must stay valid; unsupported versions are refused explicitly."""

    def test_frozen_v1_fixtures_still_validate(self):
        files = sorted(FIX.glob("*.json"))
        self.assertGreaterEqual(len(files), 4)
        for f in files:
            fx = json.loads(f.read_text())
            errs = schema.errors(fx["instance"], schema.load(fx["schema"]))
            self.assertEqual(not errs, fx["valid"], f"{f.name}: {errs[:2]}")

    def test_matrix_is_consistent_with_code(self):
        matrix = json.loads((PKG_DIR / "release" / "compatibility.json").read_text())
        from inv66_enterprise_wasm_control_plane.production.service import PROTOCOLS
        self.assertEqual(sorted(matrix["protocols"]["served"]), sorted(PROTOCOLS))
        for s in matrix["schemas"]:
            self.assertEqual(schema.load(s["name"])["x-version"], s["version"])

    def test_unsupported_protocol_refused(self):
        e = Estate()
        r = e.request("api")
        r["protocol"] = "PK_ECP_ADMIT/2"
        with self.assertRaises(EcpError) as cm:
            e.service.admit(r, e.token("ops"))
        self.assertEqual(cm.exception.code, "ECP_SCHEMA_INVALID")


if __name__ == "__main__":
    unittest.main()
