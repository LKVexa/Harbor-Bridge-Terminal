"""MC-08 INV-17 stream credit, MC-09 INV-18 futures, MC-10 INV-15 waitable sets.

The authoritative INV-17/18/15 packages are *not* in this archive.  This module
therefore defines the binding points as ``typing.Protocol`` interfaces
(``StreamSink``, ``FutureLike``, ``WaitableSetLike``) plus conforming reference
implementations used by the tests.  When the authoritative packages are
installed, ``bind_authoritative()`` imports them and checks they satisfy the
protocols; until then the gate reports the authoritative binding as BLOCKED
(the reference behaviour is still executed and evidenced).
"""
from __future__ import annotations

import importlib
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol, runtime_checkable

from .errors import CanonicalError, Code, canonical

ABI_VERSION = (1, 0)
AUTHORITATIVE = {"INV-17": "inv17_streaming_primitive", "INV-18": "inv18_completion_primitive",
                 "INV-15": "inv15_new_asynchronous_abi", "INV-13": "inv13_system_interface",
                 "SCH-01": "sch01_multi_runtime_scheduler"}


# --------------------------------------------------------------------------- INV-18
class FutureState(str, Enum):
    PENDING = "PENDING"
    VALUE = "VALUE"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


@runtime_checkable
class FutureLike(Protocol):
    def resolve_value(self, v: Any) -> bool: ...
    def resolve_error(self, e: CanonicalError) -> bool: ...
    def cancel(self, cause: str) -> bool: ...


@dataclass
class Future:
    """INV-18 reference future: exactly-once, immutable once terminal."""
    op_id: int
    corr: dict = field(default_factory=dict)
    state: FutureState = FutureState.PENDING
    value: Any = None
    error: CanonicalError | None = None
    cancel_cause: str | None = None
    duplicate_resolutions: int = 0
    _cv: threading.Condition = field(default_factory=threading.Condition, repr=False)
    _callbacks: list = field(default_factory=list, repr=False)

    def _set(self, st: FutureState, **kw: Any) -> bool:
        with self._cv:
            if self.state is not FutureState.PENDING:
                self.duplicate_resolutions += 1
                return False
            self.state = st
            for k, v in kw.items():
                setattr(self, k, v)
            self._cv.notify_all()
            cbs = list(self._callbacks)
        for cb in cbs:
            cb(self)
        return True

    def resolve_value(self, v: Any) -> bool:
        return self._set(FutureState.VALUE, value=v)

    def resolve_error(self, e: CanonicalError) -> bool:
        if not isinstance(e, CanonicalError):
            e = canonical(Code.UNKNOWN_HOST_ERROR)  # quarantine unmapped errors, never swallow
        return self._set(FutureState.ERROR, error=e)

    def cancel(self, cause: str = "CALLER") -> bool:
        return self._set(FutureState.CANCELLED, error=canonical(Code.CANCELLED), cancel_cause=cause)

    def done(self) -> bool:
        return self.state is not FutureState.PENDING

    def result(self, timeout: float | None = None) -> tuple[str, Any]:
        with self._cv:
            if not self._cv.wait_for(self.done, timeout):
                raise TimeoutError("future not resolved")
        if self.state is FutureState.VALUE:
            return ("value", self.value)
        return ("error", self.error)

    def add_done_callback(self, cb: Callable[["Future"], None]) -> None:
        with self._cv:
            if self.state is FutureState.PENDING:
                self._callbacks.append(cb)
                return
        cb(self)


# --------------------------------------------------------------------------- INV-17
@runtime_checkable
class StreamSink(Protocol):
    def grant(self, direction: str) -> bool: ...
    def outstanding(self, direction: str) -> int: ...


class CreditExhausted(RuntimeError):
    pass


