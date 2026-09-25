"""Component 52 - structured logging and W3C trace-context propagation (``PK_DYN_LOG/1``).

Log record (one canonical-JSON object per line)::

  {"schema": "PK_DYN_LOG/1", "seq": int, "ts": number, "level": "debug|info|warning|error|critical",
   "event": "<dotted.name>", "msg": str, "service": str,
   "corr": {"op_id": str, "tenant": str|null, "workload": str|null, "node": str|null},
   "trace": {"trace_id": 32hex, "span_id": 16hex, "parent_span_id": 16hex|null},
   "attrs": {...redacted...}, "prev": 64hex, "hash": 64hex}

Rules: every record passes ``core.redact`` before hashing; ``hash`` = sha256 of the
canonical record without ``hash``; ``prev`` links to the previous record (genesis =
64 zeros) so deletion/edit/reorder is detectable with ``verify_lines``.

Trace boundaries: inbound ``traceparent`` from *trusted* callers (same control
plane) is continued; context returned by an external provider is never adopted as
parent - it is recorded as a span link (``provider_span``) so a provider cannot
splice spans into our traces.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Callable

from .core import canonical, redact, redact_text, sha256_hex

SCHEMA = "PK_DYN_LOG/1"
LEVELS = ("debug", "info", "warning", "error", "critical")
GENESIS = "0" * 64
_TP_RE = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})(-.*)?$")
_EVENT_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")
MAX_MSG = 4096


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    sampled: bool = True

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"

    def child(self, rng: random.Random) -> "TraceContext":
        return TraceContext(self.trace_id, _rand_hex(rng, 16), self.span_id, self.sampled)


def _rand_hex(rng: random.Random, n: int) -> str:
    while True:
        v = "%0*x" % (n, rng.getrandbits(n * 4))
        if set(v) != {"0"}:
            return v


def new_root(rng: random.Random, sampled: bool = True) -> TraceContext:
    return TraceContext(_rand_hex(rng, 32), _rand_hex(rng, 16), None, sampled)


def parse_traceparent(value: object) -> TraceContext | None:
    """W3C Trace Context level 1; returns None for anything invalid (caller starts a new root)."""
    if not isinstance(value, str) or len(value) > 512:
        return None
    m = _TP_RE.fullmatch(value)  # lowercase only, per spec
    if not m:
        return None
    ver, tid, sid, flags, rest = m.groups()
    if ver == "ff" or (ver == "00" and rest) or set(tid) == {"0"} or set(sid) == {"0"}:
        return None
    return TraceContext(tid, sid, None, bool(int(flags, 16) & 1))


def inject(ctx: TraceContext, carrier: dict) -> dict:
    carrier["traceparent"] = ctx.traceparent()
    return carrier


def extract(carrier: dict, rng: random.Random, *, trusted: bool) -> tuple[TraceContext, dict | None]:
    """Return (context for our next span, link or None)."""
    remote = parse_traceparent(carrier.get("traceparent")) if isinstance(carrier, dict) else None
    if remote is None:
        return new_root(rng), None
    if trusted:
        return remote.child(rng), None
    return new_root(rng), {"link_trace_id": remote.trace_id, "link_span_id": remote.span_id}


def provider_span(parent: TraceContext, provider: str, rng: random.Random) -> tuple[TraceContext, dict]:
    """Outbound call to an external provider: new child span + headers to send."""
    span = parent.child(rng)
    return span, inject(span, {"x-inv08-provider": provider})


class StructuredLogger:
    def __init__(self, sink: Callable[[str], None], clock: Callable[[], float], service: str = "inv08-controller",
                 min_level: str = "info") -> None:
        if min_level not in LEVELS:
            raise ValueError(min_level)
        self.sink, self.clock, self.service, self.min_level = sink, clock, service, min_level
        self.seq, self.prev = 0, GENESIS

    def log(self, level: str, event: str, msg: str, *, ctx: TraceContext, op_id: str,
            tenant: str | None = None, workload: str | None = None, node: str | None = None,
            **attrs) -> dict | None:
        if level not in LEVELS:
            raise ValueError(f"bad level {level}")
        if not _EVENT_RE.match(event):
            raise ValueError(f"bad event name {event!r}")
        if not op_id:
            raise ValueError("op_id (correlation id) required")
        if LEVELS.index(level) < LEVELS.index(self.min_level):
            return None
        rec = {"schema": SCHEMA, "seq": self.seq + 1, "ts": self.clock(), "level": level, "event": event,
               "msg": redact_text(str(msg)[:MAX_MSG]), "service": self.service,
               "corr": {"op_id": op_id, "tenant": tenant, "workload": workload, "node": node},
               "trace": {"trace_id": ctx.trace_id, "span_id": ctx.span_id, "parent_span_id": ctx.parent_span_id},
               "attrs": redact(attrs), "prev": self.prev}
        rec["hash"] = sha256_hex(canonical(rec))  # raises before any state change
        line = canonical(rec).decode("utf-8")
        self.sink(line)
        self.seq, self.prev = rec["seq"], rec["hash"]
        return rec


def verify_lines(lines: list[str]) -> tuple[bool, list[str]]:
    problems, prev, seq = [], GENESIS, 0
    for i, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
            body = {k: v for k, v in rec.items() if k != "hash"}
            if rec["schema"] != SCHEMA:
                raise KeyError("schema")
        except (ValueError, KeyError, TypeError, AttributeError):
            problems.append(f"line {i}: unparseable")
            break
        if rec["seq"] != seq + 1:
            problems.append(f"line {i}: seq gap")
        if rec["prev"] != prev:
            problems.append(f"line {i}: chain break")
        if sha256_hex(canonical(body)) != rec["hash"]:
            problems.append(f"line {i}: hash mismatch")
        prev, seq = rec["hash"], rec["seq"]
    return not problems, problems
