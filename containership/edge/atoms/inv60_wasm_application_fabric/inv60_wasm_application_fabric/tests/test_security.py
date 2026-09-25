"""M17 M18 M35 M36 M38(partial) M39 M41 M72 - identity, authz, signing, adversarial."""
import unittest
from _harness import World, Clock
from inv60_wasm_application_fabric.fabric import ed25519, signing
from inv60_wasm_application_fabric.fabric.errors import FabricError
from inv60_wasm_application_fabric.fabric.identity import (TrustDomain, new_keypair, reference_attestation,
                                                           MAX_TOKEN_TTL_S)
from inv60_wasm_application_fabric.fabric.fabric import AUDIENCE


class Ed25519Vectors(unittest.TestCase):
    V = [("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
          "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
          "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
         ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
          "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
          "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")]

    def test_rfc8032_vectors(self):
        for sk, pk, msg, sig in self.V:
            self.assertEqual(ed25519.public_key(bytes.fromhex(sk)).hex(), pk)
            self.assertEqual(ed25519.sign(bytes.fromhex(sk), bytes.fromhex(msg)).hex(), sig)
            self.assertTrue(ed25519.verify(bytes.fromhex(pk), bytes.fromhex(msg), bytes.fromhex(sig)))

    def test_rejects_tampered_and_malformed(self):
        sk, pk, msg, sig = self.V[1]
        s = bytearray(bytes.fromhex(sig)); s[5] ^= 1
        self.assertFalse(ed25519.verify(bytes.fromhex(pk), b"\x72", bytes(s)))
        self.assertFalse(ed25519.verify(bytes.fromhex(pk), b"\x73", bytes.fromhex(sig)))
        self.assertFalse(ed25519.verify(b"\x00" * 31, b"", bytes.fromhex(sig)))
        self.assertFalse(ed25519.verify(bytes.fromhex(pk), b"\x72", b"\x00" * 63))
        big_s = bytes.fromhex(sig)[:32] + (2**253).to_bytes(32, "little")
        self.assertFalse(ed25519.verify(bytes.fromhex(pk), b"\x72", big_s))

    def test_cross_check_with_cryptography_when_present(self):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except ImportError:
            self.skipTest("cryptography not installed (optional cross-check)")
        seed, pub = new_keypair()
        k = Ed25519PrivateKey.from_private_bytes(seed)
        self.assertEqual(k.sign(b"inv60"), ed25519.sign(seed, b"inv60"))


class Authentication(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def test_positive(self):
        pr = self.w.trust.authenticate(self.w.tok("api"), AUDIENCE)
        self.assertEqual(pr.kind, "workload")

    def expect(self, fn, code="UNAUTHENTICATED"):
        with self.assertRaises(FabricError) as cm:
            fn()
        self.assertEqual(cm.exception.code, code, str(cm.exception))

    def test_expired(self):
        t = self.w.tok("api", ttl_s=10)
        self.w.clock.advance(10 + 31)
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE))

    def test_not_yet_valid_clock_skew(self):
        t = self.w.tok("api")
        self.w.clock.advance(-120)
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE))

    def test_ttl_capped(self):
        t = self.w.tok("api", ttl_s=10**6)
        self.w.clock.advance(MAX_TOKEN_TTL_S + 60)
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE))

    def test_revoked(self):
        t = self.w.tok("api")
        self.w.trust.revoke(self.w.p["api"].id)
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE))

    def test_wrong_audience(self):
        t = self.w.trust.mint_token(self.w.p["api"].id, self.w.keys["api"], "other-service")
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE))

    def test_wrong_issuer(self):
        other = TrustDomain("evil.test", clock=self.w.clock)
        other.principals = self.w.trust.principals
        t = other.mint_token(self.w.p["api"].id, self.w.keys["api"], AUDIENCE)
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE))

    def test_spoofed_signature(self):
        t = self.w.trust.mint_token(self.w.p["api"].id, self.w.keys["evil"], AUDIENCE)
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE))

    def test_replay(self):
        t = self.w.tok("api")
        self.w.trust.authenticate(t, AUDIENCE)
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE), "REPLAY_DETECTED")

    def test_unknown_principal_and_malformed(self):
        self.expect(lambda: self.w.trust.authenticate("abc.def", AUDIENCE))
        self.expect(lambda: self.w.trust.authenticate("not-a-token", AUDIENCE))

    def test_session_binding(self):
        t = self.w.tok("api", session="s1")
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE, session="s2"))

    def test_enrolment_code_single_use_and_no_default(self):
        seed, pub = new_keypair()
        code = self.w.trust.issue_enrolment_code("workload", "x", "tenant-a")
        self.w.trust.enrol(code, pub)
        self.expect(lambda: self.w.trust.enrol(code, new_keypair()[1]))
        self.expect(lambda: self.w.trust.enrol("default", new_keypair()[1]))

    def test_host_requires_attestation(self):
        seed, pub = new_keypair()
        code = self.w.trust.issue_enrolment_code("host", "h9", "infra")
        self.expect(lambda: self.w.trust.enrol(code, pub))
        code = self.w.trust.issue_enrolment_code("host", "h9", "infra")
        bad = reference_attestation(new_keypair()[1])       # quote bound to another key
        self.expect(lambda: self.w.trust.enrol(code, pub, attestation=bad))

    def test_cloned_key_rejected(self):
        code = self.w.trust.issue_enrolment_code("workload", "clone", "tenant-a")
        with self.assertRaises(FabricError) as cm:
            self.w.trust.enrol(code, self.w.p["api"].public_key)
        self.assertEqual(cm.exception.code, "ALREADY_EXISTS")

    def test_clone_from_unexpected_endpoint(self):
        seed, pub = new_keypair()
        code = self.w.trust.issue_enrolment_code("workload", "pinned", "tenant-a")
        pr = self.w.trust.enrol(code, pub, endpoint="10.0.0.5")
        t = self.w.trust.mint_token(pr.id, seed, AUDIENCE)
        self.expect(lambda: self.w.trust.authenticate(t, AUDIENCE, endpoint="10.9.9.9"))

    def test_dependency_unavailable_fails_closed(self):
        self.w.trust.revocation_source_available = False
        with self.assertRaises(FabricError) as cm:
            self.w.trust.authenticate(self.w.tok("api"), AUDIENCE)
        self.assertEqual(cm.exception.code, "UNAVAILABLE")

    def test_public_metadata_has_no_key_material(self):
        meta = self.w.p["h1"].public()
        self.assertNotIn(self.w.p["h1"].public_key.hex(), str(meta))
        self.assertTrue(meta["attested"])


