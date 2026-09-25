"""The one shared retry engine for INV-69 (C053, C025).

Retry is allowed only when BOTH the error code is retryable AND the operation
class is safe to retry: ``idempotent`` operations always, ``keyed`` operations
only with an idempotency key, ``non_idempotent`` never.  Delays use capped
exponential backoff with *full jitter*; the engine never sleeps past the
caller's deadline and checks cancellation before every sleep and attempt.  A
process-wide retry budget (token bucket) prevents synchronized retry storms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import random
import threading
import time

from .context import CallContext
from .errors import AgentError, translate

OPERATION_CLASSES = {
    # operation -> retry safety
    "authorization.check": "idempotent",
    "policy.evaluate": "idempotent",
    "approval.lookup": "idempotent",
    "sandbox.launch": "idempotent",          # launch is side-effect-free until dispatch
    "durable.acquire": "idempotent",         # same owner re-acquires; a newer fence supersedes
    "audit.persist": "keyed",                # keyed by event_hash
    "audit.export": "keyed",
    "durable.checkpoint": "keyed",
    "tool.execute.readonly": "idempotent",
    "tool.execute.side_effect": "keyed",     # only with an idempotency key honoured by the tool
    "tool.execute.unknown": "non_idempotent",
}


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.05
    max_delay: float = 2.0
    per_attempt_timeout: float = 2.0

    def __post_init__(self):
        if not (1 <= self.max_attempts <= 10):
            raise ValueError("max_attempts must be 1..10")
        if not (0 < self.base_delay <= self.max_delay <= 60):
            raise ValueError("invalid delays")

    def delay(self, attempt: int, rng: random.Random) -> float:
        """Full jitter: uniform(0, min(cap, base * 2**attempt))."""
        return rng.uniform(0.0, min(self.max_delay, self.base_delay * (2 ** attempt)))


class RetryBudget:
    """Token bucket: retries may consume at most ``ratio`` of first attempts (+ ``floor``)."""

    def __init__(self, ratio: float = 0.2, floor: int = 10):
        self.ratio, self.floor = ratio, floor
        self._requests = 0
        self._retries = 0
        self._lock = threading.Lock()

    def note_request(self):
        with self._lock:
            self._requests += 1

    def try_spend(self) -> bool:
        with self._lock:
            if self._retries < self.floor + self.ratio * self._requests:
                self._retries += 1
                return True
            return False


@dataclass
class AttemptRecord:
    attempt: int
    code: str | None
    delay: float
    outcome: str


@dataclass
class RetryResult:
    value: Any
    attempts: list[AttemptRecord] = field(default_factory=list)
    idempotency_key: str | None = None


GLOBAL_BUDGET = RetryBudget()
_RNG = random.Random()   # C066: seeded once (os.urandom); per-call Random() cost ~17us each


def call_with_retry(op: str, fn: Callable[[CallContext], Any], ctx: CallContext, *,
                    policy: RetryPolicy | None = None, idempotency_key: str | None = None,
                    budget: RetryBudget | None = None, rng: random.Random | None = None,
                    sleep: Callable[[float], None] = time.sleep,
                    clock: Callable[[], float] = time.monotonic,
                    on_attempt: Callable[[AttemptRecord], None] | None = None) -> RetryResult:
    policy = policy or RetryPolicy()
    budget = budget or GLOBAL_BUDGET
    rng = rng or _RNG
    safety = OPERATION_CLASSES.get(op)
    if safety is None:
        raise AgentError("AGT-VAL-001", "unclassified operation; refuse to guess retry safety", details={"op": op})
    retry_allowed = safety == "idempotent" or (safety == "keyed" and bool(idempotency_key))
    budget.note_request()
    records: list[AttemptRecord] = []
    for attempt in range(policy.max_attempts):
        ctx.check(clock)
        child = ctx.child(op, policy.per_attempt_timeout, clock)
        child = CallContext(child.deadline, child.cancel, child.trace, ctx.correlation_id, ctx.tenant, ctx.baggage, attempt)
        try:
            value = fn(child)
            rec = AttemptRecord(attempt, None, 0.0, "ok")
            records.append(rec)
            if on_attempt:
                on_attempt(rec)
            return RetryResult(value, records, idempotency_key)
        except BaseException as exc:  # noqa: BLE001 - translated below, never swallowed silently
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            err = translate(exc, ctx.correlation_id)
            last = attempt == policy.max_attempts - 1
            if not err.retryable or not retry_allowed or last:
                rec = AttemptRecord(attempt, err.code, 0.0, "terminal")
                records.append(rec)
                if on_attempt:
                    on_attempt(rec)
                err.details = dict(err.details, attempts=len(records), op=op,
                                   retry_allowed=retry_allowed, exhausted=last and err.retryable)
                raise err
            d = policy.delay(attempt, rng)
            if clock() + d >= ctx.deadline:
                rec = AttemptRecord(attempt, err.code, 0.0, "deadline")
                records.append(rec)
                if on_attempt:
                    on_attempt(rec)
                raise AgentError("AGT-TMO-001", "retry would exceed the caller deadline",
                                 details={"attempts": len(records), "op": op}, correlation_id=ctx.correlation_id, cause=err)
            if not budget.try_spend():
                rec = AttemptRecord(attempt, err.code, 0.0, "budget")
                records.append(rec)
                if on_attempt:
                    on_attempt(rec)
                raise AgentError("AGT-DEP-002", "retry budget exhausted (storm protection)",
                                 details={"attempts": len(records), "op": op}, correlation_id=ctx.correlation_id, cause=err)
            rec = AttemptRecord(attempt, err.code, d, "retry")
            records.append(rec)
            if on_attempt:
                on_attempt(rec)
            ctx.check(clock)
            sleep(d)
    raise AssertionError("unreachable")  # pragma: no cover
