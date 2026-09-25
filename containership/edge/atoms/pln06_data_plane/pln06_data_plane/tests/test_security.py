"""WP #11 #12 #18 #19 #20 #22 #23 #24 - adversarial security tests (threat IDs from docs/THREAT_MODEL.md)."""
from __future__ import annotations

import json
import unittest

from _support import Env  # noqa: F401  (sys.path side effect)
from pln06_data_plane import security as s
from pln06_data_plane.integrity import sha256_hex


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class KeyLifecycleTest(unittest.TestCase):
    def test_rotation_grace_revocation_expiry_and_outage(self):  # T-KEY-1..4
        clk = Clock()
        ring = s.KeyRing(clock=clk)
        ring.add("k1")
        kid, mac = ring.sign(b"m")
        ring.rotate("k2")
        self.assertEqual(ring.active_key_id, "k2")
        self.assertTrue(ring.verify("k1", b"m", mac))            # verify-only grace
        with self.assertRaises(s.KeyUnavailable):
            ring._material("k1", signing=True)                    # old key cannot sign
        ring.revoke("k1")
        with self.assertRaises(s.KeyUnavailable):
            ring.verify("k1", b"m", mac)                          # revoked never verifies
        ring.add("k3", ttl_seconds=10, activate=False)
        clk.t += 11
        with self.assertRaises(s.KeyUnavailable):
            ring.verify("k3", b"m", "00")
        ring.set_provider_outage(True)
        with self.assertRaises(s.KeyUnavailable):
            ring.sign(b"m")                                       # outage fails closed
        self.assertNotIn("material", json.dumps(ring.inventory(), default=str))

    def test_weak_or_duplicate_keys_rejected(self):
        ring = s.KeyRing()
        with self.assertRaises(s.KeyUnavailable):
            ring.add("short", b"123")
        ring.add("k")
        with self.assertRaises(s.KeyUnavailable):
            ring.add("k")


class AuthenticationTest(unittest.TestCase):
    def setUp(self):
        self.clk = Clock()
        self.ring = s.KeyRing(clock=self.clk)
        self.ring.add("k1")
        self.authn = s.Authenticator(self.ring, clock=self.clk)

    def test_valid_credential(self):
        p = self.authn.authenticate(self.authn.issue("w", "workload", ["transfer.submit"], tenant="t"))
        self.assertEqual((p.subject, p.tenant), ("w", "t"))

    def test_spoofed_tampered_expired_future_audience_replay(self):  # T-SPOOF, T-REPLAY, T-DOWNGRADE
        cred = self.authn.issue("w", "workload", ["transfer.submit"], tenant="t", single_use=True)
        forged = json.loads(json.dumps(cred))
        forged["body"]["caps"] = sorted(s.CAPABILITIES)           # privilege escalation attempt
        with self.assertRaises(s.AuthenticationFailed):
            self.authn.authenticate(forged)
        self.authn.authenticate(cred)
        with self.assertRaises(s.AuthenticationFailed):
            self.authn.authenticate(cred)                         # replay
        other = s.Authenticator(self.ring, audience="other-svc", clock=self.clk)
        with self.assertRaises(s.AuthenticationFailed):
            self.authn.authenticate(other.issue("w", "workload", [], tenant="t"))
        old = self.authn.issue("w", "workload", [], tenant="t", ttl=1)
        self.clk.t += 100
        with self.assertRaises(s.AuthenticationFailed):
            self.authn.authenticate(old)
        for junk in ({}, {"body": 1, "kid": "k1", "mac": "x"}, {"body": {}, "kid": "nope", "mac": ""}):
            with self.assertRaises((s.AuthenticationFailed, s.KeyUnavailable)):
                self.authn.authenticate(junk)

    def test_revoked_token_and_unknown_caps(self):
        cred = self.authn.issue("w", "workload", [], tenant="t")
        self.authn.revoke_token(cred["body"]["jti"])
        with self.assertRaises(s.AuthenticationFailed):
            self.authn.authenticate(cred)
        with self.assertRaises(s.AuthorizationDenied):
            self.authn.issue("w", "workload", ["root"], tenant="t")
        with self.assertRaises(s.AuthenticationFailed):
            self.authn.issue("w", "martian", [], tenant="t")

    def test_replay_cache_is_bounded_and_fails_closed(self):  # T-DOS-3
        a = s.Authenticator(self.ring, clock=self.clk, replay_cache_limit=2)
        for _ in range(2):
            a.authenticate(a.issue("w", "workload", [], tenant="t", single_use=True, ttl=1000))
        with self.assertRaises(s.AuthenticationFailed):
            a.authenticate(a.issue("w", "workload", [], tenant="t", single_use=True, ttl=1000))


