"""Observability for INV-29 (MC079..MC092).

* ``Metrics``      - counters / gauges / histograms, Prometheus text exposition,
                     hard label-cardinality cap (overflow folds into "__other__").
* ``Logger``       - structured JSON-lines logging with redaction and trace ids.
* ``traceparent``  - W3C trace-context parse / generate / propagate.
* ``DecisionLog``  - bounded decision-reason event stream + operator explain view.
* ``serve()``      - stdlib HTTP endpoints: /healthz /readyz /version /dependencies
                     /metrics /decisions /explain?nonce=...
* ``ALERT_RULES``  - failure-classification + alert rules as data (exported to
                     ops/alerts.yaml by tools/build_release.py).
"""
from __future__ import annotations

import collections
import json
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict, Optional, TextIO, Tuple
from urllib.parse import parse_qs, urlparse

from .records import redact

MAX_SERIES_PER_METRIC = 200
LATENCY_BUCKETS_MS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 1000)
_LABEL_VALUE = re.compile(r"^[A-Za-z0-9_.:/-]{0,64}$")


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._c: Dict[str, Dict[Tuple, float]] = collections.defaultdict(dict)
        self._g: Dict[str, Dict[Tuple, float]] = collections.defaultdict(dict)
        self._h: Dict[str, Dict[Tuple, list]] = collections.defaultdict(dict)
        self.dropped_series = 0

    def _key(self, store: dict, name: str, labels: dict) -> Tuple:
        key = tuple(sorted((k, v if type(v) is str and _LABEL_VALUE.fullmatch(v) else "__invalid__")
                           for k, v in labels.items()))
        series = store[name]
        if key not in series and len(series) >= MAX_SERIES_PER_METRIC:
            self.dropped_series += 1
            key = tuple((k, "__other__") for k, _ in key)
        return key

    def inc(self, name: str, value: float = 1.0, /, **labels) -> None:
        with self._lock:
            k = self._key(self._c, name, labels)
            self._c[name][k] = self._c[name].get(k, 0.0) + value

    def set(self, name: str, value: float, /, **labels) -> None:
        with self._lock:
            self._g[name][self._key(self._g, name, labels)] = float(value)

    def observe(self, name: str, value_ms: float, /, **labels) -> None:
        with self._lock:
            k = self._key(self._h, name, labels)
            h = self._h[name].setdefault(k, [0] * (len(LATENCY_BUCKETS_MS) + 1) + [0.0, 0])
            for i, b in enumerate(LATENCY_BUCKETS_MS):
                if value_ms <= b:
                    h[i] += 1
            h[len(LATENCY_BUCKETS_MS)] += 1  # +Inf
            h[-2] += value_ms
            h[-1] += 1

    def value(self, name: str, /, **labels) -> float:
        with self._lock:
            key = tuple(sorted(labels.items()))
            return self._c.get(name, {}).get(key, self._g.get(name, {}).get(key, 0.0))

    def exposition(self) -> str:
        def fmt(key, extra=()):
            items = list(key) + list(extra)
            return "{" + ",".join(f'{k}="{v}"' for k, v in items) + "}" if items else ""
        lines = []
        with self._lock:
            for name, series in sorted(self._c.items()):
                lines.append(f"# TYPE {name} counter")
                lines += [f"{name}{fmt(k)} {v}" for k, v in sorted(series.items())]
            for name, series in sorted(self._g.items()):
                lines.append(f"# TYPE {name} gauge")
                lines += [f"{name}{fmt(k)} {v}" for k, v in sorted(series.items())]
            for name, series in sorted(self._h.items()):
                lines.append(f"# TYPE {name} histogram")
                for k, h in sorted(series.items()):
                    for i, b in enumerate(LATENCY_BUCKETS_MS):
                        lines.append(f"{name}_bucket{fmt(k, [('le', str(b))])} {h[i]}")
                    lines.append(f"{name}_bucket{fmt(k, [('le', '+Inf')])} {h[len(LATENCY_BUCKETS_MS)]}")
                    lines.append(f"{name}_sum{fmt(k)} {h[-2]}")
                    lines.append(f"{name}_count{fmt(k)} {h[-1]}")
            lines.append("# TYPE inv29_metric_series_dropped_total counter")
            lines.append(f"inv29_metric_series_dropped_total {self.dropped_series}")
        return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ tracing
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def traceparent(parent: Optional[str] = None) -> str:
    """Return a child traceparent; start a new trace when ``parent`` is absent/invalid."""
    m = _TP.fullmatch(parent or "")
    trace_id = m.group(1) if m and m.group(1) != "0" * 32 else secrets.token_hex(16)
    flags = m.group(3) if m else "01"
    return f"00-{trace_id}-{secrets.token_hex(8)}-{flags}"


