"""Structured JSON event logging with correlation IDs and redaction (MC-041)."""
from __future__ import annotations

import json
import sys
import threading
import time
from contextvars import ContextVar
from typing import IO, Final

from ..security.secrets import redact

EVENT_SCHEMA: Final[str] = "PK_MICROVM_LOG/1"
LEVELS: Final[dict[str, int]] = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}
_ctx: ContextVar[dict] = ContextVar("inv24_log_ctx", default={})
MAX_LINE = 16 * 1024


class bind:
    """Context manager adding correlation fields (node/tenant/workload/operation/trace)."""

    def __init__(self, **fields: str) -> None:
        self.fields = fields

    def __enter__(self):
        self.token = _ctx.set({**_ctx.get(), **self.fields})
        return self

    def __exit__(self, *exc):
        _ctx.reset(self.token)


class EventLogger:
    def __init__(self, component: str = "INV-24", *, node: str = "unknown", stream: IO[str] | None = None,
                 level: str = "info") -> None:
        self.component, self.node, self.stream = component, node, stream or sys.stderr
        self.threshold = LEVELS[level]
        self._lock = threading.Lock()
        self.dropped = 0

    def log(self, level: str, event: str, **fields: object) -> dict | None:
        if LEVELS.get(level, 0) < self.threshold:
            return None
        rec = {"schema": EVENT_SCHEMA, "ts": round(time.time(), 6), "level": level, "component": self.component,
               "node": self.node, "event": event[:64], **{k: v for k, v in _ctx.get().items()},
               "fields": redact(fields)}
        line = json.dumps(rec, sort_keys=True, default=str)
        if len(line) > MAX_LINE:
            rec["fields"] = {"truncated": True}
            line = json.dumps(rec, sort_keys=True)
        with self._lock:
            try:
                self.stream.write(line + "\n")
            except (OSError, ValueError):
                self.dropped += 1
        return rec

    def info(self, event, **f):
        return self.log("info", event, **f)

    def warning(self, event, **f):
        return self.log("warning", event, **f)

    def error(self, event, **f):
        return self.log("error", event, **f)
