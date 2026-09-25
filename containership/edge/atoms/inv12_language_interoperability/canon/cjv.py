"""Canonical JSON Value form (CJV/1) - the language-neutral value notation used
by the golden corpus and by the Rust / Go / JavaScript / Python fixtures.

=============  ==============================================================
type           CJV
=============  ==============================================================
bool           true / false
integers       decimal *string* (exact for 64-bit in every language)
f32 / f64      bit pattern string ``"0x%08x"`` / ``"0x%016x"`` (NaN canonical)
char           decimal string of the scalar value
string         JSON string
list / tuple   array
record         object keyed by field name
variant        {"case": name}  or  {"case": name, "value": v}
enum           case name string
flags          array of set flag names in declaration order
option         null  or  {"some": v}
result         {"ok": v|null}  or  {"error": v|null}
own / borrow   decimal string handle index
=============  ==============================================================
"""
from __future__ import annotations

from .errors import ValidationError
from .numeric import bits_f32, bits_f64, f32_bits, f64_bits
from .types import (AsyncT, EnumT, FlagsT, HandleT, INT_RANGES, ListT, OptionT, Prim, RecordT,
                    ResultT, TupleT, VariantT)
from .values import Err, Ok, Some, Variant


def to_cjv(v, t):
    k = t.kind
    if isinstance(t, Prim):
        if k == "bool":
            return v
        if k in INT_RANGES:
            return str(v)
        if k == "f32":
            return "0x%08x" % f32_bits(v)
        if k == "f64":
            return "0x%016x" % f64_bits(v)
        if k == "char":
            return str(ord(v))
        return v
    if isinstance(t, ListT):
        return [to_cjv(x, t.elem) for x in v]
    if isinstance(t, TupleT):
        return [to_cjv(x, et) for x, et in zip(v, t.elems, strict=True)]
    if isinstance(t, RecordT):
        return {n: to_cjv(v[n], ft) for n, ft in t.fields}
    if isinstance(t, VariantT):
        ct = dict(t.cases)[v.case]
        return {"case": v.case} if ct is None else {"case": v.case, "value": to_cjv(v.value, ct)}
    if isinstance(t, EnumT):
        return v
    if isinstance(t, FlagsT):
        return [n for n in t.names if n in v]
    if isinstance(t, OptionT):
        return None if v is None else {"some": to_cjv(v.value, t.elem)}
    if isinstance(t, ResultT):
        side, st = ("ok", t.ok) if type(v) is Ok else ("error", t.err)
        return {side: None if st is None else to_cjv(v.value, st)}
    if isinstance(t, (HandleT, AsyncT)):
        return str(v if type(v) is int else v.index)
    raise ValidationError(f"no CJV form for {k}")


def from_cjv(j, t):
    k = t.kind
    if isinstance(t, Prim):
        if k == "bool":
            return j
        if k in INT_RANGES:
            return int(j)
        if k == "f32":
            return bits_f32(int(j, 16))
        if k == "f64":
            return bits_f64(int(j, 16))
        if k == "char":
            return chr(int(j))
        return j
    if isinstance(t, ListT):
        return [from_cjv(x, t.elem) for x in j]
    if isinstance(t, TupleT):
        return tuple(from_cjv(x, et) for x, et in zip(j, t.elems, strict=True))
    if isinstance(t, RecordT):
        return {n: from_cjv(j[n], ft) for n, ft in t.fields}
    if isinstance(t, VariantT):
        ct = dict(t.cases)[j["case"]]
        return Variant(j["case"], None if ct is None else from_cjv(j["value"], ct))
    if isinstance(t, EnumT):
        return j
    if isinstance(t, FlagsT):
        return frozenset(j)
    if isinstance(t, OptionT):
        return None if j is None else Some(from_cjv(j["some"], t.elem))
    if isinstance(t, ResultT):
        if "ok" in j:
            return Ok(None if t.ok is None else from_cjv(j["ok"], t.ok))
        return Err(None if t.err is None else from_cjv(j["error"], t.err))
    if isinstance(t, (HandleT, AsyncT)):
        return int(j)
    raise ValidationError(f"no CJV form for {k}")
