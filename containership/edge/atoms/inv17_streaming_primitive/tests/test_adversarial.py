"""C050/C087: adversarial and resource-exhaustion suite (abuse cases from security/THREAT_MODEL.md)."""
import gc
import sys
import tracemalloc
import unittest

from _pkg import control as C, security as X, stream as S, open_stream, registry


class HostileInt(int):
    """A subclass that lies about equality and explodes on repr/hash."""
    def __eq__(self, o): return True
    def __hash__(self): raise RuntimeError("hostile hash")
    def __repr__(self): raise RuntimeError("hostile repr")


class AdversarialTest(unittest.TestCase):
    def test_memory_exhaustion_is_bounded(self):
        s = S.Stream(bytes, config=S.StreamConfig(max_credit=8, max_buffer=8))
        s.grant(8)
        tracemalloc.start()
        refused = 0
        for _ in range(100_000):
            try:
                s.write(b"x" * 64)
            except (S.CreditExhausted, S.BufferLimitExceeded):
                refused += 1
        cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        self.assertEqual(len(s.buffer), 8)
        self.assertEqual(refused, 100_000 - 8)
        self.assertLess(peak, 2_000_000)

    def test_credit_overflow_attempts(self):
        s = S.Stream(int)
        for n in (sys.maxsize, 2 ** 64, 10 ** 100):
            with self.assertRaises(S.CreditLimitExceeded): s.grant(n)
        self.assertEqual(s.credit, 0)

    def test_hostile_subclass_elements_do_not_break_runtime(self):
        s = S.Stream(int); s.grant(2)
        # a subclass of the declared type is a valid element; the runtime must never call
        # its hash/repr/eq, so hostile dunder methods cannot corrupt stream state
        self.assertTrue(s.write(HostileInt(3)))
        self.assertTrue(s.write(HostileInt(4)))
        with self.assertRaises(RuntimeError):
            hash(HostileInt(1))  # proves the element really is hostile
        st = s.stats()
        self.assertEqual((st.transferred, st.buffered), (2, 2))
        self.assertIsInstance(s.read(), HostileInt)
        s.drop_reader()
        self.assertEqual(s.stats().dropped_items, 1)

    def test_type_confusion_matrix(self):
        for t, bad in ((int, [True, 1.0, "1", b"1", None]), (str, [b"s", 1, None]), (bytes, [bytearray(b"x"), "x"])):
            s = S.Stream(t); s.grant(len(bad))
            for v in bad:
                with self.assertRaises(S.ElementTypeMismatch): s.write(v)
            self.assertEqual(s.credit, len(bad))

    def test_token_spoofing_and_replay_are_audited(self):
        r = registry()
        s, tok = open_stream(r)
        forged = tok[:-4] + ("AAAA" if not tok.endswith("AAAA") else "BBBB")
        with self.assertRaises(X.AuthError):
            r.write("s1", 1, tenant="t1", workload="w1", token=forged)
        xfer = r.authority.issue("s1", "t1", "w1", ["transfer"])
        r.transfer("s1", from_tenant="t1", workload="w1", token=xfer, to_tenant="t1", to_workload="w1")
        with self.assertRaises(X.TokenReplay):
            r.transfer("s1", from_tenant="t1", workload="w1", token=xfer, to_tenant="t9", to_workload="w1")
        kinds = [e.kind for e in r.audit.events]
        self.assertIn("auth.denied", kinds); self.assertIn("auth.replay", kinds)
        self.assertEqual(r.audit.verify(), [])

    def test_stream_id_squatting_and_enumeration(self):
        r = registry()
        open_stream(r, "victim", tenant="t1")
        tok = r.authority.issue("victim", "t2", "w1", ["open", "read"])
        with self.assertRaises(C.StreamError):
            r.open(int, tenant="t2", workload="w1", token=tok, stream_id="victim")
        with self.assertRaises(X.AuthzDenied):
            r.get("victim", tenant="t2", workload="w1", token=tok, right="read")

    def test_tenant_flood_cannot_starve_others(self):
        r = registry(quotas={"attacker": C.TenantQuota(max_streams=3, max_buffered=5)})
        for i in range(3): open_stream(r, f"a{i}", tenant="attacker")
        with self.assertRaises(C.QuotaExceeded): open_stream(r, "a3", tenant="attacker")
        open_stream(r, "v", tenant="victim")
        g = r.rebalance(8)
        self.assertGreaterEqual(g.get("v", 0), 1)

    def test_reader_drop_releases_references(self):
        class Big: pass
        s = S.Stream(Big); s.grant(3)
        import weakref
        objs = [Big() for _ in range(3)]; refs = [weakref.ref(o) for o in objs]
        for o in objs: s.write(o)
        del objs, o
        s.drop_reader(); gc.collect()
        self.assertTrue(all(r() is None for r in refs), "dropped elements still referenced")

    def test_oversized_identifiers_rejected(self):
        auth = X.CapabilityAuthority()
        with self.assertRaises(ValueError): auth.issue("s" * 500, "t", "w", ["read"])


if __name__ == "__main__":
    unittest.main()
