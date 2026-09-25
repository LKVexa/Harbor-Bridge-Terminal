"""Dependency-free security regression tests for GAP-07 v5.0.0."""
from __future__ import annotations

import copy
import json
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap07_artifact_provenance_signing.core import (  # noqa: E402
    AuditLedger,
    InMemoryKeyProvider,
    ProvenanceInvalid,
    Signature,
    SignatureInvalid,
    SignerUntrusted,
    TrustStore,
    Unsigned,
    digest,
    digest_chunks,
    provenance,
    verify_provenance,
)


class CoreSecurityTest(unittest.TestCase):
    def setUp(self):
        self.keys = InMemoryKeyProvider({
            "release-k1": b"release-reference-key-0001",
            "release-k2": b"release-reference-key-0002",
            "data-k1": b"data-reference-key-00000001",
        })
        self.audit = AuditLedger()
        self.store = TrustStore("prod", self.keys, audit=self.audit)
        self.store.add("release-bot", "release", "release-k1", now=1)
        self.store.add("data-bot", "data", "data-k1", now=1)
        self.payload = b"executable-bytes"

    def test_valid_signature_and_round_trip(self):
        sig = self.store.sign("release-bot", self.payload, "code", now=10)
        decoded = Signature.from_dict(json.loads(json.dumps(sig.to_dict())))
        result = self.store.verify(decoded, self.payload, "code", now=11)
        self.assertTrue(result["verified"])
        self.assertEqual(result["digest"], digest(self.payload))

    def test_unsigned_fails_closed(self):
        with self.assertRaises(Unsigned):
            self.store.verify(None, self.payload, "code", now=11)

    def test_byte_substitution_fails(self):
        sig = self.store.sign("release-bot", self.payload, "code", now=10)
        with self.assertRaises(SignatureInvalid):
            self.store.verify(sig, b"substitution", "code", now=11)

    def test_same_role_cross_kind_replay_fails(self):
        sig = self.store.sign("release-bot", self.payload, "code", now=10)
        with self.assertRaises(SignatureInvalid):
            self.store.verify(sig, self.payload, "bundle", now=11)

    def test_cross_environment_replay_fails(self):
        sig = self.store.sign("release-bot", self.payload, "code", now=10)
        other = TrustStore("staging", self.keys)
        other.add("release-bot", "release", "release-k1")
        with self.assertRaises(SignatureInvalid):
            other.verify(sig, self.payload, "code", now=11)

    def test_role_confusion_fails_before_signing(self):
        with self.assertRaises(SignerUntrusted):
            self.store.sign("data-bot", self.payload, "code", now=10)

    def test_revocation_invalidates_prior_signature(self):
        sig = self.store.sign("release-bot", self.payload, "code", now=10)
        self.store.revoke("release-bot", now=11)
        with self.assertRaises(SignerUntrusted):
            self.store.verify(sig, self.payload, "code", now=12)

    def test_rotation_can_retain_then_retire_old_key(self):
        old = self.store.sign("release-bot", self.payload, "code", now=10)
        self.store.rotate("release-bot", "release-k2", retain_previous=True, now=11)
        self.assertTrue(self.store.verify(old, self.payload, "code", now=12)["verified"])
        self.store.retire_key("release-bot", "release-k1", now=13)
        with self.assertRaises(SignerUntrusted):
            self.store.verify(old, self.payload, "code", now=14)

    def test_signature_freshness_policy(self):
        sig = self.store.sign("release-bot", self.payload, "code", now=10)
        self.assertTrue(self.store.verify(sig, self.payload, "code", now=20, max_age_seconds=10)["verified"])
        with self.assertRaises(SignatureInvalid):
            self.store.verify(sig, self.payload, "code", now=21, max_age_seconds=10)

    def test_malformed_signature_is_structured_refusal(self):
        sig = self.store.sign("release-bot", self.payload, "code", now=10).to_dict()
        sig["digest"] = "not-a-digest"
        with self.assertRaises(SignatureInvalid) as ctx:
            self.store.verify(sig, self.payload, "code", now=11)
        self.assertEqual(ctx.exception.code, "SIGNATURE_INVALID")
        self.assertIn("code", ctx.exception.as_dict())

    def test_duplicate_signer_cannot_silently_change_role_or_key(self):
        with self.assertRaises(ValueError):
            self.store.add("release-bot", "release", "release-k2")
        with self.assertRaises(ValueError):
            self.store.add("release-bot", "data", "data-k1")

    def test_trust_snapshot_contains_metadata_not_secrets(self):
        snapshot = self.store.snapshot()
        encoded = json.dumps(snapshot, sort_keys=True)
        self.assertEqual(snapshot["schema"], "PK_TRUST_STORE/2")
        self.assertIn("release-k1", encoded)
        self.assertNotIn("release-reference-key", encoded)

    def test_key_provider_repr_does_not_expose_secret(self):
        rendered = repr(self.keys)
        self.assertNotIn("release-reference-key", rendered)
        self.assertIn("key_count=3", rendered)

    def test_stream_digest_matches_bytes_digest(self):
        self.assertEqual(digest_chunks([b"exec", b"utable", b"-bytes"]), digest(self.payload))

    def test_provenance_verifies_and_binds_metadata(self):
        payloads = [b"src", b"obj", self.payload]
        record = provenance([("source", payloads[0]), ("build", payloads[1]), ("package", payloads[2])])
        result = verify_provenance(record, payloads)
        self.assertTrue(result["verified"])

        tampered = copy.deepcopy(record)
        tampered["links"][1]["step"] = "publish"
        with self.assertRaises(ProvenanceInvalid):
            verify_provenance(tampered, payloads)

        reordered = copy.deepcopy(record)
        reordered["links"][0], reordered["links"][1] = reordered["links"][1], reordered["links"][0]
        with self.assertRaises(ProvenanceInvalid):
            verify_provenance(reordered, payloads)

        with self.assertRaises(ProvenanceInvalid):
            verify_provenance(record, [b"src", b"tampered", self.payload])

    def test_audit_chain_detects_tampering(self):
        sig = self.store.sign("release-bot", self.payload, "code", now=10)
        self.store.verify(sig, self.payload, "code", now=11)
        self.assertTrue(self.audit.verify())
        self.audit.events[0]["details"]["role"] = "authority"
        self.assertFalse(self.audit.verify())


if __name__ == "__main__":
    unittest.main()
