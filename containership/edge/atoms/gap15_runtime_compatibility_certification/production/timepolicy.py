"""Trusted time and clock-skew policy (component 06).

Wall time is only accepted from configured ``TimeSource`` objects ranked by
trust; elapsed-duration logic uses ``time.monotonic`` (MC-06-03). Every
reading carries a confidence class and an uncertainty bound. When required
confidence cannot be established, high-trust certification is refused
(MC-06-04). Rollback / forward jumps are detected against the last accepted
reading and the monotonic delta (MC-06-05).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

HIGH, MEDIUM, LOW, NONE = "high", "medium", "low", "none"
_CONFIDENCE_RANK = {HIGH: 3, MEDIUM: 2, LOW: 1, NONE: 0}


class TimeError_(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class TimeSource:
    name: str
    kind: str  # nts | ntp | ptp | gps | rtc | manual
    read: Callable[[], Optional[int]]
    confidence: str
    uncertainty_s: int


@dataclass(frozen=True)
class TimeReading:
    wall: int
    monotonic: float
    source: str
    confidence: str
    uncertainty_s: int

    def as_dict(self) -> dict:
        return {"wall": self.wall, "source": self.source, "confidence": self.confidence,
                "uncertainty_s": self.uncertainty_s}


@dataclass(frozen=True)
class TimePolicy:
    max_skew_s: int = 5
    max_forward_jump_s: int = 300
    required_confidence: str = MEDIUM
    offline_grace_s: int = 3600


class TrustedClock:
    """Consensus over ranked sources with rollback/jump detection."""

    def __init__(self, sources: list[TimeSource], policy: TimePolicy = TimePolicy(),
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        if not sources:
            raise ValueError("at least one time source is required")
        self.sources = sorted(sources, key=lambda s: -_CONFIDENCE_RANK[s.confidence])
        self.policy = policy
        self._monotonic = monotonic
        self._last: Optional[TimeReading] = None
        self.anomalies: list[dict] = []
        self.metrics = {"time_offset_s": 0, "sources_reachable": 0, "rollback_events": 0,
                        "freshness_rejections": 0}

    def now(self) -> TimeReading:
        mono = self._monotonic()
        readings = []
        for src in self.sources:
            try:
                value = src.read()
            except Exception:  # an unreachable source is simply absent
                value = None
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                readings.append((src, value))
        self.metrics["sources_reachable"] = len(readings)
        if not readings:
            reading = self._holdover(mono)
        else:
            best_src, best = readings[0]
            confidence = best_src.confidence
            spread = max(v for _, v in readings) - min(v for _, v in readings)
            self.metrics["time_offset_s"] = spread
            if spread > self.policy.max_skew_s:
                confidence = LOW  # sources disagree beyond budget
                self.anomalies.append({"type": "skew", "spread_s": spread})
            reading = TimeReading(best, mono, best_src.name, confidence,
                                  max(best_src.uncertainty_s, spread if confidence == LOW else 0))
        self._check_jump(reading)
        self._last = reading
        return reading

    def _holdover(self, mono: float) -> TimeReading:
        if self._last is None:
            return TimeReading(0, mono, "none", NONE, 2**31)
        elapsed = int(mono - self._last.monotonic)
        uncertainty = self._last.uncertainty_s + elapsed // 100 + 1
        confidence = LOW if elapsed <= self.policy.offline_grace_s else NONE
        return TimeReading(self._last.wall + elapsed, mono, "holdover", confidence, uncertainty)

    def _check_jump(self, reading: TimeReading) -> None:
        if self._last is None or reading.source in ("holdover", "none"):
            return
        expected = self._last.wall + (reading.monotonic - self._last.monotonic)
        delta = reading.wall - expected
        if delta < -self.policy.max_skew_s:
            self.metrics["rollback_events"] += 1
            self.anomalies.append({"type": "rollback", "delta_s": int(delta)})
            raise TimeError_("E_TIME_ROLLBACK", f"wall clock moved back {int(-delta)}s")
        if delta > self.policy.max_forward_jump_s:
            self.anomalies.append({"type": "forward_jump", "delta_s": int(delta)})
            raise TimeError_("E_TIME_FORWARD_JUMP", f"wall clock jumped forward {int(delta)}s")

    def require(self, confidence: Optional[str] = None) -> TimeReading:
        reading = self.now()
        needed = confidence or self.policy.required_confidence
        if _CONFIDENCE_RANK[reading.confidence] < _CONFIDENCE_RANK[needed]:
            self.metrics["freshness_rejections"] += 1
            raise TimeError_("E_TIME_UNTRUSTED",
                             f"time confidence {reading.confidence} below required {needed}")
        return reading


def fixed_source(value_ref: list, name: str = "test-nts", confidence: str = HIGH, kind: str = "nts") -> TimeSource:
    """A source that reads ``value_ref[0]`` (test / simulation helper)."""
    return TimeSource(name, kind, lambda: value_ref[0], confidence, 1)


def effective_expiry(tested_at: int, ttl_s: int, *, eol_at: Optional[int] = None,
                     offline_grace_s: int = 0, waiver_until: Optional[int] = None) -> int:
    """One shared TTL/EOL/grace computation for every subsystem (MC-06-06, MC-06-08).

    Offline grace can never extend past hard expiry or EOL unless an explicit
    (already verified) waiver deadline is supplied.
    """
    hard = tested_at + ttl_s
    limit = hard if waiver_until is None else max(hard, waiver_until)
    if eol_at is not None:
        limit = min(limit, eol_at)
    return min(hard + offline_grace_s, limit)
