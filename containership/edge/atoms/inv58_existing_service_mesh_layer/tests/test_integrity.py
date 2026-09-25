"""MC-012: artifact / policy signature, digest, provenance and approved-version verification."""
from __future__ import annotations

import unittest

from _support import KEYS, errors, integrity as I, make_service, publisher

KEY = KEYS["inv58/artifact"]
DATA = b"policy-bundle-bytes"


def manifest(**over):
    m = {"schema": I.MANIFEST_SCHEMA, "name": "mesh-policy", "version": "1.2.0", "digest": I.sha256_bytes(DATA),
         "builder": "ci://pipeline/7", "source_repo": "git://inv58", "source_rev": "abc123", "built_at": "2026-09-22T00:00:00Z"}
    m.update(over)
    m["signature"] = I.sign_manifest(m, KEY)
    return m


class IntegrityTest(unittest.TestCase):
    def setUp(self):
        self.v = I.Verifier(I.hmac_check(lambda: KEY), {"mesh-policy": frozenset({"1.2.0"})})

    def test_accept(self):
        self.assertTrue(self.v.verify(manifest(), DATA)["verified"])

    def test_every_failure_mode_fails_closed(self):
        cases = {
            "tampered bytes": (manifest(), DATA + b"!"),
            "unapproved version": (manifest(version="9.9.9"), DATA),
            "missing provenance": ({k: v for k, v in manifest().items() if k != "builder"}, DATA),
            "bad schema": (manifest(schema="X/1"), DATA),
        }
        forged = manifest()
        forged["version"] = "1.2.0-evil"
        cases["forged after signing"] = (forged, DATA)
        for name, (m, d) in cases.items():
            with self.subTest(name):
                with self.assertRaises(errors.MeshError) as cm:
                    self.v.verify(m, d)
                self.assertEqual(cm.exception.code, "E_INTEGRITY")

    def test_signer_outage_and_revocation(self):
        def down():
            raise ConnectionError()
        with self.assertRaises(errors.MeshError):
            I.Verifier(I.hmac_check(down), {"mesh-policy": frozenset({"1.2.0"})}).verify(manifest(), DATA)
        v = I.Verifier(I.hmac_check(lambda: KEY), {"mesh-policy": frozenset({"1.2.0"})}, revoked=frozenset({I.sha256_bytes(DATA)}))
        with self.assertRaises(errors.MeshError):
            v.verify(manifest(), DATA)

    def test_service_audits_integrity_failures(self):
        svc, clock, _ = make_service()
        with self.assertRaises(errors.MeshError):
            svc.verify_artifact(publisher(clock), manifest(), DATA + b"x", {"mesh-policy": frozenset({"1.2.0"})})
        self.assertIn("integrity.failure", [r["type"] for r in svc.audit.records()])
        ok = svc.verify_artifact(publisher(clock), manifest(), DATA, {"mesh-policy": frozenset({"1.2.0"})})
        self.assertTrue(ok["verified"])


if __name__ == "__main__":
    unittest.main()
