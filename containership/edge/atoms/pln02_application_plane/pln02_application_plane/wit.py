"""MC-10 - WIT subset parser and semantic interface compatibility checker.

Supported WIT subset (Component Model WIT, text form)::

    package ns:name@MAJOR.MINOR.PATCH;
    interface <id> { <items> }
    world <id> { import <id>; export <id>; }
    items: record R { f: T, ... }   enum E { a, b }   variant V { a, b(T) }
           flags F { a, b }         type A = T;       f: func(p: T, ...) -> T;
    types: bool s8 s16 s32 s64 u8 u16 u32 u64 f32 f64 char string
           list<T> option<T> result<T, E> result<T> result<_, E> result tuple<T, ...> <named>

Not supported (refused with ``WIT_INVALID``): ``resource``, ``use``, ``include``,
nested packages, gates/attributes (``@since`` etc.), borrow/own handles.

Compatibility (producer P satisfies consumer C for interface I):

* package names equal; semver: same MAJOR (for 0.x same MINOR), P >= C;
* every function in C exists in P with a structurally identical signature
  after resolving type aliases (P may add functions - additive evolution);
* named types are compared structurally, not by name only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .errors import PlaneError

MAX_SOURCE_BYTES = 256 * 1024
MAX_TYPE_DEPTH = 32
MAX_ITEMS = 2048
PRIMITIVES = {"bool", "s8", "s16", "s32", "s64", "u8", "u16", "u32", "u64", "f32", "f64", "char", "string"}
UNSUPPORTED = {"resource", "use", "include", "borrow", "own", "static", "constructor"}
_TOKEN = re.compile(r"\s+|//[^\n]*|(?P<tok>%?[a-z][a-z0-9\-]*|[0-9]+(?:\.[0-9]+){2}|->|[{}()<>,:;=@./_*])")
_ID = re.compile(r"^%?[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def _bad(line: int, reason: str) -> PlaneError:
    return PlaneError(f"WIT line {line}: {reason}", code="WIT_INVALID", details={"line": line, "reason": reason})


@dataclass
class Interface:
    name: str
    types: dict[str, Any] = field(default_factory=dict)
    funcs: dict[str, Any] = field(default_factory=dict)


@dataclass
class Package:
    namespace: str
    name: str
    version: tuple[int, int, int]
    interfaces: dict[str, Interface] = field(default_factory=dict)
    worlds: dict[str, dict[str, list[str]]] = field(default_factory=dict)


class _Parser:
    def __init__(self, src: str) -> None:
        if len(src.encode()) > MAX_SOURCE_BYTES:
            raise _bad(0, "source too large")
        self.toks: list[tuple[str, int]] = []
        pos, line = 0, 1
        while pos < len(src):
            m = _TOKEN.match(src, pos)
            if not m:
                raise _bad(line, f"unexpected character {src[pos]!r}")
            if m.group("tok"):
                self.toks.append((m.group("tok"), line))
            line += src.count("\n", pos, m.end())
            pos = m.end()
        self.i = 0

    def peek(self) -> str | None:
        return self.toks[self.i][0] if self.i < len(self.toks) else None

    def line(self) -> int:
        return self.toks[min(self.i, len(self.toks) - 1)][1] if self.toks else 0

    def take(self, expect: str | None = None) -> str:
        if self.i >= len(self.toks):
            raise _bad(self.line(), "unexpected end of input")
        tok = self.toks[self.i][0]
        if expect is not None and tok != expect:
            raise _bad(self.line(), f"expected {expect!r}, got {tok!r}")
        if tok in UNSUPPORTED:
            raise _bad(self.line(), f"unsupported WIT feature {tok!r}")
        self.i += 1
        return tok

    def ident(self) -> str:
        tok = self.take()
        if not _ID.fullmatch(tok):
            raise _bad(self.line(), f"bad identifier {tok!r}")
        return tok.lstrip("%")

    def type_(self, depth: int = 0) -> Any:
        if depth > MAX_TYPE_DEPTH:
            raise _bad(self.line(), "type nesting too deep")
        t = self.take()
        if t in PRIMITIVES:
            return t
        if t in {"list", "option"}:
            self.take("<"); inner = self.type_(depth + 1); self.take(">")
            return (t, inner)
        if t == "tuple":
            self.take("<"); items = [self.type_(depth + 1)]
            while self.peek() == ",":
                self.take(","); items.append(self.type_(depth + 1))
            self.take(">")
            return ("tuple", tuple(items))
        if t == "result":
            if self.peek() != "<":
                return ("result", None, None)
            self.take("<")
            ok = None if self.peek() == "_" and self.take("_") else self.type_(depth + 1)
            err = None
            if self.peek() == ",":
                self.take(","); err = self.type_(depth + 1)
            self.take(">")
            return ("result", ok, err)
        if not _ID.fullmatch(t):
            raise _bad(self.line(), f"bad type {t!r}")
        return ("ref", t.lstrip("%"))

    def package(self) -> Package:
        self.take("package")
        ns = self.ident(); self.take(":"); name = self.ident(); self.take("@")
        ver = self.take()
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", ver):
            raise _bad(self.line(), "package version must be MAJOR.MINOR.PATCH")
        self.take(";")
        pkg = Package(ns, name, tuple(int(x) for x in ver.split(".")))  # type: ignore[arg-type]
        items = 0
        while self.peek() is not None:
            kw = self.take()
            if kw == "interface":
                iface = self.interface()
                if iface.name in pkg.interfaces:
                    raise _bad(self.line(), f"duplicate interface {iface.name}")
                pkg.interfaces[iface.name] = iface
            elif kw == "world":
                wname = self.ident(); self.take("{")
                w: dict[str, list[str]] = {"import": [], "export": []}
                while self.peek() != "}":
                    d = self.take()
                    if d not in w:
                        raise _bad(self.line(), "world items must be import/export <interface>;")
                    w[d].append(self.ident()); self.take(";")
                self.take("}")
                pkg.worlds[wname] = w
            else:
                raise _bad(self.line(), f"unexpected top-level {kw!r}")
            items += 1
            if items > MAX_ITEMS:
                raise _bad(self.line(), "too many items")
        for wname, w in pkg.worlds.items():
            for ref in w["import"] + w["export"]:
                if ref not in pkg.interfaces:
                    raise _bad(0, f"world {wname} references unknown interface {ref}")
        return pkg

    def interface(self) -> Interface:
        iface = Interface(self.ident()); self.take("{")
        count = 0
        while self.peek() != "}":
            count += 1
            if count > MAX_ITEMS:
                raise _bad(self.line(), "too many interface items")
            kw = self.peek()
            if kw in {"record", "enum", "variant", "flags", "type"}:
                self.take()
                tname = self.ident()
                if tname in iface.types or tname in iface.funcs:
                    raise _bad(self.line(), f"duplicate name {tname}")
                if kw == "type":
                    self.take("="); iface.types[tname] = ("alias", self.type_()); self.take(";")
                    continue
                self.take("{")
                members: list[Any] = []
                while self.peek() != "}":
                    m = self.ident()
                    if kw == "record":
                        self.take(":"); members.append((m, self.type_()))
                    elif kw == "variant" and self.peek() == "(":
                        self.take("("); members.append((m, self.type_())); self.take(")")
                    else:
                        members.append((m, None))
                    if self.peek() == ",":
                        self.take(",")
                    elif self.peek() != "}":
                        raise _bad(self.line(), "expected ',' or '}'")
                self.take("}")
                names = [m[0] for m in members]
                if len(set(names)) != len(names):
                    raise _bad(self.line(), f"duplicate member in {tname}")
                iface.types[tname] = (kw, tuple(members))
            else:
                fname = self.ident(); self.take(":"); self.take("func"); self.take("(")
                params: list[tuple[str, Any]] = []
                while self.peek() != ")":
                    pn = self.ident(); self.take(":"); params.append((pn, self.type_()))
                    if self.peek() == ",":
                        self.take(",")
                self.take(")")
                result = None
                if self.peek() == "->":
                    self.take("->"); result = self.type_()
                self.take(";")
                if fname in iface.funcs or fname in iface.types:
                    raise _bad(self.line(), f"duplicate name {fname}")
                iface.funcs[fname] = (tuple(params), result)
        self.take("}")
        # every referenced named type must be defined in the interface
        for f, (params, res) in iface.funcs.items():
            for t in [p[1] for p in params] + [res]:
                _expand(t, iface, 0)
        for tname, t in iface.types.items():
            _expand(("ref", tname), iface, 0)
        return iface


def _expand(t: Any, iface: Interface, depth: int, stack: tuple[str, ...] = ()) -> Any:
    """Resolve refs/aliases into a structural form (detects cycles and undefined refs)."""
    if depth > MAX_TYPE_DEPTH:
        raise _bad(0, "type expansion too deep")
    if t is None or isinstance(t, str):
        return t
    kind = t[0]
    if kind == "ref":
        name = t[1]
        if name in stack:
            raise _bad(0, f"recursive type {name}")
        if name not in iface.types:
            raise _bad(0, f"undefined type {name} in interface {iface.name}")
        return _expand(iface.types[name], iface, depth + 1, stack + (name,))
    if kind == "alias":
        return _expand(t[1], iface, depth + 1, stack)
    if kind in {"list", "option"}:
        return (kind, _expand(t[1], iface, depth + 1, stack))
    if kind == "tuple":
        return ("tuple", tuple(_expand(x, iface, depth + 1, stack) for x in t[1]))
    if kind == "result":
        return ("result", _expand(t[1], iface, depth + 1, stack), _expand(t[2], iface, depth + 1, stack))
    if kind in {"record", "variant"}:
        return (kind, tuple((m, _expand(mt, iface, depth + 1, stack)) for m, mt in t[1]))
    if kind in {"enum", "flags"}:
        return (kind, tuple(m for m, _ in t[1]))
    raise _bad(0, f"unknown type form {kind}")


def parse(src: str) -> Package:
    if not isinstance(src, str):
        raise _bad(0, "source must be text")
    return _Parser(src).package()


def check_compatible(producer: Package, consumer: Package, interface: str) -> None:
    """Raise ``INCOMPATIBLE_INTERFACE`` unless ``producer`` satisfies ``consumer``'s ``interface``."""
    def incompatible(reason: str) -> PlaneError:
        return PlaneError(f"{interface}: {reason}", code="INCOMPATIBLE_INTERFACE",
                          details={"interface": interface, "reason": reason})
    if (producer.namespace, producer.name) != (consumer.namespace, consumer.name):
        raise incompatible("package mismatch")
    pv, cv = producer.version, consumer.version
    if pv[0] != cv[0] or (pv[0] == 0 and pv[1] != cv[1]) or pv < cv:
        raise incompatible(f"version {'.'.join(map(str, pv))} does not satisfy {'.'.join(map(str, cv))}")
    if interface not in consumer.interfaces:
        raise incompatible("consumer does not declare interface")
    if interface not in producer.interfaces:
        raise incompatible("producer does not export interface")
    pi, ci = producer.interfaces[interface], consumer.interfaces[interface]
    for fname, (cparams, cres) in ci.funcs.items():
        if fname not in pi.funcs:
            raise incompatible(f"missing function {fname}")
        pparams, pres = pi.funcs[fname]
        if len(pparams) != len(cparams):
            raise incompatible(f"arity mismatch in {fname}")
        for (pn, pt), (cn, ct) in zip(pparams, cparams):
            if _expand(pt, pi, 0) != _expand(ct, ci, 0):
                raise incompatible(f"parameter {cn} of {fname} type mismatch")
        if _expand(pres, pi, 0) != _expand(cres, ci, 0):
            raise incompatible(f"result of {fname} type mismatch")


def interface_version(pkg: Package, interface: str) -> str:
    """Stable version string for use in PK_APPLICATION/1 exports/imports."""
    if interface not in pkg.interfaces:
        raise _bad(0, f"unknown interface {interface}")
    return f"{pkg.namespace}:{pkg.name}@{'.'.join(map(str, pkg.version))}"
