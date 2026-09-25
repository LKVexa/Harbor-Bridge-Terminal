"""Minimal stdlib HTTP host for PLN-07 (MC-22, MC-39).

Endpoints: POST /v1/{issue,attenuate,verify,revoke,explain}; GET /livez,
/readyz, /healthz, /metrics; POST /admin/freeze|thaw (loopback only).
Body limit 64 KiB.  Environment:
  PLN07_CONFIG, PLN07_REVOCATION_LOG, PLN07_BIND (default 127.0.0.1:8707),
  PLN07_AUTH_SECRET (>=32 bytes, from a secret store), PLN07_TRUST_DOMAIN.
This host uses the reference authenticator/key store; production swaps them
for GAP-06 / GAP-07 adapters (see docs/ADR-0001.md).
"""
from __future__ import annotations

import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..config import ConfigStore
from ..identity import StaticTokenAuthenticator
from ..revocation import RevocationRegistry
from ..service import SecurityPlaneService
from ..signing import KeyStore

MAX_BODY = 64 * 1024


def build() -> SecurityPlaneService:
    secret = os.environ.get("PLN07_AUTH_SECRET", "").encode()
    if len(secret) < 32:
        raise SystemExit("PLN07_AUTH_SECRET must be set (>=32 bytes)")
    cfg = ConfigStore(Path(os.environ["PLN07_CONFIG"])) if os.environ.get("PLN07_CONFIG") else ConfigStore()
    keys = KeyStore(os.environ.get("PLN07_TRUST_DOMAIN", "prod"))
    keys.generate()
    rev = RevocationRegistry(Path(os.environ["PLN07_REVOCATION_LOG"])) if os.environ.get("PLN07_REVOCATION_LOG") else RevocationRegistry()
    return SecurityPlaneService(StaticTokenAuthenticator(secret), keys, config=cfg, revocations=rev)


def handler_for(svc: SecurityPlaneService):
    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, obj, ctype="application/json"):
            body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def log_message(self, *a):  # structured logging goes through Telemetry
            return

        def do_GET(self):
            h = svc.health()
            if self.path == "/livez":
                return self._send(200 if h["live"] else 503, {"live": h["live"]})
            if self.path == "/readyz":
                return self._send(200 if h["ready"] else 503, {"ready": h["ready"]})
            if self.path == "/healthz":
                return self._send(200, h)
            if self.path == "/metrics":
                return self._send(200, svc.telemetry.metrics.prometheus().encode(), "text/plain; version=0.0.4")
            self._send(404, {"code": "api.not_found"})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._send(413, {"code": "api.too_large"})
            try:
                req = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._send(400, {"code": "api.malformed"})
            req.setdefault("traceparent", self.headers.get("traceparent"))
            op = self.path.rsplit("/", 1)[-1]
            if self.path.startswith("/admin/"):
                if self.client_address[0] not in ("127.0.0.1", "::1"):
                    return self._send(403, {"code": "api.forbidden"})
                getattr(svc.quarantine, op)(req.get("kind", "plane"), req.get("value"),
                                            actor=req.get("actor", "local-admin"), reason=req.get("reason", ""))
                return self._send(200, {"ok": True})
            if op == "explain":
                return self._send(200, svc.explain(req["grant"], req["context"]))
            if op not in ("issue", "attenuate", "verify", "revoke"):
                return self._send(404, {"code": "api.not_found"})
            res = getattr(svc, op)(req)
            self._send(200 if res["ok"] or op == "verify" else 400, res)
    return H


def main() -> None:
    svc = build()
    host, port = os.environ.get("PLN07_BIND", "127.0.0.1:8707").rsplit(":", 1)
    ThreadingHTTPServer((host, int(port)), handler_for(svc)).serve_forever()


if __name__ == "__main__":
    main()
