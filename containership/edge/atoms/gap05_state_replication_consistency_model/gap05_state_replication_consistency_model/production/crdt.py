"""MC21 - CRDT / commutative type registry.

Only keys whose ``value_type`` is registered here are merged automatically; every other
type keeps concurrency open exactly as the core model does.  Every merge function is a
join-semilattice operation (commutative, associative, idempotent) - property-checked in
the test suite - so merging a conflict frontier in any order yields one value.

Values are JSON strings so the core ``Write.value: str`` contract is unchanged.  No
type uses wall-clock time (a timestamp LWW register is deliberately *not* offered).
"""
from __future__ import annotations

import json
from functools import reduce

from .errors import SchemaError


def _load(value: str):
    try:
        return json.loads(value)
    except ValueError as exc:
        raise SchemaError(f"CRDT value is not JSON: {exc}") from exc


def _dump(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def g_counter_merge(a: str, b: str) -> str:
    x, y = _load(a), _load(b)
    if not isinstance(x, dict) or not isinstance(y, dict):
        raise SchemaError("g-counter must be an object of site->count")
    return _dump({s: max(x.get(s, 0), y.get(s, 0)) for s in set(x) | set(y)})


def g_counter_value(v: str) -> int:
    return sum(_load(v).values())


def pn_counter_merge(a: str, b: str) -> str:
    x, y = _load(a), _load(b)
    return _dump({"p": _load(g_counter_merge(_dump(x.get("p", {})), _dump(y.get("p", {})))),
                  "n": _load(g_counter_merge(_dump(x.get("n", {})), _dump(y.get("n", {}))))})


def pn_counter_value(v: str) -> int:
    d = _load(v)
    return sum(d.get("p", {}).values()) - sum(d.get("n", {}).values())


def max_register_merge(a: str, b: str) -> str:
    x, y = _load(a), _load(b)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x, y)):
        raise SchemaError("max-register values must be numbers")
    return _dump(max(x, y))


def g_set_merge(a: str, b: str) -> str:
    return _dump(sorted(set(_load(a)) | set(_load(b))))


def or_set_merge(a: str, b: str) -> str:
    """Observed-remove set: {"adds": {elem: [tags]}, "removes": {elem: [tags]}}."""
    x, y = _load(a), _load(b)
    out = {}
    for part in ("adds", "removes"):
        merged = {}
        for src in (x.get(part, {}), y.get(part, {})):
            for elem, tags in src.items():
                merged[elem] = sorted(set(merged.get(elem, [])) | set(tags))
        out[part] = merged
    return _dump(out)


def or_set_value(v: str) -> list:
    d = _load(v)
    return sorted(e for e, tags in d.get("adds", {}).items()
                  if set(tags) - set(d.get("removes", {}).get(e, [])))


REGISTRY = {
    "crdt.g_counter/1": g_counter_merge,
    "crdt.pn_counter/1": pn_counter_merge,
    "crdt.max_register/1": max_register_merge,
    "crdt.g_set/1": g_set_merge,
    "crdt.or_set/1": or_set_merge,
}


def is_commutative(value_type: str | None) -> bool:
    return value_type in REGISTRY


def merge_all(value_type: str, values: list[str]) -> str:
    if value_type not in REGISTRY:
        raise SchemaError(f"{value_type!r} is not a registered commutative type")
    if not values:
        raise SchemaError("nothing to merge")
    fn = REGISTRY[value_type]
    # sort first so the fold is order-independent even if a merge were not associative;
    # seeding with fn(v0, v0) canonicalises the encoding even for a single value
    ordered = sorted(values)
    return reduce(fn, ordered[1:], fn(ordered[0], ordered[0]))