class Authorization(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.deploy(app="shop")
        self.kv = {}
        self.prov = lambda op, k, v=None: self.kv.__setitem__(k, v) if op == "set" else self.kv.get(k)
        r = self.w.fabric.link(self.w.tok("deployer-a"), "api", "kv", self.prov, tenant="tenant-a",
                               grantee=self.w.p["api"].id, operations=("get",))
        self.assertEqual(r.code, "OK")

    def call(self, who, op="get", tenant="tenant-a"):
        return self.w.fabric.call(self.w.tok(who), "api", "kv", op, "k", tenant=tenant)

    def test_granted_operation(self):
        self.assertEqual(self.call("api").code, "OK")

    def test_operation_not_in_grant(self):
        self.assertEqual(self.call("api", "set").code, "PERMISSION_DENIED")

    def test_cross_tenant_invocation(self):
        self.assertEqual(self.call("evil").code, "PERMISSION_DENIED")
        self.assertEqual(self.call("evil", tenant="tenant-b").code, "PERMISSION_DENIED")

    def test_confused_deputy_operator_cannot_invoke(self):
        self.assertEqual(self.call("ops").code, "PERMISSION_DENIED")

    def test_revocation_immediate(self):
        self.w.fabric.unlink(self.w.tok("deployer-a"), "api", "kv", tenant="tenant-a")
        self.assertEqual(self.call("api").code, "NOT_LINKED")

    def test_grant_expiry(self):
        self.w.clock.advance(3601)
        self.assertEqual(self.call("api").code, "NOT_LINKED")

    def test_workload_cannot_deploy_or_link(self):
        r = self.w.fabric.link(self.w.tok("api"), "api", "kv2", self.prov, tenant="tenant-a", grantee=self.w.p["api"].id)
        self.assertEqual(r.code, "PERMISSION_DENIED")

    def test_cross_tenant_deployer(self):
        r = self.w.fabric.stop(self.w.tok("deployer-b"), "api", tenant="tenant-a")
        self.assertEqual(r.code, "PERMISSION_DENIED")

    def test_decision_records_have_rule_ids(self):
        self.call("evil")
        d = [x for x in self.w.fabric.authz.decisions if not x.allowed][-1]
        self.assertIn(d.rule, ("R-INVOKE", "DEFAULT-DENY"))
        self.assertEqual(d.policy_version, "inv60-policy/1.0.0")

    def test_break_glass_bounded_and_needs_second_factor(self):
        ops = self.w.p["ops"]
        with self.assertRaises(FabricError):
            self.w.fabric.authz.enable_break_glass(ops, 60, second_factor=False)
        self.w.fabric.authz.enable_break_glass(ops, 60, second_factor=True)
        self.assertTrue(self.w.fabric.authz.decide(ops, "artifact.push", "x", "tenant-b").allowed)
        self.w.clock.advance(61)
        self.assertFalse(self.w.fabric.authz.decide(ops, "artifact.push", "x", "tenant-b").allowed)

    def test_policy_engine_unavailable_fails_closed(self):
        self.w.fabric.authz.policy_available = False
        self.assertEqual(self.call("api").code, "UNAVAILABLE")

    def test_unknown_action_denied(self):
        self.assertFalse(self.w.fabric.authz.decide(self.w.p["ops"], "root.everything", "x", "tenant-a").allowed)


class ArtifactSigning(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.data = b"\x00asm-component-v1"

    def push(self, env, name="tenant-a/api", data=None):
        return self.w.fabric.push(self.w.tok("deployer-a"), name, data or self.data, env, tenant="tenant-a")

    def test_trusted(self):
        self.assertEqual(self.push(self.w.artifact()).code, "OK")

    def test_unsigned(self):
        env = self.w.artifact(); env["signatures"] = []
        self.assertEqual(self.push(env).code, "SIGNATURE_INVALID")

    def test_wrong_key(self):
        self.assertEqual(self.push(self.w.artifact(seed=new_keypair()[0])).code, "SIGNATURE_INVALID")

    def test_revoked_signer(self):
        self.w.policy.revoked_signers.add("release-signer")
        self.assertEqual(self.push(self.w.artifact()).code, "SIGNATURE_INVALID")

    def test_wrong_subject_scope(self):
        env = self.w.artifact(name="tenant-z/api")
        self.assertEqual(self.push(env, name="tenant-z/api").code, "SIGNATURE_INVALID")

    def test_tampered_bytes(self):
        self.assertEqual(self.push(self.w.artifact(), data=b"\x00asm-evil").code, "SIGNATURE_INVALID")

    def test_low_provenance_level(self):
        self.assertEqual(self.push(self.w.artifact(level=1)).code, "SIGNATURE_INVALID")

    def test_untrusted_builder(self):
        st = signing.statement_for("tenant-a/api", self.data, builder="laptop", level=3, source_uri="x", commit="b" * 40)
        self.assertEqual(self.push(signing.sign_statement(st, "release-signer", self.w.signer_seed)).code, "SIGNATURE_INVALID")

    def test_stale_trust_root(self):
        self.w.clock.advance(31 * 86400)
        self.assertEqual(self.push(self.w.artifact()).code, "SIGNATURE_INVALID")

    def test_malformed_envelope(self):
        self.assertEqual(self.push({"payload": "!!"}).code, "SIGNATURE_INVALID")

    def test_start_bypass_impossible(self):
        ref = self.w.fabric.lattice.push(b"direct-bytes")        # alternate path, never verified
        r = self.w.fabric.start(self.w.tok("deployer-a"), "rogue", ref, tenant="tenant-a")
        self.assertEqual(r.code, "SIGNATURE_INVALID")

    def test_registry_swap_after_verification_detected(self):
        ref = self.push(self.w.artifact()).value
        self.w.fabric.lattice.registry[ref] = b"swapped"
        r = self.w.fabric.start(self.w.tok("deployer-a"), "api", ref, tenant="tenant-a")
        self.assertEqual(r.code, "DIGEST_MISMATCH")

    def test_cross_tenant_artifact(self):
        ref = self.push(self.w.artifact()).value
        r = self.w.fabric.start(self.w.tok("deployer-b"), "x", ref, tenant="tenant-b")
        self.assertEqual(r.code, "PERMISSION_DENIED")


class Adversarial(unittest.TestCase):
    """M41/M72: threat-model-derived abuse cases (ids from THREAT_MODEL.json)."""

    def setUp(self):
        self.w = World()

    def test_T01_tag_substitution_refused_by_schema(self):
        from inv60_wasm_application_fabric.fabric import wire
        with self.assertRaises(FabricError):
            wire.decode(b'{"meta":{"protocol":"1.0","operation_id":"op-' + b"0" * 32 + b'"},"component":"a","artifact":"latest","tenant":"t"}', "PK_LATTICE_START")

    def test_T07_injection_in_names(self):
        r = self.w.fabric.join_host(self.w.tok("ops"), "")
        self.assertEqual(r.code, "INVALID_ARGUMENT")

    def test_T09_oversized_payload(self):
        from inv60_wasm_application_fabric.fabric import wire
        with self.assertRaises(FabricError) as cm:
            wire.decode(b"x" * (wire.MAX_WIRE_BYTES + 1), "PK_LATTICE_CALL")
        self.assertEqual(cm.exception.code, "PAYLOAD_TOO_LARGE")

    def test_T10_host_cannot_enrol_other_host(self):
        r = self.w.fabric.join_host(self.w.tok("h1"), "h-other")
        self.assertEqual(r.code, "PERMISSION_DENIED")

    def test_T11_telemetry_exfiltration_blocked(self):
        with self.assertRaises(ValueError):
            self.w.fabric.metrics.inc("x", principal="spiffe://a")
        rec = self.w.fabric.log.log("info", "e", token="abc", password="hunter2")
        self.assertEqual(rec["fields"]["token"], "[REDACTED]")
        self.assertEqual(rec["fields"]["password"], "[REDACTED]")

    def test_T12_error_does_not_leak_secret(self):
        from inv60_wasm_application_fabric.fabric.errors import Result
        w = Result("INTERNAL", message="failed password=hunter2 while connecting").to_wire()
        self.assertNotIn("hunter2", str(w))


if __name__ == "__main__":
    unittest.main()
