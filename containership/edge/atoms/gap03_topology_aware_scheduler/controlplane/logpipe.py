"""MC-020 - Structured logging pipeline (GAP03-LOG/1).

JSON lines with a stable schema; correlation IDs are generated at ingress
when absent; untrusted strings are escaped (no newline/control injection);
secrets are redacted recursively; a bounded queue with an explicit drop
counter decouples the scheduler from the sink; success/debug events are
sampled, security/audit events never are.
"""
from __future__ import annotations

import collections
import json
import random
import threading
import time
import uuid

from . import privacy

SCHEMA = "GAP03-LOG/1"
REQUIRED = ("schema", "ts", "severity", "event", "code", "service", "version", "instance", "request_id", "trace_id")
SEVERITIES = ("DEBUG", "INFO", "NOTICE", "WARN", "ERROR", "SECURITY")
# taxonomy: event -> (severity, sampleable)
EVENTS = {
    "score.ok": ("DEBUG", True), "commit.ok": ("INFO", True), "policy.denied": ("NOTICE", True),
    "state.conflict": ("NOTICE", False), "dependency.failure": ("WARN", False), "internal.error": ("ERROR", False),
    "security.auth_failed": ("SECURITY", False), "security.replay": ("SECURITY", False), "audit.write_failed": ("ERROR", False),
    "config.activated": ("INFO", False), "control.changed": ("NOTICE", False),
}


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def escape(value) -> str:
    s = str(value)
    return "".join(ch if 32 <= ord(ch) < 127 and ch not in "\x7f" else f"\\u{ord(ch):04x}" for ch in s)[:512]


class Logger:
    def __init__(self, sink, *, service="gap03", version="4.3.0", instance="local", capacity=10_000, sample_rate=0.01,
                 key=b"gap03-log-pseudonym", seed=None, metrics=None):
        self.sink, self.service, self.version, self.instance = sink, service, version, instance
        self.q: collections.deque = collections.deque()
        self.capacity, self.sample_rate, self.key = capacity, sample_rate, key
        self.dropped = 0
        self.rng = random.Random(seed)
        self.metrics = metrics
        self._lock = threading.Lock()

    def log(self, event: str, *, code: str = "OK", request_id: str | None = None, trace_id: str | None = None, **fields):
        if event not in EVENTS:
            raise ValueError(f"unregistered event {event}")
        severity, sampleable = EVENTS[event]
        if sampleable and self.rng.random() >= self.sample_rate and severity in ("DEBUG", "INFO"):
            return None
        rec = {"schema": SCHEMA, "ts": round(time.time(), 3), "severity": severity, "event": event, "code": escape(code),
               "service": self.service, "version": self.version, "instance": self.instance,
               "request_id": escape(request_id or new_correlation_id()), "trace_id": escape(trace_id or "")}
        safe = privacy.sanitize(fields, signal="logs", key=self.key)
        rec.update({k: (escape(v) if isinstance(v, str) else v) for k, v in safe.items() if k not in rec})
        with self._lock:
            if len(self.q) >= self.capacity:
                if severity in ("SECURITY", "ERROR"):
                    self.q.popleft()  # evict oldest to keep mandatory events
                    self.dropped += 1
                else:
                    self.dropped += 1
                    if self.metrics:
                        self.metrics.inc("gap03_telemetry_dropped_total", signal="logs")
                    return None
            self.q.append(rec)
        return rec

    def flush(self) -> int:
        n = 0
        while True:
            with self._lock:
                if not self.q:
                    return n
                rec = self.q.popleft()
            try:
                self.sink(json.dumps(rec, sort_keys=True, ensure_ascii=True))
                n += 1
            except Exception:  # noqa: BLE001 - sink outage must not halt scheduling
                with self._lock:
                    self.dropped += 1
                    if self.metrics:
                        self.metrics.inc("gap03_telemetry_dropped_total", signal="logs")


RETENTION = {"hot_days": 14, "total_days": 90, "rotation_mb": 256, "compression": "zstd", "transport": "TLS 1.3 to collector",
             "access": "role:operator,auditor", "security_events_days": 400}


def validate_record(line: str) -> dict:
    rec = json.loads(line)
    missing = [k for k in REQUIRED if k not in rec]
    if missing:
        raise ValueError(f"log record missing {missing}")
    if rec["severity"] not in SEVERITIES:
        raise ValueError("bad severity")
    return rec
