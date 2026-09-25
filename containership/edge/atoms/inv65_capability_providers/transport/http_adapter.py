"""HTTP/JSON transport adapter (M04).  Maps PK_PROVIDER_LINK/1 and call
operations onto a bounded request surface; errors are PK_PROVIDER_ERROR/1
envelopes with catalogued HTTP statuses.  Request bodies are capped, content
type enforced, and credentials read only from the Authorization header."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

from ..errors.mapping import ProviderFault, http_status, new_correlation_id, to_envelope
from ..health.probes import probe_status

MAX_BODY = 64 * 1024


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        server_version = "inv65-provider"
        sys_version = ""

        def log_message(self, *a):  # structured logging goes through service.log
            return

        def _send(self, status: int, body: dict | str, ctype="application/json"):
            data = (json.dumps(body, sort_keys=True) if not isinstance(body, str) else body).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _fail(self, exc, cid):
            env = to_envelope(exc, cid)
            self._send(http_status(env["code"]), env)

        def _token(self):
            h = self.headers.get("Authorization", "")
            return h[7:] if h.startswith("Bearer ") else ""

        def do_GET(self):
            if self.path == "/livez":
                r = service.health(); self._send(probe_status(r, "live"), r)
            elif self.path == "/readyz":
                r = service.health(); self._send(probe_status(r, "ready"), r)
            elif self.path == "/metrics":
                self._send(200, service.metrics.exposition(), "text/plain; version=0.0.4")
            elif self.path == "/v1/contract":
                self._send(200, {"schema": "PK_PROVIDER_CONTRACT/1", "contract_id": service.contract_id,
                                 "versions": ["1.0"], "instance": service.instance_id})
            else:
                self._fail(ProviderFault("PK_PROVIDER_NO_LINK", "unknown path"), new_correlation_id())

        def do_POST(self):
            cid = new_correlation_id()
            try:
                if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                    raise ProviderFault("PK_PROVIDER_INVALID_LINK", "content-type must be application/json")
                try:
                    n = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    n = -1
                if n < 0 or n > MAX_BODY:
                    raise ProviderFault("PK_PROVIDER_INVALID_LINK", "body missing or too large")
                try:
                    body = json.loads(self.rfile.read(n) or b"{}")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    raise ProviderFault("PK_PROVIDER_INVALID_LINK", "malformed JSON") from None
                if not isinstance(body, dict):
                    raise ProviderFault("PK_PROVIDER_INVALID_LINK", "body must be an object")
                tok, dec = self._token(), body.get("decision")
                if self.path == "/v1/link":
                    out = service.link(tok, dec, link_name=body.get("link_name"), config=body.get("config"),
                                       secret_ref=body.get("secret_ref"), reason=str(body.get("reason", "link"))[:200])
                elif self.path == "/v1/unlink":
                    out = {"revoked": service.unlink(tok, dec, link_name=body.get("link_name"))}
                elif self.path == "/v1/call":
                    out = service.call(tok, dec, link_name=body.get("link_name"), op=body.get("op"),
                                       payload=body.get("payload") if isinstance(body.get("payload"), dict) else {},
                                       meta=body.get("meta") if isinstance(body.get("meta"), dict) else None)
                else:
                    raise ProviderFault("PK_PROVIDER_NO_LINK", "unknown path")
                self._send(200, out)
            except ProviderFault as e:
                self._fail(e, cid)
            except Exception as e:
                code = getattr(e, "code", "PK_PROVIDER_ERROR")
                self._fail(ProviderFault(code if isinstance(code, str) and code.startswith("PK_PROVIDER_") else "PK_PROVIDER_ERROR", "request failed"), cid)
    return Handler
