"""INV-38-C052 — Health/stall detection thresholds with hysteresis."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Thresholds:
    oldest_inflight_warn: float = 0.005
    oldest_inflight_fail: float = 0.050
    min_completion_progress: int = 1     # completions expected per window when ring non-empty
    healthy_samples_to_recover: int = 3

@dataclass
class StallDetector:
    thresholds: Thresholds = field(default_factory=Thresholds)
    state: str = "HEALTHY"
    _healthy_streak: int = 0

    def observe(self, *, oldest_inflight_age: float, completion_delta: int,
                ring_nonempty: bool) -> tuple[str, str]:
        stalled = ring_nonempty and completion_delta < self.thresholds.min_completion_progress
        if oldest_inflight_age >= self.thresholds.oldest_inflight_fail or stalled:
            self.state = "FAILED"; self._healthy_streak = 0
            return self.state, "PK_BYPASS_STALL_DETECTED"
        if oldest_inflight_age >= self.thresholds.oldest_inflight_warn:
            self.state = "DEGRADED"; self._healthy_streak = 0
            return self.state, "PK_BYPASS_LATENCY_WARN"
        # healthy sample; require a streak before declaring recovery (hysteresis)
        self._healthy_streak += 1
        if self.state != "HEALTHY" and self._healthy_streak < self.thresholds.healthy_samples_to_recover:
            return self.state, "PK_BYPASS_RECOVERING"
        self.state = "HEALTHY"
        return self.state, "PK_BYPASS_OK"
