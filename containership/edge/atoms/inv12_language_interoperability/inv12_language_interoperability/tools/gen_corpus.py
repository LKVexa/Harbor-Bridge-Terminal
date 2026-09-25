"""MC-026 golden canonical test-vector corpus generator (deterministic).

Writes fixtures/corpus/vectors.json.  Re-running must reproduce the file
byte-for-byte (checked in CI by tools/ci.py --check-corpus).
"""
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from canon import types as ty, layout, cjv  # noqa: E402
from canon.values import Err, Ok, Some, Variant  # noqa: E402

CORPUS_VERSION = "1.0.0"
WIT = (ROOT / "fixtures/corpus/corpus.wit").read_text()
IFACE = ty.load_interface(WIT)


def T(expr):
    return ty.parse_type(expr, IFACE)


VALID = [
    ("bool-false", "bool", False), ("bool-true", "bool", True),
    ("s8-min", "s8", -128), ("s8-max", "s8", 127), ("u8-max", "u8", 255),
    ("s16-min", "s16", -32768), ("u16-max", "u16", 65535),
    ("s32-min", "s32", -2**31), ("u32-max", "u32", 2**32 - 1),
    ("s64-min", "s64", -2**63), ("s64-max", "s64", 2**63 - 1),
    ("u64-max", "u64", 2**64 - 1), ("u64-2p53p1", "u64", 2**53 + 1),
    ("f32-1.5", "f32", 1.5), ("f32-negzero", "f32", -0.0), ("f32-inf", "f32", math.inf),
    ("f32-nan", "f32", math.nan), ("f64-pi", "f64", math.pi), ("f64-subnormal", "f64", 5e-324),
    ("f64-neginf", "f64", -math.inf),
    ("char-a", "char", "A"), ("char-e-acute", "char", "é"), ("char-emoji", "char", "\U0001F600"),
    ("char-ffff", "char", "￿"),
    ("string-empty", "string", ""), ("string-utf8", "string", "héllo 世界"),
    ("string-astral", "string", "\U0001F680\U0001F30D"), ("string-nul", "string", "a\x00b"),
    ("list-u8-empty", "list<u8>", []), ("list-u8", "list<u8>", [0, 1, 255]),
    ("list-string", "list<string>", ["", "x", "yz"]),
    ("list-list-u16", "list<list<u16>>", [[1, 2], [], [65535]]),
    ("tuple-mixed", "tuple<u8, u64, string>", (7, 2**64 - 1, "t")),
    ("record-point", "point", {"x": -1, "y": 2}),
    ("variant-circle", "shape", Variant("circle", 2.5)),
    ("variant-rect", "shape", Variant("rect", ({"x": 0, "y": 0}, {"x": 3, "y": -4}))),
    ("variant-empty", "shape", Variant("empty")),
    ("enum-blue", "color", "blue"),
    ("flags-none", "perms", frozenset()), ("flags-rw", "perms", frozenset({"read", "write"})),
    ("flags-wide", "wide", frozenset({"w0", "w31", "w32", "w39"})),
    ("option-none", "option<option<u32>>", None),
    ("option-some-none", "option<option<u32>>", Some(None)),
    ("option-some-some", "option<option<u32>>", Some(Some(9))),
    ("result-ok", "result<u64, string>", Ok(18446744073709551615)),
    ("result-err", "result<u64, string>", Err("boom")),
    ("result-unit-ok", "result", Ok()), ("result-unit-err", "result", Err()),
    ("own-handle", "own<file>", 1),
    ("record-doc", "doc", {
        "id": 2**63, "title": "Résumé", "tags": ["a", "\U0001F600"],
        "shapes": [Variant("empty"), Variant("circle", 0.25)], "owner": Some("dpr"),
        "mode": frozenset({"exec"}), "tint": "green", "score": Err("n/a"), "glyph": "λ"}),
]


def image(parts):
    return bytes(parts)


def u32(v):
    return list(v.to_bytes(4, "little"))


