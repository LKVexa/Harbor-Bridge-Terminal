"""M04 - WIT source model: a bounded parser for the WIT subset INV-61 carries.

Supported: ``package ns:name@ver;``, ``interface``, ``func``, ``record``, ``enum``,
``variant``, ``type`` aliases, primitive types, ``list``, ``option``, ``result``
and ``tuple``. Resources, flags, streams/futures, ``use`` and ``world`` are
rejected with a stable error rather than silently ignored (see SUPPORT_MATRIX.md).

The canonical signature string of a function is the fully-resolved type text of
its params and results; it feeds ``rpc.fingerprint`` so both sides fingerprint
the *resolved* shape, not the author's spelling of aliases.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

PRIMITIVES = frozenset(
    "bool u8 u16 u32 u64 s8 s16 s32 s64 f32 f64 char string".split()
)
MAX_SOURCE = 256 * 1024
MAX_TYPE_DEPTH = 32
_TOKEN = re.compile(r"\s*(?:(//[^\n]*)|([A-Za-z_%][A-Za-z0-9_\-]*(?::[A-Za-z0-9_\-]+)?(?:@[0-9A-Za-z.\-+]+)?)|(->|[{}()<>,:;=]))")
UNSUPPORTED = frozenset({"resource", "flags", "stream", "future", "use", "world", "own", "borrow"})


class WitError(ValueError):
    """Stable, position-bearing parse error."""


@dataclass(frozen=True)
class T:
    """A resolved WIT type. ``kind`` is a primitive name or a constructor."""

    kind: str
    args: tuple = ()          # element types / (ok, err) / tuple members
    fields: tuple = ()        # record: ((name, T), ...); variant: ((case, T|None), ...); enum: ((case, None), ...)
    name: str = ""            # declared name for record/enum/variant

    def text(self) -> str:
        if self.kind in PRIMITIVES:
            return self.kind
        if self.kind in ("list", "option"):
            return f"{self.kind}<{self.args[0].text()}>"
        if self.kind == "result":
            ok, err = self.args
            return f"result<{ok.text() if ok else '_'},{err.text() if err else '_'}>"
        if self.kind == "tuple":
            return "tuple<" + ",".join(a.text() for a in self.args) + ">"
        if self.kind == "record":
            return "record{" + ",".join(f"{n}:{t.text()}" for n, t in self.fields) + "}"
        if self.kind == "enum":
            return "enum{" + ",".join(n for n, _ in self.fields) + "}"
        if self.kind == "variant":
            return "variant{" + ",".join(n + (f"({t.text()})" if t else "") for n, t in self.fields) + "}"
        raise WitError(f"unknown kind {self.kind}")


@dataclass
class Func:
    name: str
    params: list  # [(name, T)]
    results: list  # [T]

    def param_texts(self) -> list[str]:
        return [t.text() for _, t in self.params]

    def result_texts(self) -> list[str]:
        return [t.text() for t in self.results]


@dataclass
class Interface:
    name: str
    functions: dict = field(default_factory=dict)
    types: dict = field(default_factory=dict)


@dataclass
class Package:
    namespace: str
    name: str
    version: str
    interfaces: dict = field(default_factory=dict)


def _tokens(src: str) -> list[tuple[str, int]]:
    if len(src) > MAX_SOURCE:
        raise WitError("source-too-large")
    out, pos = [], 0
    while pos < len(src):
        if src[pos:].strip() == "":
            break
        m = _TOKEN.match(src, pos)
        if not m or m.end() == pos:
            raise WitError(f"unexpected character at {pos}")
        pos = m.end()
        if m.group(1):
            continue
        out.append((m.group(2) or m.group(3), m.start()))
    return out


class _Parser:
    def __init__(self, src: str):
        self.toks = _tokens(src)
        self.i = 0

    def peek(self):
        return self.toks[self.i][0] if self.i < len(self.toks) else None

    def take(self, expect: str | None = None) -> str:
        if self.i >= len(self.toks):
            raise WitError(f"unexpected end, expected {expect or 'token'}")
        tok, pos = self.toks[self.i]
        if expect is not None and tok != expect:
            raise WitError(f"expected {expect!r} at {pos}, got {tok!r}")
        self.i += 1
        return tok

    def ident(self) -> str:
        tok = self.take()
        if not re.fullmatch(r"%?[a-z][a-z0-9]*(-[a-z0-9]+)*", tok):
            raise WitError(f"bad identifier {tok!r}")
        if tok in UNSUPPORTED:
            raise WitError(f"unsupported-construct:{tok}")
        return tok.lstrip("%")

    def type_(self, scope: dict, depth: int = 0) -> T:
        if depth > MAX_TYPE_DEPTH:
            raise WitError("type-too-deep")
        tok = self.take()
        if tok in UNSUPPORTED:
            raise WitError(f"unsupported-construct:{tok}")
        if tok in PRIMITIVES:
            return T(tok)
        if tok in ("list", "option"):
            self.take("<")
            inner = self.type_(scope, depth + 1)
            self.take(">")
            return T(tok, (inner,))
        if tok == "tuple":
            self.take("<")
            members = [self.type_(scope, depth + 1)]
            while self.peek() == ",":
                self.take(",")
                members.append(self.type_(scope, depth + 1))
            self.take(">")
            return T("tuple", tuple(members))
        if tok == "result":
            if self.peek() != "<":
                return T("result", (None, None))
            self.take("<")
            ok = None if self.peek() == "_" else self.type_(scope, depth + 1)
            if ok is None:
                self.take("_")
            err = None
            if self.peek() == ",":
                self.take(",")
                err = self.type_(scope, depth + 1)
            self.take(">")
            return T("result", (ok, err))
        if tok in scope:
            return scope[tok]
        raise WitError(f"undefined-type:{tok}")

    def interface(self) -> Interface:
        name = self.ident()
        iface = Interface(name)
        self.take("{")
        while self.peek() != "}":
            kw = self.take()
            if kw in UNSUPPORTED:
                raise WitError(f"unsupported-construct:{kw}")
            if kw == "record":
                rname = self.ident()
                self.take("{")
                fields = []
                while self.peek() != "}":
                    fname = self.ident()
                    self.take(":")
                    fields.append((fname, self.type_(iface.types)))
                    if self.peek() == ",":
                        self.take(",")
                self.take("}")
                self._define(iface, rname, T("record", fields=tuple(fields), name=rname))
            elif kw in ("enum", "variant"):
                rname = self.ident()
                self.take("{")
                cases = []
                while self.peek() != "}":
                    cname = self.ident()
                    payload = None
                    if kw == "variant" and self.peek() == "(":
                        self.take("(")
                        payload = self.type_(iface.types)
                        self.take(")")
                    cases.append((cname, payload))
                    if self.peek() == ",":
                        self.take(",")
                self.take("}")
                if not cases or len({c for c, _ in cases}) != len(cases):
                    raise WitError(f"bad-cases:{rname}")
                self._define(iface, rname, T(kw, fields=tuple(cases), name=rname))
            elif kw == "type":
                alias = self.ident()
                self.take("=")
                self._define(iface, alias, self.type_(iface.types))
                self.take(";")
            else:
                # function: <name> : func(params) -> results ;
                fname = kw
                if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", fname):
                    raise WitError(f"bad identifier {fname!r}")
                self.take(":")
                self.take("func")
                self.take("(")
                params = []
                while self.peek() != ")":
                    pname = self.ident()
                    self.take(":")
                    params.append((pname, self.type_(iface.types)))
                    if self.peek() == ",":
                        self.take(",")
                self.take(")")
                results = []
                if self.peek() == "->":
                    self.take("->")
                    results.append(self.type_(iface.types))
                self.take(";")
                if fname in iface.functions:
                    raise WitError(f"duplicate-function:{fname}")
                iface.functions[fname] = Func(fname, params, results)
                continue
            if self.peek() == ";":
                self.take(";")
        self.take("}")
        return iface

    @staticmethod
    def _define(iface: Interface, name: str, t: T) -> None:
        if name in iface.types or name in PRIMITIVES:
            raise WitError(f"duplicate-type:{name}")
        iface.types[name] = t


def parse(src: str) -> Package:
    """Parse a WIT package. Raises :class:`WitError` with a stable reason."""
    p = _Parser(src)
    p.take("package")
    ref = p.take()
    m = re.fullmatch(r"([a-z][a-z0-9\-]*):([a-z][a-z0-9\-]*)@([0-9]+\.[0-9]+\.[0-9]+[0-9A-Za-z.\-+]*)", ref)
    if not m:
        raise WitError("package reference must be ns:name@semver")
    p.take(";")
    pkg = Package(*m.groups())
    while p.peek() is not None:
        kw = p.take()
        if kw != "interface":
            raise WitError(f"unsupported-construct:{kw}" if kw in UNSUPPORTED else f"unexpected {kw!r}")
        iface = p.interface()
        if iface.name in pkg.interfaces:
            raise WitError(f"duplicate-interface:{iface.name}")
        pkg.interfaces[iface.name] = iface
    return pkg


def qualified(pkg: Package, iface: str) -> str:
    return f"{pkg.namespace}:{pkg.name}/{iface}"
