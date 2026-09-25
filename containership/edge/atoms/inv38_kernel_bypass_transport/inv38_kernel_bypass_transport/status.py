"""INV-38-C071 — Health/readiness/status snapshot for the kernel-bypass transport.

Produces an internally consistent, secret-free status document tied to a single
lifecycle generation.  Separates liveness from readiness (C071-T05) and exposes
dependency freshness and the active capability set.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .lifecycle import CompState, LifecycleMachine
from .transport import BypassQueue

STATUS_SCHEMA_VERSION = "health/1"

# Dependencies whose freshness gates readiness (C071-T02).
DEPENDENCIES = ("identity", "policy", "key", "time", "pk_core", "telemetry_sink")


@dataclass
class DependencyState:
    name: str
    healthy: bool = True
    age_seconds: float = 0.0
    max_age_seconds: float = 30.0

    @property
    def stale(self) -> bool:
        return self.age_seconds > self.max_age_seconds

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "healthy": self.healthy and not self.stale,
            "age_seconds": round(self.age_seconds, 3),
            "stale": self.stale,
        }


@dataclass
class StatusReporter:
    queue: BypassQueue
    lifecycle: LifecycleMachine
    version: str
    build_digest: str
    config_digest: str
    backend: str = "reference-model"
    dependencies: dict[str, DependencyState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in DEPENDENCIES:
            self.dependencies.setdefault(name, DependencyState(name))

    def liveness(self) -> bool:
        return self.lifecycle.state not in (CompState.STOPPED,)

    def readiness(self) -> tuple[bool, str]:
        if self.lifecycle.state not in (CompState.READY, CompState.DEGRADED):
            return False, "PK_BYPASS_NOT_READY_LIFECYCLE"
        for dep in self.dependencies.values():
            if not dep.healthy or dep.stale:
                return False, f"PK_BYPASS_DEP_UNHEALTHY:{dep.name}"
        return True, "PK_BYPASS_READY"

    def snapshot(self) -> dict:
        ready, reason = self.readiness()
        return {
            "schema": STATUS_SCHEMA_VERSION,
            "component": "INV-38",
            "generation": self.lifecycle.generation,
            "observed_at": time.time(),
            "liveness": self.liveness(),
            "readiness": ready,
            "reason_code": reason,
            "lifecycle_state": self.lifecycle.state.value,
            "version": self.version,
            "build_digest": self.build_digest,
            "config_digest": self.config_digest,
            "backend": self.backend,
            "capabilities": {
                "bypass_available": bool(self.queue.available),
                "kernel_fallback": True,
            },
            "resources": {
                "regions": self.queue.region_count,
                "ring_depth": self.queue.ring_depth,
                "completion_depth": self.queue.completion_depth,
                "max_regions": self.queue.max_regions,
                "ring_size": self.queue.ring_size,
                "completion_limit": self.queue.completion_limit,
            },
            "counters": {
                "bounds_violations": self.queue.violations,
                "fallbacks": self.queue.fallbacks,
            },
            "dependencies": [d.to_dict() for d in self.dependencies.values()],
        }
