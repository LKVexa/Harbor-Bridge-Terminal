"""MC-04 epoll, MC-05 kqueue and MC-06 portable readiness backends.

All three share one contract: ``register/modify/unregister/wait/wake/close``
producing :class:`ReadinessEvent` values with stale-safe tokens.  Readiness is
permission to *attempt* I/O, never a completion; ``ReadinessIO`` performs the
real non-blocking syscall afterwards so the underlying completion error (or
EAGAIN -> retry) is discovered by the syscall, not invented.

Policies:
* epoll: level-triggered by default; edge-triggered only with ``edge=True`` and
  then callers MUST drain until EAGAIN (``ReadinessIO.drain`` does this).
  EPOLLONESHOT is rejected (re-arm semantics are owned by INV-15 waitable sets).
  EPOLLERR/EPOLLHUP are always reported even if not requested.
* kqueue: EVFILT_READ/EVFILT_WRITE only; EV_EOF -> hup, EV_ERROR -> error; no
  EV_CLEAR/EV_ONESHOT in this release.
* portable: ``selectors.DefaultSelector`` + socketpair wakeup; available on
  every platform Python supports; engagement is counted and reported.
"""
from __future__ import annotations

import errno
import os
import select
import selectors
import socket
import threading
import time

from .errors import translate
from .native_base import (BackendClosed, BackendUnavailable, Interest, ReadinessEvent,
                          Registrations, require_nonblocking)

MAX_EVENTS_CAP = 65536


class _Wakeup:
    """Idempotent, overflow-proof wakeup channel (socketpair)."""

    def __init__(self) -> None:
        self.r, self.w = socket.socketpair()
        self.r.setblocking(False)
        self.w.setblocking(False)
        self._armed = threading.Event()

    def wake(self) -> None:
        if self._armed.is_set():
            return  # idempotent: one pending byte is enough
        self._armed.set()
        try:
            self.w.send(b"\0")
        except (BlockingIOError, OSError):
            pass  # buffer full means a wake is already pending: cannot overflow

    def drain(self) -> None:
        self._armed.clear()
        try:
            while self.r.recv(4096):
                pass
        except (BlockingIOError, OSError):
            pass

    def close(self) -> None:
        self.r.close()
        self.w.close()


class _ReadinessBase:
    semantics = "readiness"
    name = "?"

    def __init__(self, max_registrations: int = 1024, max_events: int = 256) -> None:
        if not (1 <= max_events <= MAX_EVENTS_CAP):
            raise ValueError("max_events out of range")
        self.regs = Registrations(max_registrations)
        self.max_events = max_events
        self._wake = _Wakeup()
        self._closed = False
        self._lock = threading.RLock()
        self.full_batches = 0
        self.eintr = 0
        self._rr = 0  # starvation guard rotation

    def _guard(self) -> None:
        if self._closed:
            raise BackendClosed(f"{self.name} closed")

    def wake(self) -> None:
        self._wake.wake()

    def _fairness(self, evs: list[ReadinessEvent]) -> list[ReadinessEvent]:
        # When the event array is repeatedly full, rotate the start so the
        # same descriptors cannot starve later ones.
        if len(evs) >= self.max_events:
            self.full_batches += 1
            self._rr = (self._rr + 1) % max(1, len(evs))
            return evs[self._rr:] + evs[: self._rr]
        return evs


class Epoll(_ReadinessBase):
    name = "epoll"

    def __init__(self, max_registrations: int = 1024, max_events: int = 256, edge: bool = False) -> None:
        if not hasattr(select, "epoll"):
            raise BackendUnavailable("epoll", "NOT_AVAILABLE")
        super().__init__(max_registrations, max_events)
        self.edge = edge
        self._ep = select.epoll(sizehint=max_registrations, flags=select.EPOLL_CLOEXEC)
        self._ep.register(self._wake.r.fileno(), select.EPOLLIN)

    def _mask(self, interest: int) -> int:
        m = select.EPOLLRDHUP if hasattr(select, "EPOLLRDHUP") else 0
        if interest & Interest.READ:
            m |= select.EPOLLIN
        if interest & Interest.WRITE:
            m |= select.EPOLLOUT
        if self.edge:
            m |= select.EPOLLET
        return m

    def register(self, fd: int, interest: int, owner: object = None) -> int:
        with self._lock:
            self._guard()
            require_nonblocking(fd)
            if interest & ~(Interest.READ | Interest.WRITE) or not interest:
                raise ValueError("interest must be READ and/or WRITE")
            tok = self.regs.add(fd, interest, owner)
            try:
                self._ep.register(fd, self._mask(interest))
            except OSError:
                self.regs.remove(fd)
                raise
            return tok

    def modify(self, fd: int, interest: int) -> int:
        with self._lock:
            self._guard()
            tok = self.regs.modify(fd, interest)
            self._ep.modify(fd, self._mask(interest))
            return tok

    def unregister(self, fd: int) -> None:
        with self._lock:
            self._guard()
            self.regs.remove(fd)
            try:
                self._ep.unregister(fd)
            except (OSError, ValueError):
                pass  # closed fd is auto-removed by the kernel

    def wait(self, timeout: float | None = 0.0) -> list[ReadinessEvent]:
        self._guard()
        while True:
            try:
                raw = self._ep.poll(-1 if timeout is None else timeout, self.max_events)
                break
            except InterruptedError:  # PEP 475 retries, kept for explicitness
                self.eintr += 1
        out = []
        wfd = self._wake.r.fileno()
        for fd, ev in raw:
            if fd == wfd:
                self._wake.drain()
                continue
            tok = self.regs.current_token(fd)
            if tok is None:
                self.regs.stale_events += 1
                continue
            out.append(ReadinessEvent(
                tok, fd, bool(ev & select.EPOLLIN), bool(ev & select.EPOLLOUT),
                bool(ev & select.EPOLLERR),
                bool(ev & (select.EPOLLHUP | getattr(select, "EPOLLRDHUP", 0)))))
        return self._fairness(out)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                self._ep.close()
                self._wake.close()


