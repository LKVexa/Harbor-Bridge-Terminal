"""M04 WIT parser + canonical codec + frame format; M24 property/fuzz tests."""
import math
import random
import struct
import unittest

from _harness import KV, codec, wit_model


class WitParserTest(unittest.TestCase):
    def test_reference_interface(self):
        self.assertEqual(KV.qualified, "inv61:kv/store")
        self.assertEqual(KV.version, "2.1.0")
        self.assertEqual(set(KV.funcs), {"get", "put", "scan", "echo", "slow", "boom"})
        self.assertEqual(KV.funcs["get"].param_types(), ["string"])
        self.assertEqual(KV.funcs["get"].result_types(), ["option<u64>"])
        self.assertRegex(KV.digest, r"^[0-9a-f]{64}$")

    def test_digest_is_whitespace_and_comment_independent(self):
        a = wit_model.parse("package a:b@1.0.0; interface i { f: func(x: u8) -> u8; }")[0]
        b = wit_model.parse("package a:b@1.0.0;\n// c\ninterface i {\n  f : func( x : u8 ) -> u8 ;\n}\n")[0]
        self.assertEqual(a.digest, b.digest)

    def test_rejections(self):
        bad = [
            "", "interface i {}", "package a:b; interface i {}",
            "package a:b@1.0.0;",
            "package a:b@1.0.0; interface i { f: func(x: nope) ; }",
            "package a:b@1.0.0; interface i { f: func(); f: func(); }",
            "package a:b@1.0.0; interface i { resource r {} }",
            "package a:b@1.0.0; interface i { f: func(x: flags) ; }",
            "package a:b@1.0.0; interface i { record r { } }",
            "package a:b@1.0.0; interface i { enum e { a, a } }",
            "package a:b@1.0.0; interface i { f: func(x: u8, x: u8); }",
            "package a:b@1.0.0; world w {}",
            "package a:b@1.0.0; interface i {} interface i {}",
            "package a:b@1.0.0; interface I { }",
            "package a:b@1.0.0; interface i { f: func(x: " + "list<" * 40 + "u8" + ">" * 40 + "); }",
        ]
        for src in bad:
            with self.subTest(src=src[:60]), self.assertRaises(wit_model.WitError):
                wit_model.parse(src)


ENTRY = KV.resolve(("ref", "entry"))


class CodecTest(unittest.TestCase):
    def rt(self, t, v):
        b = codec.encode(t, v)
        self.assertEqual(codec.encode(t, codec.decode(t, b)), b)  # canonical
        return codec.decode(t, b)

    def test_roundtrips(self):
        cases = [
            ("bool", True), ("u8", 255), ("s8", -128), ("u64", 2**64 - 1), ("s64", -2**63),
            ("f64", 1.5), ("f32", -0.0), ("char", "é"), ("string", "héllo"),
            (("list", "u16"), [1, 2, 3]), (("option", "string"), None), (("option", "string"), "x"),
            (("result", None, "string"), ("ok", None)), (("result", "u8", "string"), ("err", "bad")),
            (("tuple", ("u8", "string")), (1, "a")), (ENTRY, {"key": "k", "value": 9, "tags": ["t"]}),
            (KV.resolve(("ref", "consistency")), "strong"),
        ]
        for t, v in cases:
            with self.subTest(t=t):
                got = self.rt(t, v)
                if isinstance(v, float) and v == 0:
                    self.assertEqual(math.copysign(1, got), math.copysign(1, v))
                else:
                    self.assertEqual(got, v)

    def test_nan_canonicalised(self):
        weird = struct.unpack("<d", b"\x01\x00\x00\x00\x00\x00\xf8\x7f")[0]
        self.assertEqual(codec.encode("f64", weird), codec.encode("f64", math.nan))

    def test_encode_rejections(self):
        for t, v in [("u8", 256), ("u8", -1), ("u8", True), ("bool", 1), ("s8", 1.0),
                     ("char", "ab"), ("char", "\ud800"), ("string", b"x"), (("list", "u8"), "ab"),
                     (("tuple", ("u8",)), (1, 2)), (ENTRY, {"key": "k"}),
                     (KV.resolve(("ref", "consistency")), "weird"), (("result", None, None), ("ok", 1)),
                     ("string", "\ud800"), ("f32", 1e300)]:
            with self.subTest(t=t, v=v), self.assertRaises(codec.CodecError):
                codec.encode(t, v)

    def test_decode_rejections(self):
        lim = codec.Limits(max_frame_bytes=1024, max_collection=10, max_string_bytes=8, max_depth=3)
        cases = [
            ("bool", b"\x02", "bool-tag"), ("u16", b"\x01", "truncated"), ("u8", b"\x01\x02", "trailing-bytes"),
            ("string", struct.pack("<I", 2) + b"\xff\xfe", "utf8"),
            ("string", struct.pack("<I", 9) + b"x" * 9, "string-limit"),
            (("list", "u8"), struct.pack("<I", 11) + b"x" * 11, "collection-limit"),
            (("list", "u32"), struct.pack("<I", 5) + b"x", "truncated"),
            (("option", "u8"), b"\x02", "option-tag"), (("result", "u8", None), b"\x05", "result-tag"),
            ("char", struct.pack("<I", 0xD800), "char"),
            (KV.resolve(("ref", "consistency")), struct.pack("<I", 7), "enum-index"),
            (("list", ("list", ("list", ("list", "u8")))), struct.pack("<I", 1) * 4 + b"\x00", "depth"),
        ]
        for t, b, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(codec.CodecError) as cm:
                    codec.decode(t, b, lim)
                self.assertEqual(cm.exception.code, code)

    def test_header_checked_before_allocation(self):
        lim = codec.Limits(max_frame_bytes=100)
        head = codec.HEADER.pack(codec.MAGIC, 2, 1, codec.KIND_REQUEST, 0, 2**32 - 1)
        with self.assertRaises(codec.CodecError) as cm:
            codec.parse_header(head, lim)
        self.assertEqual(cm.exception.code, "frame-too-large")
        for bad, code in [(b"XXXX" + head[4:], "bad-magic"),
                          (codec.HEADER.pack(codec.MAGIC, 2, 1, 99, 0, 1), "frame-kind"),
                          (codec.HEADER.pack(codec.MAGIC, 2, 1, 1, 7, 1), "flags"), (head[:5], "truncated-header")]:
            with self.subTest(code=code), self.assertRaises(codec.CodecError) as cm:
                codec.parse_header(bad, lim)
            self.assertEqual(cm.exception.code, code)

    def test_frame_roundtrip_and_length_mismatch(self):
        f = codec.pack_frame(codec.KIND_REQUEST, b"abc", 2, 1)
        self.assertEqual(codec.unpack_frame(f), (2, 1, codec.KIND_REQUEST, b"abc"))
        with self.assertRaises(codec.CodecError):
            codec.unpack_frame(f + b"x")