class AuthorizationTest(unittest.TestCase):
    def test_deny_by_default_and_cross_tenant(self):
        p = s.Principal("w", "workload", "t1", frozenset({"transfer.submit"}), "j")
        s.Authorizer.require(p, "transfer.submit", tenant="t1")
        with self.assertRaises(s.AuthorizationDenied):
            s.Authorizer.require(p, "policy.update")
        with self.assertRaises(s.AuthorizationDenied):
            s.Authorizer.require(p, "transfer.submit", tenant="t2")
        with self.assertRaises(s.AuthorizationDenied):
            s.Authorizer.require(p, "made.up")


class LabelTest(unittest.TestCase):
    def test_signed_label_binding(self):  # T-LABEL-1..5
        clk = Clock()
        ring = s.KeyRing(clock=clk)
        ring.add("k1")
        la = s.LabelAuthority(ring, clock=clk)
        d = sha256_hex(b"payload")
        lab = la.issue(classification="pii", digest=d, tenant="t")
        la.verify(lab, classification="pii", digest=d, tenant="t")
        for kw in ({"classification": "public"}, {"digest": sha256_hex(b"other")}, {"tenant": "t2"}, {"digest": None}):
            with self.assertRaises(s.LabelInvalid):
                la.verify(lab, **{"classification": "pii", "digest": d, "tenant": "t", **kw})
        forged = json.loads(json.dumps(lab))
        forged["body"]["classification"] = "public"
        with self.assertRaises(s.LabelInvalid):
            la.verify(forged, classification="public", digest=d, tenant="t")
        with self.assertRaises(s.LabelInvalid):
            s.LabelAuthority(ring, issuer="evil").verify(lab, classification="pii", digest=d, tenant="t")
        clk.t += 10_000
        with self.assertRaises(s.LabelInvalid):
            la.verify(lab, classification="pii", digest=d, tenant="t")
        ring.rotate("k2")          # trust-root rotation: new labels verify, old key still verify-only
        clk.t = 1000.0
        la.verify(lab, classification="pii", digest=d, tenant="t")
        ring.revoke("k1")
        with self.assertRaises(s.KeyUnavailable):
            la.verify(lab, classification="pii", digest=d, tenant="t")


class AuditLedgerTest(unittest.TestCase):
    def test_chain_detects_edit_delete_reorder_and_persists(self):  # T-AUDIT-1..4
        import pathlib
        import tempfile
        tmp = pathlib.Path(tempfile.mkdtemp()) / "a.jsonl"
        ring = s.KeyRing()
        ring.add("k1")
        led = s.AuditLedger(ring, tmp)
        for i in range(5):
            led.append("admit", n=i)
        self.assertEqual(led.verify(), 5)
        self.assertEqual(s.AuditLedger(ring, tmp).verify(), 5)          # reload + verify
        lines = tmp.read_text().splitlines()
        for mutate in (lambda L: L[:2] + L[3:],                          # delete
                       lambda L: [L[1], L[0]] + L[2:],                   # reorder
                       lambda L: L[:1] + [L[1].replace('"n": 1', '"n": 9')] + L[2:]):  # edit
            tmp.write_text("\n".join(mutate(list(lines))) + "\n")
            with self.assertRaises(s.AuditTampered):
                s.AuditLedger(ring, tmp)
        with self.assertRaises(s.AuditTampered):
            led.append("not-an-event")


class SandboxAndIsolationTest(unittest.TestCase):
    def test_guard_blocks_ungranted_authority(self):  # T-ESCAPE-1
        g = s.AuthorityGuard(s.Grant(filesystem_paths=("/srv/pk",)))
        g.check("filesystem", "/srv/pk/a")
        for action, target in (("network", "x"), ("filesystem", "/srv/pkx"), ("filesystem", "/etc/passwd"),
                               ("device", "/dev/mem"), ("secret", "db"), ("shared_memory", "")):
            with self.assertRaises(s.SandboxViolation):
                g.check(action, target)
        self.assertEqual(len(g.violations), 6)

    def test_tenant_namespaces_are_disjoint(self):  # T-XTENANT-2
        self.assertNotEqual(s.tenant_namespace("a", "x"), s.tenant_namespace("b", "x"))
        self.assertNotEqual(s.tenant_namespace("a\x00b", ""), s.tenant_namespace("a", "b"))


if __name__ == "__main__":
    unittest.main()
