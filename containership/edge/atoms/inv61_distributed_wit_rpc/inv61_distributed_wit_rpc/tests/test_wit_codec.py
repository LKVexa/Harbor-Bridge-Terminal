"""M04/M24 - WIT parser, canonical codec, envelope; property and fuzz tests."""
import math
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rpc import fingerprint  # noqa: E402
from wrpc import codec, wit  # noqa: E402
from wrpc.codec import CodecError  # noqa: E402

WIT = """package pk:kv@0.2.0;
// comment
interface store {
  record entry { key: string, ttl: option<u32> }
  enum mode { fast, safe }
  variant err { missing, denied(string) }
  type key = string;
  get: func(k: key, m: mode) -> result<option<u64>, err>;
  put: func(e: entry, v: list<u8>, t: tuple<s64, f64, bool, char>);
}
"""
FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


class WitParserTest(unittest.TestCase):
    def setUp(self):
        self.pkg = wit.parse(WIT)
        self.iface = self.pkg.interfaces["store"]

    def test_package_and_functions(self):
        self.assertEqual((self.pkg.namespace, self.pkg.name, self.pkg.version), ("pk", "kv", "0.2.0"))
        self.assertEqual(sorted(self.iface.functions), ["get", "put"])
        self.assertEqual(wit.qualified(self.pkg, "store"), "pk:kv/store")

    def test_alias_resolves_so_fingerprints_ignore_spelling(self):
        a = wit.parse("package a:b@1.0.0; interface i { type k = string; f: func(x: k) -> u8; }")
        b = wit.parse("package a:b@1.0.0; interface i { f: func(x: string) -> u8; }")
        fa, fb = a.interfaces["i"].functions["f"], b.interfaces["i"].functions["f"]
        self.assertEqual(fingerprint(fa.param_texts(), fa.result_texts()),
                         fingerprint(fb.param_texts(), fb.result_texts()))

    def test_record_field_change_changes_fingerprint(self):
        a = wit.parse("package a:b@1.0.0; interface i { record r { x: u8 } f: func(v: r); }")
        b = wit.parse("package a:b@1.0.0; interface i { record r { x: u16 } f: func(v: r); }")
        fa, fb = a.interfaces["i"].functions["f"], b.interfaces["i"].functions["f"]
        self.assertNotEqual(fingerprint(fa.param_texts(), []), fingerprint(fb.param_texts(), []))

    def test_rejections_are_stable(self):
        cases = {
            "package a:b@1.0.0; interface i { resource r; }": "unsupported-construct:resource",
            "package a:b@1.0.0; world w { }": "unsupported-construct:world",
            "package a:b@1.0.0; interface i { f: func(x: nope); }": "undefined-type:nope",
            "package a:b@1.0.0; interface i { f: func(); f: func(); }": "duplicate-function:f",
            "package a:b@1.0.0; interface i { enum e { x, x } }": "bad-cases:e",
            "package ab; interface i {}": "package reference",
            "package a:b@1.0.0; interface i { f: func(x: list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<list<u8>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>); }": "type-too-deep",
        }
        for src, code in cases.items():
            with self.subTest(code=code):
                with self.assertRaises(wit.WitError) as cm:
                    wit.parse(src)
                self.assertIn(code, str(cm.exception))

    def test_source_size_bound(self):
        with self.assertRaises(wit.WitError):
            wit.parse("package a:b@1.0.0;" + " " * (wit.MAX_SOURCE + 1))


