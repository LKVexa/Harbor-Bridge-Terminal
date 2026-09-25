"""Observability for INV-52 (C071-C080).

* ``StructuredLogger`` — JSON records with stable identifiers (node, tenant,
  workload, component, operation, release) redacted before retention, bounded
  retention, deterministic sampling that never drops security/policy events
* ``prometheus_text`` — metrics exposition with a fixed label set (no message
  ids or payload values as labels: bounded cardinality)
* ``trace`` helpers — W3C traceparent create/child
* ``classify`` — the alert taxonomy that separates ordinary load, overload,
  degradation, policy rejection, dependency failure, suspected attack and
  software defect from two metric snapshots (backs ``deploy/observability``)
* ``Telemetry`` — wires a ``PubSub`` observer into the logger with release
  lineage so every decision correlates with the build that made it
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import deque
from typing import Any, Mapping

from .runtime import TRACEPARENT
from .security import redact

COMPONENT = "INV-52"
ALWAYS_KEEP = ("policy.", "topic.state", "authn.", "authz.", "config.")
LOG_FIELDS = ("ts", "level", "node", "tenant", "workload", "component", "operation", "release", "event")


def new_traceparent() -> str:
    return f"00-{os.urandom(16).hex()}-{os.urandom(8).hex()}-01"


def child_traceparent(parent: str) -> str:
    if not isinstance(parent, str) or not TRACEPARENT.match(parent):
        return new_traceparent()
    _, trace_id, _, flags = parent.split("-")
    return f"00-{trace_id}-{os.urandom(8).hex()}-{flags}"


class StructuredLogger:
    def __init__(self, *, node: str, workload: str, release: str, sample_rate: float = 1.0,
                 retention: int = 10_000, sink: Any = None):
        if not 0 <= sample_rate <= 1:
            raise ValueError("sample_rate must be in [0, 1]")
        self.base = {"node": node, "workload": workload, "component": COMPONENT, "release": release}
        self.sample_rate = sample_rate
        self.records: deque[dict[str, Any]] = deque(maxlen=retention)
        self.sink = sink
        self.dropped_by_sampling = 0
        self._lock = threading.Lock()

    def _sampled(self, event: Mapping[str, Any]) -> bool:
        name = str(event.get("event", ""))
        if name.startswith(ALWAYS_KEEP) or event.get("outcome") not in (None, "success"):
            return True  # never sample away rejections, failures or security events
        if self.sample_rate >= 1:
            return True
        key = str(event.get("message_id") or event.get("decision_id") or name)
        bucket = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        return bucket < self.sample_rate  # deterministic per message id

    def log(self, event: Mapping[str, Any], *, level: str = "info", tenant: str | None = None,
            operation: str | None = None) -> dict[str, Any] | None:
        if not self._sampled(event):
            with self._lock:
                self.dropped_by_sampling += 1
            return None
        rec = {"ts": time.time(), "level": level, **self.base,
               "tenant": tenant or _tenant_of(event.get("topic")), "operation": operation or event.get("event"),
               **redact(dict(event))}
        rec.pop("message", None)  # never retain payloads in logs
        with self._lock:
            self.records.append(rec)
        if self.sink is not None:
            try:
                self.sink.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
            except Exception:  # noqa: BLE001 - export failure degrades, never breaks messaging
                pass
        return rec


def _tenant_of(topic: Any) -> str:
    if isinstance(topic, str) and "::" in topic:
        return topic.split("::", 1)[0]
    return "default"


class Telemetry:
    """Observer for ``PubSub(observer=...)`` that logs with release lineage."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def __call__(self, event: dict[str, Any]) -> None:
        level = "warning" if event.get("outcome") not in (None, "success", "duplicate_suppressed") else "info"
        self.logger.log(event, level=level)


