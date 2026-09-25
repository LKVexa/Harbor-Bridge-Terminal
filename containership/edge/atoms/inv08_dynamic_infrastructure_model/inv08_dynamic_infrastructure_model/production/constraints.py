"""Component 18 - constraint precedence engine for placement/scaling choices.

Normalized model (CONSTRAINT_SPEC): ``Constraint(kind, attr, op, value, hard)``
* kind in PRECEDENCE = security > residency > slo > topology > capacity > cost
* op in OPS: eq, ne, in, not_in, le, ge
* hard constraints filter candidates; soft constraints rank survivors.

Resolution (``resolve``) is deterministic:
1. Apply hard constraints kind by kind in precedence order.  Security and
   residency are ALWAYS treated as hard even if declared soft (no silent
   downgrade).  If a kind eliminates all remaining candidates, stop and return
   an unsatisfiable diagnostic naming that constraint and the candidates it
   removed (INV08.CONSTRAINT.UNSATISFIABLE when ``raise_on_fail``).
2. Rank survivors by a lexicographic tuple: for each kind in precedence order,
   the number of satisfied soft constraints of that kind (higher is better);
   so one satisfied SLO preference beats any number of cost preferences.
   Final tie-breaker: candidate ``id`` ascending.
``PRECEDENCE_DIGEST`` pins the ordering; tests fail if it changes silently.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .core import digest
from .errors_catalog import error

PRECEDENCE = ("security", "residency", "slo", "topology", "capacity", "cost")
ALWAYS_HARD = frozenset({"security", "residency"})
OPS = {
    "eq": lambda a, v: a == v, "ne": lambda a, v: a != v,
    "in": lambda a, v: a in v, "not_in": lambda a, v: a not in v,
    "le": lambda a, v: a is not None and a <= v, "ge": lambda a, v: a is not None and a >= v,
}
CONSTRAINT_SPEC = {"version": "PK_DYN_CONSTRAINT/1", "precedence": list(PRECEDENCE),
                   "always_hard": sorted(ALWAYS_HARD), "ops": sorted(OPS)}
PRECEDENCE_DIGEST = digest(CONSTRAINT_SPEC)


@dataclass(frozen=True)
class Constraint:
    kind: str
    attr: str
    op: str
    value: Any
    hard: bool = True
    name: str = ""

    def __post_init__(self) -> None:
        if self.kind not in PRECEDENCE:
            raise error("INV08.CONSTRAINT.INVALID", f"unknown kind {self.kind!r}")
        if self.op not in OPS:
            raise error("INV08.CONSTRAINT.INVALID", f"unknown op {self.op!r}")
        if self.op in ("in", "not_in") and not isinstance(self.value, (list, tuple, frozenset, set)):
            raise error("INV08.CONSTRAINT.INVALID", f"{self.op} needs a collection")

    @property
    def effective_hard(self) -> bool:
        return self.hard or self.kind in ALWAYS_HARD

    @property
    def label(self) -> str:
        return self.name or f"{self.kind}:{self.attr} {self.op} {self.value!r}"

    def ok(self, cand: dict) -> bool:
        try:
            return bool(OPS[self.op](cand.get(self.attr), self.value))
        except TypeError:
            return False  # incomparable attribute => not satisfied (fail closed)


def resolve(candidates: list[dict], constraints: list[Constraint], *, raise_on_fail: bool = False) -> dict:
    ids = [c.get("id") for c in candidates]
    if any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
        raise error("INV08.CONSTRAINT.INVALID", "candidates need unique string ids")
    order = {k: i for i, k in enumerate(PRECEDENCE)}
    cons = sorted(constraints, key=lambda c: (order[c.kind], c.label))
    alive = sorted(candidates, key=lambda c: c["id"])
    trace = []
    for c in cons:
        if not c.effective_hard:
            continue
        kept = [x for x in alive if c.ok(x)]
        removed = [x["id"] for x in alive if not c.ok(x)]
        trace.append({"constraint": c.label, "kind": c.kind, "removed": removed})
        if not kept:
            diag = {"satisfiable": False, "blocking": c.label, "kind": c.kind,
                    "last_candidates": [x["id"] for x in alive], "trace": trace,
                    "hint": f"relax {c.label} or add capacity satisfying it"}
            if raise_on_fail:
                raise error("INV08.CONSTRAINT.UNSATISFIABLE", c.label, details=diag)
            return diag
        alive = kept
    soft = [c for c in cons if not c.effective_hard]

    def score(x: dict) -> tuple:
        return tuple(-sum(1 for c in soft if c.kind == k and c.ok(x)) for k in PRECEDENCE) + (x["id"],)
    ranked = sorted(alive, key=score)
    return {"satisfiable": True, "choice": ranked[0]["id"], "ranking": [x["id"] for x in ranked],
            "trace": trace, "precedence_digest": PRECEDENCE_DIGEST}