class Kqueue(_ReadinessBase):
    name = "kqueue"

    def __init__(self, max_registrations: int = 1024, max_events: int = 256) -> None:
        if not hasattr(select, "kqueue"):
            raise BackendUnavailable("kqueue", "NOT_AVAILABLE")
        super().__init__(max_registrations, max_events)
        self._kq = select.kqueue()
        self._interest: dict[int, int] = {}
        self._kq.control([select.kevent(self._wake.r.fileno(), select.KQ_FILTER_READ, select.KQ_EV_ADD)], 0, 0)

    def _apply(self, fd: int, old: int, new: int) -> None:
        ch = []
        for bit, filt in ((Interest.READ, select.KQ_FILTER_READ), (Interest.WRITE, select.KQ_FILTER_WRITE)):
            if new & bit and not old & bit:
                ch.append(select.kevent(fd, filt, select.KQ_EV_ADD))
            elif old & bit and not new & bit:
                ch.append(select.kevent(fd, filt, select.KQ_EV_DELETE))
        if ch:
            self._kq.control(ch, 0, 0)

    def register(self, fd: int, interest: int, owner: object = None) -> int:
        with self._lock:
            self._guard()
            require_nonblocking(fd)
            tok = self.regs.add(fd, interest, owner)
            try:
                self._apply(fd, 0, interest)
            except OSError:
                self.regs.remove(fd)
                raise
            self._interest[fd] = interest
            return tok

    def modify(self, fd: int, interest: int) -> int:
        with self._lock:
            tok = self.regs.modify(fd, interest)
            self._apply(fd, self._interest.get(fd, 0), interest)
            self._interest[fd] = interest
            return tok

    def unregister(self, fd: int) -> None:
        with self._lock:
            self.regs.remove(fd)
            try:
                self._apply(fd, self._interest.pop(fd, 0), 0)
            except OSError:
                pass

    def wait(self, timeout: float | None = 0.0) -> list[ReadinessEvent]:
        self._guard()
        raw = self._kq.control(None, self.max_events, timeout)
        merged: dict[int, list] = {}
        wfd = self._wake.r.fileno()
        for kev in raw:
            fd = kev.ident
            if fd == wfd:
                self._wake.drain()
                continue
            tok = self.regs.current_token(fd)
            if tok is None:
                self.regs.stale_events += 1
                continue
            m = merged.setdefault(fd, [tok, False, False, False, False])
            if kev.flags & select.KQ_EV_ERROR:
                m[3] = True
            if kev.filter == select.KQ_FILTER_READ:
                m[1] = True
            if kev.filter == select.KQ_FILTER_WRITE:
                m[2] = True
            if kev.flags & select.KQ_EV_EOF:
                m[4] = True
                if kev.fflags:
                    m[3] = True
        return self._fairness([ReadinessEvent(v[0], fd, v[1], v[2], v[3], v[4]) for fd, v in merged.items()])

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                self._kq.close()
                self._wake.close()


