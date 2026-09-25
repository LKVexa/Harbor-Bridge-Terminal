"""Protocol-faithful Vault HTTP emulator for adjacent-layer tests.

Implements the subset of the Vault /v1 HTTP API the adapter uses, over a real
socket (optionally TLS), so the adapter's transport, headers, status mapping and
JSON handling are exercised end to end.  It is NOT a substitute for the real-Vault
job (tests/test_vault_real.py, gated on INV55_VAULT_ADDR) -- see waiver WVR-001.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
import threading
import urllib.parse


class FakeVault:
    def __init__(self, token: str = "root-test-token", tls: tuple[str, str] | None = None,
                 namespace: str | None = None) -> None:
        self.token = token
        self.namespace = namespace
        self.kv: dict[str, list[dict]] = {}
        self.approles = {"role-1": "sid-1"}
        self.revoked: list[str] = []
        self.sealed = False
        self.fail_next: list[int] = []     # status codes to return for the next N requests
        self.requests: list[tuple[str, str, dict]] = []
        self.version = "1.17.6"
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code: int, body: dict | None = None) -> None:
                raw = b"" if body is None else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _handle(self, method: str) -> None:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n)) if n else {}
                parsed = urllib.parse.urlparse(self.path)
                path, q = parsed.path, urllib.parse.parse_qs(parsed.query)
                fake.requests.append((method, path, dict(self.headers)))
                if fake.fail_next:
                    return self._send(fake.fail_next.pop(0), {"errors": ["injected"]})
                if path == "/v1/sys/health":
                    return self._send(503 if fake.sealed else 200,
                                      {"initialized": True, "sealed": fake.sealed, "version": fake.version})
                if path == "/v1/auth/approle/login":
                    if fake.approles.get(body.get("role_id")) == body.get("secret_id"):
                        return self._send(200, {"auth": {"client_token": fake.token, "lease_duration": 60}})
                    return self._send(400, {"errors": ["invalid role or secret ID"]})
                if fake.namespace and self.headers.get("X-Vault-Namespace") != fake.namespace:
                    return self._send(403, {"errors": ["namespace"]})
                if self.headers.get("X-Vault-Token") != fake.token:
                    return self._send(403, {"errors": ["permission denied"]})
                if path.startswith("/v1/secret/data/"):
                    name = urllib.parse.unquote(path[len("/v1/secret/data/"):])
                    hist = fake.kv.setdefault(name, []) if method == "POST" else fake.kv.get(name)
                    if method == "GET":
                        if not hist:
                            return self._send(404, {"errors": []})
                        v = int(q.get("version", [len(hist)])[0])
                        if v < 1 or v > len(hist):
                            return self._send(404, {"errors": []})
                        entry = hist[v - 1]
                        return self._send(200, {"data": {"data": None if entry["destroyed"] else entry["data"],
                                                         "metadata": {"version": v, "destroyed": entry["destroyed"],
                                                                      "deletion_time": ""}}})
                    cas = (body.get("options") or {}).get("cas")
                    if cas is not None and cas != len(hist):
                        return self._send(400, {"errors": ["check-and-set parameter did not match the current version"]})
                    hist.append({"data": body["data"], "destroyed": False})
                    return self._send(200, {"data": {"version": len(hist)}})
                if path.startswith("/v1/secret/metadata/"):
                    name = urllib.parse.unquote(path[len("/v1/secret/metadata/"):])
                    hist = fake.kv.get(name)
                    if not hist:
                        return self._send(404, {"errors": []})
                    return self._send(200, {"data": {"current_version": len(hist), "versions": {
                        str(i + 1): {"destroyed": e["destroyed"]} for i, e in enumerate(hist)}}})
                if path.startswith("/v1/secret/destroy/"):
                    name = urllib.parse.unquote(path[len("/v1/secret/destroy/"):])
                    for v in body.get("versions", []):
                        fake.kv[name][v - 1]["destroyed"] = True
                    return self._send(204)
                if path == "/v1/sys/leases/revoke":
                    fake.revoked.append(body["lease_id"])
                    return self._send(204)
                if path == "/v1/sys/leases/renew":
                    return self._send(200, {"lease_id": body["lease_id"], "lease_duration": body.get("increment", 0)})
                if path == "/v1/auth/token/renew-self":
                    return self._send(200, {"auth": {"lease_duration": 120}})
                return self._send(404, {"errors": ["no handler"]})

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def do_PUT(self):
                self._handle("PUT")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        if tls:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.load_cert_chain(*tls)
            self.server.socket = ctx.wrap_socket(self.server.socket, server_side=True)
        self.scheme = "https" if tls else "http"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def address(self) -> str:
        host = "localhost" if self.scheme == "https" else "127.0.0.1"
        return f"{self.scheme}://{host}:{self.server.server_address[1]}"

    def __enter__(self) -> "FakeVault":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()
