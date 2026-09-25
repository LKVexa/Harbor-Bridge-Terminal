"""Threat-model-derived security tests (C023, C024, C042-C050, C087)."""
from __future__ import annotations

import json
import os
import time
import unittest

from _support import ADMIN, ALL_DATA, Env, S, pkg


class AuthnTest(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.audit = S.AuditLog(None, os.urandom(32))
        self.an = S.Authenticator(self.env.ring, audit=self.audit, node="node-0")

    def tearDown(self):
        self.env.close()

    def code(self, token, an=None):
        with self.assertRaises(pkg.BulkDataPlaneError) as cm:
            (an or self.an).verify(token)
        return cm.exception.code

    def test_positive(self):
        p = self.an.verify(self.env.token())
        self.assertEqual(p.tenant, "acme")

    def test_expired_future_revoked_spoofed(self):
        self.assertEqual(self.code(self.env.token(ttl=1, now=time.time() - 3600)), "authentication_failed")
        self.assertEqual(self.code(self.env.token(now=time.time() + 3600)), "authentication_failed")
        t = self.env.token()
        head, kid, body, sig = t.split(".")
        claims = json.loads(S._b64d(body))
        claims["tenant"] = "victim"
        forged = ".".join([head, kid, S._b64e(json.dumps(claims).encode()), sig])
        self.assertEqual(self.code(forged), "authentication_failed")
        self.assertEqual(self.code("garbage"), "authentication_failed")
        self.assertEqual(self.code(None), "authentication_failed")

    def test_generic_error_message_no_oracle(self):
        with self.assertRaises(pkg.SecurityRejected) as a:
            self.an.verify(self.env.token(ttl=1, now=time.time() - 3600))
        with self.assertRaises(pkg.SecurityRejected) as b:
            self.an.verify("v1.k1.x.y")
        self.assertEqual(a.exception.message, b.exception.message)
        self.assertEqual({r["data"]["reason"] for r in self.audit.records} >= {"expired"}, True)

    def test_key_rotation_and_revocation(self):
        old = self.env.token()
        self.env.ring.rotate("k2", os.urandom(32))
        self.an.verify(old)  # old key still verifies until revoked
        self.env.ring.revoke("k1")
        self.assertEqual(self.code(old), "authentication_failed")
        self.an.verify(self.env.token())
        self.assertRaises(pkg.CodedError, self.env.ring.revoke, "k2")

    def test_revoked_subject_and_wrong_node(self):
        self.an.revoked_subjects.add("wl-acme")
        self.assertEqual(self.code(self.env.token()), "authentication_failed")
        an2 = S.Authenticator(self.env.ring, node="node-9")
        self.assertEqual(self.code(self.env.token(tenant="x", node="node-0"), an2), "authentication_failed")

    def test_replay_of_single_use_token(self):
        t = self.env.token(once=True)
        self.an.verify(t)
        self.assertEqual(self.code(t), "replay_detected")

    def test_time_service_failure_fails_closed(self):
        def boom():
            raise OSError("ntp")
        an = S.Authenticator(self.env.ring, clock=boom)
        self.assertEqual(self.code(self.env.token(), an), "security_service_unavailable")

    def test_admin_and_data_capabilities_minted_separately(self):
        self.assertRaises(pkg.CodedError, S.mint, self.env.ring, sub="x", tenant="a", actions=["write-chunk", "freeze"])
        self.assertRaises(pkg.CodedError, S.mint, self.env.ring, sub="x", tenant="a", actions=["root"])

    def test_weak_keys_rejected(self):
        self.assertRaises(pkg.CodedError, S.KeyRing, {"k": b"short"}, "k")


class AuthzTest(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.az = S.Authorizer(S.AuditLog(None, os.urandom(32)))
        self.an = S.Authenticator(self.env.ring)

    def tearDown(self):
        self.env.close()

    def deny(self, p, action, tenant, tid=None):
        with self.assertRaises(pkg.SecurityRejected) as cm:
            self.az.check(p, action, tenant=tenant, transfer_id=tid)
        self.assertEqual(cm.exception.code, "authorization_denied")

    def test_matrix(self):
        reader = self.an.verify(self.env.token(actions=["read-progress"]))
        self.az.check(reader, "read-progress", tenant="acme")
        for a in set(ALL_DATA) - {"read-progress"}:
            self.deny(reader, a, "acme")
        for a in ADMIN:
            self.deny(reader, a, "acme")  # privilege escalation

    def test_cross_tenant_and_scope(self):
        p = self.an.verify(self.env.token(scope="tx-1"))
        self.deny(p, "write-chunk", "other")
        self.deny(p, "write-chunk", "acme", "tx-2")
        self.az.check(p, "write-chunk", tenant="acme", transfer_id="tx-1")

    def test_admin_cross_tenant_only_for_admin_actions(self):
        adm = self.an.verify(self.env.admin())
        self.az.check(adm, "quarantine", tenant="acme")
        self.deny(adm, "write-chunk", "acme")


class AuditTest(unittest.TestCase):
    def test_tamper_evident(self):
        env = Env()
        try:
            key = os.urandom(32)
            path = env.dir / "audit.jsonl"
            log = S.AuditLog(path, key)
            for i in range(5):
                log.append("e", {"i": i})
            self.assertEqual(S.verify_audit(path, key)[0], True)
            lines = path.read_text().splitlines()
            # edit
            rec = json.loads(lines[2]); rec["data"]["i"] = 99
            path.write_text("\n".join(lines[:2] + [json.dumps(rec)] + lines[3:]) + "\n")
            self.assertFalse(S.verify_audit(path, key)[0])
            # deletion
            path.write_text("\n".join(lines[:2] + lines[3:]) + "\n")
            self.assertFalse(S.verify_audit(path, key)[0])
            # reorder
            path.write_text("\n".join([lines[1], lines[0]] + lines[2:]) + "\n")
            self.assertFalse(S.verify_audit(path, key)[0])
            self.assertRaises(pkg.CodedError, S.AuditLog, path, key)
        finally:
            env.close()


class PolicyTest(unittest.TestCase):
    def test_encryption_fails_closed(self):
        self.assertFalse(S.encryption_provider_available())
        with self.assertRaises(pkg.CodedError) as cm:
            S.require_encryption()
        self.assertEqual(cm.exception.code, "encryption_unavailable")

    def test_residency(self):
        S.check_residency("eu-1", ["eu-1", "eu-2"])
        with self.assertRaises(pkg.CodedError) as cm:
            S.check_residency("us-1", ["eu-1"])
        self.assertEqual(cm.exception.code, "residency_violation")
        self.assertRaises(pkg.CodedError, S.check_residency, "eu-2", [], ["eu-1"])


if __name__ == "__main__":
    unittest.main()


class ReviewFindingsTest(unittest.TestCase):
    """Regression tests for findings from the independent review of 4.3.0."""

    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()

    def test_replay_cache_never_forgets_live_nonces(self):
        an = S.Authenticator(self.env.ring, replay_cache=3)
        first = self.env.token(once=True)
        an.verify(first)
        for _ in range(2):
            an.verify(self.env.token(once=True))
        with self.assertRaises(pkg.SecurityRejected) as cm:  # full of live nonces -> fail closed
            an.verify(self.env.token(once=True))
        self.assertEqual(cm.exception.code, "security_service_unavailable")
        with self.assertRaises(pkg.SecurityRejected) as cm:  # first is still remembered
            an.verify(first)
        self.assertEqual(cm.exception.code, "replay_detected")

    def test_expired_nonces_are_evicted(self):
        clock = {"t": 1000.0}
        an = S.Authenticator(self.env.ring, replay_cache=2, clock=lambda: clock["t"], clock_skew=0)
        for _ in range(2):
            an.verify(self.env.token(once=True, ttl=10, now=1000.0))
        clock["t"] = 1005.0
        self.assertRaises(pkg.SecurityRejected, an.verify, self.env.token(once=True, ttl=10, now=1005.0))
        clock["t"] = 1011.0
        an.verify(self.env.token(once=True, ttl=10, now=1011.0))  # old ones expired -> evicted

    def test_signed_but_malformed_claims_rejected_cleanly(self):
        kid, key = self.env.ring.signing()
        an = S.Authenticator(self.env.ring)
        import hashlib, hmac as _h
        for claims in ([], {"sub": "x"}, {"sub": "x", "tenant": "t", "nonce": "n", "actions": "write-chunk", "iat": 0, "exp": 9e12},
                       {"sub": "x", "tenant": 5, "nonce": "n", "actions": [], "iat": 0, "exp": 9e12}):
            body = S._b64e(json.dumps(claims).encode())
            sig = S._b64e(_h.new(key, f"v1.{kid}.{body}".encode(), hashlib.sha256).digest())
            with self.assertRaises(pkg.SecurityRejected) as cm:
                an.verify(f"v1.{kid}.{body}.{sig}")
            self.assertEqual(cm.exception.code, "authentication_failed")

    def test_tenant_admin_cannot_freeze_node(self):
        dp = self.env.plane()
        tenant_admin = S.mint(self.env.ring, sub="acme-ops", tenant="acme", actions=["freeze", "quarantine"])
        with self.assertRaises(pkg.SecurityRejected):
            dp.freeze(tenant_admin, True)
        self.assertFalse(dp.admission.frozen)
        dp.freeze(self.env.admin(), True)
        self.assertTrue(dp.admission.frozen)
