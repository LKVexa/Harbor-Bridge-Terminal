"""History recording and linearizability checking (MC-043).

Sequential specification (MC-043-02) -- per key, a register whose state is
``(value | ABSENT)``:

* ``read()        -> value | None``
* ``write(v)      -> ok``
* ``cas(exp, new) -> bool``    (succeeds iff state == exp)
* ``delete()      -> ok``

Linearizability is compositional (Herlihy & Wing), so histories are partitioned
by key and each partition is checked independently with the Wing-Gong /
Lowe (WGL) search with memoisation on ``(linearized-set, state)`` -- the
algorithm used by Porcupine/Knossos (MC-043-03).  Operations that never
returned (crashed/timed-out clients) are treated as *possibly* taking effect
at any point after their invocation (return time = +inf) and their result is
unconstrained.  On failure the checker returns a minimal counterexample: the
key, the longest linearizable prefix found and the operations that could not be
placed (MC-043-06).
"""
from __future__ import annotations

import itertools
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any

ABSENT = object()
INF = float("inf")


@dataclass
class Operation:
    id: int
    client: str
    key: str
    kind: str                 # read | write | cas | delete
    arg: Any = None
    ret: Any = None
    call: float = 0.0
    done: float = INF         # INF == never returned (indeterminate)
    revision: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["done"] = None if self.done == INF else self.done
        return d


class Recorder:
    """Thread-safe invoke/complete recorder (MC-043-01)."""

    def __init__(self) -> None:
        self._ops: list[Operation] = []
        self._ids = itertools.count()
        self._lock = threading.Lock()

    def invoke(self, client: str, key: str, kind: str, arg: Any = None) -> Operation:
        op = Operation(next(self._ids), client, key, kind, arg, call=time.perf_counter())
        with self._lock:
            self._ops.append(op)
        return op

    @staticmethod
    def complete(op: Operation, ret: Any, revision: int = 0) -> None:
        op.ret, op.revision, op.done = ret, revision, time.perf_counter()

    @property
    def history(self) -> list[Operation]:
        with self._lock:
            return list(self._ops)

    def dump(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([o.to_dict() for o in self.history], fh, indent=1, default=str)


def _step(state: Any, op: Operation) -> tuple[bool, Any]:
    """Apply *op* to *state*; return (result-consistent, new state)."""
    indeterminate = op.done == INF
    if op.kind == "read":
        cur = None if state is ABSENT else state
        return (indeterminate or op.ret == cur), state
    if op.kind == "write":
        return True, op.arg
    if op.kind == "delete":
        return True, ABSENT
    if op.kind == "cas":
        exp, new = op.arg
        ok = state is not ABSENT and state == exp
        if indeterminate:
            return True, (new if ok else state)
        return (op.ret == ok), (new if ok else state)
    raise ValueError(f"unknown op kind {op.kind}")


def _freeze(state: Any) -> Any:
    return ("<absent>",) if state is ABSENT else json.dumps(state, sort_keys=True, default=str)


@dataclass
class CheckResult:
    ok: bool
    keys_checked: int
    ops_checked: int
    counterexample: dict[str, Any] | None = None
    search_nodes: int = 0


def check_key(ops: list[Operation], initial: Any = ABSENT, max_nodes: int = 2_000_000) -> tuple[bool, dict[str, Any] | None, int]:
    ops = sorted(ops, key=lambda o: o.call)
    n = len(ops)
    seen: set[tuple[int, Any]] = set()
    best: list[int] = []
    nodes = 0

    def rec(done_mask: int, state: Any, order: list[int]) -> bool:
        nonlocal nodes, best
        nodes += 1
        if nodes > max_nodes:
            raise RuntimeError("linearizability search budget exhausted")
        if done_mask == (1 << n) - 1:
            return True
        key = (done_mask, _freeze(state))
        if key in seen:
            return False
        seen.add(key)
        if len(order) > len(best):
            best = list(order)
        # an op may be linearized next only if it was invoked before every
        # pending op's completion (it is 'minimal' in the real-time order)
        min_done = min(ops[i].done for i in range(n) if not done_mask >> i & 1)
        for i in range(n):
            if done_mask >> i & 1 or ops[i].call > min_done:
                continue
            ok, nxt = _step(state, ops[i])
            if ok:
                order.append(i)
                if rec(done_mask | (1 << i), nxt, order):
                    return True
                order.pop()
            # an indeterminate op may also never take effect
            if ops[i].done == INF and rec(done_mask | (1 << i), state, order):
                return True
        return False

    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 10 * n + 100))
    try:
        ok = rec(0, initial, [])
    finally:
        sys.setrecursionlimit(old)
    if ok:
        return True, None, nodes
    placed = set(best)
    return False, {"key": ops[0].key if ops else "", "linearized_prefix": [ops[i].to_dict() for i in best],
                   "unplaceable": [o.to_dict() for j, o in enumerate(ops) if j not in placed]}, nodes


def check(history: list[Operation]) -> CheckResult:
    by_key: dict[str, list[Operation]] = {}
    for o in history:
        by_key.setdefault(o.key, []).append(o)
    nodes = 0
    for k, ops in sorted(by_key.items()):
        ok, cex, n = check_key(ops)
        nodes += n
        if not ok:
            return CheckResult(False, len(by_key), len(history), cex, nodes)
    return CheckResult(True, len(by_key), len(history), None, nodes)
