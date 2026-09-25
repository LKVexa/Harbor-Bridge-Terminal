"""Production health/readiness/liveness/stall/dependency model (M16).

Produces PK_PROVIDER_HEALTH/1.  ``live`` = the dispatch loop has made progress
within the stall threshold.  ``ready`` = lifecycle serving AND every *required*
dependency ok AND not stalled.  Reason codes are machine-readable; an unknown
dependency status is reported as ``unknown`` and never counted as ok.
"""
from __future__ import annotations

import threading
import time

from ..schemas import check


class HealthModel:
    def __init__(self, contract_id: str, *, stall_after_s: float = 10.0, clock=time.monotonic):
        self.contract_id, self.stall_after_s, self._clock = contract_id, stall_after_s, clock
        self._deps: dict[str, tuple[str, bool]] = {}
        self._beat = clock()
        self._lock = threading.Lock()

    def heartbeat(self) -> None:
        with self._lock:
            self._beat = self._clock()

    def set_dependency(self, name: str, status: str, *, required: bool = True) -> None:
        if status not in ("ok", "degraded", "down", "unknown"):
            status = "unknown"
        with self._lock:
            self._deps[name] = (status, required)

    def report(self, lifecycle_state: str, active_capabilities: list[str] | None = None) -> dict:
        with self._lock:
            reasons = []
            live = (self._clock() - self._beat) <= self.stall_after_s
            if not live:
                reasons.append("DISPATCH_STALLED")
            for n, (s, req) in sorted(self._deps.items()):
                if s != "ok":
                    reasons.append(f"DEP_{n.upper()}_{s.upper()}"[:64])
            required_bad = any(s != "ok" for s, req in self._deps.values() if req)
            optional_bad = any(s != "ok" for s, req in self._deps.values() if not req)
            state = lifecycle_state
            if state in ("ready", "degraded"):
                state = "failed" if not live else ("degraded" if (required_bad or optional_bad) else "ready")
            if lifecycle_state not in ("ready", "degraded"):
                reasons.append(f"LIFECYCLE_{lifecycle_state.upper()}")
            rep = {"schema": "PK_PROVIDER_HEALTH/1", "contract_id": self.contract_id, "state": state,
                   "ready": state == "ready" or (state == "degraded" and not required_bad and live),
                   "live": live, "reasons": reasons[:32], "dependencies": {n: s for n, (s, _) in self._deps.items()},
                   "active_capabilities": list(active_capabilities or []), "checked_at": round(time.time(), 3)}
        check(rep, "pk_provider_health")
        return rep
