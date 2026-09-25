"""Real sync-caller -> async-callee bridge for INV-16 (closure item #7).

Algorithm (see ``docs/adr/ADR-0002-sync-async-bridge.md``):

1. refuse deterministically on a thread running an asyncio event loop
   (blocking there would deadlock the loop) and beyond ``max_depth`` nested
   bridges on one thread;
2. reserve a waiter slot (bounded: ``max_waiters``) or refuse;
3. ``invoke`` with ``caller_is_async=False`` (counts the bridge) and register a
   one-shot terminal listener *before* starting the callee, so a completion
   that races the registration cannot be lost;
4. run ``start(call)`` - the production runtime issues the INV-15 subtask here;
5. **fast path:** if the callee already finished inline, no Event is created;
   otherwise wait on a ``threading.Event`` (no busy-spin, INV-16 lock *not* held);
6. on timeout / caller cancellation, ``cancel`` with a structured reason; if the
   cancel loses the race to completion the completed value wins (exactly once);
7. re-verify the terminal outcome before returning; the value is returned or
   ``CallCancelled`` / ``CallTrapped`` is raised - once.

The production runtime replaces ``threading.Event`` with its native waitable
(the ``_Waiter`` seam); semantics are fixed by ``tests/test_bridge.py``.
"""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Callable

from .runtime import (AlreadyTerminal, AsyncFunctions, CallCancelled, CallState, CallTrapped,
                      CancelCode, CancelReason, Outcome)


class BridgeRefused(RuntimeError):
    """Bridging here would deadlock (event-loop thread or nesting too deep)."""


class BridgeSaturated(RuntimeError):
    """All bridge waiter slots are in use."""


class BridgeTimeout(TimeoutError):
    """The deadline elapsed; the async call was cancelled with code ``deadline``."""


class CancelToken:
    """Caller-side cancellation handle for a blocked sync caller."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self.reason: CancelReason | None = None
        self._hooks: list[Callable[[], None]] = []
        self._lock = threading.Lock()

    def cancel(self, reason: CancelReason | str | None = None) -> None:
        with self._lock:
            if self._event.is_set():
                return
            self.reason = CancelReason.coerce(reason, CancelCode.CALLER)
            self._event.set()
            hooks, self._hooks = self._hooks, []
        for h in hooks:
            h()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def _on_cancel(self, hook: Callable[[], None]) -> None:
        with self._lock:
            if not self._event.is_set():
                self._hooks.append(hook)
                return
        hook()


class _Waiter:
    __slots__ = ("done", "outcome", "value", "reason", "event", "lock")

    def __init__(self) -> None:
        self.done = False
        self.outcome: Outcome | None = None
        self.value: object = None
        self.reason: CancelReason | None = None
        self.event: threading.Event | None = None
        self.lock = threading.Lock()

    def deliver(self, _cid, outcome, value, reason) -> None:
        with self.lock:
            if self.done:
                return
            self.outcome, self.value, self.reason, self.done = outcome, value, reason, True
            ev = self.event
        if ev is not None:
            ev.set()

    def arm(self) -> threading.Event | None:
        with self.lock:
            if self.done:
                return None
            self.event = threading.Event()
            return self.event


_tls = threading.local()


def _on_event_loop_thread() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


class SyncBridge:
    def __init__(self, fns: AsyncFunctions, *, max_waiters: int = 1024, max_depth: int = 4,
                 latency_recorder: Callable[[int], None] | None = None):
        if max_waiters < 1 or max_depth < 1:
            raise ValueError("max_waiters and max_depth must be >= 1")
        self.fns = fns
        self.max_waiters = max_waiters
        self.max_depth = max_depth
        self.record = latency_recorder
        self._lock = threading.Lock()
        self.waiters = 0
        self.refusals = 0
        self.saturations = 0
        self.timeouts = 0
        self.slow_path = 0

    def call(self, function: str, start: Callable[[CallState], None], *, timeout: float | None = None,
             token: CancelToken | None = None, traceparent: str | None = None) -> object:
        t0 = time.perf_counter_ns()
        if _on_event_loop_thread():
            with self._lock:
                self.refusals += 1
            raise BridgeRefused("sync bridge on an event-loop thread would deadlock; await instead")
        depth = getattr(_tls, "depth", 0)
        if depth >= self.max_depth:
            with self._lock:
                self.refusals += 1
            raise BridgeRefused(f"bridge nesting depth {depth} >= {self.max_depth}")
        with self._lock:
            if self.waiters >= self.max_waiters:
                self.saturations += 1
                raise BridgeSaturated(f"{self.waiters} bridge waiters in use")
            self.waiters += 1
        _tls.depth = depth + 1
        try:
            return self._call(function, start, timeout, token, traceparent, t0)
        finally:
            _tls.depth = depth
            with self._lock:
                self.waiters -= 1

    def _call(self, function, start, timeout, token, traceparent, t0):
        fns = self.fns
        call = fns.invoke(function, caller_is_async=False, traceparent=traceparent)
        w = _Waiter()
        tomb = fns.add_terminal_listener(call.call_id, w.deliver)
        if tomb is not None:  # already terminal (e.g. cancelled by another party)
            w.deliver(call.call_id, tomb.outcome, None, tomb.reason)
        if token is not None:
            token._on_cancel(lambda: self._cancel(call, token.reason))
        try:
            start(call)
        except BaseException:
            # Callee failed to start: treat as a trap of this call only.
            self._cancel(call, CancelReason(CancelCode.UNSPECIFIED, "start failed", "bridge"))
            fns.remove_terminal_listener(call.call_id)
            raise
        if not w.done:
            ev = w.arm()
            if ev is not None:
                with self._lock:
                    self.slow_path += 1
                deadline = None if timeout is None else time.monotonic() + timeout
                while not w.done:  # loop tolerates spurious/early wakeups
                    remaining = None if deadline is None else deadline - time.monotonic()
                    if remaining is not None and remaining <= 0:
                        with self._lock:
                            self.timeouts += 1
                        self._cancel(call, CancelReason(CancelCode.DEADLINE, "bridge timeout", "bridge"))
                        # If completion won the race its listener may still be in flight on
                        # another thread; keep waiting (unbounded, it is already terminal).
                        deadline = None
                        continue
                    ev.wait(remaining)
        if self.record is not None:
            self.record(time.perf_counter_ns() - t0)
        if not w.done:  # pragma: no cover - cancel always produces a terminal outcome
            raise RuntimeError("bridge returned without a terminal outcome")  # pragma: no cover
        if w.outcome is Outcome.COMPLETED:
            return w.value
        if w.outcome is Outcome.CANCELLED:
            if w.reason is not None and w.reason.code is CancelCode.DEADLINE:
                raise BridgeTimeout(f"call {call.call_id} cancelled at deadline")
            raise CallCancelled(f"call {call.call_id} was cancelled")
        raise CallTrapped(f"call {call.call_id} ended when the callee trapped")

    def _cancel(self, call: CallState, reason: CancelReason | None) -> None:
        try:
            self.fns.cancel(call.call_id, reason, generation=call.generation)
        except AlreadyTerminal:
            pass  # lost the race: the other terminal outcome stands
        except (CallCancelled, CallTrapped):  # pragma: no cover - defensive
            pass
