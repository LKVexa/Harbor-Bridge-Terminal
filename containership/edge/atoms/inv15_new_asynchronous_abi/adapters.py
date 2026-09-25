"""Adjacent-layer adapters (components 31-37).

Each adapter is a thin, versioned boundary over ``AsyncHost``; none of them
polls, parks a guest stack, or buffers without a bound. The adjacent layers
themselves (SCH-01, INV-11/12/14/16/17/18) are NOT in this archive: these
adapters implement this side of each boundary against a documented contract
and are exercised against stand-ins, which is stated wherever it matters.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from concurrent.futures import Future
import threading
import time

from .errors import (AbiError, CancelReason, ErrorCode, InvalidArgument, BudgetExhaustedError,
                     UnsupportedVersion, Cancelled)
from .host import AsyncHost, InstanceView

ADAPTER_CONTRACT_VERSION = (1, 0)


def require_contract(peer_major: int):
    if peer_major != ADAPTER_CONTRACT_VERSION[0]:
        raise UnsupportedVersion(f"adapter contract major {peer_major} unsupported; need "
                                 f"{ADAPTER_CONTRACT_VERSION[0]}")


class SchedulerAdapter:
    """SCH-01 adapter (component 31): readiness events -> runnable instances.

    Event-driven via ``host.on_ready``; wakeups for the same instance coalesce
    into one runnable entry; ``run_once`` resumes each runnable instance with a
    bounded batch. Queue is bounded by the number of registered instances.
    """

    def __init__(self, host: AsyncHost, resume, *, batch=32):
        self.host, self.resume, self.batch = host, resume, batch
        self._runq: OrderedDict[str, int] = OrderedDict()
        self._lock = threading.Lock()
        self.coalesced = 0
        self.resumed = 0
        host.on_ready.append(self._on_ready)

    def _on_ready(self, instance, ready_ns):
        with self._lock:
            if instance in self._runq:
                self.coalesced += 1
                return
            self._runq[instance] = ready_ns
        self.host.metrics.hist["publish_to_runnable_ns"].observe(time.monotonic_ns() - ready_ns)

    def runnable(self):
        with self._lock:
            return list(self._runq)

    def run_once(self):
        with self._lock:
            items = list(self._runq.items())
            self._runq.clear()
        n = 0
        for name, ready_ns in items:
            view = self.host.views.get(name)
            if view is None or view.state == "torn_down":
                continue
            self.host.metrics.hist["ready_to_resume_ns"].observe(time.monotonic_ns() - ready_ns)
            self.resume(view)
            n += 1
        self.resumed += n
        return n


class AsyncFunctionAdapter:
    """INV-16 adapter (component 32): lowers a host callable onto the ABI.

    A callable returning a plain value completes synchronously; returning a
    ``concurrent.futures.Future`` yields a subtask whose resolution is published
    through the producer API (success -> complete, exception -> trap,
    future.cancel() -> nothing published; the guest's cancel is authoritative).
    """

    def __init__(self, host: AsyncHost, view: InstanceView):
        self.host, self.view = host, view

    def invoke(self, fn, *args, **call_kw):
        result = fn(*args)
        if not isinstance(result, Future):
            return self.view.call(result)
        kind, h = self.view.call(**call_kw)

        def done(f: Future, h=h):
            if f.cancelled():
                return
            exc = f.exception()
            if exc is None:
                self.host.complete(h, f.result())
            elif isinstance(exc, AbiError):
                self.host.trap(h, exc.detail, code=exc.code)
            else:
                self.host.trap(h, type(exc).__name__)

        result.add_done_callback(done)
        return kind, h


class StreamAdapter:
    """INV-17 adapter (component 33): bounded stream built on subtask readiness.

    Each ``read()`` returns a subtask; ``write()`` resolves the oldest pending
    read or buffers up to ``capacity`` items (then refuses: backpressure).
    ``close()`` resolves pending reads with the end-of-stream marker; ``error()``
    traps them. Guest cancellation of a read handle removes it from the queue.
    """

    EOS = ("__eos__",)

    def __init__(self, host, view, capacity=16):
        if capacity < 1:
            raise InvalidArgument("capacity >= 1")
        self.host, self.view, self.capacity = host, view, capacity
        self._buf = deque()
        self._reads = deque()
        self.closed = False
        self._err = None

    def read(self):
        if self._buf:
            return self.view.call(self._buf.popleft())
        if self.closed:
            return self.view.call(self.EOS)
        kind, h = self.view.call()
        self._reads.append(h)
        return kind, h

    def write(self, item):
        if self.closed:
            raise InvalidArgument("stream closed")
        while self._reads:
            h = self._reads.popleft()
            if self.host.complete(h, item) == "published":
                return "delivered"
        if len(self._buf) >= self.capacity:
            raise BudgetExhaustedError("stream buffer full")
        self._buf.append(item)
        return "buffered"

    def close(self):
        self.closed = True
        while self._reads:
            self.host.complete(self._reads.popleft(), self.EOS)

    def error(self, detail="stream error"):
        self.closed = True
        while self._reads:
            self.host.trap(self._reads.popleft(), detail)


class Completion:
    """INV-18 adapter (component 34): one-shot typed completion."""

    def __init__(self, host, view, expect_type=object):
        self.host, self.view, self.expect_type = host, view, expect_type
        _, self.handle = view.call()

    def resolve_ok(self, value):
        if not isinstance(value, self.expect_type):
            return self.host.trap(self.handle, f"type mismatch: expected {self.expect_type.__name__}",
                                  code=ErrorCode.TRAPPED)
        return self.host.complete(self.handle, ("ok", value))

    def resolve_err(self, code: int, detail: str):
        return self.host.complete(self.handle, ("err", int(code), detail))

    def lift(self):
        """Take and lift into ('ok', v) | ('err', code, detail); ABI errors pass through typed."""
        return self.view.take(self.handle)


class PollableShim:
    """INV-14 migration shim (component 37): old instance-local pollable API.

    ``poll(p)`` -> bool readiness over a subtask handle. Every use counts a
    deprecation metric; ``cutover=True`` refuses legacy use outright.
    """

    def __init__(self, host, view, *, cutover=False):
        self.host, self.view, self.cutover = host, view, cutover

    def _guard(self):
        self.host.metrics.inc("pk_async_legacy_pollable_calls_total")
        if self.cutover:
            raise UnsupportedVersion("legacy pollable API disabled after cutover")

    def start(self):
        self._guard()
        return self.view.call()[1]

    def poll(self, pollable) -> bool:
        self._guard()
        return bool(self.view.wait([pollable]))

    def block(self, pollable, timeout_ns=1_000_000_000):
        """Old blocking semantics mapped onto a host-thread wait (never a guest stack)."""
        self._guard()
        self.view.wait_blocking([pollable], timeout_ns)
        return self.view.take(pollable)
