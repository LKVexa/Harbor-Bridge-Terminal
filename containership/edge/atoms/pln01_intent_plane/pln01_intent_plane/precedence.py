"""Deterministic constraint precedence (MC-008).

When constraints on the same attribute conflict, the winner is chosen by:

1. constraint class precedence:  security > residency > availability > slo > cost
2. within a class, ``hard`` beats ``soft``
3. then the lexicographically smallest canonical JSON value (total, stable tie-break)

Hard constraints of the *same* class with different values are an
unresolvable conflict and are rejected at admission rather than guessed.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .graph import ValidationError

PRECEDENCE = ("security", "residency", "availability", "slo", "cost")
_RANK = {k: i for i, k in enumerate(PRECEDENCE)}


def resolve(constraints: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return ``{attribute: {"winner": c, "overridden": [c, ...]}}``."""
    if not isinstance(constraints, Sequence) or isinstance(constraints, (str, bytes)):
        raise ValidationError("constraints must be a list")
    by_attr: dict[str, list[Mapping[str, Any]]] = {}
    for c in constraints:
        if not isinstance(c, Mapping) or c.get("kind") not in _RANK or not isinstance(c.get("key"), str):
            raise ValidationError(f"invalid constraint {c!r}; kind must be one of {PRECEDENCE}")
        by_attr.setdefault(c["key"], []).append(c)
    out: dict[str, dict[str, Any]] = {}
    for attr, items in sorted(by_attr.items()):
        ranked = sorted(items, key=lambda c: (_RANK[c["kind"]], 0 if c.get("hard") else 1,
                                              json.dumps(c.get("value"), sort_keys=True)))
        top = ranked[0]
        if top.get("hard"):
            clash = [c for c in ranked[1:] if c["kind"] == top["kind"] and c.get("hard") and c.get("value") != top.get("value")]
            if clash:
                raise ValidationError(f"unresolvable hard {top['kind']} conflict on {attr!r}")
        out[attr] = {"winner": dict(top), "overridden": [dict(c) for c in ranked[1:] if c.get("value") != top.get("value")]}
    return out
