"""Tests for the canonical interop engine (MC-001..MC-049). stdlib unittest only.

Run:  python -m unittest discover -s inv12_language_interoperability/tests -t .
Every test is deterministic; randomized tests print/record their seed.
"""
import json
import math
import os
import pathlib
import random
import subprocess
import sys
import threading
import tracemalloc
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR.parent))
_pkg = __import__(PKG_DIR.name + ".canon", fromlist=["*"])

from importlib import import_module  # noqa: E402


def M(name):
    return import_module(f"{PKG_DIR.name}.canon.{name}")


ty, layout, V, vals, errors = M("types"), M("layout"), M("validate"), M("values"), M("errors")
limits, numeric, text, res, memory = M("limits"), M("numeric"), M("text"), M("resources"), M("memory")
registry, nego, amod, obs, config = M("registry"), M("negotiation"), M("async_model"), M("observability"), M("config")
prov, trust, boundary, cjv, gens = M("provenance"), M("trust"), M("boundary"), M("cjv"), M("generators")
Some, Ok, Err, Variant = vals.Some, vals.Ok, vals.Err, vals.Variant
IE = errors.InteropError
SEED = int(os.environ.get("INV12_SEED", "20260922"))

WIT = (PKG_DIR / "fixtures/corpus/corpus.wit").read_text()
IFACE = ty.load_interface(WIT)


def T(expr):
    return ty.parse_type(expr, IFACE)


class Codes(unittest.TestCase):
    def assertCode(self, code, fn, *a, **kw):
        with self.assertRaises(IE) as cm:
            fn(*a, **kw)
        self.assertEqual(cm.exception.code, code, str(cm.exception))
        errors.validate_envelope(cm.exception.envelope())
        return cm.exception


# ------------------------------------------------------------------ MC-001
class SchemaLoaderTest(Codes):
    def test_loads_every_declaration_kind_with_locations(self):
        self.assertEqual(IFACE.package, "inv12:corpus")
        self.assertEqual(IFACE.version, "1.0.0")
        self.assertEqual(sorted(IFACE.types), ["color", "doc", "empty-flags", "perms", "point", "shape", "wide"])
        self.assertEqual(IFACE.resources, frozenset({"file"}))
        self.assertEqual(IFACE.locations["point"].line, 6)

    def test_parse_normalize_serialize_is_deterministic(self):
        a = ty.to_json(ty.load_interface(WIT))
        noisy = WIT.replace("\n", "\n\n  // noise\n").replace(", ", " ,  ")
        b = ty.to_json(ty.load_interface(noisy))
        self.assertEqual(a, b)
        self.assertEqual(json.loads(a)["digest"], IFACE.digest())

    def test_golden_digest_is_stable(self):
        vec = json.loads((PKG_DIR / "fixtures/corpus/vectors.json").read_text())
        self.assertEqual(vec["schema_digest"], IFACE.digest())

    def test_rejections(self):
        cases = {
            "interface a { record r { x: r } }": "PK_INTEROP_SCHEMA_RECURSIVE",
            "interface a { type x = y; type y = list<x>; }": "PK_INTEROP_SCHEMA_RECURSIVE",
            "interface a { type x = nope; }": "PK_INTEROP_SCHEMA_UNRESOLVED",
            "interface a { record p { x: u8 } enum p { a } }": "PK_INTEROP_SCHEMA_DUPLICATE",
            "interface a { record p { x: u8, x: u16 } }": "PK_INTEROP_SCHEMA_DUPLICATE",
            "interface a { f: func(x: own<nores>); }": "PK_INTEROP_SCHEMA_UNRESOLVED",
            "interface a { resource r; type t = r; }": "PK_INTEROP_SCHEMA_UNRESOLVED",
            "interface a { record p {} }": "PK_INTEROP_SCHEMA_LIMIT",
            "interface a { type T = u8; }": "PK_INTEROP_SCHEMA_SYNTAX",
            "interface a { type x = u8 }": "PK_INTEROP_SCHEMA_SYNTAX",
            "package a:b@1.0; interface a {}": "PK_INTEROP_SCHEMA_SYNTAX",
            "": "PK_INTEROP_SCHEMA_SYNTAX",
            "interface a {} interface a {}": "PK_INTEROP_SCHEMA_DUPLICATE",
        }
        for src, code in cases.items():
            with self.subTest(src=src):
                self.assertCode(code, ty.load, src)

    def test_depth_and_size_limits(self):
        deep = "list<" * 80 + "u8" + ">" * 80
        self.assertCode("PK_INTEROP_SCHEMA_LIMIT", ty.parse_type, deep)
        self.assertCode("PK_INTEROP_SCHEMA_LIMIT", ty.load, "interface a {" + " " * (1 << 20) + "}")

    def test_descriptor_roundtrip_and_untrusted_descriptor(self):
        for t in IFACE.types.values():
            self.assertEqual(ty.from_descriptor(ty.descriptor(t)).canonical(), t.canonical())
        self.assertCode("PK_INTEROP_SCHEMA_DUPLICATE", ty.from_descriptor,
                        {"k": "enum", "cases": ["a", "a"]})
        self.assertCode("PK_INTEROP_SCHEMA_SYNTAX", ty.from_descriptor, {"k": "record", "fields": []})
        self.assertCode("PK_INTEROP_SCHEMA_UNRESOLVED", ty.from_descriptor, {"k": "u128"})


