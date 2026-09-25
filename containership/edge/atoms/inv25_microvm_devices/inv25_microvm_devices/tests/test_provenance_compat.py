"""Item 18 (artifact verification, C045), items 1/12 (pk_core startup check, negotiation C027/C093)."""
import os
import subprocess
import sys
import unittest

from _support import PKG_DIR, ROOT, compat, provenance

K = b"release-signer-test-key"


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.data = b'{"schema":"PK_DEVICE_CATALOGUE/1"}'
        self.pol = provenance.TrustPolicy(signers={"rel": K})
        self.att = provenance.attest(self.data, artifact_type="catalogue", name="prod", version="7",
                                     signer="rel", key=K, source_revision="abc", builder="ci")

    def ok(self, **kw):
        a = dict(artifact_type="catalogue", name="prod", version="7")
        a.update(kw)
        return a

    def test_valid_accepted(self):
        self.assertTrue(self.pol.verify(self.data, self.att, **self.ok())["verified"])

    def test_rejections(self):
        bad_sig = dict(self.att, signature="0" * 64)
        other = provenance.attest(self.data, artifact_type="catalogue", name="prod", version="7",
                                  signer="rel", key=b"other")
        cases = {
            "modified": (self.data + b" ", self.att, self.ok()),
            "bad signature": (self.data, bad_sig, self.ok()),
            "wrong signer key": (self.data, other, self.ok()),
            "replayed to other name": (self.data, self.att, self.ok(name="staging")),
            "replayed to other type": (self.data, self.att, self.ok(artifact_type="policy")),
            "missing attestation": (self.data, None, self.ok()),
            "unknown format": (self.data, dict(self.att, schema="x"), self.ok()),
            "unknown scheme": (self.data, dict(self.att, scheme="rsa"), self.ok()),
        }
        for name, (d, a, kw) in cases.items():
            with self.subTest(name), self.assertRaises(provenance.ArtifactVerificationFailed):
                self.pol.verify(d, a, **kw)

    def test_revoked_and_untrusted_signer(self):
        self.pol.revoked.add("rel")
        self.assertRaises(provenance.ArtifactVerificationFailed, self.pol.verify, self.data, self.att, **self.ok())
        pol2 = provenance.TrustPolicy(signers={})
        self.assertRaises(provenance.ArtifactVerificationFailed, pol2.verify, self.data, self.att, **self.ok())

    def test_approved_version_manifest(self):
        self.pol.approved_versions[("catalogue", "prod")] = {"6"}
        self.assertRaises(provenance.ArtifactVerificationFailed, self.pol.verify, self.data, self.att, **self.ok())


class StoreArtifactAuditTest(unittest.TestCase):
    def test_verification_outcomes_are_audited(self):
        from _support import Clock, store, verifier
        s = store.CatalogueStore("prod", verifier(Clock()))
        data = b"{}"
        pol = provenance.TrustPolicy(signers={"rel": K})
        att = provenance.attest(data, artifact_type="policy", name="p", version="1", signer="rel", key=K)
        s.verify_artifact(data, att, pol, artifact_type="policy", name="p", version="1")
        with self.assertRaises(provenance.ArtifactVerificationFailed):
            s.verify_artifact(data + b"x", att, pol, artifact_type="policy", name="p", version="1")
        self.assertEqual([e["event_type"] for e in s.audit.events], ["artifact.verified", "artifact.verification_failed"])
        self.assertEqual(s.signals()["artifact_verification_failed"], 1)


class CompatTest(unittest.TestCase):
    def test_negotiation(self):
        self.assertEqual(compat.negotiate("catalogue", ["PK_DEVICE_CATALOGUE/1"]), "PK_DEVICE_CATALOGUE/1")
        self.assertEqual(compat.negotiate("catalogue", ["PK_DEVICE_CATALOGUE/9", "PK_DEVICE_CATALOGUE/1"]),
                         "PK_DEVICE_CATALOGUE/1")

    def test_fail_closed(self):
        for offers in ([], ["PK_DEVICE_CATALOGUE/0"], ["PK_DEVICE_CATALOGUE/2"], ["garbage", None],
                       ["PK_DEVICE_SURFACE_DIFF/1"]):
            with self.subTest(offers), self.assertRaises(compat.CompatibilityMismatch):
                compat.negotiate("catalogue", offers)
        self.assertRaises(compat.CompatibilityMismatch, compat.negotiate, "nope", ["x"])

    def test_pk_core_version_gate(self):
        self.assertEqual(compat.check_pk_core("4.2.1"), "4.2.1")
        for bad in (None, "", "3.9", "5.0", "x.y"):
            with self.subTest(bad), self.assertRaises(compat.CompatibilityMismatch):
                compat.check_pk_core(bad)

    def test_matrix_claims_are_honest(self):
        for row in compat.MATRIX:
            if row["status"] == "supported":
                self.assertTrue(row["evidence"], row)

    def test_bootstrap_machine_readable_when_missing(self):
        env = {k: v for k, v in os.environ.items() if k != "PK_CORE_PATH"}
        env["PK_CORE_PATH"] = "/nonexistent-dev-path"
        env["INV25_RELEASE"] = "1"
        out = subprocess.run([sys.executable, "-m", PKG_DIR.name + ".pk_bootstrap"], cwd=str(ROOT),
                             capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 3)
        self.assertIn('"code": "INV25_DEPENDENCY_UNAVAILABLE"', out.stdout)


if __name__ == "__main__":
    unittest.main()
