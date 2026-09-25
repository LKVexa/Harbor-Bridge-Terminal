"""PK_CTRL_HS/1 authenticated establishment."""
from __future__ import annotations

import hashlib
import random
import struct
import threading
import time
import unittest

import _util  # noqa: F401

from inv36_control_transport import handshake as hs
from inv36_control_transport.errors import ErrorCode
from inv36_control_transport.keys import InMemoryKeyProvider, KeyClass
from inv36_control_transport.testing import World
from inv36_control_transport.transport import Session


def run(w: World, client=("host:h1", "host_agent", "t1"), server=("guest:g1", "guest_agent", "t1"),
        cpol=None, spol=None, registry=None, mitm=None):
    ck, cc = w.identity(*client)
    sk, sc = w.identity(*server)
    cli = hs.ClientHandshake(cpol or w.hs_policy(), ck, cc)
    srv = hs.ServerHandshake(spol or w.hs_policy(), sk, sc, registry)
    ch = cli.hello()
    if mitm and "ch" in mitm:
        ch = mitm["ch"](ch)
    sh = srv.on_client_hello(ch)
    if mitm and "sh" in mitm:
        sh = mitm["sh"](sh)
    cf, cres = cli.on_server_hello(sh)
    if mitm and "cf" in mitm:
        cf = mitm["cf"](cf)
    sres = srv.on_client_finish(cf)
    return cres, sres, (ch, sh, cf)


class HandshakePositiveTest(unittest.TestCase):
    """REQ: INV36-REQ-002, INV36-REQ-003, INV36-REQ-004 | KIND: security"""

    def test_mutual_authentication_and_matching_exports(self):
        w = World()
        c, s, _ = run(w)
        self.assertEqual(c.shared, s.shared)
        self.assertEqual(c.session_id, s.session_id)
        self.assertEqual(len(c.session_id), 32)
        self.assertEqual(c.peer.subject, "guest:g1")
        self.assertEqual(s.peer.subject, "host:h1")
        a = Session("host:h1", "guest:g1", c.shared, session_id=c.session_id)
        b = Session("guest:g1", "host:h1", s.shared, session_id=s.session_id)
        self.assertEqual(b.open(a.seal(b"hello")), b"hello")

    def test_fresh_ephemerals_every_session(self):
        w = World()
        r1, _, t1 = run(w)
        r2, _, t2 = run(w)
        self.assertNotEqual(r1.shared, r2.shared)
        self.assertNotEqual(r1.session_id, r2.session_id)
        self.assertNotEqual(t1[0][-500:-300], t2[0][-500:-300])

    def test_evidence_contains_no_secrets(self):
        w = World()
        c, _, _ = run(w)
        ev = c.evidence()
        blob = repr(ev).encode()
        self.assertNotIn(c.shared.hex().encode(), blob)
        self.assertNotIn(c.session_id.hex().encode(), blob)
        self.assertEqual(ev["suite_name"], "X25519_ED25519_HKDFSHA256_AES256GCMSIV")
        self.assertEqual(ev["trust_anchor_version"], 1)
        c.wipe()
        self.assertEqual(c.shared, b"")

    def test_transcript_binding_property(self):
        """Flipping any single byte of any handshake message must abort the handshake (MC-04.025)."""
        w = World()
        rng = random.Random(7)
        for which in ("ch", "sh", "cf"):
            for _ in range(25):
                def flip(m, rng=rng):
                    b = bytearray(m)
                    i = rng.randrange(6, len(b))
                    b[i] ^= 1 << rng.randrange(8)
                    return bytes(b)
                with self.subTest(which=which), self.assertRaises(hs.HandshakeError):
                    run(w, mitm={which: flip})


