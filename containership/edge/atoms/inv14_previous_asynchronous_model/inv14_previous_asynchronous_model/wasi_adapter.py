"""WASI 0.2 ``wasi:io/poll`` integration adapter (component P0-02).

Maps PK_POLL/1 onto the real WASI 0.2 primitive:
  wasi:io/poll@0.2.0  poll: func(in: list<borrow<pollable>>) -> list<u32>
  wasi:clocks/monotonic-clock@0.2.0  subscribe-duration: func(when: duration) -> pollable

WASI's poll has no timeout argument and traps on an empty list, so the adapter:
  1. validates the PK request exactly as ``PollSet`` does (same error codes),
  2. appends a monotonic-clock timer pollable as the LAST member,
  3. calls ``host.poll`` (which blocks until >= 1 ready),
  4. maps returned indexes < n to ``ready_indexes``; the timer index alone means
     ``timed_out``; readiness wins if both are reported,
  5. drops the timer handle in every path.

``WasiHost`` is the narrow interface a real component binding must implement.
``ReferenceWasiHost`` simulates it in Python so the translation logic is testable
here.  Proof against a REAL runtime (wasmtime / jco / wasmer with a compiled
component) is not in this archive: ``detect_runtimes`` reports what exists and the
interop gate stays BLOCKED until a runtime + compiled fixture are supplied.
"""
from __future__ import annotations

import importlib.util
import shutil
import threading
import time
from typing import Protocol, Sequence

try:
    from .polling import (MIGRATION_TARGET, POLL_SCHEMA, PollValidationError, ForeignPollable,
                          MAX_POLL_DURATION_SECONDS)
    from .clock import ticks_to_ns, DEFAULT_CLOCK_CONFIG
except ImportError:
    from polling import (MIGRATION_TARGET, POLL_SCHEMA, PollValidationError, ForeignPollable,
                         MAX_POLL_DURATION_SECONDS)
    from clock import ticks_to_ns, DEFAULT_CLOCK_CONFIG

WASI_IO = "wasi:io/poll@0.2.0"
WASI_CLOCK = "wasi:clocks/monotonic-clock@0.2.0"


class WasiHost(Protocol):
    def subscribe_duration(self, ns: int) -> int: ...
    def poll(self, handles: Sequence[int]) -> list: ...
    def drop(self, handle: int) -> None: ...
    def owner_of(self, handle: int) -> str: ...


class ReferenceWasiHost:
    """In-process simulation of wasi:io pollables + monotonic-clock timers."""

    def __init__(self):
        self._cv = threading.Condition()
        self._next = 1
        self._ready: dict = {}
        self._deadline: dict = {}
        self._owner: dict = {}
        self.live = set()

    def new_pollable(self, owner: str) -> int:
        with self._cv:
            h = self._next
            self._next += 1
            self._ready[h], self._owner[h] = False, owner
            self.live.add(h)
            return h

    def set_ready(self, h: int) -> None:
        with self._cv:
            self._ready[h] = True
            self._cv.notify_all()

    def subscribe_duration(self, ns: int) -> int:
        with self._cv:
            h = self._next
            self._next += 1
            self._deadline[h] = time.monotonic() + ns / 1e9
            self._owner[h] = "<host-timer>"
            self.live.add(h)
            return h

    def _is_ready(self, h):
        if h in self._deadline:
            return time.monotonic() >= self._deadline[h]
        return self._ready.get(h, False)

    def poll(self, handles):
        if not handles:
            raise RuntimeError("wasi:io/poll.poll trap: empty list")
        with self._cv:
            while True:
                r = [i for i, h in enumerate(handles) if self._is_ready(h)]
                if r:
                    return r
                dls = [self._deadline[h] for h in handles if h in self._deadline]
                self._cv.wait(max(0.0, min(dls) - time.monotonic()) if dls else None)

    def drop(self, h):
        with self._cv:
            self._deadline.pop(h, None)
            self.live.discard(h)

    def owner_of(self, h):
        return self._owner.get(h, "")


class WasiPollAdapter:
    def __init__(self, host, owner: str, *, clock_config: dict = DEFAULT_CLOCK_CONFIG, max_pollables: int = 4096):
        self.host, self.owner, self.cfg, self.max_pollables = host, owner, clock_config, max_pollables

    def poll(self, names: Sequence[str], handles: Sequence[int], *, timeout_ticks: int) -> dict:
        if not isinstance(timeout_ticks, int) or isinstance(timeout_ticks, bool) or timeout_ticks <= 0:
            raise PollValidationError("positive integer timeout required", code="PK_POLL_INVALID_TIMEOUT")
        names, handles = list(names), list(handles)
        if not handles:
            raise PollValidationError("poll on an empty set would trap in wasi:io", code="PK_POLL_EMPTY_SET")
        if len(handles) != len(names):
            raise PollValidationError("names and handles differ in length", code="PK_POLL_INVALID_SET")
        if len(handles) > self.max_pollables:
            raise PollValidationError("set exceeds capacity", code="PK_POLL_SET_LIMIT")
        if len(set(handles)) != len(handles):
            raise PollValidationError("duplicate handle", code="PK_POLL_DUPLICATE_HANDLE")
        if len(set(names)) != len(names):
            raise PollValidationError("duplicate name", code="PK_POLL_DUPLICATE_NAME")
        try:
            ns = ticks_to_ns(timeout_ticks, self.cfg)
        except Exception:
            raise PollValidationError("timeout exceeds configured ceiling", code="PK_POLL_TIMEOUT_LIMIT") from None
        if ns > MAX_POLL_DURATION_SECONDS * 1e9:
            raise PollValidationError("duration ceiling", code="PK_POLL_DURATION_LIMIT")
        foreign = [n for n, h in zip(names, handles) if self.host.owner_of(h) != self.owner]
        if foreign:
            raise ForeignPollable("foreign pollables do not compose", details={"foreign_pollables": foreign})
        timer = self.host.subscribe_duration(ns)
        try:
            idx = self.host.poll(handles + [timer])
        finally:
            self.host.drop(timer)
        n = len(handles)
        ready_idx = sorted(i for i in idx if isinstance(i, int) and 0 <= i < n)
        return {"schema": POLL_SCHEMA, "owner": self.owner, "ready": [names[i] for i in ready_idx],
                "ready_indexes": ready_idx, "timed_out": not ready_idx, "timeout_ticks": timeout_ticks,
                "set_size": n, "deprecated": True, "migrate_to": MIGRATION_TARGET}


def detect_runtimes() -> dict:
    """Report which real WASI 0.2 runtimes are present; used by the interop gate."""
    return {"wasmtime_cli": shutil.which("wasmtime") is not None,
            "wasmtime_py": importlib.util.find_spec("wasmtime") is not None,
            "jco": shutil.which("jco") is not None,
            "wasm_tools": shutil.which("wasm-tools") is not None,
            "compiled_fixture": False}
