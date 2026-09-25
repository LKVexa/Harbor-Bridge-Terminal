"""Graph-safe structural type comparison (INV11-MC-07).

Types are compared as a graph: references are followed through aliases, pairs
already under comparison are assumed equal (coinduction) so cyclic input
cannot recurse forever, traversal order is deterministic, and every step is
charged to a WorkBudget so hostile graphs fail closed with E-LIMIT.
Resources are nominal: two resources are equal iff their version-less ids are.
"""
from __future__ import annotations

from typing import Any

from .limits import DEFAULT_LIMITS, Limits, WorkBudget
from .resolve import Resolved, unversioned

MAX_ALIAS_CHAIN = 64


class TypeGraph:
    def __init__(self, res: Resolved) -> None:
        self.res = res

    def deref(self, t: Any) -> Any:
        """Follow alias chains to a structural form (bounded)."""
        n = 0
        while isinstance(t, dict) and set(t) == {"ref"}:
            d = self.res.types.get(t["ref"])
            if d is None:
                return t
            if d["kind"] != "alias":
                return {"def": t["ref"]}
            t, n = d["target"], n + 1
            if n > MAX_ALIAS_CHAIN:
                raise ValueError("alias chain too long or cyclic")
        return t


class Comparator:
    def __init__(self, old: Resolved, new: Resolved, limits: Limits = DEFAULT_LIMITS) -> None:
        self.a, self.b = TypeGraph(old), TypeGraph(new)
        self.budget = WorkBudget(limits)
        self.assumed: set[tuple[str, str]] = set()
        self.memo: dict[tuple[str, str], str | None] = {}
        self.swaps: list[tuple[str, str]] = []  # structurally equal but differently named

    def diff(self, x: Any, y: Any, path: str = "") -> str | None:
        """Return None when structurally equal, else a description of the first difference."""
        self.budget.spend()
        x, y = self.a.deref(x), self.b.deref(y)
        if isinstance(x, str) or isinstance(y, str) or x is None or y is None:
            return None if x == y else f"{path}: {self._show(x)} -> {self._show(y)}"
        if "def" in x and "def" in y:
            return self.diff_defs(x["def"], y["def"], path)
        if set(x) != set(y):
            return f"{path}: {self._show(x)} -> {self._show(y)}"
        for mode in ("own", "borrow"):
            if mode in x:
                return None if unversioned(x[mode]) == unversioned(y[mode]) else f"{path}: {mode}<{x[mode]}> -> {mode}<{y[mode]}>"
        if "list" in x:
            if x.get("size") != y.get("size"):
                return f"{path}: list length {x.get('size')} -> {y.get('size')}"
            return self.diff(x["list"], y["list"], path + "<list>")
        if "option" in x:
            return self.diff(x["option"], y["option"], path + "<option>")
        if "result" in x:
            for part in ("ok", "err"):
                d = self.diff(x["result"][part], y["result"][part], f"{path}<result.{part}>")
                if d:
                    return d
            return None
        if "tuple" in x:
            if len(x["tuple"]) != len(y["tuple"]):
                return f"{path}: tuple arity {len(x['tuple'])} -> {len(y['tuple'])}"
            for i, (p, q) in enumerate(zip(x["tuple"], y["tuple"], strict=True)):
                d = self.diff(p, q, f"{path}<tuple.{i}>")
                if d:
                    return d
            return None
        for k in ("future", "stream"):
            if k in x:
                return self.diff(x[k], y[k], f"{path}<{k}>")
        return None if x == y else f"{path}: {self._show(x)} -> {self._show(y)}"

    def diff_defs(self, ka: str, kb: str, path: str) -> str | None:
        key = (ka, kb)
        if key in self.memo:
            if self.memo[key] is None and unversioned(ka) != unversioned(kb):
                self.swaps.append((unversioned(ka), unversioned(kb)))
            return self.memo[key]
        if key in self.assumed:
            return None  # coinductive assumption: cycle guard
        self.assumed.add(key)
        da, db = self.a.res.types[ka], self.b.res.types[kb]
        here = f"{path}#{ka.rsplit('#', 1)[-1]}" if path else unversioned(ka)
        out: str | None = None
        if da["kind"] != db["kind"]:
            out = f"{here}: {da['kind']} -> {db['kind']}"
        elif da["kind"] == "resource":
            out = None if unversioned(ka) == unversioned(kb) else f"{here}: resource identity {unversioned(ka)} -> {unversioned(kb)}"
        elif da["kind"] == "record":
            fa, fb = da["fields"], db["fields"]
            if [f[0] for f in fa] != [f[0] for f in fb]:
                out = f"{here}: fields {[f[0] for f in fa]} -> {[f[0] for f in fb]}"
            else:
                for (n, ta), (_, tb) in zip(fa, fb, strict=True):
                    out = self.diff(ta, tb, f"{here}.{n}")
                    if out:
                        break
        elif da["kind"] == "variant":
            ca, cb = da["cases"], db["cases"]
            if [c[0] for c in ca] != [c[0] for c in cb]:
                out = f"{here}: cases {[c[0] for c in ca]} -> {[c[0] for c in cb]}"
            else:
                for (n, ta), (_, tb) in zip(ca, cb, strict=True):
                    out = self.diff(ta, tb, f"{here}.{n}")
                    if out:
                        break
        else:  # enum / flags
            if da["cases"] != db["cases"]:
                out = f"{here}: {da['kind']} {da['cases']} -> {db['cases']}"
        self.assumed.discard(key)
        if out is None and unversioned(ka) != unversioned(kb):
            self.swaps.append((unversioned(ka), unversioned(kb)))
        self.memo[key] = out
        return out

    @staticmethod
    def _show(v: Any) -> str:
        if isinstance(v, dict) and "def" in v:
            return str(v["def"])
        return str(v)
