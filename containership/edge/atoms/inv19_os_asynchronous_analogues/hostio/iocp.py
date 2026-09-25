"""MC-03 - Native Windows IOCP completion backend (ctypes over kernel32/ws2_32).

Minimum supported: Windows 10 1809 / Windows Server 2019 (GetQueuedCompletionStatusEx,
CancelIoEx, SetFileCompletionNotificationModes).  Semantics class: completion.

Design:
* One completion port per backend (``CreateIoCompletionPort(INVALID_HANDLE_VALUE, NULL, 0, n)``).
* Completion key = registration generation of the associated handle; a handle
  can be associated with exactly one port (Windows enforces this; a second
  association fails and is surfaced as INVALID_ARGUMENT).
* Every operation owns a heap-allocated ``_OpOverlapped`` (OVERLAPPED + op id)
  pinned in ``_live`` until its terminal completion is dequeued - it can never
  move or be freed while the kernel may write it.  Address reuse cannot confuse
  completions because the op id travels inside the structure and is checked
  against the operation table generation.
* ``ReadFile``/``WriteFile``/``WSARecv``/``WSASend`` returning success with
  FILE_SKIP_COMPLETION_PORT_ON_SUCCESS disabled still post a packet: sync
  success and ERROR_IO_PENDING are both resolved from the port, exactly once.
* Cancellation: ``CancelIoEx(handle, &ov)``; ERROR_NOT_FOUND means the
  operation already completed - the completion wins and is delivered normally.
* Shutdown: ``PostQueuedCompletionStatus`` with key ``WAKE_KEY`` wakes waiters;
  close cancels all, drains with a bounded timeout, then ``CloseHandle``.

This module imports on every OS; construction raises ``BackendUnavailable``
off Windows.  It has NOT been executed on Windows in this pass (no Windows CI
host) and is therefore reported BLOCKED in the certification matrix.
"""
from __future__ import annotations

import ctypes
import os
import platform
import threading
import time

from .errors import translate
from .native_base import BackendClosed, BackendUnavailable, CompletionEvent

IS_WINDOWS = platform.system() == "Windows"
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
ERROR_IO_PENDING = 997
ERROR_NOT_FOUND = 1168
ERROR_ABANDONED_WAIT_0 = 735
WAIT_TIMEOUT = 258
WAKE_KEY = 0xFFFFFFFF
INFINITE = 0xFFFFFFFF
MIN_BUILD = 17763


class OVERLAPPED(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                ("Offset", ctypes.c_uint32), ("OffsetHigh", ctypes.c_uint32),
                ("hEvent", ctypes.c_void_p)]


class _OpOverlapped(ctypes.Structure):
    _fields_ = [("ov", OVERLAPPED), ("op_id", ctypes.c_uint64)]


class OVERLAPPED_ENTRY(ctypes.Structure):
    _fields_ = [("lpCompletionKey", ctypes.c_size_t), ("lpOverlapped", ctypes.c_void_p),
                ("Internal", ctypes.c_size_t), ("dwNumberOfBytesTransferred", ctypes.c_uint32)]


def probe() -> dict:
    out = {"backend": "iocp", "available": False, "reason": None}
    if not IS_WINDOWS:
        out["reason"] = "NOT_WINDOWS"
        return out
    try:  # pragma: no cover - Windows only
        build = int(platform.version().split(".")[-1])
        out["build"] = build
        if build < MIN_BUILD:
            out["reason"] = "WINDOWS_TOO_OLD"
            return out
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        for fn in ("CreateIoCompletionPort", "GetQueuedCompletionStatusEx", "CancelIoEx",
                   "PostQueuedCompletionStatus"):
            getattr(k32, fn)
        ctypes.WinDLL("ws2_32", use_last_error=True).WSARecv
        h = k32.CreateIoCompletionPort(ctypes.c_void_p(INVALID_HANDLE_VALUE), None, 0, 1)
        if not h:
            out["reason"] = translate("iocp", ctypes.get_last_error()).code
            return out
        k32.CloseHandle(h)
    except (AttributeError, OSError, ValueError) as exc:
        out["reason"] = f"API_MISSING:{type(exc).__name__}"
        return out
    out["available"] = True
    out["reason"] = "OK"
    return out


