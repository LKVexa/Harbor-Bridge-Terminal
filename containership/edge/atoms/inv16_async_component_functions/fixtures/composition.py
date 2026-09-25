"""SURROGATE INV-10 linker: sync/async caller-callee matrix across linked components."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..bridge import SyncBridge
from ..runtime import AsyncFunctions

SURROGATE = True
INV10_FIXTURE_VERSION = "surrogate-1"
ABI_VERSION = 1


class LinkError(RuntimeError):
    pass


@dataclass
class Component:
    name: str
    exports: dict[str, tuple[bool, Callable]]     # fn -> (is_async, impl)
    abi_version: int = ABI_VERSION
    stateful: frozenset = frozenset()
    fns: AsyncFunctions = field(init=False)

    def __post_init__(self):
        self.fns = AsyncFunctions(self.name, declared={k: v[0] for k, v in self.exports.items()},
                                  stateful=self.stateful)


class Linked:
    """``call(caller_is_async, callee, fn, *args)`` routes through the correct bridge rule."""

    def __init__(self, components: list[Component]):
        vers = {c.abi_version for c in components}
        if vers != {ABI_VERSION}:
            raise LinkError(f"incompatible ABI versions {sorted(vers)}; linker speaks {ABI_VERSION}")
        self.by_name = {c.name: c for c in components}
        self.bridges = {c.name: SyncBridge(c.fns) for c in components}

    def call(self, caller_is_async: bool, callee: str, fn: str, *args):
        comp = self.by_name[callee]
        is_async, impl = comp.exports[fn]
        if is_async and not caller_is_async:
            return self.bridges[callee].call(
                fn, lambda st: comp.fns.complete(st.call_id, impl(self, *args)))
        st = comp.fns.invoke(fn, caller_is_async=caller_is_async)
        try:
            value = impl(self, *args)
        except BaseException:
            comp.fns.cancel(st.call_id, "unspecified")
            raise
        return comp.fns.complete(st.call_id, value)