def _gen(rng, t, depth=0):
    if isinstance(t, str):
        return {"bool": lambda: rng.random() < .5, "u8": lambda: rng.randrange(256),
                "u16": lambda: rng.randrange(2**16), "u32": lambda: rng.randrange(2**32),
                "u64": lambda: rng.randrange(2**64), "s32": lambda: rng.randrange(-2**31, 2**31),
                "s64": lambda: rng.randrange(-2**63, 2**63), "f64": lambda: rng.uniform(-1e9, 1e9),
                "string": lambda: "".join(chr(rng.choice([rng.randrange(32, 127), rng.randrange(0xA0, 0xD7FF),
                                                          rng.randrange(0xE000, 0x10FFFF)])) for _ in range(rng.randrange(8))),
                "char": lambda: chr(rng.randrange(0xE000, 0x10FFFF))}[t]()
    k = t[0]
    if k == "list":
        return [_gen(rng, t[1], depth + 1) for _ in range(rng.randrange(4))]
    if k == "option":
        return None if rng.random() < .3 else _gen(rng, t[1], depth + 1)
    if k == "tuple":
        return tuple(_gen(rng, x, depth + 1) for x in t[1])
    if k == "record":
        return {n: _gen(rng, x, depth + 1) for n, x in t[1]}
    if k == "enum":
        return rng.choice(t[1])
    if k == "result":
        side = rng.random() < .5
        s = t[1] if side else t[2]
        return ("ok" if side else "err", None if s is None else _gen(rng, s, depth + 1))


def _rtype(rng, depth=0):
    scal = ["bool", "u8", "u16", "u32", "u64", "s32", "s64", "f64", "string", "char"]
    if depth > 3 or rng.random() < .4:
        return rng.choice(scal)
    k = rng.choice(["list", "option", "tuple", "record", "enum", "result"])
    if k in ("list", "option"):
        return (k, _rtype(rng, depth + 1))
    if k == "tuple":
        return ("tuple", tuple(_rtype(rng, depth + 1) for _ in range(rng.randrange(1, 4))))
    if k == "record":
        return ("record", tuple((f"f{i}", _rtype(rng, depth + 1)) for i in range(rng.randrange(1, 4))))
    if k == "enum":
        return ("enum", tuple(f"c{i}" for i in range(rng.randrange(1, 5))))
    return ("result", rng.choice([None, _rtype(rng, depth + 1)]), rng.choice([None, _rtype(rng, depth + 1)]))


class PropertyAndFuzzTest(unittest.TestCase):
    """M24: seeded property tests + mutation fuzzing (reproducible by seed)."""
    SEED = 61_430

    def test_property_roundtrip_is_identity_and_canonical(self):
        rng = random.Random(self.SEED)
        for i in range(1500):
            t = _rtype(rng)
            v = _gen(rng, t)
            b = codec.encode(t, v)
            d = codec.decode(t, b)
            self.assertEqual(codec.encode(t, d), b, f"iteration {i} seed {self.SEED}")

    def test_mutation_fuzz_never_raises_unexpected(self):
        rng = random.Random(self.SEED + 1)
        crashes = []
        for i in range(4000):
            t = _rtype(rng)
            b = bytearray(codec.encode(t, _gen(rng, t)))
            for _ in range(rng.randrange(1, 4)):
                op = rng.randrange(3)
                if op == 0 and b:
                    b[rng.randrange(len(b))] = rng.randrange(256)
                elif op == 1 and b:
                    del b[rng.randrange(len(b)):]
                else:
                    b += bytes(rng.randrange(256) for _ in range(rng.randrange(1, 6)))
            try:
                codec.decode(t, bytes(b))
            except codec.CodecError:
                pass
            except Exception as e:  # pragma: no cover - a finding
                crashes.append((i, type(e).__name__, bytes(b).hex()))
        self.assertEqual(crashes, [])

    def test_random_bytes_against_envelope(self):
        rng = random.Random(self.SEED + 2)
        for _ in range(3000):
            blob = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 200)))
            try:
                codec.decode(codec.REQUEST_ENVELOPE, blob)
            except codec.CodecError:
                pass

    def test_corpus_regressions(self):
        import pathlib
        corpus = pathlib.Path(__file__).with_name("corpus")
        n = 0
        for p in sorted(corpus.glob("*.bin")):
            n += 1
            try:
                codec.decode(codec.REQUEST_ENVELOPE, p.read_bytes())
            except codec.CodecError:
                pass
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
