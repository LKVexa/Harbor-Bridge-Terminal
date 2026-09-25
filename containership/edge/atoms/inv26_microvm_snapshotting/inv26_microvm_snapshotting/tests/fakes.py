"""Protocol fakes on real Unix sockets (separate server threads) for adapter tests.

* :class:`FakeVMM` speaks the subset of the Firecracker **or** Cloud Hypervisor
  REST API that the adapters use, and writes/reads real snapshot files at the
  paths the client sends — so the adapters' file handling, permissions and
  wiping are exercised end-to-end. It is a *protocol* fake: it proves the
  client sends the documented requests; it does not prove a real VMM accepts
  them (that needs /dev/kvm — BLOCKED_EXTERNAL in this build environment).
* :class:`FakeGuestAgent` emulates the Firecracker vsock host socket
  (``CONNECT <port>`` handshake) and an in-guest reseed agent that answers
  with ``sha256(seed || nonce)``; ``mode`` can make it lie, stall or refuse.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import socketserver
import tempfile
import threading
from http.server import BaseHTTPRequestHandler


class _UnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class FakeVMM:
    def __init__(self, flavor: str = "firecracker", memory: bytes = b"fake-guest-ram" * 64):
        self.flavor = flavor
        self.dir = tempfile.mkdtemp(prefix="fakevmm-")
        self.path = os.path.join(self.dir, "api.sock")
        self.memory = memory
        self.state = "Running"
        self.calls: list[tuple[str, str, dict]] = []
        self.fail_paths: set[str] = set()
        self.loaded: tuple[bytes, bytes] | None = None
        self.load_file_modes: list[int] = []
        vmm = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _body(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"{}") if n else {}

            def _reply(self, code, obj=None):
                data = json.dumps(obj).encode() if obj is not None else b""
                self.send_response(code)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _handle(self):
                body = self._body()
                vmm.calls.append((self.command, self.path, body))
                if self.path in vmm.fail_paths:
                    return self._reply(400, {"fault_message": "injected"})
                try:
                    code = vmm.dispatch(self.command, self.path, body)
                except Exception as exc:  # malformed client request -> 400, like a VMM
                    return self._reply(400, {"fault_message": type(exc).__name__})
                return self._reply(code)

            do_PUT = do_PATCH = _handle

        self.server = _UnixHTTPServer(self.path, H)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def dispatch(self, method, path, body) -> int:
        if self.flavor == "firecracker":
            if (method, path) == ("PATCH", "/vm"):
                if body.get("state") not in ("Paused", "Resumed"):
                    raise ValueError("state")
                self.state = body["state"]
                return 204
            if (method, path) == ("PUT", "/snapshot/create"):
                if self.state != "Paused" or body.get("snapshot_type") != "Full":
                    raise ValueError("must pause first / full snapshots only")
                with open(body["snapshot_path"], "wb") as fh:
                    fh.write(json.dumps({"vmm": "fc", "state": "Paused"}).encode())
                with open(body["mem_file_path"], "wb") as fh:
                    fh.write(self.memory)
                return 204
            if (method, path) == ("PUT", "/snapshot/load"):
                if body.get("resume_vm") is not False or body["mem_backend"]["backend_type"] != "File":
                    raise ValueError("adapter must load paused from a file backend")
                self.load_file_modes.append(os.stat(body["snapshot_path"]).st_mode & 0o777)
                with open(body["snapshot_path"], "rb") as a, open(body["mem_backend"]["backend_path"], "rb") as b:
                    self.loaded = (a.read(), b.read())
                self.state = "Paused"
                return 204
        else:  # cloud-hypervisor
            if path == "/api/v1/vm.pause":
                self.state = "Paused"
                return 204
            if path == "/api/v1/vm.resume":
                self.state = "Running"
                return 204
            if path == "/api/v1/vm.snapshot":
                d = body["destination_url"].removeprefix("file://")
                for name, data in (("state.json", b'{"vmm":"ch"}'), ("memory-ranges", self.memory),
                                   ("config.json", b"{}")):
                    with open(os.path.join(d, name), "wb") as fh:
                        fh.write(data)
                return 204
            if path == "/api/v1/vm.restore":
                d = body["source_url"].removeprefix("file://")
                with open(os.path.join(d, "state.json"), "rb") as a, open(os.path.join(d, "memory-ranges"), "rb") as b:
                    self.loaded = (a.read(), b.read())
                self.state = "Paused"
                return 204
        return 404

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class FakeGuestAgent:
    def __init__(self, port: int = 10_026, mode: str = "honest"):
        self.dir = tempfile.mkdtemp(prefix="fakevsock-")
        self.path = os.path.join(self.dir, "v.sock")
        self.port, self.mode = port, mode
        self.seeds: list[bytes] = []
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.path)
        self.sock.listen(8)
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                f = conn.makefile("rwb")
                line = f.readline().decode().strip()
                if self.mode == "refuse" or line != f"CONNECT {self.port}":
                    f.write(b"NO\n")
                    f.flush()
                    continue
                f.write(b"OK 1073741824\n")
                f.flush()
                if self.mode == "stall":
                    threading.Event().wait(5)
                    continue
                msg = json.loads(f.readline())
                seed, nonce = base64.b64decode(msg["seed"]), base64.b64decode(msg["nonce"])
                self.seeds.append(seed)
                proof = hashlib.sha256(seed + nonce).hexdigest()
                if self.mode == "lie":
                    proof = hashlib.sha256(b"not-the-seed").hexdigest()
                f.write(json.dumps({"ok": True, "proof": proof}).encode() + b"\n")
                f.flush()

    def close(self):
        self.sock.close()
