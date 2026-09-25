"""MC-011 -- typed, generation-protected resource table.

Handles are 32-bit ``(generation << 20) | slot``.  A dropped slot bumps its
generation, so a stale handle can never alias the slot's next occupant.
Ownership is explicit: an *owned* handle may be dropped/transferred, a
*borrow* is valid only while its parent is live and is never droppable by the
borrower.  Exhaustion fails with QUOTA_EXCEEDED, never by reuse of a live slot.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable

from .errors import ErrorCode, Inv13Error

SLOT_BITS = 20
SLOT_MASK = (1 << SLOT_BITS) - 1
GEN_MASK = (1 << (32 - SLOT_BITS)) - 1


@dataclass(slots=True)
class _Entry:
    kind: str
    value: Any
    owned: bool
    parent: int | None
    on_drop: Callable[[Any], None] | None
    borrows: int = 0


class ResourceTable:
    def __init__(self, capacity: int = 1024) -> None:
        if not 0 < capacity <= SLOT_MASK:
            raise ValueError("capacity out of range")
        self.capacity = capacity
        self._slots: list[_Entry | None] = []
        self._gens: list[int] = []
        self._free: list[int] = []
        self._lock = threading.RLock()
        self.dropped = 0

    def __len__(self) -> int:
        with self._lock:
            return sum(1 for e in self._slots if e is not None)

    def _alloc(self, entry: _Entry) -> int:
        if self._free:
            slot = self._free.pop()
        elif len(self._slots) < self.capacity:
            slot = len(self._slots)
            self._slots.append(None)
            self._gens.append(1)
        else:
            raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, "resource table full")
        self._slots[slot] = entry
        return (self._gens[slot] << SLOT_BITS) | slot

    def _lookup(self, handle: Any) -> tuple[int, _Entry]:
        if not isinstance(handle, int) or isinstance(handle, bool) or handle <= 0 or handle >> 32:
            raise Inv13Error(ErrorCode.INVALID_HANDLE)
        slot, gen = handle & SLOT_MASK, handle >> SLOT_BITS
        if slot >= len(self._slots):
            raise Inv13Error(ErrorCode.INVALID_HANDLE)
        entry = self._slots[slot]
        if entry is None or self._gens[slot] != gen:
            raise Inv13Error(ErrorCode.STALE_HANDLE)
        return slot, entry

    def push(self, kind: str, value: Any, *, on_drop: Callable[[Any], None] | None = None) -> int:
        with self._lock:
            return self._alloc(_Entry(kind, value, True, None, on_drop))

    def borrow(self, handle: int) -> int:
        with self._lock:
            _, parent = self._lookup(handle)
            parent.borrows += 1
            return self._alloc(_Entry(parent.kind, parent.value, False, handle, None))

    def get(self, handle: int, kind: str) -> Any:
        with self._lock:
            _, entry = self._lookup(handle)
            if entry.kind != kind:
                raise Inv13Error(ErrorCode.WRONG_HANDLE_TYPE, (entry.kind, kind))
            if entry.parent is not None:
                self._lookup(entry.parent)  # borrow dies with its parent
            return entry.value

    def release_borrow(self, handle: int) -> None:
        with self._lock:
            slot, entry = self._lookup(handle)
            if entry.owned:
                raise Inv13Error(ErrorCode.WRONG_HANDLE_TYPE, "not a borrow")
            self._retire(slot)
            try:
                _, parent = self._lookup(entry.parent)
                parent.borrows -= 1
            except Inv13Error:
                pass

    def drop(self, handle: int) -> None:
        with self._lock:
            slot, entry = self._lookup(handle)
            if not entry.owned:
                raise Inv13Error(ErrorCode.WRONG_HANDLE_TYPE, "borrowed handles cannot be dropped")
            if entry.borrows:
                raise Inv13Error(ErrorCode.ALREADY_EXISTS,
                                 "outstanding borrows")
            self._retire(slot)
        if entry.on_drop is not None:
            entry.on_drop(entry.value)

    def transfer(self, handle: int, other: "ResourceTable") -> int:
        """Move an owned resource to another table; the source handle dies."""
        with self._lock:
            slot, entry = self._lookup(handle)
            if not entry.owned or entry.borrows:
                raise Inv13Error(ErrorCode.WRONG_HANDLE_TYPE, "only unborrowed owned handles transfer")
            self._retire(slot)
        return other.push(entry.kind, entry.value, on_drop=entry.on_drop)

    def _retire(self, slot: int) -> None:
        self._slots[slot] = None
        self._gens[slot] = (self._gens[slot] % GEN_MASK) + 1
        self._free.append(slot)
        self.dropped += 1

    def leak_report(self) -> list[dict[str, Any]]:
        with self._lock:
            return [{"slot": i, "kind": e.kind, "owned": e.owned}
                    for i, e in enumerate(self._slots) if e is not None]

    def close_all(self) -> int:
        """Instance teardown: drop borrows first, then owned resources."""
        with self._lock:
            live = [(i, e) for i, e in enumerate(self._slots) if e is not None]
            for i, e in live:
                if not e.owned:
                    self._retire(i)
            owned = [(i, e) for i, e in live if e.owned]
            for i, _ in owned:
                self._retire(i)
        for _, e in owned:
            if e.on_drop is not None:
                try:
                    e.on_drop(e.value)
                except Exception:
                    pass
        return len(live)