# Invalid images: (id, type, image bytes, root, expected error code)
INVALID = [
    ("bad-variant-disc", "shape", image([3] + [0] * 19), 0, "PK_INTEROP_INVALID_DISCRIMINANT"),
    ("bad-enum-disc", "color", image([7]), 0, "PK_INTEROP_INVALID_DISCRIMINANT"),
    ("bad-option-disc", "option<u32>", image([2, 0, 0, 0, 0, 0, 0, 0]), 0, "PK_INTEROP_INVALID_DISCRIMINANT"),
    ("bad-utf8-ff", "string", image(u32(8) + u32(1) + [0xFF]), 0, "PK_INTEROP_ENCODING"),
    ("bad-utf8-surrogate", "string", image(u32(8) + u32(3) + [0xED, 0xA0, 0x80]), 0, "PK_INTEROP_ENCODING"),
    ("bad-utf8-overlong", "string", image(u32(8) + u32(2) + [0xC0, 0xAF]), 0, "PK_INTEROP_ENCODING"),
    ("bad-char-surrogate", "char", image(u32(0xD800)), 0, "PK_INTEROP_ENCODING"),
    ("bad-char-too-big", "char", image(u32(0x110000)), 0, "PK_INTEROP_ENCODING"),
    ("bad-string-oob", "string", image(u32(8) + u32(100)), 0, "PK_INTEROP_MEMORY_BOUNDS"),
    ("bad-list-oob", "list<u8>", image(u32(4000) + u32(1)), 0, "PK_INTEROP_MEMORY_BOUNDS"),
    ("bad-list-len-overflow", "list<u64>", image(u32(8) + u32(0x20000000)), 0, "PK_INTEROP_MEMORY_OVERFLOW"),
    ("bad-list-misaligned", "list<u32>", image(u32(9) + u32(1) + [0] * 8), 0, "PK_INTEROP_MEMORY_ALIGNMENT"),
    ("bad-flags-bits", "perms", image([0x08]), 0, "PK_INTEROP_INVALID_FLAGS"),
    ("bad-handle-zero", "own<file>", image(u32(0)), 0, "PK_INTEROP_HANDLE"),
    ("bad-root-oob", "u64", image([0, 0, 0, 0]), 0, "PK_INTEROP_MEMORY_BOUNDS"),
    ("bad-root-misaligned", "u32", image([0] * 8), 2, "PK_INTEROP_MEMORY_ALIGNMENT"),
    ("bad-zero-size-list-bomb", "list<empty-flags>", image(u32(8) + u32(0xFFFFFFFF)), 0, "PK_INTEROP_LIMIT"),
]


def build():
    vectors = []
    for vid, expr, value in VALID:
        t = T(expr)
        img, root = layout.encode(value, t, validated=(t.kind in ("own", "borrow")))
        back = layout.decode(img, root, t)
        vectors.append({"id": vid, "type": expr, "descriptor": ty.descriptor(t),
                        "type_hash": ty.type_hash(t), "value": cjv.to_cjv(value, t),
                        "image": img.hex(), "root": root, "size": layout.size(t),
                        "align": layout.alignment(t)})
        assert cjv.to_cjv(back, t) == vectors[-1]["value"], vid
    failures = []
    for vid, expr, img, root, code in INVALID:
        t = T(expr)
        try:
            layout.decode(img, root, t)
        except Exception as e:  # noqa: BLE001
            got = getattr(e, "code", type(e).__name__)
        else:
            got = None
        if got != code:
            raise SystemExit(f"{vid}: python reference produced {got}, corpus expects {code}")
        failures.append({"id": vid, "type": expr, "descriptor": ty.descriptor(t),
                         "image": img.hex(), "root": root, "error": code})
    return {"corpus": "inv12-golden", "version": CORPUS_VERSION,
            "schema_digest": IFACE.digest(), "valid": vectors, "invalid": failures}


def render():
    return json.dumps(build(), indent=1, sort_keys=True, ensure_ascii=True) + "\n"


if __name__ == "__main__":
    out = ROOT / "fixtures/corpus/vectors.json"
    text = render()
    if "--check" in sys.argv:
        ok = out.exists() and out.read_text() == text
        print("corpus deterministic:", ok)
        sys.exit(0 if ok else 1)
    out.write_text(text)
    d = json.loads(text)
    print(f"wrote {len(d['valid'])} valid + {len(d['invalid'])} invalid vectors")
