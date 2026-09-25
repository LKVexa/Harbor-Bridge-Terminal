"""MC-011 guest-memory adapter and MC-012 realloc/post-return lifecycle.

:class:`GuestMemory` wraps a guest linear memory (a ``bytearray`` owned by the
adapter, or any writable buffer exposed by a real runtime, e.g. the
``WebAssembly.Memory`` buffer in the Node harness).  Every access is:

* bounds-checked with checked 32-bit arithmetic (``ptr + len`` may not overflow
  2**32 and must lie inside the current memory size);
* alignment-checked where the canonical ABI requires natural alignment;
* copy-out only: reads return fresh ``bytes``; the host never retains a
  ``memoryview`` into guest memory, so no host object aliases guest memory.

:class:`Allocator` is the reference ``realloc``.  A runtime-provided realloc is
wrapped by :class:`CheckedRealloc`, which validates every region it returns
(alignment, bounds, no overlap with a live allocation) and records it so that
:class:`CallLifecycle` can prove each allocation is released exactly once.

Lifecycle state machine for one call::

    IDLE --begin--> LOWERING --ok--> CALLED --results lifted--> RETURNED
      LOWERING --error--> ROLLED_BACK (every allocation of this call freed)
      RETURNED --post_return--> DONE (post-return callback ran exactly once)
    Any second post_return, or any read of a released region -> PK_INTEROP_LIFECYCLE
"""
from __future__ import annotations

import bisect
import struct
import threading

from .errors import InteropError, LifecycleError

U32_MAX = 2**32 - 1
PAGE = 65536


def _bounds(msg):
    return InteropError(msg, code="PK_INTEROP_MEMORY_BOUNDS")


def _align_err(msg):
    return InteropError(msg, code="PK_INTEROP_MEMORY_ALIGNMENT")


def _overflow(msg):
    return InteropError(msg, code="PK_INTEROP_MEMORY_OVERFLOW")


def align_to(ptr: int, alignment: int) -> int:
    if alignment <= 0 or alignment & (alignment - 1):
        raise _align_err("alignment must be a power of two")
    r = (ptr + alignment - 1) & ~(alignment - 1)
    if r > U32_MAX:
        raise _overflow("aligned offset overflows u32")
    return r


def checked_add(a: int, b: int) -> int:
    r = a + b
    if a < 0 or b < 0 or r > U32_MAX:
        raise _overflow("offset arithmetic overflows u32")
    return r


def checked_mul(a: int, b: int) -> int:
    r = a * b
    if a < 0 or b < 0 or r > U32_MAX:
        raise _overflow("size arithmetic overflows u32")
    return r


class GuestMemory:
    """Bounds/alignment-checked view over one guest linear memory."""

    def __init__(self, buffer=None, *, max_bytes: int = 256 * 1024 * 1024):
        self._buf = bytearray() if buffer is None else buffer
        self.max_bytes = max_bytes
        self.lock = threading.RLock()

    def __len__(self):
        return len(self._buf)

    def grow_to(self, size: int):
        if size > self.max_bytes or size > U32_MAX + 1:
            raise InteropError("guest memory limit reached", code="PK_INTEROP_LIMIT")
        if type(self._buf) is not bytearray:
            raise _bounds("externally owned memory cannot be grown by the adapter")
        if size > len(self._buf):
            self._buf.extend(b"\x00" * (size - len(self._buf)))

    def _check(self, ptr: int, n: int, alignment: int = 1):
        if type(ptr) is not int or type(n) is not int or ptr < 0 or n < 0:
            raise _bounds("pointer/length must be non-negative ints")
        if ptr > U32_MAX or n > U32_MAX:
            raise _overflow("pointer/length exceeds u32")
        end = checked_add(ptr, n)
        if end > len(self._buf):
            raise _bounds(f"access [{ptr}, {end}) outside memory of {len(self._buf)} bytes")
        if alignment > 1 and ptr % alignment:
            raise _align_err(f"pointer {ptr} is not {alignment}-byte aligned")

    def read(self, ptr: int, n: int, alignment: int = 1) -> bytes:
        with self.lock:
            self._check(ptr, n, alignment)
            return bytes(self._buf[ptr:ptr + n])

    def write(self, ptr: int, data: bytes, alignment: int = 1):
        with self.lock:
            self._check(ptr, len(data), alignment)
            self._buf[ptr:ptr + len(data)] = data

    _FMT = {1: "<B", 2: "<H", 4: "<I", 8: "<Q"}

    def load_uint(self, ptr: int, size: int) -> int:
        return struct.unpack(self._FMT[size], self.read(ptr, size, size))[0]

    def store_uint(self, ptr: int, size: int, v: int):
        if not 0 <= v < (1 << (8 * size)):
            raise _overflow("integer does not fit the store width")
        self.write(ptr, struct.pack(self._FMT[size], v), size)

    def snapshot(self) -> bytes:
        with self.lock:
            return bytes(self._buf)


