"""Export/sink adapters (32): a durable JSON-lines file sink and an
OTLP/JSON-shaped encoder, driven by a retrying exporter with exponential
backoff, a bounded retry budget and a circuit breaker.  Export is always
gated by the tenant policy (``may_export``) -- residency first."""
from __future__ import annotations

import json
import os
from typing import Callable, Iterable

from .controls import CircuitBreaker
from .errors import DependencyUnavailable
from .signals import Record


def to_otlp_json(records: Iterable[Record]) -> dict:
    """Encode to the OTLP/JSON resource->scope->items shape (metrics as gauges,
    logs as logRecords).  Not a certified OTLP implementation: validated only
    against the shape, which is why component 32's interoperability check is
    BLOCKED pending a real collector."""
    by_res: dict = {}
    for r in records:
        res = r.resource
        rk = (res.tenant, res.environment, res.site, res.workload, res.boundary, res.instance)
        by_res.setdefault(rk, []).append(r)
    out = []
    for rk, recs in sorted(by_res.items()):
        attrs = [{"key": k, "value": {"stringValue": v}} for k, v in zip(
            ("tenant.id", "deployment.environment", "site.id", "service.name", "gap09.boundary", "service.instance.id"), rk) if v]
        metrics = [{"name": r.name, "gauge": {"dataPoints": [{"timeUnixNano": str(r.at * 10**9), "asDouble": float(r.body["value"])}]}}
                   for r in recs if r.kind == "metric"]
        logs = [{"timeUnixNano": str(r.at * 10**9), "severityText": r.body.get("severity", "INFO"),
                 "body": {"stringValue": r.body.get("text", "")},
                 **({"traceId": r.trace_id} if r.trace_id else {}), **({"spanId": r.span_id} if r.span_id else {})}
                for r in recs if r.kind == "log"]
        entry = {"resource": {"attributes": attrs}}
        if metrics:
            entry["scopeMetrics"] = [{"scope": {"name": "gap09"}, "metrics": metrics}]
        if logs:
            entry["scopeLogs"] = [{"scope": {"name": "gap09"}, "logRecords": logs}]
        out.append(entry)
    return {"resourceData": out}


class FileSink:
    def __init__(self, path: str) -> None:
        self.path = path

    def send(self, payload: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


class Exporter:
    def __init__(self, sink, *, breaker: CircuitBreaker, max_attempts: int = 5, base_delay: float = 0.5,
                 sleep: Callable[[float], None] = lambda s: None, clock: Callable[[], float] = lambda: 0.0) -> None:
        self.sink, self.breaker, self.max_attempts, self.base_delay = sink, breaker, max_attempts, base_delay
        self.sleep, self.clock = sleep, clock
        self.sent = self.failed = 0

    def export(self, payload: dict) -> int:
        """Return attempts used; raise DependencyUnavailable once the budget or
        breaker says stop (the caller keeps the data in its WAL)."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                self.breaker.call(lambda: self.sink.send(payload), self.clock())
                self.sent += 1
                return attempt
            except DependencyUnavailable:
                self.failed += 1
                raise
            except Exception:
                if attempt == self.max_attempts:
                    self.failed += 1
                    raise DependencyUnavailable("export retry budget exhausted", attempts=attempt)
                self.sleep(self.base_delay * 2 ** (attempt - 1))
        raise AssertionError("unreachable")