# ------------------------------------------------------------------ MC-002/003
class TypeSetTest(Codes):
    def test_all_primitive_boundaries(self):
        for k, (lo, hi) in ty.INT_RANGES.items():
            t = ty.Prim(k)
            for v in (lo, hi):
                self.assertEqual(layout.decode(*layout.encode(v, t), t), v)
            self.assertCode("PK_INTEROP_OUT_OF_RANGE", V.validate, lo - 1, t)
            self.assertCode("PK_INTEROP_OUT_OF_RANGE", V.validate, hi + 1, t)
            self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, True, t)

    def test_tuple_enum_flags_first_class(self):
        t = T("tuple<u8, string, color>")
        v = (1, "x", "red")
        self.assertEqual(layout.decode(*layout.encode(v, t), t), v)
        self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, [1, "x", "red"], t)
        self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, (1, "x"), t)
        self.assertCode("PK_INTEROP_INVALID_DISCRIMINANT", V.validate, "purple", T("color"))
        self.assertCode("PK_INTEROP_INVALID_FLAGS", V.validate, {"fly"}, T("perms"))
        big = ty.FlagsT("flags", "b", tuple(f"g{i}" for i in range(70)))
        v = frozenset({"g0", "g33", "g69"})
        self.assertEqual(layout.size(big), 12)
        self.assertEqual(layout.decode(*layout.encode(v, big), big), v)


# ------------------------------------------------------------------ MC-004/005
class ResourceTest(Codes):
    def setUp(self):
        self.a, self.b = res.ResourceTable("a"), res.ResourceTable("b")
        self.dropped = []

    def test_own_moves_and_source_goes_stale(self):
        h = self.a.new("file", "rep1", self.dropped.append)
        h2 = self.a.transfer_own(h, self.b)
        self.assertCode("PK_INTEROP_HANDLE", self.a.rep, h)
        self.assertEqual(self.b.rep(h2), "rep1")
        self.b.drop(h2)
        self.assertEqual(self.dropped, ["rep1"])
        self.assertCode("PK_INTEROP_HANDLE", self.b.drop, h2)
        self.assertEqual(self.dropped, ["rep1"])

    def test_foreign_and_stale_handles_refused(self):
        h = self.a.new("file", 1)
        self.assertCode("PK_INTEROP_HANDLE", self.b.rep, h)
        self.a.drop(h)
        h_new = self.a.new("file", 2)
        self.assertEqual(h_new.index, h.index)
        self.assertCode("PK_INTEROP_HANDLE", self.a.rep, h)  # generation mismatch
        self.assertCode("PK_INTEROP_HANDLE", self.a.validate, h_new, "own", "socket")

    def test_borrow_scope_rules(self):
        h = self.a.new("file", "r", self.dropped.append)
        with res.CallScope() as s:
            b = self.a.lend(h, self.b, s)
            self.assertEqual(self.b.rep(b), "r")
            self.assertCode("PK_INTEROP_BORROW", self.a.drop, h)
            self.assertCode("PK_INTEROP_BORROW", self.a.transfer_own, h, self.b)
            self.assertCode("PK_INTEROP_HANDLE", self.b.transfer_own, b, self.a)
            self.b.drop(b)
        self.a.drop(h)
        self.assertEqual(self.dropped, ["r"])

    def test_leaked_borrow_is_revoked_and_fails_call(self):
        h = self.a.new("file", "r")
        with self.assertRaises(IE) as cm:
            with res.CallScope() as s:
                b = self.a.lend(h, self.b, s)
        self.assertEqual(cm.exception.code, "PK_INTEROP_BORROW")
        self.assertCode("PK_INTEROP_HANDLE", self.b.rep, b)
        self.a.drop(h)  # lend count restored

    def test_table_capacity(self):
        t = res.ResourceTable("t", max_handles=2)
        t.new("f", 1)
        t.new("f", 2)
        self.assertCode("PK_INTEROP_LIMIT", t.new, "f", 3)


# ------------------------------------------------------------------ MC-006/018
class ValidatorTest(Codes):
    def test_path_aware_errors(self):
        doc = T("doc")
        good = {"id": 1, "title": "t", "tags": ["a"], "shapes": [Variant("circle", 1.5)],
                "owner": None, "mode": frozenset(), "tint": "red", "score": Ok(1.0), "glyph": "x"}
        V.validate(good, doc)
        bad = dict(good, shapes=[Variant("empty"), Variant("rect", ({"x": 1, "y": 2}, {"x": 1, "y": 2**31}))])
        e = self.assertCode("PK_INTEROP_OUT_OF_RANGE", V.validate, bad, doc)
        self.assertEqual(e.path, ["shapes", 1, "rect", 1, "y"])
        e = self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, dict(good, extra=1), doc)
        self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, {k: v for k, v in good.items() if k != "id"}, doc)
        self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, dict(good, owner="x"), doc)

    def test_detached_copy_no_alias(self):
        src = [[1, 2], [3]]
        out = V.validate(src, T("list<list<u8>>"))
        src[0][0] = 99
        self.assertEqual(out, [[1, 2], [3]])
        self.assertIsNot(out[0], src[0])

    def test_hostile_subclasses_refused(self):
        class L(list):
            def __iter__(self):
                raise AssertionError("executed")
        self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, L([1]), T("list<u8>"))

    def test_cycles_refused(self):
        x = []
        x.append(x)
        t = ty.ListT("list", ty.Prim("u8"))
        self.assertRaises(IE, V.validate, x, ty.ListT("list", t))

    def test_limits_enforced_before_allocation(self):
        lim = limits.Limits(max_list_items=3, max_depth=4, max_string_bytes=4, max_nodes=50, max_total_bytes=8)
        self.assertCode("PK_INTEROP_LIMIT", V.validate, [1, 2, 3, 4], T("list<u8>"), limits=lim)
        self.assertCode("PK_INTEROP_LIMIT", V.validate, "hello", T("string"), limits=lim)
        self.assertCode("PK_INTEROP_LIMIT", V.validate, ["abc", "def", "ghi"], T("list<string>"), limits=lim)
        deep = T("list<list<list<list<list<u8>>>>>")
        self.assertCode("PK_INTEROP_LIMIT", V.validate, [[[[[1]]]]], deep, limits=lim)

    def test_limit_policy_only_tightens(self):
        pol = limits.LimitPolicy(interfaces={"api": {"max_list_items": 10}},
                                 types={("api", "blob"): {"max_string_bytes": 100}})
        self.assertEqual(pol.resolve("api", "blob").max_list_items, 10)
        self.assertEqual(pol.resolve("api", "blob").max_string_bytes, 100)
        self.assertEqual(pol.resolve("other").max_list_items, limits.HARD_CEILING.max_list_items)
        self.assertCode("PK_INTEROP_CONFIG", limits.LimitPolicy,
                        interfaces={"api": {"max_list_items": 10**9}})


