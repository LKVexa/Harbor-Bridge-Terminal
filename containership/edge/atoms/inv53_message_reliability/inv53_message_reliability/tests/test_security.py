"""Authentication, authorization, key rotation, audit chain (components 13, 14, 30, 34-36)."""
from __future__ import annotations

import json
import os
import unittest

from _support import KEY_A, KEY_B, TmpDirCase
from inv53_message_reliability import security as S

REQ = {"v": "inv53.wire/1", "op": "put", "tenant": "acme", "queue": "q", "message": {"id": "m"}}


def ring():
    r = S.Keyring()
    r.add("ka", KEY_A, activate=True)
    return r


class AuthnTest(unittest.TestCase):
    def signed(self, key=KEY_A, kid="ka", principal="alice", ts=100.0, nonce="n1", req=REQ):
        return {**req, "auth": S.sign(key, req, kid=kid, principal=principal, ts=ts, nonce=nonce)}

    def test_valid_signature(self):
        self.assertEqual(S.Authenticator(ring()).authenticate(self.signed(), now=100), "alice")

    def test_tampered_body_rejected(self):
        r = self.signed()
        r["queue"] = "other"
        with self.assertRaises(S.AuthenticationError):
            S.Authenticator(ring()).authenticate(r, now=100)

    def test_wrong_key_rejected(self):
        with self.assertRaises(S.AuthenticationError):
            S.Authenticator(ring()).authenticate(self.signed(key=KEY_B), now=100)

    def test_replay_rejected(self):
        a = S.Authenticator(ring())
        r = self.signed()
        a.authenticate(r, now=100)
        with self.assertRaises(S.AuthenticationError):
            a.authenticate(r, now=100)

    def test_skew_rejected(self):
        with self.assertRaises(S.AuthenticationError):
            S.Authenticator(ring(), skew_seconds=10).authenticate(self.signed(ts=0), now=100)

    def test_missing_and_malformed_auth(self):
        a = S.Authenticator(ring())
        for bad in (dict(REQ), {**REQ, "auth": "x"}, {**REQ, "auth": {"kid": "ka"}},
                    {**REQ, "auth": {"kid": "ka", "principal": 1, "ts": 1, "nonce": "n", "mac": "m"}},
                    {**REQ, "auth": {"kid": "ka", "principal": "p", "ts": True, "nonce": "n", "mac": "m"}}):
            with self.assertRaises(S.AuthenticationError):
                a.authenticate(bad, now=100)

    def test_principal_bound_to_kid(self):
        r = ring()
        r.add("kb", KEY_B)
        a = S.Authenticator(r, principals={"alice": "ka"})
        with self.assertRaises(S.AuthenticationError):
            a.authenticate(self.signed(key=KEY_B, kid="kb"), now=100)

    def test_rotation_and_retirement(self):
        r = ring()
        old = self.signed(nonce="old")
        r.rotate("k2", KEY_B)
        self.assertEqual(r.kids(), {"ka": "verify-only", "k2": "active"})
        a = S.Authenticator(r)
        self.assertEqual(a.authenticate(old, now=100), "alice", "verify-only key still verifies during overlap")
        r.retire("ka")
        with self.assertRaises(S.AuthenticationError):
            a.authenticate(self.signed(nonce="after-retire"), now=100)
        with self.assertRaises(ValueError):
            r.retire("k2")

    def test_short_keys_refused(self):
        with self.assertRaises(ValueError):
            S.Keyring().add("k", b"short")

    def test_kms_unbound_fails_closed(self):
        with self.assertRaises(S.SecurityDependencyError):
            S.Authenticator(S.UnboundKmsProvider()).authenticate(self.signed(), now=100)

    def test_provider_crash_fails_closed(self):
        class Boom:
            def get(self, kid):
                raise RuntimeError("network")
        with self.assertRaises(S.SecurityDependencyError):
            S.Authenticator(Boom()).authenticate(self.signed(), now=100)

    def test_env_provider(self):
        os.environ["INV53_KEY_KENV"] = KEY_A.hex()
        try:
            self.assertEqual(S.EnvKeyProvider().get("kenv"), KEY_A)
            os.environ["INV53_KEY_KENV"] = "zz"
            with self.assertRaises(S.SecurityDependencyError):
                S.EnvKeyProvider().get("kenv")
        finally:
            del os.environ["INV53_KEY_KENV"]
        with self.assertRaises(S.AuthenticationError):
            S.EnvKeyProvider().get("absent")

    def test_nonce_cache_saturation_fails_closed_inside_window(self):
        a = S.Authenticator(ring(), nonce_cache=2)
        a.authenticate(self.signed(nonce="a"), now=100)
        a.authenticate(self.signed(nonce="b"), now=100)
        with self.assertRaises(S.SecurityDependencyError):
            a.authenticate(self.signed(nonce="c"), now=100)
        # once the old nonces are outside the skew window they may be evicted
        self.assertEqual(a.authenticate(self.signed(nonce="d", ts=1000), now=1000), "alice")


