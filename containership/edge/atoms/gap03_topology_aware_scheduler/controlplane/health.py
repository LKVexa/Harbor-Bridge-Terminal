"""MC-018 - Production health / readiness endpoints (GAP03-HEALTH/1).

/livez   - process alive (cheap, no dependencies)
/startupz - recovery + migrations complete
/readyz  - SAFE TO COMMIT: lease held, stores writable, identity + audit up,
           no pending migration, degraded policy allows commit, hysteresis applied
/healthz/deep - authorized diagnostics (versions, generations, controls, stale ages)

Each dependency probe runs under a hard deadline in a bounded worker pool, so
a hung dependency yields ``timeout`` instead of blocking the probe.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .. import __version__

PROBE_DEADLINE_S = 0.25
READY_UP_AFTER, READY_DOWN_AFTER = 2, 1  # hysteresis: 2 good evaluations to become ready, 1 bad to drop
HEALTH_SLO = {"livez_p99_ms": 5, "readyz_p99_ms": 300, "availability": "99.95%"}


class Health:
    def __init__(self, *, checks: dict, info, clock=time.monotonic, max_workers: int = 4, metrics=None):
        self.metrics = metrics
        self.checks, self.info, self.clock = checks, info, clock  # checks: name -> callable returning (ok, detail)
        self.pool = cf.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="gap03-health")
        self.started = False
        self.shutting_down = False
        self._streak_ok = self._streak_bad = 0
        self.ready = False
        self._lock = threading.Lock()

    def livez(self) -> dict:
        return {"status": "ok"}

    def startupz(self) -> dict:
        return {"status": "ok" if self.started else "starting"}

    def _run(self) -> dict:
        futs = {n: self.pool.submit(fn) for n, fn in self.checks.items()}
        out = {}
        deadline = self.clock() + PROBE_DEADLINE_S
        for n, f in futs.items():
            try:
                ok, detail = f.result(timeout=max(0.0, deadline - self.clock()))
                out[n] = {"ok": bool(ok), "reason": detail}
            except cf.TimeoutError:
                out[n] = {"ok": False, "reason": "timeout"}
            except Exception as exc:  # noqa: BLE001
                out[n] = {"ok": False, "reason": f"error:{exc.__class__.__name__}"}
        return out

    def readyz(self) -> dict:
        deps = self._run()
        good = self.started and not self.shutting_down and all(d["ok"] for d in deps.values())
        with self._lock:
            if good:
                self._streak_ok, self._streak_bad = self._streak_ok + 1, 0
                if self._streak_ok >= READY_UP_AFTER:
                    self.ready = True
            else:
                self._streak_bad, self._streak_ok = self._streak_bad + 1, 0
                if self._streak_bad >= READY_DOWN_AFTER:
                    self.ready = False  # fail-safe: drop immediately
        failing = sorted(n for n, d in deps.items() if not d["ok"])
        if self.metrics:
            self.metrics.inc("gap03_health_probe_total", probe="readyz", status="ready" if self.ready else "not_ready")
        return {"status": "ready" if self.ready else "not_ready", "failing": failing}

    def deep(self, *, authorized: bool) -> dict:
        if not authorized:
            return {"status": "forbidden"}
        return {"version": __version__, **self.info(), "dependencies": self._run(), "ready": self.ready,
                "slo": HEALTH_SLO}


def serve(health: Health, host: str = "127.0.0.1", port: int = 0, *, deep_token: str | None = None):
    """Minimal HTTP binding (stdlib).  Returns (server, thread)."""

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # structured logging handles access logs
            pass

        def do_GET(self):
            if self.path == "/livez":
                code, body = 200, health.livez()
            elif self.path == "/startupz":
                body = health.startupz()
                code = 200 if body["status"] == "ok" else 503
            elif self.path == "/readyz":
                body = health.readyz()
                code = 200 if body["status"] == "ready" else 503
            elif self.path == "/healthz/deep":
                ok = deep_token is not None and self.headers.get("Authorization") == f"Bearer {deep_token}"
                body = health.deep(authorized=ok)
                code = 200 if ok else 403
            else:
                code, body = 404, {"status": "not_found"}
            data = json.dumps(body, sort_keys=True).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = ThreadingHTTPServer((host, port), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, t