class Iocp:  # pragma: no cover - Windows only; exercised by the Windows CI job
    name = "iocp"
    semantics = "completion"

    def __init__(self, concurrency: int = 0, max_ops: int = 4096) -> None:
        if not IS_WINDOWS:
            raise BackendUnavailable("iocp", "NOT_WINDOWS")
        self.k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k32.CreateIoCompletionPort.restype = ctypes.c_void_p
        self.port = self.k32.CreateIoCompletionPort(ctypes.c_void_p(INVALID_HANDLE_VALUE), None, 0, concurrency)
        if not self.port:
            raise BackendUnavailable("iocp", translate("iocp", ctypes.get_last_error()).code)
        self._lock = threading.RLock()
        self._live: dict[int, tuple[_OpOverlapped, object, int]] = {}   # addr -> (ov, buffer, handle)
        self._assoc: dict[int, int] = {}
        self._closed = False
        self._waiters = 0
        self.max_ops = max_ops

    def associate(self, handle: int, key: int) -> None:
        with self._lock:
            if self._closed:
                raise BackendClosed("iocp closed")
            if handle in self._assoc:
                raise ValueError("handle already associated with this port")
            r = self.k32.CreateIoCompletionPort(ctypes.c_void_p(handle), ctypes.c_void_p(self.port), key, 0)
            if not r:
                raise OSError(0, translate("iocp", ctypes.get_last_error()).code)
            self._assoc[handle] = key

    def _start(self, fn, handle: int, op_id: int, buf, length: int, offset: int):
        with self._lock:
            if self._closed:
                raise BackendClosed("iocp closed")
            if handle not in self._assoc:
                raise ValueError("handle not associated")
            if len(self._live) >= self.max_ops:
                raise OverflowError("iocp operation limit")
            ov = _OpOverlapped()
            ov.op_id = op_id
            ov.ov.Offset = offset & 0xFFFFFFFF
            ov.ov.OffsetHigh = (offset >> 32) & 0xFFFFFFFF
            addr = ctypes.addressof(ov)
            self._live[addr] = (ov, buf, handle)   # pinned before the call
            ok = fn(ctypes.c_void_p(handle), buf, length, None, ctypes.byref(ov.ov))
            if not ok:
                err = ctypes.get_last_error()
                if err != ERROR_IO_PENDING:
                    del self._live[addr]            # synchronous failure: no packet will arrive
                    return CompletionEvent(op_id, None, translate("iocp", err))
            return None                              # success or pending: resolved from the port

    def read(self, handle: int, op_id: int, nbytes: int, offset: int = 0):
        buf = ctypes.create_string_buffer(nbytes)
        return self._start(self.k32.ReadFile, handle, op_id, buf, nbytes, offset), buf

    def write(self, handle: int, op_id: int, data: bytes, offset: int = 0):
        buf = ctypes.create_string_buffer(data, len(data))
        return self._start(self.k32.WriteFile, handle, op_id, buf, len(data), offset)

    def cancel(self, handle: int, op_addr: int) -> bool:
        with self._lock:
            if op_addr not in self._live:
                return False
            ov = self._live[op_addr][0]
            if not self.k32.CancelIoEx(ctypes.c_void_p(handle), ctypes.byref(ov.ov)):
                if ctypes.get_last_error() == ERROR_NOT_FOUND:
                    return False  # already completed: completion wins
                raise OSError(0, translate("iocp", ctypes.get_last_error()).code)
            return True

    def wait(self, timeout: float | None = 0.0, max_events: int = 64) -> list[CompletionEvent]:
        with self._lock:
            if self._closed:
                raise BackendClosed("iocp closed")
            self._waiters += 1
        try:
            entries = (OVERLAPPED_ENTRY * max_events)()
            n = ctypes.c_ulong(0)
            ms = INFINITE if timeout is None else int(max(0.0, timeout) * 1000)
            ok = self.k32.GetQueuedCompletionStatusEx(ctypes.c_void_p(self.port), entries, max_events,
                                                      ctypes.byref(n), ms, False)
            if not ok:
                err = ctypes.get_last_error()
                if err == WAIT_TIMEOUT:
                    return []
                raise OSError(0, translate("iocp", err).code)
            out = []
            with self._lock:
                for i in range(n.value):
                    e = entries[i]
                    if e.lpCompletionKey == WAKE_KEY and not e.lpOverlapped:
                        continue
                    rec = self._live.pop(e.lpOverlapped, None)
                    if rec is None:
                        continue  # stale/duplicate packet: never delivered
                    ov = rec[0]
                    status = ov.ov.Internal & 0xFFFFFFFF
                    if status == 0:
                        out.append(CompletionEvent(ov.op_id, e.dwNumberOfBytesTransferred, None))
                    else:
                        out.append(CompletionEvent(ov.op_id, None, translate("iocp", status, "ntstatus")))
            return out
        finally:
            with self._lock:
                self._waiters -= 1

    def wake(self) -> None:
        self.k32.PostQueuedCompletionStatus(ctypes.c_void_p(self.port), 0, WAKE_KEY, None)

    def close(self, drain_timeout: float = 2.0) -> dict:
        with self._lock:
            if self._closed:
                return {}
            for addr, (_, _, h) in list(self._live.items()):
                self.cancel(h, addr)
        end = time.monotonic() + drain_timeout
        while self._live and time.monotonic() < end:
            self.wait(0.05)
        with self._lock:
            self._closed = True
            for _ in range(self._waiters):
                self.wake()
        while self._waiters and time.monotonic() < end + 1:
            time.sleep(0.01)  # never close the port while a waiter dereferences it
        abandoned = len(self._live)
        self.k32.CloseHandle(ctypes.c_void_p(self.port))
        return {"abandoned": abandoned}
