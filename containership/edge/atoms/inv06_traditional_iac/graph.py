"""Resource dependency graph (MC-017 package-local reference).

Builds a DAG from explicit ``depends_on`` lists and ``${type.name...}``
references found anywhere in resource values, detects cycles and dangling
references fail-closed, and produces deterministic apply/destroy ordering plus
replacement fan-out (everything that transitively depends on a replaced node).
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .state import IacError

REF_RE = re.compile(r"\$\{([A-Za-z_][\w-]*\.[A-Za-z_][\w-]*)(?:\.[\w.\-\[\]]*)?\}")
MAX_NODES = 100_000


class GraphError(IacError):
    code = "PK_IAC_GRAPH_INVALID"


def _refs(value: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(value, str):
        out.update(REF_RE.findall(value))
    elif isinstance(value, Mapping):
        for v in value.values():
            out |= _refs(v)
    elif isinstance(value, list):
        for v in value:
            out |= _refs(v)
    return out


class ResourceGraph:
    def __init__(self, resources: Mapping[str, Any]) -> None:
        if len(resources) > MAX_NODES:
            raise GraphError("graph exceeds node limit", details={"nodes": len(resources), "limit": MAX_NODES})
        self.nodes = sorted(resources)
        self.deps: dict[str, set[str]] = {}
        dangling: dict[str, list[str]] = {}
        for rid in self.nodes:
            value = resources[rid]
            deps = set(_refs(value))
            if isinstance(value, Mapping) and isinstance(value.get("depends_on"), list):
                deps |= {d for d in value["depends_on"] if isinstance(d, str)}
            if rid in deps:
                raise GraphError("resource depends on itself", details={"resource": rid})
            missing = sorted(d for d in deps if d not in resources)
            if missing:
                dangling[rid] = missing
            self.deps[rid] = deps
        if dangling:
            raise GraphError("dangling references", details={"dangling": dangling})
        self.order = self._toposort()

    def _toposort(self) -> list[str]:
        indeg = {n: len(self.deps[n]) for n in self.nodes}
        users: dict[str, list[str]] = {n: [] for n in self.nodes}
        for n, ds in self.deps.items():
            for d in ds:
                users[d].append(n)
        ready = sorted(n for n, k in indeg.items() if k == 0)
        order: list[str] = []
        while ready:
            n = ready.pop(0)
            order.append(n)
            for u in sorted(users[n]):
                indeg[u] -= 1
                if indeg[u] == 0:
                    ready.append(u)
            ready.sort()
        if len(order) != len(self.nodes):
            cyc = sorted(n for n, k in indeg.items() if k > 0)
            raise GraphError("dependency cycle", details={"nodes": cyc})
        return order

    def dependents(self, rid: str) -> set[str]:
        """Transitive dependents: what must be replaced/re-applied if ``rid`` is replaced."""
        out: set[str] = set()
        frontier = [rid]
        while frontier:
            cur = frontier.pop()
            for n, ds in self.deps.items():
                if cur in ds and n not in out:
                    out.add(n)
                    frontier.append(n)
        return out

    def apply_order(self, subset: set[str] | None = None) -> list[str]:
        return [n for n in self.order if subset is None or n in subset]

    def destroy_order(self, subset: set[str] | None = None) -> list[str]:
        return list(reversed(self.apply_order(subset)))


def ordered_plan(plan: Mapping[str, Any], desired: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, list[str]]:
    """Order a ``PK_IAC_PLAN/1`` for execution: creates/updates dependency-first, deletes dependents-first."""
    g_new = ResourceGraph(desired)
    g_old = ResourceGraph(current)
    return {
        "apply": g_new.apply_order(set(plan["create"]) | set(plan["update"])),
        "destroy": g_old.destroy_order(set(plan["delete"])),
    }
