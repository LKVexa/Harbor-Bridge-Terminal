"""MC-05 / MC-06 transport: HTTPS JSON binding with mandatory mutual TLS.

``serve(service, ...)`` starts a stdlib ``ThreadingHTTPServer`` wrapped in an
``ssl.SSLContext`` with ``CERT_REQUIRED`` and TLS >= 1.2.  The peer certificate
(already chain-verified by OpenSSL against the client CA) is mapped to a
``Principal`` via ``principal_map`` keyed by certificate CN.  Unknown CNs get
401.  Bodies are size-capped before parsing.  This is a reference binding; a
production deployment would sit behind hardened ingress (BLOCKED: no infra).
"""
from __future__ import annotations

import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .errors import Gap06Error, fail

MAX_BODY = 10 * 1024 * 1024


def make_server(handler_fn, *, host, port, cert_file, key_file, client_ca_file, principal_map):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # no request logging of bodies/secrets
            pass

        def _principal(self):
            cert = self.connection.getpeercert()
            cn = None
            for rdn in (cert or {}).get("subject", ()):
                for k, v in rdn:
                    if k == "commonName":
                        cn = v
            p = principal_map.get(cn)
            if p is None:
                raise fail("E_UNAUTHENTICATED", "client certificate not mapped to a principal")
            return p

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n < 0 or n > MAX_BODY:
                    raise fail("E_SCHEMA", "body too large")
                body = self.rfile.read(n)
                out, status = handler_fn(self.path, self._principal(), body), 200
            except Gap06Error as e:
                out, status = e.to_dict(), e.to_dict()["http_status"]
            except Exception:
                out, status = fail("E_INTERNAL", "internal error").to_dict(), 500
            data = json.dumps(out).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(cert_file, key_file)
    ctx.load_verify_locations(client_ca_file)
    srv = ThreadingHTTPServer((host, port), H)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv
