"""Stream transports: TCP fallback (G12-A005), dual-stack racing / Happy
Eyeballs v2 (G12-A014), TLS/TCP fallback (G12-A016) and the QUIC slot
(G12-A015).

Every connect is bounded by a hard deadline enforced with non-blocking
sockets and ``select`` — never by a blocking ``connect()`` — so a black-holed
SYN cannot hold a thread past its budget, and losing racers are closed the
moment a winner appears (no half-open sockets are leaked; ``open_sockets()``
is exposed for tests).

TCP settings on an established path: TCP_NODELAY, SO_KEEPALIVE with
TCP_KEEPIDLE/INTVL/CNT (Linux), bounded send buffer for backpressure.

QUIC: no QUIC implementation exists in the Python standard library and the
build forbids third-party runtime dependencies, so ``QuicAdapter.connect``
returns reason ``UNSUPPORTED`` and the controller falls back to TLS/TCP.  This is
reported NOT-EVIDENCED for every G12-A015 item, never PASS.
"""
from __future__ import annotations

import errno
import ipaddress
import select
import socket
import ssl
import time
from dataclasses import dataclass, field

CONNECTION_ATTEMPT_DELAY = 0.25     # RFC 8305 section 5 recommended default
MIN_ATTEMPT_DELAY, MAX_ATTEMPT_DELAY = 0.01, 2.0
HISTORY_WEIGHT_CAP = 3              # bounded influence of past failures (starvation guard)

_OPEN: set[int] = set()


def open_sockets() -> int:
    return len(_OPEN)


def _track(s: socket.socket) -> socket.socket:
    _OPEN.add(id(s))
    return s


def _close(s: socket.socket) -> None:
    _OPEN.discard(id(s))
    try:
        s.close()
    except OSError:
        pass


@dataclass
class ConnectResult:
    ok: bool
    reason: str
    sock: socket.socket | None = None
    address: tuple[str, int] | None = None
    family: int | None = None
    elapsed: float = 0.0
    attempts: list[dict] = field(default_factory=list)


def _errno_reason(e: int) -> str:
    if e == errno.ECONNREFUSED:
        return "NET_REFUSED"
    if e in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EADDRNOTAVAIL, errno.EAFNOSUPPORT):
        return "NET_UNREACHABLE"
    if e in (errno.EPERM, errno.EACCES):
        return "NET_FILTERED"
    return "NET_UNREACHABLE"


def configure_stream(s: socket.socket, *, keepalive_idle: int = 30, keepalive_interval: int = 10,
                     keepalive_count: int = 3, sndbuf: int = 256 * 1024) -> None:
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    for opt, val in (("TCP_KEEPIDLE", keepalive_idle), ("TCP_KEEPINTVL", keepalive_interval),
                     ("TCP_KEEPCNT", keepalive_count)):
        if hasattr(socket, opt):
            s.setsockopt(socket.IPPROTO_TCP, getattr(socket, opt), val)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sndbuf)


def interleave(addresses: list[tuple[str, int]], *, prefer_v6: bool = True, history: dict | None = None) -> list[tuple[str, int]]:
    """RFC 8305 section 4: alternate families, preferred family first.

    ``history`` maps family (4/6) -> recent consecutive failures; its influence
    is capped at HISTORY_WEIGHT_CAP so one family is demoted, never starved.
    """
    v6 = [a for a in addresses if ipaddress.ip_address(a[0]).version == 6]
    v4 = [a for a in addresses if ipaddress.ip_address(a[0]).version == 4]
    first, second = (v6, v4) if prefer_v6 else (v4, v6)
    if history:
        f6, f4 = min(history.get(6, 0), HISTORY_WEIGHT_CAP), min(history.get(4, 0), HISTORY_WEIGHT_CAP)
        if prefer_v6 and f6 > f4 + 1:
            first, second = v4, v6
        elif not prefer_v6 and f4 > f6 + 1:
            first, second = v6, v4
    out = []
    for i in range(max(len(first), len(second))):
        if i < len(first):
            out.append(first[i])
        if i < len(second):
            out.append(second[i])
    return out


