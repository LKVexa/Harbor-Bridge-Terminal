"""MC-02 - Native Linux io_uring completion backend (raw syscalls via ctypes).

ABI boundary: the three io_uring syscalls (setup/enter/register) plus mmap of
the SQ ring, CQ ring and SQE array.  No liburing, no compiled shim.  Structure
layouts follow include/uapi/linux/io_uring.h (params 120 B, SQE 64 B, CQE 16 B).

Minimum kernel: 5.6 (IORING_OP_READ/WRITE/SEND/RECV/ASYNC_CANCEL); the probe
refuses selection when a required opcode is not reported supported.

Semantics class: completion.  Native resources are released by explicit
``close()`` (and a context manager), never by GC timing.  The ring fd is
O_CLOEXEC (kernel default, verified at open).  Fork: the ring belongs to the
creating pid; any call from another pid raises ``BackendClosed``.

Memory ordering: SQE/array stores precede the SQ tail store and the
``io_uring_enter`` syscall; on x86-64 (TSO) this is sufficient.  On arm64 the
same ordering is relied upon via the syscall boundary; arm64 is therefore
recorded as UNVERIFIED in the compatibility matrix until tested there.

Advanced features: SQPOLL, registered buffers, registered files and multishot
are explicitly DISABLED in this release (flags 0); enabling them is gated by
capability probing and must not change observable behaviour.
"""
from __future__ import annotations

import ctypes
import errno
import fcntl
import mmap
import os
import platform
import struct
import threading
import time
from typing import Iterable

from .errors import translate
from .native_base import BackendClosed, BackendUnavailable, CompletionEvent

SYS_SETUP, SYS_ENTER, SYS_REGISTER = 425, 426, 427
OFF_SQ_RING, OFF_CQ_RING, OFF_SQES = 0, 0x8000000, 0x10000000
ENTER_GETEVENTS = 1
SQ_CQ_OVERFLOW = 1 << 1   # IORING_SQ_CQ_OVERFLOW in the SQ ring flags word
SETUP_CQSIZE = 1 << 3
REGISTER_PROBE = 8
OP = {"nop": 0, "poll_add": 6, "async_cancel": 14, "read": 22, "write": 23, "send": 26, "recv": 27}
REQUIRED_OPS = ("nop", "read", "write", "async_cancel", "send", "recv")
MIN_KERNEL = (5, 6)
MAX_ENTRIES = 32768
SQE_SIZE, CQE_SIZE = 64, 16
CANCEL_USER_DATA_BIT = 1 << 63  # our own async_cancel SQEs are tagged; never an op id


class _Params(ctypes.Structure):
    _fields_ = [("sq_entries", ctypes.c_uint32), ("cq_entries", ctypes.c_uint32),
                ("flags", ctypes.c_uint32), ("sq_thread_cpu", ctypes.c_uint32),
                ("sq_thread_idle", ctypes.c_uint32), ("features", ctypes.c_uint32),
                ("wq_fd", ctypes.c_uint32), ("resv", ctypes.c_uint32 * 3),
                ("sq_off", ctypes.c_uint32 * 8), ("sq_user_addr", ctypes.c_uint64),
                ("cq_off", ctypes.c_uint32 * 8), ("cq_user_addr", ctypes.c_uint64)]


_libc = None


def _syscall():
    global _libc
    if _libc is None:
        _libc = ctypes.CDLL(None, use_errno=True)
        _libc.syscall.restype = ctypes.c_long
    return _libc.syscall


def kernel_version() -> tuple[int, int]:
    rel = platform.release().split("-")[0].split(".")
    try:
        return int(rel[0]), int(rel[1])
    except (IndexError, ValueError):
        return (0, 0)


def _check_abi() -> None:
    if ctypes.sizeof(_Params) != 120:
        raise BackendUnavailable("io_uring", "ABI_MISMATCH", "io_uring_params size")


def probe() -> dict:
    """Operational probe: setup a tiny ring, query opcode support, tear down."""
    out = {"backend": "io_uring", "available": False, "reason": None, "kernel": ".".join(map(str, kernel_version())),
           "ops": {}, "features": 0}
    if platform.system() != "Linux":
        out["reason"] = "NOT_LINUX"
        return out
    if platform.machine() not in ("x86_64", "aarch64"):
        out["reason"] = "ARCH_UNSUPPORTED"
        return out
    try:
        with open("/proc/sys/kernel/io_uring_disabled") as fh:
            val = fh.read().strip()
            out["io_uring_disabled_sysctl"] = val
            if val == "2":
                out["reason"] = "ADMIN_DISABLED"
                return out
    except OSError:
        pass
    try:
        _check_abi()
        p = _Params()
        fd = _syscall()(SYS_SETUP, 4, ctypes.byref(p))
        if fd < 0:
            e = ctypes.get_errno()
            out["reason"] = {errno.ENOSYS: "ENOSYS", errno.EPERM: "EPERM_SECCOMP_OR_SYSCTL",
                             errno.EACCES: "EACCES", errno.ENOMEM: "ENOMEM", errno.EMFILE: "EMFILE",
                             errno.EINVAL: "EINVAL"}.get(e, f"ERRNO_{e}")
            return out
        try:
            out["features"] = p.features
            nops = 64
            buf = (ctypes.c_uint8 * (16 + 8 * nops))()
            r = _syscall()(SYS_REGISTER, fd, REGISTER_PROBE, buf, nops)
            if r < 0:
                out["reason"] = "PROBE_UNSUPPORTED"
                return out
            last = buf[0]
            for name, code in OP.items():
                flags = struct.unpack_from("<H", bytes(buf), 16 + 8 * code + 2)[0] if code <= last else 0
                out["ops"][name] = bool(flags & 1)
            missing = [o for o in REQUIRED_OPS if not out["ops"].get(o)]
            if missing:
                out["reason"] = "OPCODES_MISSING:" + ",".join(missing)
                return out
        finally:
            os.close(fd)
    except BackendUnavailable as exc:
        out["reason"] = exc.reason
        return out
    if kernel_version() < MIN_KERNEL:
        out["reason"] = "KERNEL_TOO_OLD"
        return out
    out["available"] = True
    out["reason"] = "OK"
    return out


