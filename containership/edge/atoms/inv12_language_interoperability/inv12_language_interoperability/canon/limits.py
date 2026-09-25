"""MC-018 schema-derived resource limits.

A :class:`Limits` is an immutable budget.  :class:`LimitPolicy` resolves the
effective budget for an (interface, type) pair: the global default, overridden by
an interface-level entry, overridden by a type-level entry.  Overrides may only
*tighten* the global ceiling (a policy that loosens a hard ceiling is rejected at
construction time), so a mis-configured interface cannot open a DoS hole.

A :class:`Budget` is the mutable per-operation meter charged during
validation / lowering.  Every charge happens *before* the corresponding
allocation or recursion.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from types import MappingProxyType

from .errors import LimitError, ConfigError


@dataclass(frozen=True)
class Limits:
    max_depth: int = 64
    max_list_items: int = 100_000
    max_nodes: int = 200_000
    max_string_bytes: int = 16 * 1024 * 1024
    max_total_bytes: int = 64 * 1024 * 1024
    max_handles: int = 10_000
    max_concurrent_calls: int = 1_024
    max_stream_window: int = 1_024

    def __post_init__(self):
        for f in fields(self):
            v = getattr(self, f.name)
            if type(v) is not int or v < 0:
                raise ConfigError(f"limit {f.name} must be a non-negative int", path=[f.name])

    def tightened(self, **kw) -> "Limits":
        new = replace(self, **kw)
        for f in fields(self):
            if getattr(new, f.name) > getattr(self, f.name):
                raise ConfigError(f"override may not loosen {f.name}", path=[f.name])
        return new

    def as_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


HARD_CEILING = Limits()


class LimitPolicy:
    """Resolve per-interface / per-type limits (immutable after construction)."""

    def __init__(self, default: Limits = HARD_CEILING, interfaces=None, types=None):
        if not isinstance(default, Limits):
            raise ConfigError("default must be Limits")
        HARD_CEILING.tightened(**default.as_dict())  # default itself may not exceed ceiling
        self.default = default
        ints, tys = {}, {}
        for name, kw in dict(interfaces or {}).items():
            ints[name] = default.tightened(**kw)
        for (iname, tname), kw in dict(types or {}).items():
            base = ints.get(iname, default)
            tys[(iname, tname)] = base.tightened(**kw)
        self._interfaces = MappingProxyType(ints)
        self._types = MappingProxyType(tys)

    def resolve(self, interface: str | None = None, type_name: str | None = None) -> Limits:
        if interface is not None and type_name is not None and (interface, type_name) in self._types:
            return self._types[(interface, type_name)]
        if interface is not None and interface in self._interfaces:
            return self._interfaces[interface]
        return self.default


class Budget:
    """Per-operation meter.  Not shared between threads."""

    __slots__ = ("limits", "nodes", "bytes")

    def __init__(self, limits: Limits):
        self.limits = limits
        self.nodes = 0
        self.bytes = 0

    def node(self, path):
        self.nodes += 1
        if self.nodes > self.limits.max_nodes:
            raise LimitError(f"value exceeds {self.limits.max_nodes} nodes", path=path)

    def depth(self, depth, path):
        if depth > self.limits.max_depth:
            raise LimitError(f"value exceeds nesting depth {self.limits.max_depth}", path=path)

    def items(self, n, path):
        if n > self.limits.max_list_items:
            raise LimitError(f"list exceeds {self.limits.max_list_items} items", path=path)

    def string(self, nbytes, path):
        if nbytes > self.limits.max_string_bytes:
            raise LimitError(f"string exceeds {self.limits.max_string_bytes} bytes", path=path)
        self.charge(nbytes, path)

    def charge(self, nbytes, path):
        self.bytes += nbytes
        if self.bytes > self.limits.max_total_bytes:
            raise LimitError(f"value exceeds {self.limits.max_total_bytes} canonical bytes", path=path)
