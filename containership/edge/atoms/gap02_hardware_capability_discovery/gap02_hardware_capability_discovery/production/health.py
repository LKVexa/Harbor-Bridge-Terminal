"""GAP02-MC-30 — Health/readiness endpoint (+ MC-31 /metrics, MC-35 /explain).

Loopback-only by default. /healthz = process alive; /readyz = a snapshot
exists, is younger than the freshness bound, and the node is not frozen.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from urllib.parse import parse_qs, urlparse

from .explain import explain


def readiness(executor, now: int, freshness: int = 60) -> tuple[bool, dict]:
    snap = executor.store.current()
    if snap is None:
        return False, {"ready": False, "reason": "no sweep"}
    if executor.quarantine.frozen:
        return False, {"ready": False, "reason": "frozen"}
    age = now - snap.report.published_at
    if age > freshness:
        return False, {"ready": False, "reason": "stale", "age": age}
    return True, {"ready": True, "generation": snap.generation, "age": age}


def serve(executor, metrics=None, host: str = "127.0.0.1", port: int = 0, freshness: int = 60):
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise ValueError("health endpoint binds loopback only; front it with an authenticated proxy")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silence default stderr logging
            pass

        def _send(self, code: int, body: str, ctype="application/json"):
            b = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/healthz":
                return self._send(200, '{"alive":true}')
            if u.path == "/readyz":
                ok, d = readiness(executor, int(time.time()), freshness)
                return self._send(200 if ok else 503, json.dumps(d))
            if u.path == "/metrics" and metrics is not None:
                return self._send(200, metrics.render(), "text/plain; version=0.0.4")
            if u.path == "/explain":
                cap = parse_qs(u.query).get("capability", [""])[0][:128]
                return self._send(200, json.dumps(explain(executor.store.current(), cap)))
            return self._send(404, '{"error":"not found"}')

    srv = ThreadingHTTPServer((host, port), H)
    threading.Thread(target=srv.serve_forever, daemon=True, name="gap02-health").start()
    return srv