class IoUring:
    name = "io_uring"
    semantics = "completion"

    def __init__(self, sq_entries: int = 64, cq_entries: int | None = None,
                 max_submit_retries: int = 8) -> None:
        cq_entries = cq_entries or sq_entries * 2
        for n, v in (("sq_entries", sq_entries), ("cq_entries", cq_entries)):
            if isinstance(v, bool) or not isinstance(v, int) or not (1 <= v <= MAX_ENTRIES):
                raise ValueError(f"{n} must be in [1, {MAX_ENTRIES}]")
        if cq_entries < sq_entries:
            raise ValueError("cq_entries must be >= sq_entries")
        _check_abi()
        self._pid = os.getpid()
        self._lock = threading.RLock()
        self._closed = False
        self._maps: list[mmap.mmap] = []
        self.max_submit_retries = max_submit_retries
        self.cq_overflow_seen = 0
        self.submitted = 0
        self.reaped = 0
        self.stale_cqes = 0
        self.cq_overflow_flushes = 0
        self._inflight: dict[int, list] = {}      # user_data -> keepalive buffers
        p = _Params()
        p.flags = SETUP_CQSIZE
        p.cq_entries = cq_entries
        fd = _syscall()(SYS_SETUP, sq_entries, ctypes.byref(p))
        if fd < 0:
            e = ctypes.get_errno()
            raise BackendUnavailable("io_uring", translate("io_uring", -e).code, f"errno={e}")
        self.fd = fd
        try:
            if not (fcntl.fcntl(fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC):
                fcntl.fcntl(fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
            self.params = p
            so, co = list(p.sq_off), list(p.cq_off)
            sq_size = so[6] + p.sq_entries * 4
            cq_size = co[5] + p.cq_entries * CQE_SIZE
            self._sq = mmap.mmap(fd, sq_size, mmap.MAP_SHARED | getattr(mmap, "MAP_POPULATE", 0),
                                 mmap.PROT_READ | mmap.PROT_WRITE, offset=OFF_SQ_RING)
            self._maps.append(self._sq)
            self._cq = mmap.mmap(fd, cq_size, mmap.MAP_SHARED | getattr(mmap, "MAP_POPULATE", 0),
                                 mmap.PROT_READ | mmap.PROT_WRITE, offset=OFF_CQ_RING)
            self._maps.append(self._cq)
            self._sqes = mmap.mmap(fd, p.sq_entries * SQE_SIZE, mmap.MAP_SHARED | getattr(mmap, "MAP_POPULATE", 0),
                                   mmap.PROT_READ | mmap.PROT_WRITE, offset=OFF_SQES)
            self._maps.append(self._sqes)
            self._sq_head, self._sq_tail, self._sq_mask, self._sq_n, self._sq_flags, self._sq_dropped, self._sq_array = so[:7]
            self._cq_head, self._cq_tail, self._cq_mask, self._cq_n, self._cq_overflow, self._cq_cqes = co[:6]
            if self._u32(self._sq, self._sq_n) != p.sq_entries or self._u32(self._cq, self._cq_n) != p.cq_entries:
                raise BackendUnavailable("io_uring", "RING_OFFSET_MISMATCH")
            self.sq_entries, self.cq_entries = p.sq_entries, p.cq_entries
        except BaseException:
            self._teardown()  # partial-initialisation rollback
            raise

    # ------------------------------------------------------------------ ring access
    @staticmethod
    def _u32(m: mmap.mmap, off: int) -> int:
        return struct.unpack_from("<I", m, off)[0]

    @staticmethod
    def _w32(m: mmap.mmap, off: int, v: int) -> None:
        struct.pack_into("<I", m, off, v & 0xFFFFFFFF)

    def _guard(self) -> None:
        if self._closed:
            raise BackendClosed("io_uring closed")
        if os.getpid() != self._pid:
            raise BackendClosed("io_uring used across fork; child must create its own ring")

    def sq_space(self) -> int:
        head = self._u32(self._sq, self._sq_head)
        tail = self._u32(self._sq, self._sq_tail)
        return self.sq_entries - ((tail - head) & 0xFFFFFFFF)

    # ------------------------------------------------------------------ submission
    def _prep(self, opcode: int, fd: int, addr: int, length: int, off: int, user_data: int,
              op_flags: int = 0) -> None:
        tail = self._u32(self._sq, self._sq_tail)
        head = self._u32(self._sq, self._sq_head)
        if ((tail - head) & 0xFFFFFFFF) >= self.sq_entries:
            raise BlockingIOError(errno.EBUSY, "SQ full")
        idx = tail & self._u32(self._sq, self._sq_mask)
        base = idx * SQE_SIZE
        self._sqes[base:base + SQE_SIZE] = b"\0" * SQE_SIZE
        struct.pack_into("<BBHiQQIIQ", self._sqes, base, opcode, 0, 0, fd, off & 0xFFFFFFFFFFFFFFFF,
                         addr, length, op_flags, user_data)
        self._w32(self._sq, self._sq_array + 4 * idx, idx)
        self._w32(self._sq, self._sq_tail, tail + 1)  # publish after SQE is written

    def _enter(self, to_submit: int, min_complete: int, flags: int) -> int:
        tries = 0
        while True:
            r = _syscall()(SYS_ENTER, self.fd, to_submit, min_complete, flags, None, 0)
            if r >= 0:
                return r
            e = ctypes.get_errno()
            if e == errno.EINTR and tries < self.max_submit_retries:
                tries += 1
                continue
            if e in (errno.EAGAIN, errno.EBUSY) and tries < self.max_submit_retries:
                tries += 1
                self._drain_into_buffer()  # CQ pressure: reap to make room
                continue
            raise OSError(e, os.strerror(e))

    def submit(self, opcode: str, fd: int, user_data: int, *, buf=None, length: int = 0,
               offset: int = -1, flags: int = 0) -> None:
        """Queue and submit one SQE. ``buf`` is pinned until the CQE is reaped."""
        with self._lock:
            self._guard()
            if opcode not in OP:
                raise ValueError(f"unsupported opcode {opcode}")
            if user_data & CANCEL_USER_DATA_BIT:
                raise ValueError("user_data high bit is reserved")
            if user_data in self._inflight:
                raise ValueError("user_data already in flight (ID reuse while observable)")
            if isinstance(fd, bool) or not isinstance(fd, int) or fd < -1:
                raise ValueError("invalid descriptor")
            if opcode not in ("nop",) and fd >= 0:
                try:
                    os.fstat(fd)
                except OSError:
                    raise OSError(errno.EBADF, "descriptor closed before submission") from None
            addr = ctypes.addressof(buf) if buf is not None else 0
            self._prep(OP[opcode], fd, addr, length, offset, user_data, flags)
            self._inflight[user_data] = [buf]
            n = self._enter(1, 0, 0)
            if n != 1:  # short submit: the SQE stays queued; the next enter submits it
                self._enter(0, 0, 0)
            self.submitted += 1

    def cancel(self, user_data: int) -> bool:
        """Request native cancellation. Returns False if not in flight (already reaped)."""
        with self._lock:
            self._guard()
            if user_data not in self._inflight:
                return False
            self._prep(OP["async_cancel"], -1, user_data, 0, 0, user_data | CANCEL_USER_DATA_BIT)
            self._enter(1, 0, 0)
            return True

    # ------------------------------------------------------------------ completion
    _pending: list

    def _drain_into_buffer(self) -> None:
        self._pending = getattr(self, "_pending", [])
        self._pending.extend(self._reap_raw(1 << 16))

    def _reap_raw(self, max_events: int) -> list[tuple[int, int, int]]:
        out = []
        head = self._u32(self._cq, self._cq_head)
        tail = self._u32(self._cq, self._cq_tail)
        mask = self._u32(self._cq, self._cq_mask)
        while head != tail and len(out) < max_events:
            ud, res, fl = struct.unpack_from("<QiI", self._cq, self._cq_cqes + (head & mask) * CQE_SIZE)
            out.append((ud, res, fl))
            head = (head + 1) & 0xFFFFFFFF
        self._w32(self._cq, self._cq_head, head)
        ov = self._u32(self._cq, self._cq_overflow)
        if ov != self.cq_overflow_seen:
            self.cq_overflow_seen = ov
        return out

    def wait(self, timeout: float | None = 0.0, max_events: int = 256) -> list[CompletionEvent]:
        """Reap up to ``max_events`` CQEs. Negative ``res`` -> CanonicalError."""
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
        spins = 0
        while True:
            with self._lock:
                self._guard()
                raw = getattr(self, "_pending", [])
                self._pending = raw[max_events:]
                raw = raw[:max_events]
                raw += self._reap_raw(max_events - len(raw))
                events = []
                for ud, res, fl in raw:
                    if ud & CANCEL_USER_DATA_BIT:
                        continue  # result of our own cancel request
                    if self._inflight.pop(ud, None) is None:
                        self.stale_cqes += 1
                        continue  # stale / duplicate - never delivered
                    self.reaped += 1
                    if res < 0:
                        events.append(CompletionEvent(ud, None, translate("io_uring", res), fl))
                    else:
                        events.append(CompletionEvent(ud, res, None, fl))
                if events or not self._inflight:
                    return events
            # CQ overflow: with IORING_FEAT_NODROP the kernel parks overflowed
            # CQEs and every later CQE queues behind them until an enter with
            # GETEVENTS flushes the backlog.  Without this, one overflow
            # stalls the ring permanently (found by tools/soak.py burst).
            with self._lock:
                if not self._closed and (self._u32(self._sq, self._sq_flags) & SQ_CQ_OVERFLOW or spins % 16 == 0):
                    if self._u32(self._sq, self._sq_flags) & SQ_CQ_OVERFLOW:
                        self.cq_overflow_flushes += 1
                    try:
                        _syscall()(SYS_ENTER, self.fd, 0, 0, ENTER_GETEVENTS, None, 0)
                    except OSError:
                        pass
            if deadline is not None and time.monotonic() >= deadline:
                return events
            # adaptive wait: brief spin, then short sleeps (lock released so
            # cancel/submit from other threads are never blocked by a waiter)
            spins += 1
            if spins > 50:
                time.sleep(min(0.001, 0.00005 * (spins - 50)))

    @property
    def inflight(self) -> int:
        with self._lock:
            return len(self._inflight)

    # ------------------------------------------------------------------ shutdown
    def close(self, drain_timeout: float = 1.0) -> dict:
        """Cancel in-flight work, drain CQEs (bounded), then unmap and close."""
        report = {"cancelled": 0, "drained": 0, "abandoned": 0}
        with self._lock:
            if self._closed:
                return report
            if os.getpid() == self._pid:
                for ud in list(self._inflight):
                    try:
                        if self.cancel(ud):
                            report["cancelled"] += 1
                    except OSError:
                        break
        end = time.monotonic() + drain_timeout
        while self._inflight and time.monotonic() < end and not self._closed:
            report["drained"] += len(self.wait(0.01))
        with self._lock:
            report["abandoned"] = len(self._inflight)
            self._teardown()
        return report

    def _teardown(self) -> None:
        for m in self._maps:
            try:
                m.close()
            except Exception:
                pass
        self._maps.clear()
        fd = getattr(self, "fd", -1)
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
            self.fd = -1
        self._inflight = {}
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def run_selftest() -> dict:
    """Real host I/O: pipe write then read through the ring, plus cancel + EBADF."""
    r, w = os.pipe()
    out = {}
    try:
        with IoUring(8) as ring:
            data = (ctypes.c_char * 5).from_buffer_copy(b"hello")
            ring.submit("write", w, 1, buf=data, length=5, offset=-1)
            buf = (ctypes.c_char * 16)()
            ring.submit("read", r, 2, buf=buf, length=16, offset=-1)
            evs = {}
            end = time.monotonic() + 2
            while len(evs) < 2 and time.monotonic() < end:
                for e in ring.wait(0.05):
                    evs[e.op_id] = e
            out["write"] = evs.get(1) and evs[1].result
            out["read"] = evs.get(2) and evs[2].result
            out["bytes"] = bytes(buf.raw[: out["read"] or 0])
    finally:
        os.close(r)
        os.close(w)
    return out
