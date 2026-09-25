"""Components 1-6, 8: IDL, envelope, handle encoding, negotiation, vectors."""
import json
import subprocess
import sys
import unittest

from _util import ROOT
from inv15_new_asynchronous_abi import _generated_bindings as G
from inv15_new_asynchronous_abi import handles as H
from inv15_new_asynchronous_abi.errors import (AbiError, CancelAck, CancelReason, ErrorCode, FORBIDDEN_CODES,
                                               from_envelope, BY_CODE, Replayed, UnsupportedFeature)
from inv15_new_asynchronous_abi.wire import codec


class TestIdl(unittest.TestCase):
    def test_bindings_reproducible(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "bindgen.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_generated_discriminants_match_runtime(self):
        self.assertEqual(G.ERROR_CODE, {e.name: int(e) for e in ErrorCode if e is not ErrorCode.OK})
        self.assertEqual(G.CANCEL_REASON, {e.name: int(e) for e in CancelReason})
        self.assertEqual(G.CANCEL_ACK, {e.name: int(e) for e in CancelAck})

    def test_forbidden_and_reserved_values_unassigned(self):
        for e in ErrorCode:
            self.assertNotIn(int(e), FORBIDDEN_CODES)
            self.assertLess(int(e), 64)

    def test_every_code_has_exception_and_roundtrips_envelope(self):
        for e in ErrorCode:
            if e is ErrorCode.OK:
                continue
            exc = BY_CODE[e]("d")
            env = exc.envelope()
            self.assertEqual(from_envelope(env).code, e)
            kind, got = codec.decode_call_result(codec.encode_call_result("error", exc))
            self.assertEqual((kind, got["code"]), ("error", int(e)))


class TestHandleEncoding(unittest.TestCase):
    def setUp(self):
        self.h = H.Handle(3, 9, 2, bytes(range(16)))

    def test_fixed_width_roundtrip(self):
        b = H.encode(self.h)
        self.assertEqual(len(b), 30)
        self.assertEqual(H.decode(b), self.h)

    def test_boundaries(self):
        for v in (0, H.U32):
            h = H.Handle(v, v, v, b"\x01" * 16)
            self.assertEqual(H.decode(H.encode(h)), h)
        for bad in (-1, H.U32 + 1, True, 1.0):
            with self.assertRaises(AbiError):
                H.Handle(bad, 0, 0, bytes(16))

    def test_redacted_repr(self):
        self.assertNotIn(self.h.token.hex(), repr(self.h) + str(self.h))

    def test_auth_binding(self):
        k = b"k" * 32
        b = H.encode(self.h, auth_key=k, tenant="t1")
        self.assertEqual(len(b), 46)
        self.assertEqual(H.decode(b, auth_key=k, tenant="t1"), self.h)
        with self.assertRaises(Replayed):
            H.decode(b, auth_key=k, tenant="t2")
        with self.assertRaises(Replayed):
            H.decode(H.encode(self.h), auth_key=k, tenant="t1")
        with self.assertRaises(UnsupportedFeature):
            H.decode(b)
        tampered = bytearray(b)
        tampered[20] ^= 1
        with self.assertRaises(Replayed):
            H.decode(bytes(tampered), auth_key=k, tenant="t1")


class TestNegotiation(unittest.TestCase):
    def test_negotiate(self):
        self.assertEqual(codec.negotiate([(1, 0)]), (1, 0))
        self.assertEqual(codec.negotiate([(1, 5), (2, 0)]), (1, 1))
        with self.assertRaises(AbiError) as c:
            codec.negotiate([(2, 0), (0, 9)])
        self.assertEqual(c.exception.code, ErrorCode.UNSUPPORTED_VERSION)

    def test_wait_is_canonical_set(self):
        a, b = H.Handle(1, 1, 0, bytes(16)), H.Handle(1, 0, 0, b"\x01" * 16)
        self.assertEqual(codec.encode_wait([a, b, a]), codec.encode_wait([b, a]))


class TestVectors(unittest.TestCase):
    def test_vectors_reproducible(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_interop_agrees(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "interop.py")], capture_output=True, text=True)
        rep = json.loads(r.stdout)
        self.assertEqual(rep["verdict"], "AGREE", rep)
        self.assertGreaterEqual(rep["vectors"], 60)

    def test_harness_detects_a_divergent_codec(self):
        """Falsifier: a codec that accepts duplicate wait members must be caught."""
        from inv15_new_asynchronous_abi.tools_shim import interop_with_broken_alt
        self.assertGreater(interop_with_broken_alt(), 0)


if __name__ == "__main__":
    unittest.main()
