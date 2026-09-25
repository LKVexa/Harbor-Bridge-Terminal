"""Remote transport adapter (GAP-006) and remote chain endpoint.

INV-21 does not own the network transport; it owns the *handoff*. This module
supplies the adapter contract plus two concrete adapters:

* :class:`HttpJsonTransport` -- stdlib HTTP/1.1 JSON POST to a peer's
  :class:`ChainHttpServer` (``POST /pk/local-chain/1``). The credential travels
  in ``Authorization: Bearer``; the body is a ``PK_LOCAL_CHAIN/1`` request.
* :class:`LoopbackTransport` -- same wire format through a JSON round-trip
  in-process, used by the semantic-equivalence corpus and fault injection.

Wire rules: responses are validated against ``local_chain_response``; a
malformed/oversized body or unknown error code becomes
``PK_CHAIN_REMOTE_PROTOCOL``; connection failures / timeouts become
``PK_CHAIN_TRANSPORT_UNAVAILABLE`` / ``PK_CHAIN_DEADLINE_EXCEEDED``. The
server re-authenticates the credential, re-applies depth/cycle bounds and runs
the call through its own chainer, so a remote hop has the same authz as a
local one.
"""
from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Protocol

from .context import CallContext, Deadline, IdentityVerifier
from .errors import (ChainError, DeadlineExceeded, RemoteProtocolError, TransportUnavailable,
                     ValidationFailed, from_envelope, normalize)
from .schema import load_schema, validate

CHAIN_SCHEMA = "PK_LOCAL_CHAIN/1"
PATH = "/pk/local-chain/1"
MAX_BODY = 1 << 20


class RemoteTransport(Protocol):
    def send(self, callee: str, request, ctx: CallContext, timeout_s: float): ...


def build_wire(callee: str, request, ctx: CallContext) -> dict:
    return {"schema": CHAIN_SCHEMA, "callee": callee, "context": ctx.to_wire(), "payload": request}


def parse_response(body: bytes):
    if len(body) > MAX_BODY:
        raise RemoteProtocolError("remote response too large")
    try:
        doc = json.loads(body)
    except (ValueError, RecursionError):
        raise RemoteProtocolError("remote response not JSON") from None
    if validate(doc, load_schema("local_chain_response")):
        raise RemoteProtocolError("remote response violates PK_LOCAL_CHAIN/1")
    if doc["ok"]:
        return doc.get("result")
    raise from_envelope(doc.get("error"))


class LoopbackTransport:
    """In-process peer; exercises the exact wire encoding without sockets."""

    def __init__(self, server: "ChainEndpoint") -> None:
        self.server = server
        self.fail_next: Optional[BaseException] = None
        self.sent = 0

    def send(self, callee, request, ctx, timeout_s):
        self.sent += 1
        if self.fail_next is not None:
            exc, self.fail_next = self.fail_next, None
            raise exc
        body = json.dumps(build_wire(callee, request, ctx)).encode()
        status, out = self.server.handle(body, ctx.credential)
        return parse_response(out)


class HttpJsonTransport:
    def __init__(self, base_url: str, *, max_response: int = MAX_BODY, ssl_context=None,
                 allow_plaintext: bool = False) -> None:
        from urllib.parse import urlsplit
        u = urlsplit(base_url)
        if u.scheme not in ("http", "https") or not u.hostname:
            raise ValueError("base_url must be http(s)://host[:port]")
        loopback = u.hostname in ("127.0.0.1", "::1", "localhost")
        if u.scheme == "http" and not (loopback or allow_plaintext):
            # the bearer credential must never cross a network in clear text (C047)
            raise ValueError("plaintext http refused for non-loopback peer; use https")
        self.url = base_url.rstrip("/") + PATH
        self.max_response = max_response
        self.ssl_context = ssl_context

    def send(self, callee, request, ctx, timeout_s):
        if timeout_s <= 0:
            raise DeadlineExceeded("no time left for remote hop", trace_id=ctx.trace_id)
        body = json.dumps(build_wire(callee, request, ctx)).encode()
        req = urllib.request.Request(self.url, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {ctx.credential or ''}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout_s, context=self.ssl_context) as resp:
                data = resp.read(self.max_response + 1)
        except urllib.error.HTTPError as e:
            data = e.read(self.max_response + 1)
        except (socket.timeout, TimeoutError):
            raise DeadlineExceeded("remote hop timed out", trace_id=ctx.trace_id) from None
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            raise TransportUnavailable("remote peer unreachable", trace_id=ctx.trace_id) from e
        return parse_response(data)


