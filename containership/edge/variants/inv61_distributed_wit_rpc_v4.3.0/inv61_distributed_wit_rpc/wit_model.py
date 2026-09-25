"""M04 - WIT source model: a strict parser for the WIT subset INV-61 supports.

Supported (pinned target: WIT text format of the WebAssembly Component Model,
subset documented in docs/WIT_SUBSET.md):

    package ns:name@X.Y.Z;
    interface <name> {
        record <name> { field: type, ... }
        enum <name> { a, b, ... }
        <fn>: func(p: type, ...) -> type;
    }

Types: bool u8 u16 u32 u64 s8 s16 s32 s64 f32 f64 char string
       list<T> option<T> result<T, E> result<_, E> result<T> tuple<T, ...>
       and locally declared record / enum names.

Anything else (resources, flags, variants, use/import, worlds) is rejected with
a WitError rather than silently ignored.  The parser is pure and deterministic;
``Interface.digest`` is a normalized SHA-256 used for compatibility checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any

WIT_SUBSET_VERSION = "inv61-wit-subset/1"
SCALARS = frozenset("bool u8 u16 u32 u64 s8 s16 s32 s64 f32 f64 char string".split())
_IDENT = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_TOKEN = re.compile(r"\s*(->|[A-Za-z_][A-Za-z0-9_\-]*|@[0-9A-Za-z.\-+]+|[{}()<>,:;=]|\S)")
MAX_NESTING = 16


class WitError(ValueError):
    """Raised for any WIT source the INV-61 subset does not accept."""


@dataclass(frozen=True)
class Func:
    name: str
    params: tuple[tuple[str, Any], ...]
    result: Any  # type tree or None

    def param_types(self) -> list[str]:
        return [type_str(t) for _, t in self.params]

    def result_types(self) -> list[str]:
        return [] if self.result is None else [type_str(self.result)]


@dataclass
class Interface:
    package: str
    version: str
    name: str
    records: dict[str, tuple[tuple[str, Any], ...]] = field(default_factory=dict)
    enums: dict[str, tuple[str, ...]] = field(default_factory=dict)
    funcs: dict[str, Func] = field(default_factory=dict)

    @property
    def qualified(self) -> str:
        return f"{self.package}/{self.name}"

    def normalized(self) -> dict[str, Any]:
        return {
            "subset": WIT_SUBSET_VERSION,
            "package": self.package,
            "version": self.version,
            "interface": self.name,
            "records": {k: [[n, type_str(t)] for n, t in v] for k, v in sorted(self.records.items())},
            "enums": {k: list(v) for k, v in sorted(self.enums.items())},
            "funcs": {k: {"params": [[n, type_str(t)] for n, t in f.params],
                          "result": None if f.result is None else type_str(f.result)}
                      for k, f in sorted(self.funcs.items())},
        }

    @property
    def digest(self) -> str:
        blob = json.dumps(self.normalized(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def resolve(self, t: Any) -> Any:
        """Expand record/enum names into structural type trees for the codec."""
        return _resolve(t, self, 0)


def type_str(t: Any) -> str:
    if isinstance(t, str):
        return t
    kind = t[0]
    if kind in ("list", "option"):
        return f"{kind}<{type_str(t[1])}>"
    if kind == "result":
        ok = "_" if t[1] is None else type_str(t[1])
        err = "_" if t[2] is None else type_str(t[2])
        return f"result<{ok}, {err}>"
    if kind == "tuple":
        return "tuple<" + ", ".join(type_str(x) for x in t[1]) + ">"
    if kind == "ref":
        return t[1]
    raise WitError(f"unknown type node {kind}")


def _resolve(t: Any, iface: Interface, depth: int) -> Any:
    if depth > MAX_NESTING:
        raise WitError("type nesting too deep")
    if isinstance(t, str):
        return t
    kind = t[0]
    if kind in ("list", "option"):
        return (kind, _resolve(t[1], iface, depth + 1))
    if kind == "result":
        return ("result",
                None if t[1] is None else _resolve(t[1], iface, depth + 1),
                None if t[2] is None else _resolve(t[2], iface, depth + 1))
    if kind == "tuple":
        return ("tuple", tuple(_resolve(x, iface, depth + 1) for x in t[1]))
    if kind == "ref":
        name = t[1]
        if name in iface.records:
            return ("record", tuple((n, _resolve(ft, iface, depth + 1)) for n, ft in iface.records[name]))
        if name in iface.enums:
            return ("enum", iface.enums[name])
        raise WitError(f"unresolved type: {name}")
    raise WitError(f"unknown type node {kind}")


class _P:
    def __init__(self, src: str):
        src = re.sub(r"//[^\n]*", "", src)
        self.toks: list[str] = []
        pos = 0
        while pos < len(src):
            m = _TOKEN.match(src, pos)
            if not m or not m.group(1):
                if src[pos:].strip() == "":
                    break
                raise WitError(f"unexpected character at offset {pos}")
            self.toks.append(m.group(1))
            pos = m.end()
        self.i = 0

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self) -> str:
        if self.i >= len(self.toks):
            raise WitError("unexpected end of input")
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, tok: str) -> None:
        got = self.next()
        if got != tok:
            raise WitError(f"expected {tok!r}, got {got!r}")

    def ident(self) -> str:
        tok = self.next()
        if not _IDENT.match(tok):
            raise WitError(f"invalid identifier {tok!r}")
        return tok

    def type(self, depth: int = 0) -> Any:
        if depth > MAX_NESTING:
            raise WitError("type nesting too deep")
        tok = self.next()
        if tok in SCALARS:
            return tok
        if tok in ("list", "option"):
            self.expect("<")
            inner = self.type(depth + 1)
            self.expect(">")
            return (tok, inner)
        if tok == "result":
            if self.peek() != "<":
                return ("result", None, None)
            self.expect("<")
            ok = None if self.peek() == "_" and self.next() else self.type(depth + 1)
            err = None
            if self.peek() == ",":
                self.next()
                err = self.type(depth + 1)
            self.expect(">")
            return ("result", ok, err)
        if tok == "tuple":
            self.expect("<")
            items = [self.type(depth + 1)]
            while self.peek() == ",":
                self.next()
                items.append(self.type(depth + 1))
            self.expect(">")
            return ("tuple", tuple(items))
        if tok in ("resource", "flags", "variant", "borrow", "own", "stream", "future"):
            raise WitError(f"unsupported WIT construct in INV-61 subset: {tok}")
        if _IDENT.match(tok):
            return ("ref", tok)
        raise WitError(f"invalid type token {tok!r}")


def parse(src: str) -> list[Interface]:
    """Parse WIT source into interfaces; raises WitError on any defect."""
    p = _P(src)
    if p.next() != "package":
        raise WitError("source must begin with a package declaration")
    ns = p.ident()
    p.expect(":")
    pkg = p.ident()
    ver_tok = p.next()
    if not re.fullmatch(r"@\d+\.\d+\.\d+", ver_tok):
        raise WitError("package must carry an exact @X.Y.Z version")
    p.expect(";")
    package, version = f"{ns}:{pkg}", ver_tok[1:]
    out: list[Interface] = []
    names: set[str] = set()
    while p.peek() is not None:
        kw = p.next()
        if kw != "interface":
            raise WitError(f"unsupported top-level item: {kw}")
        iface = Interface(package, version, p.ident())
        if iface.name in names:
            raise WitError(f"duplicate interface {iface.name}")
        names.add(iface.name)
        p.expect("{")
        seen: set[str] = set()
        while p.peek() != "}":
            head = p.next()
            if head == "record":
                name = p.ident()
                _dup(seen, name)
                p.expect("{")
                fields: list[tuple[str, Any]] = []
                while p.peek() != "}":
                    fname = p.ident()
                    if fname in {f for f, _ in fields}:
                        raise WitError(f"duplicate field {fname}")
                    p.expect(":")
                    fields.append((fname, p.type()))
                    if p.peek() == ",":
                        p.next()
                p.expect("}")
                if not fields:
                    raise WitError("empty record")
                iface.records[name] = tuple(fields)
            elif head == "enum":
                name = p.ident()
                _dup(seen, name)
                p.expect("{")
                cases: list[str] = []
                while p.peek() != "}":
                    c = p.ident()
                    if c in cases:
                        raise WitError(f"duplicate enum case {c}")
                    cases.append(c)
                    if p.peek() == ",":
                        p.next()
                p.expect("}")
                if not cases:
                    raise WitError("empty enum")
                iface.enums[name] = tuple(cases)
            elif _IDENT.match(head):
                _dup(seen, head)
                p.expect(":")
                p.expect("func")
                p.expect("(")
                params: list[tuple[str, Any]] = []
                while p.peek() != ")":
                    pname = p.ident()
                    if pname in {n for n, _ in params}:
                        raise WitError(f"duplicate parameter {pname}")
                    p.expect(":")
                    params.append((pname, p.type()))
                    if p.peek() == ",":
                        p.next()
                p.expect(")")
                result = None
                if p.peek() == "->":
                    p.next()
                    result = p.type()
                p.expect(";")
                iface.funcs[head] = Func(head, tuple(params), result)
            else:
                raise WitError(f"unexpected token {head!r} in interface body")
        p.expect("}")
        # every reference must resolve
        for f in iface.funcs.values():
            for _, t in f.params:
                iface.resolve(t)
            if f.result is not None:
                iface.resolve(f.result)
        for flds in iface.records.values():
            for _, t in flds:
                iface.resolve(t)
        out.append(iface)
    if not out:
        raise WitError("package declares no interfaces")
    return out


def _dup(seen: set[str], name: str) -> None:
    if name in seen:
        raise WitError(f"duplicate definition {name}")
    seen.add(name)
