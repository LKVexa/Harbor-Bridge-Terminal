"""Components 02 (signature/provenance), 04 (key lifecycle), 10 (canonical profile)."""
import json
import os
import unittest

from fixtures import PK_A, SK_A, seed, sample, signed, make_stack, tmpdir
from gap09_unified_observability.components import ed25519
from gap09_unified_observability.components.canonical import canonicalize, canonical_bytes
from gap09_unified_observability.components.errors import Malformed
from gap09_unified_observability.components.keys import Ed25519Verifier, KeyRecord, KeyRegistry
from gap09_unified_observability.runtime import ReporterUntrusted

VEC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vectors")


class TestEd25519RFC8032(unittest.TestCase):
    def test_rfc8032_vectors(self):
        with open(os.path.join(VEC, "rfc8032_ed25519.json")) as fh:
            vecs = json.load(fh)
        for v in vecs:
            sk, pk, msg, sig = (bytes.fromhex(v[k]) for k in ("secret", "public", "message", "signature"))
            self.assertEqual(ed25519.public_key(sk), pk)
            self.assertEqual(ed25519.sign(sk, msg), sig)
            self.assertTrue(ed25519.verify(pk, msg, sig))

    def test_negative_vectors(self):
        msg = b"payload"
        sig = ed25519.sign(SK_A, msg)
        self.assertFalse(ed25519.verify(PK_A, msg + b"x", sig))                  # altered payload
        self.assertFalse(ed25519.verify(PK_A, msg, sig[:63]))                    # truncated
        bad = bytearray(sig); bad[0] ^= 1
        self.assertFalse(ed25519.verify(PK_A, msg, bytes(bad)))                  # corrupted R
        s = int.from_bytes(sig[32:], "little") + ed25519.L                       # malleated S (S+L)
        self.assertFalse(ed25519.verify(PK_A, msg, sig[:32] + s.to_bytes(32, "little")))
        self.assertFalse(ed25519.verify(ed25519.public_key(seed("other")), msg, sig))  # wrong key
        self.assertFalse(ed25519.verify(b"\xff" * 32, msg, sig))                 # invalid point


class TestCanonicalProfile(unittest.TestCase):
    def test_cross_language_vectors(self):
        with open(os.path.join(VEC, "csp1_vectors.json")) as fh:
            vecs = json.load(fh)
        for v in vecs:
            self.assertEqual(canonicalize(v["input"]), v["canonical"], v["name"])

    def test_refusals(self):
        for bad in (float("nan"), float("inf"), -0.0, 2**53 + 1, 10**400, {1: 2}, "\ud800"):
            with self.assertRaises(Malformed):
                canonicalize(bad)
        deep = []
        cur = deep
        for _ in range(20):
            cur.append([]); cur = cur[0]
        with self.assertRaises(Malformed):
            canonicalize(deep)


class TestKeyLifecycleAndVerifier(unittest.TestCase):
    def setUp(self):
        self.ingest, self.reg, self.clock, self.audit = make_stack(tmpdir())

    def test_positive(self):
        self.assertEqual(self.ingest.submit(**signed([sample()])), 1)

    def test_unknown_key_swapped_key_and_revoked(self):
        with self.assertRaises(ReporterUntrusted):
            self.ingest.submit(**signed([sample()], key_id="nope"))
        other = seed("b")
        self.reg.add(KeyRecord("kb", "rep-b", "ed25519", ed25519.public_key(other), 0, 10**9, frozenset({"t1"})), actor="t")
        with self.assertRaises(ReporterUntrusted):  # key belongs to another reporter
            self.ingest.submit(**signed([sample()], key_id="kb", sid="x2", sk=other))
        self.reg.revoke("k1", actor="t", reason="compromise")
        with self.assertRaises(ReporterUntrusted) as cm:
            self.ingest.submit(**signed([sample()], sid="x3"))
        self.assertEqual(cm.exception.details["reason"], "revoked")

    def test_rotation_overlap_then_expiry(self):
        sk2 = seed("rep-a-2")
        self.reg.rotate("k1", KeyRecord("k2", "rep-a", "ed25519", ed25519.public_key(sk2), 0, 10**9, frozenset({"t1"})),
                        overlap_until=1001, actor="t")
        self.assertEqual(self.ingest.submit(**signed([sample()], sid="o1")), 1)      # old key inside overlap
        self.assertEqual(self.ingest.submit(**signed([sample(at=101)], sid="o2", key_id="k2", sk=sk2)), 1)
        self.clock.now = self.clock.synced = 1001
        with self.assertRaises(ReporterUntrusted):
            self.ingest.submit(**signed([sample(at=102)], sid="o3", issued=1001))   # boundary: not_after exclusive

    def test_key_id_reuse_and_bad_algorithm_refused(self):
        with self.assertRaises(Malformed):
            self.reg.add(KeyRecord("k1", "rep-a", "ed25519", PK_A, 0, 10, frozenset({"t1"})), actor="t")
        with self.assertRaises(Malformed):
            KeyRecord("k9", "rep-a", "rsa-1024", PK_A, 0, 10, frozenset({"t1"}))

    def test_signature_encoding_single_form(self):
        args = signed([sample()])
        args["signature"] = args["signature"].upper()
        with self.assertRaises(ReporterUntrusted):
            self.ingest.submit(**args)

    def test_payload_substitution(self):
        args = signed([sample(value=1.0)])
        args["samples"] = [sample(value=2.0)]
        with self.assertRaises(ReporterUntrusted):
            self.ingest.submit(**args)

    def test_transcript_recorded_without_secrets(self):
        v = self.ingest.verifier
        self.ingest.submit(**signed([sample()]))
        t = v.transcripts[-1]
        for k in ("envelope_sha256", "key_id", "algorithm", "fingerprint", "verifier_build", "outcome"):
            self.assertIn(k, t)
        self.assertNotIn(SK_A.hex(), json.dumps(t))

    def test_audit_chain_covers_key_events(self):
        self.reg.revoke("k1", actor="t", reason="r")
        kinds = [e["kind"] for e in self.audit.entries()]
        self.assertIn("key_lifecycle", kinds)
        self.audit.verify(self.audit.head())


if __name__ == "__main__":
    unittest.main()
