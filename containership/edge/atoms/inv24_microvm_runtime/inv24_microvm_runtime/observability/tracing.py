"""W3C trace-context propagation and in-process spans (MC-042)."""
from __future__ import annotations

import re
import secrets
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass, field

_TP = re.compile(r"00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})")
_current: ContextVar["Span | None"] = ContextVar("inv24_span", default=None)
MAX_SPANS = 10_000


def parse_traceparent(header: str | None) -> tuple[str, str] | None:
    if not header:
        return None
    m = _TP.fullmatch(header.strip())
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return m.group(1), m.group(2)


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    start: float = field(default_factory=time.time)
    end: float | None = None
    attrs: dict = field(default_factory=dict)
    status: str = "ok"

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-01"


class Tracer:
    def __init__(self) -> None:
        self.finished: list[Span] = []
        self._lock = threading.Lock()

    def span(self, name: str, *, traceparent: str | None = None, **attrs):
        tracer = self

        class _Ctx:
            def __enter__(self_inner):
                parent = _current.get()
                remote = parse_traceparent(traceparent)
                if parent:
                    tid, pid = parent.trace_id, parent.span_id
                elif remote:
                    tid, pid = remote
                else:
                    tid, pid = secrets.token_hex(16), None
                self_inner.span = Span(name, tid, secrets.token_hex(8), pid, attrs={k: str(v)[:128] for k, v in attrs.items()})
                self_inner.tok = _current.set(self_inner.span)
                return self_inner.span

            def __exit__(self_inner, et, ev, tb):
                s = self_inner.span
                s.end = time.time()
                if ev is not None:
                    s.status = f"error:{getattr(ev, 'code', type(ev).__name__)}"
                _current.reset(self_inner.tok)
                with tracer._lock:
                    if len(tracer.finished) < MAX_SPANS:
                        tracer.finished.append(s)
                return False
        return _Ctx()
