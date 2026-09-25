"""MC-004 resource-handle type system and MC-005 own/borrow semantics.

Model (follows the Component Model canonical ABI):

* Each component instance owns one :class:`ResourceTable`.  A handle is an
  index into exactly one table; handles are never meaningful in another table
  (cross-component non-alias).  The Python :class:`Handle` object also carries
  the table id and a per-slot *generation*, so a stale handle (slot reused after
  drop) or a foreign handle is detected and refused (``PK_INTEROP_HANDLE``).
* ``own<R>``: exactly one owner.  Passing an own handle to another component
  *moves* it: the source slot is removed and a fresh own slot is created in the
  destination table (:meth:`ResourceTable.transfer_own`).  An own handle with
  outstanding borrows cannot move or be dropped (``PK_INTEROP_BORROW``).
* ``borrow<R>``: a temporary loan scoped to one call (:class:`CallScope`).
  Lending increments the lender's ``lend_count``; the callee MUST drop every
  borrow it received before the call returns.  On scope exit any borrow still
  held is forcibly revoked (fail-safe) and the call fails with
  ``PK_INTEROP_BORROW``.  Borrows cannot be moved or re-lent as own.
* Dropping an own handle runs its destructor exactly once.

State machine per slot::

    OWN(lend=0) --lend--> OWN(lend>0) --end-call--> OWN(lend=0)
    OWN(lend=0) --transfer--> REMOVED(src) + OWN(dst)
    OWN(lend=0) --drop--> REMOVED (+ destructor once)
    BORROW --drop--> REMOVED (lender lend-1)
    BORROW --scope end while live--> REVOKED (error)

Locking: every table has its own lock.  Operations touching two tables acquire
both locks in ascending ``table_id`` order, so there is a total lock order and
no deadlock.
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .errors import HandleError, InteropError, LimitError

_TABLE_IDS = itertools.count(1)


def _borrow_err(msg, path=()):
    return InteropError(msg, code="PK_INTEROP_BORROW", path=path)


@dataclass(frozen=True)
class Handle:
    table_id: int
    index: int
    generation: int
    resource: str
    kind: str  # "own" | "borrow"

    def __repr__(self):
        return f"Handle({self.kind}<{self.resource}>#{self.index}@t{self.table_id}g{self.generation})"


class _Slot:
    __slots__ = ("resource", "rep", "kind", "lend_count", "generation", "dtor",
                 "lender", "scope")

    def __init__(self, resource, rep, kind, generation, dtor=None, lender=None, scope=None):
        self.resource = resource
        self.rep = rep
        self.kind = kind
        self.lend_count = 0
        self.generation = generation
        self.dtor = dtor
        self.lender = lender     # (table, Handle) for borrows
        self.scope = scope


class ResourceTable:
    def __init__(self, owner: str, *, max_handles: int = 10_000):
        self.owner = owner
        self.table_id = next(_TABLE_IDS)
        self.max_handles = max_handles
        self._slots: dict[int, _Slot] = {}
        self._free: list[int] = []
        self._gens: dict[int, int] = {}
        self._next = 1          # index 0 is never a valid handle (spec: reserved)
        self.lock = threading.RLock()
        self.dtor_calls = 0

    # -------------------------------------------------------------- internals
    def _alloc(self, slot_factory) -> Handle:
        if len(self._slots) >= self.max_handles:
            raise LimitError(f"resource table {self.owner} is full ({self.max_handles})")
        idx = self._free.pop() if self._free else self._next
        if idx == self._next:
            self._next += 1
        gen = self._gens.get(idx, 0) + 1
        self._gens[idx] = gen
        slot = slot_factory(gen)
        self._slots[idx] = slot
        return Handle(self.table_id, idx, gen, slot.resource, slot.kind)

    def _get(self, h: object, kind: Optional[str] = None, resource: Optional[str] = None) -> _Slot:
        if type(h) is not Handle:
            raise HandleError("not a resource handle")
        if h.table_id != self.table_id:
            raise HandleError("handle belongs to another component's table")
        slot = self._slots.get(h.index)
        if slot is None or slot.generation != h.generation:
            raise HandleError("stale or dropped handle")
        if kind is not None and slot.kind != kind:
            raise HandleError(f"expected {kind} handle, got {slot.kind}")
        if resource is not None and slot.resource != resource:
            raise HandleError(f"handle is {slot.resource}, expected {resource}")
        return slot

    def _remove(self, h: Handle):
        del self._slots[h.index]
        self._free.append(h.index)

    # -------------------------------------------------------------- public API
    def new(self, resource: str, rep: Any, dtor: Optional[Callable[[Any], None]] = None) -> Handle:
        with self.lock:
            return self._alloc(lambda g: _Slot(resource, rep, "own", g, dtor))

    def rep(self, h: Handle, resource: Optional[str] = None):
        with self.lock:
            return self._get(h, resource=resource).rep

    def live(self) -> int:
        with self.lock:
            return len(self._slots)

    def at(self, index: int, kind: str, resource: str) -> Handle:
        """Resolve a wire index received by this table into a validated Handle."""
        with self.lock:
            slot = self._slots.get(index) if type(index) is int else None
            if slot is None:
                raise HandleError("wire handle index names no live slot")
            h = Handle(self.table_id, index, slot.generation, slot.resource, slot.kind)
            self._get(h, kind=kind, resource=resource)
            return h

    def validate(self, h: object, kind: str, resource: str) -> Handle:
        with self.lock:
            self._get(h, kind=kind, resource=resource)
            return h

    def drop(self, h: Handle) -> None:
        dtor = rep = None
        lender = None
        with self.lock:
            slot = self._get(h)
            if slot.kind == "own":
                if slot.lend_count:
                    raise _borrow_err("cannot drop an own handle with outstanding borrows")
                dtor, rep = slot.dtor, slot.rep
                if dtor is not None:
                    self.dtor_calls += 1
            else:
                lender = slot.lender
            self._remove(h)
        if lender is not None:
            ltable, lh = lender
            with ltable.lock:
                ls = ltable._slots.get(lh.index)
                if ls is not None and ls.generation == lh.generation:
                    ls.lend_count -= 1
        if dtor is not None:
            dtor(rep)

    def transfer_own(self, h: Handle, dest: "ResourceTable") -> Handle:
        """Move an own handle into *dest*; the source handle becomes stale."""
        if dest is self:
            raise HandleError("transfer to the same table is a no-op and is refused")
        first, second = sorted((self, dest), key=lambda t: t.table_id)
        with first.lock, second.lock:
            slot = self._get(h, kind="own")
            if slot.lend_count:
                raise _borrow_err("cannot move an own handle with outstanding borrows")
            if len(dest._slots) >= dest.max_handles:
                raise LimitError(f"resource table {dest.owner} is full")
            self._remove(h)
            return dest._alloc(lambda g: _Slot(slot.resource, slot.rep, "own", g, slot.dtor))

    def lend(self, h: Handle, dest: "ResourceTable", scope: "CallScope") -> Handle:
        """Create a borrow of *h* in *dest*, valid only inside *scope*."""
        if not scope.active:
            raise _borrow_err("call scope is not active")
        first, second = sorted((self, dest), key=lambda t: t.table_id)
        with first.lock, second.lock:
            slot = self._get(h)
            if len(dest._slots) >= dest.max_handles:
                raise LimitError(f"resource table {dest.owner} is full")
            slot.lend_count += 1
            b = dest._alloc(lambda g: _Slot(slot.resource, slot.rep, "borrow", g,
                                            lender=(self, h), scope=scope))
        scope._borrows.append((dest, b))
        return b


class CallScope:
    """Scope of one cross-component call; enforces borrow release on exit."""

    def __init__(self):
        self._borrows: list = []
        self.active = False
        self.revoked = 0

    def __enter__(self):
        self.active = True
        return self

    def __exit__(self, et, ev, tb):
        self.active = False
        leaked = []
        for table, b in self._borrows:
            with table.lock:
                s = table._slots.get(b.index)
                live = s is not None and s.generation == b.generation
            if live:
                leaked.append(b)
                table.drop(b)       # fail-safe revocation restores lender lend_count
        self.revoked = len(leaked)
        if leaked and et is None:
            raise _borrow_err(f"callee returned while holding {len(leaked)} borrow(s)")
        return False