class Allocator:
    """Deterministic reference bump allocator used as the guest ``realloc``.

    ``realloc(0, 0, align, size)`` allocates; ``realloc(p, old, align, 0)``
    frees.  The golden corpus and the Rust/Go/JS fixtures implement exactly the
    same algorithm, which is what makes the canonical memory images comparable
    byte-for-byte.
    """

    def __init__(self, memory: GuestMemory, base: int = 0):
        self.mem = memory
        self.base = base
        self.pos = base

    def reset(self):
        """Reclaim the whole arena; only legal when no allocation is live."""
        self.pos = self.base

    def __call__(self, old_ptr: int, old_size: int, alignment: int, new_size: int) -> int:
        if old_ptr or old_size:
            if new_size == 0:
                return 0  # free; bump allocators never reuse
            raise LifecycleError("reference allocator does not support in-place growth")
        p = align_to(self.pos, alignment)
        end = checked_add(p, new_size)
        self.mem.grow_to(end)
        self.pos = end
        return p


class CheckedRealloc:
    """Validate and account every region returned by a (possibly hostile) realloc.

    Live allocations are keyed by a monotonically increasing allocation id (not
    by pointer, because zero-size allocations may legally share an address with
    a later allocation).  Non-empty regions are kept in a sorted interval index
    so the overlap check is O(log n) per allocation.
    """

    def __init__(self, memory: GuestMemory, realloc):
        self.mem = memory
        self._realloc = realloc
        self.live: dict[int, tuple] = {}     # alloc id -> (ptr, size)
        self._starts: list[int] = []         # sorted starts of non-empty live regions
        self._ends: dict[int, int] = {}      # start -> end
        self._ids = 0
        self.allocations = 0
        self.frees = 0
        self.lock = threading.RLock()

    def alloc_tracked(self, alignment: int, size: int) -> tuple:
        # The guest allocator is not assumed to be thread-safe (a component
        # instance is non-reentrant), so the realloc call, validation and
        # registration happen under one lock per instance.
        with self.lock:
            return self._alloc_locked(alignment, size)

    def _alloc_locked(self, alignment: int, size: int) -> tuple:
        ptr = self._realloc(0, 0, alignment, size)
        if type(ptr) is not int:
            raise InteropError("realloc returned a non-integer", code="PK_INTEROP_REALLOC")
        if ptr % alignment:
            raise InteropError("realloc returned a misaligned pointer", code="PK_INTEROP_REALLOC")
        try:
            self.mem._check(ptr, size)
        except InteropError:
            raise InteropError("realloc returned an out-of-bounds region", code="PK_INTEROP_REALLOC") from None
        # caller holds self.lock
        if size:
            i = bisect.bisect_right(self._starts, ptr)
            if i and self._ends[self._starts[i - 1]] > ptr:
                raise InteropError("realloc returned a region overlapping a live allocation",
                                   code="PK_INTEROP_REALLOC")
            if i < len(self._starts) and self._starts[i] < ptr + size:
                raise InteropError("realloc returned a region overlapping a live allocation",
                                   code="PK_INTEROP_REALLOC")
            self._starts.insert(i, ptr)
            self._ends[ptr] = ptr + size
        self._ids += 1
        self.live[self._ids] = (ptr, size)
        self.allocations += 1
        return self._ids, ptr

    def alloc(self, alignment: int, size: int) -> int:
        return self.alloc_tracked(alignment, size)[1]

    def free(self, alloc_id: int):
        with self.lock:
            if alloc_id not in self.live:
                raise LifecycleError("double free or free of an unknown allocation")
            ptr, size = self.live.pop(alloc_id)
            if size:
                i = bisect.bisect_left(self._starts, ptr)
                del self._starts[i]
                del self._ends[ptr]
            self.frees += 1
            self._realloc(ptr, size, 1, 0)
            if not self.live and hasattr(self._realloc, "reset"):
                self._realloc.reset()

    def leaked(self) -> int:
        with self.lock:
            return len(self.live)


class CallLifecycle:
    """Tracks allocations of one call and enforces post-return exactly once."""

    STATES = ("IDLE", "LOWERING", "CALLED", "RETURNED", "DONE", "ROLLED_BACK")

    def __init__(self, realloc: CheckedRealloc, post_return=None):
        self.realloc = realloc
        self.post_return_cb = post_return
        self.state = "IDLE"
        self.owned: list[int] = []
        self.lock = threading.Lock()

    def _to(self, allowed, new):
        with self.lock:
            if self.state not in allowed:
                raise LifecycleError(f"illegal lifecycle transition {self.state} -> {new}")
            self.state = new

    def begin(self):
        self._to(("IDLE",), "LOWERING")

    def alloc(self, alignment, size):
        if self.state != "LOWERING":
            raise LifecycleError("allocation outside the lowering phase")
        aid, p = self.realloc.alloc_tracked(alignment, size)
        self.owned.append(aid)
        return p

    def rollback(self):
        self._to(("LOWERING",), "ROLLED_BACK")
        for aid in reversed(self.owned):
            if aid in self.realloc.live:
                self.realloc.free(aid)
        self.owned.clear()

    def called(self):
        self._to(("LOWERING",), "CALLED")

    def returned(self):
        self._to(("CALLED",), "RETURNED")

    def post_return(self):
        self._to(("RETURNED",), "DONE")
        try:
            if self.post_return_cb is not None:
                self.post_return_cb()
        finally:
            for aid in reversed(self.owned):
                if aid in self.realloc.live:
                    self.realloc.free(aid)
            self.owned.clear()