class ChainEndpoint:
    """Server side of a remote hop: authenticate, validate, dispatch via local chainer."""

    def __init__(self, chainer, verifier: IdentityVerifier, *, max_token_age_s: float = 300.0) -> None:
        self.chainer = chainer
        self.verifier = verifier
        # bearer credentials are multi-hop by design (not single-use); this bounds the
        # replay window of a captured token regardless of the TTL it was issued with
        self.max_token_age_s = max_token_age_s
        # NOTE (follow-up audit SP-10): request-level de-duplication was tried and removed. The body is
        # not signed, so a party holding the bearer token can mint fresh requests at will; de-dup only
        # broke legitimate repeated calls (semantic divergence from the local path). Real replay
        # protection needs channel binding / mTLS or request signing (ADR-005).

    def handle(self, body: bytes, credential: Optional[str]) -> tuple:
        trace = None
        try:
            if len(body) > MAX_BODY:
                raise ValidationFailed("request too large")
            try:
                doc = json.loads(body)
            except (ValueError, RecursionError):
                raise ValidationFailed("request not JSON") from None
            if validate(doc, load_schema("local_chain_request")):
                raise ValidationFailed("request violates PK_LOCAL_CHAIN/1")
            c = doc["context"]
            trace = c["trace_id"]
            principal = self.verifier.verify(credential or "")
            import time as _t
            if _t.time() - principal.issued_at > self.max_token_age_s:
                from .errors import Unauthenticated
                raise Unauthenticated("credential older than peer max_token_age_s")
            if principal.tenant != c["tenant"] or principal.subject != c["subject"]:
                raise ValidationFailed("context does not match credential", field="context")
            dl = None if c.get("deadline_ms") is None else Deadline.after(max(0.001, c["deadline_ms"] / 1000))
            ctx = CallContext(principal, c["trace_id"], c["operation"], c.get("idempotency_key"), dl,
                              path=tuple(c["path"]), credential=credential)
            result = self.chainer.invoke(doc["callee"], doc["payload"], ctx, _allow_remote=False)
            out = {"schema": CHAIN_SCHEMA, "ok": True, "route": "local", "result": result, "trace_id": trace}
            return 200, json.dumps(out).encode()
        except BaseException as exc:  # noqa: BLE001 -- normalised, never leaked
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            err = normalize(exc, origin="handler", correlation_id=trace)
            out = {"schema": CHAIN_SCHEMA, "ok": False, "route": "refused", "error": err.envelope()}
            if trace:
                out["trace_id"] = trace
            return 200, json.dumps(out).encode()


class ChainHttpServer:
    """Minimal threaded HTTP host for a ChainEndpoint (tests / single-node)."""

    def __init__(self, endpoint: ChainEndpoint, host: str = "127.0.0.1", port: int = 0) -> None:
        ep = endpoint

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def _send(self, status, body, ctype="application/json"):
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):  # noqa: N802 -- health/readiness/metrics surface (GAP-019)
                ch = ep.chainer
                if self.path == "/healthz":
                    h = ch.health(); self._send(200 if h["live"] else 503, json.dumps({"live": h["live"]}).encode())
                elif self.path == "/readyz":
                    h = ch.health(); self._send(200 if h["ready"] else 503, json.dumps(h, default=str).encode())
                elif self.path == "/metrics":
                    self._send(200, ch.export_metrics().encode(), "text/plain; version=0.0.4")
                else:
                    self._send(404, b"{}")

            def do_POST(self):  # noqa: N802
                if self.path != PATH:
                    self.send_response(404); self.end_headers(); return
                n = int(self.headers.get("Content-Length") or 0)
                if n > MAX_BODY:
                    self.send_response(413); self.end_headers(); return
                auth = self.headers.get("Authorization", "")
                token = auth[7:] if auth.startswith("Bearer ") else None
                status, out = ep.handle(self.rfile.read(n), token)
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(out)))
                    self.end_headers()
                    self.wfile.write(out)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # caller gave up (deadline); result is discarded, never retried implicitly

        self.httpd = ThreadingHTTPServer((host, port), H)
        self.httpd.daemon_threads = True
        self.url = f"http://{host}:{self.httpd.server_address[1]}"
        self._t = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self._t.start(); return self

    def __exit__(self, *exc):
        self.httpd.shutdown(); self.httpd.server_close()