# ------------------------------------------------------------------ MC-007/008/009
class RegistryNumericUnicodeTest(Codes):
    def test_every_language_maps_every_kind(self):
        for lang in registry.SUPPORTED_LANGUAGES:
            for k in registry.KINDS:
                self.assertIn(k, registry.REGISTRY[lang])
        self.assertEqual(registry.representation("u64", "javascript"), "bigint")
        self.assertCode("PK_INTEROP_UNREPRESENTABLE", registry.representation, "stream", "go")
        self.assertCode("PK_INTEROP_UNREPRESENTABLE", registry.check_type, T("list<u8>"), "cobol")
        with self.assertRaises(TypeError):
            registry.REGISTRY["rust"]["u8"] = "x"

    def test_registry_extension_requires_full_profile(self):
        self.assertCode("PK_INTEROP_CONFIG", registry.extend, "zig", {"u8": "u8"})
        full = {k: k for k in registry.KINDS}
        self.assertIn("zig", registry.extend("zig", full))

    def test_numeric_policy(self):
        c = numeric.convert
        self.assertEqual(c(2.0**53 - 1, source="js-number", target="u64"), 2**53 - 1)
        self.assertCode("PK_INTEROP_LOSSY_CONVERSION", c, 2.0**53 + 2, source="js-number", target="u64")
        self.assertCode("PK_INTEROP_LOSSY_CONVERSION", c, 1.5, source="js-number", target="s32")
        self.assertCode("PK_INTEROP_LOSSY_CONVERSION", c, -0.0, source="float64", target="s32")
        self.assertCode("PK_INTEROP_LOSSY_CONVERSION", c, math.nan, source="float64", target="s32")
        self.assertCode("PK_INTEROP_OUT_OF_RANGE", c, 300, source="rust-u16", target="u8")
        self.assertCode("PK_INTEROP_OUT_OF_RANGE", c, 2**40, source="go-int32", target="s64")
        self.assertEqual(c(2**24, source="python-int", target="f32"), 16777216.0)
        self.assertCode("PK_INTEROP_LOSSY_CONVERSION", c, 2**24 + 1, source="python-int", target="f32")
        self.assertCode("PK_INTEROP_LOSSY_CONVERSION", c, 0.1, source="float64", target="f32")
        self.assertCode("PK_INTEROP_TYPE_MISMATCH", c, 1, source="python-int", target="bool")
        self.assertEqual(numeric.f32_bits(math.nan), numeric.CANONICAL_NAN32)

    def test_unicode_policy(self):
        self.assertCode("PK_INTEROP_ENCODING", text.encode_utf8, "a\ud800")
        for bad in (b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe2\x82"):
            self.assertCode("PK_INTEROP_ENCODING", text.decode_utf8, bad)
        self.assertEqual(text.from_utf16([0xD83D, 0xDE00]), "\U0001F600")
        self.assertCode("PK_INTEROP_ENCODING", text.from_utf16, [0xD83D])
        self.assertCode("PK_INTEROP_ENCODING", text.from_utf16, [0xDE00, 0x41])
        self.assertEqual(text.to_utf16("\U0001F600A"), [0xD83D, 0xDE00, 0x41])
        # no normalization: NFC and NFD forms stay distinct
        nfc, nfd = "\u00e9", "e\u0301"
        self.assertNotEqual(layout.encode(nfc, T("string"))[0], layout.encode(nfd, T("string"))[0])
        self.assertCode("PK_INTEROP_ENCODING", text.char_from_u32, 0xDFFF)


# ------------------------------------------------------------------ MC-010/011/012/013
class LayoutMemoryTest(Codes):
    def test_golden_corpus_python(self):
        vec = json.loads((PKG_DIR / "fixtures/corpus/vectors.json").read_text())
        for v in vec["valid"]:
            t = ty.from_descriptor(v["descriptor"])
            with self.subTest(v["id"]):
                self.assertEqual(layout.size(t), v["size"])
                self.assertEqual(layout.alignment(t), v["align"])
                val = cjv.from_cjv(v["value"], t)
                img, root = layout.encode(val, t, validated=t.kind in ("own", "borrow"))
                self.assertEqual(img.hex(), v["image"])
                self.assertEqual(cjv.to_cjv(layout.decode(img, root, t), t), v["value"])
        for v in vec["invalid"]:
            t = ty.from_descriptor(v["descriptor"])
            with self.subTest(v["id"]):
                self.assertCode(v["error"], layout.decode, bytes.fromhex(v["image"]), v["root"], t)

    def test_known_spec_layouts(self):
        self.assertEqual((layout.size(T("option<u64>")), layout.alignment(T("option<u64>"))), (16, 8))
        self.assertEqual(layout.size(T("result<_, u8>")), 2)
        self.assertEqual(layout.size(T("result")), 1)
        self.assertEqual(layout.size(T("tuple<u8, u32, u8>")), 12)
        e = ty.EnumT("enum", "e", tuple(f"c{i}" for i in range(257)))
        self.assertEqual(layout.size(e), 2)
        self.assertEqual(layout.flatten(T("option<string>")), ["i32", "i32", "i32"])
        self.assertEqual(layout.flatten(T("result<f32, u32>")), ["i32", "i32"])
        self.assertEqual(layout.flatten(T("result<f32, u64>")), ["i32", "i64"])
        sig = layout.flatten_signature([T("string")] * 9, T("string"))
        self.assertTrue(sig["params_indirect"] and sig["results_indirect"])

    def test_bool_lift_is_spec_nonzero(self):
        self.assertIs(layout.decode(b"\x07", 0, T("bool")), True)

    def test_guest_memory_bounds_overflow_alignment(self):
        m = memory.GuestMemory(bytearray(16))
        self.assertCode("PK_INTEROP_MEMORY_BOUNDS", m.read, 10, 7)
        self.assertCode("PK_INTEROP_MEMORY_OVERFLOW", m.read, 2**32 - 1, 2)
        self.assertCode("PK_INTEROP_MEMORY_ALIGNMENT", m.load_uint, 2, 4)
        self.assertCode("PK_INTEROP_MEMORY_BOUNDS", m.read, -1, 1)
        data = m.read(0, 4)
        m.write(0, b"\x01\x02\x03\x04")
        self.assertEqual(data, b"\x00" * 4)  # copy-out, no alias

    def test_hostile_realloc_rejected(self):
        mem = memory.GuestMemory(bytearray(64))
        for bad, code in ((lambda *a: 3, "PK_INTEROP_REALLOC"), (lambda *a: 1000, "PK_INTEROP_REALLOC"),
                          (lambda *a: "x", "PK_INTEROP_REALLOC")):
            cr = memory.CheckedRealloc(mem, bad)
            self.assertCode(code, cr.alloc, 4, 8)
        same = memory.CheckedRealloc(mem, lambda *a: 8)
        same.alloc(4, 8)
        self.assertCode("PK_INTEROP_REALLOC", same.alloc, 4, 8)  # overlapping

    def test_lifecycle_exactly_once_and_rollback(self):
        mem = memory.GuestMemory()
        cr = memory.CheckedRealloc(mem, memory.Allocator(mem, base=8))
        calls = []
        lc = memory.CallLifecycle(cr, post_return=lambda: calls.append(1))
        lc.begin()
        lc.alloc(4, 16)
        lc.alloc(1, 3)
        lc.called()
        lc.returned()
        lc.post_return()
        self.assertEqual((calls, cr.leaked(), cr.frees), ([1], 0, 2))
        self.assertCode("PK_INTEROP_LIFECYCLE", lc.post_return)
        lc2 = memory.CallLifecycle(cr)
        lc2.begin()
        lc2.alloc(8, 8)
        lc2.rollback()
        self.assertEqual(cr.leaked(), 0)
        self.assertCode("PK_INTEROP_LIFECYCLE", lc2.alloc, 1, 1)
        self.assertCode("PK_INTEROP_LIFECYCLE", cr.free, 999)

    def test_variant_option_result_wire(self):
        t = T("option<option<u32>>")
        for v in (None, Some(None), Some(Some(0))):
            self.assertEqual(layout.decode(*layout.encode(v, t), t), v)
        self.assertCode("PK_INTEROP_INVALID_DISCRIMINANT", layout.decode, b"\x02" + b"\x00" * 11, 0, t)
        r = T("result<string, u8>")
        self.assertEqual(layout.decode(*layout.encode(Err(3), r), r), Err(3))
        self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, Ok(None), r)
        self.assertCode("PK_INTEROP_TYPE_MISMATCH", V.validate, Variant("empty", 1), T("shape"))


