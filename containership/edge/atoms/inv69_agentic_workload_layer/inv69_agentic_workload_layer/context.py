"""Deadline, cancellation, trace context and bounded admission (C025, C074).

``CallContext`` is the one object propagated across every internal and
adjacent-layer call.  It carries an absolute deadline (monotonic clock), a
cancellation token, W3C ``traceparent``-compatible trace identifiers and a
correlation id.  Baggage is allowlisted and secret-named keys are refused.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any
import re
import secrets
import threading
import time

from .errors import AgentError, new_correlation_id
from .redaction import is_secret_key

# Per-operation timeout budgets in seconds (defaults; configurable via config.timeouts).
DEFAULT_TIMEOUTS = {
    "authorization": 0.5,
    "policy": 0.25,
    "approval_lookup": 0.25,
    "sandbox_launch_fast": 1.0,
    "sandbox_launch_heavy": 10.0,
    "tool_execution": 30.0,
    "audit_persist": 0.5,
    "audit_export": 5.0,
    "dependency_call": 2.0,
    "overall_run": 300.0,
}

BAGGAGE_ALLOWLIST = frozenset({"tenant", "site", "release_id", "profile", "config_digest"})
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class CancellationToken:
    """Cooperative cancellation; propagates parent -> child, never child -> parent."""

    def __init__(self, parent: "CancellationToken | None" = None):
        self._event = threading.Event()
        self._parent = parent
        self.reason: str | None = None

    def cancel(self, reason: str = "caller cancelled") -> None:
        self.reason = reason
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set() or (self._parent is not None and self._parent.cancelled)

    def child(self) -> "CancellationToken":
        return CancellationToken(self)


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool = True
    links: tuple[str, ...] = ()        # span links for resume/failover (not parentage)

    @classmethod
    def new_root(cls, sampled: bool = True) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8), sampled)

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.sampled)

    def linked_root(self) -> "TraceContext":
        """New trace for resumed/failover work, linked (not parented) to this one."""
        return TraceContext(secrets.token_hex(16), secrets.token_hex(8), self.sampled,
                            links=(f"{self.trace_id}:{self.span_id}",))

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"

    @classmethod
    def parse(cls, header: Any) -> "TraceContext":
        """Parse untrusted traceparent; malformed input yields a fresh root (never raises)."""
        if isinstance(header, str) and len(header) <= 64:
            m = _TRACEPARENT.match(header)
            if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
                return cls(m.group(1), m.group(2), m.group(3) == "01")
        return cls.new_root()


@dataclass(frozen=True)
class CallContext:
    deadline: float                     # absolute, time.monotonic()
    cancel: CancellationToken
    trace: TraceContext
    correlation_id: str
    tenant: str = "default"
    baggage: tuple[tuple[str, str], ...] = ()
    attempt: int = 0

    @classmethod
    def new(cls, *, timeout: float = DEFAULT_TIMEOUTS["overall_run"], tenant: str = "default",
            traceparent: str | None = None, baggage: dict[str, str] | None = None,
            clock=time.monotonic) -> "CallContext":
        if not (isinstance(timeout, (int, float)) and 0 < timeout <= 86400):
            raise AgentError("AGT-VAL-001", "timeout must be in (0, 86400] seconds")
        bag = []
        for k, v in sorted((baggage or {}).items()):
            if k not in BAGGAGE_ALLOWLIST or is_secret_key(k):
                raise AgentError("AGT-VAL-001", "baggage key not allowlisted", details={"key": str(k)[:64]})
            bag.append((k, str(v)[:128]))
        trace = TraceContext.parse(traceparent) if traceparent else TraceContext.new_root()
        return cls(clock() + timeout, CancellationToken(), trace, new_correlation_id(), tenant, tuple(bag))

    def remaining(self, clock=time.monotonic) -> float:
        return self.deadline - clock()

    def child(self, op: str, budget: float | None = None, clock=time.monotonic) -> "CallContext":
        """Derive a child context for one operation; its deadline never exceeds the parent's."""
        per_op = budget if budget is not None else DEFAULT_TIMEOUTS.get(op, DEFAULT_TIMEOUTS["dependency_call"])
        return replace(self, deadline=min(self.deadline, clock() + per_op),
                       cancel=self.cancel.child(), trace=self.trace.child())

    def check(self, clock=time.monotonic) -> None:
        if self.cancel.cancelled:
            raise AgentError("AGT-CAN-001", correlation_id=self.correlation_id)
        if self.remaining(clock) <= 0:
            raise AgentError("AGT-TMO-001", correlation_id=self.correlation_id)


class Admission:
    """Bounded admission control with explicit backpressure (never an unbounded queue).

    ``max_active`` concurrent runs; up to ``max_waiting`` callers may wait up to
    their own deadline; anything beyond is shed immediately with AGT-CAP-003.
    Priority classes: ``critical`` work may use a reserved slot.
    """

    def __init__(self, max_active: int = 64, max_waiting: int = 256, reserved_critical: int = 2):
        if max_active <= reserved_critical or max_waiting < 0:
            raise ValueError("invalid admission limits")
        self.max_active, self.max_waiting, self.reserved = max_active, max_waiting, reserved_critical
        self._active = 0
        self._waiting = 0
        self._cv = threading.Condition()
        self.shed = 0
        self.admitted = 0
        self.oldest_wait_started: float | None = None

    def _limit(self, priority: str) -> int:
        return self.max_active if priority == "critical" else self.max_active - self.reserved

    def acquire(self, ctx: CallContext, priority: str = "normal") -> None:
        with self._cv:
            if self._active < self._limit(priority):
                self._active += 1
                self.admitted += 1
                return
            if self._waiting >= self.max_waiting:
                self.shed += 1
                raise AgentError("AGT-CAP-003", correlation_id=ctx.correlation_id,
                                 details={"active": self._active, "waiting": self._waiting})
            self._waiting += 1
            if self.oldest_wait_started is None:
                self.oldest_wait_started = time.monotonic()
            try:
                while self._active >= self._limit(priority):
                    ctx.check()
                    self._cv.wait(timeout=max(0.0, min(0.05, ctx.remaining())))
                self._active += 1
                self.admitted += 1
            finally:
                self._waiting -= 1
                if self._waiting == 0:
                    self.oldest_wait_started = None

    def release(self) -> None:
        with self._cv:
            self._active -= 1
            self._cv.notify()

    def stats(self) -> dict[str, Any]:
        with self._cv:
            age = (time.monotonic() - self.oldest_wait_started) if self.oldest_wait_started else 0.0
            return {"active": self._active, "waiting": self._waiting, "max_active": self.max_active,
                    "max_waiting": self.max_waiting, "shed": self.shed, "admitted": self.admitted,
                    "oldest_wait_s": round(age, 6)}