class HandshakeNegativeTest(unittest.TestCase):
    """REQ: INV36-REQ-002, INV36-REQ-017, INV36-REQ-018 | KIND: security"""

    def assertCode(self, code, fn):
        with self.assertRaises(hs.HandshakeError) as cm:
            fn()
        self.assertEqual(cm.exception.code, code, cm.exception)

    def test_wrong_trust_root(self):
        w, other = World(), World()
        ck, cc = other.identity("host:evil", "host_agent", "t1")
        sk, sc = w.identity("guest:g1", "guest_agent", "t1")
        cli = hs.ClientHandshake(w.hs_policy(), ck, cc)
        srv = hs.ServerHandshake(w.hs_policy(), sk, sc)
        self.assertCode(ErrorCode.HS_TRUST_CHAIN, lambda: srv.on_client_hello(cli.hello()))

    def test_wrong_identity_expected_peer(self):
        w = World()
        self.assertCode(ErrorCode.HS_IDENTITY, lambda: run(w, cpol=w.hs_policy(expected_peer="guest:other")))

    def test_role_not_permitted(self):
        w = World()
        self.assertCode(ErrorCode.HS_POLICY,
                        lambda: run(w, spol=w.hs_policy(allowed_peer_roles=frozenset({"node"}))))

    def test_expired_and_not_yet_valid(self):
        w = World()
        old = time.time() - 10_000
        self.assertCode(ErrorCode.HS_EXPIRED, lambda: self._custom(w, not_before=old, ttl=60))
        self.assertCode(ErrorCode.HS_EXPIRED, lambda: self._custom(w, not_before=time.time() + 10_000, ttl=60))

    def _custom(self, w, **kw):
        ck, cc = w.identity("host:x", "host_agent", "t1", **kw)
        sk, sc = w.identity("guest:g1", "guest_agent", "t1")
        srv = hs.ServerHandshake(w.hs_policy(), sk, sc)
        return srv.on_client_hello(hs.ClientHandshake(w.hs_policy(), ck, cc).hello())

    def test_clock_skew_tolerance(self):
        w = World()
        self._custom(w, not_before=time.time() + 100, ttl=3600)  # within 300 s skew
        pol = w.hs_policy(max_clock_skew_s=10)
        ck, cc = w.identity("host:x", "host_agent", "t1", not_before=time.time() + 100)
        sk, sc = w.identity("guest:g1", "guest_agent", "t1")
        self.assertCode(ErrorCode.HS_EXPIRED,
                        lambda: hs.ServerHandshake(pol, sk, sc).on_client_hello(hs.ClientHandshake(pol, ck, cc).hello()))

    def test_revoked_credential_and_epoch(self):
        w = World()
        ck, cc = w.identity("host:x", "host_agent", "t1", serial="deadbeef")
        w.revocations.serials.add("deadbeef")
        sk, sc = w.identity("guest:g1", "guest_agent", "t1")
        self.assertCode(ErrorCode.HS_REVOKED, lambda: hs.ServerHandshake(w.hs_policy(), sk, sc).on_client_hello(
            hs.ClientHandshake(w.hs_policy(), ck, cc).hello()))
        w.revocations.serials.clear()
        w.epochs.revoke(1, reason="compromise")
        self.assertCode(ErrorCode.HS_REVOKED, lambda: run(w))

    def test_revocation_service_unavailable_fails_closed_and_cache_window(self):
        w = World()
        w.revocations.available = False
        self.assertCode(ErrorCode.HS_DEPENDENCY, lambda: run(w))
        w2 = World()
        pol = w2.hs_policy(allow_cached_revocation_s=60)
        run(w2, spol=pol, cpol=pol)          # populates cache
        w2.revocations.available = False
        run(w2, spol=pol, cpol=pol)          # approved cached window
        stale = World()
        stale.revocations.fetched_at = time.time() - 10_000
        self.assertCode(ErrorCode.HS_DEPENDENCY, lambda: run(stale))

    def test_clock_failure_fails_closed(self):
        w = World()

        def broken():
            raise OSError("ntp down")

        self.assertCode(ErrorCode.HS_DEPENDENCY, lambda: run(w, spol=w.hs_policy(clock=broken)))

    def test_attestation(self):
        w = World()
        meas = hashlib.sha256(b"guest-image-v1").hexdigest()
        w.attestation.required_roles = {"guest_agent"}
        w.attestation.allowed = {"guest_agent": {meas}}
        self.assertCode(ErrorCode.HS_ATTESTATION, lambda: run(w))
        ck, cc = w.identity("host:h1", "host_agent", "t1")
        sk, sc = w.identity("guest:g1", "guest_agent", "t1", measurement=meas)
        cli = hs.ClientHandshake(w.hs_policy(), ck, cc)
        srv = hs.ServerHandshake(w.hs_policy(), sk, sc)
        cf, _ = cli.on_server_hello(srv.on_client_hello(cli.hello()))
        srv.on_client_finish(cf)
        w.attestation.available = False
        self.assertCode(ErrorCode.HS_DEPENDENCY, lambda: run(w))

    def test_environment_namespace_isolation(self):
        w = World()
        self.assertCode(ErrorCode.HS_IDENTITY, lambda: self._custom(w, env="prod"))

    def test_malformed_credential(self):
        w = World()
        _, cc = w.identity("host:x", "host_agent", "t1")
        body_len = int.from_bytes(cc[:2], "big")
        # non-canonical whitespace in the signed body
        body = cc[2:2 + body_len].replace(b",", b", ", 1)
        forged = len(body).to_bytes(2, "big") + body + cc[-64:]
        with self.assertRaises(hs.HandshakeError):
            hs.parse_credential(forged)
        with self.assertRaises(hs.HandshakeError):
            hs.parse_credential(cc[:-1])

    def test_replayed_client_hello_and_duplicate_session(self):
        w = World()
        reg = hs.new_registry()
        ck, cc = w.identity("host:h1", "host_agent", "t1")
        sk, sc = w.identity("guest:g1", "guest_agent", "t1")
        ch = hs.ClientHandshake(w.hs_policy(), ck, cc).hello()
        hs.ServerHandshake(w.hs_policy(), sk, sc, reg).on_client_hello(ch)
        self.assertCode(ErrorCode.HS_REPLAY, lambda: hs.ServerHandshake(w.hs_policy(), sk, sc, reg).on_client_hello(ch))

    def test_replayed_transcript_cannot_complete(self):
        """An attacker replaying a recorded CH+CF to a fresh server fails (new server ephemeral)."""
        w = World()
        _, _, (ch, sh, cf) = run(w)
        sk, sc = w.identity("guest:g2", "guest_agent", "t1")
        srv = hs.ServerHandshake(w.hs_policy(), sk, sc)
        srv.on_client_hello(ch)
        self.assertCode(ErrorCode.HS_TRANSCRIPT, lambda: srv.on_client_finish(cf))

    def test_downgrade_and_negotiation(self):
        w = World()
        # MITM strips the suite list to a (nonexistent) weaker suite 0
        def to_null(ch):
            return ch[:6] + b"\x01" + struct.pack(">H", 0) + ch[9:]
        self.assertCode(ErrorCode.HS_NEGOTIATION, lambda: run(w, mitm={"ch": to_null}))
        # server selects a suite the client never offered
        def bad_select(sh):
            return sh[:6] + struct.pack(">H", 2) + sh[8:]
        self.assertCode(ErrorCode.HS_NEGOTIATION, lambda: run(w, mitm={"sh": bad_select}))
        self.assertCode(ErrorCode.HS_NEGOTIATION, lambda: run(w, cpol=w.hs_policy(suites=(0,))))

    def test_mitm_key_substitution(self):
        w = World()

        def swap_eph(sh):
            b = bytearray(sh)
            b[8 + 32:8 + 64] = bytes(32)  # replace server ephemeral
            return bytes(b)
        with self.assertRaises(hs.HandshakeError):
            run(w, mitm={"sh": swap_eph})

    def test_reflection_rejected(self):
        w = World()
        self.assertCode(ErrorCode.HS_IDENTITY, lambda: run(w, client=("same:id", "host_agent", "t1"),
                                                           server=("same:id", "guest_agent", "t1")))

    def test_size_limits_and_version(self):
        w = World()
        sk, sc = w.identity("guest:g1", "guest_agent", "t1")
        srv = hs.ServerHandshake(w.hs_policy(), sk, sc)
        self.assertCode(ErrorCode.HS_FORMAT, lambda: srv.on_client_hello(b"PKHS\x01\x01" + b"\0" * 9000))
        self.assertCode(ErrorCode.HS_NEGOTIATION, lambda: srv.on_client_hello(b"PKHS\x02\x01" + b"\0" * 100))
        self.assertCode(ErrorCode.HS_FORMAT, lambda: srv.on_client_hello(b"XXXX\x01\x01"))

    def test_time_limit(self):
        w = World()
        pol = w.hs_policy(timeout_s=0.0)
        self.assertCode(ErrorCode.HS_TIMEOUT, lambda: run(w, cpol=pol))

    def test_simultaneous_handshakes(self):
        w = World()
        errs, results = [], []

        def one():
            try:
                results.append(run(w)[0].session_id)
            except Exception as exc:  # noqa: BLE001
                errs.append(exc)

        ts = [threading.Thread(target=one) for _ in range(16)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertFalse(errs)
        self.assertEqual(len(set(results)), 16)

    def test_registry_is_bounded(self):
        reg = hs.new_registry(4)
        for i in range(100):
            reg.claim(bytes([i]))
        self.assertLessEqual(len(reg._seen), 4)

    def test_key_provider_prod_guard(self):
        with self.assertRaises(Exception):
            InMemoryKeyProvider("prod")
        p = InMemoryKeyProvider("test")
        ref = p.create("x", KeyClass.IDENTITY)
        self.assertNotIn("PRIVATE", repr(p.get_signing_key(ref)))


if __name__ == "__main__":
    unittest.main()
