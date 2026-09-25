"""Shared fixtures: stub VMM over a real Unix socket, pinned temp manifests, fake KVM."""
from __future__ import annotations

import errno
import hashlib
import json
import os
import pathlib
import stat
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STUB_VMM = r'''#!{python}
import http.server, json, os, socketserver, sys
sock = sys.argv[sys.argv.index("--api-sock") + 1]
mode = os.environ.get("STUB_MODE", "ok")
if mode == "crash":
    sys.exit(3)
calls = []
class H(http.server.BaseHTTPRequestHandler):
    def do_PUT(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{{}}")
        calls.append((self.path, body))
        if mode == "reject" and self.path == "/machine-config":
            self._send(400, {{"fault_message": "bad config"}})
        elif mode == "bootfail" and self.path == "/actions":
            self._send(500, {{"fault_message": "kernel panic"}})
        elif mode == "hang" and self.path == "/actions":
            import time; time.sleep(30)
        else:
            self._send(204, None)
    do_PATCH = do_PUT
    def _send(self, code, payload):
        data = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(data))); self.end_headers()
        self.wfile.write(data)
    def log_message(self, *a): pass
class S(socketserver.UnixStreamServer):
    def get_request(self):
        req, _ = super().get_request(); return req, ("uds", 0)
srv = S(sock, H)
srv.serve_forever()
'''


def make_stub_vmm(directory: str) -> str:
    path = os.path.join(directory, "firecracker-stub")
    with open(path, "w") as fh:
        fh.write(STUB_VMM.format(python=sys.executable))
    os.chmod(path, 0o755)
    return path


def sha(path: str) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def pinned_manifest(directory: str, **paths: str) -> str:
    entries = [{"name": name.replace("_", "-"), "kind": "binary", "version": "1.0.0-test",
                "sha256": sha(p), "source": "test fixture"} for name, p in paths.items()]
    mpath = os.path.join(directory, "manifest.json")
    pathlib.Path(mpath).write_text(json.dumps({"schema": "PK_MICROVM_ARTIFACTS/1", "manifest_version": "t",
                                               "artifacts": entries}))
    return mpath


class FakeKvm:
    """ioctl/opener doubles for deterministic KVM scenarios."""

    def __init__(self, scenario: str = "ok", api: int = 12, missing: tuple = ()) -> None:
        self.scenario, self.api, self.missing, self.closed = scenario, api, set(missing), 0

    def opener(self, path, flags):
        if self.scenario == "absent":
            raise FileNotFoundError(path)
        if self.scenario == "denied":
            raise PermissionError(path)
        if self.scenario == "busy":
            raise OSError(errno.EBUSY, "busy")
        return 99

    def closer(self, fd):
        self.closed += 1

    def ioctl(self, fd, req, arg=0):
        from inv24_microvm_runtime.virtualization.kvm import KVM_GET_API_VERSION, REQUIRED_CAPS, ARCH_CAPS
        if self.scenario == "revoked":
            raise OSError(errno.ENODEV, "revoked")
        if req == KVM_GET_API_VERSION:
            return self.api
        names = {v: k for k, v in {**REQUIRED_CAPS, **ARCH_CAPS["x86_64"]}.items()}
        return 0 if names.get(arg) in self.missing else 1

    def preflight(self, **kw):
        from inv24_microvm_runtime.virtualization.kvm import KvmPreflight
        return KvmPreflight(opener=self.opener, closer=self.closer, ioctl=self.ioctl, arch="x86_64", **kw)


def keyring(*ids: str):
    from inv24_microvm_runtime.security.keys import Keyring, StaticKeyProvider
    ids = ids or ("k1",)
    return Keyring(StaticKeyProvider({i: hashlib.sha256(i.encode()).digest() for i in ids}), ids[0])


def tmpdir() -> str:
    # short base path keeps UDS paths under the 107-byte sun_path limit
    return tempfile.mkdtemp(prefix="i24-", dir="/tmp")