class Portable(_ReadinessBase):
    name = "portable"

    def __init__(self, max_registrations: int = 1024, max_events: int = 256) -> None:
        super().__init__(max_registrations, max_events)
        self._sel = selectors.DefaultSelector()
        self.selector_impl = type(self._sel).__name__
        self._sel.register(self._wake.r, selectors.EVENT_READ, None)

    @staticmethod
    def _mask(interest: int) -> int:
        m = 0
        if interest & Interest.READ:
            m |= selectors.EVENT_READ
        if interest & Interest.WRITE:
            m |= selectors.EVENT_WRITE
        return m

    def register(self, fd: int, interest: int, owner: object = None) -> int:
        with self._lock:
            self._guard()
            require_nonblocking(fd)
            if not interest:
                raise ValueError("empty interest")
            tok = self.regs.add(fd, interest, owner)
            try:
                self._sel.register(fd, self._mask(interest), tok)
            except (OSError, ValueError, KeyError):
                self.regs.remove(fd)
                raise
            return tok

    def modify(self, fd: int, interest: int) -> int:
        with self._lock:
            tok = self.regs.modify(fd, interest)
            self._sel.modify(fd, self._mask(interest), tok)
            return tok

    def unregister(self, fd: int) -> None:
        with self._lock:
            self.regs.remove(fd)
            try:
                self._sel.unregister(fd)
            except (KeyError, ValueError, OSError):
                pass

    def wait(self, timeout: float | None = 0.0) -> list[ReadinessEvent]:
        self._guard()
        out = []
        for key, ev in self._sel.select(timeout):
            if key.data is None:
                self._wake.drain()
                continue
            fd = key.fd
            tok = self.regs.current_token(fd)
            if tok is None or tok != key.data:
                self.regs.stale_events += 1
                continue
            # selectors folds error/hup into readable/writable; the follow-up
            # syscall in ReadinessIO discovers the concrete error.
            out.append(ReadinessEvent(tok, fd, bool(ev & selectors.EVENT_READ),
                                      bool(ev & selectors.EVENT_WRITE), False, False))
            if len(out) >= self.max_events:
                break
        return self._fairness(out)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                self._sel.close()
                self._wake.close()


class ReadinessIO:
    """Performs the real non-blocking syscall after readiness.

    Returns ("value", data|n) on success, ("value", b"") at EOF, ("retry", None)
    on EAGAIN, and ("error", CanonicalError) when the syscall fails - the error
    is discovered by retrying, never fabricated from the readiness flags.
    """

    def __init__(self, backend_name: str) -> None:
        self.backend = backend_name

    def read(self, fd: int, n: int = 65536):
        try:
            data = os.read(fd, n)
            return ("value", data)
        except BlockingIOError:
            return ("retry", None)
        except OSError as exc:
            return ("error", translate(self.backend, exc.errno))

    def write(self, fd: int, data: bytes):
        try:
            return ("value", os.write(fd, data))
        except BlockingIOError:
            return ("retry", None)
        except OSError as exc:
            return ("error", translate(self.backend, exc.errno))

    def drain(self, fd: int, n: int = 65536, limit: int = 1 << 20):
        """Edge-triggered contract: read until EAGAIN/EOF/error (bounded)."""
        chunks, total = [], 0
        while total < limit:
            kind, v = self.read(fd, n)
            if kind != "value":
                return (kind, v, b"".join(chunks))
            if not v:
                return ("eof", None, b"".join(chunks))
            chunks.append(v)
            total += len(v)
        return ("limit", None, b"".join(chunks))


def probe_epoll() -> dict:
    if not hasattr(select, "epoll"):
        return {"backend": "epoll", "available": False, "reason": "NOT_AVAILABLE"}
    try:
        e = Epoll(4, 4)
        r, w = os.pipe()
        os.set_blocking(r, False)
        e.register(r, Interest.READ)
        os.write(w, b"x")
        ok = any(ev.readable for ev in e.wait(0.5))
        e.close(); os.close(r); os.close(w)
        return {"backend": "epoll", "available": ok, "reason": "OK" if ok else "NO_EVENT"}
    except OSError as exc:
        return {"backend": "epoll", "available": False, "reason": translate("epoll", exc.errno).code}


def probe_kqueue() -> dict:
    if not hasattr(select, "kqueue"):
        return {"backend": "kqueue", "available": False, "reason": "NOT_AVAILABLE"}
    try:
        k = Kqueue(4, 4)
        r, w = os.pipe()
        os.set_blocking(r, False)
        k.register(r, Interest.READ)
        os.write(w, b"x")
        ok = any(ev.readable for ev in k.wait(0.5))
        k.close(); os.close(r); os.close(w)
        return {"backend": "kqueue", "available": ok, "reason": "OK" if ok else "NO_EVENT"}
    except OSError as exc:  # pragma: no cover - BSD only
        return {"backend": "kqueue", "available": False, "reason": translate("kqueue", exc.errno).code}


def probe_portable() -> dict:
    p = Portable(4, 4)
    impl = p.selector_impl
    p.close()
    return {"backend": "portable", "available": True, "reason": "OK", "selector": impl}