def race(addresses: list[tuple[str, int]], *, deadline_s: float = 5.0, attempt_delay: float = CONNECTION_ATTEMPT_DELAY,
         prefer_v6: bool = True, history: dict | None = None, source: dict | None = None,
         clock=time.monotonic) -> ConnectResult:
    """Happy Eyeballs connection racing with cancellation of losers.

    ``source`` optionally maps family -> source IP to pin (G12-B022).
    """
    if not MIN_ATTEMPT_DELAY <= attempt_delay <= MAX_ATTEMPT_DELAY:
        raise ValueError("attempt_delay outside RFC 8305 bounds")
    order = interleave(addresses, prefer_v6=prefer_v6, history=history)
    start = clock()
    end = start + deadline_s
    pending: dict[socket.socket, tuple[str, int]] = {}
    attempts: list[dict] = []
    last_reason = "NET_TIMEOUT"
    idx = 0
    next_start = start
    try:
        while clock() < end:
            now = clock()
            if idx < len(order) and (now >= next_start or not pending):
                addr = order[idx]
                idx += 1
                fam = socket.AF_INET6 if ipaddress.ip_address(addr[0]).version == 6 else socket.AF_INET
                rec = {"address": f"{addr[0]}:{addr[1]}", "family": 6 if fam == socket.AF_INET6 else 4,
                       "started": round(now - start, 4)}
                attempts.append(rec)
                try:
                    s = _track(socket.socket(fam, socket.SOCK_STREAM))
                except OSError as exc:
                    rec["outcome"] = _errno_reason(exc.errno)
                    last_reason = rec["outcome"]
                    continue
                s.setblocking(False)
                try:
                    if source and source.get(rec["family"]):
                        s.bind((source[rec["family"]], 0))
                    rc = s.connect_ex(addr)
                except OSError as exc:
                    rc = exc.errno
                if rc not in (0, errno.EINPROGRESS):
                    rec["outcome"] = _errno_reason(rc)
                    last_reason = rec["outcome"]
                    _close(s)
                    continue
                pending[s] = addr
                next_start = now + attempt_delay
            if not pending:
                if idx >= len(order):
                    break
                continue
            wait = max(0.0, min(end, next_start if idx < len(order) else end) - clock())
            _, w, _ = select.select([], list(pending), [], wait)
            for s in w:
                err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                addr = pending.pop(s)
                rec = next(a for a in attempts if a["address"] == f"{addr[0]}:{addr[1]}" and "outcome" not in a)
                if err == 0:
                    rec["outcome"] = "OK"
                    s.setblocking(True)
                    configure_stream(s)
                    for loser in list(pending):
                        lrec = next(a for a in attempts if a["address"] == f"{pending[loser][0]}:{pending[loser][1]}" and "outcome" not in a)
                        lrec["outcome"] = "CANCELLED_DEADLINE" if False else "cancelled-loser"
                        _close(loser)
                    pending.clear()
                    _OPEN.discard(id(s))
                    return ConnectResult(True, "OK", s, addr, s.family, clock() - start, attempts)
                rec["outcome"] = _errno_reason(err)
                last_reason = rec["outcome"]
                _close(s)
        for s, addr in pending.items():
            _close(s)
            for a in attempts:
                if a["address"] == f"{addr[0]}:{addr[1]}" and "outcome" not in a:
                    a["outcome"] = "CANCELLED_DEADLINE"
            last_reason = "CANCELLED_DEADLINE"
        pending.clear()
        return ConnectResult(False, last_reason, None, None, None, clock() - start, attempts)
    finally:
        for s in pending:
            _close(s)


def tcp_connect(address: tuple[str, int], *, deadline_s: float = 3.0, source: dict | None = None) -> ConnectResult:
    """Single-address TCP fallback with a hard deadline (no indefinite connect)."""
    return race([address], deadline_s=deadline_s, source=source)


# --- TLS ------------------------------------------------------------------------------

def tls_context(*, cafile: str | None = None, min_version=ssl.TLSVersion.TLSv1_2) -> ssl.SSLContext:
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cafile)
    ctx.minimum_version = min_version
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")   # TLS1.2 AEAD-only; TLS1.3 suites are AEAD by definition
    return ctx


def tls_connect(address: tuple[str, int], server_name: str, ctx: ssl.SSLContext, *, deadline_s: float = 5.0,
                session: ssl.SSLSession | None = None) -> ConnectResult:
    """TLS over the TCP fallback; certificate/identity failures get their own reason code."""
    start = time.monotonic()
    r = tcp_connect(address, deadline_s=deadline_s)
    if not r.ok:
        return r
    remaining = max(0.05, deadline_s - (time.monotonic() - start))
    raw = r.sock
    raw.settimeout(remaining)
    try:
        tls = ctx.wrap_socket(raw, server_hostname=server_name, session=session)
        tls.settimeout(None)
        r.sock, r.reason = tls, "OK"
        return r
    except ssl.SSLCertVerificationError:
        reason = "AUTH_TLS_CERT"
    except ssl.SSLError as exc:
        reason = "AUTH_TLS_CERT" if "CERTIFICATE" in str(exc).upper() else "AUTH_FAILED"
    except socket.timeout:
        reason = "CANCELLED_DEADLINE"
    except OSError as exc:
        reason = _errno_reason(exc.errno or 0)
    raw.close()
    return ConnectResult(False, reason, None, address, None, time.monotonic() - start, r.attempts)


class QuicAdapter:
    """Explicitly unsupported in this build (see module docstring)."""

    name = "quic"
    supported = False

    def connect(self, *a, **k) -> ConnectResult:
        return ConnectResult(False, "UNSUPPORTED")