def prometheus_text(metrics: Mapping[str, Any], *, node: str, release: str) -> str:
    lab = f'component="{COMPONENT}",node="{node}",release="{release}"'
    lines = []
    for k, v in sorted(metrics.items()):
        if isinstance(v, int) and not isinstance(v, bool):
            lines.append(f"inv52_{k}_total{{{lab}}} {v}" if k not in ("topics", "routes", "dead_letter_backlog")
                         else f"inv52_{k}{{{lab}}} {v}")
    for outcome, n in sorted(metrics.get("outcomes", {}).items()):
        lines.append(f'inv52_publish_outcome_total{{{lab},outcome="{outcome}"}} {n}')
    for reason, n in sorted(metrics.get("dead_letter_reasons", {}).items()):
        lines.append(f'inv52_dead_letter_reason_total{{{lab},reason="{reason}"}} {n}')
    lat = metrics.get("latency")
    if lat:
        run = 0
        for b, c in zip(lat["bounds_ns"], lat["counts"]):
            run += c
            lines.append(f'inv52_publish_latency_seconds_bucket{{{lab},le="{b / 1e9:g}"}} {run}')
        lines.append(f'inv52_publish_latency_seconds_bucket{{{lab},le="+Inf"}} {lat["count"]}')
        lines.append(f"inv52_publish_latency_seconds_sum{{{lab}}} {lat['sum_ns'] / 1e9:.9f}")
        lines.append(f"inv52_publish_latency_seconds_count{{{lab}}} {lat['count']}")
    return "\n".join(lines) + "\n"


# Alert taxonomy (C080).  Thresholds are PROPOSED defaults, owner approval pending.
THRESHOLDS = {"overload_shed_ratio": 0.05, "degraded_error_ratio": 0.01, "attack_denied_ratio": 0.2,
              "attack_min_denied": 20, "defect_invalid_ratio": 0.2, "dependency_sink_ratio": 0.2}


def classify(before: Mapping[str, Any], after: Mapping[str, Any], *, dependency_down: bool = False,
             thresholds: Mapping[str, float] = THRESHOLDS) -> dict[str, Any]:
    """Classify the interval between two ``PubSub.metrics()`` snapshots."""
    def d(k: str) -> int:
        return int(after.get(k, 0)) - int(before.get(k, 0))

    attempts = d("published") + d("denied") + d("invalid") + d("shed") + d("oversize")
    signals: list[str] = []
    if attempts <= 0:
        return {"class": "idle", "signals": [], "attempts": 0}
    ratio = lambda n: n / attempts  # noqa: E731
    if dependency_down or (d("published") and d("sink_errors") / max(1, d("published")) >= thresholds[
            "dependency_sink_ratio"]):
        signals.append("dependency_failure")
    if d("denied") >= thresholds["attack_min_denied"] and ratio(d("denied")) >= thresholds["attack_denied_ratio"]:
        signals.append("attack_suspected")
    elif d("denied"):
        signals.append("policy_rejection")
    if ratio(d("shed")) >= thresholds["overload_shed_ratio"]:
        signals.append("overload")
    if d("route_errors") and ratio(d("route_errors")) >= thresholds["defect_invalid_ratio"]:
        signals.append("software_defect")
    elif ratio(d("invalid") + d("oversize")) >= thresholds["defect_invalid_ratio"]:
        signals.append("client_defect")
    if not signals and ratio(d("route_errors") + d("sink_errors")) >= thresholds["degraded_error_ratio"]:
        signals.append("degradation")
    order = ["attack_suspected", "dependency_failure", "software_defect", "overload", "degradation",
             "client_defect", "policy_rejection"]
    top = next((s for s in order if s in signals), "normal_load")
    return {"class": top, "signals": signals, "attempts": attempts}


TELEMETRY_POLICY = {
    "schema": "PK_MSG_TELEMETRY_POLICY/1",
    "retention": {"logs_events_in_process": 10_000, "decisions_in_process": 10_000,
                  "exported_logs_days": 30, "exported_metrics_days": 395, "audit_chain_days": 400},
    "sampling": {"default_rate": 1.0, "never_sampled": list(ALWAYS_KEEP) + ["non-success outcomes"],
                 "method": "deterministic sha256(message_id) bucket"},
    "privacy": {"payload_in_logs": False, "payload_in_metrics": False, "redaction": "security.redact",
                "metric_labels": ["component", "node", "release", "outcome", "reason"],
                "high_cardinality_only_in": "decision records / explain view (bounded, access-controlled)"},
    "export": {"allowed": ["metrics", "decisions", "logs", "audit"], "cross_tenant": False},
    "status": "PROPOSED — requires owner/privacy approval",
}
