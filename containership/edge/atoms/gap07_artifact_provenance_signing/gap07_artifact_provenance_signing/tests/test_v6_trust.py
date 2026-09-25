import datetime
import unittest
from dataclasses import replace

from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing.errors import GapError
from gap07_artifact_provenance_signing.tests.fixtures import IDENT, NS, PKI, T0
from gap07_artifact_provenance_signing.trust import Anchor, TrustGeneration, issue_cert, validate_x509


class TrustModel(unittest.TestCase):
    def setUp(self):
        self.pki = PKI()
        self.kid = self.pki.refs["k1"].kid

    def code(self, trust, now=T0, purpose="sign:code", kid=None):
        with self.assertRaises(GapError) as cm:
            trust.resolve_kid(kid or self.kid, now, purpose=purpose)
        return cm.exception.code

    def test_valid_chain_records_generation(self):
        t = self.pki.trust(generation=7)
        v = t.resolve_kid(self.kid, T0, purpose="sign:code")
        self.assertEqual((v.identity, v.generation), (IDENT, 7))
        self.assertEqual(t.trust_report(self.kid, T0, "sign:code")["result"], "trusted")

    def test_refusals_are_distinct(self):
        self.assertEqual(self.code(self.pki.trust(), now=T0 + 10**7), "CERT_EXPIRED")
        self.assertEqual(self.code(self.pki.trust(), now=T0 - 10**5), "CERT_NOT_YET_VALID")
        self.assertEqual(self.code(self.pki.trust(revoked_serials=frozenset({"leaf-k1"}))), "CERT_REVOKED")
        self.assertEqual(self.code(self.pki.trust(revoked_kids=frozenset({self.kid}))), "CERT_REVOKED")
        self.assertEqual(self.code(self.pki.trust(revoked_identities=frozenset({IDENT}))), "CERT_REVOKED")
        self.assertEqual(self.code(self.pki.trust(revoked_serials=frozenset({"int-1"}))), "CERT_REVOKED")
        self.assertEqual(self.code(self.pki.trust(), purpose="sign:policy"), "CERT_USAGE")
        retired = replace(self.pki.anchor, state="retired")
        self.assertEqual(self.code(self.pki.trust(anchors=(retired,))), "CHAIN_UNTRUSTED")
        self.assertEqual(self.code(self.pki.trust(anchors=())), "CHAIN_UNTRUSTED")
        self.assertEqual(self.code(self.pki.trust(), kid="acme/site-a/prod/x:y@1"), "SIGNER_UNTRUSTED")

    def test_name_constraints_cannot_be_escaped(self):
        self.pki.add_signer("spiffe://evil/prod/bot", "evil")
        self.assertEqual(self.code(self.pki.trust(), kid=self.pki.refs["evil"].kid), "NAME_CONSTRAINT")

    def test_path_length(self):
        tight = replace(self.pki.anchor, max_path_len=0)
        self.assertEqual(self.code(self.pki.trust(anchors=(tight,))), "PATH_LENGTH")

    def test_untrusted_root_and_alternate_path_do_not_broaden(self):
        rogue = algs.generate_private_key("ed25519")
        rogue_inter = issue_cert(issuer_id="rogue-root", issuer_alg="ed25519", issuer_sign=algs.software_signer("ed25519", rogue),
                                 serial="int-rogue", subject="spiffe://acme/ca/rogue", namespace=NS, kid="rk", alg="ed25519",
                                 spki=algs.spki(algs.generate_private_key("ed25519").public_key()), usages=["ca"],
                                 not_before=T0 - 10, not_after=T0 + 10**6, path_len=0)
        t = self.pki.trust(certs=tuple(self.pki.certs) + (rogue_inter,))
        v = t.resolve_kid(self.kid, T0, purpose="sign:code")
        self.assertEqual(v.path[0], "root-1")  # rogue path never chosen / never broadens

    def test_forged_certificate_signature(self):
        certs = list(self.pki.certs)
        leaf = dict(certs[-1], usages=sorted(certs[-1]["usages"] + ["sign:grant"]))
        certs[-1] = leaf
        self.assertEqual(self.code(self.pki.trust(certs=tuple(certs))), "SIGNATURE_INVALID")

    def test_stale_generation_and_bounds(self):
        with self.assertRaises(GapError) as cm:
            self.pki.trust(issued_at=T0 - 10**6).check_fresh(T0)
        self.assertEqual(cm.exception.code, "TRUST_STALE")
        dup = tuple(self.pki.certs) + (self.pki.certs[-1],)
        with self.assertRaises(GapError):
            self.pki.trust(certs=dup)

    def test_kid_must_be_namespace_qualified_and_unique(self):
        leaf = dict(self.pki.certs[-1], serial="leaf-dup")
        with self.assertRaises(GapError) as cm:
            self.pki.trust(certs=tuple(self.pki.certs) + (leaf,))
        self.assertEqual(cm.exception.code, "KEY_ID_COLLISION")

    def test_round_trip_serialisation_is_stable(self):
        t = self.pki.trust()
        t2 = TrustGeneration.from_dict(t.to_dict())
        self.assertEqual(t.digest, t2.digest)


class X509Interop(unittest.TestCase):
    def _chain(self, eku_code_signing=True, expired=False):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
        now = datetime.datetime.fromtimestamp(T0, datetime.timezone.utc)
        rk = ec.generate_private_key(ec.SECP256R1())
        lk = ec.generate_private_key(ec.SECP256R1())
        rname = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "GAP07 Test Root")])
        root = (x509.CertificateBuilder().subject_name(rname).issuer_name(rname).public_key(rk.public_key()).serial_number(1)
                .not_valid_before(now - datetime.timedelta(days=10)).not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
                .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(rk.public_key()), critical=False)
                .sign(rk, hashes.SHA256()))
        end = now - datetime.timedelta(days=1) if expired else now + datetime.timedelta(days=30)
        eku = [ExtendedKeyUsageOID.CODE_SIGNING] if eku_code_signing else [ExtendedKeyUsageOID.SERVER_AUTH]
        leaf = (x509.CertificateBuilder().subject_name(x509.Name([])).issuer_name(rname).public_key(lk.public_key()).serial_number(2)
                .not_valid_before(now - datetime.timedelta(days=5)).not_valid_after(end)
                .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(IDENT)]), critical=True)
                .add_extension(x509.ExtendedKeyUsage(eku), critical=False)
                .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(rk.public_key()), critical=False)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .sign(rk, hashes.SHA256()))
        der = serialization.Encoding.DER
        return leaf.public_bytes(der), root.public_bytes(der)

    def test_code_signing_chain(self):
        leaf, root = self._chain()
        res = validate_x509(leaf, [], [root], T0)
        self.assertEqual(res["identity"], IDENT)

    def test_wrong_eku_and_expired(self):
        leaf, root = self._chain(eku_code_signing=False)
        with self.assertRaises(GapError):
            validate_x509(leaf, [], [root], T0)
        leaf, root = self._chain(expired=True)
        with self.assertRaises(GapError):
            validate_x509(leaf, [], [root], T0)

    def test_untrusted_root(self):
        leaf, _ = self._chain()
        _, other_root = self._chain()
        with self.assertRaises(GapError) as cm:
            validate_x509(leaf, [], [other_root], T0)
        self.assertEqual(cm.exception.code, "CHAIN_UNTRUSTED")


if __name__ == "__main__":
    unittest.main()
