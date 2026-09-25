"""Authentication, tenant isolation, capabilities, audit chain, secrets, artifacts."""
import pathlib
import tempfile
import unittest

from _support import FakeClock, authority, env
from inv52_messaging_abstraction import runtime as rt
from inv52_messaging_abstraction import security as sec


def tenant_bus(clock=None, keys=None):
    auth, clock = authority(clock, keys)
    tb = sec.TenantBus(rt.PubSub(), auth)
    return tb, auth, clock


class AuthnTest(unittest.TestCase):
    def test_valid_token_publishes(self):
        tb, auth, _ = tenant_bus()
        tb.grant("acme", "shop", "publish:orders", "subscribe:orders")
        sink = []
        tb.subscribe(auth.issue("shop", "acme"), "orders", lambda m: True, sink)
        self.assertEqual(tb.publish(auth.issue("shop", "acme"), "orders", env("shop")), 1)

    def test_forged_expired_replayed_malformed_tokens_denied(self):
        tb, auth, clock = tenant_bus()
        tb.grant("acme", "shop", "publish:orders")
        good = auth.issue("shop", "acme", ttl=60)
        body, sig = good.split(".")
        forged = body + "." + sig[:-2] + ("AA" if sig[-2:] != "AA" else "BB")
        for tok in (forged, "x", None, "a.b.c", "e30.AAAA"):
            with self.assertRaises(sec.Unauthenticated):
                tb.publish(tok, "orders", env("shop"))
        tb.publish(good, "orders", env("shop"))
        with self.assertRaises(sec.Unauthenticated):  # replay
            tb.publish(good, "orders", env("shop"))
        old = auth.issue("shop", "acme", ttl=10)
        clock.advance(100)
        with self.assertRaises(sec.Unauthenticated):
            tb.publish(old, "orders", env("shop"))

    def test_key_provider_or_clock_outage_denies(self):
        def down():
            raise OSError("kms down")
        auth, clock = authority()
        tok = auth.issue("shop", "acme")
        broken = sec.TokenAuthority(down, "k1", clock=clock)
        tb = sec.TenantBus(rt.PubSub(), broken)
        with self.assertRaises(sec.TrustUnavailable):
            tb.publish(tok, "orders", env("shop"))
        bad_clock = sec.TokenAuthority(lambda: {"k1": b"k" * 48}, "k1", clock=lambda: 0)
        with self.assertRaises(sec.TrustUnavailable):
            bad_clock.verify(tok)

    def test_verify_cost_does_not_scale_with_replay_cache(self):
        """Regression: donor code copied the whole nonce cache on every verify."""
        import time
        from collections import OrderedDict
        auth, clock = authority()
        auth._capacity = 2_000_000
        auth._seen = OrderedDict((f"n{i}", int(clock()) + 3000) for i in range(500_000))
        tok = auth.issue("a", "t")
        t0 = time.perf_counter()
        auth.verify(tok)
        self.assertLess(time.perf_counter() - t0, 0.005)

    def test_expired_nonces_are_evicted(self):
        auth, clock = authority()
        for _ in range(5):
            auth.verify(auth.issue("a", "t", ttl=10))
        clock.advance(100)
        auth.verify(auth.issue("a", "t", ttl=10))
        self.assertEqual(len(auth._seen), 1)

    def test_weak_key_refused(self):
        a = sec.TokenAuthority(lambda: {"k1": b"short"}, "k1", clock=FakeClock())
        with self.assertRaises(sec.Unauthenticated):
            a.issue("x", "y")

    def test_key_rotation_old_tokens_valid_until_removed(self):
        keys = {"k1": b"a" * 32}
        clock = FakeClock()
        a = sec.TokenAuthority(lambda: keys, "k1", clock=clock)
        old = a.issue("s", "t")
        old2 = a.issue("s", "t")
        keys["k2"] = b"b" * 32
        a.active_key_id = "k2"
        self.assertEqual(a.verify(old).key_id, "k1")
        new = a.issue("s", "t")
        del keys["k1"]
        self.assertEqual(a.verify(new).key_id, "k2")
        with self.assertRaises(sec.Unauthenticated):
            a.verify(old2)  # k1 removed from the provider: tokens signed with it now fail


