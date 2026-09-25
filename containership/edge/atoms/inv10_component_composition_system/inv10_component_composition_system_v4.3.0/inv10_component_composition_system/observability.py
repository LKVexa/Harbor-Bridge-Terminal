"""MC-24..MC-27: metrics, structured logs + trace context, health, explain.

* :class:`Metrics` implements the contract's named signals (``compositions``
  counter by outcome, ``unsatisfied_imports`` by interface, ``cycles_detected``,
  ``external_imports`` gauge) plus latency histogram, and renders Prometheus
  text exposition.
* :class:`StructuredLogger` emits JSON lines with operation id, W3C
  ``traceparent`` propagation, tenant/workload correlation, sampling and
  redaction.
* :func:`health_report` and :func:`explain` are the operator surfaces.
"""
from __future__ import annotations

import json
import random
import re
import secrets
import sys
import threading
import time
from collections import defaultdict
from typing import Any, Callable, Mapping, TextIO

from .security import redact

LATENCY_BUCKETS_MS = (1, 5, 10, 25, 50, 100, 200, 500, 1000, 5000)
MAX_LABEL_CARDINALITY = 1000


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self.gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self.hist: dict[str, list[int]] = defaultdict(lambda: [0] * (len(LATENCY_BUCKETS_MS) + 1))
        self.hist_sum: dict[str, float] = defaultdict(float)

    def _labels(self, name: str, labels: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        seen = sum(1 for (n, _) in self.counters if n == name)
        if seen >= MAX_LABEL_CARDINALITY and (name, key) not in self.counters:
            return (("overflow", "true"),)  # bound cardinality (untrusted interface names)
        return key

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self.counters[(name, self._labels(name, labels))] += value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self.gauges[(name, tuple(sorted(labels.items())))] = value

    def observe_ms(self, name: str, ms: float) -> None:
        with self._lock:
            idx = next((i for i, b in enumerate(LATENCY_BUCKETS_MS) if ms <= b), len(LATENCY_BUCKETS_MS))
            self.hist[name][idx] += 1
            self.hist_sum[name] += ms

    def record_outcome(self, outcome: str, *, error: Mapping[str, Any] | None = None,
                       result: Mapping[str, Any] | None = None, latency_ms: float | None = None) -> None:
        self.inc("inv10_compositions_total", outcome=outcome)
        if error and error.get("code") == "UNSATISFIED_IMPORT":
            self.inc("inv10_unsatisfied_imports_total", interface=str(error["details"].get("interface")))
        if error and error.get("code") == "COMPOSITION_CYCLE":
            self.inc("inv10_cycles_detected_total")
        if result is not None:
            self.set("inv10_external_imports", len(result["external_imports"]),
                     composition=result["composition"][:16])
        if latency_ms is not None:
            self.observe_ms("inv10_link_latency_ms", latency_ms)

    def render_prometheus(self) -> str:
        def fmt(labels: tuple[tuple[str, str], ...]) -> str:
            if not labels:
                return ""
            esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in labels) + "}"
        lines = []
        with self._lock:
            for (n, l), v in sorted(self.counters.items()):
                lines.append(f"{n}{fmt(l)} {v}")
            for (n, l), v in sorted(self.gauges.items()):
                lines.append(f"{n}{fmt(l)} {v}")
            for n, buckets in sorted(self.hist.items()):
                cum = 0
                for b, c in zip(list(LATENCY_BUCKETS_MS) + ["+Inf"], buckets):
                    cum += c
                    lines.append(f'{n}_bucket{{le="{b}"}} {cum}')
                lines.append(f"{n}_count {cum}")
                lines.append(f"{n}_sum {self.hist_sum[n]}")
        return "\n".join(lines) + "\n"


_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def child_traceparent(parent: str | None) -> str:
    m = _TRACEPARENT.match(parent or "")
    trace = m.group(1) if m and m.group(1) != "0" * 32 else secrets.token_hex(16)
    flags = m.group(3) if m else "01"
    return f"00-{trace}-{secrets.token_hex(8)}-{flags}"