# ------------------------------------------------------------------ MC-014/040
class ErrorEnvelopeTest(Codes):
    def test_envelope_is_redacted_and_bounded(self):
        e = IE("x" * 1000 + "\x1b[31m", code="PK_INTEROP_LIMIT", path=["a"] * 100)
        env = e.envelope()
        errors.validate_envelope(env)
        self.assertLessEqual(len(env["detail"]), errors.MAX_DETAIL_CHARS)
        self.assertNotIn("\x1b", env["detail"])
        self.assertEqual(len(env["path"]), errors.MAX_PATH_SEGMENTS)
        self.assertTrue(env["retryable"])

    def test_payload_values_never_in_diagnostics(self):
        marker = "SENSITIVE-PAYLOAD-123"
        for fn in (lambda: V.validate({"x": 1, "y": marker}, T("point")),
                   lambda: V.validate(marker, T("color")),
                   lambda: V.validate({"x": 1, "y": 2, marker: 3}, T("point"))):
            with self.assertRaises(IE) as cm:
                fn()
            self.assertNotIn(marker, json.dumps(cm.exception.envelope()))

    def test_unregistered_code_refused(self):
        with self.assertRaises(KeyError):
            IE("x", code="MADE_UP")
        self.assertRaises(ValueError, errors.validate_envelope, {"schema": "x"})


# ------------------------------------------------------------------ MC-015/016
class NegotiationEvolutionTest(Codes):
    A = {"canonical_abi": ["1"], "mapping_profile": ["inv12-mapping@2.0.0"],
         "interfaces": {"x:y/api": ["1.0.0", "1.2.0", "2.0.0"]}}
    B = {"canonical_abi": ["1"], "mapping_profile": ["inv12-mapping@2.0.0", "inv12-mapping@1.0.0"],
         "interfaces": {"x:y/api": ["1.0.0", "1.2.0"]}}

    def test_highest_common_and_transcript(self):
        r = nego.negotiate(self.A, self.B)
        self.assertEqual(r["interfaces"]["x:y/api"], "1.2.0")
        self.assertEqual(r["mapping_profile"], "inv12-mapping@2.0.0")
        r2 = nego.negotiate(self.A, dict(self.B, interfaces={"x:y/api": ["1.0.0"]}))
        self.assertNotEqual(r["transcript"], r2["transcript"])

    def test_fail_closed(self):
        self.assertCode("PK_INTEROP_VERSION", nego.negotiate, self.A, dict(self.B, canonical_abi=["2"]))
        self.assertCode("PK_INTEROP_VERSION", nego.negotiate, self.A,
                        dict(self.B, interfaces={"x:y/api": ["3.0.0"]}))
        self.assertCode("PK_INTEROP_VERSION", nego.negotiate, self.A, self.B,
                        {"min_interface": {"x:y/api": "2.0.0"}})
        self.assertCode("PK_INTEROP_VERSION", nego.negotiate, self.A, self.B,
                        {"required_interfaces": ["x:y/other"]})
        self.assertCode("PK_INTEROP_VERSION", nego.negotiate, self.A, dict(self.B, interfaces={"a": ["1"]}))

    def test_evolution_classification(self):
        old = ty.load_interface("package p:q@1.0.0; interface i { enum c { a, b } record r { x: u8 } f: func(x: u8); }")
        add = ty.load_interface("package p:q@1.1.0; interface i { enum c { a, b } record r { x: u8 } f: func(x: u8); g: func(); }")
        case = ty.load_interface("package p:q@2.0.0; interface i { enum c { a, b, z } record r { x: u8 } f: func(x: u8); }")
        brk = ty.load_interface("package p:q@1.0.1; interface i { enum c { a, b } record r { x: u16 } f: func(x: u8); }")
        self.assertEqual(nego.check_version_bump(old, add)["required"], "minor")
        self.assertEqual({c["class"] for c in nego.compare(old, case)}, {"adapter"})
        self.assertEqual(nego.check_version_bump(old, case)["required"], "major")
        self.assertCode("PK_INTEROP_INCOMPATIBLE", nego.check_version_bump, old, brk)
        self.assertEqual(nego.compare(old, old), [])


