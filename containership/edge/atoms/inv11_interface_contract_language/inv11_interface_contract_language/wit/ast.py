"""WIT AST / type system (INV11-MC-02).  Immutable, span-carrying nodes.

Type forms: primitives (bool s8..s64 u8..u64 f32 f64 char string), named refs,
list<T>, list<T, N> (fixed-length, gated), option<T>, result / result<T> /
result<_, E> / result<T, E>, tuple<...>, own<R>, borrow<R>, future<T>, stream<T>
(both recorded as async-gated forms).  Declarations: type alias, record,
variant, enum, flags, resource (constructor/method/static), func, use, include.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from .diagnostics import Span

PRIMITIVES = ("bool", "s8", "s16", "s32", "s64", "u8", "u16", "u32", "u64", "f32", "f64",
              "char", "string")
PRIM_ALIASES = {"float32": "f32", "float64": "f64"}


@dataclass(frozen=True)
class Gate:
    kind: str  # since | unstable | deprecated
    value: str


@dataclass(frozen=True)
class Prim:
    name: str
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Ref:
    name: str
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class ListT:
    elem: Type
    size: int | None = None
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class OptionT:
    inner: Type
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class ResultT:
    ok: Type | None
    err: Type | None
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class TupleT:
    items: tuple[Type, ...]
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Handle:
    mode: str  # own | borrow
    resource: str
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class AsyncT:
    kind: str  # future | stream
    inner: Type | None
    span: Span | None = field(default=None, compare=False)


Type = Union[Prim, Ref, ListT, OptionT, ResultT, TupleT, Handle, AsyncT]  # noqa: UP007 (runtime alias, py3.10)


@dataclass(frozen=True)
class Param:
    name: str
    type: Type
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Func:
    name: str
    params: tuple[Param, ...]
    result: Type | None
    kind: str = "freestanding"  # freestanding | constructor | method | static
    is_async: bool = False
    gates: tuple[Gate, ...] = ()
    doc: str = field(default="", compare=False)
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Member:  # record field / variant case / enum case / flag
    name: str
    type: Type | None = None
    gates: tuple[Gate, ...] = ()
    doc: str = field(default="", compare=False)
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class TypeDecl:
    name: str
    kind: str  # alias | record | variant | enum | flags | resource
    target: Type | None = None  # alias
    members: tuple[Member, ...] = ()
    funcs: tuple[Func, ...] = ()  # resource members
    gates: tuple[Gate, ...] = ()
    doc: str = field(default="", compare=False)
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class UsePath:
    """`iface`, `ns:pkg/iface`, or `ns:pkg/iface@1.2.3`."""
    package: str | None  # "ns:pkg" or None for local
    name: str
    version: str | None = None
    span: Span | None = field(default=None, compare=False)

    def text(self) -> str:
        if self.package is None:
            return self.name
        return f"{self.package}/{self.name}" + (f"@{self.version}" if self.version else "")


@dataclass(frozen=True)
class Use:
    path: UsePath
    names: tuple[tuple[str, str], ...]  # (original, local alias)
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Interface:
    name: str
    types: tuple[TypeDecl, ...] = ()
    funcs: tuple[Func, ...] = ()
    uses: tuple[Use, ...] = ()
    gates: tuple[Gate, ...] = ()
    doc: str = field(default="", compare=False)
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class WorldItem:
    direction: str  # import | export
    name: str  # extern name (plain name or interface path text)
    kind: str  # interface-ref | inline-interface | func
    ref: UsePath | None = None
    inline: Interface | None = None
    func: Func | None = None
    gates: tuple[Gate, ...] = ()
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Include:
    path: UsePath
    renames: tuple[tuple[str, str], ...] = ()
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class World:
    name: str
    items: tuple[WorldItem, ...] = ()
    types: tuple[TypeDecl, ...] = ()
    uses: tuple[Use, ...] = ()
    includes: tuple[Include, ...] = ()
    gates: tuple[Gate, ...] = ()
    doc: str = field(default="", compare=False)
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class TopUse:
    path: UsePath
    alias: str | None
    span: Span | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Document:
    file: str
    package: tuple[str, str, str | None] | None  # (namespace, name, version)
    interfaces: tuple[Interface, ...] = ()
    worlds: tuple[World, ...] = ()
    uses: tuple[TopUse, ...] = ()
    nested_packages: tuple[Document, ...] = ()
    package_span: Span | None = field(default=None, compare=False)
