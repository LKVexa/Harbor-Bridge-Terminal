"""Runtime metrics with bounded cardinality and Prometheus text exposition (MC-040, MC-043)."""
from __future__ import annotations

import bisect
import math
import re
import threading
from typing import Final

from ..errors import Inv24Error

MAX_SERIES_PER_METRIC: Final[int] = 1000
OVERFLOW_LABEL: Final[str] = "__overflow__"
_NAME = re.compile(r"[a-z_][a-z0-9_]*")
BOOT_BUCKETS_S: Final[tuple[float, ...]] = (0.01, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.25, 0.5, 1.0)


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class _Metric:
    kind = "untyped"

    def __init__(self, name: str, help_: str, labels: tuple[str, ...]) -> None:
        if not _NAME.fullmatch(name) or not all(_NAME.fullmatch(l) for l in labels):
            raise Inv24Error("CONFIG_REJECTED", f"invalid metric/label name {name}")
        self.name, self.help, self.labels = name, help_, labels
        self._lock = threading.Lock()
        self._series: dict[tuple[str, ...], object] = {}
        self.overflowed = 0

    def _key(self, labels: dict[str, str]) -> tuple[str, ...]:
        if set(labels) != set(self.labels):
            raise Inv24Error("CONFIG_REJECTED", f"{self.name}: labels must be exactly {self.labels}")
        key = tuple(str(labels[l])[:64] for l in self.labels)
        if key not in self._series and len(self._series) >= MAX_SERIES_PER_METRIC:
            self.overflowed += 1
            key = tuple(OVERFLOW_LABEL for _ in self.labels)
        return key

    def _fmt_labels(self, key, extra: str = "") -> str:
        parts = [f'{l}="{_esc(v)}"' for l, v in zip(self.labels, key)]
        if extra:
            parts.append(extra)
        return "{" + ",".join(parts) + "}" if parts else ""


class Counter(_Metric):
    kind = "counter"

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        if amount < 0 or math.isnan(amount):
            raise Inv24Error("CONFIG_REJECTED", "counters only increase")
        with self._lock:
            k = self._key(labels)
            self._series[k] = self._series.get(k, 0.0) + amount

    def value(self, **labels: str) -> float:
        return self._series.get(tuple(str(labels[l]) for l in self.labels), 0.0)

    def expose(self) -> list[str]:
        return [f"{self.name}_total{self._fmt_labels(k)} {v}" for k, v in sorted(self._series.items())]


class Gauge(_Metric):
    kind = "gauge"

    def set(self, value: float, **labels: str) -> None:
        with self._lock:
            self._series[self._key(labels)] = float(value)

    def add(self, delta: float, **labels: str) -> None:
        with self._lock:
            k = self._key(labels)
            self._series[k] = self._series.get(k, 0.0) + delta

    def value(self, **labels: str) -> float:
        return self._series.get(tuple(str(labels[l]) for l in self.labels), 0.0)

    def expose(self) -> list[str]:
        return [f"{self.name}{self._fmt_labels(k)} {v}" for k, v in sorted(self._series.items())]


class Histogram(_Metric):
    kind = "histogram"

    def __init__(self, name, help_, labels, buckets=BOOT_BUCKETS_S) -> None:
        super().__init__(name, help_, labels)
        self.buckets = tuple(sorted(buckets))

    def observe(self, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(labels)
            s = self._series.setdefault(k, {"counts": [0] * (len(self.buckets) + 1), "sum": 0.0, "n": 0, "raw": []})
            s["counts"][bisect.bisect_left(self.buckets, value)] += 1
            s["sum"] += value
            s["n"] += 1
            if len(s["raw"]) < 10_000:
                s["raw"].append(value)

    def quantile(self, q: float, **labels: str) -> float | None:
        s = self._series.get(tuple(str(labels[l]) for l in self.labels))
        if not s or not s["raw"]:
            return None
        data = sorted(s["raw"])
        return data[min(len(data) - 1, int(math.ceil(q * len(data))) - 1)]

    def expose(self) -> list[str]:
        out = []
        for k, s in sorted(self._series.items()):
            cum = 0
            for b, c in zip(self.buckets + (math.inf,), s["counts"]):
                cum += c
                le = "+Inf" if b == math.inf else repr(b)
                le_label = 'le="' + le + '"'
                out.append(f"{self.name}_bucket{self._fmt_labels(k, le_label)} {cum}")
            out.append(f"{self.name}_sum{self._fmt_labels(k)} {s['sum']}")
            out.append(f"{self.name}_count{self._fmt_labels(k)} {s['n']}")
        return out


class Registry:
    def __init__(self) -> None:
        self._metrics: dict[str, _Metric] = {}

    def _add(self, m: _Metric):
        if m.name in self._metrics:
            raise Inv24Error("CONFIG_REJECTED", f"duplicate metric {m.name}")
        self._metrics[m.name] = m
        return m

    def counter(self, name, help_, labels=()):
        return self._add(Counter(name, help_, tuple(labels)))

    def gauge(self, name, help_, labels=()):
        return self._add(Gauge(name, help_, tuple(labels)))

    def histogram(self, name, help_, labels=(), buckets=BOOT_BUCKETS_S):
        return self._add(Histogram(name, help_, tuple(labels), buckets))

    def expose(self) -> str:
        lines = []
        for m in self._metrics.values():
            lines += [f"# HELP {m.name} {m.help}", f"# TYPE {m.name} {m.kind}", *m.expose()]
        return "\n".join(lines) + "\n"


def standard_registry() -> tuple[Registry, dict[str, _Metric]]:
    """The contract's signals plus dependency/capability/version health."""
    r = Registry()
    m = {
        "instances": r.gauge("microvm_instances", "microVMs by state and tenant", ("state", "tenant")),
        "boot": r.histogram("microvm_boot_seconds", "cold boot time against the budget", ("environment",)),
        "device_refusals": r.counter("microvm_device_refusals", "out-of-model device requests", ("device",)),
        "budget_breaches": r.counter("microvm_boot_budget_breaches", "boots over budget", ("environment",)),
        "admission": r.counter("microvm_admission_decisions", "admission decisions", ("outcome", "code")),
        "queue_depth": r.gauge("microvm_admission_queue_depth", "queued admissions", ()),
        "lifecycle": r.histogram("microvm_lifecycle_seconds", "lifecycle op duration", ("op",),
                                 buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5)),
        "cleanup": r.counter("microvm_cleanup", "cleanup outcomes", ("outcome",)),
        "dependency_up": r.gauge("microvm_dependency_up", "1 if dependency healthy", ("dependency",)),
        "build_info": r.gauge("microvm_build_info", "runtime/firecracker/config versions", ("runtime", "firecracker", "config_revision")),
    }
    return r, m
