"""MC57 — OCI conformance fixtures and a local fake registry (Distribution API subset).

The fake registry implements: bearer-token challenge + token realm, optional Basic
auth, manifests by tag/digest with Content-Type, blobs with Range support, fault
injection hooks (fail N requests, truncate a blob mid-stream, serve wrong bytes).
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from inv02_container_substrate.oci import MT_CONFIG, MT_INDEX, MT_LAYER_GZIP, MT_MANIFEST


def sha(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def make_tar(entries: list[tuple], gz: bool = True) -> tuple[bytes, str]:
    """entries: (name, kind, data/linkname, mode).  Returns (blob, diff_id)."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for e in entries:
            name, kind = e[0], e[1]
            ti = tarfile.TarInfo(name)
            ti.mode = e[3] if len(e) > 3 else (0o755 if kind == "dir" else 0o644)
            if kind == "file":
                data = e[2]
                ti.size = len(data)
                tar.addfile(ti, io.BytesIO(data))
            elif kind == "dir":
                ti.type = tarfile.DIRTYPE
                tar.addfile(ti)
            elif kind == "sym":
                ti.type, ti.linkname = tarfile.SYMTYPE, e[2]
                tar.addfile(ti)
            elif kind == "hard":
                ti.type, ti.linkname = tarfile.LNKTYPE, e[2]
                tar.addfile(ti)
            elif kind == "chr":
                ti.type, ti.devmajor, ti.devminor = tarfile.CHRTYPE, 1, 3
                tar.addfile(ti)
    plain = raw.getvalue()
    return (gzip.compress(plain, mtime=0) if gz else plain), sha(plain)


def make_image(layers_entries: list[list[tuple]], os_="linux", arch="amd64", variant=None):
    """Build a complete OCI image: returns dict(manifest, config, layers, diff_ids, digest)."""
    layers, diff_ids = [], []
    for ents in layers_entries:
        b, d = make_tar(ents)
        layers.append(b)
        diff_ids.append(d)
    cfg = {"architecture": arch, "os": os_, "rootfs": {"type": "layers", "diff_ids": diff_ids},
           "config": {"Cmd": ["/bin/true"]}}
    if variant:
        cfg["variant"] = variant
    config = json.dumps(cfg, sort_keys=True).encode()
    manifest = json.dumps({"schemaVersion": 2, "mediaType": MT_MANIFEST,
                           "config": {"mediaType": MT_CONFIG, "digest": sha(config), "size": len(config)},
                           "layers": [{"mediaType": MT_LAYER_GZIP, "digest": sha(b), "size": len(b)} for b in layers]},
                          sort_keys=True).encode()
    return {"manifest": manifest, "config": config, "layers": layers, "diff_ids": diff_ids, "digest": sha(manifest)}


def make_index(images: list[tuple[dict, str, str, str | None]]) -> bytes:
    return json.dumps({"schemaVersion": 2, "mediaType": MT_INDEX, "manifests": [
        {"mediaType": MT_MANIFEST, "digest": img["digest"], "size": len(img["manifest"]),
         "platform": {k: v for k, v in (("os", o), ("architecture", a), ("variant", v)) if v}}
        for img, o, a, v in images]}).encode()


class FakeRegistry:
    def __init__(self, *, token: str | None = None, basic: tuple[str, str] | None = None) -> None:
        self.blobs: dict[str, bytes] = {}
        self.manifests: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.token, self.basic = token, basic
        self.fail_next = 0
        self.truncate_once: set[str] = set()
        self.corrupt: set[str] = set()
        self.requests: list[tuple[str, dict]] = []
        self.lock = threading.Lock()
        reg = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _send(self, code, body=b"", headers=None):
                self.send_response(code)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                with reg.lock:
                    reg.requests.append((self.path, dict(self.headers)))
                    if reg.fail_next > 0:
                        reg.fail_next -= 1
                        return self._send(503, b"unavailable")
                if self.path.startswith("/token"):
                    if reg.basic:
                        want = "Basic " + base64.b64encode(f"{reg.basic[0]}:{reg.basic[1]}".encode()).decode()
                        if self.headers.get("Authorization") != want:
                            return self._send(401)
                    return self._send(200, json.dumps({"token": reg.token}).encode(), {"Content-Type": "application/json"})
                if reg.token and self.headers.get("Authorization") != f"Bearer {reg.token}":
                    host = self.headers.get("Host")
                    return self._send(401, b"", {"WWW-Authenticate":
                                                 f'Bearer realm="http://{host}/token",service="fake",scope="repository:x:pull"'})
                parts = self.path.split("/")
                # /v2/<repo...>/manifests/<ref> | /v2/<repo...>/blobs/<digest>
                if len(parts) < 5 or parts[1] != "v2":
                    return self._send(404)
                kind, ref, repo = parts[-2], parts[-1], "/".join(parts[2:-2])
                if kind == "manifests":
                    m = reg.manifests.get((repo, ref))
                    if not m:
                        return self._send(404)
                    return self._send(200, m[0], {"Content-Type": m[1], "Docker-Content-Digest": sha(m[0])})
                if kind == "blobs":
                    b = reg.blobs.get(ref)
                    if b is None:
                        return self._send(404)
                    if ref in reg.corrupt:
                        b = b[:-1] + bytes([b[-1] ^ 1])
                    start = 0
                    rng = self.headers.get("Range")
                    if rng and rng.startswith("bytes="):
                        start = int(rng[6:].split("-")[0])
                    body = b[start:]
                    code = 206 if start else 200
                    if ref in reg.truncate_once:
                        reg.truncate_once.discard(ref)
                        self.send_response(code)
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body[: len(body) // 2])
                        self.wfile.flush()
                        self.close_connection = True
                        return
                    return self._send(code, body, {"Content-Type": "application/octet-stream"})
                return self._send(404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.host = f"127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def add_image(self, repo: str, tag: str | None, img: dict) -> None:
        self.blobs[sha(img["config"])] = img["config"]
        for b in img["layers"]:
            self.blobs[sha(b)] = b
        self.manifests[(repo, img["digest"])] = (img["manifest"], MT_MANIFEST)
        if tag:
            self.manifests[(repo, tag)] = (img["manifest"], MT_MANIFEST)

    def add_index(self, repo: str, tag: str, index: bytes) -> None:
        self.manifests[(repo, tag)] = (index, MT_INDEX)
        self.manifests[(repo, sha(index))] = (index, MT_INDEX)

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
