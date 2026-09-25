"""Observability and operator experience (G12-G075..G084).

* ``Metrics`` — registry with declared name/type/unit/help/labels, a per-metric
  label-cardinality budget (overflowing label sets collapse into
  ``__overflow__`` and are counted), fixed histogram buckets, Prometheus text
  exposition.  ``CATALOG`` is the stable metric vocabulary; raw peer ids, IPs,
  candidates, exceptions or URLs are refused as label values.
* ``EventLog`` — JSON-lines events with stable ``event_id``, severity and
  reason code, bounded field sizes, privacy redaction, and repeat suppression
  that keeps count + first/last occurrence.
* ``TraceContext`` — W3C traceparent parse/format; spans for request, gather,
  attempt, auth, relay allocation, validation, migration and teardown; an
  untrusted inbound traceparent is replaced (and linked), never adopted.
* ``HealthServer`` — /livez, /readyz (dependency-aware) and /metrics over
  http.server bound to loopback by default.
* ``explain`` — operator explain view built from a path state + attempt
  history + reason codes, with endpoints pseudonymised.
* ``dashboard`` / ``alert_rules`` — generated Grafana JSON and Prometheus
  multi-window burn-rate rules from CATALOG (validated by synthetic injection
  in the tests: retry storm vs load, relay saturation, DNS failure, traversal
  regression, security event are distinguishable).
* ``RETENTION`` — telemetry retention/sampling/privacy policy as data;
  ``lineage`` stamps release/config/topology identifiers onto telemetry.
"""
from __future__ import annotations

import hashlib
import http.server
import ipaddress
import json
import os
import re
import secrets as _secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from . import reasons
from .security import redact

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)

CATALOG = {
    "g12_attempts_total": ("counter", "1", "Traversal attempts by strategy and outcome class", ("strategy", "outcome")),
    "g12_establish_seconds": ("histogram", "s", "Time to establish a usable path", ("strategy",)),
    "g12_active_paths": ("gauge", "1", "Paths currently healthy by strategy", ("strategy",)),
    "g12_partitions_total": ("counter", "1", "Peers declared partitioned", ()),
    "g12_retries_total": ("counter", "1", "Retry attempts after backoff", ("layer",)),
    "g12_backoff_seconds": ("histogram", "s", "Scheduled retry delay", ()),
    "g12_relay_bytes_total": ("counter", "By", "Bytes carried by relay", ("direction", "region")),
    "g12_relay_cost_usd_total": ("counter", "USD", "Estimated relay cost", ("region",)),
    "g12_dependency_up": ("gauge", "1", "Dependency health (1 up, 0 down/stale/unknown)", ("dependency",)),
    "g12_policy_rejections_total": ("counter", "1", "Policy/security rejections by reason", ("reason",)),
    "g12_breaker_state": ("gauge", "1", "Circuit breaker state (0 closed, 1 half-open, 2 open)", ("scope",)),
    "g12_dns_failures_total": ("counter", "1", "DNS failures by reason", ("reason",)),
    "g12_auth_failures_total": ("counter", "1", "Authentication failures by reason", ("reason",)),
}
FORBIDDEN_LABEL = re.compile(r"(\d{1,3}\.){3}\d{1,3}|:[0-9a-fA-F]{0,4}:|https?://|Error|Exception|\s")


