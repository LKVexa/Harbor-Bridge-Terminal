"""MC-010 canonical binary layout engine and MC-013 variant/option/result wire model.

Implements the Component Model canonical ABI memory representation for the
types in :mod:`types`:

=============  ======  =====  =============================================
type           size    align  representation
=============  ======  =====  =============================================
bool           1       1      0 / 1 (lift: any non-zero is true, per spec)
s8/u8          1       1      two's complement / unsigned, little-endian
s16/u16        2       2
s32/u32        4       4
s64/u64        8       8
f32 / f64      4 / 8   4 / 8  IEEE-754; NaN canonicalized on store
char           4       4      Unicode scalar value as u32 (invalid -> trap)
string         8       4      (ptr:u32, byte_len:u32), UTF-8, align-1 payload
list<T>        8       4      (ptr:u32, count:u32), elements at size(T) stride
record/tuple   *       max    fields in order, each at align_to(offset, align)
variant        *       max    discriminant (u8 <=256 cases, u16 <=65536, else
                              u32) then payload at align_to(disc, max case
                              align); size rounded to the variant alignment
enum           disc    disc   variant with no payloads
option<T>      -       -      variant { none, some(T) }
result<T,E>    -       -      variant { ok(T), error(E) }
flags          0/1/2/4n       n=0: 0 bytes; <=8: u8; <=16: u16; else u32 x ceil(n/32)
own/borrow     4       4      i32 handle index in the *receiving* table
future/stream  4       4      i32 handle index
=============  ======  =====  =============================================

Invalid discriminants, undeclared flag bits (stricter than the spec, which
ignores them), out-of-bounds or misaligned pointers, overflowing lengths and
invalid UTF-8 / char values are rejected on lift.  Every lift reads through the
checked :class:`~memory.GuestMemory`.

Round-trip invariant: ``lift(lower(v)) == v`` for every valid ``v`` **except**
(1) NaN payload bits (canonicalized) and (2) handle identity (lowering an own
handle moves it; the lifted handle is a fresh handle in the receiving table).
``lower(lift(bytes)) == bytes`` does not hold for non-canonical ``bool`` bytes
(2..255 lift to ``True`` and lower back to 1).

Flattening follows the spec: MAX_FLAT_PARAMS = 16, MAX_FLAT_RESULTS = 1; when
exceeded, values are passed indirectly through memory.
"""
from __future__ import annotations

import math

from .errors import InteropError, ValidationError
from .memory import Allocator, GuestMemory, align_to, checked_add, checked_mul
from .numeric import bits_f32, bits_f64, f32_bits, f64_bits
from .text import char_from_u32, decode_utf8, encode_utf8
from .types import (AsyncT, EnumT, FlagsT, HandleT, INT_RANGES, ListT, OptionT, Prim,
                    RecordT, ResultT, TupleT, Type, VariantT, enum_as_variant,
                    option_as_variant, result_as_variant)
from .values import Err, Ok, Some, Variant

MAX_FLAT_PARAMS = 16
MAX_FLAT_RESULTS = 1
_PRIM_SIZE = {"bool": 1, "s8": 1, "u8": 1, "s16": 2, "u16": 2, "s32": 4, "u32": 4,
              "s64": 8, "u64": 8, "f32": 4, "f64": 8, "char": 4}


def _despecialize(t: Type) -> Type:
    if isinstance(t, EnumT):
        return enum_as_variant(t)
    if isinstance(t, OptionT):
        return option_as_variant(t)
    if isinstance(t, ResultT):
        return result_as_variant(t)
    if isinstance(t, TupleT):
        return RecordT("record", "", tuple((str(i), e) for i, e in enumerate(t.elems)))
    return t


def disc_size(n: int) -> int:
    if n <= 0:
        raise ValidationError("variant needs at least one case")
    return 1 if n <= 2**8 else 2 if n <= 2**16 else 4


