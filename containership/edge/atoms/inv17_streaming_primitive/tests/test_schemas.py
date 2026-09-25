"""C021-C022/C082/C093: every public interface has a hashed schema and exhaustive contract tests."""
import json
import unittest

from _pkg import PKG_DIR, control as C, stream as S, wire as W


class SchemaArtifactTest(unittest.TestCase):
    def test_manifest_hashes_match(self):
        import hashlib
        man = json.loads((PKG_DIR / "interfaces" / "schema-manifest.json").read_text())
        for rel, digest in man["sha256"].items():
            self.assertEqual(hashlib.sha256((PKG_DIR / rel).read_bytes()).hexdigest(), digest, rel)
        for iface in ("PK_STREAM/1", "PK_STREAM_CREDIT/1", "PK_STREAM_CLOSE/1"):
            self.assertTrue((PKG_DIR / man["interfaces"][iface]).exists())

    def test_contract_interfaces_all_have_schemas(self):
        for name in S.PROTOCOL_VERSIONS:
            self.assertIn(name, W.SCHEMAS)

    def test_wit_declares_every_operation(self):
        wit = (PKG_DIR / "schemas" / "pk_stream.wit").read_text()
        for op in ("grant:", "write:", "read:", "close:", "state:", "limits:"):
            self.assertIn(op, wit)


class PkStreamTest(unittest.TestCase):
    def test_describe_every_state(self):
        def mk():
            s = S.Stream(bytes, stream_id="s-1"); return s
        cases = []
        s = mk(); cases.append((s, "credit_stalled"))
        s = mk(); s.grant(1); cases.append((s, "open"))
        s = mk(); s.freeze("x"); cases.append((s, "frozen"))
        s = mk(); s.end(); cases.append((s, "ended"))
        s = mk(); s.drop_writer(); cases.append((s, "writer_dropped"))
        s = mk(); s.drop_reader(); cases.append((s, "reader_dropped"))
        for s, state in cases:
            self.assertEqual(W.describe(s)["state"], state)

    def test_describe_refuses_unschematised_element_type(self):
        with self.assertRaises(W.WireInvalid):
            W.describe(S.Stream(set, stream_id="s-1"))


class CreditCloseTest(unittest.TestCase):
    def setUp(self):
        self.fx = json.loads((PKG_DIR / "compatibility" / "fixtures" / "v1-golden.json").read_text())

    def test_golden_accept(self):
        for doc in self.fx["accept"]:
            s = S.Stream(int, stream_id="s-golden")
            (W.apply_credit if doc["interface"] == "PK_STREAM_CREDIT" else W.apply_close)(s, doc)

    def test_golden_reject(self):
        for doc in self.fx["reject"]:
            s = S.Stream(int, stream_id="s-golden")
            fn = W.apply_credit if doc["interface"] == "PK_STREAM_CREDIT" else W.apply_close
            with self.assertRaises((W.WireInvalid, C.VersionUnsupported), msg=doc):
                fn(s, doc)
            self.assertEqual((s.credit, s.state), (0, "credit_stalled"), "a rejected message must not mutate state")

    def test_close_kinds_semantics(self):
        for kind, state in (("end", "ended"), ("drop_reader", "reader_dropped"), ("drop_writer", "writer_dropped")):
            s = S.Stream(int, stream_id="x")
            W.apply_close(s, {"interface": "PK_STREAM_CLOSE", "version": 1, "stream_id": "x", "kind": kind})
            self.assertEqual(s.state, state)

    def test_credit_respects_runtime_ceiling(self):
        s = S.Stream(int, stream_id="x", config=S.StreamConfig(max_credit=2, max_buffer=2))
        with self.assertRaises(S.CreditLimitExceeded):
            W.apply_credit(s, {"interface": "PK_STREAM_CREDIT", "version": 1, "stream_id": "x", "credit": 3})

    def test_non_object(self):
        with self.assertRaises(W.WireInvalid):
            W.apply_credit(S.Stream(int), [1])


class ErrorEnvelopeTest(unittest.TestCase):
    def test_every_error_class_fits_envelope(self):
        import inspect
        from _pkg import adapters, configuration, control, security
        classes = set()
        for mod in (S, control, security, configuration, adapters, W):
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, S.StreamError):
                    classes.add(obj)
        self.assertGreaterEqual(len(classes), 20)
        codes = set()
        for cls in classes:
            doc = W.error_envelope(cls("m", k=object()))
            codes.add(doc["code"])
        self.assertEqual(len(codes), len(classes), "error codes must be unique per class")


if __name__ == "__main__":
    unittest.main()
