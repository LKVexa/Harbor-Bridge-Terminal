"""Typed capability / interface definitions for INV-29 (INV29-MC010).

``compose()`` reconciles imports by capability *name*.  This module adds a local,
dependency-free typed layer so a capability whose *signature* drifted is caught
even when INV-11 is not installed.  When INV-11 is present, its verdict is
required *in addition* to this one (MC002, BLOCKED_EXTERNAL); neither can
turn the other's refusal into an allow.

Compatibility classes (mirrors the INV-11 vocabulary):

* ``IDENTICAL``  - same interface id, same major, identical function set
* ``ADDITIVE``   - host offers a superset of what the guest needs, same major
* ``BREAKING``   - a required function is missing or its shape changed, or the
                   major version differs, or the interface id is unknown
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping, Tuple

IDENTICAL = "identical"
ADDITIVE = "additive"
BREAKING = "breaking"

_VERSION = re.compile(r"^(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})$")
_IDENT = re.compile(r"^[a-z][a-z0-9-]{0,62}(:[a-z][a-z0-9-/]{0,62})?$")
_TYPE = re.compile(r"^[a-z][a-z0-9<>,_ -]{0,63}$")
MAX_FUNCS = 512
MAX_PARAMS = 32


class InterfaceIncompatible(PermissionError):
    """Raised when a guest interface cannot be linked against the host's."""


@dataclass(frozen=True, slots=True)
class Func:
    name: str
    params: Tuple[Tuple[str, str], ...]
    results: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not type(self.name) is str or not _IDENT.fullmatch(self.name):
            raise ValueError(f"invalid function name {self.name!r}")
        if not isinstance(self.params, tuple) or len(self.params) > MAX_PARAMS:
            raise ValueError("params must be a tuple of at most 32 (name, type) pairs")
        for p in self.params:
            if (not isinstance(p, tuple) or len(p) != 2 or not _IDENT.fullmatch(str(p[0]))
                    or not type(p[1]) is str or not _TYPE.fullmatch(p[1])):
                raise ValueError(f"invalid parameter {p!r} in {self.name}")
        if not isinstance(self.results, tuple) or len(self.results) > MAX_PARAMS:
            raise ValueError("results must be a tuple")
        for r in self.results:
            if not type(r) is str or not _TYPE.fullmatch(r):
                raise ValueError(f"invalid result type {r!r} in {self.name}")

    @property
    def shape(self) -> tuple:
        return (tuple(t for _, t in self.params), self.results)


@dataclass(frozen=True, slots=True)
class Interface:
    id: str
    version: str
    funcs: FrozenSet[Func]

    def __post_init__(self) -> None:
        if not type(self.id) is str or not _IDENT.fullmatch(self.id):
            raise ValueError(f"invalid interface id {self.id!r}")
        if not type(self.version) is str or not _VERSION.fullmatch(self.version):
            raise ValueError(f"invalid semantic version {self.version!r}")
        if not isinstance(self.funcs, frozenset) or len(self.funcs) > MAX_FUNCS:
            raise ValueError("funcs must be a frozenset of at most 512 Func")
        if not all(isinstance(f, Func) for f in self.funcs):
            raise TypeError("funcs must contain only Func")
        names = [f.name for f in self.funcs]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate function names in {self.id}")

    @property
    def major(self) -> int:
        return int(self.version.split(".")[0])

    def by_name(self) -> Mapping[str, Func]:
        return {f.name: f for f in self.funcs}


def classify(host: Interface, guest: Interface) -> dict:
    """Classify whether ``guest`` (what the module imports) links against ``host``."""
    if host.id != guest.id:
        return {"class": BREAKING, "reason": "interface-id-mismatch", "detail": [host.id, guest.id]}
    if host.major != guest.major:
        return {"class": BREAKING, "reason": "major-version-mismatch",
                "detail": [host.version, guest.version]}
    have = host.by_name()
    problems = []
    for name, need in sorted(guest.by_name().items()):
        got = have.get(name)
        if got is None:
            problems.append(f"missing:{name}")
        elif got.shape != need.shape:
            problems.append(f"shape:{name}")
    if problems:
        return {"class": BREAKING, "reason": "function-mismatch", "detail": problems}
    if len(have) == len(guest.funcs):
        return {"class": IDENTICAL, "reason": "ok", "detail": []}
    return {"class": ADDITIVE, "reason": "ok", "detail": []}


def check_link(host: Interface, guest: Interface) -> dict:
    result = classify(host, guest)
    if result["class"] == BREAKING:
        raise InterfaceIncompatible(f"{guest.id}@{guest.version}: {result['reason']} {result['detail']}")
    return {"linked": True, **result}


def check_all(host_ifaces: Iterable[Interface], guest_ifaces: Iterable[Interface]) -> list:
    """Link every guest interface; an import with no host interface of the same id is refused."""
    table = {}
    for h in host_ifaces:
        if h.id in table:
            raise ValueError(f"host exports {h.id} twice")
        table[h.id] = h
    out = []
    for g in sorted(guest_ifaces, key=lambda i: i.id):
        h = table.get(g.id)
        if h is None:
            raise InterfaceIncompatible(f"{g.id}: not exported by host image")
        out.append({"interface": g.id, **check_link(h, g)})
    return out


def to_record(iface: Interface) -> dict:
    return {"id": iface.id, "version": iface.version,
            "funcs": [{"name": f.name, "params": [list(p) for p in f.params], "results": list(f.results)}
                      for f in sorted(iface.funcs, key=lambda f: f.name)]}


def from_record(rec: object) -> Interface:
    if not isinstance(rec, dict) or set(rec) != {"id", "version", "funcs"}:
        raise ValueError("interface record must have exactly id, version, funcs")
    if not isinstance(rec["funcs"], list):
        raise ValueError("funcs must be a list")
    funcs = []
    for f in rec["funcs"]:
        if not isinstance(f, dict) or set(f) != {"name", "params", "results"}:
            raise ValueError("func record must have exactly name, params, results")
        if not isinstance(f["params"], list) or not isinstance(f["results"], list):
            raise ValueError("params/results must be lists")
        funcs.append(Func(f["name"], tuple(tuple(p) if isinstance(p, list) else p for p in f["params"]),
                          tuple(f["results"])))
    return Interface(rec["id"], rec["version"], frozenset(funcs))
