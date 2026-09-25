"""virtio-vsock adapter (MC-03).

Socket operations live here, never in the cryptographic/session code
(MC-03.002).  The adapter provides:

* :func:`vsock_connect` - bounded connect with an explicit deadline, typed
  failures and no secret-bearing debug output;
* :class:`VsockListener` - bounded backlog, process-wide connection limit,
  per-CID accept-churn limiting (MC-03.009/.023/.026);
* :func:`platform_support` / :func:`local_cid` - capability discovery.

CID/port are **not** identities: every connection must complete PK_CTRL_HS/1
before any control message is processed (MC-03.028, docs/ADR-0001).

Supported: Linux (``AF_VSOCK``, kernel >= 4.8; host side needs
``vhost_vsock``, guest side ``vmw_vsock_virtio_transport``).  Windows (Hyper-V
sockets) and macOS (Virtualization.framework) are **unsupported** by this
adapter and fail with :class:`~.stream.StreamUnavailable` (MC-03.001).
"""
from __future__ import annotations

import errno
import fcntl
import platform
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from .stream import SocketStream, StreamReset, StreamTimeout, StreamUnavailable

VMADDR_CID_ANY = getattr(socket, "VMADDR_CID_ANY", 0xFFFFFFFF)
VMADDR_CID_HOST = getattr(socket, "VMADDR_CID_HOST", 2)
VMADDR_CID_LOCAL = 1
IOCTL_VM_SOCKETS_GET_LOCAL_CID = 0x7B9
MIN_PORT = 1024           # ports < 1024 require CAP_NET_BIND_SERVICE on the host side
DEFAULT_PORT = 5036
DEFAULT_BUFFER = 256 * 1024
MAX_BUFFER = 4 * 1024 * 1024
MAX_BACKLOG = 128


def available() -> bool:
    return platform.system() == "Linux" and hasattr(socket, "AF_VSOCK")


def platform_support() -> dict:
    info = {"system": platform.system(), "machine": platform.machine(), "release": platform.release(),
            "af_vsock": hasattr(socket, "AF_VSOCK"), "dev_vsock": False, "local_cid": None, "tier": "unsupported"}
    if available():
        try:
            with open("/dev/vsock", "rb"):
                info["dev_vsock"] = True
        except OSError:
            pass
        info["local_cid"] = local_cid()
        info["tier"] = "device-present-uncertified" if info["dev_vsock"] else "no-device"
    return info


def local_cid() -> int | None:
    if not available():
        return None
    try:
        with open("/dev/vsock", "rb") as fh:
            raw = fcntl.ioctl(fh, IOCTL_VM_SOCKETS_GET_LOCAL_CID, b"\0" * 4)
        return struct.unpack("I", raw)[0]
    except OSError:
        return None


def _new_socket(buffer_bytes: int) -> socket.socket:
    if not available():
        raise StreamUnavailable("AF_VSOCK not available on this platform")
    if not 4096 <= buffer_bytes <= MAX_BUFFER:
        raise ValueError("buffer size out of range")
    try:
        s = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    except OSError as exc:
        raise StreamUnavailable(f"vsock socket unavailable: {errno.errorcode.get(exc.errno or 0, str(exc.errno))}") from exc
    for opt in ("SO_VM_SOCKETS_BUFFER_MAX_SIZE", "SO_VM_SOCKETS_BUFFER_SIZE"):
        if hasattr(socket, opt):
            try:
                s.setsockopt(socket.AF_VSOCK, getattr(socket, opt), buffer_bytes)
            except OSError:
                pass  # transport may not support resizing; defaults remain bounded by the kernel
    return s


def _classify(exc: OSError, what: str) -> Exception:
    code = errno.errorcode.get(exc.errno or 0, str(exc.errno))
    if isinstance(exc, TimeoutError) or exc.errno in (errno.ETIMEDOUT,):
        return StreamTimeout(f"{what} timed out", detail={"errno": code})
    if exc.errno in (errno.ENODEV, errno.EADDRNOTAVAIL, errno.EAFNOSUPPORT, errno.ENETUNREACH, errno.EHOSTUNREACH):
        return StreamUnavailable(f"{what}: vsock endpoint unavailable", detail={"errno": code})
    return StreamReset(f"{what} failed", detail={"errno": code})


