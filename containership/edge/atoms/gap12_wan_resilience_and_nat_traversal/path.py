"""Reference path-selection state machine for GAP-12.

This module deliberately has no ``pk_core`` dependency so the networking logic can
be unit-tested in isolation.  It does not implement STUN/TURN/ICE itself; callers
supply a probe function for each declared connection strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
import secrets
from numbers import Real
from typing import Callable

STRATEGIES = ("direct", "hole-punch", "relay")
BACKOFF_BASE = 1
BACKOFF_FACTOR = 2
BACKOFF_CEILING = 60
PROBE_FRESHNESS = 30
ATTEMPT_HISTORY = 64


class Partitioned(RuntimeError):
    """Raised when a peer is partitioned or is still inside its retry window."""


Probe = Callable[[str], object]


def _validate_now(now: Real) -> float:
    if isinstance(now, bool) or not isinstance(now, Real):
        raise TypeError("now must be a finite, non-negative number")
    value = float(now)
    if not math.isfinite(value) or value < 0:
        raise ValueError("now must be a finite, non-negative number")
    return value


@dataclass
class Path:
    """Mutable reachability state for one peer/site pair.

    ``now`` is intentionally supplied by the caller.  Production integrations
    should pass a monotonic clock value rather than wall-clock time.
    """

    peer: str
    strategy: str | None = None
    last_success: float | None = None
    attempts: list[dict[str, object]] = field(default_factory=list)
    failures: int = 0
    retry_at: float | None = None
    partitioned: bool = False
    relay_bytes: int = 0
    last_error: str | None = None
    _jitter_seed: int = field(default_factory=lambda: secrets.randbits(64), repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.peer, str):
            raise TypeError("peer must be a string")
        normalized = self.peer.strip()
        if not normalized:
            raise ValueError("peer must not be empty")
        if len(normalized) > 255:
            raise ValueError("peer must be 255 characters or fewer")
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in normalized):
            raise ValueError("peer must not contain control characters")
        self.peer = normalized

    def backoff(self) -> int:
        """Return the exponential backoff bound before jitter.

        The first exhausted round waits ``BACKOFF_BASE`` seconds, then doubles
        until the declared ceiling is reached.
        """
        if self.failures <= 0:
            return 0
        exponent = min(self.failures - 1, BACKOFF_CEILING.bit_length() + 1)
        return min(BACKOFF_BASE * (BACKOFF_FACTOR ** exponent), BACKOFF_CEILING)

    def retry_delay(self) -> float:
        """Return a bounded per-path jittered retry delay in seconds.

        Equal-jitter in the upper half of the current backoff window avoids zero
        delay hot-loops while de-synchronising peers during a widespread outage.

        v4.3.0: the delay keeps millisecond resolution.  v4.2.0 rounded it up to
        whole seconds with a 1 s floor, so the first retry of EVERY peer landed on
        exactly ``failure_time + 1 s`` (a 10,000-peer fleet simulation put 100 %
        of the fleet in one instant); the jitter only existed from the third round.
        """
        bound = self.backoff()
        if bound <= 0:
            return 0.0
        rng = random.Random(self._jitter_seed ^ self.failures)
        factor = 0.5 + (rng.random() * 0.5)
        return min(float(BACKOFF_CEILING), max(BACKOFF_BASE / 2, round(bound * factor, 3)))

    def healthy_at(self, now: Real) -> bool:
        """Return true only when a successful probe is recent and not from the future."""
        current = _validate_now(now)
        if self.last_success is None:
            return False
        age = current - self.last_success
        return 0 <= age <= PROBE_FRESHNESS

    def _record_attempt(self, strategy: str, now: float, outcome: str, error_type: str | None = None) -> None:
        record: dict[str, object] = {"strategy": strategy, "at": now, "outcome": outcome}
        if error_type:
            record["error_type"] = error_type
        self.attempts.append(record)
        if len(self.attempts) > ATTEMPT_HISTORY:
            del self.attempts[:-ATTEMPT_HISTORY]

    def connect(self, prober: Probe, now: Real) -> dict[str, object]:
        """Escalate through strategies in cost order until one probe succeeds.

        Probe exceptions are treated as strategy failures and recorded by exception
        type only, so one broken transport backend cannot prevent a lower-priority
        fallback and exception messages cannot leak secrets into diagnostics.
        """
        if not callable(prober):
            raise TypeError("prober must be callable")
        current = _validate_now(now)
        if self.retry_at is not None and current < self.retry_at:
            remaining = self.retry_at - current
            raise Partitioned(f"{self.peer}: backing off for {remaining:.3f}s")

        tried: list[str] = []
        for strategy in STRATEGIES:
            tried.append(strategy)
            try:
                succeeded = bool(prober(strategy))
            except Exception as exc:  # transport/plugin failure, not process-control exceptions
                self.last_error = type(exc).__name__
                self._record_attempt(strategy, current, "error", self.last_error)
                continue

            if succeeded:
                self._record_attempt(strategy, current, "success")
                self.strategy = strategy
                self.last_success = current
                self.failures = 0
                self.retry_at = None
                self.partitioned = False
                self.last_error = None
                return {
                    "schema": "PK_PATH_STATE/1",
                    "peer": self.peer,
                    "strategy": strategy,
                    "healthy": True,
                    "partitioned": False,
                    "last_success": current,
                    "retry_at": None,
                    "tried": tried,
                }

            self._record_attempt(strategy, current, "failure")

        self.failures += 1
        self.strategy = None
        self.last_success = None
        self.partitioned = True
        self.last_error = self.last_error or "all_strategies_exhausted"
        delay = self.retry_delay()
        self.retry_at = current + delay
        raise Partitioned(
            f"{self.peer}: all strategies exhausted ({', '.join(STRATEGIES)}); "
            f"next retry in {delay}s"
        )

    def record_relay_bytes(self, count: int) -> int:
        """Account bytes carried while relay is the active path."""
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("relay byte count must be an integer")
        if count < 0:
            raise ValueError("relay byte count must be non-negative")
        if self.strategy != "relay":
            raise RuntimeError("relay byte accounting requires an active relay path")
        self.relay_bytes += count
        return self.relay_bytes

    def state(self, now: Real) -> dict[str, object]:
        current = _validate_now(now)
        healthy = self.healthy_at(current)
        retry_in = 0.0 if self.retry_at is None else max(0.0, self.retry_at - current)
        if healthy:
            status = "healthy"
        elif self.retry_at is not None and current < self.retry_at:
            status = "backing_off"
        elif self.partitioned:
            status = "partitioned"
        elif self.last_success is not None:
            status = "stale"
        else:
            status = "unknown"
        return {
            "schema": "PK_PATH_STATE/1",
            "peer": self.peer,
            "strategy": self.strategy,
            "status": status,
            "healthy": healthy,
            "partitioned": self.partitioned,
            "last_success": self.last_success,
            "failures": self.failures,
            "backoff": self.backoff(),
            "retry_at": self.retry_at,
            "retry_in": retry_in,
            "relay_bytes": self.relay_bytes,
            "last_error": self.last_error,
        }
