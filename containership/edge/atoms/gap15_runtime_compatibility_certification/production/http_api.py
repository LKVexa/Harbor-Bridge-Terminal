"""Production service/API host (component 14) — stdlib HTTP(S) server.

Routes (API major version 1; any other major is rejected, MC-14-08):

  POST /v1/evidence            single envelope or {"items": [...]} batch
  POST /v1/certify             {"key": {...}, "new_admission": bool, "features": [...]}
  POST /v1/admission           admission contract (component 30)
  POST /v1/admission/recheck   {"request_id": ...}
  GET  /v1/matrix?partition=   PK_COMPATIBILITY_MATRIX/1
  GET  /v1/lifecycle?partition=  PK_RUNTIME_LIFECYCLE/1
  GET  /v1/explain/<decision>  explain (component 28)
  GET  /healthz  /readyz  /metrics  /version

Hardening: Content-Length required and bounded before reading; per-connection
socket deadline; bounded concurrency (ConcurrencyGate); structured error body
``{"error": {"category", "code", "message"}}`` with stable categories;
``Retry-After`` on 429/503; graceful drain on shutdown; optional TLS >= 1.2 with
client-certificate (mTLS) channel binding.
"""
from __future__ import annotations

import hashlib
import json
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .canonical import CanonicalError, canonical_bytes, parse
from .capacity import LIMITS
from .service import CertificationService, ServiceError, _err
from .state import CertKey

REQUEST_DEADLINE_S = 10.0


def tls_context(certfile: str, keyfile: str, client_ca: Optional[str] = None) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    ctx.load_cert_chain(certfile, keyfile)
    if client_ca:
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_verify_locations(client_ca)
    return ctx