# ------------------------------------------------------------------ MC-017
class AsyncTest(Codes):
    def test_future_lifecycle(self):
        f = amod.Future(T("u8"))
        self.assertCode("PK_INTEROP_OUT_OF_RANGE", f.resolve, 999)
        f.resolve(7)
        self.assertCode("PK_INTEROP_ASYNC", f.resolve, 8)
        self.assertEqual(f.read(), 7)
        self.assertCode("PK_INTEROP_ASYNC", f.read)
        g = amod.Future(T("u8"))
        g.cancel()
        self.assertCode("PK_INTEROP_CANCELLED", g.read)
        h = amod.Future(T("u8"))
        self.assertCode("PK_INTEROP_LIMIT", h.read, 0.01)

    def test_stream_backpressure_fifo_cancel(self):
        s = amod.Stream(T("list<u8>"), window=2)
        src = [1]
        s.write(src)
        src.append(2)
        s.write([3])
        self.assertCode("PK_INTEROP_LIMIT", s.write, [4], 0.01)
        self.assertEqual(s.read(), [1])
        s.write([5])
        s.cancel()
        self.assertEqual(s.discarded, 2)
        self.assertCode("PK_INTEROP_CANCELLED", s.read)
        self.assertCode("PK_INTEROP_LIMIT", amod.Stream, None, window=10**9)

    def test_stream_threaded_exactly_once(self):
        s = amod.Stream(T("u32"), window=8)
        got = []

        def consume():
            while True:
                try:
                    got.append(s.read(5))
                except StopIteration:
                    return
        th = threading.Thread(target=consume)
        th.start()
        for i in range(2000):
            s.write(i, 5)
        s.close()
        th.join(10)
        self.assertEqual(got, list(range(2000)))


# ------------------------------------------------------------------ MC-037..042
class ObservabilityTest(Codes):
    def test_metrics_bounded_cardinality(self):
        m = obs.Metrics()
        for i in range(1000):
            m.inc("mapping_refusals", language=f"lang{i}", code="PK_INTEROP_UNREPRESENTABLE")
        self.assertEqual(m.cardinality(), 1)
        self.assertEqual(m.value("mapping_refusals", language="other", code="PK_INTEROP_UNREPRESENTABLE"), 1000)
        self.assertRaises(KeyError, m.inc, "made_up")
        self.assertRaises(KeyError, m.inc, "boundary_calls", tenant="t1")
        m.observe_us("boundary_latency", 1.5, source_language="go", target_language="rust")
        self.assertIn('le="2"', m.exposition())

    def test_trace_attributes_allow_list(self):
        tr = obs.Tracer()
        with self.assertRaises(KeyError):
            with tr.span("x", payload="secret"):
                pass
        with self.assertRaises(IE):
            with tr.span("call", interface="i"):
                raise IE("boom", code="PK_INTEROP_LIMIT")
        self.assertEqual(tr.export()[-1]["attributes"]["code"], "PK_INTEROP_LIMIT")

    def test_audit_chain_detects_tampering(self):
        log = obs.AuditLog(b"k" * 32)
        for i in range(5):
            log.emit("config_activated", "op", revision=i)
        self.assertTrue(log.verify())
        import copy
        for mutate in (lambda r: r[2]["fields"].__setitem__("revision", "9"),
                       lambda r: r.pop(1), lambda r: r.insert(1, dict(r[1])),
                       lambda r: r.reverse()):
            recs = copy.deepcopy(log.records)
            mutate(recs)
            self.assertFalse(log.verify(recs))
        self.assertFalse(obs.AuditLog(b"x" * 32).verify(log.records))

    def test_health_and_capacity(self):
        h = obs.Health()
        self.assertEqual(h.status()["state"], "HEALTHY")
        h.set("quota_exhausted", True)
        self.assertEqual(h.status()["state"], "DEGRADED")
        h.set("mapping_profile_missing", True)
        self.assertFalse(h.status()["ready"])
        cap = obs.CapacityController(max_calls=4, max_bytes=100, max_resources=10, tenants=2)
        with cap.admit("t1"), cap.admit("t1"):
            self.assertCode("PK_INTEROP_LIMIT", cap.admit("t1").__enter__)
            with cap.admit("t2"):
                pass
        self.assertEqual(cap.total["calls"], 0)


