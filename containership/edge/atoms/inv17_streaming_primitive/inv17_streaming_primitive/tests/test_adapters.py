"""C030/C083: adjacent-layer adapters (INV-15/12/18/19/20) and sibling-contract reciprocity."""
import importlib.util
import sys
import unittest

from _pkg import adapters as A, stream as S, PKG_DIR

VENDOR = PKG_DIR / "vendor"


class WaitableSetTest(unittest.TestCase):
    def test_readiness(self):
        ws = A.WaitableSet()
        a, b = S.Stream(int), S.Stream(int)
        ws.join(a); ws.join(b)
        self.assertEqual(ws.poll(), {})
        a.grant(1)
        self.assertEqual(ws.poll(), {a.stream_id: {"writable"}})
        a.write(1)
        self.assertEqual(ws.poll(), {a.stream_id: {"readable"}})
        b.end()
        self.assertEqual(ws.poll()[b.stream_id], {"readable"})
        ws.leave(b); self.assertNotIn(b.stream_id, ws.poll())


class CodecTest(unittest.TestCase):
    def test_roundtrip_and_type_recheck(self):
        c = A.CanonicalCodec()
        for v, t in ((b"x", bytes), ("é", str), (-5, int), (2.5, float), ({"a": [1]}, dict), ((1, 2), tuple)):
            self.assertEqual(c.lift(c.lower(v), t), v)
        with self.assertRaises(A.AdapterError): c.lift(c.lower(1), str)
        with self.assertRaises(A.AdapterError): c.lower(True)
        with self.assertRaises(A.AdapterError): c.lower(1 << 70)
        with self.assertRaises(A.AdapterError): c.lower(object())
        for junk in (b"", b"z", b"i123", b"s\xff", "str"):
            with self.assertRaises(A.AdapterError): c.lift(junk, int)
        with self.assertRaises(A.AdapterError): c.lower(b"x" * (1 << 20))


class CompletionTest(unittest.TestCase):
    def test_drain_to_trailer(self):
        s = S.Stream(int); s.grant(3)
        for i in (1, 2, 3): s.write(i)
        s.end()
        tr = A.Completion()
        self.assertEqual(A.drain_to_completion(s, tr, lambda a, v: a + v, 0), 6)
        self.assertTrue(tr.done)
        with self.assertRaises(A.AdapterError): tr.resolve(1)

    def test_writer_drop_resolves_error_not_value(self):
        s = S.Stream(int); s.grant(1); s.write(1); s.drop_writer()
        tr = A.Completion()
        with self.assertRaises(S.EndDropped):
            A.drain_to_completion(s, tr, lambda a, v: a + v, 0)
        self.assertIsInstance(tr.value, S.EndDropped)

    def test_not_ready(self):
        with self.assertRaises(A.AdapterError):
            A.drain_to_completion(S.Stream(int), A.Completion(), lambda a, v: a, 0)


class HttpBodyTest(unittest.TestCase):
    def test_chunked_body_respects_credit(self):
        s = S.Stream(bytes); body = A.HttpBody(s, chunk=4)
        data = b"0123456789"
        self.assertEqual(body.send(data), 0)
        s.grant(2)
        self.assertEqual(body.send(data), 8)
        with self.assertRaises(A.AdapterError): body.receive_all()
        s.grant(1); body.send(data[8:]); s.end()
        self.assertEqual(body.receive_all(), data)
        with self.assertRaises(A.AdapterError): A.HttpBody(S.Stream(str))
        with self.assertRaises(ValueError): A.HttpBody(S.Stream(bytes), chunk=0)


class OsBridgeTest(unittest.TestCase):
    def test_readiness_clamped_to_ceiling(self):
        s = S.Stream(int, config=S.StreamConfig(max_credit=8, max_buffer=8))
        br = A.OsReadinessBridge(s)
        self.assertEqual(br.on_ready(5), 5)
        self.assertEqual(br.on_ready(10 ** 9), 3)
        self.assertEqual(br.on_ready(1), 0)
        for bad in (-1, True, 1.5):
            with self.assertRaises(A.AdapterError): br.on_ready(bad)


def _load_contract(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build()


class SiblingReciprocityTest(unittest.TestCase):
    """Loads the real sibling contracts vendored from the owner's PK estate (needs vendored pk_core)."""

    @classmethod
    def setUpClass(cls):
        if str(VENDOR) not in sys.path:
            sys.path.insert(0, str(VENDOR))
        own = _load_contract(PKG_DIR / "contract.py", "inv17_contract_under_test")
        cls.own = [(d.name, d.relation) for d in own.dependencies]
        cls.sibs = {}
        for p in sorted((VENDOR / "pk_siblings").glob("*/contract.py")):
            c = _load_contract(p, "sib_" + p.parent.name)
            cls.sibs[c.element] = [(d.name, d.relation) for d in c.dependencies]

    def test_all_five_siblings_present(self):
        self.assertEqual(sorted(self.sibs), ["INV-12", "INV-15", "INV-18", "INV-19", "INV-20"])

    def test_reciprocity_report_matches_known_state(self):
        rep = {r["sibling"]: r for r in A.reciprocity(self.own, self.sibs)}
        for sid in ("INV-15", "INV-18", "INV-19", "INV-20"):
            self.assertTrue(rep[sid]["consistent"], rep[sid])
        # Recorded finding (integration/adjacent-layers.json): INV-12 does not declare INV-17.
        self.assertFalse(rep["INV-12"]["consistent"])
        self.assertIsNone(rep["INV-12"]["sibling_says"])


if __name__ == "__main__":
    unittest.main()
