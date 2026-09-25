"""Observability for INV-53 (components 61-65, 67).

* :class:`Metrics` – counters, gauges and fixed-bucket histograms with a declared
  label allow-list and a hard series cap (cardinality safety), exported in the
  Prometheus text format.  Tenant labels are opt-in and bounded.
* :class:`StructuredLogger` – one JSON object per line; any field whose name looks
  like payload, secret, key, token or lease material is replaced by a length/hash
  marker before it leaves the process (redaction by default).
* W3C ``traceparent`` parsing/creation and propagation through message headers.
* :func:`decision_event` – every refusal/dead-letter carries a machine-readable
  reason code so operators can see *why* (decision-reason model).
* Release lineage: every exported sample set carries ``inv53_build_info`` with
  version, config digest and build id.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sys
import time
from threading import RLock
from typing import Any, Callable, Mapping, TextIO

from . import __version__

DEFAULT_BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
ALLOWED_LABELS = frozenset({"queue", "tenant", "op", "code", "reason", "state"})
REDACT = re.compile(r"(payload|body|secret|key|token|lease|mac|password|credential|authorization)", re.I)
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class CardinalityError(RuntimeError):
    pass


class Metrics:
    def __init__(self, *, max_series: int = 2_000, build: Mapping[str, str] | None = None) -> None:
        self.max_series = max_series
        self._c: dict[tuple, float] = {}
        self._g: dict[tuple, float] = {}
        self._h: dict[tuple, list] = {}
        self._help: dict[str, str] = {}
        self._lock = RLock()
        self.dropped = 0
        self.build = {"version": __version__, **(build or {})}

    def _key(self, name: str, labels: Mapping[str, str]) -> tuple:
        bad = set(labels) - ALLOWED_LABELS
        if bad:
            raise CardinalityError(f"label(s) {sorted(bad)} are not on the allow-list")
        return (name, tuple(sorted((k, str(v)[:64]) for k, v in labels.items())))

    def _admit(self, store: dict, key: tuple) -> bool:
        if key in store:
            return True
        if len(self._c) + len(self._g) + len(self._h) >= self.max_series:
            self.dropped += 1          # never raise into the data path; count the drop instead
            return False
        return True

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            if self._admit(self._c, k):
                self._c[k] = self._c.get(k, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            if self._admit(self._g, k):
                self._g[k] = float(value)

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            if not self._admit(self._h, k):
                return
            h = self._h.setdefault(k, [[0] * len(DEFAULT_BUCKETS), 0, 0.0])
            for i, b in enumerate(DEFAULT_BUCKETS):
                if value <= b:
                    h[0][i] += 1
            h[1] += 1
            h[2] += value

    def value(self, name: str, **labels: str) -> float:
        k = self._key(name, labels)
        return self._c.get(k, self._g.get(k, 0.0))

    @staticmethod
    def _fmt(labels: tuple, extra: tuple = ()) -> str:
        items = list(labels) + list(extra)
        if not items:
            return ""
        esc = lambda v: v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')  # noqa: E731
        return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in items) + "}"

    def prometheus(self, *, config_digest: str = "unknown") -> str:
        with self._lock:
            out = ["# TYPE inv53_build_info gauge",
                   "inv53_build_info" + self._fmt(tuple(sorted({**self.build, "config_digest": config_digest}.items()))) + " 1"]
            for store, typ in ((self._c, "counter"), (self._g, "gauge")):
                for name in sorted({k[0] for k in store}):
                    out.append(f"# TYPE {name} {typ}")
                    for (n, lab), v in sorted(store.items()):
                        if n == name:
                            out.append(f"{name}{self._fmt(lab)} {v:g}")
            for name in sorted({k[0] for k in self._h}):
                out.append(f"# TYPE {name} histogram")
                for (n, lab), (buckets, count, total) in sorted(self._h.items()):
                    if n != name:
                        continue
                    for b, c in zip(DEFAULT_BUCKETS, buckets):
                        out.append(f"{name}_bucket{self._fmt(lab, (('le', f'{b:g}'),))} {c}")
                    out.append(f"{name}_bucket{self._fmt(lab, (('le', '+Inf'),))} {count}")
                    out.append(f"{name}_count{self._fmt(lab)} {count}")
                    out.append(f"{name}_sum{self._fmt(lab)} {total:g}")
            out.append("# TYPE inv53_metrics_dropped_series counter")
            out.append(f"inv53_metrics_dropped_series {self.dropped}")
            return "\n".join(out) + "\n"


def redact(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "<depth-limit>"
    if isinstance(value, Mapping):
        out = {}
        for k, v in value.items():
            if REDACT.search(str(k)):
                blob = json.dumps(v, sort_keys=True, default=str).encode()
                out[k] = f"<redacted len={len(blob)} sha256={hashlib.sha256(blob).hexdigest()[:12]}>"
            else:
                out[k] = redact(v, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(v, depth=depth + 1) for v in value[:50]]
    if isinstance(value, str) and len(value) > 512:
        return value[:512] + f"...<truncated {len(value) - 512}>"
    return value


class StructuredLogger:
    def __init__(self, stream: TextIO | None = None, *, component: str = "INV-53",
                 clock: Callable[[], float] = time.time, sample: Mapping[str, float] | None = None) -> None:
        self.stream = stream or sys.stderr
        self.component = component
        self.clock = clock
        self.sample = dict(sample or {})         # event -> keep ratio (1.0 default)
        self._lock = RLock()

    def log(self, level: str, event: str, *, trace: Mapping[str, str] | None = None, **fields: Any) -> None:
        ratio = self.sample.get(event, 1.0)
        if ratio < 1.0 and (int.from_bytes(secrets.token_bytes(2), "big") / 65535.0) > ratio:
            return
        rec = {"ts": self.clock(), "level": level, "component": self.component, "event": event,
               **({"trace_id": trace["trace_id"], "span_id": trace["span_id"]} if trace else {}),
               "fields": redact(fields)}
        with self._lock:
            self.stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")


def new_trace() -> dict[str, str]:
    return {"trace_id": secrets.token_hex(16), "span_id": secrets.token_hex(8), "flags": "01"}


def parse_traceparent(header: str | None) -> dict[str, str] | None:
    if not isinstance(header, str):
        return None
    m = _TRACEPARENT.match(header.strip())
    if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
        return None
    return {"trace_id": m.group(1), "span_id": m.group(2), "flags": m.group(3)}


def child_span(parent: Mapping[str, str] | None) -> dict[str, str]:
    if not parent:
        return new_trace()
    return {"trace_id": parent["trace_id"], "span_id": secrets.token_hex(8), "flags": parent.get("flags", "01")}


def traceparent(ctx: Mapping[str, str]) -> str:
    return f"00-{ctx['trace_id']}-{ctx['span_id']}-{ctx.get('flags', '01')}"


def decision_event(action: str, code: str, reason: str, **context: Any) -> dict[str, Any]:
    return {"schema": "inv53.decision/1", "action": action, "code": code, "reason": reason,
            "context": redact(context)}


def build_id() -> str:
    return os.environ.get("INV53_BUILD_ID", "unset")
