"""#3 concrete transport adapters, #19 authority guards, #58 control-path isolation.

``TransportAdapter`` is the versioned SPI (``PK_TRANSPORT_SPI/1``).  Shipped
adapters move real bytes:

* :class:`InProcessAdapter` - Component-Model-style typed interface binding
  (``pk:data-plane/transfer@1.0.0``) inside one process, zero network authority.
* :class:`SharedMemoryAdapter` - POSIX shared memory with tenant-namespaced
  segments, pinning limits and guaranteed unlink.
* :class:`VsockControlAdapter` - VM-control messages only; refuses any payload
  that is not an inline-tier control verb (INV-36 isolation).
* :class:`NetworkRpcAdapter` / :class:`NetworkRpcServer` - framed cross-node
  RPC (``pk06-rpc/1``) with version negotiation, HMAC peer authentication,
  optional TLS/mTLS via ``ssl.SSLContext``, deadlines, bounded frames,
  chunk manifests and receiver-side verification.  It is the wRPC *profile*
  of this package; wire compatibility with upstream wRPC is tracked as waiver
  W-003 in ``WAIVERS.json``.
* :class:`RdmaAdapter` - capability probe only; reports ``unsupported`` unless
  RDMA devices exist, and the selector then records an explicit fallback.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import socket
import ssl
import struct
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from multiprocessing import shared_memory

from . import integrity
from .data_plane import CONTROL_INLINE_LIMIT, _StructuredError
from .security import AuthorityGuard, Grant, tenant_namespace

SPI_VERSION = "PK_TRANSPORT_SPI/1"
COMPONENT_INTERFACE = "pk:data-plane/transfer@1.0.0"
RPC_PROTOCOL = "pk06-rpc"
RPC_VERSIONS = (1,)
MAX_FRAME = 4 * 1024 * 1024
CONTROL_VERBS = frozenset({"start", "stop", "pause", "resume", "snapshot", "health", "configure"})


class TransportError(_StructuredError, RuntimeError):
    code = "PK_TRANSPORT_FAILED"
    retryable = True


class TransportUnsupported(_StructuredError, RuntimeError):
    code = "PK_TRANSPORT_UNSUPPORTED"


class ControlPathViolation(_StructuredError, PermissionError):
    code = "PK_CONTROL_PATH_VIOLATION"


class DeadlineExceeded(_StructuredError, TimeoutError):
    code = "PK_DEADLINE_EXCEEDED"
    retryable = True


class Cancelled(_StructuredError, RuntimeError):
    code = "PK_TRANSFER_CANCELLED"


@dataclass
class Receipt:
    adapter: str
    transfer_id: str | None
    bytes_moved: int
    copies: int
    manifest_root: str
    elapsed_s: float
    extra: dict[str, object] = field(default_factory=dict)


def _check(deadline: float | None, cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise Cancelled("transfer cancelled")
    if deadline is not None and time.monotonic() > deadline:
        raise DeadlineExceeded("deadline exceeded")


class TransportAdapter:
    """Versioned adapter SPI.  Subclasses implement :meth:`_send`."""

    name = "abstract"
    tiers: frozenset[str] = frozenset()
    localities: frozenset[str] = frozenset()
    grant = Grant()

    def __init__(self) -> None:
        self.guard = AuthorityGuard(self.grant)
        self._lock = threading.Lock()
        self._stats = {"sent": 0, "bytes": 0, "errors": 0}
        self._open = True

    def capabilities(self) -> dict[str, object]:
        return {"spi": SPI_VERSION, "name": self.name, "tiers": sorted(self.tiers),
                "localities": sorted(self.localities), "available": self.available()}

    def available(self) -> bool:
        return self._open

    def health(self) -> dict[str, object]:
        with self._lock:
            return {"adapter": self.name, "healthy": self.available(), **self._stats}

    def close(self) -> None:
        self._open = False

    def send(self, decision: Mapping[str, object], data: bytes, *, deadline: float | None = None,
             cancel: threading.Event | None = None) -> Receipt:
        if not self._open:
            raise TransportUnsupported("adapter closed", adapter=self.name)
        if decision.get("tier") not in self.tiers:
            raise TransportUnsupported("tier not served by adapter", adapter=self.name, tier=decision.get("tier"))
        if len(data) != decision.get("size"):
            raise TransportError("payload size differs from admitted size", retryable=False)
        _check(deadline, cancel)
        start = time.monotonic()
        try:
            receipt = self._send(decision, data, deadline=deadline, cancel=cancel)
        except Exception:
            with self._lock:
                self._stats["errors"] += 1
            raise
        receipt.elapsed_s = time.monotonic() - start
        with self._lock:
            self._stats["sent"] += 1
            self._stats["bytes"] += len(data)
        return receipt

    def _send(self, decision: Mapping[str, object], data: bytes, *, deadline: float | None,
              cancel: threading.Event | None) -> Receipt:  # pragma: no cover - interface
        raise NotImplementedError


# --------------------------------------------------------------------------
# In-process Component-Model-style adapter
# --------------------------------------------------------------------------


class InProcessAdapter(TransportAdapter):
    name = "component-model-inprocess"
    tiers = frozenset({"inline", "local", "bulk"})
    localities = frozenset({"in_process", "auto"})
    grant = Grant()  # zero network/filesystem/device authority

    def __init__(self, handler: Callable[[Mapping[str, object], memoryview], None],
                 interface: str = COMPONENT_INTERFACE) -> None:
        super().__init__()
        if interface != COMPONENT_INTERFACE:
            raise TransportUnsupported("unsupported component interface version", interface=interface,
                                       supported=COMPONENT_INTERFACE)
        self.interface = interface
        self._handler = handler

    def _send(self, decision, data, *, deadline, cancel):
        manifest = integrity.build_manifest(str(decision.get("transfer_id") or "inline"), data)
        view = memoryview(data).toreadonly()   # zero-copy hand-off, read-only to the callee
        self._handler(decision, view)
        return Receipt(self.name, decision.get("transfer_id"), len(data), 0, manifest.root, 0.0,  # type: ignore[arg-type]
                       {"interface": self.interface})


# --------------------------------------------------------------------------
# Shared-memory bulk adapter
# --------------------------------------------------------------------------


class SharedMemoryAdapter(TransportAdapter):
    name = "shared-memory"
    tiers = frozenset({"local", "bulk"})
    localities = frozenset({"same_node", "same_host_vm", "in_process", "auto"})
    grant = Grant(shared_memory=True)

    def __init__(self, receiver: Callable[[str, int, str], bytes], *, max_segment_bytes: int = 64 * 1024 * 1024,
                 max_live_segments: int = 16) -> None:
        super().__init__()
        self._receiver = receiver
        self._max_bytes = max_segment_bytes
        self._max_live = max_live_segments
        self._live: set[str] = set()

    def live_segments(self) -> int:
        with self._lock:
            return len(self._live)

    def _send(self, decision, data, *, deadline, cancel):
        if len(data) > self._max_bytes:
            raise TransportUnsupported("payload exceeds shared-memory registration limit",
                                       size=len(data), limit=self._max_bytes)
        self.guard.check("shared_memory", "segment")
        name = tenant_namespace(str(decision["tenant"]), str(decision.get("transfer_id")) + secrets.token_hex(4))
        with self._lock:
            if len(self._live) >= self._max_live:
                raise TransportError("shared-memory pin budget exhausted", live=len(self._live))
            self._live.add(name)
        seg = None
        try:
            seg = shared_memory.SharedMemory(name=name, create=True, size=max(1, len(data)))
            seg.buf[:len(data)] = data  # type: ignore[index]  # JSON-shaped mapping
            manifest = integrity.build_manifest(str(decision.get("transfer_id")), data)
            _check(deadline, cancel)
            received = self._receiver(name, len(data), manifest.root)
            integrity.verify(manifest, received)
            return Receipt(self.name, decision.get("transfer_id"), len(data), 1, manifest.root, 0.0,
                           {"segment": name})
        finally:
            if seg is not None:
                seg.close()
                try:
                    seg.unlink()
                except FileNotFoundError:
                    pass
            with self._lock:
                self._live.discard(name)


def shm_reader(name: str, size: int, _root: str) -> bytes:
    """Reference receiver: attach, copy out, detach (never unlinks - owner does)."""
    seg = shared_memory.SharedMemory(name=name, create=False)
    try:
        return bytes(seg.buf[:size])  # type: ignore[index]  # JSON-shaped mapping
    finally:
        seg.close()


# --------------------------------------------------------------------------
# vsock VM-control adapter (INV-36 control path)
# --------------------------------------------------------------------------


class VsockControlAdapter(TransportAdapter):
    name = "vsock-control"
    tiers = frozenset({"inline"})
    localities = frozenset({"vm_control"})
    grant = Grant(network=True)

    def __init__(self, sock: socket.socket) -> None:
        """``sock`` is a connected AF_VSOCK socket (or a socketpair end in tests)."""
        super().__init__()
        self._sock = sock
        self.control_bytes = 0

    @classmethod
    def connect(cls, cid: int, port: int, timeout: float = 5.0) -> VsockControlAdapter:
        if not hasattr(socket, "AF_VSOCK"):
            raise TransportUnsupported("AF_VSOCK not supported on this platform")
        s = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)  # type: ignore[attr-defined]
        s.settimeout(timeout)
        s.connect((cid, port))
        return cls(s)

    def _send(self, decision, data, *, deadline, cancel):
        verb = decision.get("control_verb")
        if decision.get("locality") != "vm_control" or decision.get("tier") != "inline" or len(data) > CONTROL_INLINE_LIMIT:
            raise ControlPathViolation("bulk payload refused on control path", size=len(data))
        if verb not in CONTROL_VERBS:
            raise ControlPathViolation("only VM-control verbs may use vsock", verb=verb)
        self.guard.check("network", "vsock")
        frame = json.dumps({"verb": verb, "len": len(data)}).encode()
        msg = struct.pack("!II", len(frame), len(data)) + frame + data
        if deadline is not None:
            self._sock.settimeout(max(0.001, deadline - time.monotonic()))
        self._sock.sendall(msg)
        self.control_bytes += len(data)
        return Receipt(self.name, None, len(data), 1, integrity.sha256_hex(data), 0.0, {"verb": verb})


def read_control_frame(sock: socket.socket) -> tuple[dict[str, object], bytes]:
    hdr = _recv_exact(sock, 8)
    flen, dlen = struct.unpack("!II", hdr)
    if flen > 4096 or dlen > CONTROL_INLINE_LIMIT:
        raise ControlPathViolation("oversized control frame", frame=flen, data=dlen)
    return json.loads(_recv_exact(sock, flen)), _recv_exact(sock, dlen)


# --------------------------------------------------------------------------
# Framed network RPC (wRPC profile)
# --------------------------------------------------------------------------


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            raise TransportError("peer closed connection")
        buf += part
    return bytes(buf)


def _send_frame(sock: socket.socket, obj: Mapping[str, object], payload: bytes = b"") -> None:
    head = json.dumps(obj, sort_keys=True).encode()
    if len(head) > 65536 or len(payload) > MAX_FRAME:
        raise TransportError("frame too large", retryable=False)
    sock.sendall(struct.pack("!II", len(head), len(payload)) + head + payload)


def _recv_frame(sock: socket.socket) -> tuple[dict[str, object], bytes]:
    hl, pl = struct.unpack("!II", _recv_exact(sock, 8))
    if hl > 65536 or pl > MAX_FRAME:
        raise TransportError("peer sent oversized frame", retryable=False)
    return json.loads(_recv_exact(sock, hl)), _recv_exact(sock, pl)


def _proof(secret: bytes, nonce: str, who: str) -> str:
    return hmac.new(secret, f"{who}:{nonce}".encode(), hashlib.sha256).hexdigest()


class NetworkRpcServer:
    """Receiver for ``pk06-rpc/1``; verifies peers and every chunk, quarantines on mismatch."""

    def __init__(self, peer_secrets: Mapping[str, bytes], *, host: str = "127.0.0.1", port: int = 0,
                 ssl_context: ssl.SSLContext | None = None, max_bytes: int = 256 * 1024 * 1024,
                 quarantine: integrity.QuarantineStore | None = None, server_id: str = "pln06-server") -> None:
        self._secrets = dict(peer_secrets)
        self._ctx = ssl_context
        self._max = max_bytes
        self.quarantine = quarantine or integrity.QuarantineStore()
        self.server_id = server_id
        self.received: dict[str, bytes] = {}
        self._sock = socket.create_server((host, port))
        self._sock.settimeout(0.2)
        self.address = self._sock.getsockname()[:2]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self.errors: list[str] = []

    def start(self) -> NetworkRpcServer:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        self._sock.close()

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except (TimeoutError, OSError):
                continue
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, raw: socket.socket) -> None:
        conn: socket.socket = raw
        try:
            conn.settimeout(10)
            if self._ctx is not None:
                conn = self._ctx.wrap_socket(raw, server_side=True)
            hello, _ = _recv_frame(conn)
            versions = [v for v in hello.get("versions", []) if v in RPC_VERSIONS]  # type: ignore[attr-defined, union-attr]
            if hello.get("protocol") != RPC_PROTOCOL or not versions:
                _send_frame(conn, {"ok": False, "code": "PK_VERSION_UNSUPPORTED", "supported": list(RPC_VERSIONS)})
                return
            peer = str(hello.get("peer"))
            secret = self._secrets.get(peer)
            nonce = secrets.token_hex(16)
            _send_frame(conn, {"ok": True, "version": max(versions), "nonce": nonce, "server": self.server_id})
            auth, _ = _recv_frame(conn)
            if secret is None or not hmac.compare_digest(str(auth.get("proof")), _proof(secret, nonce, peer)):
                _send_frame(conn, {"ok": False, "code": "PK_AUTHN_FAILED"})
                return
            _send_frame(conn, {"ok": True, "proof": _proof(secret, str(auth.get("nonce")), self.server_id)})
            head, _ = _recv_frame(conn)
            manifest = integrity.Manifest(str(head["transfer_id"]), int(head["size"]), int(head["chunk_size"]),  # type: ignore[arg-type, call-overload]
                                          tuple(head["chunks"]), str(head["root"]))  # type: ignore[arg-type]
            if manifest.size > self._max:
                _send_frame(conn, {"ok": False, "code": "PK_BACKPRESSURE"})
                return
            _send_frame(conn, {"ok": True})
            parts: list[tuple[int, bytes]] = []
            for _ in range(len(manifest.chunks) if manifest.size else 0):
                meta, blob = _recv_frame(conn)
                parts.append((int(meta["i"]), blob))  # type: ignore[arg-type, call-overload]
            try:
                data = integrity.reassemble(manifest, parts)
            except integrity.IntegrityMismatch as exc:
                self.quarantine.put(manifest.transfer_id, exc.as_dict()["message"])  # type: ignore[arg-type]
                _send_frame(conn, {"ok": False, "code": exc.code})
                return
            self.received[manifest.transfer_id] = data
            _send_frame(conn, {"ok": True, "root": manifest.root})
        except Exception as exc:  # noqa: BLE001 - server must never crash on hostile input
            self.errors.append(type(exc).__name__)
        finally:
            try:
                conn.close()
            except OSError:
                pass


class NetworkRpcAdapter(TransportAdapter):
    name = "network-rpc"
    tiers = frozenset({"local", "bulk"})
    localities = frozenset({"remote", "same_node", "auto"})
    grant = Grant(network=True)

    def __init__(self, address: tuple[str, int], *, peer_id: str, secret: bytes, server_id: str = "pln06-server",
                 ssl_context: ssl.SSLContext | None = None, server_hostname: str | None = None,
                 chunk_size: int = 1024 * 1024, versions: tuple[int, ...] = RPC_VERSIONS,
                 tamper: Callable[[int, bytes], bytes] | None = None) -> None:
        super().__init__()
        self._addr = address
        self._peer = peer_id
        self._secret = secret
        self._server_id = server_id
        self._ctx = ssl_context
        self._sni = server_hostname
        self._chunk = min(chunk_size, MAX_FRAME)
        self._versions = versions
        self._tamper = tamper  # fault-injection hook for tests

    def _send(self, decision, data, *, deadline, cancel):
        self.guard.check("network", f"{self._addr[0]}:{self._addr[1]}")
        timeout = 10.0 if deadline is None else max(0.001, deadline - time.monotonic())
        try:
            raw = socket.create_connection(self._addr, timeout=timeout)
        except TimeoutError as exc:
            raise DeadlineExceeded("connect deadline exceeded") from exc
        except OSError as exc:
            raise TransportError(f"connect failed: {type(exc).__name__}") from exc
        sock: socket.socket = raw
        try:
            if self._ctx is not None:
                sock = self._ctx.wrap_socket(raw, server_hostname=self._sni)
            _send_frame(sock, {"protocol": RPC_PROTOCOL, "versions": list(self._versions), "peer": self._peer})
            hello, _ = _recv_frame(sock)
            if not hello.get("ok"):
                raise TransportUnsupported("version negotiation failed", **{k: v for k, v in hello.items() if k != "ok"})  # type: ignore[arg-type]  # JSON-shaped mapping
            my_nonce = secrets.token_hex(16)
            _send_frame(sock, {"proof": _proof(self._secret, str(hello["nonce"]), self._peer), "nonce": my_nonce})
            auth, _ = _recv_frame(sock)
            if not auth.get("ok"):
                raise TransportError("peer rejected authentication", retryable=False)
            if not hmac.compare_digest(str(auth.get("proof")), _proof(self._secret, my_nonce, str(hello["server"]))) \
                    or hello.get("server") != self._server_id:
                raise TransportError("server failed mutual authentication", retryable=False)
            manifest = integrity.build_manifest(str(decision["transfer_id"]), data, self._chunk)
            _send_frame(sock, manifest.as_dict())
            ack, _ = _recv_frame(sock)
            if not ack.get("ok"):
                raise TransportError("receiver refused transfer", code_detail=ack.get("code"))
            if manifest.size:
                for i, blob in enumerate(integrity.chunks(data, self._chunk)):
                    _check(deadline, cancel)
                    if self._tamper is not None:
                        blob = self._tamper(i, blob)
                    _send_frame(sock, {"i": i}, blob)
            final, _ = _recv_frame(sock)
            if not final.get("ok"):
                raise integrity.IntegrityMismatch("receiver verification failed", detail=final.get("code"))
            return Receipt(self.name, decision.get("transfer_id"), len(data), 1, manifest.root, 0.0,  # type: ignore[arg-type]
                           {"protocol": f"{RPC_PROTOCOL}/{hello['version']}", "tls": self._ctx is not None})
        except TimeoutError as exc:
            raise DeadlineExceeded("network deadline exceeded") from exc
        except (ConnectionError, OSError) as exc:
            if isinstance(exc, (_StructuredError,)):
                raise
            raise TransportError(f"network failure: {type(exc).__name__}") from exc
        finally:
            sock.close()


# --------------------------------------------------------------------------
# RDMA capability probe
# --------------------------------------------------------------------------


class RdmaAdapter(TransportAdapter):
    name = "rdma"
    tiers = frozenset({"bulk"})
    localities = frozenset({"remote"})
    grant = Grant(devices=("/dev/infiniband/uverbs0",))

    def __init__(self, sysfs: str = "/sys/class/infiniband") -> None:
        super().__init__()
        self._devices = sorted(os.listdir(sysfs)) if os.path.isdir(sysfs) else []

    def available(self) -> bool:
        return self._open and bool(self._devices)

    def _send(self, decision, data, *, deadline, cancel):
        raise TransportUnsupported("RDMA verbs binding not shipped; see WAIVERS.json W-004",
                                   devices=self._devices)


# --------------------------------------------------------------------------
# Selection / capability negotiation
# --------------------------------------------------------------------------

PREFERENCE = {
    ("inline", "vm_control"): ("vsock-control",),
    ("inline", "in_process"): ("component-model-inprocess",),
    ("inline", "auto"): ("component-model-inprocess",),
    ("local", "in_process"): ("component-model-inprocess", "shared-memory"),
    ("local", "same_node"): ("shared-memory", "network-rpc"),
    ("local", "same_host_vm"): ("shared-memory",),
    ("local", "auto"): ("shared-memory", "network-rpc"),
    ("bulk", "remote"): ("rdma", "network-rpc"),
    ("bulk", "same_node"): ("shared-memory", "network-rpc"),
    ("bulk", "same_host_vm"): ("shared-memory",),
    ("bulk", "in_process"): ("component-model-inprocess",),
    ("bulk", "auto"): ("rdma", "network-rpc", "shared-memory"),
    # vm_control is inline-only by construction: size > inline limit is promoted to "local" and has
    # no mapping, so bulk bytes can never be routed onto the control transport.
}


def select_adapter(decision: Mapping[str, object], adapters: Mapping[str, TransportAdapter],
                   *, excluded: frozenset[str] = frozenset()) -> tuple[TransportAdapter, dict[str, object]]:
    """Turn an admission decision into an executable adapter choice.

    vsock never appears in a non-inline preference list (INV-36 proof), and an
    unavailable preferred adapter is skipped with an explicit recorded reason.
    """
    key = (str(decision.get("tier")), str(decision.get("locality")))
    prefs = PREFERENCE.get(key)
    if not prefs:
        raise TransportUnsupported("no adapter mapping for tier/locality", tier=key[0], locality=key[1])
    skipped: list[dict[str, str]] = []
    for name in prefs:
        adapter = adapters.get(name)
        if name in excluded:
            skipped.append({"adapter": name, "reason": "quarantined/excluded"})
        elif adapter is None:
            skipped.append({"adapter": name, "reason": "not configured"})
        elif not adapter.available():
            skipped.append({"adapter": name, "reason": "unavailable"})
        elif key[0] not in adapter.tiers:
            skipped.append({"adapter": name, "reason": "tier unsupported"})
        else:
            return adapter, {"adapter": name, "skipped": skipped, "preference": list(prefs)}
    raise TransportUnsupported("no available adapter for decision", tier=key[0], locality=key[1], skipped=skipped)