def _flags_size(n: int) -> int:
    return 0 if n == 0 else 1 if n <= 8 else 2 if n <= 16 else 4 * ((n + 31) // 32)


def alignment(t: Type) -> int:
    t = _despecialize(t)
    if isinstance(t, Prim):
        return _PRIM_SIZE.get(t.kind, 4)  # string -> 4
    if isinstance(t, (ListT, HandleT, AsyncT)):
        return 4
    if isinstance(t, RecordT):
        return max((alignment(ft) for _, ft in t.fields), default=1)
    if isinstance(t, VariantT):
        return max([disc_size(len(t.cases))] + [alignment(ct) for _, ct in t.cases if ct])
    if isinstance(t, FlagsT):
        n = len(t.names)
        return 1 if n <= 8 else 2 if n <= 16 else 4
    raise ValidationError(f"no alignment for {t.kind}")


def size(t: Type) -> int:
    t = _despecialize(t)
    if isinstance(t, Prim):
        return _PRIM_SIZE.get(t.kind, 8)  # string -> 8
    if isinstance(t, (ListT,)):
        return 8
    if isinstance(t, (HandleT, AsyncT)):
        return 4
    if isinstance(t, RecordT):
        s = 0
        for _, ft in t.fields:
            s = align_to(s, alignment(ft))
            s = checked_add(s, size(ft))
        return align_to(s, alignment(t))
    if isinstance(t, VariantT):
        s = disc_size(len(t.cases))
        s = align_to(s, _max_case_align(t))
        s = checked_add(s, max((size(ct) for _, ct in t.cases if ct), default=0))
        return align_to(s, alignment(t))
    if isinstance(t, FlagsT):
        return _flags_size(len(t.names))
    raise ValidationError(f"no size for {t.kind}")


def _max_case_align(t: VariantT) -> int:
    return max((alignment(ct) for _, ct in t.cases if ct), default=1)


def _payload_offset(t: VariantT) -> int:
    return align_to(disc_size(len(t.cases)), _max_case_align(t))


# ------------------------------------------------------------------ store
class HandleCodec:
    """Default handle codec: writes/reads the raw index (used by the corpus).

    Production callers pass a codec bound to resource tables so that lowering an
    own handle moves it and lifting validates the index in the receiving table.
    """

    def lower(self, value, t):
        from .resources import Handle
        if type(value) is Handle:
            return value.index
        if type(value) is int and 0 < value <= 0xFFFFFFFF:
            return value
        raise ValidationError("handle value required", code="PK_INTEROP_HANDLE")

    def lift(self, index, t):
        if index == 0:
            raise InteropError("handle index 0 is never valid", code="PK_INTEROP_HANDLE")
        return index


class _Ctx:
    def __init__(self, mem: GuestMemory, alloc, handles):
        self.mem = mem
        self.alloc = alloc
        self.handles = handles or HandleCodec()


def store(ctx: _Ctx, v, t: Type, ptr: int):
    k = t.kind
    if isinstance(t, Prim):
        if k == "bool":
            ctx.mem.store_uint(ptr, 1, 1 if v else 0)
        elif k in INT_RANGES:
            n = _PRIM_SIZE[k]
            ctx.mem.store_uint(ptr, n, v & ((1 << (8 * n)) - 1))
        elif k == "f32":
            ctx.mem.store_uint(ptr, 4, f32_bits(v))
        elif k == "f64":
            ctx.mem.store_uint(ptr, 8, f64_bits(v))
        elif k == "char":
            ctx.mem.store_uint(ptr, 4, ord(v))
        elif k == "string":
            data = encode_utf8(v)
            p = ctx.alloc(1, len(data))
            ctx.mem.write(p, data)
            ctx.mem.store_uint(ptr, 4, p)
            ctx.mem.store_uint(ptr + 4, 4, len(data))
        return
    if isinstance(t, ListT):
        es, ea = size(t.elem), alignment(t.elem)
        nbytes = checked_mul(len(v), es)
        p = ctx.alloc(ea, nbytes)
        for i, e in enumerate(v):
            store(ctx, e, t.elem, p + i * es)
        ctx.mem.store_uint(ptr, 4, p)
        ctx.mem.store_uint(ptr + 4, 4, len(v))
        return
    if isinstance(t, TupleT):
        return store(ctx, {str(i): e for i, e in enumerate(v)}, _despecialize(t), ptr)
    if isinstance(t, RecordT):
        off = 0
        for n, ft in t.fields:
            off = align_to(off, alignment(ft))
            store(ctx, v[n], ft, ptr + off)
            off += size(ft)
        return
    if isinstance(t, FlagsT):
        bits = 0
        for i, n in enumerate(t.names):
            if n in v:
                bits |= 1 << i
        sz = _flags_size(len(t.names))
        if sz in (1, 2):
            ctx.mem.store_uint(ptr, sz, bits)
        else:
            for w in range(sz // 4):
                ctx.mem.store_uint(ptr + 4 * w, 4, (bits >> (32 * w)) & 0xFFFFFFFF)
        return
    if isinstance(t, (HandleT, AsyncT)):
        ctx.mem.store_uint(ptr, 4, ctx.handles.lower(v, t))
        return
    # variant family
    vt = _despecialize(t)
    if isinstance(t, EnumT):
        case, payload = v, None
    elif isinstance(t, OptionT):
        case, payload = ("none", None) if v is None else ("some", v.value)
    elif isinstance(t, ResultT):
        case, payload = ("ok", v.value) if type(v) is Ok else ("error", v.value)
    else:
        case, payload = v.case, v.value
    names = [c for c, _ in vt.cases]
    idx = names.index(case)
    ctx.mem.store_uint(ptr, disc_size(len(names)), idx)
    ct = vt.cases[idx][1]
    if ct is not None:
        store(ctx, payload, ct, ptr + _payload_offset(vt))


def load(mem: GuestMemory, ptr: int, t: Type, handles=None, _depth=0):
    if _depth > 128:
        raise InteropError("lift nesting too deep", code="PK_INTEROP_LIMIT")
    handles = handles or HandleCodec()
    k = t.kind
    d = _depth + 1
    if isinstance(t, Prim):
        if k == "bool":
            return mem.load_uint(ptr, 1) != 0
        if k in INT_RANGES:
            n = _PRIM_SIZE[k]
            u = mem.load_uint(ptr, n)
            if k[0] == "s" and u >= 1 << (8 * n - 1):
                u -= 1 << (8 * n)
            return u
        if k == "f32":
            f = bits_f32(mem.load_uint(ptr, 4))
            return math.nan if math.isnan(f) else f
        if k == "f64":
            f = bits_f64(mem.load_uint(ptr, 8))
            return math.nan if math.isnan(f) else f
        if k == "char":
            return char_from_u32(mem.load_uint(ptr, 4))
        if k == "string":
            p, n = mem.load_uint(ptr, 4), mem.load_uint(ptr + 4, 4)
            return decode_utf8(mem.read(p, n))
    if isinstance(t, ListT):
        p, n = mem.load_uint(ptr, 4), mem.load_uint(ptr + 4, 4)
        es, ea = size(t.elem), alignment(t.elem)
        total = checked_mul(n, es)
        mem._check(p, total, ea)
        if es == 0 and n > 1_000_000:
            raise InteropError("zero-size list element count too large", code="PK_INTEROP_LIMIT")
        return [load(mem, p + i * es, t.elem, handles, d) for i in range(n)]
    if isinstance(t, TupleT):
        r = load(mem, ptr, _despecialize(t), handles, d)
        return tuple(r[str(i)] for i in range(len(t.elems)))
    if isinstance(t, RecordT):
        out, off = {}, 0
        for n, ft in t.fields:
            off = align_to(off, alignment(ft))
            out[n] = load(mem, ptr + off, ft, handles, d)
            off += size(ft)
        return out
    if isinstance(t, FlagsT):
        sz = _flags_size(len(t.names))
        if sz == 0:
            return frozenset()
        if sz in (1, 2):
            bits = mem.load_uint(ptr, sz)
        else:
            bits = 0
            for w in range(sz // 4):
                bits |= mem.load_uint(ptr + 4 * w, 4) << (32 * w)
        if bits >> len(t.names):
            raise InteropError("flags value sets undeclared bits", code="PK_INTEROP_INVALID_FLAGS")
        return frozenset(n for i, n in enumerate(t.names) if bits >> i & 1)
    if isinstance(t, (HandleT, AsyncT)):
        return handles.lift(mem.load_uint(ptr, 4), t)
    vt = _despecialize(t)
    n = len(vt.cases)
    idx = mem.load_uint(ptr, disc_size(n))
    if idx >= n:
        raise InteropError(f"discriminant {idx} >= {n} cases", code="PK_INTEROP_INVALID_DISCRIMINANT")
    case, ct = vt.cases[idx]
    payload = None if ct is None else load(mem, ptr + _payload_offset(vt), ct, handles, d)
    if isinstance(t, EnumT):
        return case
    if isinstance(t, OptionT):
        return None if case == "none" else Some(payload)
    if isinstance(t, ResultT):
        return Ok(payload) if case == "ok" else Err(payload)
    return Variant(case, payload)


# ------------------------------------------------------------ public helpers
def lower_to_memory(value, t: Type, mem: GuestMemory, realloc, handles=None) -> int:
    """Store an already-validated value; returns the root pointer."""
    ctx = _Ctx(mem, realloc, handles)
    root = realloc(alignment(t), size(t))
    store(ctx, value, t, root)
    return root


def encode(value, t: Type, *, validated: bool = False) -> tuple[bytes, int]:
    """Validate and lower *value* into a fresh deterministic memory image.

    Returns ``(image, root_ptr)``.  This is the golden-vector wire form.
    """
    if not validated:
        from .validate import validate
        value = validate(value, t)
    mem = GuestMemory()
    alloc = Allocator(mem)
    root = lower_to_memory(value, t, mem, lambda a, s: alloc(0, 0, a, s))
    return mem.snapshot(), root


def decode(image: bytes, root: int, t: Type, handles=None):
    return load(GuestMemory(bytearray(image)), root, t, handles)


# ------------------------------------------------------------- flattening
def _join(a, b):
    if a == b:
        return a
    if {a, b} == {"i32", "f32"}:
        return "i32"
    return "i64"


def flatten(t: Type) -> list:
    t2 = _despecialize(t)
    if isinstance(t2, Prim):
        k = t2.kind
        if k in ("s64", "u64"):
            return ["i64"]
        if k == "f32":
            return ["f32"]
        if k == "f64":
            return ["f64"]
        if k == "string":
            return ["i32", "i32"]
        return ["i32"]
    if isinstance(t2, ListT):
        return ["i32", "i32"]
    if isinstance(t2, (HandleT, AsyncT)):
        return ["i32"]
    if isinstance(t2, RecordT):
        out = []
        for _, ft in t2.fields:
            out += flatten(ft)
        return out
    if isinstance(t2, FlagsT):
        return ["i32"] * (_flags_size(len(t2.names)) // 4 or (1 if t2.names else 0))
    if isinstance(t2, VariantT):
        flat = []
        for _, ct in t2.cases:
            if ct is None:
                continue
            for i, ft in enumerate(flatten(ct)):
                if i < len(flat):
                    flat[i] = _join(flat[i], ft)
                else:
                    flat.append(ft)
        return ["i32"] + flat
    raise ValidationError(f"cannot flatten {t.kind}")


def flatten_signature(params: list, result) -> dict:
    fp = []
    for p in params:
        fp += flatten(p)
    fr = flatten(result) if result is not None else []
    return {
        "params": fp if len(fp) <= MAX_FLAT_PARAMS else ["i32"],
        "params_indirect": len(fp) > MAX_FLAT_PARAMS,
        "results": fr if len(fr) <= MAX_FLAT_RESULTS else ["i32"],
        "results_indirect": len(fr) > MAX_FLAT_RESULTS,
    }