class Metrics:
    def __init__(self, *, cardinality_budget: int = 50):
        self.budget = cardinality_budget
        self.values: dict[str, OrderedDict] = {n: OrderedDict() for n in CATALOG}
        self.overflowed: dict[str, int] = {n: 0 for n in CATALOG}
        self._lock = threading.Lock()

    def _key(self, name: str, labels: dict) -> tuple:
        kind, _, _, allowed = CATALOG[name]
        if len(labels) == len(allowed):
            fast = tuple(labels.get(a) for a in allowed)
            if fast in self.values[name]:
                return fast                        # already validated when first admitted
        if set(labels) != set(allowed):
            raise ValueError(f"{name}: labels must be exactly {allowed}")
        for v in labels.values():
            if not isinstance(v, str) or len(v) > 40 or FORBIDDEN_LABEL.search(v):
                raise ValueError(f"{name}: unbounded/forbidden label value {v!r}")
        key = tuple(labels[a] for a in allowed)
        table = self.values[name]
        if key not in table and len(table) >= self.budget:
            self.overflowed[name] += 1
            key = tuple("__overflow__" for _ in allowed)
        return key

    def inc(self, name: str, labels: dict | None = None, value: float = 1.0) -> None:
        with self._lock:
            k = self._key(name, labels or {})
            self.values[name][k] = self.values[name].get(k, 0.0) + value

    def set(self, name: str, labels: dict | None, value: float) -> None:
        with self._lock:
            self.values[name][self._key(name, labels or {})] = float(value)

    def observe(self, name: str, labels: dict | None, value: float) -> None:
        with self._lock:
            k = self._key(name, labels or {})
            h = self.values[name].setdefault(k, {"buckets": [0] * len(BUCKETS), "sum": 0.0, "count": 0})
            for i, b in enumerate(BUCKETS):
                if value <= b:
                    h["buckets"][i] += 1
            h["sum"] += value
            h["count"] += 1

    def expose(self) -> str:
        out = []
        with self._lock:
            for name, (kind, unit, help_, labels) in CATALOG.items():
                out.append(f"# HELP {name} {help_} [{unit}]")
                out.append(f"# TYPE {name} {kind}")
                for key, v in self.values[name].items():
                    lab = ",".join(f'{a}="{b}"' for a, b in zip(labels, key))
                    if kind == "histogram":
                        for b, c in zip(BUCKETS, v["buckets"]):
                            out.append(f'{name}_bucket{{{lab + "," if lab else ""}le="{b}"}} {c}')
                        out.append(f'{name}_bucket{{{lab + "," if lab else ""}le="+Inf"}} {v["count"]}')
                        out.append(f"{name}_sum{{{lab}}} {v['sum']}")
                        out.append(f"{name}_count{{{lab}}} {v['count']}")
                    else:
                        out.append(f"{name}{{{lab}}} {v}")
        return "\n".join(out) + "\n"


# --- G076 structured logs ----------------------------------------------------------------------------

EVENTS = {
    "G12-E001": ("info", "path established"),
    "G12-E002": ("warning", "strategy attempt failed"),
    "G12-E003": ("error", "peer partitioned"),
    "G12-E004": ("warning", "policy rejection"),
    "G12-E005": ("error", "authentication failure"),
    "G12-E006": ("warning", "dependency degraded"),
    "G12-E007": ("info", "configuration activated"),
    "G12-E008": ("critical", "kill switch engaged"),
    "G12-E009": ("warning", "relay budget soft limit"),
}


class EventLog:
    def __init__(self, sink=None, *, suppress_window: float = 60.0, max_field: int = 200, clock=time.time,
                 lineage: dict | None = None):
        self.sink = sink or (lambda line: None)
        self.window, self.max_field, self.clock = suppress_window, max_field, clock
        self.lineage = lineage or {}
        self.suppressed: OrderedDict = OrderedDict()
        self.max_suppression_keys = 4096
        self.lines: list[str] = []

    def emit(self, event_id: str, reason: str, **fields) -> dict | None:
        if event_id not in EVENTS:
            raise KeyError(event_id)
        reasons.check(reason)
        now = self.clock()
        key = (event_id, reason, fields.get("peer_token"))
        s = self.suppressed.get(key)
        if s and now - s["first"] <= self.window:
            s["count"] += 1
            s["last"] = now
            return None
        rec = {"ts": round(now, 3), "event_id": event_id, "severity": EVENTS[event_id][0], "msg": EVENTS[event_id][1],
               "reason": reason, "reason_class": reasons.reason_class(reason), **self.lineage}
        if s:
            rec["suppressed_repeats"] = s["count"]
            rec["first_seen"], rec["last_seen"] = s["first"], s["last"]
        for k, v in fields.items():
            if not isinstance(v, (str, int, float, bool)) and v is not None:
                v = type(v).__name__                       # never dump objects
            if isinstance(v, str):
                v = redact(v)[: self.max_field]
            rec[k] = v
        self.suppressed[key] = {"first": now, "last": now, "count": 0}
        self.suppressed.move_to_end(key)
        while len(self.suppressed) > self.max_suppression_keys:     # bounded (found by bench: grew per peer)
            self.suppressed.popitem(last=False)
        line = json.dumps(rec, sort_keys=True)
        self.lines.append(line)
        del self.lines[:-1000]
        self.sink(line)
        return rec


