"""Group D — identity, encryption, trust and abuse resistance."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gap12_wan_resilience_and_nat_traversal.tests._covers import covers  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import security as sec  # noqa: E402

AEAD = unittest.skipUnless(sec.HAVE_AEAD, "cryptography package absent: SecureChannel refuses to construct")


class TrustGateTest(unittest.TestCase):
    def _gate(self, clk):
        def verifier(peer, ev):
            if ev != b"good":
                raise ValueError("bad")
            return sec.Attestation(peer, clk[0], clk[0] + 100, "sha256:x")
        return sec.TrustGate(verifier, clock=lambda: clk[0])

    @covers("G12-D043:spec1,spec2,unit,impl-doc,authz-identity,key-lifecycle", "G12-H096:neg-security")
    def test_trust_requires_fresh_attestation_and_does_not_outlive_it(self):
        clk = [1000.0]
        g = self._gate(clk)
        self.assertEqual(g.admit("site-b", b"forged"), (False, "AUTH_FAILED"))
        self.assertEqual(g.admit("site-b", b"good"), (True, "OK"))
        self.assertTrue(g.is_trusted("site-b"))
        clk[0] += 101
        self.assertFalse(g.is_trusted("site-b"))               # reachability cannot outlive trust
        self.assertEqual(g.admit("site-b", b"good"), (True, "OK"))
        g.revoke("site-b")
        self.assertFalse(g.is_trusted("site-b"))
        self.assertEqual(g.admit("site-b", b"good"), (False, "POLICY_UNTRUSTED_PEER"))

    @covers("G12-D043:unit,deps,fault")
    def test_absent_gap06_fails_closed(self):
        self.assertEqual(sec.TrustGate(None).admit("x", b"good"), (False, "DEP_UNAVAILABLE"))

    @covers("G12-D043:authz-identity", "G12-D051:authz-identity")
    def test_attestation_for_another_peer_is_refused(self):
        g = sec.TrustGate(lambda peer, ev: sec.Attestation("mallory", 0, 1e12, "x"), clock=lambda: 10.0)
        self.assertEqual(g.admit("site-b", b"good"), (False, "POLICY_UNTRUSTED_PEER"))


@AEAD
class ChannelTest(unittest.TestCase):
    def _pair(self, epoch=0):
        s = os.urandom(32)
        return (sec.SecureChannel(s, me="a", peer="b", initiator=True, epoch=epoch),
                sec.SecureChannel(s, me="b", peer="a", initiator=False, epoch=epoch))

    @covers("G12-D044:spec1,unit,impl-doc,auth-control", "G12-C040:unit")
    def test_directional_keys_context_binding(self):
        a, b = self._pair()
        self.assertEqual(b.open(a.seal(b"hi")), b"hi")
        self.assertEqual(a.open(b.seal(b"yo")), b"yo")
        with self.assertRaises(ValueError):
            a.open(a.seal(b"reflected"))                        # own direction's frame cannot be reflected back
        s = os.urandom(32)
        c = sec.SecureChannel(s, me="a", peer="c", initiator=True)
        d = sec.SecureChannel(s, me="c", peer="a", initiator=False)
        with self.assertRaises(ValueError):
            b.open(c.seal(b"cross-peer"))                       # identity-bound context
        self.assertEqual(d.open(c.seal(b"ok")), b"ok")

    @covers("G12-D044:spec2,unit,integration", "G12-H096:neg-security")
    def test_relay_sees_only_ciphertext_and_cannot_downgrade(self):
        import socket
        from gap12_wan_resilience_and_nat_traversal.wan import turn
        a, b = self._pair()
        with turn.TurnServer(("127.0.0.1", 0), {"a": "p"}) as srv:
            seen = []
            orig = srv._client_packet

            def spy(data, src):
                seen.append(bytes(data))
                return orig(data, src)
            srv._client_packet = spy
            c = turn.TurnClient(srv.address, "a", "p")
            c.allocate()
            peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            peer.bind(("127.0.0.1", 0))
            c.create_permission("127.0.0.1")
            secret = b"LEASE renew node-7 with token XYZ"
            c.send(peer.getsockname(), a.seal(secret))           # direct -> relay transition keeps E2E
            frame, _ = peer.recvfrom(4096)
            self.assertEqual(b.open(frame), secret)
            self.assertTrue(all(secret not in s for s in seen))
            tampered = bytearray(frame)
            tampered[-1] ^= 1
            with self.assertRaises(ValueError):
                b.open(bytes(tampered))                           # relay cannot alter
            with self.assertRaises(ValueError):
                b.open(frame[:12] + b"\x00" * (len(frame) - 12))  # cannot strip to plaintext
            c.close()
            peer.close()

    @covers("G12-D045:impl-doc,unit,key-lifecycle", "G12-D044:key-lifecycle")
    def test_rotation_by_epoch_rejects_old_epoch(self):
        a, b = self._pair()
        old = a.seal(b"old")
        a.rotate()
        b.rotate()
        self.assertEqual(b.open(a.seal(b"new")), b"new")
        with self.assertRaises(ValueError):
            b.open(old)
        with self.assertRaises(ValueError):
            sec.SecureChannel(b"short", me="a", peer="b", initiator=True)

    @covers("G12-D046:spec1,spec2,unit,impl-doc,fault", "G12-H096:neg-security")
    def test_replay_reorder_duplicate_cross_session_post_restart(self):
        a, b = self._pair()
        frames = [a.seal(f"m{i}".encode()) for i in range(10)]
        for f in reversed(frames[5:]):
            b.open(f)                                            # reordered within window: accepted
        for f in (frames[7], frames[9]):
            with self.assertRaisesRegex(ValueError, "AUTH_REPLAY"):
                b.open(f)                                        # duplicate
        x, y = self._pair()
        with self.assertRaises(ValueError):
            y.open(frames[0])                                    # other session (different secret)
        b2 = sec.SecureChannel(b._secret, me="b", peer="a", initiator=False, epoch=0)
        b2.rotate()                                              # restart policy: resume at a NEW epoch
        with self.assertRaisesRegex(ValueError, "AUTH_REPLAY"):
            b2.open(frames[0])                                   # pre-restart frames cannot be replayed

    @covers("G12-D046:unit,resource-bounds")
    def test_window_bounds(self):
        w = sec.ReplayWindow(64)
        self.assertTrue(w.check_and_set(1000))
        self.assertFalse(w.check_and_set(1000 - 64))             # too old
        self.assertTrue(w.check_and_set(999))
        self.assertLess(w.bitmap.bit_length(), 65)
        with self.assertRaises(ValueError):
            sec.ReplayWindow(10 ** 7)


class TurnCredTest(unittest.TestCase):
    @covers("G12-D047:unit,impl-doc,key-lifecycle", "G12-D052:key-lifecycle")
    def test_time_limited_credentials_rotate_with_overlap_and_revoke(self):
        clk = [1000.0]
        c = sec.TurnRestCredentials({"k1": b"s1"}, "k1", ttl=60, clock=lambda: clk[0])
        u, p, kid = c.issue("site-a")
        self.assertTrue(c.verify(u, p))
        c.rotate("k2", b"s2")
        self.assertTrue(c.verify(u, p))                          # overlap: old creds still valid
        u2, p2, kid2 = c.issue("site-a")
        self.assertEqual(kid2, "k2")
        c.rotate("k3", b"s3", retire="k1")
        self.assertFalse(c.verify(u, p))                         # retired secret -> invalid
        self.assertTrue(c.verify(u2, p2))
        clk[0] += 61
        self.assertFalse(c.verify(u2, p2))                       # expiry
        clk[0] -= 61
        c.revoke_user("site-a")
        self.assertFalse(c.verify(u2, p2))


class RelayAuthzTest(unittest.TestCase):
    @covers("G12-D048:unit,impl-doc,authz-identity")
    def test_tenancy_isolation(self):
        a = sec.RelayAuthorizer({"relay-eu-1": "tenant-a", "relay-eu-2": "tenant-b"}, {"tenant-a": {"site-1"}})
        self.assertEqual(a.authorize("tenant-a", "relay-eu-1", "site-1"), "OK")
        self.assertEqual(a.authorize("tenant-a", "relay-eu-2", "site-1"), "POLICY_EGRESS_DENIED")
        self.assertEqual(a.authorize("tenant-a", "relay-eu-1", "site-9"), "POLICY_EGRESS_DENIED")
        self.assertEqual(a.authorize("tenant-b", "relay-eu-1", "site-1"), "POLICY_EGRESS_DENIED")


class RateLimitTest(unittest.TestCase):
    @covers("G12-D049:spec1,spec2,unit,impl-doc,resource-bounds", "G12-H096:neg-security")
    def test_hierarchical_limits_and_bounded_keyspace(self):
        clk = [0.0]
        r = sec.RateLimiter({"source": (1, 2), "peer": (10, 10), "global": (100, 100)}, max_keys=50,
                            clock=lambda: clk[0])
        self.assertEqual(r.allow({"source": "1.2.3.4", "peer": "p", "global": "all"}), (True, None))
        self.assertEqual(r.allow({"source": "1.2.3.4", "peer": "p", "global": "all"}), (True, None))
        self.assertEqual(r.allow({"source": "1.2.3.4", "peer": "p", "global": "all"}), (False, "source"))
        clk[0] = 1.0
        self.assertTrue(r.allow({"source": "1.2.3.4", "peer": "p", "global": "all"})[0])
        for i in range(100_000):                                  # attacker-created keys
            r.allow({"source": f"s{i}"})
        self.assertLessEqual(r.size(), 50 * 3 + 3)
        self.assertGreater(r.denied["source"], 0)
        self.assertEqual(sec.RateLimiter.prefix_of("198.51.100.77"), "198.51.100.0/24")


class BreakerTest(unittest.TestCase):
    @covers("G12-D050:spec1,spec2,unit,impl-doc", "G12-H098:impl-doc")
    def test_closed_open_half_open_and_shared_retry_budget(self):
        clk = [0.0]
        b = sec.CircuitBreaker(failure_threshold=3, open_for=10, half_open_max=1, close_after=2, clock=lambda: clk[0])
        for _ in range(3):
            self.assertTrue(b.admit()[0])
            b.record(False)
        self.assertEqual(b.state, "open")
        self.assertEqual(b.admit(), (False, "BUDGET_BREAKER_OPEN"))
        clk[0] = 11
        self.assertTrue(b.admit()[0])
        self.assertEqual(b.admit(), (False, "BUDGET_BREAKER_OPEN"))   # bounded half-open admission
        b.record(True)
        self.assertTrue(b.admit()[0])
        b.record(True)
        self.assertEqual(b.state, "closed")
        b.override = "force_open"
        self.assertEqual(b.admit(), (False, "OPERATOR_DISABLED"))
        # nested layers share ONE budget: total retries bounded by ratio*firsts+floor
        rb = sec.RetryBudget(ratio=0.2, floor=3, window=100, clock=lambda: clk[0])
        for _ in range(100):
            rb.first_attempt()
        layer_a = sum(rb.try_retry() for _ in range(50))
        layer_b = sum(rb.try_retry() for _ in range(50))
        self.assertEqual(layer_a + layer_b, 23)


class EgressTest(unittest.TestCase):
    @covers("G12-D051:unit,impl-doc,authz-identity", "G12-A001:fallback-policy")
    def test_deny_by_default_and_deny_wins(self):
        e = sec.EgressPolicy(allow=[("198.51.100.0/24", (3478, 3480))], deny=["198.51.100.66/32"], allowed_peers={"site-b"})
        self.assertEqual(e.check("198.51.100.1", 3478), "OK")
        self.assertEqual(e.check("198.51.100.66", 3478), "POLICY_EGRESS_DENIED")
        self.assertEqual(e.check("198.51.100.1", 443), "POLICY_EGRESS_DENIED")
        self.assertEqual(e.check("192.0.2.1", 3478), "POLICY_EGRESS_DENIED")
        self.assertEqual(e.check("198.51.100.1", 3478, peer="mallory"), "POLICY_EGRESS_DENIED")


class SecretsTest(unittest.TestCase):
    @covers("G12-D052:spec1,spec2,unit,impl-doc")
    def test_opaque_refs_least_privilege_rotation_and_no_leak(self):
        with self.assertRaises(ValueError):
            sec.SecretRef("hunter2")
        ref = sec.SecretRef("secret://turn/primary")
        p = sec.SecretProvider({ref: b"s3cr3t", sec.SecretRef("secret://admin/root"): b"x"}, grants={"secret://turn/"})
        s = p.get(ref)
        self.assertEqual(s.reveal(), b"s3cr3t")
        self.assertNotIn("s3cr3t", repr(s) + str(s) + f"{s}")
        with self.assertRaises(TypeError):
            import pickle
            pickle.dumps(s)
        with self.assertRaises(PermissionError):
            p.get(sec.SecretRef("secret://admin/root"))
        got = []
        p.on_rotate(got.append)
        p.rotate(ref, b"new")
        self.assertEqual(got, [ref])
        try:
            raise RuntimeError(f"connect failed with {s}")
        except RuntimeError as exc:
            self.assertNotIn("s3cr3t", str(exc))
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "turn"))
        path = os.path.join(d, "turn", "primary")
        with open(path, "wb") as fh:
            fh.write(b"filesecret")
        os.chmod(path, 0o644)
        fp = sec.SecretProvider(d, grants={"secret://turn/"})
        with self.assertRaises(PermissionError):
            fp.get(ref)                                          # world-readable secret refused
        os.chmod(path, 0o600)
        self.assertEqual(fp.get(ref).reveal(), b"filesecret")


class PrivacyTest(unittest.TestCase):
    @covers("G12-D053:unit,impl-doc", "G12-G083:redaction", "G12-G075:redaction")
    def test_redaction_of_endpoints_and_secrets(self):
        text = 'peer 198.51.100.7:40000 via [2001:db8::5]:3478 password="pw123" token=abc key: zzz'
        r = sec.redact(text)
        for leak in ("198.51.100.7", "2001:db8::5", "pw123", "abc", "zzz"):
            self.assertNotIn(leak, r)
        self.assertIn(sec.endpoint_token("198.51.100.7"), r)     # stable pseudonym keeps correlation
        self.assertEqual(sec.endpoint_token("198.51.100.7"), sec.endpoint_token("198.51.100.7"))


class AnomalyTest(unittest.TestCase):
    @covers("G12-D054:unit,impl-doc")
    def test_forced_relay_scanning_and_credential_misuse(self):
        a = sec.AnomalyDetector(min_attempts=10, scan_distinct_peers=20, auth_fail_burst=5)
        for i in range(12):
            a.observe("src", "relay" if i else "direct_fail", "p", float(i))
        for i in range(25):
            a.observe("scanner", "attempt", f"peer{i}", 1.0)
        for i in range(6):
            a.observe("brute", "auth_fail", "p", 1.0)
        self.assertIn("forced_relay", a.findings("src", 20))
        self.assertIn("scanning", a.findings("scanner", 20))
        self.assertIn("credential_misuse", a.findings("brute", 20))
        self.assertEqual(a.findings("src", 10_000), [])            # windowed


class AuditTest(unittest.TestCase):
    @covers("G12-D055:unit,impl-doc,audit", "G12-D043:audit", "G12-D049:audit")
    def test_hash_chain_detects_tamper(self):
        d = tempfile.mkdtemp()
        log = sec.AuditLog(os.path.join(d, "audit.jsonl"))
        for i in range(5):
            log.append("trust_admit", reason="OK", actor="gap12", subject=f"site-{i}", config_generation="7")
        self.assertEqual(sec.AuditLog.verify(log.entries), (True, None))
        entries = [json.loads(l) for l in open(os.path.join(d, "audit.jsonl"))]
        self.assertEqual(sec.AuditLog.verify(entries), (True, None))
        entries[2]["subject"] = "site-evil"
        self.assertEqual(sec.AuditLog.verify(entries), (False, 2))
        del entries[3]
        self.assertFalse(sec.AuditLog.verify(entries)[0])


if __name__ == "__main__":
    unittest.main()