class StructuredLogger:
    def __init__(self, stream: TextIO | None = None, *, sample_rate: float = 1.0,
                 clock: Callable[[], float] = time.time, rng: random.Random | None = None) -> None:
        self.stream = stream or sys.stderr
        self.sample_rate = sample_rate
        self.clock = clock
        self.rng = rng or random.Random()
        self._lock = threading.Lock()

    def log(self, level: str, event: str, *, operation_id: str, traceparent: str | None = None,
            **fields: Any) -> dict[str, Any] | None:
        if level in {"debug", "info"} and self.rng.random() >= self.sample_rate:
            return None  # warnings/errors are never sampled away
        rec = {"ts": self.clock(), "level": level, "event": event, "operation_id": operation_id,
               "traceparent": traceparent, **redact(fields)}
        with self._lock:
            self.stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        return rec


def health_report(*, version: str, limits: Any, dependencies: Mapping[str, Callable[[], bool]],
                  frozen: bool = False, active: str | None = None) -> dict[str, Any]:
    deps = {}
    for name, probe in sorted(dependencies.items()):
        try:
            deps[name] = "ok" if probe() else "degraded"
        except Exception as exc:  # probe failure is data, not a crash
            deps[name] = f"down:{type(exc).__name__}"
    ready = all(v == "ok" for v in deps.values()) and not frozen
    return {"status": "ready" if ready else "not-ready", "live": True, "version": version,
            "frozen": frozen, "active_composition": active, "dependencies": deps,
            "limits": dict(vars(limits)),
            "capabilities": ["compose", "wit", "aliasing", "dead-export-elimination", "incremental",
                             "nested", "diff", "explain", "migrate-4.1.0"]}


def explain(units: list[Any], *, external: frozenset[str] = frozenset(), result: Mapping[str, Any] | None = None,
            error: Mapping[str, Any] | None = None, decisions: list[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Operator report: dependency paths, candidates, cycle path, decisions."""
    providers: dict[str, list[str]] = defaultdict(list)
    for u in units:
        for e in u.exports:
            providers[e].append(u.name)
    imports = []
    for u in sorted(units, key=lambda u: u.name):
        for i in sorted(u.imports):
            cands = sorted(providers.get(i, []))
            status = ("bound" if len(cands) == 1 else "ambiguous" if cands else
                      "external" if i in external else "unsatisfied")
            imports.append({"consumer": u.name, "interface": i, "candidates": cands, "status": status})
    report: dict[str, Any] = {"imports": imports,
                              "unused_exports": sorted(set(providers) - {i for u in units for i in u.imports})}
    if result:
        deps: dict[str, set[str]] = defaultdict(set)
        for b in result["bindings"]:
            if "provider" in b:
                deps[b["consumer"]].add(b["provider"])
        def depth(n: str, seen: frozenset[str] = frozenset()) -> int:
            return 0 if not deps[n] else 1 + max(depth(d, seen | {n}) for d in deps[n])
        report["order"] = result["order"]
        report["depth"] = {n: depth(n) for n in result["order"]}
        report["composition"] = result["composition"]
    if error:
        report["error"] = dict(error)
    if decisions:
        report["policy_decisions"] = [dict(d) for d in decisions]
    return report


def render_explain_text(report: Mapping[str, Any]) -> str:
    out = []
    if "error" in report:
        out.append(f"REFUSED {report['error']['code']}: {report['error']['message']}")
    for row in report["imports"]:
        out.append(f"{row['consumer']:<24} imports {row['interface']:<40} -> {row['status']} {row['candidates']}")
    if report.get("unused_exports"):
        out.append("unused exports: " + ", ".join(report["unused_exports"]))
    if "order" in report:
        out.append("order: " + " -> ".join(report["order"]))
    return "\n".join(out)