def trace_id(tp: str) -> Optional[str]:
    m = _TP.fullmatch(tp or "")
    return m.group(1) if m else None


# ------------------------------------------------------------------ logging
class Logger:
    def __init__(self, stream: TextIO = sys.stderr, *, component: str = "INV-29", version: str = "",
                 release: str = "", sample_debug: float = 0.0):
        self.stream, self.component, self.version, self.release = stream, component, version, release
        self.sample_debug = sample_debug
        self._lock = threading.Lock()

    def log(self, level: str, event: str, *, tp: Optional[str] = None, **fields) -> dict:
        if level == "debug" and (self.sample_debug <= 0 or secrets.randbelow(10_000) >= self.sample_debug * 10_000):
            return {}
        rec = {"ts": round(time.time(), 3), "level": level, "component": self.component,
               "version": self.version, "release": self.release, "event": event,
               "trace_id": trace_id(tp) if tp else None, **redact(fields)}
        line = json.dumps(rec, sort_keys=True, default=str)
        with self._lock:
            self.stream.write(line + "\n")
        return rec


# ------------------------------------------------------------------ decisions
class DecisionLog:
    """Bounded ring of decision-reason events; feeds the explain view."""

    def __init__(self, capacity: int = 10_000, metrics: Optional[Metrics] = None, logger: Optional[Logger] = None):
        self._ring = collections.deque(maxlen=capacity)
        self._lock = threading.Lock()
        self.metrics, self.logger = metrics, logger

    def __call__(self, event: dict) -> None:
        ev = {"at": time.time(), **redact(event)}
        with self._lock:
            self._ring.append(ev)
        if self.metrics is not None and event.get("event") == "decision":
            self.metrics.inc("inv29_compositions_total", outcome=event["outcome"], code=event["code"])
            if event["code"] == "INV29-E-IMPORT":
                self.metrics.inc("inv29_import_refusals_total")
            if event["code"] in ("INV29-E-LAYER", "INV29-E-ATTESTATION"):
                self.metrics.inc("inv29_layer_failures_total", code=event["code"])
        if self.logger is not None:
            fields = {k: v for k, v in event.items() if k != "event"}
            self.logger.log("info" if event.get("outcome") != "refused" else "warn",
                            str(event.get("event", "event")), **fields)

    def recent(self, n: int = 100) -> list:
        with self._lock:
            return list(self._ring)[-n:]

    def explain(self, *, module: Optional[str] = None, tenant: Optional[str] = None) -> list:
        """Operator explain view: why was this module/tenant admitted or refused?"""
        with self._lock:
            evs = [e for e in self._ring if e.get("event") == "decision"
                   and (module is None or e.get("module") == module)
                   and (tenant is None or e.get("tenant") == tenant)]
        return [{"at": e["at"], "outcome": e["outcome"], "code": e["code"],
                 "why": EXPLANATIONS.get(e["code"], "see reason"), "reason": e.get("reason")} for e in evs[-50:]]