class IsolationTest(unittest.TestCase):
    def test_tenants_cannot_cross(self):
        tb, auth, _ = tenant_bus()
        tb.grant("acme", "shop", "publish:orders", "subscribe:orders")
        tb.grant("evil", "shop", "publish:orders", "subscribe:orders")
        acme_sink, evil_sink = [], []
        tb.subscribe(auth.issue("shop", "acme"), "orders", lambda m: True, acme_sink)
        tb.subscribe(auth.issue("shop", "evil"), "orders", lambda m: True, evil_sink)
        tb.publish(auth.issue("shop", "acme"), "orders", env("shop", data={"secret": 1}))
        self.assertEqual(len(acme_sink), 1)
        self.assertEqual(evil_sink, [])
        tb.publish(auth.issue("shop", "evil"), "orders", env("shop"))
        self.assertEqual(len(acme_sink), 1)

    def test_dead_letters_are_tenant_scoped(self):
        tb, auth, _ = tenant_bus()
        tb.grant("acme", "shop", "publish:o", "subscribe:o")
        tb.grant("evil", "spy", "subscribe:o")
        tb.publish(auth.issue("shop", "acme"), "o", env("shop"))
        self.assertEqual(len(tb.dead_letters(auth.issue("shop", "acme"), "o")), 1)
        self.assertEqual(tb.dead_letters(auth.issue("spy", "evil"), "o"), [])

    def test_namespace_separator_injection_refused(self):
        tb, auth, _ = tenant_bus()
        with self.assertRaises(ValueError):
            tb.grant("acme", "shop", "publish:evil::orders")
        tb.grant("acme", "shop", "publish:orders")
        with self.assertRaises(sec.Unauthenticated):
            tb.qualified("acme::x", "orders")

    def test_least_privilege_nothing_by_default_and_revocation(self):
        tb, auth, _ = tenant_bus()
        with self.assertRaises(rt.TopicDenied):
            tb.publish(auth.issue("shop", "acme"), "orders", env("shop"))
        tb.grant("acme", "shop", "subscribe:orders")
        with self.assertRaises(rt.TopicDenied):  # subscribe does not imply publish
            tb.publish(auth.issue("shop", "acme"), "orders", env("shop"))
        tb.grant("acme", "shop", "publish:orders")
        tb.publish(auth.issue("shop", "acme"), "orders", env("shop"))
        tb.grant("acme", "shop")  # revoke all
        with self.assertRaises(rt.TopicDenied):
            tb.publish(auth.issue("shop", "acme"), "orders", env("shop"))
        self.assertEqual(tb.bus.publishers["acme::orders"], frozenset())

    def test_source_must_match_token_identity(self):
        tb, auth, _ = tenant_bus()
        tb.grant("acme", "shop", "publish:orders")
        with self.assertRaises(rt.TopicDenied):
            tb.publish(auth.issue("shop", "acme"), "orders", env("billing"))


class AuditChainTest(unittest.TestCase):
    def test_denials_and_accepts_are_chained_and_verifiable(self):
        tb, auth, _ = tenant_bus()
        tb.grant("acme", "shop", "publish:o")
        tb.publish(auth.issue("shop", "acme"), "o", env("shop"))
        with self.assertRaises(sec.Unauthenticated):
            tb.publish("junk", "o", env("shop"))
        ev = tb.audit.events()
        kinds = [e["kind"] for e in ev]
        self.assertEqual(kinds, ["capability.grant", "publish.accepted", "authn.denied"])
        self.assertTrue(sec.AuditChain.verify(ev, head=tb.audit.head()))

    def test_tamper_reorder_and_truncation_detected(self):
        c = sec.AuditChain()
        for i in range(5):
            c.append("x", i=i)
        ev = c.events()
        t = [dict(e) for e in ev]
        t[2]["i"] = 99
        self.assertFalse(sec.AuditChain.verify(t))
        self.assertFalse(sec.AuditChain.verify([ev[1], ev[0]] + ev[2:]))
        self.assertFalse(sec.AuditChain.verify(ev[:-1], head=c.head()))

    def test_audit_redacts_secrets(self):
        c = sec.AuditChain()
        e = c.append("cfg", password="hunter2", note="-----BEGIN RSA PRIVATE KEY-----")
        self.assertEqual(e["password"], sec.REDACTED)
        self.assertEqual(e["note"], sec.REDACTED)


class SecretsArtifactsTest(unittest.TestCase):
    def test_find_secrets(self):
        self.assertEqual(sec.find_secrets({"a": {"api_key": "x"}, "b": "ok", "ref": "secretref:vault/x"}),
                         ["$.a.api_key"])
        self.assertTrue(sec.find_secrets({"conn": "Server=x;password=abc"}))

    def test_artifact_admission(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "adapter.whl"
            p.write_bytes(b"artifact")
            dg = sec.sha256_file(p)
            ok = sec.verify_artifact(p, {dg: {"name": "a", "version": "1", "provenance": "slsa:x"}})
            self.assertEqual(ok["sha256"], dg)
            with self.assertRaises(sec.ArtifactRejected):
                sec.verify_artifact(p, {})
            with self.assertRaises(sec.ArtifactRejected):
                sec.verify_artifact(p, {dg: {"name": "a", "version": "1", "provenance": ""}})
            p.write_bytes(b"tampered")
            with self.assertRaises(sec.ArtifactRejected):
                sec.verify_artifact(p, {dg: {"name": "a", "version": "1", "provenance": "slsa:x"}})


if __name__ == "__main__":
    unittest.main()
