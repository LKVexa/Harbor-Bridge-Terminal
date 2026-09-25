"""Structured logging for INV-14 (component P1-10; C073, C075, C079).

Schema ``PK_POLL_LOG/1`` (schemas/pk_poll_log.schema.json).  Every record carries
stable identifiers -- tenant, workload, component, operation, correlation_id and
trace_id -- plus a closed ``event`` vocabulary and a severity.  All free-form
fields pass through ``redaction.redact``; records are bounded to 4 KiB.
"""
from __future__ import annotations

import json
import sys
import threading
import time

try:
    from .redaction import redact
except ImportError:
    from redaction import redact

LOG_SCHEMA = "PK_POLL_LOG/1"
LEVELS = ("DEBUG", "INFO", "WARN", "ERROR", "AUDIT")
OPERATIONS = ("poll", "admit", "authorize", "lifecycle", "config", "migrate", "checkpoint", "export")
MAX_LINE = 4096


class StructLogger:
    def __init__(self, stream=None, *, component: str = "INV-14", version: str = "4.3.0", clock=time.time):
        self._stream = stream if stream is not None else sys.stderr
        self._lock = threading.Lock()
        self.component, self.version, self._clock = component, version, clock
        self.dropped = 0

    def log(self, level: str, operation: str, event: str, *, tenant: str = "-", workload: str = "-",
            correlation_id: str = "-", trace_id: str = "-", **fields) -> dict:
        if level not in LEVELS:
            level = "ERROR"
        if operation not in OPERATIONS:
            operation = "poll"
        rec = {"schema": LOG_SCHEMA, "ts": round(self._clock(), 6), "level": level,
               "component": self.component, "component_version": self.version,
               "tenant": str(tenant)[:64], "workload": str(workload)[:64], "operation": operation,
               "event": str(event)[:64], "correlation_id": str(correlation_id)[:64],
               "trace_id": str(trace_id)[:32], "fields": redact(fields)}
        line = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        if len(line) > MAX_LINE:
            rec["fields"] = {"_truncated": True}
            line = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        with self._lock:
            try:
                self._stream.write(line + "\n")
            except Exception:
                self.dropped += 1  # logging never changes poll semantics
        return rec
