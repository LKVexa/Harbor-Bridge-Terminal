"""In-process HTTP double of the Vault KV v2 / sys / approle API surface used by
``runtime/vault.py``.  It follows the documented wire shapes; it is NOT Vault and
passing against it is not a Vault certification (see COMPATIBILITY.md)."""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class FakeVault:
    def __init__(self, token="root-test-token", role=("role-1", "sid-1"), ssl_context=None):
        self.kv: dict[str, list[dict]] = {}
        self.tokens = {token}
        self.role = role
        self.sealed = False
        self.fail_status: list[int] = []
        self.delay_s = 0.0
        self.revoked: list[str] = []
        self.requests: list[tuple[str, str, dict]] = []
        self.namespace_seen: list[str | None] = []
        fv = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body=None):
                raw = b"" if body is None else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _do(self, method):
                u = urlsplit(self.path)
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}") if n else {}
                fv.requests.append((method, u.path, {k: v for k, v in self.headers.items()}))
                fv.namespace_seen.append(self.headers.get("X-Vault-Namespace"))
                if fv.delay_s:
                    time.sleep(fv.delay_s)
                if fv.fail_status:
                    return self._send(fv.fail_status.pop(0), {"errors": ["injected"]})
                p = u.path
                if p == "/v1/sys/health":
                    return self._send(503 if fv.sealed else 200, {"initialized": True, "sealed": fv.sealed, "version": "fake-1.0"})
                if p == "/v1/auth/approle/login" and method == "POST":
                    if (body.get("role_id"), body.get("secret_id")) != fv.role:
                        return self._send(400, {"errors": ["invalid role or secret id"]})
                    tok = f"approle-token-{len(fv.tokens)}"
                    fv.tokens.add(tok)
                    return self._send(200, {"auth": {"client_token": tok, "lease_duration": 60}})
                if self.headers.get("X-Vault-Token") not in fv.tokens:
                    return self._send(403, {"errors": ["permission denied"]})
                if fv.sealed:
                    return self._send(503, {"errors": ["Vault is sealed"]})
                parts = p.split("/", 4)   # ['', 'v1', mount, kind, name]
                if p == "/v1/sys/leases/revoke":
                    fv.revoked.append(body.get("lease_id"))
                    return self._send(204)
                if len(parts) == 5:
                    _, _, mount, kind, name = parts
                    hist = fv.kv.get(name)
                    if kind == "data" and method == "GET":
                        if not hist:
                            return self._send(404, {"errors": []})
                        q = parse_qs(u.query)
                        v = int(q["version"][0]) if "version" in q else len(hist)
                        if v < 1 or v > len(hist):
                            return self._send(404, {"errors": []})
                        e = hist[v - 1]
                        meta = {"version": v, "destroyed": e["destroyed"], "deletion_time": ""}
                        return self._send(200, {"lease_id": "", "lease_duration": 0,
                                                "data": {"data": None if e["destroyed"] else e["data"], "metadata": meta}})
                    if kind == "data" and method == "POST":
                        hist = fv.kv.setdefault(name, [])
                        cas = (body.get("options") or {}).get("cas")
                        if cas is not None and cas != len(hist):
                            return self._send(400, {"errors": ["check-and-set parameter did not match the current version"]})
                        hist.append({"data": body.get("data"), "destroyed": False})
                        return self._send(200, {"data": {"version": len(hist)}})
                    if kind == "metadata" and method == "GET":
                        if not hist:
                            return self._send(404, {"errors": []})
                        return self._send(200, {"data": {"current_version": len(hist), "versions": {
                            str(i + 1): {"destroyed": e["destroyed"]} for i, e in enumerate(hist)}}})
                    if kind == "destroy" and method == "POST":
                        for v in body.get("versions", []):
                            hist[v - 1]["destroyed"] = True
                        return self._send(204)
                return self._send(404, {"errors": []})

            def do_GET(self):
                self._do("GET")

            def do_POST(self):
                self._do("POST")

            def do_PUT(self):
                self._do("PUT")

        class Srv(ThreadingHTTPServer):
            daemon_threads = True

            def handle_error(self, request, client_address):
                pass   # client-side timeouts close sockets mid-write by design

        self.httpd = Srv(("127.0.0.1", 0), H)
        if ssl_context is not None:
            self.httpd.socket = ssl_context.wrap_socket(self.httpd.socket, server_side=True)
        scheme = "https" if ssl_context is not None else "http"
        self.port = self.httpd.server_address[1]
        self.address = f"{scheme}://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *e):
        self.httpd.shutdown()
        self.httpd.server_close()
