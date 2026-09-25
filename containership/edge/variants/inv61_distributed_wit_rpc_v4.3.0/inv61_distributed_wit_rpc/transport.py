"""M03/M08/M10 - real socket transport (TCP, optionally mutual TLS) for
PK_WRPC_FRAME/2, plus a multiplexing client with deadlines, cancellation,
reconnect and classified retry.

Connection lifecycle (server side):

    ACCEPTED -> (TLS handshake) -> AWAIT_HELLO -> READY -> DRAINING -> CLOSED

* Connection count is capped (``max_connections``); excess sockets are closed
  immediately.
* The first frame MUST be HELLO within ``handshake_timeout_s``; anything else
  closes the connection before the dispatcher is reachable.
* Headers are validated before any body buffer is allocated.
* Every read uses a socket timeout (idle timeout between frames).
* Requests on one connection are dispatched concurrently and responses are
  written under a per-connection write lock (multiplexing by request_id).
* ``drain()`` stops accepting, refuses new requests with ``draining`` and waits
  for in-flight calls before closing.
"""
from __future__ import annotations

import concurrent.futures as cf
import os
import secrets
import socket
import ssl
import threading
import time
import uuid
from typing import Any, Callable

from . import codec, negotiation
from .resilience import RetryPolicy
from .rpc import fingerprint
from .security import Key, sign
from .server import RpcService
from .wit_model import Interface


class TransportError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _read_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise TransportError("eof" if not buf else "truncated")
        buf += chunk
    return bytes(buf)


def read_frame(sock: socket.socket, limits: codec.Limits) -> tuple[int, int, int, bytes]:
    head = _read_exact(sock, codec.HEADER_SIZE)
    major, minor, kind, _flags, length = codec.parse_header(head, limits)  # before alloc
    body = _read_exact(sock, length) if length else b""
    return major, minor, kind, body


