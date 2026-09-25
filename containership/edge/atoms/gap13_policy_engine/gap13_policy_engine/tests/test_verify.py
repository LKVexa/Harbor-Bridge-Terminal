"""G13-MC-001 cryptographic verification adapter: golden + negative vectors."""
import base64
import json
import unittest

import testkit as k
from gap13_policy_engine.canonical import canonical_bytes
from gap13_policy_engine.errors import DependencyUnavailable
from gap13_policy_engine.verify import VerificationState as S

g = k.g


def mutate(env: bytes, fn) -> bytes:
    d = json.loads(env)
    fn(d)
    return canonical_bytes(d)


class VerifyTests(unittest.TestCase):
    def test_valid(self):
        r = k.verifier().verify(k.envelope(), now=k.T0)
        self.assertEqual(r.state, S.VERIFIED)
        self.assertEqual(r.evidence()["trust_store_version"], "ts-1")

    def test_negative_vectors(self):
        env = k.envelope()
        payload = base64.b64decode(json.loads(env)["payload_b64"])
        tampered = payload.replace(b'"deny"', b'"allow"')

        def swap_payload(d):
            d["payload_b64"] = base64.b64encode(tampered).decode()
        cases = {
            "modified-bytes": (mutate(env, swap_payload), S.REJECTED),
            "modified-bytes-digest-fixed": (mutate(env, lambda d: (swap_payload(d), d.__setitem__("digest", "sha256:" + __import__("hashlib").sha256(tampered).hexdigest()))), S.REJECTED),
            "wrong-signer-key": (k.envelope(seed=k.ROGUE), S.REJECTED),
            "unknown-signer": (k.envelope(key_id="nope"), S.UNKNOWN_SIGNER),
            "alg-confusion": (mutate(env, lambda d: d["signature"].__setitem__("alg", "hmac-sha256")), S.UNSUPPORTED_ALGORITHM),
            "alg-none": (mutate(env, lambda d: d["signature"].__setitem__("alg", "none")), S.UNSUPPORTED_ALGORITHM),
            "malformed-sig": (mutate(env, lambda d: d["signature"].__setitem__("value_b64", "!!!")), S.REJECTED),
            "short-sig": (mutate(env, lambda d: d["signature"].__setitem__("value_b64", "AAAA")), S.REJECTED),
            "extra-field": (mutate(env, lambda d: d.__setitem__("verified", True)), S.REJECTED),
            "garbage": (b"not json", S.REJECTED),
            "wrong-env": (k.envelope(environment="staging"), S.REJECTED),
            "wrong-issuer": (k.envelope(issuer="someone-else"), S.REJECTED),
            "future": (k.envelope(issued_at=k.T0 + 10_000), S.REJECTED),
            "expired-bundle": (k.envelope(expires_at=k.T0 - 1, issued_at=k.T0 - 100), S.EXPIRED),
        }
        for name, (e, want) in cases.items():
            with self.subTest(name):
                r = k.verifier().verify(e, now=k.T0)
                self.assertEqual(r.state, want, r.reason)
                self.assertFalse(r.verified)
                self.assertIsNone(r.bundle)

    def test_key_lifecycle(self):
        for over, want in [({"revoked": True}, S.REVOKED), ({"compromised": True}, S.REVOKED),
                           ({"not_after": k.T0 - 1}, S.EXPIRED), ({"not_before": k.T0 + 1}, S.EXPIRED),
                           ({"purpose": "code-signing"}, S.REJECTED), ({"environments": ("dev",)}, S.REJECTED),
                           ({"algorithm": "rsa-pss"}, S.UNSUPPORTED_ALGORITHM)]:
            with self.subTest(over):
                v = k.verifier(store=k.trust_store(**over))
                self.assertEqual(v.verify(k.envelope(), now=k.T0).state, want)

    def test_stale_trust_store(self):
        ts = k.trust_store()
        ts = g.TrustStore(ts.version, ts.keys, fetched_at=k.T0 - 100_000)
        self.assertEqual(k.verifier(store=ts).verify(k.envelope(), now=k.T0).state, S.REJECTED)

    def test_trust_source_outage_fails_closed(self):
        class Down:
            def trust_store(self):
                raise ConnectionError("gap-07 down")
        v = g.BundleVerifier(Down(), environment="prod")
        with self.assertRaises(DependencyUnavailable):
            v.verify(k.envelope(), now=k.T0)

    def test_no_negotiation(self):
        with self.assertRaises(ValueError):
            g.BundleVerifier(g.StaticTrustSource(k.trust_store()), environment="prod", allowed_algorithms=("none",))

    def test_trust_store_from_fixture(self):
        import pathlib
        doc = json.loads((pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "trust_store.json").read_text())
        ts = g.TrustStore.from_dict(doc)
        self.assertTrue(k.verifier(store=ts).verify(k.envelope(), now=k.T0).verified)

    def test_verified_bytes_are_parsed_bytes(self):
        r = k.verifier().verify(k.envelope(), now=k.T0)
        self.assertIsInstance(r.payload, bytes)
        self.assertEqual(r.bundle.digest, r.digest)


if __name__ == "__main__":
    unittest.main()
