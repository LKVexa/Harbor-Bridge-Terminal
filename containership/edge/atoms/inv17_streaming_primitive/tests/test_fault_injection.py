"""C060: fault injection -- endpoint loss, dependency outage, probe crash, clock jumps,
hostile callbacks -- each with its recovery objective asserted."""
import unittest

from _pkg import adapters as A, configuration as K, control as C, security as X, stream as S, open_stream, registry


class FaultInjectionTest(unittest.TestCase):
    def test_reader_process_death_mid_stream(self):
        """Objective: writer learns on the first attempt; memory reclaimed immediately."""
        s = S.Stream(bytes); s.grant(3); s.write(b"a"); s.write(b"b")
        s.drop_reader()  # injected: reader process gone
        with self.assertRaises(S.EndDropped): s.write(b"c")
        self.assertEqual(s.stats().buffered, 0)

    def test_writer_process_death_mid_stream(self):
        """Objective: reader drains what was sent, then gets an error -- not a clean EOF."""
        s = S.Stream(bytes); s.grant(2); s.write(b"a"); s.drop_writer()
        self.assertEqual(s.read(), b"a")
        with self.assertRaises(S.EndDropped): s.read()

    def test_key_service_flap(self):
        """Objective: fail closed during the outage, recover without restart when it returns."""
        r = registry(); s, tok = open_stream(r); s.grant(5)
        r.authority.keys.available = False
        for _ in range(3):
            with self.assertRaises(X.TrustServiceUnavailable):
                r.write("s1", 1, tenant="t1", workload="w1", token=tok)
        r.authority.keys.available = True
        self.assertTrue(r.write("s1", 1, tenant="t1", workload="w1", token=tok))

    def test_clock_jump_forward_expires_tokens(self):
        now = [0.0]
        auth = X.CapabilityAuthority(clock=X.TrustedClock(lambda: now[0]))
        r = C.StreamRegistry(authority=auth)
        tok = auth.issue("s", "t", "w", ["open", "write"], ttl=30)
        r.open(int, tenant="t", workload="w", token=tok, stream_id="s")
        now[0] += 3600
        with self.assertRaises(X.AuthError):
            r.write("s", 1, tenant="t", workload="w", token=tok)

    def test_config_probe_crash_and_bad_overlay(self):
        """Objective: last-known-good configuration keeps serving."""
        m = K.ConfigManager(); good = m.provenance.digest
        with self.assertRaises(K.ActivationFailed):
            m.activate({}, author="a", source_revision="r", reason="x", health_probe=lambda c: 1 / 0)
        with self.assertRaises(K.ConfigInvalid):
            m.activate({"stream": "corrupt"}, author="a", source_revision="r", reason="x")
        self.assertEqual(m.provenance.digest, good)

    def test_fold_callback_raises_leaves_trailer_unresolved(self):
        s = S.Stream(int); s.grant(1); s.write(1); s.end()
        tr = A.Completion()
        with self.assertRaises(ZeroDivisionError):
            A.drain_to_completion(s, tr, lambda a, v: v / 0, 0)
        self.assertFalse(tr.done)

    def test_overload_then_recovery(self):
        """Objective: breaker opens under sustained overload and closes after drain + cooldown."""
        now = [0.0]
        r = registry(global_buffer_budget=2, clock=lambda: now[0])
        s, tok = open_stream(r); s.grant(50)
        for i in range(2): r.write("s1", i, tenant="t1", workload="w1", token=tok)
        for _ in range(6):
            with self.assertRaises(C.LoadShed): r.write("s1", 9, tenant="t1", workload="w1", token=tok)
        self.assertEqual(r.breaker.state, "open")
        s.read(); s.read(); now[0] += 10
        self.assertTrue(r.breaker.allow())
        r.write("s1", 3, tenant="t1", workload="w1", token=tok)
        self.assertEqual(r.breaker.state, "closed")
        self.assertEqual(r.health().status, "healthy")


if __name__ == "__main__":
    unittest.main()