def server_tls_context(cert: str, key: str, ca: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(cert, key)
    ctx.load_verify_locations(ca)
    ctx.verify_mode = ssl.CERT_REQUIRED  # mutual TLS
    return ctx


def client_tls_context(cert: str, key: str, ca: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(cert, key)
    ctx.load_verify_locations(ca)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def _peer_cn(sock: Any) -> str | None:
    if not isinstance(sock, ssl.SSLSocket):
        return None
    cert = sock.getpeercert() or {}
    for rdn in cert.get("subject", ()):
        for k, v in rdn:
            if k == "commonName":
                return v
    return None


class RpcServer:
    def __init__(self, service: RpcService, host: str = "127.0.0.1", port: int = 0, *,
                 tls: ssl.SSLContext | None = None, require_tls: bool = False,
                 max_connections: int = 512, handshake_timeout_s: float = 5.0,
                 idle_timeout_s: float = 120.0, conn_rate: float = 200.0) -> None:
        if require_tls and tls is None:
            raise ValueError("require_tls set but no TLS context supplied")
        self.service, self.tls = service, tls
        self.max_connections = max_connections
        self.handshake_timeout_s, self.idle_timeout_s = handshake_timeout_s, idle_timeout_s
        self._sock = socket.create_server((host, port), reuse_port=False)
        self._sock.settimeout(0.2)
        self.address = self._sock.getsockname()[:2]
        self._conns: set[socket.socket] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._accepting = True
        from .resilience import TokenBucket
        self._conn_bucket = TokenBucket(conn_rate, conn_rate)
        self._thread = threading.Thread(target=self._accept_loop, name="inv61-accept", daemon=True)
        self.rejected_connections = 0

    def start(self) -> "RpcServer":
        self._thread.start()
        return self

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw, _addr = self._sock.accept()
            except (socket.timeout, TimeoutError):
                continue
            except OSError:
                break
            with self._lock:
                over = len(self._conns) >= self.max_connections
            if over or not self._accepting or not self._conn_bucket.take():
                self.rejected_connections += 1
                self.service.metrics.inc("inv61_connections_rejected_total")
                raw.close()
                continue
            threading.Thread(target=self._serve, args=(raw,), daemon=True, name="inv61-conn").start()

    def _serve(self, raw: socket.socket) -> None:
        svc = self.service
        sock: Any = raw
        try:
            raw.settimeout(self.handshake_timeout_s)
            if self.tls is not None:
                sock = self.tls.wrap_socket(raw, server_side=True)
            with self._lock:
                self._conns.add(sock)
            svc.metrics.inc("inv61_connections_total", state="accepted")
            peer = _peer_cn(sock)
            major, minor, kind, body = read_frame(sock, svc.limits)
            if kind != codec.KIND_HELLO:
                raise TransportError("expected-hello")
            ack = svc.hello(body)
            chosen = codec.decode(codec.HELLO_ACK, ack)["chosen"]
            sock.sendall(codec.pack_frame(codec.KIND_HELLO_ACK, ack, *chosen))
            sock.settimeout(self.idle_timeout_s)
            wlock = threading.Lock()
            pending: list[cf.Future] = []
            pool = cf.ThreadPoolExecutor(max_workers=16, thread_name_prefix="inv61-mux")
            try:
                while not self._stop.is_set():
                    try:
                        major, minor, kind, body = read_frame(sock, svc.limits)
                    except (socket.timeout, TimeoutError):
                        break  # idle
                    if (major, minor) != tuple(chosen):
                        raise TransportError("version-changed-mid-session")
                    if kind == codec.KIND_CANCEL:
                        svc.cancel(body)
                        continue
                    if kind != codec.KIND_REQUEST:
                        raise TransportError("unexpected-kind")

                    def work(b=body):
                        out = svc.handle(b, tls_peer=peer)
                        frame = codec.pack_frame(codec.KIND_RESPONSE, out, *chosen)
                        with wlock:
                            sock.sendall(frame)
                    pending = [f for f in pending if not f.done()]
                    pending.append(pool.submit(work))
            finally:
                pool.shutdown(wait=True)
        except (TransportError, codec.CodecError, negotiation.NegotiationError, ssl.SSLError, OSError) as e:
            svc.metrics.inc("inv61_connection_errors_total", reason=type(e).__name__)
        finally:
            with self._lock:
                self._conns.discard(sock)
            try:
                sock.close()
            except OSError:
                pass

    def active_connections(self) -> int:
        with self._lock:
            return len(self._conns)

    def drain(self, timeout_s: float = 10.0) -> bool:
        """Graceful drain: stop accepting, refuse new calls, wait for in-flight."""
        self._accepting = False
        self.service.begin_drain()
        end = time.monotonic() + timeout_s
        while self.service.inflight() > 0 and time.monotonic() < end:
            time.sleep(0.01)
        ok = self.service.inflight() == 0
        self.close()
        return ok

    def close(self) -> None:
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass
        with self._lock:
            conns = list(self._conns)
        for c in conns:
            try:
                c.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self._thread.join(timeout=2)


class RpcClient:
    """Multiplexing client. One connection, many in-flight calls."""

    def __init__(self, host: str, port: int, key: Key, *, tenant: str = "default",
                 tls: ssl.SSLContext | None = None, server_hostname: str | None = None,
                 offered: tuple[tuple[int, int], ...] = negotiation.SUPPORTED,
                 min_accepted: tuple[int, int] = negotiation.MIN_ACCEPTED,
                 connect_timeout_s: float = 5.0, retry: RetryPolicy | None = None,
                 limits: codec.Limits = codec.DEFAULT_LIMITS) -> None:
        self.addr, self.key, self.tenant = (host, port), key, tenant
        self.tls, self.server_hostname = tls, server_hostname or host
        self.offered, self.min_accepted = list(offered), min_accepted
        self.connect_timeout_s, self.retry = connect_timeout_s, retry or RetryPolicy()
        self.limits = limits
        self._sock: Any = None
        self._wlock = threading.Lock()
        self._clock = threading.Lock()
        self._waiters: dict[str, tuple[threading.Event, list]] = {}
        self.chosen: tuple[int, int] | None = None
        self.reconnects = 0

    # --------------------------------------------------------- connection
    def connect(self) -> None:
        with self._clock:
            if self._sock is not None:
                return
            raw = socket.create_connection(self.addr, timeout=self.connect_timeout_s)
            sock: Any = raw
            try:
                self._handshake(raw)
            except BaseException:
                raw.close()
                raise

    def _handshake(self, raw: socket.socket) -> None:
            sock: Any = raw
            if self.tls is not None:
                sock = self.tls.wrap_socket(raw, server_hostname=self.server_hostname)
            nonce = secrets.token_hex(16)
            hello = codec.encode(codec.HELLO, {"peer": self.key.key_id, "offered": self.offered,
                                               "min_accepted": self.min_accepted, "client_nonce": nonce})
            sock.sendall(codec.pack_frame(codec.KIND_HELLO, hello, *max(self.offered)))
            _maj, _min, kind, body = read_frame(sock, self.limits)
            if kind != codec.KIND_HELLO_ACK:
                sock.close()
                raise TransportError("bad-handshake")
            ack = codec.decode(codec.HELLO_ACK, body)
            blob = negotiation.transcript(self.key.key_id, self.offered, self.min_accepted, nonce,
                                          ack["peer"], ack["chosen"], ack["server_nonce"])
            try:
                negotiation.verify_ack(self.key.secret, blob, ack["transcript_mac"], self.offered, ack["chosen"])
            except negotiation.NegotiationError:
                sock.close()
                raise
            self.chosen = tuple(ack["chosen"])
            sock.settimeout(None)
            self._sock = sock
            threading.Thread(target=self._reader, args=(sock,), daemon=True, name="inv61-client-rx").start()

    def _reader(self, sock: Any) -> None:
        try:
            while True:
                _maj, _min, kind, body = read_frame(sock, self.limits)
                if kind != codec.KIND_RESPONSE:
                    raise TransportError("unexpected-kind")
                resp = codec.decode(codec.RESPONSE_ENVELOPE, body, self.limits)
                w = self._waiters.pop(resp["request_id"], None)
                if w:
                    w[1].append(resp)
                    w[0].set()
        except Exception:
            pass
        finally:
            with self._clock:
                if self._sock is sock:
                    self._sock = None
            for rid, (ev, box) in list(self._waiters.items()):
                box.append(None)  # connection lost: ambiguous completion
                ev.set()

    def close(self) -> None:
        with self._clock:
            s, self._sock = self._sock, None
        if s is not None:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            s.close()

    # ---------------------------------------------------------------- calls
    def call_once(self, iface: Interface, func: str, args: list, *, deadline_s: float = 5.0,
                  idempotency_key: str | None = None, traceparent: str | None = None,
                  cancel: threading.Event | None = None) -> dict:
        self.connect()
        f = iface.funcs[func]
        ptype = ("tuple", tuple(iface.resolve(t) for _, t in f.params))
        now_ms = int(time.time() * 1000)
        env = {
            "request_id": uuid.uuid4().hex, "sender": self.key.principal, "tenant": self.tenant,
            "nonce": secrets.token_hex(16), "issued_ms": now_ms,
            "deadline_ms": now_ms + int(deadline_s * 1000),
            "interface": iface.qualified, "version": iface.version, "function": func,
            "fp": fingerprint(f.param_types(), f.result_types()),
            "idempotency_key": idempotency_key, "traceparent": traceparent,
            "args": codec.encode(ptype, list(args), self.limits), "key_id": "", "mac": b"",
        }
        env = sign(env, self.key)
        ev, box = threading.Event(), []
        self._waiters[env["request_id"]] = (ev, box)
        frame = codec.pack_frame(codec.KIND_REQUEST, codec.encode(codec.REQUEST_ENVELOPE, env, self.limits),
                                 *self.chosen)
        sock = self._sock
        if sock is None:
            raise TransportError("not-connected")
        with self._wlock:
            sock.sendall(frame)
        end = time.monotonic() + deadline_s + 0.5
        while not ev.wait(0.02):
            if cancel is not None and cancel.is_set():
                body = codec.encode(codec.CANCEL, {"request_id": env["request_id"]})
                with self._wlock:
                    sock.sendall(codec.pack_frame(codec.KIND_CANCEL, body, *self.chosen))
                cancel = None
            if time.monotonic() > end:
                self._waiters.pop(env["request_id"], None)
                return {"status": "deadline-exceeded", "detail": "client", "result": None, "retryable": False}
        resp = box[0]
        if resp is None:
            return {"status": "unavailable", "detail": "connection-lost", "result": None, "retryable": True,
                    "ambiguous": True}
        if resp["status"] == "ok" and f.result is not None:
            resp = dict(resp)
            resp["value"] = codec.decode(iface.resolve(f.result), resp["result"], self.limits)
        return resp

    def call(self, iface: Interface, func: str, args: list, *, deadline_s: float = 5.0,
             idempotency_key: str | None = None, traceparent: str | None = None,
             sleep: Callable[[float], None] = time.sleep) -> dict:
        """Call with classified retry.  Only idempotency-keyed calls are retried."""
        start, attempt = time.monotonic(), 0
        while True:
            attempt += 1
            remaining = deadline_s - (time.monotonic() - start)
            try:
                resp = self.call_once(iface, func, args, deadline_s=max(0.001, remaining),
                                      idempotency_key=idempotency_key, traceparent=traceparent)
            except (OSError, TransportError) as e:
                self.close()
                resp = {"status": "unavailable", "detail": getattr(e, "code", type(e).__name__),
                        "result": None, "retryable": True}
            if resp["status"] == "unavailable" and resp.get("detail") == "connection-lost":
                self.close()
            remaining = deadline_s - (time.monotonic() - start)
            if not self.retry.should_retry(resp["status"], attempt, idempotency_key is not None, remaining):
                resp["attempts"] = attempt
                return resp
            self.reconnects += 1
            sleep(min(self.retry.backoff(attempt), max(0.0, remaining)))
