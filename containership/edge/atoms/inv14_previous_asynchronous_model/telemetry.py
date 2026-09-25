"""Telemetry export for PK_POLL_METRICS/1 (component P1-09; C071-C080).

Two exporters over the same bounded aggregates:
  * ``prometheus_text`` -- Prometheus text exposition format 0.0.4.
  * ``otlp_json``       -- an OTLP/JSON ``ExportMetricsServiceRequest`` body.
Label policy (TEL-1): the ONLY labels are ``component``, ``tenant`` (hashed to a
bounded bucket set when more than MAX_TENANT_SERIES distinct tenants are seen),
``outcome`` and ``reason`` from closed vocabularies.  Poll owners, pollable names,
trace ids and correlation ids MUST NOT appear as labels (TEL-2).  Sampling (TEL-3)
applies to per-poll latency observations only; counters are never sampled.
Remote push (network export) is deliberately not implemented here: shipping the
body is a collector/host concern and is BLOCKED in the checklist until a real
collector endpoint exists.
"""
from __future__ import annotations

import hashlib
import random
import re
import threading

OUTCOMES = ("ready", "timeout", "cancelled", "refused")
REASONS = ("none", "foreign_owner", "identity", "policy", "admission", "invalid", "quota")
LATENCY_BUCKETS_MS = (1, 5, 10, 50, 100, 500, 1000, 5000, 60000)
MAX_TENANT_SERIES = 64
_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")


class Telemetry:
    def __init__(self, *, component: str = "INV-14", sample_rate: float = 1.0, seed: int | None = None):
        if not (0.0 <= float(sample_rate) <= 1.0):
            raise ValueError("sample_rate must be in [0, 1]")
        self.component, self.sample_rate = component, float(sample_rate)
        self._rng = random.Random(seed)
        self._lock = threading.Lock()
        self._counts: dict = {}
        self._hist: dict = {}
        self._tenants: set = set()
        self.samples_dropped = 0

    def _tenant_label(self, tenant: str) -> str:
        if tenant in self._tenants or len(self._tenants) < MAX_TENANT_SERIES:
            self._tenants.add(tenant)
            return tenant
        return "bucket-" + str(int(hashlib.sha256(tenant.encode()).hexdigest(), 16) % 16)

    def record(self, tenant: str, outcome: str, reason: str = "none", latency_ms: float | None = None) -> None:
        outcome = outcome if outcome in OUTCOMES else "refused"
        reason = reason if reason in REASONS else "invalid"
        with self._lock:
            t = self._tenant_label(str(tenant)[:64])
            k = (t, outcome, reason)
            self._counts[k] = self._counts.get(k, 0) + 1
            if latency_ms is not None:
                if self._rng.random() >= self.sample_rate:
                    self.samples_dropped += 1
                    return
                h = self._hist.setdefault(t, [0] * (len(LATENCY_BUCKETS_MS) + 1) + [0.0, 0])
                idx = next((i for i, b in enumerate(LATENCY_BUCKETS_MS) if latency_ms <= b), len(LATENCY_BUCKETS_MS))
                h[idx] += 1
                h[-2] += float(latency_ms)
                h[-1] += 1

    def series_count(self) -> int:
        with self._lock:
            return len(self._counts) + len(self._hist)

    def prometheus_text(self) -> str:
        out = ["# HELP inv14_polls_total Legacy INV-14 polls by outcome.", "# TYPE inv14_polls_total counter"]
        with self._lock:
            for (t, o, r), v in sorted(self._counts.items()):
                out.append(f'inv14_polls_total{{component="{self.component}",tenant="{_esc(t)}",outcome="{o}",reason="{r}"}} {v}')
            out += ["# HELP inv14_poll_latency_ms Poll wait latency (sampled).", "# TYPE inv14_poll_latency_ms histogram"]
            for t, h in sorted(self._hist.items()):
                cum = 0
                for i, b in enumerate(LATENCY_BUCKETS_MS):
                    cum += h[i]
                    out.append(f'inv14_poll_latency_ms_bucket{{component="{self.component}",tenant="{_esc(t)}",le="{b}"}} {cum}')
                cum += h[len(LATENCY_BUCKETS_MS)]
                out.append(f'inv14_poll_latency_ms_bucket{{component="{self.component}",tenant="{_esc(t)}",le="+Inf"}} {cum}')
                out.append(f'inv14_poll_latency_ms_sum{{component="{self.component}",tenant="{_esc(t)}"}} {h[-2]:.3f}')
                out.append(f'inv14_poll_latency_ms_count{{component="{self.component}",tenant="{_esc(t)}"}} {h[-1]}')
        return "\n".join(out) + "\n"

    def otlp_json(self, *, time_unix_nano: int) -> dict:
        with self._lock:
            points = [{"attributes": [_attr("component", self.component), _attr("tenant", t),
                                      _attr("outcome", o), _attr("reason", r)],
                       "asInt": str(v), "timeUnixNano": str(time_unix_nano)}
                      for (t, o, r), v in sorted(self._counts.items())]
        return {"resourceMetrics": [{
            "resource": {"attributes": [_attr("service.name", "inv14-legacy-poll"), _attr("service.version", "4.3.0")]},
            "scopeMetrics": [{"scope": {"name": "inv14.telemetry", "version": "4.3.0"},
                              "metrics": [{"name": "inv14.polls", "unit": "1",
                                           "sum": {"aggregationTemporality": 2, "isMonotonic": True,
                                                   "dataPoints": points}}]}]}]}


def _attr(k, v):
    return {"key": k, "value": {"stringValue": str(v)}}


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def parse_prometheus(text: str) -> list:
    """Minimal strict parser used by the contract tests to prove the exposition is well-formed."""
    samples = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\{(.*)\} (-?[0-9.eE+]+|\+Inf)$', line)
        if not m:
            raise ValueError("bad sample line: " + line[:80])
        labels = dict(re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"', m.group(2)))
        samples.append((m.group(1), labels, float(m.group(3))))
    return samples
