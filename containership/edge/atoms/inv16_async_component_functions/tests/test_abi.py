"""Closure #9: canonical ABI transport - round-trips, canonicality, limits, fuzz."""
import math
import random
import struct
import unittest

from _util import rt, scale, sub

abi = sub("abi")
C = abi.Codec()


def rand_value(rng, depth=0):
    k = rng.randint(0, 9 if depth < 4 else 5)
    if k == 0: return None
    if k == 1: return rng.random() < 0.5
    if k == 2: return rng.randint(-(1 << 63), (1 << 63) - 1)
    if k == 3: return rng.choice([0.0, -0.0, 1.5, float("inf"), -1e308, rng.random()])
    if k == 4: return "".join(chr(rng.choice([0x41, 0xe9, 0x4e2d, 0x1f600])) for _ in range(rng.randint(0, 5)))
    if k == 5: return bytes(rng.randrange(256) for _ in range(rng.randint(0, 6)))
    if k == 6: return [rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    if k == 7: return {f"k{rng.randint(0, 9)}": rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))}
    if k == 8: return abi.Variant(rng.choice(["ok", "err"]), rand_value(rng, depth + 1))
    return abi.ErrorValue("E" + str(rng.randint(0, 9)), "m")


class Abi(unittest.TestCase):
    def test_every_category_round_trips_through_completion(self):
        f = rt.AsyncFunctions("i", declared={"a": True}, transport=C)
        samples = [None, True, False, 0, -1, (1 << 63) - 1, -(1 << 63), 1.25, "héllo 中 😀", b"\x00\xff",
                   [1, [2, [3]]], {"b": 1, "a": [None]}, abi.Variant("some", 3), abi.ErrorValue("E1", "bad")]
        for v in samples:
            c = f.invoke("a")
            got = f.complete(c.call_id, v)
            self.assertEqual(got, v)
            if isinstance(v, (list, dict)):
                self.assertIsNot(got, v)          # fresh objects, no identity crosses the ABI
        c = f.invoke("a")
        self.assertTrue(math.isnan(f.complete(c.call_id, float("nan"))))
        self.assertEqual(f.complete(f.invoke("a").call_id, (1, 2)), [1, 2])   # tuple lowers as list

    def test_payload_bound_to_call_id(self):
        p = C.lower({"x": 1}, 7)
        with self.assertRaises(abi.AbiError):
            C.lift(p, 8)

    def test_canonical_and_deterministic(self):
        self.assertEqual(C.lower({"b": 1, "a": 2}, 1), C.lower({"a": 2, "b": 1}, 1))
        p = bytearray(C.lower({"a": 1, "b": 2}, 1))
        # swap key order in the wire form -> non-canonical, must be rejected
        body = bytes(p[16:])
        swapped = body.replace(b"\x01\x00\x00\x00a", b"\x01\x00\x00\x00Z", 1)
        with self.assertRaises(abi.AbiError):
            C.lift(bytes(p[:16]) + swapped.replace(b"Z", b"c"), 1)
        bad_nan = bytearray(C.lower(float("nan"), 1))
        bad_nan[-8:] = struct.pack("<Q", 0x7ff0000000000001)
        with self.assertRaises(abi.AbiError):
            C.lift(bytes(bad_nan), 1)

    def test_limits_and_malformed(self):
        small = abi.Codec(abi.Limits(max_bytes=64, max_depth=3, max_items=10))
        for v in ("x" * 100, [[[[[1]]]]], list(range(20))):
            with self.assertRaises(abi.AbiError):
                small.lower(v, 1)
        for v in (object(), {1: 2}, {1.0}, 1 << 64, "\ud800", rt):
            with self.assertRaises((abi.AbiError, abi.AbiTypeError)):
                C.lower(v, 1)
        good = C.lower(["abc", 1], 3)
        for bad in (good[:-1], good + b"\x00", b"XXX" + good[3:], good[:3] + b"\x09" + good[4:],
                    b"", good[:10]):
            with self.assertRaises(abi.AbiError):
                C.lift(bad, 3)
        # huge declared length must not allocate
        evil = struct.pack("<3sBQI", b"PKV", 1, 3, 5) + b"\x07" + struct.pack("<I", 0xFFFFFFFF)
        with self.assertRaises(abi.AbiError):
            C.lift(evil, 3)
        invalid_utf8 = struct.pack("<3sBQI", b"PKV", 1, 3, 7) + b"\x05" + struct.pack("<I", 2) + b"\xc3\x28"
        with self.assertRaises(abi.AbiError):
            C.lift(invalid_utf8, 3)

    def test_property_round_trip(self):
        rng = random.Random(909)
        for i in range(scale(2000)):
            v = rand_value(rng)
            p = C.lower(v, i + 1)
            self.assertEqual(C.lower(C.lift(p, i + 1), i + 1), p)   # canonical fixpoint

    def test_mutation_fuzz_never_crashes(self):
        rng = random.Random(4242)
        seeds = [C.lower(rand_value(rng), 1) for _ in range(50)]
        for _ in range(scale(5000)):
            b = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 4)):
                op = rng.randint(0, 2)
                if op == 0 and b:
                    b[rng.randrange(len(b))] = rng.randrange(256)
                elif op == 1 and b:
                    del b[rng.randrange(len(b))]
                else:
                    b.insert(rng.randrange(len(b) + 1), rng.randrange(256))
            try:
                v = C.lift(bytes(b), 1)
            except abi.AbiError:
                continue
            self.assertEqual(C.lift(C.lower(v, 1), 1), v) if v == v else None

    def test_schema_version_skew(self):
        p = bytearray(C.lower(1, 1))
        p[3] = 2
        with self.assertRaises(abi.AbiError):
            C.lift(bytes(p), 1)
        with self.assertRaises(abi.AbiError):
            abi.Codec(schema=2)


if __name__ == "__main__":
    unittest.main()