# ------------------------------------------------------------------ MC-043..049
class ConfigTrustTest(Codes):
    KEYS = {"alice": b"a" * 32, "bob": b"b" * 32, "carol": b"c" * 32}

    def mgr(self, audit=None):
        return config.ConfigManager(self.KEYS, quorum=2, audit=audit)

    def test_defaults_are_secure(self):
        d = config.default_config()
        self.assertFalse(any(d["features"].values()))
        self.assertEqual(config.validate_config(d), d)

    def test_activation_requires_quorum_and_is_atomic(self):
        audit = obs.AuditLog(b"k" * 32)
        m = self.mgr(audit)
        doc = config.default_config()
        doc["revision"] = 2
        doc["languages"] = ["rust", "go"]
        self.assertCode("PK_INTEROP_PROVENANCE", m.activate, doc, [config.approve(doc, "alice", self.KEYS["alice"])])
        forged = [config.approve(doc, "alice", self.KEYS["alice"]), config.approve(doc, "bob", b"z" * 32)]
        self.assertCode("PK_INTEROP_PROVENANCE", m.activate, doc, forged)
        good = [config.approve(doc, a, self.KEYS[a]) for a in ("alice", "bob")]
        snap = m.activate(doc, good)
        self.assertEqual(snap.languages, frozenset({"rust", "go"}))
        self.assertCode("PK_INTEROP_CONFIG", m.activate, doc, good)          # replay
        self.assertEqual(m.rollback().revision, 1)
        self.assertEqual([p["revision"] for p in m.provenance()], [1, 2])
        self.assertTrue(audit.verify())
        self.assertEqual([r["event"] for r in audit.records][-2:], ["config_activated", "config_rolled_back"])

    def test_invalid_configs_rejected(self):
        base = config.default_config()
        muts = [lambda d: d.update(extra=1), lambda d: d["limits"].update(max_depth=10**6),
                lambda d: d["features"].update(zero_copy=True), lambda d: d.update(languages=["cobol"]),
                lambda d: d["mapping_profile"].update(digest="sha256:" + "0" * 64),
                lambda d: d.update(revision=0), lambda d: d["limits"].update(bogus=1)]
        import copy
        for mu in muts:
            d = copy.deepcopy(base)
            mu(d)
            self.assertCode("PK_INTEROP_CONFIG", config.validate_config, d)

    def test_capability_gate_and_outage_policy(self):
        now = [1000]
        health = obs.Health()
        gate = trust.CapabilityGate({"k1": b"s" * 32}, lambda: now[0], grace_s=60, health=health)
        tok = trust.mint("comp-a", ["interop.call:api"], 2000, "k1", b"s" * 32)
        self.assertEqual(gate.authorize(tok, "interop.call:api"), "comp-a")
        self.assertCode("PK_INTEROP_UNAUTHORIZED", gate.authorize, tok, "interop.call:other")
        self.assertCode("PK_INTEROP_UNAUTHORIZED", gate.authorize, dict(tok, caps=["*"]), "*")
        self.assertCode("PK_INTEROP_UNAUTHORIZED", gate.authorize, dict(tok, kid="k9"), "interop.call:api")
        gate.set_trust_available(False)
        self.assertEqual(gate.authorize(tok, "interop.call:api"), "comp-a")    # degraded grace
        self.assertCode("PK_INTEROP_TRUST_UNAVAILABLE", gate.authorize, tok, "interop.call:api", privileged=True)
        fresh = trust.mint("comp-b", ["interop.call:api"], 2000, "k1", b"s" * 32)
        self.assertCode("PK_INTEROP_TRUST_UNAVAILABLE", gate.authorize, fresh, "interop.call:api")
        now[0] = 1100
        self.assertCode("PK_INTEROP_TRUST_UNAVAILABLE", gate.authorize, tok, "interop.call:api")
        gate.set_trust_available(True)

        def broken():
            raise OSError("ntp down")
        g2 = trust.CapabilityGate({"k1": b"s" * 32}, broken)
        self.assertCode("PK_INTEROP_TRUST_UNAVAILABLE", g2.authorize, tok, "interop.call:api")

    def test_key_rotation_and_revocation(self):
        now = [1000]
        gate = trust.CapabilityGate({"k1": b"s" * 32}, lambda: now[0])
        old = trust.mint("comp-a", ["c"], 2000, "k1", b"s" * 32)
        gate.authorize(old, "c")
        gate.rotate("k2", b"t" * 32, retire="k1")
        self.assertCode("PK_INTEROP_UNAUTHORIZED", gate.authorize, old, "c")
        new = trust.mint("comp-a", ["c"], 2000, "k2", b"t" * 32)
        self.assertEqual(gate.authorize(new, "c"), "comp-a")
        gate.revoke_subject("comp-a")
        self.assertCode("PK_INTEROP_UNAUTHORIZED", gate.authorize, new, "c")
        m = self.mgr()
        doc = config.default_config()
        doc["revision"] = 2
        stale = [config.approve(doc, a, self.KEYS[a]) for a in ("alice", "bob")]
        m.rotate_approver_key("bob", b"B" * 32)
        self.assertCode("PK_INTEROP_PROVENANCE", m.activate, doc, stale)
        m.revoke_approver("carol")
        self.assertCode("PK_INTEROP_CONFIG", m.revoke_approver, "alice")
        m.activate(doc, [config.approve(doc, "alice", self.KEYS["alice"]), config.approve(doc, "bob", b"B" * 32)])

    def test_artifact_provenance(self):
        f = PKG_DIR / "fixtures/corpus/corpus.wit"
        d = prov.sha256_file(f)
        pol = prov.ArtifactPolicy({"corpus": {"version": "1.0.0", "digest": d}})
        self.assertEqual(pol.verify("corpus", "1.0.0", f), d)
        self.assertCode("PK_INTEROP_PROVENANCE", pol.verify, "corpus", "1.0.1", f)
        self.assertCode("PK_INTEROP_PROVENANCE", pol.verify, "other", "1.0.0", f)
        self.assertCode("PK_INTEROP_PROVENANCE", pol.verify, "corpus", "1.0.0", PKG_DIR / "VERSION")
        s = prov.sbom(PKG_DIR, "4.3.0")
        self.assertEqual(s["bomFormat"], "CycloneDX")
        self.assertTrue(any(c["name"] == "canon/layout.py" for c in s["components"]))


