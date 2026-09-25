"""Negative / edge paths that the thematic suites do not reach (coverage policy ci/coverage-policy.json)."""
import unittest

from _pkg import configuration as K, observability as O, security as X, stream as S, open_stream, registry


class EdgePathTest(unittest.TestCase):
    def test_keyring_rejects_short_keys_at_construction(self):
        with self.assertRaises(ValueError): X.KeyRing({"k": b"short"})

    def test_verify_unknown_right_and_version(self):
        a = X.CapabilityAuthority()
        tok = a.issue("s", "t", "w", ["read"])
        with self.assertRaises(ValueError): a.verify(tok, stream_id="s", tenant="t", workload="w", right="fly")
        body = X.canonical({"v": 2, "kid": "k1"})
        import hashlib
        import hmac
        mac = hmac.new(a.keys.get("k1"), body, hashlib.sha256).digest()
        with self.assertRaises(X.AuthError):
            a.verify(X._b64(body) + "." + X._b64(mac), stream_id="s", tenant="t", workload="w", right="read")

    def test_replay_cache_never_evicts_live_single_use_nonce(self):
        now = [0.0]
        a = X.CapabilityAuthority(clock=X.TrustedClock(lambda: now[0]), replay_cache=2)
        v = lambda tok: a.verify(tok, stream_id="s", tenant="t", workload="w", right="transfer")
        t1, t2, t3 = (a.issue("s", "t", "w", ["transfer"], ttl=10) for _ in range(3))
        v(t1); v(t2)
        with self.assertRaises(X.TrustServiceUnavailable): v(t3)   # full: fail closed, no eviction
        with self.assertRaises(X.TokenReplay): v(t1)                # t1 still protected
        for _ in range(5):  # multi-use tokens never occupy the cache
            a.verify(a.issue("s", "t", "w", ["read"]), stream_id="s", tenant="t", workload="w", right="read")
        self.assertEqual(len(a._replay), 2)
        now[0] += 11
        t4 = a.issue("s", "t", "w", ["transfer"], ttl=10)
        v(t4)                                                       # expired nonces purged, room again
        self.assertEqual(len(a._replay), 1)

    def test_single_use_is_a_signed_claim(self):
        keys = X.KeyRing()
        a = X.CapabilityAuthority(keys=keys)
        tok = a.issue("s", "t", "w", ["read"], single_use=True)
        cap = a.verify(tok, stream_id="s", tenant="t", workload="w", right="read")
        self.assertTrue(cap.single_use)
        with self.assertRaises(X.TokenReplay):
            a.verify(tok, stream_id="s", tenant="t", workload="w", right="read")

    def test_rebalance_stops_when_streams_are_full(self):
        r = registry()
        s, _ = open_stream(r, config=S.StreamConfig(max_credit=2, max_buffer=2))
        self.assertEqual(r.rebalance(50), {"s1": 2})
        s.freeze("x")
        self.assertEqual(r.rebalance(5), {})

    def test_degraded_stall_ratio(self):
        r = registry()
        s, _ = open_stream(r, config=S.StreamConfig(max_credit=100, max_buffer=100))
        s.grant(100)
        for i in range(30): s.write(i); s.read()
        s2, _ = open_stream(r, "b", config=S.StreamConfig(max_credit=100, max_buffer=100))
        s2.grant(15)
        for i in range(15): s2.write(i); s2.read()
        for _ in range(10):
            with self.assertRaises(S.CreditExhausted): s2.write(1)
        s2.grant(1)  # not stalled now, ratio 10/25 = 0.4 -> degraded
        h = r.health()
        self.assertEqual(h.status, "degraded")
        self.assertIn("stall ratio", h.reasons[0])

    def test_validator_maximum_and_items(self):
        schema = {"type": "array", "items": {"type": "integer", "maximum": 3}}
        self.assertEqual(K.validate([1, 2], schema), [])
        self.assertEqual(len(K.validate([1, 9], schema)), 1)

    def test_probe_failure_audited(self):
        audit = X.AuditLedger()
        m = K.ConfigManager(audit=audit)
        with self.assertRaises(K.ActivationFailed):
            m.activate({}, author="a", source_revision="r", reason="x", health_probe=lambda c: False)
        self.assertEqual(audit.events[-1].outcome, "auto")

    def test_stream_requires_runtime_type(self):
        with self.assertRaises(TypeError): S.Stream("int")

    def test_exporter_guards(self):
        r = registry()
        exp = O.MetricsExporter(r)
        orig = O.MAX_SERIES
        try:
            O.MAX_SERIES = 1
            with self.assertRaises(RuntimeError): exp.samples()
        finally:
            O.MAX_SERIES = orig
        orig_allowed = O.ALLOWED_LABELS
        try:
            O.ALLOWED_LABELS = frozenset()
            open_stream(r)
            with self.assertRaises(ValueError): exp.samples()
        finally:
            O.ALLOWED_LABELS = orig_allowed


if __name__ == "__main__":
    unittest.main()