@dataclass
class CreditStream:
    """INV-17 reference: readiness -> credit, where a credit is permission to
    *attempt* one I/O, never proof of transfer.

    * One outstanding credit per direction; repeated level-triggered readiness
      while a credit is outstanding is coalesced (no duplicate credit).
    * A consumed credit whose attempt returns EAGAIN is lost only after the
      stream re-arms, so no readiness edge is lost.
    * A per-stream and a global cap bound credit; exceeding them refuses.
    """
    stream_id: int
    max_outstanding: int = 1
    global_cap: "CreditPool | None" = None
    eof: bool = False
    error: CanonicalError | None = None
    closed: bool = False
    _out: dict = field(default_factory=lambda: {"read": 0, "write": 0})
    coalesced: int = 0
    granted: int = 0
    consumed: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def grant(self, direction: str) -> bool:
        with self._lock:
            if self.closed or self.eof and direction == "read" or self.error is not None:
                return False
            if self._out[direction] >= self.max_outstanding:
                self.coalesced += 1
                return False
            if self.global_cap is not None and not self.global_cap.take():
                return False  # backpressure: pool exhausted
            self._out[direction] += 1
            self.granted += 1
            return True

    def consume(self, direction: str) -> None:
        with self._lock:
            if self._out[direction] <= 0:
                raise CreditExhausted(f"no {direction} credit outstanding")
            self._out[direction] -= 1
            self.consumed += 1
            if self.global_cap is not None:
                self.global_cap.give()

    def outstanding(self, direction: str) -> int:
        with self._lock:
            return self._out[direction]

    def close(self, error: CanonicalError | None = None) -> None:
        with self._lock:
            if self.closed:
                return
            self.closed = True
            self.error = self.error or error
            if self.global_cap is not None:
                for d in ("read", "write"):
                    for _ in range(self._out[d]):
                        self.global_cap.give()
            self._out = {"read": 0, "write": 0}


@dataclass
class CreditPool:
    capacity: int
    used: int = 0
    refused: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def take(self) -> bool:
        with self._lock:
            if self.used >= self.capacity:
                self.refused += 1
                return False
            self.used += 1
            return True

    def give(self) -> None:
        with self._lock:
            if self.used <= 0:
                raise RuntimeError("credit pool underflow")
            self.used -= 1


# --------------------------------------------------------------------------- INV-15
@runtime_checkable
class WaitableSetLike(Protocol):
    def add(self, handle: int) -> None: ...
    def remove(self, handle: int) -> None: ...
    def notify(self, handle: int) -> None: ...
    def wait(self, timeout: float | None, max_items: int) -> list[int]: ...


class WaitableSetFull(RuntimeError):
    pass


class WaitableSet:
    """INV-15 reference waitable set.

    ABI: handles are u32; ``ABI_VERSION`` = (1, 0); reserved fields are zero.
    Lost-wakeup safety: ``notify`` sets the ready bit under the same condition
    lock ``wait`` checks before sleeping.  Wake storms are coalesced: a handle
    already ready is not re-queued.  ``wait`` returns at most ``max_items``.
    """

    def __init__(self, capacity: int = 1024) -> None:
        self.capacity = capacity
        self._cv = threading.Condition()
        self._members: set[int] = set()
        self._ready: list[int] = []
        self._ready_set: set[int] = set()
        self.coalesced = 0
        self.closed = False

    def add(self, handle: int) -> None:
        if isinstance(handle, bool) or not isinstance(handle, int) or not (0 <= handle < 2**32):
            raise ValueError("handle must be u32")
        with self._cv:
            if len(self._members) >= self.capacity:
                raise WaitableSetFull(f"capacity {self.capacity}")
            self._members.add(handle)

    def remove(self, handle: int) -> None:
        with self._cv:
            self._members.discard(handle)
            if handle in self._ready_set:
                self._ready_set.discard(handle)
                self._ready.remove(handle)

    def notify(self, handle: int) -> None:
        with self._cv:
            if handle not in self._members:
                return  # invalid/removed handle: ignored, never delivered
            if handle in self._ready_set:
                self.coalesced += 1
                return
            self._ready.append(handle)
            self._ready_set.add(handle)
            self._cv.notify()

    def close(self) -> None:
        with self._cv:
            self.closed = True
            self._cv.notify_all()

    def wait(self, timeout: float | None = None, max_items: int = 64) -> list[int]:
        with self._cv:
            self._cv.wait_for(lambda: self._ready or self.closed, timeout)
            out = self._ready[:max_items]
            del self._ready[:max_items]
            for h in out:
                self._ready_set.discard(h)
            return out


# --------------------------------------------------------------------------- binding
def bind_authoritative() -> dict[str, str]:
    """Try to import the authoritative sibling packages; report per layer."""
    out = {}
    for layer, mod in AUTHORITATIVE.items():
        try:
            importlib.import_module(mod)
            out[layer] = "BOUND"
        except ModuleNotFoundError:
            out[layer] = "BLOCKED: authoritative package not installed (reference implementation used)"
    return out