# ------------------------------------------------------------------ integration
class BoundaryIntegrationTest(Codes):
    API = """package demo:files@1.0.0;
    interface api {
      resource file;
      record entry { name: string, size: u64, tags: list<string> }
      open: func(path: string) -> own<file>;
      stat: func(f: borrow<file>) -> entry;
      close: func(f: own<file>);
      echo: func(e: list<entry>) -> list<entry>;
      keep: func(f: borrow<file>);
    }"""

    def setUp(self):
        self.iface = ty.load_interface(self.API)
        self.cfg = config.ConfigManager({"a": b"a" * 32}, quorum=1)
        self.metrics, self.tracer = obs.Metrics(), obs.Tracer()
        self.closed = []
        self.stash = []

        def open_(inst, path):
            return inst.table.new("file", {"path": path}, lambda rep: self.closed.append(rep["path"]))

        def stat(inst, f):
            rep = inst.table.rep(f)
            inst.table.drop(f)
            return {"name": rep["path"], "size": 42, "tags": ["x"]}

        def close(inst, f):
            inst.table.drop(f)

        def keep(inst, f):
            self.stash.append(f)   # misbehaving callee: keeps the borrow

        self.server = boundary.Instance("server", "rust", {"open": open_, "stat": stat, "close": close,
                                                           "echo": lambda inst, e: e, "keep": keep})
        self.client = boundary.Instance("client", "go")
        self.b = boundary.Boundary(self.iface, self.cfg, metrics=self.metrics, tracer=self.tracer)

    def test_full_resource_lifecycle_through_real_memory(self):
        h = self.b.call(self.client, self.server, "open", ("/data/a",))
        self.assertEqual(h.kind, "own")
        self.assertEqual(self.client.table.live(), 1)
        self.assertEqual(self.server.table.live(), 0)
        e = self.b.call(self.client, self.server, "stat", (h,))
        self.assertEqual(e, {"name": "/data/a", "size": 42, "tags": ["x"]})
        self.b.call(self.client, self.server, "close", (h,))
        self.assertEqual(self.closed, ["/data/a"])
        self.assertEqual((self.client.table.live(), self.server.table.live()), (0, 0))
        self.assertCode("PK_INTEROP_HANDLE", self.b.call, self.client, self.server, "close", (h,))
        self.assertEqual(self.server.realloc.leaked(), 0)
        self.assertEqual(self.client.realloc.leaked(), 0)
        self.assertEqual(self.metrics.value("boundary_calls", source_language="go", target_language="rust"), 4)

    def test_leaked_borrow_fails_call(self):
        h = self.b.call(self.client, self.server, "open", ("/x",))
        self.assertCode("PK_INTEROP_BORROW", self.b.call, self.client, self.server, "keep", (h,))
        self.assertCode("PK_INTEROP_HANDLE", self.server.table.rep, self.stash[0])
        self.b.call(self.client, self.server, "close", (h,))

    def test_invalid_args_leave_no_trace(self):
        big = [{"name": "n", "size": 2**64, "tags": []}]
        e = self.assertCode("PK_INTEROP_OUT_OF_RANGE", self.b.call, self.client, self.server, "echo", (big,))
        self.assertEqual(e.path, ["e", 0, "size"])
        self.assertEqual(e.envelope()["source_language"], "go")
        self.assertEqual(self.server.realloc.allocations, 0)

    def test_disabled_language_refused(self):
        doc = config.default_config()
        doc.update(revision=2, languages=["rust"])
        self.cfg.activate(doc, [config.approve(doc, "a", b"a" * 32)])
        self.assertCode("PK_INTEROP_UNREPRESENTABLE", self.b.call, self.client, self.server, "open", ("/x",))

    def test_no_alias_across_boundary(self):
        arg = [{"name": "a", "size": 1, "tags": ["t"]}]
        out = self.b.call(self.client, self.server, "echo", (arg,))
        arg[0]["tags"][0] = "mutated"
        self.assertEqual(out[0]["tags"], ["t"])


# ------------------------------------------------------------------ MC-027 properties
class PropertyTest(unittest.TestCase):
    def test_roundtrip_and_detachment_properties(self):
        rng = random.Random(SEED)
        for i in range(400):
            t = gens.gen_type(rng, 3)
            v = gens.gen_value(rng, t)
            with self.subTest(seed=SEED, case=i, type=t.canonical()[:80]):
                canon_v = V.validate(v, t)
                img, root = layout.encode(canon_v, t, validated=True)
                back = layout.decode(img, root, t)
                self.assertEqual(cjv.to_cjv(back, t), cjv.to_cjv(v, t))
                img2, _ = layout.encode(back, t)
                self.assertEqual(img, img2)                      # lower(lift(lower(v))) == lower(v)
                self.assertEqual(len(img) >= layout.size(t), True)


# ------------------------------------------------------------------ MC-030 malicious memory
class MaliciousMemoryTest(Codes):
    def test_mutated_images_only_raise_structured_errors(self):
        rng = random.Random(SEED + 1)
        crashes = 0
        for _ in range(1500):
            t = gens.gen_type(rng, 3)
            img, root = layout.encode(gens.gen_value(rng, t), t)
            bad = gens.mutate(rng, img)
            try:
                layout.decode(bad, root, t)
            except IE:
                pass
            except Exception:  # noqa: BLE001
                crashes += 1
        self.assertEqual(crashes, 0)

    def test_specific_attacks(self):
        mem = memory.GuestMemory(bytearray(64))
        self.assertCode("PK_INTEROP_MEMORY_OVERFLOW", memory.checked_mul, 2**31, 4)
        self.assertCode("PK_INTEROP_MEMORY_OVERFLOW", memory.checked_add, 2**32 - 4, 8)
        big = (0).to_bytes(4, "little") + (0xFFFFFFFF).to_bytes(4, "little")
        self.assertCode("PK_INTEROP_MEMORY_OVERFLOW", layout.decode, big, 0, T("list<u32>"))
        self.assertCode("PK_INTEROP_MEMORY_BOUNDS", layout.decode, big, 0, T("list<u8>"))
        self.assertCode("PK_INTEROP_MEMORY_BOUNDS", mem.write, 60, b"\x00" * 8)
        self.assertCode("PK_INTEROP_HANDLE", layout.decode, b"\x00" * 4, 0, T("own<file>"))


