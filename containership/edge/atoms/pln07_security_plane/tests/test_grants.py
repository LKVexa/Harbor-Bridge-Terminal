"""Framework-independent security tests for PLN-07 grant primitives."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "grants.py"
spec = importlib.util.spec_from_file_location("pln07_grants", MODULE_PATH)
grants = importlib.util.module_from_spec(spec)
assert spec and spec.loader
import sys
sys.modules[spec.name] = grants
spec.loader.exec_module(grants)

Grant = grants.Grant
GrantInvalid = grants.GrantInvalid
Verifier = grants.Verifier
Widening = grants.Widening
MAX_DELEGATION_DEPTH = grants.MAX_DELEGATION_DEPTH


class GrantInvariantTest(unittest.TestCase):
    def test_id_is_parent_bound_and_fingerprint_is_full_sha256(self):
        a = Grant("root-a", "t1", {"state"}, 100)
        b = Grant("root-b", "t1", {"state"}, 100)
        ca = a.attenuate(subject="worker")
        cb = b.attenuate(subject="worker")
        self.assertNotEqual(ca.id, cb.id)
        self.assertEqual(len(ca.id), 16)
        self.assertEqual(len(ca.fingerprint), 64)
        legacy = Grant("controller", "t1", {"state"}, 100)
        self.assertEqual(legacy.id, "3bb0ef82f0bd2218")

    def test_scope_and_expiry_widening_are_refused(self):
        root = Grant("controller", "t1", {"state"}, 100)
        with self.assertRaises(Widening):
            root.attenuate(scope={"state", "secret"})
        with self.assertRaises(Widening):
            root.attenuate(not_after=101)

    def test_direct_child_constructor_cannot_bypass_parent_constraints(self):
        root = Grant("controller", "t1", {"state"}, 100)
        with self.assertRaises(Widening):
            Grant("worker", "t1", {"state", "secret"}, 100, root, 1)
        with self.assertRaises(Widening):
            Grant("worker", "t2", {"state"}, 100, root, 1)
        with self.assertRaises(GrantInvalid):
            Grant("worker", "t1", {"state"}, 100, root, 0)

    def test_noop_attenuation_is_refused(self):
        root = Grant("controller", "t1", {"state"}, 100)
        with self.assertRaises(GrantInvalid) as ctx:
            root.attenuate()
        self.assertEqual(ctx.exception.code, "grant.noop")

    def test_depth_is_bounded(self):
        grant = Grant("s0", "t1", {"state"}, 100)
        for i in range(MAX_DELEGATION_DEPTH):
            grant = grant.attenuate(subject=f"s{i + 1}")
        with self.assertRaises(GrantInvalid):
            grant.attenuate(subject="too-deep")

    def test_revoked_ancestor_invalidates_descendant(self):
        root = Grant("controller", "t1", {"state"}, 100)
        child = root.attenuate(subject="worker")
        with self.assertRaises(GrantInvalid) as ctx:
            Verifier(revoked={root.id}).verify(child, 10, "state", "t1")
        self.assertEqual(ctx.exception.code, "grant.revoked")

    def test_expiry_tenant_capability_and_skew(self):
        root = Grant("controller", "t1", {"state"}, 100)
        self.assertTrue(Verifier(skew=2).verify(root, 102, "state", "t1"))
        with self.assertRaises(GrantInvalid):
            Verifier(skew=1).verify(root, 102, "state", "t1")
        with self.assertRaises(GrantInvalid):
            Verifier().verify(root, 10, "state", "t2")
        with self.assertRaises(GrantInvalid):
            Verifier().verify(root, 10, "invoke", "t1")

    def test_machine_readable_decision(self):
        root = Grant("controller", "t1", {"state"}, 100)
        decision = Verifier().verify_detailed(root, 101, "state", "t1")
        self.assertFalse(decision.verified)
        self.assertEqual(decision.code, "grant.expired")
        self.assertEqual(decision.as_dict()["type"], "PK_GRANT_VERIFICATION/1")

    def test_signature_requirement_is_fail_closed(self):
        root = Grant("controller", "t1", {"state"}, 100, issuer="authority")
        verifier = Verifier(require_signatures=True, signature_verifier=lambda g: g.signature == b"ok")
        with self.assertRaises(GrantInvalid) as ctx:
            verifier.verify(root, 10, "state", "t1")
        self.assertEqual(ctx.exception.code, "grant.unsigned")
        signed = root.signed(b"ok")
        self.assertTrue(verifier.verify(signed, 10, "state", "t1"))
        bad = root.signed(b"bad")
        with self.assertRaises(GrantInvalid):
            verifier.verify(bad, 10, "state", "t1")

    def test_input_validation_rejects_ambiguous_values(self):
        with self.assertRaises(TypeError):
            Grant("controller", "t1", "state", 100)
        with self.assertRaises(ValueError):
            Grant("", "t1", {"state"}, 100)
        with self.assertRaises(TypeError):
            Grant("controller", "t1", {"state"}, True)
        with self.assertRaises(ValueError):
            Verifier(skew=-1)

    def test_schema_documents_are_present_and_versioned(self):
        import json
        schema_dir = MODULE_PATH.parent / "schemas"
        expected = {
            "PK_GRANT-1.schema.json": "PK_GRANT/1",
            "PK_GRANT_VERIFICATION-1.schema.json": "PK_GRANT_VERIFICATION/1",
            "PK_REVOCATION-1.schema.json": "PK_REVOCATION/1",
        }
        for filename, schema_id in expected.items():
            document = json.loads((schema_dir / filename).read_text(encoding="utf-8"))
            self.assertEqual(document["$id"], schema_id)
            self.assertEqual(document["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_canonical_payload_is_deterministic_and_typed(self):
        import json
        grant = Grant("controller", "t1", {"invoke", "state"}, 100, issuer="authority")
        body = json.loads(grant.canonical_payload)
        self.assertEqual(body["type"], "PK_GRANT/1")
        self.assertEqual(body["scope"], ["invoke", "state"])
        self.assertEqual(body["parent_id"], None)
        self.assertEqual(grant.canonical_payload, grant.canonical_payload)


if __name__ == "__main__":
    unittest.main()
