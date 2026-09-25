import base64
import time
import unittest

from cryptography.hazmat.primitives import serialization

from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing.errors import GapError
from gap07_artifact_provenance_signing.keys import (AwsKmsCustody, AzureKeyVaultCustody, CustodyPolicy, GcpKmsCustody, KeyRef,
                                                    Pkcs11Custody, ResilientCustody, SoftwareKeyCustody, VaultTransitCustody)

MSG = b"GAP07 signed bytes"


class ClientError(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}


class FakeAwsKms:
    """Mirrors the boto3 KMS request/response shapes used by the adapter."""

    def __init__(self, alg="ecdsa-p256-sha256"):
        self.key = algs.generate_private_key(alg)
        self.alg = alg
        self.fail = []
        self.state = "Enabled"
        self.sign_calls = 0
        self.swap_key = False

    def _maybe_fail(self):
        if self.fail:
            raise self.fail.pop(0)

    def sign(self, KeyId, Message, SigningAlgorithm, MessageType):
        self._maybe_fail()
        self.sign_calls += 1
        k = algs.generate_private_key(self.alg) if self.swap_key else self.key
        return {"KeyId": f"arn:aws:kms:us-east-1:1:key/{KeyId}", "Signature": algs.software_signer(self.alg, k)(Message), "SigningAlgorithm": SigningAlgorithm}

    def get_public_key(self, KeyId):
        self._maybe_fail()
        return {"PublicKey": algs.spki(self.key.public_key()), "SigningAlgorithms": ["ECDSA_SHA_256"]}

    def describe_key(self, KeyId):
        self._maybe_fail()
        return {"KeyMetadata": {"KeyState": self.state, "Enabled": self.state == "Enabled", "Origin": "AWS_KMS"}}


def aws_ref():
    return KeyRef("aws-kms", "acme", "site-a", "prod", "alias/release", "1234abcd-12ab-34cd-56ef-1234567890ab", "ecdsa-p256-sha256", region="us-east-1")


class Custody(unittest.TestCase):
    def resilient(self, fake, **pol):
        ref = aws_ref()
        return ref, ResilientCustody(AwsKmsCustody(fake), {ref.kid: algs.spki(fake.key.public_key())},
                                     CustodyPolicy(timeout_s=0.5, backoff_s=0.0, **pol))

    def test_aws_sign_and_policy(self):
        fake = FakeAwsKms()
        ref, rc = self.resilient(fake)
        sig = rc.sign(ref, MSG)
        algs.verify_raw(ref.algorithm, algs.spki(fake.key.public_key()), sig, MSG)
        self.assertEqual(rc.check_key_policy(ref).protection_level, "hsm")

    def test_transient_retry_then_success(self):
        fake = FakeAwsKms()
        fake.fail = [ClientError("ThrottlingException")]
        ref, rc = self.resilient(fake)
        self.assertTrue(rc.sign(ref, MSG))

    def test_transient_exhaustion_is_key_unavailable(self):
        fake = FakeAwsKms()
        fake.fail = [ClientError("KMSInternalException")] * 3
        ref, rc = self.resilient(fake)
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, MSG)
        self.assertEqual(cm.exception.code, "KEY_UNAVAILABLE")
        self.assertTrue(cm.exception.transient)

    def test_permanent_is_key_disabled_no_retry(self):
        fake = FakeAwsKms()
        fake.fail = [ClientError("DisabledException"), ClientError("ThrottlingException")]
        ref, rc = self.resilient(fake)
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, MSG)
        self.assertEqual(cm.exception.code, "KEY_DISABLED")
        self.assertEqual(len(fake.fail), 1)  # not retried

    def test_disabled_key_state(self):
        fake = FakeAwsKms()
        fake.state = "PendingDeletion"
        ref, rc = self.resilient(fake)
        with self.assertRaises(GapError) as cm:
            rc.check_key_policy(ref)
        self.assertEqual(cm.exception.code, "KEY_DISABLED")

    def test_alias_redirect_detected(self):
        fake = FakeAwsKms()
        ref, rc = self.resilient(fake)
        fake.swap_key = True
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, MSG)
        self.assertEqual(cm.exception.code, "KEY_MISMATCH")

    def test_timeout(self):
        fake = FakeAwsKms()
        orig = fake.sign
        fake.sign = lambda **kw: (time.sleep(1.0), orig(**kw))[1]
        ref, rc = self.resilient(fake, max_attempts=1)
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, MSG)
        self.assertEqual(cm.exception.code, "KEY_UNAVAILABLE")

    def test_circuit_breaker(self):
        fake = FakeAwsKms()
        fake.fail = [ClientError("ThrottlingException")] * 100
        ref, rc = self.resilient(fake, max_attempts=1, breaker_threshold=2, breaker_reset_s=60)
        for _ in range(2):
            with self.assertRaises(GapError):
                rc.sign(ref, MSG)
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, MSG)
        self.assertEqual(cm.exception.code, "CIRCUIT_OPEN")

    def test_health_probe_never_signs(self):
        fake = FakeAwsKms()
        ref, rc = self.resilient(fake)
        self.assertTrue(rc.health(ref)["ok"])
        self.assertEqual(fake.sign_calls, 0)

    def test_software_custody_refused_by_production_policy(self):
        sc = SoftwareKeyCustody()
        ref = KeyRef("software", "acme", "site-a", "prod", "dev", "1", "ed25519", protection_level="software")
        spki = sc.create(ref)
        rc = ResilientCustody(sc, {ref.kid: spki})
        with self.assertRaises(GapError) as cm:
            rc.check_key_policy(ref)
        self.assertEqual(cm.exception.code, "KEY_POLICY_VIOLATION")
        self.assertNotIn("PrivateKey", repr(sc))
        self.assertFalse(any(hasattr(sc, n) for n in ("private_key", "export", "get_key")))

    def test_unpinned_kid_refused(self):
        fake = FakeAwsKms()
        ref = aws_ref()
        rc = ResilientCustody(AwsKmsCustody(fake), {})
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, MSG)
        self.assertEqual(cm.exception.code, "KEY_MISMATCH")


