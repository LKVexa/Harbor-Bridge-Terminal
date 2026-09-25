"""MC-006 recursive composite validator.

``validate(value, type)`` checks a host value against a resolved :class:`Type`
*recursively* (every field, element and case payload), enforces the per-type
budget from :mod:`limits`, and returns a *detached* canonical copy (so no alias
of the caller's mutable containers survives).  Validation happens entirely
before any guest-memory allocation, handle transfer or I/O.

Errors are path-aware: the error ``path`` lists record field names, list
indexes, tuple positions and case names from the root to the offending node.
Only exact built-in host types are admitted; subclasses of ``int``/``str``/
``list``/``dict`` are refused before any user-defined hook can run.
"""
from __future__ import annotations

from .errors import InteropError, ValidationError
from .limits import Budget, Limits, HARD_CEILING
from .numeric import check_float, check_int
from .text import check_char, encode_utf8
from .types import (AsyncT, EnumT, FlagsT, HandleT, INT_RANGES, ListT, OptionT, Prim,
                    RecordT, ResultT, TupleT, Type, VariantT)
from .values import Err, Ok, Some, Variant


def _mm(msg, path):
    return ValidationError(msg, code="PK_INTEROP_TYPE_MISMATCH", path=list(path))


def validate(value, t: Type, *, limits: Limits = HARD_CEILING, table=None):
    """Validate *value* against *t* and return a detached canonical copy."""
    if not isinstance(t, Type):
        raise ValidationError("type must be a resolved canon Type")
    budget = Budget(limits)
    return _v(value, t, budget, table, (), 0, set())


def _v(value, t, b: Budget, table, path, depth, active):
    b.depth(depth, list(path))
    b.node(list(path))
    k = t.kind
    if isinstance(t, Prim):
        if k == "bool":
            if type(value) is not bool:
                raise _mm(f"{type(value).__name__} is not a bool", path)
            return value
        if k in INT_RANGES:
            return check_int(value, k, list(path))
        if k in ("f32", "f64"):
            return check_float(value, k, list(path))
        if k == "char":
            return check_char(value, list(path))
        if k == "string":
            if type(value) is str and len(value) > b.limits.max_string_bytes:
                # UTF-8 needs >= 1 byte per code point: refuse before encoding.
                b.string(len(value), list(path))
            b.string(len(encode_utf8(value, list(path))), list(path))
            return value
    d = depth + 1
    if isinstance(t, ListT):
        if type(value) not in (list, tuple):
            raise _mm(f"{type(value).__name__} is not a list", path)
        b.items(len(value), list(path))
        marker = id(value)
        if marker in active:
            raise ValidationError("cyclic value", code="PK_INTEROP_CANONICALIZATION", path=list(path))
        active.add(marker)
        try:
            return [_v(x, t.elem, b, table, path + (i,), d, active) for i, x in enumerate(value)]
        finally:
            active.discard(marker)
    if isinstance(t, TupleT):
        if type(value) is not tuple:
            raise _mm(f"{type(value).__name__} is not a tuple", path)
        if len(value) != len(t.elems):
            raise _mm(f"tuple arity {len(value)} != {len(t.elems)}", path)
        return tuple(_v(x, et, b, table, path + (i,), d, active) for i, (x, et) in enumerate(zip(value, t.elems, strict=True)))
    if isinstance(t, RecordT):
        if type(value) is not dict:
            raise _mm(f"{type(value).__name__} is not a record", path)
        names = [n for n, _ in t.fields]
        for key in value:
            if type(key) is not str:
                raise _mm("record keys must be exact str", path)
        extra = set(value) - set(names)
        missing = [n for n in names if n not in value]
        if extra:
            raise _mm(f"unknown record field(s): {len(extra)}", path)
        if missing:
            raise _mm(f"missing record field {missing[0]!r}", path)
        marker = id(value)
        if marker in active:
            raise ValidationError("cyclic value", code="PK_INTEROP_CANONICALIZATION", path=list(path))
        active.add(marker)
        try:
            return {n: _v(value[n], ft, b, table, path + (n,), d, active) for n, ft in t.fields}
        finally:
            active.discard(marker)
    if isinstance(t, VariantT):
        if type(value) is not Variant:
            raise _mm(f"{type(value).__name__} is not a Variant", path)
        cases = dict(t.cases)
        if type(value.case) is not str or value.case not in cases:
            raise ValidationError("unknown variant case", code="PK_INTEROP_INVALID_DISCRIMINANT", path=list(path))
        ct = cases[value.case]
        if ct is None:
            if value.value is not None:
                raise _mm(f"case {value.case} carries no payload", path + (value.case,))
            return Variant(value.case, None)
        return Variant(value.case, _v(value.value, ct, b, table, path + (value.case,), d, active))
    if isinstance(t, EnumT):
        if type(value) is not str or value not in t.cases:
            raise ValidationError("unknown enum case", code="PK_INTEROP_INVALID_DISCRIMINANT", path=list(path))
        return value
    if isinstance(t, FlagsT):
        if type(value) not in (set, frozenset):
            raise _mm(f"{type(value).__name__} is not a flags set", path)
        for f in value:
            if type(f) is not str or f not in t.names:
                raise ValidationError("undeclared flag", code="PK_INTEROP_INVALID_FLAGS", path=list(path))
        return frozenset(value)
    if isinstance(t, OptionT):
        if value is None:
            return None
        if type(value) is not Some:
            raise _mm(f"{type(value).__name__} is not None or Some", path)
        return Some(_v(value.value, t.elem, b, table, path + ("some",), d, active))
    if isinstance(t, ResultT):
        if type(value) is Ok:
            side, st, ctor = "ok", t.ok, Ok
        elif type(value) is Err:
            side, st, ctor = "error", t.err, Err
        else:
            raise _mm(f"{type(value).__name__} is not Ok or Err", path)
        if st is None:
            if value.value is not None:
                raise _mm(f"result {side} side carries no payload", path + (side,))
            return ctor(None)
        return ctor(_v(value.value, st, b, table, path + (side,), d, active))
    if isinstance(t, HandleT):
        from .resources import Handle
        if type(value) is not Handle:
            raise _mm(f"{type(value).__name__} is not a resource handle", path)
        if value.resource != t.resource:
            raise ValidationError("handle for the wrong resource type", code="PK_INTEROP_HANDLE", path=list(path))
        if table is not None:
            try:
                table.validate(value, "own" if t.kind == "own" else value.kind, t.resource)
            except InteropError as e:
                raise e.at(*path)
        return value
    if isinstance(t, AsyncT):
        from .async_model import Future, Stream
        want = Future if t.kind == "future" else Stream
        if type(value) is not want:
            raise _mm(f"{type(value).__name__} is not a {t.kind}", path)
        return value
    raise _mm(f"unsupported type kind {k}", path)