# ------------------------------------------------------------------ MC-031/032 stress + leaks
class ConcurrencyLeakTest(Codes):
    def test_parallel_transfers_lends_and_drops(self):
        tables = [res.ResourceTable(f"t{i}") for i in range(4)]
        drops = []
        lock = threading.Lock()
        handles = [tables[0].new("f", i, lambda r: (lock.acquire(), drops.append(r), lock.release()))
                   for i in range(400)]
        errs = []
        box = {i: (0, h) for i, h in enumerate(handles)}
        box_lock = threading.Lock()

        def worker(seed):
            rng = random.Random(seed)
            for _ in range(1500):
                i = rng.randrange(400)
                with box_lock:
                    ti, h = box[i]
                dst = tables[rng.randrange(4)]
                try:
                    if rng.random() < .5 and dst is not tables[ti]:
                        nh = tables[ti].transfer_own(h, dst)
                        with box_lock:
                            if box[i][1] is h:
                                box[i] = (tables.index(dst), nh)
                            else:
                                errs.append("lost update")
                    else:
                        with res.CallScope() as s:
                            b = tables[ti].lend(h, dst, s) if dst is not tables[ti] else None
                            if b is not None:
                                dst.drop(b)
                except IE as e:
                    if e.code not in ("PK_INTEROP_HANDLE", "PK_INTEROP_BORROW"):
                        errs.append(e.code)
        ths = [threading.Thread(target=worker, args=(SEED + k,)) for k in range(8)]
        [t.start() for t in ths]
        [t.join(60) for t in ths]
        self.assertEqual(errs, [])
        self.assertEqual(sum(t.live() for t in tables), 400)
        for ti, h in box.values():
            tables[ti].drop(h)
        self.assertEqual(sorted(drops), list(range(400)))       # each destructor exactly once
        self.assertEqual(sum(t.live() for t in tables), 0)

    def test_boundary_calls_under_contention(self):
        it = BoundaryIntegrationTest("test_no_alias_across_boundary")
        it.setUp()
        errs = []

        def run(n):
            client = boundary.Instance(f"c{n}", "go")
            for k in range(150):
                try:
                    h = it.b.call(client, it.server, "open", (f"/f{n}/{k}",))
                    it.b.call(client, it.server, "stat", (h,))
                    it.b.call(client, it.server, "close", (h,))
                    if client.table.live():
                        errs.append("leak")
                except Exception as e:  # noqa: BLE001
                    errs.append(repr(e))
        ths = [threading.Thread(target=run, args=(n,)) for n in range(6)]
        old = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)          # force fine-grained preemption (regression for B-008)
        try:
            [t.start() for t in ths]
            [t.join(120) for t in ths]
        finally:
            sys.setswitchinterval(old)
        self.assertEqual(errs, [])
        self.assertEqual(len(it.closed), 900)
        self.assertEqual(it.server.table.live(), 0)

    @unittest.skipIf(os.environ.get("INV12_COVERAGE"), "tracer allocations distort tracemalloc")
    def test_no_growth_over_long_run(self):
        it = BoundaryIntegrationTest("test_no_alias_across_boundary")
        it.setUp()
        payload = [{"name": "n" * 64, "size": 7, "tags": ["a", "b"]}] * 20

        def cycle(n):
            for _ in range(n):
                it.b.call(it.client, it.server, "echo", (payload,))
        cycle(200)
        tracemalloc.start()
        s1 = tracemalloc.take_snapshot()
        cycle(1500)
        s2 = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(st.size_diff for st in s2.compare_to(s1, "filename"))
        self.assertLess(growth, 1_500_000, f"memory grew {growth} bytes")  # trace buffer is bounded
        self.assertEqual((it.server.realloc.leaked(), it.client.realloc.leaked()), (0, 0))
        self.assertLess(len(it.server.memory), 64 * 1024)                  # arena reclaimed


class OptimizedModeTest(unittest.TestCase):
    def test_semantics_identical_under_python_O(self):
        code = ("import sys;sys.path.insert(0,%r);import %s.canon as c;"
                "from %s.canon.validate import validate as VV;from %s.canon import types as T, errors as E\n"
                "try:\n VV(300, T.Prim('u8'))\nexcept E.InteropError as e:\n print(e.code)\n"
                "print(c.encode([1,2], T.parse_type('list<u8>'))[0].hex())") % (
            str(PKG_DIR.parent), PKG_DIR.name, PKG_DIR.name, PKG_DIR.name)
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.split(), ["PK_INTEROP_OUT_OF_RANGE", "08000000020000000102"])



class DocsExamplesTest(unittest.TestCase):
    """MC-*-53: documented configuration examples are validated in CI."""

    def test_config_examples_validate(self):
        ex = sorted((PKG_DIR / "docs/examples").glob("config.*.json"))
        self.assertGreaterEqual(len(ex), 2)
        for p in ex:
            with self.subTest(p.name):
                config.validate_config(json.loads(p.read_text()))

    def test_docs_reference_existing_files(self):
        import re
        for md in (PKG_DIR / "docs").glob("*.md"):
            for ref in re.findall(r"`((?:canon|tools|fixtures|ci|docs)/[A-Za-z0-9_./-]+\.(?:py|mjs|json|go|rs|wit|md|yml))`", md.read_text()):
                with self.subTest(doc=md.name, ref=ref):
                    self.assertTrue((PKG_DIR / ref).exists(), ref)


if __name__ == "__main__":
    unittest.main()
