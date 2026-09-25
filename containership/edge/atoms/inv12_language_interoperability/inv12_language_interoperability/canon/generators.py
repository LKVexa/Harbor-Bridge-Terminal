"""MC-027 property-based generation (stdlib ``random``, reproducible seeds).

``gen_type(rng, depth)`` draws a random *valid* canonical type (no handles);
``gen_value(rng, t)`` draws a random valid value of that type with boundary
values over-represented; ``mutate(rng, image)`` produces adversarial images for
fuzzing (bit flips, length/pointer smashing, truncation, extension).
"""
from __future__ import annotations

import math
import random

from .types import (EnumT, FlagsT, INT_RANGES, ListT, OptionT, PRIMITIVES, Prim, RecordT,
                    ResultT, TupleT, VariantT)
from .values import Err, Ok, Some, Variant

_F32_SPECIALS = [0.0, -0.0, 1.0, -1.5, math.inf, -math.inf, math.nan, 3.4028234663852886e38,
                 1.401298464324817e-45]
_F64_SPECIALS = [0.0, -0.0, math.pi, 5e-324, 1.7976931348623157e308, -math.inf, math.nan]
_STRINGS = ["", "a", "\x00", "é", "世界", "\U0001F600", "￿", "x" * 40]


def _name(rng, prefix):
    return f"{prefix}{rng.randrange(1000)}"


def gen_type(rng: random.Random, depth: int = 3):
    if depth <= 0 or rng.random() < 0.35:
        return Prim(rng.choice(PRIMITIVES))
    d = depth - 1
    c = rng.randrange(9)
    if c == 0:
        return ListT("list", gen_type(rng, d))
    if c == 1:
        return OptionT("option", gen_type(rng, d))
    if c == 2:
        return ResultT("result", gen_type(rng, d) if rng.random() < .8 else None,
                       gen_type(rng, d) if rng.random() < .8 else None)
    if c == 3:
        return TupleT("tuple", tuple(gen_type(rng, d) for _ in range(rng.randint(1, 4))))
    if c == 4:
        n = rng.randint(1, 5)
        return RecordT("record", "r", tuple((f"f{i}", gen_type(rng, d)) for i in range(n)))
    if c == 5:
        n = rng.randint(1, 5)
        return VariantT("variant", "v", tuple(
            (f"c{i}", gen_type(rng, d) if rng.random() < .7 else None) for i in range(n)))
    if c == 6:
        return EnumT("enum", "e", tuple(f"e{i}" for i in range(rng.choice([1, 2, 3, 255, 256, 257]))))
    if c == 7:
        return FlagsT("flags", "g", tuple(f"g{i}" for i in range(rng.choice([0, 1, 8, 9, 16, 17, 32, 33, 64]))))
    return Prim(rng.choice(PRIMITIVES))


def gen_value(rng: random.Random, t, depth: int = 0):
    k = t.kind
    if isinstance(t, Prim):
        if k == "bool":
            return rng.random() < .5
        if k in INT_RANGES:
            lo, hi = INT_RANGES[k]
            return rng.choice([lo, hi, 0, lo + 1, hi - 1, rng.randint(lo, hi)])
        if k == "f32":
            if rng.random() < .4:
                return rng.choice(_F32_SPECIALS)
            import struct
            return struct.unpack("<f", struct.pack("<f", rng.uniform(-1e6, 1e6)))[0]
        if k == "f64":
            return rng.choice(_F64_SPECIALS) if rng.random() < .4 else rng.uniform(-1e300, 1e300)
        if k == "char":
            while True:
                cp = rng.choice([0, 0x7F, 0x80, 0x7FF, 0x800, 0xD7FF, 0xE000, 0xFFFF, 0x10000,
                                 0x10FFFF, rng.randrange(0x110000)])
                if not 0xD800 <= cp <= 0xDFFF:
                    return chr(cp)
        if k == "string":
            if rng.random() < .5:
                return rng.choice(_STRINGS)
            return "".join(gen_value(rng, Prim("char")) for _ in range(rng.randint(0, 12)))
    n_items = 0 if depth > 4 else rng.choice([0, 1, 2, 3, 5])
    if isinstance(t, ListT):
        return [gen_value(rng, t.elem, depth + 1) for _ in range(n_items)]
    if isinstance(t, TupleT):
        return tuple(gen_value(rng, e, depth + 1) for e in t.elems)
    if isinstance(t, RecordT):
        return {n: gen_value(rng, ft, depth + 1) for n, ft in t.fields}
    if isinstance(t, VariantT):
        c, ct = rng.choice(t.cases)
        return Variant(c, None if ct is None else gen_value(rng, ct, depth + 1))
    if isinstance(t, EnumT):
        return rng.choice(t.cases)
    if isinstance(t, FlagsT):
        return frozenset(n for n in t.names if rng.random() < .4)
    if isinstance(t, OptionT):
        return None if rng.random() < .3 else Some(gen_value(rng, t.elem, depth + 1))
    if isinstance(t, ResultT):
        if rng.random() < .5:
            return Ok(None if t.ok is None else gen_value(rng, t.ok, depth + 1))
        return Err(None if t.err is None else gen_value(rng, t.err, depth + 1))
    raise ValueError(k)


def mutate(rng: random.Random, image: bytes) -> bytes:
    b = bytearray(image)
    op = rng.randrange(6)
    if op == 0 and b:
        i = rng.randrange(len(b))
        b[i] ^= 1 << rng.randrange(8)
    elif op == 1 and len(b) >= 4:
        i = rng.randrange(0, len(b) - 3)
        b[i:i + 4] = rng.choice([0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, len(b), len(b) + 1, 1, 3]).to_bytes(4, "little")
    elif op == 2 and b:
        del b[rng.randrange(len(b)):]
    elif op == 3:
        b += bytes(rng.randrange(256) for _ in range(rng.randint(1, 16)))
    elif op == 4 and b:
        i = rng.randrange(len(b))
        b[i] = rng.choice([0x00, 0xFF, 0xC0, 0xED, 0xF4, 0xF8, 0x80])
    elif b:
        i = rng.randrange(len(b))
        b[i] = rng.randrange(256)
    return bytes(b)
