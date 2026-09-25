"""Operator-facing observability for INV-17.

Controls: C071 (health/readiness/version/capability surface), C072 (metrics exporter,
Prometheus text exposition), C073 (structured logging), C074 (W3C trace-context
propagation), C075 (cardinality/privacy guard), C076-C077 (decision explain view),
C078 (release lineage on every signal), C079 (sampling/retention policy hooks).
Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import secrets
import sys
import time
from dataclasses import asdict, dataclass
from typing import IO, Any, Mapping

from .stream import PROTOCOL_VERSIONS

VERSION = "4.3.0"

# ------------------------------------------------------------------ lineage (C078)
@dataclass(frozen=True)
class Lineage:
    component: str = "INV-17"
    version: str = VERSION
    source_revision: str = os.environ.get("INV17_SOURCE_REVISION", "unrecorded")
    build_id: str = os.environ.get("INV17_BUILD_ID", "local")
    config_digest: str = "unset"
    instance: str = os.environ.get("INV17_INSTANCE", "local-0")
    site: str = os.environ.get("INV17_SITE", "unset")

    def labels(self) -> dict[str, str]:
        return {"component": self.component, "version": self.version, "build": self.build_id,
                "revision": self.source_revision, "instance": self.instance}


# ------------------------------------------------------------------ privacy (C075)
ALLOWED_LABELS = frozenset({"state", "end", "reason", "tenant_hash", "workload_hash", "code", "status", "kind"})
MAX_SERIES = 10000


def pseudonymise(value: str, salt: str = os.environ.get("INV17_TELEMETRY_SALT", "inv17")) -> str:
    """Stable, non-reversible tenant/workload identifier for telemetry (C075)."""
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:12]


_SECRETish = re.compile(r"(token|secret|password|authorization|key)", re.I)


def redact(fields: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in fields.items():
        if _SECRETish.search(k):
            out[k] = "[REDACTED]"
        elif k in ("tenant", "workload"):
            out[f"{k}_hash"] = pseudonymise(str(v))
        elif k in ("payload", "element", "value"):
            out[k] = f"[{type(v).__name__} omitted]"
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------ metrics (C072)
def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class MetricsExporter:
    """Renders registry state as Prometheus text exposition (format 0.0.4)."""

    def __init__(self, registry, lineage: Lineage | None = None) -> None:
        self.registry = registry
        self.lineage = lineage or Lineage()

    def samples(self) -> list[tuple[str, dict[str, str], float]]:
        out: list[tuple[str, dict[str, str], float]] = []
        by_state: dict[str, int] = {}
        agg = {"credit_stalls": 0, "transferred": 0, "reads": 0, "dropped_items": 0, "buffered": 0,
               "duplicate_writes": 0}
        drops = {"reader": 0, "writer": 0}
        for s in self.registry.streams():
            st = s.stats()
            by_state[st.state] = by_state.get(st.state, 0) + 1
            for k in agg:
                agg[k] += getattr(st, k)
            drops["reader"] += int(st.reader_dropped)
            drops["writer"] += int(st.writer_dropped)
        for state, n in sorted(by_state.items()):
            out.append(("inv17_streams_open", {"state": state}, n))
        out.append(("inv17_credit_stalls_total", {}, agg["credit_stalls"]))
        out.append(("inv17_elements_transferred_total", {}, agg["transferred"]))
        out.append(("inv17_elements_read_total", {}, agg["reads"]))
        out.append(("inv17_elements_dropped_total", {}, agg["dropped_items"]))
        out.append(("inv17_elements_buffered", {}, agg["buffered"]))
        out.append(("inv17_duplicate_writes_total", {}, agg["duplicate_writes"]))
        for end, n in drops.items():
            out.append(("inv17_dropped_end_streams", {"end": end}, n))
        out.append(("inv17_load_shed_total", {}, self.registry.shed_count))
        out.append(("inv17_breaker_open", {}, 1 if self.registry.breaker.state == "open" else 0))
        out.append(("inv17_disabled", {}, 1 if self.registry.disabled else 0))
        kinds: dict[str, int] = {}
        for ev in self.registry.audit.events:
            kinds[ev.kind] = kinds.get(ev.kind, 0) + 1
        for kind, n in sorted(kinds.items()):  # bounded: AuditLedger.KINDS is a closed set
            out.append(("inv17_audit_events_total", {"kind": kind}, n))
        health = self.registry.health().status
        for st in ("healthy", "degraded", "unhealthy", "disabled"):
            out.append(("inv17_health_status", {"status": st}, 1 if st == health else 0))
        out.append(("inv17_build_info", self.lineage.labels(), 1))
        if len(out) > MAX_SERIES:
            raise RuntimeError("series cap exceeded")
        for name, labels, _ in out:
            if name != "inv17_build_info" and set(labels) - ALLOWED_LABELS:
                raise ValueError(f"label not allowed on {name}: {set(labels) - ALLOWED_LABELS}")
        return out

    HELP = {
        "inv17_streams_open": ("gauge", "Open streams by lifecycle state"),
        "inv17_credit_stalls_total": ("counter", "Writes refused for lack of credit"),
        "inv17_elements_transferred_total": ("counter", "Elements accepted by writers"),
        "inv17_elements_read_total": ("counter", "Elements delivered to readers"),
        "inv17_elements_dropped_total": ("counter", "Buffered elements reclaimed on reader drop"),
        "inv17_elements_buffered": ("gauge", "Elements currently in flight"),
        "inv17_duplicate_writes_total": ("counter", "Idempotent retries acknowledged without enqueue"),
        "inv17_dropped_end_streams": ("gauge", "Streams with a dropped end, by end"),
        "inv17_load_shed_total": ("counter", "Writes shed by quota or overload"),
        "inv17_breaker_open": ("gauge", "1 when the admission circuit is open"),
        "inv17_disabled": ("gauge", "1 when emergency disable is active"),
        "inv17_audit_events_total": ("counter", "Security audit events by kind"),
        "inv17_health_status": ("gauge", "1 for the current health state"),
        "inv17_build_info": ("gauge", "Release lineage"),
    }

    def render(self) -> str:
        lines: list[str] = []
        seen: set[str] = set()
        for name, labels, value in self.samples():
            if name not in seen:
                kind, text = self.HELP[name]
                lines += [f"# HELP {name} {text}", f"# TYPE {name} {kind}"]
                seen.add(name)
            lab = ",".join(f'{k}="{_esc(str(v))}"' for k, v in sorted(labels.items()))
            lines.append(f"{name}{{{lab}}} {value}" if lab else f"{name} {value}")
        return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ tracing (C074)
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool = True

    @classmethod
    def new(cls, sampled: bool = True) -> TraceContext:
        return cls(secrets.token_hex(16), secrets.token_hex(8), sampled)

    @classmethod
    def parse(cls, header: str | None) -> TraceContext | None:
        """Parse a W3C ``traceparent``; malformed or all-zero ids are rejected (None)."""
        if not header or not isinstance(header, str):
            return None
        m = _TP.match(header.strip().lower())
        if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
            return None
        return cls(m.group(1), m.group(2), bool(int(m.group(3), 16) & 1))

    def child(self) -> TraceContext:
        return TraceContext(self.trace_id, secrets.token_hex(8), self.sampled)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


# ------------------------------------------------------------------ logging (C073/C079)
LOG_FIELDS = ("ts", "level", "event", "component", "version", "instance", "stream_id", "operation",
              "trace_id", "span_id", "code")


class StructuredLogger:
    """JSON-lines logger with stable fields, redaction and head-based sampling."""

    LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}

    def __init__(self, stream: IO[str] | None = None, *, lineage: Lineage | None = None, level: str = "info",
                 sample_rate: float = 1.0, rng: random.Random | None = None) -> None:
        self.stream = stream or sys.stderr
        self.lineage = lineage or Lineage()
        self.level = self.LEVELS[level]
        self.sample_rate = sample_rate
        self._rng = rng or random.Random()  # noqa: S311 - log sampling, not security
        self.emitted = 0
        self.sampled_out = 0

    def log(self, level: str, event: str, *, trace: TraceContext | None = None, **fields: Any) -> dict | None:
        if self.LEVELS[level] < self.level:
            return None
        # errors and security events are never sampled out (telemetry policy)
        if level in ("debug", "info") and self._rng.random() >= self.sample_rate:
            self.sampled_out += 1
            return None
        rec = {"ts": round(time.time(), 6), "level": level, "event": event, "component": self.lineage.component,
               "version": self.lineage.version, "instance": self.lineage.instance,
               "trace_id": trace.trace_id if trace else None, "span_id": trace.span_id if trace else None}
        rec.update(redact(fields))
        self.stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        self.emitted += 1
        return rec


# ------------------------------------------------------------------ explain (C076/C077)
def explain(registry, stream_id: str | None = None) -> dict[str, Any]:
    """Why did INV-17 decide what it decided? Ties decisions to config/policy/topology."""
    decisions = [d for d in registry.decisions if stream_id is None or d.get("stream") == stream_id]
    return {
        "component": "INV-17",
        "policy": {"disabled": registry.disabled,
                   "frozen_scopes": sorted(f"{a}:{b}" for a, b in registry.frozen_scopes),
                   "breaker": registry.breaker.state, "global_buffer_budget": registry.global_buffer_budget,
                   "default_quota": asdict(registry.default_quota)},
        "topology": {"scope": "instance-local", "streams": len(registry.streams())},
        "decisions": [redact(d) for d in decisions[-50:]],
    }


# ------------------------------------------------------------------ status (C071)
CAPABILITIES = ("typed-elements", "credit-backpressure", "explicit-eos", "drop-detection", "bounded-buffer",
                "idempotent-write", "bounded-wait", "cancellation", "capability-auth", "quarantine")


def status(registry, lineage: Lineage | None = None) -> dict[str, Any]:
    lineage = lineage or Lineage()
    h = registry.health()
    return {
        "component": "INV-17", "version": lineage.version, "lineage": asdict(lineage),
        "live": True, "ready": h.status in ("healthy", "degraded"), "health": h.status, "reasons": h.reasons[:20],
        "streams": h.streams, "interfaces": {k: f"{k}/{v}" for k, v in PROTOCOL_VERSIONS.items()},
        "capabilities": list(CAPABILITIES),
    }


def serve_status(registry, host: str = "127.0.0.1", port: int = 0):  # pragma: no cover - thin I/O shell
    """Optional loopback HTTP endpoint: /healthz /readyz /version /metrics /explain."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    exporter = MetricsExporter(registry)

    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            st = status(registry)
            routes = {"/healthz": (200 if st["live"] else 503, st), "/readyz": (200 if st["ready"] else 503, st),
                      "/version": (200, {"version": st["version"], "interfaces": st["interfaces"]}),
                      "/explain": (200, explain(registry))}
            if self.path == "/metrics":
                body, code, ctype = exporter.render().encode(), 200, "text/plain; version=0.0.4"
            elif self.path in routes:
                code, doc = routes[self.path]
                body, ctype = json.dumps(doc).encode(), "application/json"
            else:
                body, code, ctype = b"{}", 404, "application/json"
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer((host, port), H)