def vsock_connect(cid: int, port: int, *, timeout: float = 2.0, buffer_bytes: int = DEFAULT_BUFFER) -> SocketStream:
    if not 0 <= cid <= 0xFFFFFFFF or not 1 <= port <= 0xFFFFFFFF:
        raise ValueError("invalid vsock address")
    s = _new_socket(buffer_bytes)
    try:
        s.settimeout(timeout)
        s.connect((cid, port))
    except OSError as exc:
        s.close()  # deterministic descriptor release on every failure path (MC-03.010)
        raise _classify(exc, "connect") from exc
    return SocketStream(s)


@dataclass
class ChurnLimiter:
    """Per-source token bucket against connection churn (MC-03.026)."""

    rate_per_s: float = 5.0
    burst: int = 10
    max_sources: int = 4096
    clock: Callable[[], float] = time.monotonic
    _b: dict[int, tuple[float, float]] = field(default_factory=dict, init=False)

    def allow(self, source: int) -> bool:
        now = self.clock()
        tokens, t = self._b.get(source, (float(self.burst), now))
        tokens = min(self.burst, tokens + (now - t) * self.rate_per_s)
        if len(self._b) >= self.max_sources and source not in self._b:
            self._b.clear()
        if tokens < 1:
            self._b[source] = (tokens, now)
            return False
        self._b[source] = (tokens - 1, now)
        return True


@dataclass
class VsockListener:
    port: int = DEFAULT_PORT
    cid: int = VMADDR_CID_ANY
    backlog: int = 64
    max_connections: int = 256
    buffer_bytes: int = DEFAULT_BUFFER
    churn: ChurnLimiter = field(default_factory=ChurnLimiter)
    active: int = field(default=0, init=False)
    refused: dict[str, int] = field(default_factory=lambda: {"limit": 0, "churn": 0}, init=False)
    _sock: socket.socket | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def open(self) -> "VsockListener":
        if not 1 <= self.backlog <= MAX_BACKLOG:
            raise ValueError("backlog out of range")
        if self.port < MIN_PORT:
            raise ValueError("privileged vsock ports are not used by INV-36")
        s = _new_socket(self.buffer_bytes)
        try:
            s.bind((self.cid, self.port))
            s.listen(self.backlog)
        except OSError as exc:
            s.close()
            if exc.errno == errno.EADDRINUSE:
                raise StreamUnavailable("vsock port already in use (collision)", detail={"port": self.port}) from exc
            raise _classify(exc, "listen") from exc
        self._sock = s
        return self

    def accept(self, timeout: float | None = 1.0) -> tuple[SocketStream, tuple[int, int]] | None:
        if self._sock is None:
            raise StreamUnavailable("listener not open")
        self._sock.settimeout(timeout)
        try:
            conn, addr = self._sock.accept()
        except TimeoutError:
            return None
        except OSError as exc:
            raise _classify(exc, "accept") from exc
        cid = addr[0]
        with self._lock:
            if self.active >= self.max_connections:
                self.refused["limit"] += 1
                conn.close()
                return None
            if not self.churn.allow(cid):
                self.refused["churn"] += 1
                conn.close()
                return None
            self.active += 1
        return SocketStream(conn), addr

    def released(self) -> None:
        with self._lock:
            self.active = max(0, self.active - 1)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None


DEPLOYMENT_ROLES = {
    "host_to_guest": {"listener": "guest agent (CID >= 3, port 5036)", "initiator": "host agent",
                      "notes": "host initiates placements/leases; guest never trusts the CID"},
    "guest_to_host": {"listener": "host agent (CID 2 / VMADDR_CID_ANY on host, port 5036)",
                      "initiator": "guest agent", "notes": "guest reports status; host authorizes per policy"},
    "port_allocation": "5036 fixed per INV-36; collisions fail with StreamUnavailable at bind; "
                       "no wildcard ports; non-privileged (>=1024)",
    "privileges": "guest: none beyond /dev/vsock access; host: access to /dev/vhost-vsock via the VMM; "
                  "no CAP_NET_ADMIN, no root required for ports >= 1024",
}