class CodecTest(unittest.TestCase):
    def setUp(self):
        self.iface = wit.parse(WIT).interfaces["store"]
        self.put = [t for _, t in self.iface.functions["put"].params]

    def test_round_trip_and_canonical(self):
        vals = [{"key": "a", "ttl": 7}, [0, 1, 255], [-(2 ** 63), 1.5, False, "\U0001F600"]]
        b = codec.encode_args(self.put, vals)
        self.assertEqual(codec.decode_args(self.put, b), vals)
        self.assertEqual(codec.encode_args(self.put, codec.decode_args(self.put, b)), b)

    def test_golden_vectors(self):
        """Cross-implementation fixtures (fixtures/golden_vectors.json) pin the exact bytes."""
        import json
        vectors = json.loads((FIXTURE_DIR / "golden_vectors.json").read_text())
        for v in vectors:
            t = wit.parse(f"package g:v@1.0.0; interface i {{ f: func(x: {v['type']}); }}").interfaces["i"].functions["f"].params[0][1]
            with self.subTest(type=v["type"], value=v["value"]):
                out = bytearray()
                codec.encode_value(t, v["value"], out)
                self.assertEqual(out.hex(), v["hex"])

    def test_nan_is_canonicalised_and_foreign_nan_rejected(self):
        t = wit.T("f64")
        out = bytearray()
        codec.encode_value(t, float("nan"), out)
        self.assertTrue(math.isnan(codec.decode_args([t], bytes(out))[0]))
        with self.assertRaises(CodecError) as cm:
            codec.decode_args([t], bytes.fromhex("7ff8000000000001"))
        self.assertEqual(cm.exception.code, "nan-noncanonical")

    def test_negative_paths(self):
        u8, s8, b = wit.T("u8"), wit.T("s8"), wit.T("bool")
        bad = [
            ([u8], "80", "truncated"), ([u8], "8002", "int-range"), ([u8], "8000", "varint-noncanonical"),
            ([b], "02", "bool-range"), ([u8], "0101", "trailing-bytes"),
            ([wit.T("string")], "01ff", "utf8"), ([wit.T("list", (u8,))], "ffff03", "list-limit"),
            ([wit.T("option", (u8,))], "02", "option-tag"), ([s8], "8002", "int-range"),
        ]
        for types, hx, code in bad:
            with self.subTest(code=code):
                with self.assertRaises(CodecError) as cm:
                    codec.decode_args(types, bytes.fromhex(hx))
                self.assertEqual(cm.exception.code, code)
        for t, v in [(u8, 256), (u8, -1), (u8, True), (s8, 128), (wit.T("char"), "ab"), (wit.T("char"), "\ud800")]:
            with self.assertRaises(CodecError):
                codec.encode_value(t, v, bytearray())

    def test_signed_extremes(self):
        for bits in (8, 16, 32, 64):
            t = wit.T(f"s{bits}")
            for v in (-(1 << (bits - 1)), -1, 0, 1, (1 << (bits - 1)) - 1):
                out = bytearray()
                codec.encode_value(t, v, out)
                self.assertEqual(codec.decode_args([t], bytes(out)), [v])

    def test_envelope_header_decoded_without_touching_args(self):
        h = {"interface": "pk:kv/store", "version": "0.2.0", "function": "get", "fp": "0123456789abcdef",
             "deadline": 12.5, "request_id": "00" * 16, "traceparent": ""}
        raw = codec.encode_frame(h, b"\xff\xff\xff")   # garbage args: header must still decode
        got, payload = codec.decode_header(raw)
        self.assertEqual(got["fp"], h["fp"])
        self.assertEqual(payload, b"\xff\xff\xff")
        for mutate, code in [(lambda r: b"XX" + r[2:], "magic"), (lambda r: r[:2] + b"\x09" + r[3:], "wire-version"),
                             (lambda r: r[:-1], "truncated"), (lambda r: r + b"\x00", "trailing-bytes")]:
            with self.assertRaises(CodecError) as cm:
                codec.decode_header(mutate(raw))
            self.assertEqual(cm.exception.code, code)
        with self.assertRaises(CodecError):
            codec.encode_frame(dict(h, deadline=float("inf")), b"")


def _random_value(t, rng, depth=0):
    k = t.kind
    if k == "bool":
        return rng.random() < 0.5
    if k == "string":
        return "".join(chr(rng.choice([rng.randrange(32, 127), rng.randrange(0x80, 0xD7FF), 0x1F600])) for _ in range(rng.randrange(0, 12)))
    if k.startswith("u"):
        return rng.randrange(0, 1 << int(k[1:]))
    if k.startswith("s"):
        n = int(k[1:])
        return rng.randrange(-(1 << (n - 1)), 1 << (n - 1))
    if k == "f64":
        return rng.choice([0.0, -0.0, 1e308, -1e-308, rng.uniform(-1e6, 1e6), float("inf")])
    if k == "string":
        return "".join(chr(rng.choice([rng.randrange(32, 127), rng.randrange(0x80, 0xD7FF), 0x1F600])) for _ in range(rng.randrange(0, 12)))
    if k == "list":
        return [_random_value(t.args[0], rng, depth + 1) for _ in range(rng.randrange(0, 4))]
    if k == "option":
        return None if rng.random() < 0.3 else _random_value(t.args[0], rng, depth + 1)
    if k == "tuple":
        return [_random_value(a, rng, depth + 1) for a in t.args]
    if k == "record":
        return {n: _random_value(ft, rng, depth + 1) for n, ft in t.fields}
    if k == "result":
        tag = rng.choice(["ok", "err"])
        inner = t.args[0 if tag == "ok" else 1]
        return {tag: None if inner is None else _random_value(inner, rng, depth + 1)}
    if k == "enum":
        return rng.choice(t.fields)[0]
    if k == "variant":
        n, pt = rng.choice(t.fields)
        return {n: None if pt is None else _random_value(pt, rng, depth + 1)}
    raise AssertionError(k)


