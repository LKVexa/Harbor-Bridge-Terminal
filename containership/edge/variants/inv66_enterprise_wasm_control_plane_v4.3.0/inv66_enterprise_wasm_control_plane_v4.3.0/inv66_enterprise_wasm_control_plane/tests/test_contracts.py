"""Public-interface contract tests and compatibility fixtures (MC-012/013/014/016/018/055)."""
from __future__ import annotations

import json
import pathlib
import unittest

from support import Harness, config, request
from inv66_enterprise_wasm_control_plane import errors, schema

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

# Frozen at 4.3.0.  Codes may be ADDED; removing or renaming one breaks clients.
GOLDEN_CODES_4_3_0 = {
    "AUTHN_MISSING", "AUTHN_INVALID", "AUTHN_REPLAY", "AUTHZ_DENIED", "AUTHZ_EXPLICIT_DENY", "SCHEMA_INVALID",
    "PROTOCOL_UNSUPPORTED", "MANIFEST_TOO_LARGE", "MANIFEST_EMPTY", "MANIFEST_TOO_MANY_COMPONENTS",
    "COMPONENT_DUPLICATE", "IMAGE_MALFORMED", "IMAGE_NOT_PINNED", "REGISTRY_NOT_APPROVED", "SIGNER_NOT_APPROVED",
    "SIGNATURE_INVALID", "ATTESTATION_MISSING", "POLICY_DENIED", "POLICY_UNAVAILABLE", "QUOTA_EXCEEDED",
    "OVERLOADED", "DEADLINE_EXCEEDED", "FROZEN", "IDEMPOTENCY_CONFLICT", "NOT_LEADER", "STORE_UNAVAILABLE",
    "DEPLOY_FAILED", "CONFIG_INVALID", "ILLEGAL_TRANSITION", "NOT_FOUND", "INTERNAL",
}


class ContractTest(unittest.TestCase):
    def test_error_catalog_is_backward_compatible(self):
        self.assertTrue(GOLDEN_CODES_4_3_0 <= set(errors.CATALOG))
        for code in errors.CATALOG:
            e = errors.Error(code).to_dict()
            self.assertEqual(schema.validate(e, "urn:inv66:schema:PK_ECP_ERROR:1"), [])
        with self.assertRaises(ValueError):
            errors.Error("MADE_UP")

    def test_schemas_are_valid_and_validator_agrees_with_reference(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("reference jsonschema not installed (validator self-test still ran)")
        reg = schema.registry()
        from referencing import Registry, Resource
        refreg = Registry().with_resources([(k, Resource.from_contents(v)) for k, v in reg.items()])
        for sid, s in reg.items():
            jsonschema.Draft202012Validator.check_schema(s)
        samples = [request(), request(protocol="X"), request(tenant=""), {"protocol": "PK_ECP_ADMIT/1"}, config(),
                   dict(config(), limits={}), {"subject": "user:a", "role": "deployer", "scope": "org:x", "effect": "allow"},
                   {"subject": "a", "role": "god", "scope": "x", "effect": "maybe"}]
        for sid in reg:
            v = jsonschema.Draft202012Validator(reg[sid], registry=refreg)
            for smp in samples:
                self.assertEqual(bool(schema.validate(smp, sid)), not v.is_valid(smp), (sid, smp))

    def test_versioned_fixtures_still_accepted(self):
        """Golden request/response fixtures for every supported protocol version."""
        for path in sorted(FIXTURES.glob("admit_request.v1.*.json")):
            doc = json.loads(path.read_text())
            self.assertEqual(schema.validate(doc, "urn:inv66:schema:PK_ECP_ADMIT:1:request"), [], path.name)
        h = Harness()
        for path in sorted(FIXTURES.glob("admit_request.v1.*.json")):
            doc = json.loads(path.read_text())
            r = h.svc.admit(h.tok(), doc)
            self.assertEqual(schema.validate(r, "urn:inv66:schema:PK_ECP_ADMIT:1:response"), [])
            expect = json.loads((FIXTURES / path.name.replace("request", "expect")).read_text())
            self.assertEqual(r["admitted"], expect["admitted"])
            self.assertEqual(sorted(e["code"] for e in r["errors"]), expect["codes"])
        h.close()

    def test_unknown_protocol_version_negotiation(self):
        from inv66_enterprise_wasm_control_plane.errors import ControlPlaneError
        h = Harness()
        with self.assertRaises(ControlPlaneError) as cm:
            h.svc.admit(h.tok(), request(protocol="PK_ECP_ADMIT/2"))
        self.assertEqual(cm.exception.error.code, "PROTOCOL_UNSUPPORTED")
        self.assertIn("PK_ECP_ADMIT/1", h.svc.version_info()["protocols"]["admit"])
        h.close()


if __name__ == "__main__":
    unittest.main()
