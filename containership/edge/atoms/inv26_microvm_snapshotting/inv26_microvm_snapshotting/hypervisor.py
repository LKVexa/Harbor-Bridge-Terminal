"""Hypervisor and guest-entropy ports with concrete adapters (X001, X002, C021, C043).

:class:`HypervisorPort` is the narrow, brokered surface the service is allowed
to use (C043: the service itself holds no KVM authority; the adapter talks to
one VMM API socket per microVM):

    pause(vm) -> capture(vm, workdir) -> (state_bytes, memory_bytes)
    load(vm, workdir, state_bytes, memory_bytes)   # guest stays PAUSED
    resume(vm)                                      # only after entropy ack
    destroy(vm)                                     # on any restore failure

Adapters
--------
* :class:`FirecrackerAdapter` — Firecracker's documented REST API over its
  Unix socket: ``PATCH /vm {"state": "Paused"|"Resumed"}``,
  ``PUT /snapshot/create {"snapshot_type": "Full", "snapshot_path", "mem_file_path"}``,
  ``PUT /snapshot/load {"snapshot_path", "mem_backend": {"backend_type": "File",
  "backend_path"}, "resume_vm": false}``.
* :class:`CloudHypervisorAdapter` — Cloud Hypervisor's REST API:
  ``PUT /api/v1/vm.pause``, ``PUT /api/v1/vm.snapshot {"destination_url": "file://…"}``,
  ``PUT /api/v1/vm.restore {"source_url": "file://…"}``, ``PUT /api/v1/vm.resume``.
* :class:`ReferenceHypervisor` — in-process model for tests/benchmarks of the
  domain path. **It never counts as hypervisor evidence.**

The Firecracker and Cloud Hypervisor clients are exercised in CI against
protocol fakes that listen on real Unix sockets in a separate thread
(``tests/fakes.py``); they have **not** been run against a real VMM in this
repository (no /dev/kvm in the build environment) — see COMPONENTS_STATUS.

Entropy (X002)
--------------
:class:`VsockAgentInjector` delivers the seed to an in-guest agent over the
Firecracker vsock host socket (``CONNECT <port>\\n`` -> ``OK …``), then
requires the agent to echo ``sha256(seed || nonce)``; anything else fails
closed and the guest is destroyed before it can run. The in-guest agent (which
writes the seed via ``RNDADDENTROPY`` and reseeds the CRNG) is **not part of
this repository**; on x86_64 Firecracker >= 1.8 a VMGenID bump is an
additional, complementary signal to the guest kernel.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import secrets
import socket
import threading
from pathlib import Path

from .errors import SnapshotServiceError


# ------------------------------------------------------------------ transport
class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect(self._path)
        self.sock = s


def _call(sock_path: str, method: str, path: str, body: dict | None, timeout: float) -> dict:
    conn = _UnixHTTPConnection(sock_path, timeout)
    try:
        payload = json.dumps(body).encode() if body is not None else None
        conn.request(method, path, body=payload, headers={"Content-Type": "application/json",
                                                           "Accept": "application/json"})
        resp = conn.getresponse()
        raw = resp.read(1 << 20)
    except socket.timeout:
        raise SnapshotServiceError("SNAP_TIMEOUT", f"VMM {method} {path} timed out") from None
    except OSError as exc:
        raise SnapshotServiceError("SNAP_HYPERVISOR_FAILED", f"VMM socket: {type(exc).__name__}") from None
    finally:
        conn.close()
    if resp.status >= 300:
        raise SnapshotServiceError("SNAP_HYPERVISOR_FAILED", f"VMM {method} {path} -> {resp.status}")
    try:
        return json.loads(raw) if raw else {}
    except ValueError:
        return {}


# ------------------------------------------------------------------ port
class HypervisorPort:
    name = "abstract"
    version = "0"
    arch = "x86_64"

    def pause(self, vm_id: str) -> None: ...  # pragma: no cover
    def capture(self, vm_id: str, workdir: Path) -> tuple[bytes, bytes]: ...  # pragma: no cover
    def load(self, vm_id: str, workdir: Path, state: bytes, memory: bytes) -> None: ...  # pragma: no cover
    def resume(self, vm_id: str) -> None: ...  # pragma: no cover
    def destroy(self, vm_id: str) -> None: ...  # pragma: no cover
    def health(self) -> bool:
        return True


def _write_private(p: Path, data: bytes) -> None:
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


def _unlink(p: Path) -> None:
    try:
        p.unlink()
    except FileNotFoundError:
        pass


def wipe(p: Path) -> None:
    """Best-effort overwrite + unlink of a plaintext working file (X010)."""
    try:
        size = p.stat().st_size
        with open(p, "r+b") as fh:
            remaining = size
            while remaining > 0:
                n = min(remaining, 1 << 20)
                fh.write(b"\x00" * n)
                remaining -= n
            fh.flush()
            os.fsync(fh.fileno())
        p.unlink()
    except FileNotFoundError:
        pass


class FirecrackerAdapter(HypervisorPort):
    name = "firecracker"

    def __init__(self, sockets: dict[str, str], *, version: str = "1.9", arch: str = "x86_64",
                 timeout_s: float = 5.0, killer=None):
        self.sockets, self.version, self.arch, self.timeout = sockets, version, arch, timeout_s
        self._killer = killer  # callable(vm_id): terminates the VMM process (jailer-owned)

    def _sock(self, vm_id: str) -> str:
        try:
            return self.sockets[vm_id]
        except KeyError:
            raise SnapshotServiceError("SNAP_HYPERVISOR_FAILED", "no VMM socket registered for VM") from None

    def pause(self, vm_id):
        _call(self._sock(vm_id), "PATCH", "/vm", {"state": "Paused"}, self.timeout)

    def capture(self, vm_id, workdir):
        st, mem = workdir / "vm.state", workdir / "vm.mem"
        _call(self._sock(vm_id), "PUT", "/snapshot/create",
              {"snapshot_type": "Full", "snapshot_path": str(st), "mem_file_path": str(mem)}, self.timeout)
        try:
            return st.read_bytes(), mem.read_bytes()
        finally:
            wipe(st)
            wipe(mem)

    def load(self, vm_id, workdir, state, memory):
        st, mem = workdir / "vm.state", workdir / "vm.mem"
        _write_private(st, state)
        _write_private(mem, memory)
        try:
            _call(self._sock(vm_id), "PUT", "/snapshot/load",
                  {"snapshot_path": str(st), "mem_backend": {"backend_type": "File", "backend_path": str(mem)},
                   "enable_diff_snapshots": False, "resume_vm": False}, self.timeout)
        finally:
            wipe(st)
            # Firecracker mmaps the File memory backend MAP_PRIVATE: overwriting it after
            # load would corrupt not-yet-faulted guest pages. Unlink only; the inode lives
            # until the VMM exits. The work dir MUST be a private tmpfs (RUNBOOK day-0) so
            # the plaintext never reaches persistent media (X010 residual risk).
            _unlink(mem)

    def resume(self, vm_id):
        _call(self._sock(vm_id), "PATCH", "/vm", {"state": "Resumed"}, self.timeout)

    def destroy(self, vm_id):
        if self._killer is not None:
            self._killer(vm_id)

    def health(self):
        return all(os.path.exists(p) for p in self.sockets.values())


class CloudHypervisorAdapter(HypervisorPort):
    name = "cloud-hypervisor"

    def __init__(self, sockets: dict[str, str], *, version: str = "41.0", arch: str = "x86_64",
                 timeout_s: float = 5.0, killer=None):
        self.sockets, self.version, self.arch, self.timeout = sockets, version, arch, timeout_s
        self._killer = killer

    def _sock(self, vm_id):
        try:
            return self.sockets[vm_id]
        except KeyError:
            raise SnapshotServiceError("SNAP_HYPERVISOR_FAILED", "no VMM socket registered for VM") from None

    def pause(self, vm_id):
        _call(self._sock(vm_id), "PUT", "/api/v1/vm.pause", None, self.timeout)

    def capture(self, vm_id, workdir):
        _call(self._sock(vm_id), "PUT", "/api/v1/vm.snapshot", {"destination_url": f"file://{workdir}"},
              self.timeout)
        st, mem = workdir / "state.json", workdir / "memory-ranges"
        try:
            return st.read_bytes(), mem.read_bytes()
        finally:
            wipe(st)
            wipe(mem)
            wipe(workdir / "config.json")

    def load(self, vm_id, workdir, state, memory):
        _write_private(workdir / "state.json", state)
        _write_private(workdir / "memory-ranges", memory)
        try:
            _call(self._sock(vm_id), "PUT", "/api/v1/vm.restore", {"source_url": f"file://{workdir}"},
                  self.timeout)
        finally:
            wipe(workdir / "state.json")
            _unlink(workdir / "memory-ranges")  # see FirecrackerAdapter.load: never overwrite a mapped file

    def resume(self, vm_id):
        _call(self._sock(vm_id), "PUT", "/api/v1/vm.resume", None, self.timeout)

    def destroy(self, vm_id):
        if self._killer is not None:
            self._killer(vm_id)


class ReferenceHypervisor(HypervisorPort):
    """In-process VMM model: each VM is a bytearray of 'guest memory' plus a state dict."""

    name = "reference"
    version = "1"

    def __init__(self):
        self.vms: dict[str, dict] = {}
        self.fail_next: str | None = None  # fault injection: "capture" | "load" | "resume"
        self.delay_s = 0.0
        self._lock = threading.Lock()
        self.available = True

    def boot(self, vm_id: str, memory: bytes) -> None:
        with self._lock:
            self.vms[vm_id] = {"state": "Running", "memory": bytes(memory), "rng": None}

    def _maybe_fail(self, stage: str):
        if not self.available:
            raise SnapshotServiceError("SNAP_HYPERVISOR_FAILED", "reference VMM offline")
        if self.fail_next == stage:
            self.fail_next = None
            raise SnapshotServiceError("SNAP_HYPERVISOR_FAILED", f"injected {stage} failure")
        if self.delay_s:
            import time as _t
            _t.sleep(self.delay_s)

    def pause(self, vm_id):
        self._maybe_fail("pause")
        with self._lock:
            if vm_id not in self.vms:
                raise SnapshotServiceError("SNAP_HYPERVISOR_FAILED", "unknown VM")
            self.vms[vm_id]["state"] = "Paused"

    def capture(self, vm_id, workdir):
        self._maybe_fail("capture")
        with self._lock:
            vm = self.vms[vm_id]
            return json.dumps({"vm": vm_id, "state": "Paused"}).encode(), vm["memory"]

    def load(self, vm_id, workdir, state, memory):
        self._maybe_fail("load")
        with self._lock:
            self.vms[vm_id] = {"state": "Paused", "memory": memory, "rng": None, "restored": True}

    def resume(self, vm_id):
        self._maybe_fail("resume")
        with self._lock:
            vm = self.vms[vm_id]
            if vm["rng"] is None:
                raise SnapshotServiceError("SNAP_ENTROPY_FAILED", "guest resumed without reseed")
            vm["state"] = "Running"

    def destroy(self, vm_id):
        with self._lock:
            self.vms.pop(vm_id, None)

    def health(self):
        return self.available


# ------------------------------------------------------------------ entropy
class EntropyInjector:
    def inject(self, vm_id: str, seed: bytes) -> None: ...  # pragma: no cover


class ReferenceEntropyInjector(EntropyInjector):
    """Writes the seed into :class:`ReferenceHypervisor` guest state (reference profile only)."""

    def __init__(self, hv: ReferenceHypervisor):
        self.hv = hv
        self.fail = False

    def inject(self, vm_id, seed):
        if self.fail:
            raise OSError("guest agent unavailable")
        if len(seed) != 32:
            raise ValueError("seed length")
        with self.hv._lock:
            self.hv.vms[vm_id]["rng"] = hashlib.sha256(seed).hexdigest()


class VsockAgentInjector(EntropyInjector):
    """Seed delivery over the Firecracker vsock host UDS with an authenticated echo."""

    def __init__(self, uds_paths: dict[str, str], *, port: int = 10_026, timeout_s: float = 2.0):
        self.uds, self.port, self.timeout = uds_paths, port, timeout_s

    def inject(self, vm_id, seed):
        nonce = secrets.token_bytes(16)
        want = hashlib.sha256(seed + nonce).hexdigest()
        path = self.uds.get(vm_id)
        if path is None:
            raise OSError("no vsock socket for VM")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(self.timeout)
            s.connect(path)
            s.sendall(f"CONNECT {self.port}\n".encode())
            ack = _readline(s)
            if not ack.startswith(b"OK "):
                raise OSError("vsock handshake refused")
            msg = {"op": "reseed", "seed": base64.b64encode(seed).decode(),
                   "nonce": base64.b64encode(nonce).decode()}
            s.sendall(json.dumps(msg).encode() + b"\n")
            reply = json.loads(_readline(s) or b"{}")
        if not (isinstance(reply, dict) and reply.get("ok") is True
                and isinstance(reply.get("proof"), str) and secrets.compare_digest(reply["proof"], want)):
            raise OSError("guest agent did not prove seed receipt")


def _readline(s: socket.socket, limit: int = 4096) -> bytes:
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = s.recv(1)
        if not chunk:
            break
        buf += chunk
        if len(buf) > limit:
            raise OSError("line too long")
    return buf.strip()