PROP_WIT = """package p:q@1.0.0; interface i {
 record r { a: u64, b: s32, c: list<option<string>>, d: tuple<bool, f64> }
 variant v { none, one(r), many(list<r>) }
 enum e { x, y, z }
 f: func(a: r, b: v, c: e, d: result<list<u8>, string>, e: list<s64>);
}"""


class PropertyAndFuzzTest(unittest.TestCase):
    """M24: seeded, reproducible. Properties: round-trip identity, canonical re-encode,
    decode never raises anything but CodecError, and never reads past its input."""

    SEED = 61
    CASES = 400
    MUTATIONS = 3000

    def setUp(self):
        self.types = [t for _, t in wit.parse(PROP_WIT).interfaces["i"].functions["f"].params]

    def test_round_trip_property(self):
        rng = random.Random(self.SEED)
        for _ in range(self.CASES):
            vals = [_random_value(t, rng) for t in self.types]
            b = codec.encode_args(self.types, vals)
            self.assertEqual(codec.encode_args(self.types, codec.decode_args(self.types, b)), b)

    def test_mutation_fuzz_only_raises_codec_error(self):
        rng = random.Random(self.SEED + 1)
        seeds = [codec.encode_args(self.types, [_random_value(t, rng) for t in self.types]) for _ in range(20)]
        accepted = rejected = 0
        for _ in range(self.MUTATIONS):
            b = bytearray(rng.choice(seeds))
            for _ in range(rng.randrange(1, 4)):
                op = rng.randrange(3)
                if op == 0 and b:
                    b[rng.randrange(len(b))] = rng.randrange(256)
                elif op == 1 and b:
                    del b[rng.randrange(len(b)):]
                else:
                    b.insert(rng.randrange(len(b) + 1), rng.randrange(256))
            try:
                vals = codec.decode_args(self.types, bytes(b))
            except CodecError:
                rejected += 1
                continue
            accepted += 1
            # anything accepted must be canonical: re-encoding reproduces the input exactly
            self.assertEqual(codec.encode_args(self.types, vals), bytes(b))
        self.assertGreater(rejected, 0)

    def test_header_fuzz(self):
        rng = random.Random(self.SEED + 2)
        base = codec.encode_frame({"interface": "p:q/i", "version": "1.0.0", "function": "f",
                                   "fp": "00" * 8, "deadline": 1.0, "request_id": "11" * 16,
                                   "traceparent": "00-" + "a" * 32 + "-" + "b" * 16 + "-01"}, b"\x00")
        for _ in range(self.MUTATIONS):
            b = bytearray(base)
            b[rng.randrange(len(b))] = rng.randrange(256)
            try:
                codec.decode_header(bytes(b))
            except CodecError:
                pass

    def test_list_of_zero_size_elements_round_trips(self):
        """Regression (assessor defect 9): list<empty-record> encoded but refused to decode."""
        t = wit.parse("package a:b@1.0.0; interface i { record e { } f: func(x: list<e>); }").interfaces["i"].functions["f"].params[0][1]
        b = codec.encode_args([t], [[{}, {}, {}]])
        self.assertEqual(b, b"\x03")
        self.assertEqual(codec.decode_args([t], b), [[{}, {}, {}]])

    def test_nesting_depth_limit_enforced(self):
        t = wit.T("u8")
        for _ in range(codec.MAX_DEPTH + 2):
            t = wit.T("option", (t,))
        with self.assertRaises(CodecError) as cm:
            codec.decode_args([t], b"\x01" * (codec.MAX_DEPTH + 3))
        self.assertEqual(cm.exception.code, "too-deep")

    def test_non_ascii_traceparent_dropped_not_fatal(self):
        raw = bytearray(codec.encode_frame({"interface": "a:b/i", "version": "1", "function": "f", "fp": "00" * 8,
                                            "deadline": 1.0, "request_id": "00" * 16, "traceparent": "x" * 5}, b""))
        i = raw.index(b"xxxxx")
        raw[i] = 0xC3
        self.assertEqual(codec.decode_header(bytes(raw))[0]["traceparent"], "")

    def test_hostile_length_prefix_does_not_allocate(self):
        # a 4-billion-element list claim over a 5-byte input must be refused immediately
        t = wit.T("list", (wit.T("u8"),))
        with self.assertRaises(CodecError):
            codec.decode_args([t], bytes.fromhex("ffffffff0f"))


if __name__ == "__main__":
    unittest.main()
