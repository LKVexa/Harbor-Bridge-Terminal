"""M05/M06/M08/M09 - negotiation, authentication, AEAD channel, anti-replay."""
import os
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from wrpc import security as S  # noqa: E402
from wrpc.security import SecurityError  # noqa: E402


def _pair(kr=None, peer="c", versions=S.SUPPORTED_VERSIONS):
    kr = kr or S.Keyring()
    psk = os.urandom(32)
    kid = kr.add(peer, psk, 3600)
    return kr, kid, psk


class HandshakeTest(unittest.TestCase):
    def test_mutual_auth_and_channel(self):
        kr, kid, psk = _pair()
        c = S.ClientHandshake("c", kid, psk)
        s = S.ServerHandshake("srv", kr)
        fin, cchan, v = c.finish(s.accept(c.hello), "srv")
        schan, peer, v2 = s.complete(fin)
        self.assertEqual((peer, v, v2), ("c", "wrpc/2", "wrpc/2"))
        self.assertEqual(schan.open(cchan.seal(b"ping")), b"ping")
        self.assertEqual(cchan.open(schan.seal(b"pong")), b"pong")

    def test_wrong_psk_fails_both_directions(self):
        kr, kid, _ = _pair()
        c = S.ClientHandshake("c", kid, os.urandom(32))
        with self.assertRaises(SecurityError) as cm:
            c.finish(S.ServerHandshake("srv", kr).accept(c.hello), "srv")
        self.assertEqual(cm.exception.code, "authentication-failed")

    def test_server_identity_pinned(self):
        kr, kid, psk = _pair()
        c = S.ClientHandshake("c", kid, psk)
        with self.assertRaises(SecurityError):
            c.finish(S.ServerHandshake("impostor", kr).accept(c.hello), "srv")

    def test_forged_client_finish_rejected(self):
        kr, kid, psk = _pair()
        c = S.ClientHandshake("c", kid, psk)
        s = S.ServerHandshake("srv", kr)
        s.accept(c.hello)
        with self.assertRaises(SecurityError):
            s.complete({"type": "finish", "mac": "00" * 32})

    def test_unknown_expired_revoked_and_wrong_peer_share_one_code(self):
        kr, kid, psk = _pair()
        codes = set()
        for hello in [dict(S.ClientHandshake("c", "nope", psk).hello),
                      dict(S.ClientHandshake("other", kid, psk).hello)]:
            with self.assertRaises(SecurityError) as cm:
                S.ServerHandshake("srv", kr).accept(hello)
            codes.add(cm.exception.code)
        with self.assertRaises(SecurityError) as cm:
            S.ServerHandshake("srv", kr).accept(S.ClientHandshake("c", kid, psk).hello, now=10 ** 12)
        codes.add(cm.exception.code)
        kr.revoke(kid)
        with self.assertRaises(SecurityError) as cm:
            S.ServerHandshake("srv", kr).accept(S.ClientHandshake("c", kid, psk).hello)
        codes.add(cm.exception.code)
        self.assertEqual(codes, {"authentication-failed"})

    def test_rotation_overlap_then_old_key_expires(self):
        kr, old, psk = _pair()
        new = kr.rotate("c", os.urandom(32), 3600, overlap_s=10, now=1000.0)
        self.assertEqual(kr.current("c", now=1005.0), new)
        kr.lookup(old, "c", now=1005.0)                   # still valid inside overlap
        with self.assertRaises(SecurityError):
            kr.lookup(old, "c", now=1011.0)

    def test_weak_and_duplicate_keys_rejected(self):
        kr = S.Keyring()
        with self.assertRaises(SecurityError):
            kr.add("c", b"short", 10)
        kr.add("c", os.urandom(32), 10, key_id="k")
        with self.assertRaises(SecurityError):
            kr.add("c", os.urandom(32), 10, key_id="k")

    def test_malformed_hello_variants(self):
        kr, kid, psk = _pair()
        base = S.ClientHandshake("c", kid, psk).hello
        for bad in [{}, dict(base, type="x"), dict(base, nonce="zz"), dict(base, nonce="00"),
                    dict(base, versions="wrpc/2"), dict(base, versions=[]), dict(base, versions=["x"] * 17)]:
            with self.assertRaises(SecurityError):
                S.ServerHandshake("srv", kr).accept(bad)


