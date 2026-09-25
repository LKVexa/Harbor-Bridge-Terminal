"""MC-001/002/003/004/005/013 - canonical type AST and schema loader.

Grammar (normative, a strict subset of WIT; EBNF)::

    document   := package? interface+
    package    := "package" ident ":" ident ("@" semver)? ";"
    interface  := "interface" ident "{" item* "}"
    item       := record | variant | enum | flags | resource | alias | func
    record     := "record"  ident "{" (ident ":" type ("," ident ":" type)* ","?)? "}"
    variant    := "variant" ident "{" case ("," case)* ","? "}"
    case       := ident ("(" type ")")?
    enum       := "enum"    ident "{" ident ("," ident)* ","? "}"
    flags      := "flags"   ident "{" (ident ("," ident)* ","?)? "}"
    resource   := "resource" ident ";"
    alias      := "type" ident "=" type ";"
    func       := ident ":" "func" "(" params? ")" ("->" type)? ";"
    type       := prim | "list<" type ">" | "option<" type ">"
                | "result" ("<" (type | "_") ("," type)? ">")?
                | "tuple<" type ("," type)* ">" | "own<" ident ">" | "borrow<" ident ">"
                | "future" ("<" type ">")? | "stream" ("<" type ">")? | ident
    prim       := bool | s8 | u8 | s16 | u16 | s32 | u32 | s64 | u64
                | f32 | f64 | char | string

Identifiers are kebab-case ASCII (``[a-z][a-z0-9]*(-[a-z0-9]+)*``), matching WIT.
``//`` line comments are ignored.  Source locations (line, column) are preserved
on every declaration for diagnostics.

Types are immutable frozen dataclasses.  Named types are *resolved* during
loading, so every :class:`Type` reachable from a loaded :class:`Interface` is a
fully structural tree (plus resource names, which are nominal).  Recursive named
types are illegal (WIT forbids them) and are rejected.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .errors import SchemaError

PRIMITIVES = ("bool", "s8", "u8", "s16", "u16", "s32", "u32", "s64", "u64",
              "f32", "f64", "char", "string")
INT_RANGES = {
    "u8": (0, 2**8 - 1), "s8": (-2**7, 2**7 - 1),
    "u16": (0, 2**16 - 1), "s16": (-2**15, 2**15 - 1),
    "u32": (0, 2**32 - 1), "s32": (-2**31, 2**31 - 1),
    "u64": (0, 2**64 - 1), "s64": (-2**63, 2**63 - 1),
}
_IDENT = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
KEYWORDS = frozenset(PRIMITIVES) | {
    "list", "option", "result", "tuple", "own", "borrow", "future", "stream",
    "record", "variant", "enum", "flags", "resource", "type", "func", "interface",
    "package", "_"}

# Structural limits for schemas (MC-018/MC-001-19).
MAX_SCHEMA_BYTES = 1 << 20
MAX_DECLARATIONS = 4096
MAX_FIELDS = 1024
MAX_CASES = 1024          # variant/enum
MAX_FLAGS = 1024
MAX_TUPLE = 256
MAX_TYPE_DEPTH = 64


# --------------------------------------------------------------------------- AST
@dataclass(frozen=True)
class Type:
    kind: str

    def canonical(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError


@dataclass(frozen=True)
class Prim(Type):
    def canonical(self) -> str:
        return self.kind


@dataclass(frozen=True)
class ListT(Type):
    elem: Type

    def canonical(self) -> str:
        return f"list<{self.elem.canonical()}>"


@dataclass(frozen=True)
class OptionT(Type):
    elem: Type

    def canonical(self) -> str:
        return f"option<{self.elem.canonical()}>"


@dataclass(frozen=True)
class ResultT(Type):
    ok: Optional[Type]
    err: Optional[Type]

    def canonical(self) -> str:
        o = self.ok.canonical() if self.ok else "_"
        e = self.err.canonical() if self.err else "_"
        return f"result<{o},{e}>"


@dataclass(frozen=True)
class TupleT(Type):
    elems: tuple

    def canonical(self) -> str:
        return "tuple<" + ",".join(t.canonical() for t in self.elems) + ">"


@dataclass(frozen=True)
class RecordT(Type):
    name: str
    fields: tuple  # ((name, Type), ...)

    def canonical(self) -> str:
        return "record{" + ",".join(f"{n}:{t.canonical()}" for n, t in self.fields) + "}"


@dataclass(frozen=True)
class VariantT(Type):
    name: str
    cases: tuple  # ((name, Type|None), ...)

    def canonical(self) -> str:
        return "variant{" + ",".join(
            n + (f"({t.canonical()})" if t else "") for n, t in self.cases) + "}"


@dataclass(frozen=True)
class EnumT(Type):
    name: str
    cases: tuple

    def canonical(self) -> str:
        return "enum{" + ",".join(self.cases) + "}"


@dataclass(frozen=True)
class FlagsT(Type):
    name: str
    names: tuple

    def canonical(self) -> str:
        return "flags{" + ",".join(self.names) + "}"


@dataclass(frozen=True)
class HandleT(Type):
    """``own<R>`` (kind ``own``) or ``borrow<R>`` (kind ``borrow``)."""
    resource: str

    def canonical(self) -> str:
        return f"{self.kind}<{self.resource}>"


@dataclass(frozen=True)
class AsyncT(Type):
    """``future<T>`` / ``stream<T>`` (element may be None)."""
    elem: Optional[Type]

    def canonical(self) -> str:
        return self.kind + (f"<{self.elem.canonical()}>" if self.elem else "")


def prim(name: str) -> Prim:
    if name not in PRIMITIVES:
        raise SchemaError(f"unknown primitive {name!r}", code="PK_INTEROP_SCHEMA_UNRESOLVED")
    return Prim(name)


def enum_as_variant(t: EnumT) -> VariantT:
    return VariantT("variant", t.name, tuple((c, None) for c in t.cases))


def option_as_variant(t: OptionT) -> VariantT:
    return VariantT("variant", "option", (("none", None), ("some", t.elem)))


def result_as_variant(t: ResultT) -> VariantT:
    return VariantT("variant", "result", (("ok", t.ok), ("error", t.err)))


def type_hash(t: Type) -> str:
    """Stable structural identifier: sha256 over the canonical form."""
    return "sha256:" + hashlib.sha256(t.canonical().encode("utf-8")).hexdigest()


def descriptor(t: Type) -> dict:
    """Language-neutral JSON descriptor consumed by the non-Python bindings."""
    k = t.kind
    if isinstance(t, Prim):
        return {"k": k}
    if isinstance(t, (ListT, OptionT)):
        return {"k": k, "t": descriptor(t.elem)}
    if isinstance(t, ResultT):
        return {"k": k, "ok": descriptor(t.ok) if t.ok else None,
                "err": descriptor(t.err) if t.err else None}
    if isinstance(t, TupleT):
        return {"k": k, "ts": [descriptor(e) for e in t.elems]}
    if isinstance(t, RecordT):
        return {"k": k, "fields": [[n, descriptor(ft)] for n, ft in t.fields]}
    if isinstance(t, VariantT):
        return {"k": k, "cases": [[n, descriptor(ct) if ct else None] for n, ct in t.cases]}
    if isinstance(t, EnumT):
        return {"k": k, "cases": list(t.cases)}
    if isinstance(t, FlagsT):
        return {"k": k, "names": list(t.names)}
    if isinstance(t, HandleT):
        return {"k": k, "r": t.resource}
    if isinstance(t, AsyncT):
        return {"k": k, "t": descriptor(t.elem) if t.elem else None}
    raise SchemaError(f"no descriptor for {k}")


def from_descriptor(d: object, _depth: int = 0) -> Type:
    """Inverse of :func:`descriptor` with full validation (untrusted input)."""
    if _depth > MAX_TYPE_DEPTH:
        raise SchemaError("descriptor too deep", code="PK_INTEROP_SCHEMA_LIMIT")
    if type(d) is not dict or type(d.get("k")) is not str:
        raise SchemaError("malformed descriptor")
    k = d["k"]
    n = _depth + 1
    if k in PRIMITIVES:
        return Prim(k)
    if k == "list":
        return ListT("list", from_descriptor(d.get("t"), n))
    if k == "option":
        return OptionT("option", from_descriptor(d.get("t"), n))
    if k == "result":
        return ResultT("result", None if d.get("ok") is None else from_descriptor(d["ok"], n),
                       None if d.get("err") is None else from_descriptor(d["err"], n))
    if k == "tuple":
        ts = d.get("ts")
        if type(ts) is not list or not ts or len(ts) > MAX_TUPLE:
            raise SchemaError("malformed tuple descriptor")
        return TupleT("tuple", tuple(from_descriptor(x, n) for x in ts))
    if k == "record":
        fs = d.get("fields")
        if type(fs) is not list or not fs or len(fs) > MAX_FIELDS:
            raise SchemaError("malformed record descriptor")
        out = tuple((_ident(f[0]), from_descriptor(f[1], n)) for f in fs)
        _no_dupes([f[0] for f in out], "record field")
        return RecordT("record", "", out)
    if k == "variant":
        cs = d.get("cases")
        if type(cs) is not list or not cs or len(cs) > MAX_CASES:
            raise SchemaError("malformed variant descriptor")
        out = tuple((_ident(c[0]), None if c[1] is None else from_descriptor(c[1], n)) for c in cs)
        _no_dupes([c[0] for c in out], "variant case")
        return VariantT("variant", "", out)
    if k == "enum":
        cs = d.get("cases")
        if type(cs) is not list or not cs or len(cs) > MAX_CASES:
            raise SchemaError("malformed enum descriptor")
        _no_dupes(cs, "enum case")
        return EnumT("enum", "", tuple(_ident(c) for c in cs))
    if k == "flags":
        ns = d.get("names")
        if type(ns) is not list or len(ns) > MAX_FLAGS:
            raise SchemaError("malformed flags descriptor")
        _no_dupes(ns, "flag")
        return FlagsT("flags", "", tuple(_ident(x) for x in ns))
    if k in ("own", "borrow"):
        return HandleT(k, _ident(d.get("r")))
    if k in ("future", "stream"):
        return AsyncT(k, None if d.get("t") is None else from_descriptor(d["t"], n))
    raise SchemaError(f"unknown descriptor kind {k!r}", code="PK_INTEROP_SCHEMA_UNRESOLVED")


def _ident(x: object) -> str:
    if type(x) is not str or not _IDENT.match(x):
        raise SchemaError("invalid identifier")
    return x


def _no_dupes(names, what):
    seen = set()
    for x in names:
        if x in seen:
            raise SchemaError(f"duplicate {what} {x!r}", code="PK_INTEROP_SCHEMA_DUPLICATE")
        seen.add(x)


# --------------------------------------------------------------- declarations
@dataclass(frozen=True)
class Location:
    line: int
    column: int


@dataclass(frozen=True)
class Function:
    name: str
    params: tuple  # ((name, Type), ...)
    result: Optional[Type]
    loc: Location

    def canonical(self) -> str:
        ps = ",".join(f"{n}:{t.canonical()}" for n, t in self.params)
        return f"func({ps})" + (f"->{self.result.canonical()}" if self.result else "")


@dataclass(frozen=True)
class Interface:
    package: Optional[str]
    version: Optional[str]
    name: str
    types: dict = field(hash=False, compare=False)      # name -> Type (resolved)
    resources: frozenset = frozenset()
    functions: dict = field(default_factory=dict, hash=False, compare=False)
    locations: dict = field(default_factory=dict, hash=False, compare=False)

    def canonical(self) -> str:
        parts = [f"interface {self.package or ''}/{self.name}@{self.version or ''}"]
        for r in sorted(self.resources):
            parts.append(f"resource {r}")
        for n in sorted(self.types):
            parts.append(f"type {n}={self.types[n].canonical()}")
        for n in sorted(self.functions):
            parts.append(f"func {n}={self.functions[n].canonical()}")
        return "\n".join(parts) + "\n"

    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()

    def type(self, name: str) -> Type:
        try:
            return self.types[name]
        except KeyError:
            raise SchemaError(f"unknown type {name!r}", code="PK_INTEROP_SCHEMA_UNRESOLVED") from None


# ------------------------------------------------------------------- lexer
_TOKEN = re.compile(r"""
    (?P<ws>[ \t\r\n]+) | (?P<comment>//[^\n]*) |
    (?P<arrow>->) | (?P<ident>[a-z_][a-z0-9_-]*) | (?P<semver>[0-9][0-9A-Za-z.+-]*) |
    (?P<punct>[{}()<>,:;=@/])
""", re.X)


def _lex(text: str):
    toks, i, line, col = [], 0, 1, 1
    while i < len(text):
        m = _TOKEN.match(text, i)
        if not m:
            raise SchemaError(f"unexpected character at {line}:{col}",
                              path=[f"{line}:{col}"])
        kind, val = m.lastgroup, m.group()
        if kind not in ("ws", "comment"):
            toks.append((kind, val, line, col))
        nl = val.count("\n")
        if nl:
            line += nl
            col = len(val) - val.rfind("\n")
        else:
            col += len(val)
        i = m.end()
    toks.append(("eof", "", line, col))
    return toks


class _Parser:
    def __init__(self, text: str):
        self.t = _lex(text)
        self.i = 0

    def peek(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def err(self, msg, code="PK_INTEROP_SCHEMA_SYNTAX"):
        _, v, ln, c = self.peek()
        return SchemaError(f"{msg} at {ln}:{c}", code=code, path=[f"{ln}:{c}"])

    def take(self, val=None, kind=None):
        tk = self.peek()
        if (val is not None and tk[1] != val) or (kind is not None and tk[0] != kind):
            raise self.err(f"expected {val or kind}")
        self.i += 1
        return tk

    def accept(self, val):
        if self.peek()[1] == val:
            self.i += 1
            return True
        return False

    def ident(self, allow_kw=False):
        tk = self.take(kind="ident")
        if not _IDENT.match(tk[1]) or (not allow_kw and tk[1] in KEYWORDS):
            self.i -= 1
            raise self.err(f"invalid identifier {tk[1][:40]!r}")
        return tk[1]

    def loc(self):
        _, _, ln, c = self.peek()
        return Location(ln, c)

    # type expressions produce *unresolved* nodes: ("ref", name) placeholders
    def type_expr(self, depth=0):
        if depth > MAX_TYPE_DEPTH:
            raise self.err("type nesting too deep", "PK_INTEROP_SCHEMA_LIMIT")
        tk = self.take(kind="ident")
        n = tk[1]
        d = depth + 1
        if n in PRIMITIVES:
            return Prim(n)
        if n in ("list", "option"):
            self.take("<")
            e = self.type_expr(d)
            self.take(">")
            return ListT("list", e) if n == "list" else OptionT("option", e)
        if n == "result":
            ok = err = None
            if self.accept("<"):
                if not self.accept("_"):
                    if self.peek()[1] == "_":
                        self.i += 1
                    else:
                        ok = self.type_expr(d)
                if self.accept(","):
                    err = self.type_expr(d)
                self.take(">")
            return ResultT("result", ok, err)
        if n == "tuple":
            self.take("<")
            elems = [self.type_expr(d)]
            while self.accept(","):
                elems.append(self.type_expr(d))
                if len(elems) > MAX_TUPLE:
                    raise self.err("tuple too long", "PK_INTEROP_SCHEMA_LIMIT")
            self.take(">")
            return TupleT("tuple", tuple(elems))
        if n in ("own", "borrow"):
            self.take("<")
            r = self.ident()
            self.take(">")
            return HandleT(n, r)
        if n in ("future", "stream"):
            e = None
            if self.accept("<"):
                e = self.type_expr(d)
                self.take(">")
            return AsyncT(n, e)
        self.i -= 1
        return _Ref(self.ident())


@dataclass(frozen=True)
class _Ref(Type):
    def __init__(self, name):  # noqa: D401 - small placeholder
        object.__setattr__(self, "kind", "ref")
        object.__setattr__(self, "name", name)

    def canonical(self):  # pragma: no cover - never survives resolution
        return f"ref:{self.name}"


def load(text: str) -> list:
    """Parse, resolve and normalize a schema document; returns [Interface]."""
    if type(text) is not str:
        raise SchemaError("schema must be text")
    if len(text.encode("utf-8", "strict")) > MAX_SCHEMA_BYTES:
        raise SchemaError("schema too large", code="PK_INTEROP_SCHEMA_LIMIT")
    p = _Parser(text)
    package = version = None
    if p.accept("package"):
        ns = p.ident(allow_kw=True)
        p.take(":")
        nm = p.ident(allow_kw=True)
        package = f"{ns}:{nm}"
        if p.accept("@"):
            version = p.take(kind="semver")[1]
            if not re.match(r"\d+\.\d+\.\d+\Z", version):
                raise p.err("version must be MAJOR.MINOR.PATCH")
        p.take(";")
    out, names = [], set()
    while p.peek()[0] != "eof":
        p.take("interface")
        iname = p.ident()
        if iname in names:
            raise p.err(f"duplicate interface {iname}", "PK_INTEROP_SCHEMA_DUPLICATE")
        names.add(iname)
        out.append(_interface(p, package, version, iname))
    if not out:
        raise p.err("document declares no interface")
    return out


def load_interface(text: str, name: Optional[str] = None) -> Interface:
    ifs = load(text)
    if name is None:
        if len(ifs) != 1:
            raise SchemaError("document has several interfaces; name one",
                              code="PK_INTEROP_SCHEMA_DUPLICATE")
        return ifs[0]
    for i in ifs:
        if i.name == name:
            return i
    raise SchemaError(f"interface {name!r} not found", code="PK_INTEROP_SCHEMA_UNRESOLVED")


def _interface(p: _Parser, package, version, iname) -> Interface:
    p.take("{")
    raw, locs, resources, funcs = {}, {}, set(), {}

    def declare(name, loc):
        if name in raw or name in resources or name in funcs:
            raise SchemaError(f"duplicate declaration {name!r} at {loc.line}:{loc.column}",
                              code="PK_INTEROP_SCHEMA_DUPLICATE", path=[name])
        if len(raw) + len(resources) + len(funcs) >= MAX_DECLARATIONS:
            raise SchemaError("too many declarations", code="PK_INTEROP_SCHEMA_LIMIT")
        locs[name] = loc

    while not p.accept("}"):
        loc = p.loc()
        kw = p.peek()[1]
        if kw == "record":
            p.i += 1
            name = p.ident()
            declare(name, loc)
            p.take("{")
            fields = []
            while not p.accept("}"):
                fields.append((p.ident(), (p.take(":"), p.type_expr())[1]))
                if not p.accept(","):
                    p.take("}")
                    break
            if not fields or len(fields) > MAX_FIELDS:
                raise SchemaError(f"record {name} must have 1..{MAX_FIELDS} fields",
                                  code="PK_INTEROP_SCHEMA_LIMIT", path=[name])
            _no_dupes([f[0] for f in fields], f"field in {name}")
            raw[name] = ("record", tuple(fields))
        elif kw == "variant":
            p.i += 1
            name = p.ident()
            declare(name, loc)
            p.take("{")
            cases = []
            while not p.accept("}"):
                cn = p.ident()
                ct = None
                if p.accept("("):
                    ct = p.type_expr()
                    p.take(")")
                cases.append((cn, ct))
                if not p.accept(","):
                    p.take("}")
                    break
            if not cases or len(cases) > MAX_CASES:
                raise SchemaError(f"variant {name} must have 1..{MAX_CASES} cases",
                                  code="PK_INTEROP_SCHEMA_LIMIT", path=[name])
            _no_dupes([c[0] for c in cases], f"case in {name}")
            raw[name] = ("variant", tuple(cases))
        elif kw in ("enum", "flags"):
            p.i += 1
            name = p.ident()
            declare(name, loc)
            p.take("{")
            items = []
            while not p.accept("}"):
                items.append(p.ident())
                if not p.accept(","):
                    p.take("}")
                    break
            lim = MAX_CASES if kw == "enum" else MAX_FLAGS
            if (kw == "enum" and not items) or len(items) > lim:
                raise SchemaError(f"{kw} {name} has an illegal member count",
                                  code="PK_INTEROP_SCHEMA_LIMIT", path=[name])
            _no_dupes(items, f"member in {name}")
            raw[name] = (kw, tuple(items))
        elif kw == "resource":
            p.i += 1
            name = p.ident()
            declare(name, loc)
            p.take(";")
            resources.add(name)
        elif kw == "type":
            p.i += 1
            name = p.ident()
            declare(name, loc)
            p.take("=")
            raw[name] = ("alias", p.type_expr())
            p.take(";")
        else:
            name = p.ident()
            declare(name, loc)
            p.take(":")
            p.take("func")
            p.take("(")
            params = []
            while not p.accept(")"):
                params.append((p.ident(), (p.take(":"), p.type_expr())[1]))
                if not p.accept(","):
                    p.take(")")
                    break
            _no_dupes([x[0] for x in params], f"parameter in {name}")
            res = p.type_expr() if p.accept("->") else None
            p.take(";")
            funcs[name] = (tuple(params), res, loc)

    # ------------------------------------------------------------ resolution
    resolved: dict = {}
    visiting: list = []

    def res_type(t, depth=0):
        if depth > MAX_TYPE_DEPTH:
            raise SchemaError("type nesting too deep after resolution",
                              code="PK_INTEROP_SCHEMA_LIMIT")
        d = depth + 1
        if isinstance(t, _Ref):
            return res_named(t.name)
        if isinstance(t, Prim):
            return t
        if isinstance(t, ListT):
            return ListT("list", res_type(t.elem, d))
        if isinstance(t, OptionT):
            return OptionT("option", res_type(t.elem, d))
        if isinstance(t, ResultT):
            return ResultT("result", t.ok and res_type(t.ok, d), t.err and res_type(t.err, d))
        if isinstance(t, TupleT):
            return TupleT("tuple", tuple(res_type(e, d) for e in t.elems))
        if isinstance(t, HandleT):
            if t.resource not in resources:
                raise SchemaError(f"{t.kind}<{t.resource}> names no declared resource",
                                  code="PK_INTEROP_SCHEMA_UNRESOLVED", path=[t.resource])
            return t
        if isinstance(t, AsyncT):
            return AsyncT(t.kind, t.elem and res_type(t.elem, d))
        raise SchemaError("internal: unknown node")  # pragma: no cover

    def res_named(name):
        if name in resolved:
            return resolved[name]
        if name in resources:
            raise SchemaError(f"resource {name!r} must be used as own<{name}> or borrow<{name}>",
                              code="PK_INTEROP_SCHEMA_UNRESOLVED", path=[name])
        if name not in raw:
            raise SchemaError(f"unresolved type reference {name!r}",
                              code="PK_INTEROP_SCHEMA_UNRESOLVED", path=[name])
        if name in visiting:
            cycle = visiting[visiting.index(name):] + [name]
            raise SchemaError("recursive type " + " -> ".join(cycle),
                              code="PK_INTEROP_SCHEMA_RECURSIVE", path=[name])
        visiting.append(name)
        kind, body = raw[name]
        if kind == "record":
            t = RecordT("record", name, tuple((f, res_type(ft)) for f, ft in body))
        elif kind == "variant":
            t = VariantT("variant", name, tuple((c, ct and res_type(ct)) for c, ct in body))
        elif kind == "enum":
            t = EnumT("enum", name, body)
        elif kind == "flags":
            t = FlagsT("flags", name, body)
        else:
            t = res_type(body)
        visiting.pop()
        resolved[name] = t
        return t

    for n in raw:
        res_named(n)
    functions = {}
    for n, (params, res, loc) in funcs.items():
        functions[n] = Function(n, tuple((pn, res_type(pt)) for pn, pt in params),
                                res and res_type(res), loc)
    return Interface(package, version, iname, dict(resolved), frozenset(resources),
                     functions, dict(locs))


def parse_type(text: str, interface: Optional[Interface] = None) -> Type:
    """Parse a standalone type expression, resolving names against *interface*."""
    p = _Parser(text)
    t = p.type_expr()
    if p.peek()[0] != "eof":
        raise p.err("trailing input after type")

    def res(x, depth=0):
        if depth > MAX_TYPE_DEPTH:
            raise SchemaError("too deep", code="PK_INTEROP_SCHEMA_LIMIT")
        d = depth + 1
        if isinstance(x, _Ref):
            if interface is None:
                raise SchemaError(f"unresolved type reference {x.name!r}",
                                  code="PK_INTEROP_SCHEMA_UNRESOLVED")
            return interface.type(x.name)
        if isinstance(x, ListT):
            return ListT("list", res(x.elem, d))
        if isinstance(x, OptionT):
            return OptionT("option", res(x.elem, d))
        if isinstance(x, ResultT):
            return ResultT("result", x.ok and res(x.ok, d), x.err and res(x.err, d))
        if isinstance(x, TupleT):
            return TupleT("tuple", tuple(res(e, d) for e in x.elems))
        if isinstance(x, HandleT) and interface is not None and x.resource not in interface.resources:
            raise SchemaError("unknown resource", code="PK_INTEROP_SCHEMA_UNRESOLVED")
        if isinstance(x, AsyncT):
            return AsyncT(x.kind, x.elem and res(x.elem, d))
        return x
    return res(t)


def to_json(iface: Interface) -> str:
    """Deterministic JSON serialization of a loaded interface (golden-able)."""
    doc = {
        "package": iface.package, "version": iface.version, "interface": iface.name,
        "resources": sorted(iface.resources),
        "types": {n: descriptor(iface.types[n]) for n in sorted(iface.types)},
        "functions": {n: {"params": [[pn, descriptor(pt)] for pn, pt in f.params],
                          "result": descriptor(f.result) if f.result else None}
                      for n, f in sorted(iface.functions.items())},
        "digest": iface.digest(),
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
