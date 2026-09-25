"""Metrics, structured logging, tracing, health/readiness/version endpoint and
safe explain view (items 41-45).

* Metrics: counters/gauges/histograms rendered in Prometheus text format;
  label cardinality is bounded (namespace/reason only — never object names).
* Logging: one JSON object per line, redacted, with trace/span ids.
* Tracing: W3C ``traceparent`` generation/propagation; spans are recorded to an
  in-process exporter (an OTLP exporter is a deployment choice, not included).
* Health: ``/healthz`` (liveness: loop progressed recently), ``/readyz``
  (leader-or-standby healthy, config valid, dependencies reachable),
  ``/version`` and ``/configz`` (digest only) served by stdlib http.server.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .audit import redact

_MAX_SERIES = 2000


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[tuple, float] = {}
        self.gauges: dict[tuple, float] = {}
        self.hist: dict[tuple, list[float]] = {}
        self.dropped_series = 0
        self.buckets = (0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5)

    def _key(self, name, labels):
        return (name, tuple(sorted((labels or {}).items())))

    def _room(self, store, key):
        if key in store:
            return True
        if len(self.counters) + len(self.gauges) + len(self.hist) >= _MAX_SERIES:
            self.dropped_series += 1
            return False
        return True

    def inc(self, name, labels=None, v=1.0):
        with self._lock:
            k = self._key(name, labels)
            if self._room(self.counters, k):
                self.counters[k] = self.counters.get(k, 0) + v

    def set(self, name, v, labels=None):
        with self._lock:
            k = self._key(name, labels)
            if self._room(self.gauges, k):
                self.gauges[k] = v

    def observe(self, name, v, labels=None):
        with self._lock:
            k = self._key(name, labels)
            if self._room(self.hist, k):
                self.hist.setdefault(k, []).append(v)

    def get(self, name, labels=None):
        return self.counters.get(self._key(name, labels), 0)

    def render(self) -> str:
        def lab(ls):
            return "{" + ",".join(f'{k}="{v}"' for k, v in ls) + "}" if ls else ""
        lines = []
        with self._lock:
            for (n, ls), v in sorted(self.counters.items()):
                lines.append(f"{n}{lab(ls)} {v}")
            for (n, ls), v in sorted(self.gauges.items()):
                lines.append(f"{n}{lab(ls)} {v}")
            for (n, ls), vs in sorted(self.hist.items()):
                for b in self.buckets:
                    lines.append(f'{n}_bucket{lab(ls + (("le", str(b)),))} {sum(1 for x in vs if x <= b)}')
                lines.append(f'{n}_bucket{lab(ls + (("le", "+Inf"),))} {len(vs)}')
                lines.append(f"{n}_sum{lab(ls)} {sum(vs)}")
                lines.append(f"{n}_count{lab(ls)} {len(vs)}")
        lines.append(f"inv67_metrics_dropped_series {self.dropped_series}")
        return "\n".join(lines) + "\n"


class JsonFormatter(logging.Formatter):
    def format(self, rec):
        body = {"ts": round(rec.created, 6), "level": rec.levelname.lower(), "logger": rec.name, "msg": rec.getMessage()}
        extra = getattr(rec, "fields", None)
        if extra:
            body.update(redact(extra))
        return json.dumps(body, sort_keys=True)


def get_logger(name="inv67", stream=None) -> logging.Logger:
    lg = logging.getLogger(name)
    if not lg.handlers or stream is not None:
        lg.handlers = []
        h = logging.StreamHandler(stream)
        h.setFormatter(JsonFormatter())
        lg.addHandler(h)
        lg.propagate = False
        lg.setLevel(logging.INFO)
    return lg


def log(lg: logging.Logger, level: int, msg: str, **fields):
    lg.log(level, msg, extra={"fields": fields})


class Tracer:
    def __init__(self):
        self.spans: list[dict] = []
        self._lock = threading.Lock()
        self._local = threading.local()

    @staticmethod
    def parse(tp: str | None):
        if not tp:
            return None
        try:
            ver, tid, sid, flags = tp.split("-")
            if ver == "00" and len(tid) == 32 and len(sid) == 16 and int(tid, 16) and int(sid, 16):
                return tid, sid
        except (AttributeError, ValueError):
            pass
        return None

    @contextmanager
    def span(self, span_name, parent: str | None = None, **attrs):
        ctx = self.parse(parent) if parent else getattr(self._local, "ctx", None)
        tid = ctx[0] if ctx else os.urandom(16).hex()
        sid = os.urandom(8).hex()
        prev = getattr(self._local, "ctx", None)
        self._local.ctx = (tid, sid)
        t0 = time.perf_counter()
        err = None
        try:
            yield f"00-{tid}-{sid}-01"
        except Exception as e:
            err = type(e).__name__
            raise
        finally:
            with self._lock:
                self.spans.append({"name": span_name, "trace": tid, "span": sid, "parent": ctx[1] if ctx else None,
                                   "ms": round((time.perf_counter() - t0) * 1000, 3), "error": err,
                                   "attrs": redact(attrs)})
            self._local.ctx = prev


class Health:
    def __init__(self, version: str, stall_after: float = 60.0, clock=time.monotonic):
        self.version, self.stall_after, self.clock = version, stall_after, clock
        self.last_progress = clock()
        self.checks: dict[str, Callable[[], bool]] = {}
        self.config_digest = ""
        self.capabilities: list[str] = []

    def progressed(self):
        self.last_progress = self.clock()

    def live(self) -> tuple[bool, str]:
        age = self.clock() - self.last_progress
        return (age <= self.stall_after, f"last progress {age:.1f}s ago")

    def ready(self) -> tuple[bool, dict]:
        res = {}
        for name, fn in self.checks.items():
            try:
                res[name] = bool(fn())
            except Exception:  # noqa: BLE001 - any failing dependency check means not ready (fail closed)
                res[name] = False
        live, _ = self.live()
        res["loop"] = live
        return all(res.values()), res

    def serve(self, host="127.0.0.1", port=0, metrics: Metrics | None = None):
        health = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype="application/json"):
                data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path == "/healthz":
                    ok, msg = health.live()
                    self._send(200 if ok else 503, {"ok": ok, "detail": msg})
                elif self.path == "/readyz":
                    ok, res = health.ready()
                    self._send(200 if ok else 503, {"ok": ok, "checks": res})
                elif self.path == "/version":
                    self._send(200, {"version": health.version, "capabilities": health.capabilities})
                elif self.path == "/configz":
                    self._send(200, {"configDigest": health.config_digest})
                elif self.path == "/metrics" and metrics is not None:
                    self._send(200, metrics.render(), "text/plain; version=0.0.4")
                else:
                    self._send(404, {"error": "not found"})

        srv = ThreadingHTTPServer((host, port), H)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        return srv


def explain(obj: dict) -> dict:
    """Safe diagnostics: why is this workload in its current state? Spec values
    are summarized, never echoed wholesale; annotations/secret-like keys redacted."""
    st = obj.get("status", {})
    return redact({
        "object": f'{obj["metadata"]["namespace"]}/{obj["metadata"]["name"]}',
        "generation": obj["metadata"].get("generation"),
        "observedGeneration": st.get("observedGeneration"),
        "phase": st.get("phase"), "state": st.get("state"),
        "attempt": st.get("attemptId"),
        "conditions": [{k: c[k] for k in ("type", "status", "reason", "message")} for c in st.get("conditions", [])],
        "lastError": st.get("lastError"),
        "finalizers": obj["metadata"].get("finalizers", []),
        "units": [u.get("name") for u in (obj.get("spec", {}).get("template", {}).get("spec", {}).get("containers") or [])],
    })