# --- G077 tracing ---------------------------------------------------------------------------------------

TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
SPAN_NAMES = ("request", "gather", "attempt", "auth", "relay_allocate", "validate", "migrate", "teardown")


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent: str | None
    name: str
    start: float
    end: float | None = None
    attrs: dict = field(default_factory=dict)
    links: list[str] = field(default_factory=list)


class Tracer:
    def __init__(self, *, sample_rate: float = 1.0, clock=time.monotonic):
        self.spans: list[Span] = []
        self.sample_rate, self.clock = sample_rate, clock

    def start(self, name: str, *, parent: Span | None = None, inbound: str | None = None, trusted: bool = False) -> Span:
        if name not in SPAN_NAMES:
            raise ValueError(name)
        links = []
        if parent is not None:
            tid, pid = parent.trace_id, parent.span_id
        else:
            tid, pid = _secrets.token_hex(16), None
            m = TP.match(inbound or "")
            if m and m.group(1) != "0" * 32:
                if trusted:
                    tid, pid = m.group(1), m.group(2)
                else:
                    links.append(inbound)                  # link, don't adopt, an untrusted id
        sp = Span(tid, _secrets.token_hex(8), pid, name, self.clock(), links=links)
        self.spans.append(sp)
        del self.spans[:-5000]
        return sp

    def end(self, sp: Span, **attrs) -> None:
        sp.end = self.clock()
        sp.attrs.update({k: (redact(v) if isinstance(v, str) else v) for k, v in attrs.items()})

    @staticmethod
    def header(sp: Span) -> str:
        return f"00-{sp.trace_id}-{sp.span_id}-01"


# --- G078 health / readiness ---------------------------------------------------------------------------------

class HealthServer:
    def __init__(self, readiness, metrics: Metrics | None = None, bind=("127.0.0.1", 0)):
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path == "/livez":
                    code, body = 200, {"status": "alive"}
                elif self.path == "/readyz":
                    ok, detail = outer.readiness()
                    code, body = (200 if ok else 503), {"status": "ready" if ok else "not_ready", "detail": detail}
                elif self.path == "/metrics" and outer.metrics is not None:
                    data = outer.metrics.expose().encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                else:
                    code, body = 404, {"status": "not_found"}
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.readiness, self.metrics = readiness, metrics
        self.httpd = http.server.ThreadingHTTPServer(bind, H)
        self.address = self.httpd.server_address
        self._t = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()


def readiness_from(dep_view: dict[str, str], *, required=("dns", "identity", "keys")) -> tuple[bool, dict]:
    missing = {d: s for d, s in dep_view.items() if d in required and s != "up"}
    return not missing, {"dependencies": dep_view, "blocking": missing}


# --- G080 explain view -------------------------------------------------------------------------------------

def explain(state: dict, attempts: list[dict], *, salt: bytes = b"gap12") -> dict:
    from .security import endpoint_token
    steps = []
    for a in attempts[-16:]:
        code = a.get("reason") or {"success": "OK", "failure": "NET_UNREACHABLE", "error": "DEFECT_EXCEPTION"}.get(a.get("outcome"), "UNSUPPORTED")
        steps.append({"strategy": a.get("strategy"), "outcome": a.get("outcome"), "reason": code,
                      "class": reasons.reason_class(code), "meaning": reasons.REASONS[code][1]})
    status = state.get("status")
    summary = {
        "healthy": f"using {state.get('strategy')} (last success {state.get('last_success')})",
        "backing_off": f"every strategy failed; next retry in {state.get('retry_in', 0):.1f}s (failures={state.get('failures')})",
        "partitioned": "every strategy failed and the retry window has elapsed; a new attempt is allowed",
        "stale": "last success is older than the freshness window; re-probe before trusting",
        "unknown": "no attempt has been made yet",
    }.get(status, status)
    return {"peer": endpoint_token(str(state.get("peer")), salt), "status": status, "summary": summary,
            "decision_trail": steps, "last_error_type": state.get("last_error")}


# --- G081/G082 generated dashboards and alerts ---------------------------------------------------------------------

