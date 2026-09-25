"""Health, readiness, lifecycle and stall detection (checklist component 12, supports 13).

Machine-readable status only: orchestrators read ``HealthMonitor.snapshot()`` (a dict with a
schema id and stable reason codes) and never parse log text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from .errors import Inv20Error

HEALTH_SCHEMA = "INV20_HEALTH/1"


class IllegalTransition(Inv20Error):
    code = "E_ILLEGAL_STATE"


class Phase(str, Enum):
    UNINITIALIZED = "uninitialized"
    CONFIGURING = "configuring"
    READY = "ready"
    DEGRADED = "degraded"
    DRAINING = "draining"
    UNHEALTHY = "unhealthy"
    QUARANTINED = "quarantined"
    STOPPED = "stopped"


TRANSITIONS: Dict[Phase, Set[Phase]] = {
    Phase.UNINITIALIZED: {Phase.CONFIGURING, Phase.STOPPED},
    Phase.CONFIGURING: {Phase.READY, Phase.DEGRADED, Phase.UNHEALTHY, Phase.STOPPED},
    Phase.READY: {Phase.DEGRADED, Phase.DRAINING, Phase.UNHEALTHY, Phase.QUARANTINED, Phase.CONFIGURING},
    Phase.DEGRADED: {Phase.READY, Phase.DRAINING, Phase.UNHEALTHY, Phase.QUARANTINED, Phase.CONFIGURING},
    Phase.DRAINING: {Phase.STOPPED, Phase.UNHEALTHY},
    Phase.UNHEALTHY: {Phase.CONFIGURING, Phase.QUARANTINED, Phase.STOPPED},
    Phase.QUARANTINED: {Phase.CONFIGURING, Phase.STOPPED},
    Phase.STOPPED: set(),
}
ACCEPTS_TRAFFIC = {Phase.READY, Phase.DEGRADED}
TERMINAL = {Phase.STOPPED}
RECOVERABLE = {Phase.DEGRADED, Phase.UNHEALTHY, Phase.QUARANTINED}


@dataclass
class HealthMonitor:
    version: str
    clock: Callable[[], float] = time.monotonic
    stall_after_s: float = 30.0
    queue_saturation: float = 0.9
    drain_max_s: float = 15.0
    mandatory_deps: Tuple[str, ...] = ("config", "policy", "identity")
    phase: Phase = Phase.UNINITIALIZED
    reason: str = "boot"
    changed_at: float = 0.0
    config_revision: Optional[int] = None
    config_digest: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    deps: Dict[str, bool] = field(default_factory=dict)
    heartbeat_at: float = 0.0
    inflight: Dict[str, float] = field(default_factory=dict)      # request id -> last progress
    queue_depth: int = 0
    queue_capacity: int = 1
    drain_started: Optional[float] = None
    transitions: List[Tuple[str, str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.changed_at = self.heartbeat_at = self.clock()

    def transition(self, to: Phase, reason: str) -> None:
        if to not in TRANSITIONS[self.phase]:
            raise IllegalTransition(f"{self.phase.value}->{to.value}")
        self.transitions.append((self.phase.value, to.value, reason))
        self.phase, self.reason, self.changed_at = to, reason, self.clock()
        if to is Phase.DRAINING:
            self.drain_started = self.clock()

    # inputs
    def set_config(self, revision: int, digest: str, valid: bool) -> None:
        self.config_revision, self.config_digest = revision, digest
        self.deps["config"] = valid

    def set_dependency(self, name: str, ok: bool) -> None:
        self.deps[name] = ok

    def beat(self) -> None:
        self.heartbeat_at = self.clock()

    def progress(self, request_id: str) -> None:
        self.inflight[request_id] = self.clock()

    def finished(self, request_id: str) -> None:
        self.inflight.pop(request_id, None)

    # evaluation
    def evaluate(self) -> Phase:
        """Recompute phase from inputs; returns the resulting phase."""
        if self.phase in (Phase.STOPPED, Phase.QUARANTINED, Phase.UNINITIALIZED):
            return self.phase
        if self.phase is Phase.DRAINING:
            if not self.inflight:
                self.transition(Phase.STOPPED, "drained")
            elif self.clock() - (self.drain_started or 0) > self.drain_max_s:
                self.transition(Phase.UNHEALTHY, "drain_stuck")
            return self.phase
        missing = [d for d in self.mandatory_deps if not self.deps.get(d, False)]
        if "config" in missing:
            target, why = Phase.UNHEALTHY, "config_invalid"
        elif missing:
            target, why = Phase.DEGRADED, "dependency_unavailable:" + ",".join(sorted(missing))
        elif self.stalled():
            target, why = Phase.DEGRADED, "request_stalled"
        elif self.queue_depth >= self.queue_saturation * self.queue_capacity:
            target, why = Phase.DEGRADED, "queue_saturated"
        else:
            target, why = Phase.READY, "ok"
        if target is not self.phase:
            if target in TRANSITIONS[self.phase]:
                self.transition(target, why)
            elif self.phase is Phase.UNHEALTHY and target is not Phase.UNHEALTHY:
                self.transition(Phase.CONFIGURING, "recovering")
                if target in TRANSITIONS[self.phase]:
                    self.transition(target, why)
        else:
            self.reason = why
        return self.phase

    def stalled(self) -> List[str]:
        now = self.clock()
        return sorted(r for r, t in self.inflight.items() if now - t > self.stall_after_s)

    @property
    def ready(self) -> bool:
        return self.phase is Phase.READY

    @property
    def live(self) -> bool:
        return self.clock() - self.heartbeat_at <= 3 * self.stall_after_s and self.phase is not Phase.STOPPED

    def begin_drain(self) -> None:
        self.transition(Phase.DRAINING, "drain_requested")

    def quarantine(self, reason: str) -> None:
        self.transition(Phase.QUARANTINED, reason)

    def snapshot(self) -> dict:
        return {"schema": HEALTH_SCHEMA, "version": self.version, "phase": self.phase.value,
                "ready": self.ready, "live": self.live, "accepts_traffic": self.phase in ACCEPTS_TRAFFIC,
                "reason": self.reason, "changed_at": self.changed_at,
                "config": {"revision": self.config_revision, "digest": self.config_digest},
                "dependencies": dict(sorted(self.deps.items())), "capabilities": sorted(self.capabilities),
                "stalled_requests": len(self.stalled()), "queue": {"depth": self.queue_depth,
                                                                    "capacity": self.queue_capacity}}
