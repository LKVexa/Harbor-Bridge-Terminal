"""SURROGATE INV-15 subtask table: handles, capacity, cancel, trap, leak accounting."""
from __future__ import annotations

import threading

from ..runtime import AlreadyTerminal, AsyncFunctions, CancelCode, CancelReason, Outcome

SURROGATE = True
INV15_FIXTURE_VERSION = "surrogate-1"


class SubtaskCapacity(RuntimeError):
    pass


class SubtaskTable:
    """Owns subtask handles; each handle belongs to exactly one INV-16 call id."""

    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self._next = 1
        self.live: dict[int, int] = {}          # handle -> owning call id
        self.by_call: dict[int, set[int]] = {}  # call id -> handles
        self.cancelled: dict[int, str] = {}     # handle -> reason code
        self.lock = threading.Lock()

    def spawn(self, call_id: int) -> int:
        with self.lock:
            if len(self.live) >= self.capacity:
                raise SubtaskCapacity("INV-15 subtask table full")
            h = self._next
            self._next += 1
            self.live[h] = call_id
            self.by_call.setdefault(call_id, set()).add(h)
            return h

    def finish(self, handle: int) -> int:
        with self.lock:
            cid = self.live.pop(handle)
            self.by_call[cid].discard(handle)
            if not self.by_call[cid]:
                del self.by_call[cid]
            return cid

    def cancel_owned(self, call_id: int, code: str) -> int:
        with self.lock:
            hs = self.by_call.pop(call_id, set())
            for h in hs:
                self.live.pop(h, None)
                self.cancelled[h] = code
            return len(hs)

    def outstanding(self) -> int:
        with self.lock:
            return len(self.live)


class AbiBinding:
    """Glue: INV-16 terminal transitions reclaim INV-15 subtasks; INV-15 traps trap INV-16."""

    def __init__(self, fns: AsyncFunctions, table: SubtaskTable):
        self.fns, self.table = fns, table

    def invoke(self, function: str, subtasks: int = 1, **kw):
        call = self.fns.invoke(function, **kw)
        handles = []
        try:
            for _ in range(subtasks):
                handles.append(self.table.spawn(call.call_id))
        except Exception:
            self.table.cancel_owned(call.call_id, "spawn_failed")
            self.fns.cancel(call.call_id, CancelReason(CancelCode.UNSPECIFIED, "subtask capacity", "inv15"))
            raise
        self.fns.add_terminal_listener(call.call_id, self._on_terminal)
        return call, handles

    def _on_terminal(self, call_id, outcome: Outcome, _value, reason) -> None:
        code = outcome.value if reason is None else reason.code.value
        self.table.cancel_owned(call_id, code)

    def subtask_done(self, handle: int, value=None, last: bool = False):
        cid = self.table.finish(handle)
        if last:
            return self.fns.complete(cid, value)
        return None

    def cancel(self, call_id: int, code: CancelCode = CancelCode.CALLER):
        try:
            return self.fns.cancel(call_id, CancelReason(code, "", "caller"))
        except AlreadyTerminal:
            return None

    def trap(self) -> int:
        return self.fns.trap_all()
