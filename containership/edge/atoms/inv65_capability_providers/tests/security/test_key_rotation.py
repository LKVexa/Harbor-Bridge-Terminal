import os, tempfile, unittest
from inv65_capability_providers.crypto import at_rest
from inv65_capability_providers.crypto.at_rest import KeyRing
from inv65_capability_providers.crypto.transport import assert_bind_allowed
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.state.store import LinkStateStore


@unittest.skipUnless(at_rest.available(), "cryptography extra not installed")
class KeyRotation(unittest.TestCase):
    def setUp(self):
        self.ring = KeyRing(); self.ring.add("k1", os.urandom(32)); self.d = tempfile.mkdtemp()
        self.k = ["t", "e", "s", "w", "c", "l"]

    def test_state_is_encrypted_at_rest(self):
        s = LinkStateStore(self.d, keyring=self.ring); s.put(self.k, {"config_version": 1, "bucket": "PLAINBUCKET"})
        with open(os.path.join(self.d, "wal.jsonl")) as f:
            self.assertNotIn("PLAINBUCKET", f.read())
        self.assertEqual(LinkStateStore(self.d, keyring=self.ring).get(self.k)["bucket"], "PLAINBUCKET")

    def test_rotation_rekeys_and_old_key_can_retire(self):
        s = LinkStateStore(self.d, keyring=self.ring); s.put(self.k, {"config_version": 1, "bucket": "b"})
        self.ring.add("k2", os.urandom(32)); self.assertEqual(s.rekey(), 1); self.ring.retire("k1")
        self.assertEqual(LinkStateStore(self.d, keyring=self.ring).get(self.k)["bucket"], "b")

    def test_missing_key_fails_closed(self):
        s = LinkStateStore(self.d, keyring=self.ring); s.put(self.k, {"config_version": 1, "bucket": "b"})
        with self.assertRaises(ProviderFault) as c:
            LinkStateStore(self.d, keyring=None).get(self.k)
        self.assertEqual(c.exception.code, "PK_PROVIDER_KEY_UNAVAILABLE")
        other = KeyRing(); other.add("k9", os.urandom(32))
        with self.assertRaises(ProviderFault):
            LinkStateStore(self.d, keyring=other).get(self.k)

    def test_ciphertext_bound_to_record_key(self):
        blob = at_rest.seal(self.ring, b"x", b"key-A")
        with self.assertRaises(ProviderFault) as c:
            at_rest.open_(self.ring, blob, b"key-B")
        self.assertEqual(c.exception.code, "PK_PROVIDER_STATE_CORRUPT")


class TransportPolicy(unittest.TestCase):
    def test_plaintext_refused_outside_loopback_test_mode(self):
        with self.assertRaises(PermissionError):
            assert_bind_allowed("0.0.0.0", False, True)
        with self.assertRaises(PermissionError):
            assert_bind_allowed("127.0.0.1", False, False)
        assert_bind_allowed("127.0.0.1", False, True)
