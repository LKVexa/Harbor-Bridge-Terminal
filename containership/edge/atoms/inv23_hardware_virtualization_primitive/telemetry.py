"""Structured metrics, logs and traces for INV-23 (MC-07).

Vendor-neutral: a ``Telemetry`` facade forwards to a ``Sink``.  ``NoopSink`` is the
default; ``MemorySink`` backs tests and diagnostics; ``OTelSink`` adapts to
OpenTelemetry when that optional package is installed.  Every sink call is isolated:
an exception inside telemetry is swallowed and counted, never altering a safety
decision.  Label keys and values are validated against a bounded vocabulary so
holder strings, hostnames, claim tokens and other unbounded values cannot become
metric labels.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from .backends.base import REASONS, STATES

SEMCONV_VERSION = "inv23.telemetry/1"

METRICS = {
    # name: (kind, allowed label keys)
    "inv23_virt_primitive": ("gauge", ("state", "backend", "platform")),
    "inv23_nesting_depth": ("gauge", ("backend",)),
    "inv23_claim_conflicts_total": ("counter", ("provider",)),
    "inv23_probe_failures_total": ("counter", ("reason", "backend")),
    "inv23_probe_latency_seconds": ("histogram", ("backend",)),
    "inv23_claim_acquire_seconds": ("histogram", ("provider",)),
    "inv23_claim_renew_failures_total": ("counter", ("provider",)),
    "inv23_stale_owner_recoveries_total": ("counter", ("provider",)),
    "inv23_fencing_rejections_total": ("counter", ("provider",)),
    "inv23_unsupported_platform_total": ("counter", ("platform", "architecture")),
    "inv23_telemetry_errors_total": ("counter", ()),
}

_BOUNDED_VALUES = {
    "state": set(STATES) | {"claimed"},
    "reason": set(REASONS),
    "backend": {"linux-kvm", "windows-whpx", "macos-hvf", "static", "none"},
    "platform": {"linux", "windows", "darwin", "other"},
    "architecture": {"x86_64", "amd64", "arm64", "aarch64", "i686", "i386", "other"},
    "provider": {"memory", "posix-flock", "windows-lockfile"},
}
MAX_SERIES = 512  # documented cardinality ceiling across all metrics

EVENTS = {
    "INV23-E001": ("probe.success", logging.INFO),
    "INV23-E002": ("probe.failure", logging.WARNING),
    "INV23-E003": ("claim.acquired", logging.INFO),
    "INV23-E004": ("claim.conflict", logging.WARNING),
    "INV23-E005": ("claim.released", logging.INFO),
    "INV23-E006": ("claim.release_rejected", logging.WARNING),
    "INV23-E007": ("claim.recovered_stale_owner", logging.WARNING),
    "INV23-E008": ("claim.fencing_rejected", logging.ERROR),
    "INV23-E009": ("claim.lease_renew_failed", logging.ERROR),
}
_SECRET_KEYS = {"token", "owner_token", "secret", "fencing_secret", "token_hash", "token_sha256"}


class LabelError(ValueError):
    pass


def check_labels(metric: str, labels: Mapping[str, str]) -> Tuple[Tuple[str, str], ...]:
    if metric not in METRICS:
        raise LabelError(f"unknown metric {metric!r}")
    allowed = METRICS[metric][1]
    for k, v in labels.items():
        if k not in allowed:
            raise LabelError(f"label {k!r} not allowed on {metric}")
        vocab = _BOUNDED_VALUES.get(k)
        if vocab is not None and v not in vocab:
            raise LabelError(f"label {k}={v!r} outside bounded vocabulary")
    return tuple(sorted(labels.items()))


def redact(fields: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in fields.items():
        if k in _SECRET_KEYS:
            out[k] = "[REDACTED]"
        elif isinstance(v, Mapping):
            out[k] = redact(v)
        else:
            out[k] = v
    return out


class Sink:
    def metric(self, name: str, kind: str, value: float, labels: Tuple[Tuple[str, str], ...]) -> None: ...
    def event(self, record: Dict[str, Any]) -> None: ...
    def span(self, name: str, attrs: Dict[str, Any], duration_ns: int, error: Optional[str]) -> None: ...


class NoopSink(Sink):
    pass


class MemorySink(Sink):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: Dict[Tuple[str, Tuple], float] = {}
        self.gauges: Dict[Tuple[str, Tuple], float] = {}
        self.histograms: Dict[Tuple[str, Tuple], List[float]] = {}
        self.events: List[Dict[str, Any]] = []
        self.spans: List[Dict[str, Any]] = []

    def metric(self, name, kind, value, labels):
        key = (name, labels)
        with self._lock:
            if kind == "counter":
                self.counters[key] = self.counters.get(key, 0) + value
            elif kind == "gauge":
                self.gauges[key] = value
            else:
                self.histograms.setdefault(key, []).append(value)

    def event(self, record):
        with self._lock:
            self.events.append(record)

    def span(self, name, attrs, duration_ns, error):
        with self._lock:
            self.spans.append({"name": name, "attrs": attrs, "duration_ns": duration_ns, "error": error})

    def series_count(self) -> int:
        return len(self.counters) + len(self.gauges) + len(self.histograms)


class OTelSink(Sink):  # pragma: no cover - optional dependency
    """Adapter to opentelemetry-api when installed (``pip install .[otel]``)."""

    def __init__(self) -> None:
        from opentelemetry import metrics, trace

        self._meter = metrics.get_meter("inv23")
        self._tracer = trace.get_tracer("inv23")
        self._inst: Dict[str, Any] = {}

    def metric(self, name, kind, value, labels):
        attrs = dict(labels)
        if name not in self._inst:
            if kind == "counter":
                self._inst[name] = self._meter.create_counter(name)
            elif kind == "histogram":
                self._inst[name] = self._meter.create_histogram(name)
            else:
                self._inst[name] = self._meter.create_gauge(name)
        inst = self._inst[name]
        (inst.add if kind == "counter" else inst.record if kind == "histogram" else inst.set)(value, attrs)

    def event(self, record):
        logging.getLogger("inv23").log(record.get("level", logging.INFO), record.get("event"), extra={"inv23": record})

    def span(self, name, attrs, duration_ns, error):
        with self._tracer.start_as_current_span(name, attributes=attrs) as sp:
            if error:
                sp.set_attribute("error.type", error)


class Telemetry:
    def __init__(self, sink: Optional[Sink] = None, *, component_version: str = "") -> None:
        self.sink = sink or NoopSink()
        self.component_version = component_version
        self._lock = threading.Lock()
        self.errors = 0
        self.last_success: Optional[float] = None
        self.last_failure_reason: Optional[str] = None

    def _safe(self, fn, *a) -> None:
        try:
            fn(*a)
        except Exception:  # noqa: BLE001 - isolation is the point
            with self._lock:
                self.errors += 1

    def count(self, metric: str, value: float = 1, **labels: str) -> None:
        lab = check_labels(metric, labels)
        self._safe(self.sink.metric, metric, METRICS[metric][0], value, lab)

    def gauge(self, metric: str, value: float, **labels: str) -> None:
        lab = check_labels(metric, labels)
        self._safe(self.sink.metric, metric, "gauge", value, lab)

    def observe(self, metric: str, value: float, **labels: str) -> None:
        lab = check_labels(metric, labels)
        self._safe(self.sink.metric, metric, "histogram", value, lab)

    def event(self, event_id: str, **fields: Any) -> None:
        name, level = EVENTS[event_id]
        rec = {
            "event_id": event_id,
            "event": name,
            "level": level,
            "ts": time.time(),
            "component_version": self.component_version,
            "semconv": SEMCONV_VERSION,
        }
        rec.update(redact(fields))
        self._safe(self.sink.event, rec)

    @contextmanager
    def span(self, name: str, **attrs: Any) -> Iterator[Dict[str, Any]]:
        t0 = time.monotonic_ns()
        bag = dict(redact(attrs))
        err = None
        try:
            yield bag
        except BaseException as exc:
            err = type(exc).__name__
            raise
        finally:
            self._safe(self.sink.span, name, redact(bag), time.monotonic_ns() - t0, err)


def label_platform(p: str) -> str:
    return p if p in _BOUNDED_VALUES["platform"] else "other"


def label_arch(a: str) -> str:
    return a if a in _BOUNDED_VALUES["architecture"] else "other"
