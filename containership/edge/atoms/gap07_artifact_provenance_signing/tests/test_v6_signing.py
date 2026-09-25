import copy
import json
import unittest

from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing.canonical import b64u_encode, canonical_bytes
from gap07_artifact_provenance_signing.errors import GapError
from gap07_artifact_provenance_signing.signing import artifact_digest, parse_envelope, signed_message, verify_signature
from gap07_artifact_provenance_signing.tests.fixtures import IDENT, NS, PKI, T0
from gap07_artifact_provenance_signing.trust import Namespace

PAYLOAD = b"executable-bytes"
D = artifact_digest(PAYLOAD)


class SigningV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pki = PKI()
        for a in ("ecdsa-p256-sha256", "ecdsa-p384-sha384", "rsa-pss-sha256-3072"):
            cls.pki.add_signer(f"spiffe://acme/prod/{a}", a, a)
        cls.trust = cls.pki.trust()
        cls.env = cls.pki.signer().sign(PAYLOAD, "code", now=T0)

    def verify(self, env, **kw):
        args = dict(digest_hex=D, kind="code", trust=self.trust, now=T0 + 10)
        args.update(kw)
        return verify_signature(env, **args)

    def code(self, env, **kw):
        with self.assertRaises(GapError) as cm:
            self.verify(env, **kw)
        return cm.exception.code

    def test_every_approved_algorithm_round_trips(self):
        for a in ("ecdsa-p256-sha256", "ecdsa-p384-sha384", "rsa-pss-sha256-3072"):
            env = self.pki.signer(a, f"spiffe://acme/prod/{a}").sign(PAYLOAD, "code", now=T0)
            self.assertEqual(self.verify(env)["alg"], a)
        res = self.verify(self.env)
        self.assertTrue(res["verified"])
        self.assertEqual(res["trust"]["trust_generation"], 1)
        self.assertEqual(res["trust"]["path"], ["root-1", "int-1", "leaf-k1"])

    def test_wire_form_must_be_canonical(self):
        raw = canonical_bytes(self.env)
        self.assertTrue(self.verify(raw)["verified"])
        spaced = json.dumps(self.env, indent=1).encode()
        self.assertEqual(self.code(spaced), "ENVELOPE_MALFORMED")
        dup = raw[:-1] + b',"v":3}'
        self.assertEqual(self.code(dup), "ENVELOPE_MALFORMED")

    def test_negative_vectors(self):
        cases = {
            "kind": ("kind", "bundle", "SIGNATURE_INVALID"),
            "env": ("env", "staging", "TENANT_MISMATCH"),
            "tenant": ("tenant", "other", "TENANT_MISMATCH"),
            "digest": ("digest", "0" * 64, "SIGNATURE_INVALID"),
            "signer": ("signer", "spiffe://acme/prod/mallory", "IDENTITY_MISMATCH"),
            "kid": ("kid", "acme/site-a/prod/software:nope@1", "SIGNER_UNTRUSTED"),
            "issued_at": ("issued_at", T0 + 1, "SIGNATURE_INVALID"),
            "alg": ("alg", "ecdsa-p256-sha256", "ALG_DOWNGRADE"),
            "alg_hmac": ("alg", "HMAC-SHA256-REF-v2", "ALG_DOWNGRADE"),
            "alg_unknown": ("alg", "ed448", "ALG_DOWNGRADE"),
            "policy_domain": ("policy_domain", "other", "SIGNATURE_INVALID"),
            "digest_alg": ("digest_alg", "md5", "ALG_UNSUPPORTED"),
            "refs": ("refs", ["b", "a"], "ENVELOPE_MALFORMED"),
        }
        for name, (field, value, expect) in cases.items():
            env = dict(self.env)
            env[field] = value
            with self.subTest(name=name):
                got = self.code(env, digest_hex=D if field != "digest" else D)
                self.assertIn(got, {expect, "SIGNATURE_INVALID", "ALG_DOWNGRADE", "ALG_UNSUPPORTED"} if name.startswith("alg") else {expect})

    def test_truncated_and_malformed_signature(self):
        for sig in (self.env["sig"][:-4], self.env["sig"] + "A", self.env["sig"] + "=", "!!!", ""):
            env = dict(self.env, sig=sig)
            with self.subTest(sig=sig[-6:]):
                self.assertIn(self.code(env), {"SIGNATURE_INVALID", "ENVELOPE_MALFORMED"})

    def test_missing_extra_and_legacy(self):
        env = dict(self.env)
        del env["nonce"]
        self.assertEqual(self.code(env), "ENVELOPE_MALFORMED")
        self.assertEqual(self.code(dict(self.env, extra=1)), "ENVELOPE_MALFORMED")
        self.assertEqual(self.code(dict(self.env, v=2)), "ENVELOPE_VERSION_UNSUPPORTED")
        self.assertEqual(self.code({"schema": "PK_SIGNATURE/1", "mac": "x"}), "ENVELOPE_VERSION_UNSUPPORTED")
        self.assertEqual(self.code({"schema": "PK_SIGNATURE/2"}), "ENVELOPE_VERSION_UNSUPPORTED")

    def test_wrong_request_context(self):
        self.assertEqual(self.code(self.env, kind="bundle"), "SIGNATURE_INVALID")
        self.assertEqual(self.code(self.env, digest_hex=artifact_digest(b"other")), "SIGNATURE_INVALID")
        self.assertEqual(self.code(self.env, policy_domain="other"), "SIGNATURE_INVALID")
        other_ns = PKI(ns=Namespace("acme", "site-b", "prod")).trust()
        self.assertEqual(self.code(self.env, trust=other_ns), "TENANT_MISMATCH")

    def test_freshness(self):
        self.assertEqual(self.code(self.env, now=T0 + 1000, max_age_s=100), "SIGNATURE_EXPIRED")
        early = self.pki.trust(issued_at=T0 - 5000)
        self.assertEqual(self.code(self.env, now=T0 - 1000, trust=early), "SIGNATURE_FUTURE")
        self.assertEqual(self.code(self.env, now=T0 - 1000), "TRUST_CORRUPT")  # trust generation from the future

    def test_domain_separation_is_unambiguous(self):
        a = dict(self.env, signer="ab", kid="c")
        b = dict(self.env, signer="a", kid="bc")
        self.assertNotEqual(signed_message(a), signed_message(b))

    def test_reference_hmac_never_production(self):
        with self.assertRaises(GapError) as cm:
            algs.get("HMAC-SHA256-REF-v2")
        self.assertEqual(cm.exception.code, "ALG_REFERENCE_ONLY")

    def test_key_shape_does_not_select_algorithm(self):
        # an Ed25519 key presented as ECDSA must be refused, not "auto-detected"
        with self.assertRaises(GapError) as cm:
            algs.load_public_key("ecdsa-p256-sha256", algs.spki(algs.generate_private_key("ed25519").public_key()))
        self.assertEqual(cm.exception.code, "KEY_POLICY_VIOLATION")


if __name__ == "__main__":
    unittest.main()
