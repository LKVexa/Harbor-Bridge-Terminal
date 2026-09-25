"""Dependency-free lease and elastic-capacity model for INV-08.

The model intentionally contains no ``pk_core`` dependency so its safety-critical
state transitions can be unit-tested even when the wider conformance framework
is not installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import TypedDict


Number = int | float
_NODE_ID_RE = re.compile(r"^node-(\d+)$")


class PoolInvariantError(ValueError):
    """Raised when mutable/restored pool state violates an internal invariant."""


class NodeState(TypedDict):
    expires: Number
    busy: bool


class TickResult(TypedDict):
    size: int
    target: int
    added: int
    reclaimed: list[str]
    renewed: list[str]
    demand: Number
    node_hours: float


def _require_int(name: str, value: object, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int, got {value!r}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value!r}")
    return value


def _require_finite_number(name: str, value: object, *, nonnegative: bool = False) -> Number:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be non-negative, got {value!r}")
    return value


def _finite_sum(name: str, left: Number, right: Number) -> Number:
    value = left + right
    if isinstance(value, float) and not math.isfinite(value):
        raise OverflowError(f"{name} overflowed to a non-finite value")
    return value


@dataclass
class Pool:
    """Lease-backed elastic node pool with bounded, transactional scaling decisions.

    ``tick()`` treats ``elapsed_hours`` as the accounting interval represented by
    the decision.  The default is one hour for backward compatibility with the
    original model's one-tick-equals-one-node-hour assumption.

    ``nodes`` remains public for compatibility, but every tick validates restored
    or externally modified state before any mutation is committed.
    """

    min_nodes: int
    max_nodes: int
    per_node: int = 4
    lease_ttl: int = 10
    nodes: dict[str, NodeState] = field(default_factory=dict)
    _n: int = 0
    node_hours: float = 0.0
    _last_now: Number | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.min_nodes = _require_int("min_nodes", self.min_nodes, minimum=0)
        self.max_nodes = _require_int("max_nodes", self.max_nodes, minimum=0)
        if self.min_nodes > self.max_nodes:
            raise ValueError(
                f"need 0 <= min_nodes <= max_nodes, got {self.min_nodes}, {self.max_nodes}"
            )
        self.per_node = _require_int("per_node", self.per_node, minimum=1)
        self.lease_ttl = _require_int("lease_ttl", self.lease_ttl, minimum=1)
        self._n = _require_int("_n", self._n, minimum=0)
        _require_finite_number("node_hours", self.node_hours, nonnegative=True)
        if not isinstance(self.nodes, dict):
            raise ValueError(f"nodes must be a dict, got {type(self.nodes).__name__}")
        self._validate_state()
        self._n = max(self._n, self._highest_generated_node_number())

    def _highest_generated_node_number(self) -> int:
        highest = 0
        for node_id in self.nodes:
            match = _NODE_ID_RE.match(node_id)
            if match:
                highest = max(highest, int(match.group(1)))
        return highest

    def _validate_state(self) -> None:
        if len(self.nodes) > self.max_nodes:
            raise PoolInvariantError(
                f"pool contains {len(self.nodes)} nodes but max_nodes is {self.max_nodes}"
            )
        for node_id, state in self.nodes.items():
            if not isinstance(node_id, str) or not node_id:
                raise PoolInvariantError(f"node id must be a non-empty string, got {node_id!r}")
            if not isinstance(state, dict):
                raise PoolInvariantError(f"state for {node_id!r} must be a dict")
            if "expires" not in state or "busy" not in state:
                raise PoolInvariantError(f"state for {node_id!r} must contain expires and busy")
            try:
                _require_finite_number(f"{node_id}.expires", state["expires"])
            except ValueError as exc:
                raise PoolInvariantError(str(exc)) from exc
            if not isinstance(state["busy"], bool):
                raise PoolInvariantError(
                    f"{node_id}.busy must be bool, got {state['busy']!r}"
                )

    def _next_node_id(self, nodes: dict[str, NodeState], counter: int) -> tuple[str, int]:
        while True:
            counter += 1
            node_id = f"node-{counter}"
            if node_id not in nodes:
                return node_id, counter

    def set_busy(self, node_id: str, busy: bool = True) -> None:
        """Safely update a node's busy flag."""
        if not isinstance(busy, bool):
            raise ValueError(f"busy must be bool, got {busy!r}")
        if node_id not in self.nodes:
            raise KeyError(node_id)
        self.nodes[node_id]["busy"] = busy

    def snapshot(self) -> dict[str, object]:
        """Return a detached diagnostic snapshot of current state."""
        return {
            "min_nodes": self.min_nodes,
            "max_nodes": self.max_nodes,
            "per_node": self.per_node,
            "lease_ttl": self.lease_ttl,
            "nodes": {node_id: dict(state) for node_id, state in self.nodes.items()},
            "node_hours": self.node_hours,
            "last_now": self._last_now,
        }

    def tick(self, now: Number, demand: Number, *, elapsed_hours: Number = 1.0) -> TickResult:
        """Advance the pool by one scaling decision.

        The operation is transactional: inputs and mutable state are validated and
        all changes are made on a copy before the new state is committed.
        """
        now = _require_finite_number("now", now)
        demand = _require_finite_number("demand", demand, nonnegative=True)
        elapsed_hours = _require_finite_number(
            "elapsed_hours", elapsed_hours, nonnegative=True
        )
        if self._last_now is not None and now < self._last_now:
            raise ValueError(f"now regressed from {self._last_now!r} to {now!r}")
        self._validate_state()

        # Bound before division/ceil so arbitrarily large integer demand cannot
        # force unnecessary huge-number work when max_nodes already caps the pool.
        max_capacity = self.max_nodes * self.per_node
        if demand >= max_capacity:
            demand_nodes = self.max_nodes
        else:
            demand_nodes = math.ceil(demand / self.per_node) if demand else 0
        target = max(self.min_nodes, min(self.max_nodes, demand_nodes))

        working: dict[str, NodeState] = {
            node_id: {"expires": state["expires"], "busy": state["busy"]}
            for node_id, state in self.nodes.items()
        }
        renewed: list[str] = []
        for node_id, state in working.items():
            if state["busy"]:
                state["expires"] = _finite_sum("lease expiry", now, self.lease_ttl)
                renewed.append(node_id)

        reclaimed: list[str] = []
        for node_id, state in sorted(list(working.items())):
            surplus = len(working) > target
            if not state["busy"] and (state["expires"] <= now or surplus):
                reclaimed.append(node_id)
                del working[node_id]

        counter = max(self._n, self._highest_generated_node_number())
        added = 0
        while len(working) < target:
            node_id, counter = self._next_node_id(working, counter)
            working[node_id] = {
                "expires": _finite_sum("lease expiry", now, self.lease_ttl),
                "busy": False,
            }
            added += 1

        accounted = len(self.nodes) * elapsed_hours
        next_node_hours = self.node_hours + accounted
        if not math.isfinite(float(next_node_hours)):
            raise OverflowError("node_hours overflowed to a non-finite value")

        # Commit only after every validation and calculation succeeds.
        self.nodes = working
        self._n = counter
        self.node_hours = float(next_node_hours)
        self._last_now = now

        return {
            "size": len(self.nodes),
            "target": target,
            "added": added,
            "reclaimed": reclaimed,
            "renewed": renewed,
            "demand": demand,
            "node_hours": self.node_hours,
        }