def make_handler(svc: CertificationService, *, metrics_token: Optional[str] = None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "gap15"
        sys_version = ""
        timeout = REQUEST_DEADLINE_S

        def log_message(self, fmt, *args):  # route through the structured logger instead of stderr
            svc.log.log("debug", "http.access", path=self.path[:128], status=args[1] if len(args) > 1 else None)

        def _send(self, status: int, body: dict | str, *, ctype="application/json", retry_after: float = 0.0) -> None:
            data = body.encode() if isinstance(body, str) else canonical_bytes(body)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if retry_after:
                self.send_header("Retry-After", str(max(1, int(retry_after + 0.999))))
            self.end_headers()
            self.wfile.write(data)

        def _fail(self, exc: ServiceError) -> None:
            self._send(exc.http, exc.as_dict(), retry_after=exc.retry_after)

        def _token(self) -> str:
            h = self.headers.get("Authorization", "")
            if not h.startswith("Bearer "):
                raise _err("authn", "E_AUTH_MISSING")
            return h[7:].strip()

        def _binding(self) -> Optional[str]:
            try:
                der = self.connection.getpeercert(binary_form=True)  # type: ignore[attr-defined]
            except AttributeError:
                return None
            return hashlib.sha256(der).hexdigest() if der else None

        def _body(self):
            if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
                raise _err("validation", "E_CHUNKED_UNSUPPORTED")
            if self.headers.get("Content-Encoding"):
                raise _err("validation", "E_CONTENT_ENCODING_UNSUPPORTED", "compressed bodies are refused")
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise _err("validation", "E_CONTENT_TYPE")
            raw_len = self.headers.get("Content-Length")
            if raw_len is None or not raw_len.isdigit():
                raise _err("validation", "E_LENGTH_REQUIRED")
            n = int(raw_len)
            if n > LIMITS["max_body_bytes"] * 4:
                raise _err("validation", "E_PAYLOAD_TOO_LARGE")
            data = self.rfile.read(n)
            if len(data) != n:
                raise _err("validation", "E_PARTIAL_BODY")
            return data

        def _version_ok(self, path: str) -> str:
            if path in ("/healthz", "/readyz", "/metrics", "/version"):
                return path
            if not path.startswith("/v1/"):
                raise _err("validation", "E_API_VERSION_UNSUPPORTED", "supported API major versions: 1")
            return path[3:]

        def do_GET(self):
            t0 = time.perf_counter()
            try:
                u = urlparse(self.path)
                path = self._version_ok(u.path)
                q = parse_qs(u.query)
                if path == "/healthz":
                    return self._send(200, svc.health())
                if path == "/readyz":
                    r = svc.readiness()
                    return self._send(200 if r["ready"] else 503, r)
                if path == "/version":
                    return self._send(200, {"version": svc.log.build, "revisions": svc.log.revisions})
                if path == "/metrics":
                    if metrics_token is None or self.headers.get("Authorization", "") != f"Bearer {metrics_token}":
                        raise _err("authn", "E_AUTH_METRICS")
                    return self._send(200, svc.metrics.exposition(), ctype="text/plain; version=0.0.4")
                token = self._token()
                now = svc._now()
                if path == "/matrix":
                    part = q.get("partition", [""])[0]
                    p = svc._principal(token, now)
                    svc._authorize(p, "matrix.read", part)
                    return self._send(200, svc.store.matrix_view(part))
                if path == "/lifecycle":
                    part = q.get("partition", [""])[0]
                    p = svc._principal(token, now)
                    svc._authorize(p, "matrix.read", part)
                    return self._send(200, svc.lifecycle_view(part, now))
                if path.startswith("/explain/"):
                    return self._send(200, svc.explain(token, path.split("/", 2)[2], reevaluate=q.get("reevaluate") == ["1"]))
                raise _err("validation", "E_ROUTE", "unknown route")
            except ServiceError as exc:
                self._fail(exc)
            except Exception:  # never leak internals
                svc.log.log("error", "http.internal", path=self.path[:128])
                self._fail(_err("internal", "E_INTERNAL"))
            finally:
                svc.metrics.observe("gap15_request_seconds", time.perf_counter() - t0, op="matrix")

        def do_POST(self):
            try:
                path = self._version_ok(urlparse(self.path).path)
                token = self._token()
                raw = self._body()
                tp = self.headers.get("traceparent")
                if path == "/evidence":
                    try:
                        doc = parse(raw, max_bytes=LIMITS["max_body_bytes"] * 4)
                    except CanonicalError as exc:
                        raise _err("validation", exc.code) from None
                    if isinstance(doc, dict) and set(doc) == {"items"} and isinstance(doc["items"], list):
                        items = [canonical_bytes(i) for i in doc["items"]]
                        return self._send(200, svc.ingest_batch(token, items, traceparent=tp, channel_binding=self._binding()))
                    return self._send(200, svc.ingest(token, raw, traceparent=tp, channel_binding=self._binding()))
                try:
                    doc = parse(raw)
                except CanonicalError as exc:
                    raise _err("validation", exc.code) from None
                if not isinstance(doc, dict):
                    raise _err("validation", "E_SHAPE")
                if path == "/certify":
                    return self._send(200, svc.certify_request(token, doc, traceparent=tp))
                if path == "/admission":
                    return self._send(200, svc.admit(token, doc))
                if path == "/admission/recheck":
                    return self._send(200, svc.prestart_recheck(token, str(doc.get("request_id", ""))))
                raise _err("validation", "E_ROUTE", "unknown route")
            except ServiceError as exc:
                self._fail(exc)
            except Exception:
                svc.log.log("error", "http.internal", path=self.path[:128])
                self._fail(_err("internal", "E_INTERNAL"))

    return Handler


class ApiServer:
    def __init__(self, svc: CertificationService, host: str = "127.0.0.1", port: int = 0, *,
                 tls: Optional[ssl.SSLContext] = None, metrics_token: Optional[str] = None) -> None:
        self.svc = svc
        self.httpd = ThreadingHTTPServer((host, port), make_handler(svc, metrics_token=metrics_token))
        self.httpd.daemon_threads = True
        if tls is not None:
            self.httpd.socket = tls.wrap_socket(self.httpd.socket, server_side=True)
        self.thread: Optional[threading.Thread] = None

    @property
    def address(self) -> tuple:
        return self.httpd.server_address

    def start(self) -> "ApiServer":
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        return self

    def shutdown(self, deadline_s: float = 5.0) -> dict:
        """Stop new work, drain in-flight (bounded), close audit/store handles (MC-14-04)."""
        t0 = time.monotonic()
        self.svc.begin_shutdown()
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread:
            self.thread.join(timeout=max(0.0, deadline_s - (time.monotonic() - t0)))
        self.svc.store.db.execute("PRAGMA wal_checkpoint(FULL)")
        return {"drained_in_s": round(time.monotonic() - t0, 3), "clean": not (self.thread and self.thread.is_alive())}
