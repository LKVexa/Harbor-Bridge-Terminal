"""MC-06: WebAssembly Component Model / WIT world integration.

A bounded, dependency-free parser for the WIT subset INV-10 needs to link:
``package ns:pkg@ver;``, ``interface name { ... }`` (functions / resources /
types are recorded, bodies are brace-balanced), and ``world name { import x;
export y; }``. Each world becomes a :class:`Unit` whose imports/exports are
fully qualified ``ns:pkg/iface@ver`` identifiers. It does not validate core
Wasm binaries or canonical-ABI lowering — that stays with INV-09 — and a
world referencing an interface that is neither local nor fully qualified is
refused rather than guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .composition import Unit
from .errors import WitParseError

MAX_WIT_BYTES = 1 << 20
_TOKEN = re.compile(r"//[^\n]*|/\*.*?\*/|[A-Za-z_%][\w\-:/.@%]*|[{};,()<>=\-]|\S", re.S)
_IDENT = re.compile(r"^%?[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_QUALIFIED = re.compile(r"^[a-z][a-z0-9\-]*:[a-z][a-z0-9\-]*(/[a-z][a-z0-9\-]*)?(@[0-9]+\.[0-9]+\.[0-9]+[\w.\-+]*)?$")


@dataclass
class WitInterface:
    name: str
    functions: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)


@dataclass
class WitWorld:
    name: str
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)


@dataclass
class WitPackage:
    namespace: str
    package: str
    version: str | None
    interfaces: dict[str, WitInterface] = field(default_factory=dict)
    worlds: dict[str, WitWorld] = field(default_factory=dict)

    def qualify(self, ref: str) -> str:
        if _QUALIFIED.match(ref) and "/" in ref:
            return ref
        if ref in self.interfaces:
            base = f"{self.namespace}:{self.package}/{ref}"
            return f"{base}@{self.version}" if self.version else base
        raise WitParseError(f"unresolved interface reference {ref!r}", reference=ref)

    def to_unit(self, world: str, *, component_name: str | None = None) -> Unit:
        if world not in self.worlds:
            raise WitParseError(f"unknown world {world!r}", world=world)
        w = self.worlds[world]
        return Unit(
            component_name or f"{self.namespace}:{self.package}/{world}",
            frozenset(self.qualify(r) for r in w.imports),
            frozenset(self.qualify(r) for r in w.exports),
        )


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text) if not t.startswith(("//", "/*"))]


def parse(text: str) -> WitPackage:
    if not isinstance(text, str):
        raise WitParseError("WIT source must be str")
    if len(text.encode("utf-8")) > MAX_WIT_BYTES:
        raise WitParseError("WIT source exceeds size limit", limit=MAX_WIT_BYTES)
    toks = _tokens(text)
    i = 0

    def expect(value: str) -> None:
        nonlocal i
        if i >= len(toks) or toks[i] != value:
            raise WitParseError(f"expected {value!r}", position=i, found=toks[i] if i < len(toks) else None)
        i += 1

    def take() -> str:
        nonlocal i
        if i >= len(toks):
            raise WitParseError("unexpected end of input")
        i += 1
        return toks[i - 1]

    if not toks or toks[0] != "package":
        raise WitParseError("WIT document must start with a package declaration")
    i = 1
    pkg_ref = take()
    expect(";")
    m = re.match(r"^([a-z][a-z0-9\-]*):([a-z][a-z0-9\-]*)(?:@(\S+))?$", pkg_ref)
    if not m:
        raise WitParseError("invalid package name", package=pkg_ref)
    pkg = WitPackage(m.group(1), m.group(2), m.group(3))

    def skip_block() -> None:
        depth = 0
        nonlocal i
        while i < len(toks):
            t = take()
            if t == "{":
                depth += 1
            elif t == "}":
                depth -= 1
                if depth == 0:
                    return
        raise WitParseError("unbalanced braces")

    while i < len(toks):
        kw = take()
        if kw == "interface":
            name = take()
            if not _IDENT.match(name):
                raise WitParseError("invalid interface name", name=name)
            if name in pkg.interfaces:
                raise WitParseError("duplicate interface", name=name)
            iface = WitInterface(name)
            expect("{")
            while i < len(toks) and toks[i] != "}":
                item = take()
                if item == "resource":
                    iface.resources.append(take())
                    if toks[i] == "{":
                        skip_block()
                    else:
                        expect(";")
                    continue
                if item in {"record", "variant", "enum", "flags"}:
                    iface.types.append(take())
                    skip_block()
                    continue
                if item in {"type", "use"}:
                    iface.types.append(take()) if item == "type" else None
                    while take() != ";":
                        pass
                    continue
                # function: ``name: func(...) -> ...;``
                fname = item.rstrip(":")
                if not _IDENT.match(fname):
                    raise WitParseError("unexpected token in interface", token=item)
                iface.functions.append(fname)
                while take() != ";":
                    pass
            expect("}")
            pkg.interfaces[name] = iface
        elif kw == "world":
            name = take()
            if name in pkg.worlds:
                raise WitParseError("duplicate world", name=name)
            world = WitWorld(name)
            expect("{")
            while i < len(toks) and toks[i] != "}":
                direction = take()
                if direction not in {"import", "export", "include"}:
                    raise WitParseError("world items must be import/export/include", token=direction)
                ref = take()
                if toks[i] == "{" or (i + 1 < len(toks) and toks[i] == "interface"):
                    raise WitParseError("inline world interfaces are not supported; declare a named interface")
                expect(";")
                if direction == "include":
                    if ref not in pkg.worlds:
                        raise WitParseError("include of unknown world", world=ref)
                    world.imports += pkg.worlds[ref].imports
                    world.exports += pkg.worlds[ref].exports
                else:
                    (world.imports if direction == "import" else world.exports).append(ref)
            expect("}")
            pkg.worlds[name] = world
        else:
            raise WitParseError("unexpected top-level token", token=kw)
    for w in pkg.worlds.values():
        for ref in w.imports + w.exports:
            pkg.qualify(ref)
    return pkg
