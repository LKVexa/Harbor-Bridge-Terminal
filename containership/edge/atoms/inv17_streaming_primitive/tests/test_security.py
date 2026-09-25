"""C023/C044 authentication, C024/C042/C043 capabilities, C046 isolation, C047 data policy,
C048 trust-service outage, C049 tamper-evident audit."""
import json
import unittest

from _pkg import security as X, open_stream, registry


class CapabilityTest(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        self.auth = X.CapabilityAuthority(clock=X.TrustedClock(lambda: self.now[0]))

    def v(self, tok, **kw):
        args = dict(stream_id="s", tenant="t", workload="w", right="write"); args.update(kw)
        return self.auth.verify(tok, **args)

    def test_valid_token(self):
        tok = self.auth.issue("s", "t", "w", ["write"])
        self.assertIn("write", self.v(tok).rights)

    def test_wrong_right_stream_tenant(self):
        tok = self.auth.issue("s", "t", "w", ["read"])
        with self.assertRaises(X.AuthzDenied): self.v(tok)
        tok = self.auth.issue("s", "t", "w", ["write"])
        with self.assertRaises(X.AuthzDenied): self.v(tok, stream_id="other")
        with self.assertRaises(X.AuthzDenied): self.v(tok, tenant="t2")
        with self.assertRaises(X.AuthzDenied): self.v(tok, workload="w2")

    def test_expiry(self):
        tok = self.auth.issue("s", "t", "w", ["write"], ttl=10)
        self.now[0] += 11
        with self.assertRaises(X.AuthError): self.v(tok)

    def test_forgery_and_tamper(self):
        tok = self.auth.issue("s", "t", "w", ["read"])
        body, mac = tok.split(".")
        claims = json.loads(X._unb64(body)); claims["rgt"] = ["read", "write"]
        forged = X._b64(X.canonical(claims)) + "." + mac
        with self.assertRaises(X.AuthError): self.v(forged)
        other = X.CapabilityAuthority(clock=self.auth.clock)
        with self.assertRaises(X.AuthError):  # different key ring: unknown/bad key
            other.verify(self.auth.issue("s", "t", "w", ["write"]), stream_id="s", tenant="t", workload="w", right="write")
        for junk in ("", "a", "a.b.c", "!!.!!", "x" * 5000):
            with self.assertRaises(X.AuthError): self.v(junk)

    def test_single_use_transfer_replay(self):
        tok = self.auth.issue("s", "t", "w", ["transfer"])
        self.v(tok, right="transfer")
        with self.assertRaises(X.TokenReplay): self.v(tok, right="transfer")

    def test_revocation(self):
        tok = self.auth.issue("s", "t", "w", ["write"])
        self.auth.revoke(tok)
        with self.assertRaises(X.AuthError): self.v(tok)

    def test_key_rotation(self):
        old = self.auth.issue("s", "t", "w", ["write"])
        self.auth.keys.rotate("k2", b"\x01" * 32)
        new = self.auth.issue("s", "t", "w", ["write"])
        self.v(old); self.v(new)
        self.auth.keys.retire("k1")
        with self.assertRaises(X.AuthError): self.v(old)
        with self.assertRaises(ValueError): self.auth.keys.retire("k2")
        with self.assertRaises(ValueError): self.auth.keys.rotate("k3", b"short")

    def test_issue_validation(self):
        for rights in ([], ["root"]):
            with self.assertRaises(ValueError): self.auth.issue("s", "t", "w", rights)
        with self.assertRaises(ValueError): self.auth.issue("s", "t", "w", ["read"], ttl=10_000)
        with self.assertRaises(ValueError): self.auth.issue("", "t", "w", ["read"])


class TrustOutageTest(unittest.TestCase):
    def test_key_and_time_outage_fail_closed(self):
        r = registry()
        s, tok = open_stream(r)
        r.authority.keys.available = False
        with self.assertRaises(X.TrustServiceUnavailable):
            r.write("s1", 1, tenant="t1", workload="w1", token=tok)
        r.authority.keys.available = True
        r.authority.clock.available = False
        with self.assertRaises(X.TrustServiceUnavailable):
            r.get("s1", tenant="t1", workload="w1", token=tok, right="read")
        kinds = [e.kind for e in r.audit.events]
        self.assertEqual(kinds.count("trust.unavailable"), 2)
        # the local data plane is unaffected for already-authorised holders of the handle
        s.grant(1); s.write(9); self.assertEqual(s.read(), 9)


class IsolationTest(unittest.TestCase):
    def test_cross_tenant_access_denied_and_audited(self):
        r = registry()
        open_stream(r, "a", tenant="t1")
        tok_b = r.authority.issue("a", "t2", "w1", ["read"])
        with self.assertRaises(X.AuthzDenied):
            r.get("a", tenant="t2", workload="w1", token=tok_b, right="read")
        self.assertEqual(r.audit.events[-1].kind, "authz.denied")

    def test_explicit_transfer(self):
        r = registry()
        s, _ = open_stream(r, "a", tenant="t1")
        xfer = r.authority.issue("a", "t1", "w1", ["transfer"])
        r.transfer("a", from_tenant="t1", workload="w1", token=xfer, to_tenant="t2", to_workload="w9")
        self.assertEqual((s.tenant, s.workload), ("t2", "w9"))
        tok_old = r.authority.issue("a", "t1", "w1", ["read"])
        with self.assertRaises(X.AuthzDenied):
            r.get("a", tenant="t1", workload="w1", token=tok_old, right="read")
        with self.assertRaises((X.AuthError, X.AuthzDenied)):  # stale transfer token is useless
            r.transfer("a", from_tenant="t2", workload="w9", token=xfer, to_tenant="t1", to_workload="w1")


class DataPolicyTest(unittest.TestCase):
    def test_encryption_and_residency(self):
        p = X.DataPolicy(allowed_regions=frozenset({"eu"}))
        p.check(classification="internal", encrypted=False, crosses_boundary=True, region="eu")
        p.check(classification="restricted", encrypted=False, crosses_boundary=False, region="eu")
        with self.assertRaises(X.DataPolicyViolation):
            p.check(classification="confidential", encrypted=False, crosses_boundary=True, region="eu")
        with self.assertRaises(X.DataPolicyViolation):
            p.check(classification="public", encrypted=True, crosses_boundary=True, region="us")
        with self.assertRaises(X.DataPolicyViolation):
            p.check(classification="secret", encrypted=True, crosses_boundary=True, region="eu")


class AuditTest(unittest.TestCase):
    def test_chain_detects_tamper_reorder_delete_truncate(self):
        a = X.AuditLedger()
        for i in range(5):
            a.record("stream.open", "t", f"s{i}", "allowed")
        self.assertEqual(a.verify(), [])
        head = a.anchor()
        a.events[2].outcome = "denied"
        self.assertTrue(any("tampered" in p for p in a.verify()))
        a.events[2].outcome = "allowed"
        a.events[1], a.events[3] = a.events[3], a.events[1]
        self.assertTrue(a.verify())
        a.events[1], a.events[3] = a.events[3], a.events[1]
        del a.events[2]
        self.assertTrue(a.verify())
        b = X.AuditLedger()
        for i in range(3):
            b.record("stream.open", "t", str(i), "allowed")
        h = b.anchor(); b.events.pop()
        self.assertEqual(b.verify(), [])  # truncation invisible without an anchor ...
        self.assertTrue(b.verify(expected_head=h))  # ... and caught with one
        self.assertEqual(len(a.export_jsonl().splitlines()), 4)
        with self.assertRaises(ValueError):
            a.record("made.up", "x", "y", "z")
        self.assertNotEqual(head, "")


if __name__ == "__main__":
    unittest.main()