EXPLANATIONS = {
    "INV29-OK": "both layers independently verified, imports closed, identity/attestation/policy/replay checks passed",
    "INV29-E-LAYER": "a layer failed verification or the environment requires more layers than provided",
    "INV29-E-IMPORT": "the module imports a capability the sealed host image does not expose",
    "INV29-E-ATTESTATION": "a sealed/hardened/measured-boot attestation was missing, stale, revoked or did not verify",
    "INV29-E-IDENTITY": "tenant id or artifact digest missing/malformed",
    "INV29-E-POLICY": "tenant not authorised, capability denylisted, over the cardinality limit, or lacking provenance",
    "INV29-E-REPLAY": "nonce reused or record expired",
    "INV29-E-INTERFACE": "typed interface signature/version incompatible",
    "INV29-E-DISABLED": "the hybrid tier is under emergency disable",
    "INV29-E-DEPENDENCY": "a required dependency was absent, incompatible, degraded or unavailable",
    "INV29-E-INPUT": "malformed input",
}

# failure classification + alerting (MC092); thresholds are defaults, owners tune them in ops/
ALERT_RULES = [
    {"alert": "INV29SingleLayerAdmitted", "severity": "SEV1", "class": "security-invariant",
     "expr": 'sum(inv29_compositions_total{outcome="admitted"}) and on() inv29_min_layer_count < 2',
     "for": "0m", "action": "emergency disable; page security on-call"},
    {"alert": "INV29AttestationFailuresSpike", "severity": "SEV2", "class": "trust-chain",
     "expr": 'rate(inv29_layer_failures_total{code="INV29-E-ATTESTATION"}[5m]) > 0.1', "for": "10m",
     "action": "check INV-27/INV-44 signer health and key revocations"},
    {"alert": "INV29DependencyUnavailable", "severity": "SEV2", "class": "dependency",
     "expr": "inv29_dependency_available == 0", "for": "5m",
     "action": "admission fails closed; restore dependency; see RUNBOOKS.md#dependency-loss"},
    {"alert": "INV29ImportRefusalRate", "severity": "SEV3", "class": "workload-config",
     "expr": "rate(inv29_import_refusals_total[15m]) > 1", "for": "15m",
     "action": "notify workload owners; not a platform fault"},
    {"alert": "INV29AdmissionLatencyP99", "severity": "SEV3", "class": "performance",
     "expr": "histogram_quantile(0.99, rate(inv29_admission_latency_ms_bucket[5m])) > 25", "for": "15m",
     "action": "see CAPACITY.md"},
    {"alert": "INV29ReplayCacheSaturated", "severity": "SEV2", "class": "capacity",
     "expr": "inv29_replay_cache_fill_ratio > 0.9", "for": "5m",
     "action": "scale replicas / shorten record TTL; saturation refuses admissions"},
    {"alert": "INV29MetricCardinalityOverflow", "severity": "SEV4", "class": "telemetry",
     "expr": "increase(inv29_metric_series_dropped_total[1h]) > 0", "for": "0m", "action": "review labels"},
]


# ------------------------------------------------------------------ endpoints
def serve(*, port: int, version_info, ready: Callable[[], Tuple[bool, dict]],
          dependencies: Callable[[], dict], metrics: Metrics, decisions: DecisionLog,
          host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """Start the operational endpoints on a daemon thread and return the server."""

    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, body, ctype="application/json"):
            data = body.encode() if type(body) is str else json.dumps(body, sort_keys=True, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            u = urlparse(self.path)
            if u.path == "/healthz":
                return self._send(200, {"status": "alive"})
            if u.path == "/readyz":
                ok, detail = ready()
                return self._send(200 if ok else 503, {"ready": ok, **detail})
            if u.path == "/version":
                return self._send(200, version_info() if callable(version_info) else version_info)
            if u.path == "/dependencies":
                d = dependencies()
                return self._send(200 if d.get("all_required_available") else 503, d)
            if u.path == "/metrics":
                return self._send(200, metrics.exposition(), "text/plain; version=0.0.4")
            if u.path == "/decisions":
                return self._send(200, decisions.recent(100))
            if u.path == "/explain":
                q = parse_qs(u.query)
                return self._send(200, decisions.explain(module=(q.get("module") or [None])[0],
                                                         tenant=(q.get("tenant") or [None])[0]))
            return self._send(404, {"error": "not found"})

        def log_message(self, *a):  # silence default stderr access log
            pass

    srv = ThreadingHTTPServer((host, port), H)
    threading.Thread(target=srv.serve_forever, daemon=True, name="inv29-http").start()
    return srv