class AuthzTest(unittest.TestCase):
    def setUp(self):
        self.z = S.Authorizer([S.Grant("alice", "acme", "orders", frozenset({"produce"})),
                               S.Grant("ops", "acme", "*", frozenset({"admin"}))])

    def test_default_deny_and_exact_scope(self):
        self.z.check("alice", "acme", "orders", "produce")
        for args in (("alice", "acme", "orders", "consume"), ("alice", "acme", "other", "produce"),
                     ("alice", "globex", "orders", "produce"), ("mallory", "acme", "orders", "produce")):
            with self.assertRaises(S.AuthorizationError):
                self.z.check(*args)

    def test_admin_does_not_imply_data_access(self):
        with self.assertRaises(S.AuthorizationError):
            self.z.check("ops", "acme", "orders", "consume")

    def test_grants_cannot_span_tenants(self):
        with self.assertRaises(ValueError):
            S.Grant("x", "*", "*", frozenset({"produce"}))
        with self.assertRaises(ValueError):
            S.Grant("x", "t", "*", frozenset({"root"}))


class AuditTest(TmpDirCase):
    def test_chain_verifies_and_detects_edit(self):
        log = S.AuditLog(self.tmp / "a.jsonl")
        for i in range(5):
            log.append("evt", n=i)
        self.assertEqual(log.verify(), (True, "5 records"))
        lines = (self.tmp / "a.jsonl").read_text().splitlines()
        rec = json.loads(lines[2]); rec["fields"]["n"] = 99
        lines[2] = json.dumps(rec, sort_keys=True)
        (self.tmp / "a.jsonl").write_text("\n".join(lines) + "\n")
        ok, why = S.AuditLog(self.tmp / "a.jsonl").verify()
        self.assertFalse(ok)
        self.assertIn("hash mismatch", why)

    def test_tail_truncation_needs_external_anchor(self):
        log = S.AuditLog(self.tmp / "a.jsonl")
        for i in range(4):
            log.append("evt", n=i)
        anchor = log.head()
        lines = (self.tmp / "a.jsonl").read_text().splitlines()
        (self.tmp / "a.jsonl").write_text("\n".join(lines[:2]) + "\n")
        fresh = S.AuditLog(self.tmp / "a.jsonl")
        self.assertTrue(fresh.verify()[0], "a chain alone cannot see tail truncation")
        self.assertFalse(fresh.verify(anchored_head=anchor)[0], "the external anchor does")

    def test_malformed_anchor_and_non_record_lines_fail_verification(self):
        log = S.AuditLog(self.tmp / "a.jsonl")
        for i in range(3):
            log.append("evt", n=i)
        lines = (self.tmp / "a.jsonl").read_text().splitlines()
        (self.tmp / "a.jsonl").write_text(lines[0] + "\n")
        fresh = S.AuditLog(self.tmp / "a.jsonl")
        for bad in ({}, {"seq": "3", "hash": "x"}, {"seq": True, "hash": "x"}, {"seq": 3}):
            self.assertFalse(fresh.verify(anchored_head=bad)[0], bad)
        (self.tmp / "b.jsonl").write_text("[1]\n")
        v = S.AuditLog.__new__(S.AuditLog)
        v.path, v.GENESIS = self.tmp / "b.jsonl", S.AuditLog.GENESIS
        self.assertEqual(v.verify()[0], False)
        self.assertTrue(S.AuditLog(self.tmp / "none.jsonl").verify(anchored_head={"seq": 0, "hash": S.AuditLog.GENESIS})[0])

    def test_refuses_secret_fields(self):
        log = S.AuditLog(self.tmp / "a.jsonl")
        for f in ("key", "mac", "lease_token", "payload"):
            with self.assertRaises(ValueError):
                log.append("evt", **{f: "x"})

    def test_sink_outage_raises_security_dependency(self):
        (self.tmp / "dir_not_file").mkdir()
        with self.assertRaises(S.SecurityDependencyError):
            S.AuditLog(self.tmp / "dir_not_file")          # unreadable at open
        log = S.AuditLog(self.tmp / "later.jsonl")
        log.path = self.tmp / "dir_not_file"                # sink disappears after open
        with self.assertRaises(S.SecurityDependencyError):
            log.append("evt")


if __name__ == "__main__":
    unittest.main()
