"""Operation identity and exactly-once lifecycle shared by every backend.

Operation IDs are 64-bit ``(generation << 32) | slot``.  A slot is reused only
after its operation reached a terminal state *and* was released, and every
reuse bumps the generation, so a stale native completion (old CQE, old
OVERLAPPED, old epoll token) can never resolve a newer operation: it is
detected, counted in ``stale_completions`` and dropped.

State machine (PK_ASYNC_OP/1)::

    SUBMITTED -> INFLIGHT -> COMPLETED | FAILED | CANCELLED | TIMED_OUT
    SUBMITTED -> CANCELLED | FAILED          (rejected before reaching host)

Terminal states are immutable.  When completion and cancellation race, the
first to acquire the table lock wins; the loser observes ``False`` and the
event is counted as ``lost_race`` - never delivered twice.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .errors import CanonicalError


class OpState(str, Enum):
    SUBMITTED = "SUBMITTED"
    INFLIGHT = "INFLIGHT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


TERMINAL = frozenset({OpState.COMPLETED, OpState.FAILED, OpState.CANCELLED, OpState.TIMED_OUT})
LEGAL = {
    OpState.SUBMITTED: {OpState.INFLIGHT, OpState.CANCELLED, OpState.FAILED, OpState.TIMED_OUT},
    OpState.INFLIGHT: {OpState.COMPLETED, OpState.FAILED, OpState.CANCELLED, OpState.TIMED_OUT},
}


class IllegalTransition(RuntimeError):
    pass


class TableFull(RuntimeError):
    pass


@dataclass
class Operation:
    op_id: int
    kind: str
    tenant: str
    workload: str
    fd: int
    state: OpState = OpState.SUBMITTED
    result: Any = None
    error: CanonicalError | None = None
    deadline: float | None = None
    trace: dict | None = None
    keepalive: list = field(default_factory=list)  # native buffers pinned until release
    on_terminal: Callable[["Operation"], None] | None = None

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL


def pack(slot: int, gen: int) -> int:
    return ((gen & 0xFFFFFFFF) << 32) | (slot & 0xFFFFFFFF)


def unpack(op_id: int) -> tuple[int, int]:
    return op_id & 0xFFFFFFFF, (op_id >> 32) & 0xFFFFFFFF


class OperationTable:
    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive int")
        self.capacity = capacity
        self._lock = threading.RLock()
        self._slots: list[Operation | None] = [None] * capacity
        self._gens = [0] * capacity
        self._free = list(range(capacity - 1, -1, -1))
        self.stale_completions = 0
        self.lost_races = 0
        self.resolved = 0

    def __len__(self) -> int:
        with self._lock:
            return self.capacity - len(self._free)

    def allocate(self, kind: str, tenant: str, workload: str, fd: int, **kw: Any) -> Operation:
        with self._lock:
            if not self._free:
                raise TableFull(f"operation table full ({self.capacity})")
            slot = self._free.pop()
            self._gens[slot] = (self._gens[slot] + 1) & 0xFFFFFFFF or 1
            op = Operation(pack(slot, self._gens[slot]), kind, tenant, workload, fd, **kw)
            self._slots[slot] = op
            return op

    def lookup(self, op_id: int) -> Operation | None:
        slot, gen = unpack(op_id)
        with self._lock:
            if slot >= self.capacity:
                return None
            op = self._slots[slot]
            if op is None or self._gens[slot] != gen:
                return None
            return op

    def transition(self, op_id: int, new: OpState, *, result: Any = None,
                   error: CanonicalError | None = None) -> bool:
        """Move to ``new``; return False (and count) for stale/terminal targets."""
        with self._lock:
            op = self.lookup(op_id)
            if op is None:
                self.stale_completions += 1
                return False
            if op.terminal:
                self.lost_races += 1
                return False
            if new not in LEGAL[op.state]:
                raise IllegalTransition(f"{op.state.value} -> {new.value}")
            op.state = new
            if new in TERMINAL:
                op.result, op.error = result, error
                self.resolved += 1
            cb = op.on_terminal if new in TERMINAL else None
        if cb is not None:
            cb(op)
        return True

    def release(self, op_id: int) -> Operation:
        """Free a terminal operation's slot (and its pinned buffers)."""
        with self._lock:
            op = self.lookup(op_id)
            if op is None:
                raise KeyError(op_id)
            if not op.terminal:
                raise IllegalTransition("cannot release a non-terminal operation")
            slot, _ = unpack(op_id)
            self._slots[slot] = None
            op.keepalive.clear()
            self._free.append(slot)
            return op

    def live(self) -> list[Operation]:
        with self._lock:
            return [o for o in self._slots if o is not None and not o.terminal]
