"""INV-38-C053 — Bounded retry with backoff and jitter, gated by retry-safety.

Retries are permitted only for outcomes whose ``Retryability`` allows it
(C053-T01).  Backoff is exponential with bounded jitter; attempts and total
elapsed time are both capped (C053-T03).  Clock and randomness are injectable so
the policy is deterministically testable (C053-T08).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .outcomes import OperationResult, Outcome, Retryability


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.001
    max_delay: float = 0.05
    max_elapsed: float = 0.5
    multiplier: float = 2.0
    jitter: float = 0.5  # fraction of computed delay, +/-

    def backoff(self, attempt: int, rand: float) -> float:
        raw = min(self.max_delay, self.base_delay * (self.multiplier ** (attempt - 1)))
        # rand in [0,1) -> symmetric jitter in [-jitter, +jitter]
        factor = 1.0 + self.jitter * (2.0 * rand - 1.0)
        return max(0.0, raw * factor)


def is_retryable(result: OperationResult) -> bool:
    return result.retryability in (
        Retryability.SAFE,
        Retryability.RETRY_WITH_IDEMPOTENCY_KEY,
        Retryability.RETRY_AFTER_RECONCILIATION,
    )


@dataclass
class RetryLedger:
    attempts: int = 0
    accumulated_delay: float = 0.0
    last_reason: str = ""
    exhausted: bool = False


def run_with_retry(
    op: Callable[[int], OperationResult],
    policy: RetryPolicy,
    *,
    now: Callable[[], float],
    rand: Callable[[], float],
    idempotency_key: str | None = None,
) -> tuple[OperationResult, RetryLedger]:
    """Execute ``op(attempt)`` with bounded retry. ``op`` returns OperationResult.

    RETRY_WITH_IDEMPOTENCY_KEY outcomes require an idempotency_key or they are
    treated as terminal (C053-T05) to avoid duplicate resource allocation.
    """
    ledger = RetryLedger()
    start = now()
    while True:
        ledger.attempts += 1
        result = op(ledger.attempts)
        ledger.last_reason = result.reason_code
        if result.outcome in (Outcome.SUCCESS, Outcome.PARTIAL_SUCCESS, Outcome.DEGRADED):
            return result, ledger
        if not is_retryable(result):
            return result, ledger
        if (result.retryability is Retryability.RETRY_WITH_IDEMPOTENCY_KEY
                and not idempotency_key):
            return result, ledger
        if ledger.attempts >= policy.max_attempts:
            ledger.exhausted = True
            return result, ledger
        delay = policy.backoff(ledger.attempts, rand())
        if (now() - start) + delay > policy.max_elapsed:
            ledger.exhausted = True
            return result, ledger
        ledger.accumulated_delay += delay