def dashboard() -> dict:
    panels = []
    for i, (name, (kind, unit, help_, labels)) in enumerate(CATALOG.items()):
        expr = (f"sum by ({','.join(labels) or 'job'}) (rate({name}[5m]))" if kind == "counter" else
                f"histogram_quantile(0.95, sum by (le) (rate({name}_bucket[5m])))" if kind == "histogram" else
                f"max by ({','.join(labels) or 'job'}) ({name})")
        panels.append({"id": i + 1, "type": "timeseries", "title": help_, "unit": unit,
                       "targets": [{"expr": expr}], "gridPos": {"x": (i % 2) * 12, "y": (i // 2) * 8, "w": 12, "h": 8}})
    return {"title": "GAP-12 WAN resilience", "uid": "gap12-wan", "schemaVersion": 39, "panels": panels,
            "templating": {"list": []}, "tags": ["gap12", "generated"]}


SLO = {"establish_success": 0.995, "window_days": 30}


def alert_rules() -> list[dict]:
    err = 1 - SLO["establish_success"]
    burn = lambda long, short, factor, sev: {
        "alert": f"G12EstablishBurn{long}", "severity": sev,
        "expr": (f'(sum(rate(g12_attempts_total{{outcome!="ok"}}[{long}])) / sum(rate(g12_attempts_total[{long}])) > {factor}*{err}) and '
                 f'(sum(rate(g12_attempts_total{{outcome!="ok"}}[{short}])) / sum(rate(g12_attempts_total[{short}])) > {factor}*{err})'),
        "for": "2m"}
    return [
        burn("1h", "5m", 14.4, "page"),
        burn("6h", "30m", 6, "page"),
        burn("3d", "6h", 1, "ticket"),
        {"alert": "G12RetryStorm", "severity": "page", "for": "5m",
         "expr": "sum(rate(g12_retries_total[5m])) > 3 * sum(rate(g12_attempts_total[5m]))"},
        {"alert": "G12RelaySaturation", "severity": "page", "for": "10m",
         "expr": 'sum(rate(g12_attempts_total{strategy="relay"}[10m])) / sum(rate(g12_attempts_total[10m])) > 0.5'},
        {"alert": "G12DnsFailure", "severity": "page", "for": "5m", "expr": "sum(rate(g12_dns_failures_total[5m])) > 1"},
        {"alert": "G12TraversalRegression", "severity": "ticket", "for": "30m",
         "expr": 'sum(rate(g12_attempts_total{strategy="hole-punch",outcome="ok"}[30m])) / sum(rate(g12_attempts_total{strategy="hole-punch"}[30m])) < 0.5'},
        {"alert": "G12SecurityEvent", "severity": "page", "for": "0m", "expr": "sum(increase(g12_auth_failures_total[5m])) > 20"},
    ]


def classify_incident(rates: dict[str, float]) -> str:
    """The same decision the alert set encodes, evaluated on synthetic rates (used by tests)."""
    attempts = rates.get("attempts", 0.0) or 1e-9
    if rates.get("auth_failures", 0) > 20 / 300:
        return "security_event"
    if rates.get("dns_failures", 0) > 1:
        return "dns_failure"
    if rates.get("retries", 0) > 3 * attempts:
        return "retry_storm"
    if rates.get("relay_attempts", 0) / attempts > 0.5:
        return "relay_saturation"
    if rates.get("holepunch_attempts", 0) and rates.get("holepunch_ok", 0) / rates["holepunch_attempts"] < 0.5:
        return "traversal_regression"
    return "ordinary_load"


# --- G083 retention / G084 lineage -------------------------------------------------------------------------------

RETENTION = {
    "metrics": {"retention_days": 395, "resolution": "15s->5m after 30d", "contains_endpoints": False},
    "events": {"retention_days": 30, "sampling": "all errors; info sampled 10%", "redaction": "endpoint pseudonyms, secrets removed"},
    "traces": {"retention_days": 7, "sampling": "1% head + 100% of failed establishments", "redaction": "attributes redacted"},
    "security_audit": {"retention_days": 400, "sampling": "none (complete)", "tamper_evidence": "sha256 hash chain"},
    "support_bundles": {"retention_days": 14, "redaction": "redact() over every text member", "access": "incident responders"},
}


def lineage(*, release: str, artifact_digest: str, config_generation: int, config_digest: str, topology: str) -> dict:
    return {"release": release, "artifact": artifact_digest[:16], "config_gen": config_generation,
            "config_digest": config_digest[:16], "topology": topology}
