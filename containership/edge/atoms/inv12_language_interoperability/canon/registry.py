"""MC-007 language representation registry.

Replaces flat type allow-lists with a *versioned* table stating the exact native
representation of every canonical type kind in every supported guest language.
A profile must cover every canonical kind: each entry is either an exact mapping
or an explicit refusal (``None``) — there is no implicit fallback.

``check(kind, language)`` raises ``PK_INTEROP_UNREPRESENTABLE`` for a refused or
unknown pair.  ``PROFILE_DIGEST`` is the sha256 of the canonical JSON of the
table and is what mapping-policy provenance (MC-045) approves.
"""
from __future__ import annotations

import hashlib
import json
from types import MappingProxyType

from .errors import InteropError, ConfigError

PROFILE_ID = "inv12-mapping"
PROFILE_VERSION = "2.0.0"

KINDS = ("bool", "s8", "u8", "s16", "u16", "s32", "u32", "s64", "u64", "f32", "f64",
         "char", "string", "list", "tuple", "record", "variant", "enum", "flags",
         "option", "result", "own", "borrow", "future", "stream")

_TABLE = {
    "rust": {
        "bool": "bool", "s8": "i8", "u8": "u8", "s16": "i16", "u16": "u16",
        "s32": "i32", "u32": "u32", "s64": "i64", "u64": "u64",
        "f32": "f32", "f64": "f64", "char": "char", "string": "String (UTF-8)",
        "list": "Vec<T>", "tuple": "(T1, ..)", "record": "struct", "variant": "enum with payloads",
        "enum": "fieldless enum", "flags": "bitflags struct", "option": "Option<T>",
        "result": "Result<T, E>", "own": "owned resource struct (Drop releases)",
        "borrow": "&Resource (call-scoped)", "future": "FutureReader<T>", "stream": "StreamReader<T>",
    },
    "go": {
        "bool": "bool", "s8": "int8", "u8": "uint8", "s16": "int16", "u16": "uint16",
        "s32": "int32", "u32": "uint32", "s64": "int64", "u64": "uint64",
        "f32": "float32", "f64": "float64", "char": "rune (validated scalar)",
        "string": "string (validated UTF-8)", "list": "[]T", "tuple": "struct{F0..Fn}",
        "record": "struct", "variant": "tagged struct", "enum": "uint8/16/32 typed const",
        "flags": "uint8/16/32/[]uint32 bitset", "option": "Option[T] {IsSome bool; Val T}",
        "result": "Result[T,E] {IsErr bool; Ok T; Err E}", "own": "resource handle type",
        "borrow": "borrowed handle (call-scoped)", "future": None, "stream": None,
    },
    "javascript": {
        "bool": "boolean", "s8": "number", "u8": "number", "s16": "number", "u16": "number",
        "s32": "number", "u32": "number", "s64": "bigint", "u64": "bigint",
        "f32": "number (Math.fround-exact)", "f64": "number", "char": "string (1 scalar)",
        "string": "string (UTF-16, lone surrogates refused)", "list": "Array<T>",
        "tuple": "Array (fixed arity)", "record": "Object (camelCase keys)",
        "variant": "{tag, val}", "enum": "string", "flags": "Object<string, boolean>",
        "option": "{tag:'none'} | {tag:'some', val}", "result": "{tag:'ok'|'err', val}",
        "own": "class instance (Symbol.dispose)", "borrow": "class instance (call-scoped)",
        "future": "Promise-like reader", "stream": "ReadableStream-like reader",
    },
    "python": {
        "bool": "bool", "s8": "int", "u8": "int", "s16": "int", "u16": "int",
        "s32": "int", "u32": "int", "s64": "int", "u64": "int",
        "f32": "float (f32-exact)", "f64": "float", "char": "str (len 1, no surrogate)",
        "string": "str (no surrogates)", "list": "list", "tuple": "tuple", "record": "dict",
        "variant": "canon.values.Variant", "enum": "str", "flags": "frozenset[str]",
        "option": "None | canon.values.Some", "result": "canon.values.Ok | canon.values.Err",
        "own": "canon.resources.Handle(kind='own')", "borrow": "canon.resources.Handle(kind='borrow')",
        "future": "canon.async_model.Future", "stream": "canon.async_model.Stream",
    },
}


def _freeze(table: dict) -> MappingProxyType:
    out = {}
    for lang, m in table.items():
        missing = [k for k in KINDS if k not in m]
        extra = [k for k in m if k not in KINDS]
        if missing or extra:
            raise ConfigError(f"profile for {lang} must map every kind exactly once",
                              path=[lang])
        out[lang] = MappingProxyType(dict(m))
    return MappingProxyType(out)


REGISTRY = _freeze(_TABLE)
SUPPORTED_LANGUAGES = frozenset(REGISTRY)


def table_json(registry=REGISTRY) -> str:
    return json.dumps({"profile": PROFILE_ID, "version": PROFILE_VERSION,
                       "table": {k: dict(v) for k, v in registry.items()}},
                      sort_keys=True, separators=(",", ":"))


PROFILE_DIGEST = "sha256:" + hashlib.sha256(table_json().encode()).hexdigest()


def representation(kind: str, language: str, registry=REGISTRY) -> str:
    if type(language) is not str or language not in registry:
        raise InteropError("unsupported guest language", code="PK_INTEROP_UNREPRESENTABLE",
                           target_language=language if type(language) is str else None)
    if type(kind) is not str or kind not in registry[language]:
        raise InteropError("unknown canonical type kind", code="PK_INTEROP_UNREPRESENTABLE",
                           target_language=language)
    rep = registry[language][kind]
    if rep is None:
        raise InteropError(f"{language} profile refuses {kind}", code="PK_INTEROP_UNREPRESENTABLE",
                           target_language=language)
    return rep


def check_type(t, language: str, registry=REGISTRY) -> None:
    """Recursively check that every node of type *t* is representable."""
    from .types import (AsyncT, ListT, OptionT, RecordT, ResultT, TupleT, VariantT)
    stack = [t]
    while stack:
        x = stack.pop()
        representation(x.kind, language, registry)
        if isinstance(x, (ListT, OptionT)):
            stack.append(x.elem)
        elif isinstance(x, AsyncT) and x.elem is not None:
            stack.append(x.elem)
        elif isinstance(x, ResultT):
            stack += [y for y in (x.ok, x.err) if y is not None]
        elif isinstance(x, TupleT):
            stack += list(x.elems)
        elif isinstance(x, RecordT):
            stack += [ft for _, ft in x.fields]
        elif isinstance(x, VariantT):
            stack += [ct for _, ct in x.cases if ct is not None]


def extend(language: str, mapping: dict, registry=REGISTRY):
    """Return a new registry with an additional guest profile (future guests)."""
    if type(language) is not str or not language.isidentifier() or language in registry:
        raise ConfigError("new language name must be a fresh identifier")
    t = {k: dict(v) for k, v in registry.items()}
    t[language] = dict(mapping)
    return _freeze(t)