class OtherProviders(unittest.TestCase):
    def test_gcp(self):
        key = algs.generate_private_key("ecdsa-p256-sha256")
        pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        from cryptography.hazmat.primitives.asymmetric import ec, utils
        from cryptography.hazmat.primitives import hashes

        class R:  # response objects
            pass

        class FakeGcp:
            def asymmetric_sign(self, request):
                r = R()
                r.name = request["name"]
                r.signature = key.sign(request["digest"]["sha256"], ec.ECDSA(utils.Prehashed(hashes.SHA256())))
                return r

            def get_public_key(self, request):
                r = R()
                r.pem = pem
                return r

            def get_crypto_key_version(self, request):
                r = R()
                r.state, r.protection_level = 1, 2
                return r

        ref = KeyRef("gcp-kms", "acme", "site-a", "prod", "projects/p/locations/l/keyRings/r/cryptoKeys/k", "3", "ecdsa-p256-sha256")
        g = GcpKmsCustody(FakeGcp())
        rc = ResilientCustody(g, {ref.kid: algs.spki(key.public_key())})
        algs.verify_raw(ref.algorithm, algs.spki(key.public_key()), rc.sign(ref, MSG), MSG)
        self.assertEqual(rc.check_key_policy(ref).protection_level, "hsm")

    def test_vault_transit_version_pinning(self):
        key = algs.generate_private_key("ed25519")
        from cryptography.hazmat.primitives import serialization as s
        raw = key.public_key().public_bytes(s.Encoding.Raw, s.PublicFormat.Raw)

        class Transit:
            version = 2

            def sign_data(self, **kw):
                return {"data": {"signature": f"vault:v{self.version}:" + base64.b64encode(key.sign(base64.b64decode(kw["hash_input"]))).decode()}}

            def read_key(self, name, mount_point):
                return {"data": {"type": "ed25519", "keys": {"2": {"public_key": base64.b64encode(raw).decode()}}, "latest_version": 2, "exportable": False, "managed_key_name": "hsm1"}}

        class Client:
            class secrets:
                transit = Transit()

        ref = KeyRef("vault-transit", "acme", "site-a", "prod", "release", "2", "ed25519")
        v = VaultTransitCustody(Client())
        rc = ResilientCustody(v, {ref.kid: algs.spki(key.public_key())})
        self.assertTrue(rc.sign(ref, MSG))
        Client.secrets.transit.version = 3  # key rotated server-side: must not be silently accepted
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, MSG)
        self.assertEqual(cm.exception.code, "KEY_MISMATCH")

    def test_azure_jose_to_der(self):
        from cryptography.hazmat.primitives.asymmetric import ec, utils
        from cryptography.hazmat.primitives import hashes
        key = algs.generate_private_key("ecdsa-p256-sha256")
        nums = key.public_key().public_numbers()

        class Obj:
            pass

        def mk_key():
            k = Obj()
            k.id = "https://v.vault.azure.net/keys/release/abc123"
            k.key = Obj()
            k.key.kty, k.key.crv = "EC-HSM", "P-256"
            k.key.x, k.key.y = nums.x.to_bytes(32, "big"), nums.y.to_bytes(32, "big")
            k.properties = Obj()
            k.properties.enabled, k.properties.exportable = True, False
            return k

        class KC:
            def get_key(self, name, version):
                return mk_key()

        class CC:
            def sign(self, alg, digest):
                r, s = utils.decode_dss_signature(key.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256()))))
                o = Obj()
                o.signature, o.key_id = r.to_bytes(32, "big") + s.to_bytes(32, "big"), "https://v.vault.azure.net/keys/release/abc123"
                return o

        ref = KeyRef("azure-kv", "acme", "site-a", "prod", "release", "abc123", "ecdsa-p256-sha256")
        rc = ResilientCustody(AzureKeyVaultCustody(KC(), lambda kid: CC()), {ref.kid: algs.spki(key.public_key())})
        algs.verify_raw(ref.algorithm, algs.spki(key.public_key()), rc.sign(ref, MSG), MSG)
        self.assertEqual(rc.check_key_policy(ref).protection_level, "hsm")

    def test_pkcs11_session_exhaustion_is_transient(self):
        class SessionCount(Exception):
            pass

        class Ctx:
            def __enter__(self):
                raise SessionCount()

            def __exit__(self, *a):
                return False

        ref = KeyRef("pkcs11", "acme", "site-a", "prod", "release", "1", "ed25519")
        rc = ResilientCustody(Pkcs11Custody(lambda: Ctx(), {}), {ref.kid: b"x"}, CustodyPolicy(backoff_s=0, max_attempts=2))
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, MSG)
        self.assertEqual(cm.exception.code, "KEY_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