class NegotiationTest(unittest.TestCase):
    def test_highest_common(self):
        self.assertEqual(S.negotiate(["wrpc/1", "wrpc/2"], ("wrpc/3", "wrpc/2", "wrpc/1")), "wrpc/2")

    def test_no_common(self):
        with self.assertRaises(SecurityError) as cm:
            S.negotiate(["wrpc/9"])
        self.assertEqual(cm.exception.code, "no-common-version")

    def test_downgrade_by_mitm_is_detected(self):
        """A MITM strips the client's preferred version; server picks the weaker one,
        but the client's offer is in the MAC'd transcript so the server MAC fails."""
        kr, kid, psk = _pair()
        c = S.ClientHandshake("c", kid, psk, versions=("wrpc/3", "wrpc/2"))
        tampered = dict(c.hello, versions=["wrpc/2"])
        accept = S.ServerHandshake("srv", kr, supported=("wrpc/3", "wrpc/2")).accept(tampered)
        with self.assertRaises(SecurityError) as cm:
            c.finish(accept, "srv")
        self.assertEqual(cm.exception.code, "authentication-failed")

    def test_server_choosing_unoffered_version_rejected(self):
        kr, kid, psk = _pair()
        c = S.ClientHandshake("c", kid, psk)
        accept = S.ServerHandshake("srv", kr).accept(c.hello)
        accept["version"] = "wrpc/0"
        with self.assertRaises(SecurityError) as cm:
            c.finish(accept, "srv")
        self.assertEqual(cm.exception.code, "downgrade")


class ChannelTest(unittest.TestCase):
    def setUp(self):
        kr, kid, psk = _pair()
        c = S.ClientHandshake("c", kid, psk)
        s = S.ServerHandshake("srv", kr)
        fin, self.c, _ = c.finish(s.accept(c.hello), "srv")
        self.s, _, _ = s.complete(fin)

    def test_replayed_record_rejected(self):
        rec = self.c.seal(b"a")
        self.s.open(rec)
        with self.assertRaises(SecurityError) as cm:
            self.s.open(rec)
        self.assertEqual(cm.exception.code, "replay")

    def test_reordered_record_rejected(self):
        r1, r2 = self.c.seal(b"1"), self.c.seal(b"2")
        self.s.open(r2)
        with self.assertRaises(SecurityError):
            self.s.open(r1)

    def test_tampered_ciphertext_and_seq_rejected(self):
        rec = bytearray(self.c.seal(b"hello"))
        rec[-1] ^= 1
        with self.assertRaises(SecurityError) as cm:
            self.s.open(bytes(rec))
        self.assertEqual(cm.exception.code, "record-auth-failed")
        rec2 = bytearray(self.c.seal(b"hello"))
        rec2[7] ^= 1                         # bump the sequence number in the clear header
        with self.assertRaises(SecurityError):
            self.s.open(bytes(rec2))

    def test_forgery_does_not_advance_window(self):
        good = self.c.seal(b"x")
        forged = good[:8] + os.urandom(len(good) - 8)
        with self.assertRaises(SecurityError):
            self.s.open(forged)
        self.assertEqual(self.s.open(good), b"x")

    def test_reflection_rejected(self):
        """A record the client sent cannot be bounced back to the client (direction-bound nonce + key)."""
        with self.assertRaises(SecurityError):
            self.c.open(self.c.seal(b"reflect"))

    def test_nonce_never_repeats(self):
        seqs = {self.c.seal(b"")[:8] for _ in range(1000)}
        self.assertEqual(len(seqs), 1000)

    def test_request_id_window(self):
        w = S.ReplayWindow(request_ttl_s=10, max_ids=2)
        w.check_request("a", 0)
        with self.assertRaises(SecurityError):
            w.check_request("a", 1)
        w.check_request("b", 1)
        with self.assertRaises(SecurityError) as cm:
            w.check_request("c", 2)          # full of live ids: fail closed
        self.assertEqual(cm.exception.code, "replay-cache-full")
        w.check_request("c", 20)             # expired ids are evicted


if __name__ == "__main__":
    unittest.main()
