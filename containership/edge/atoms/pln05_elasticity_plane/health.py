"""Health, readiness and stall detection for PLN-05 (MC-15 / MC-24).

States (worst wins): ``failed`` > ``stalled`` > ``unready`` > ``degraded`` > ``healthy``.

* **live** is false only for ``failed`` (the process cannot make decisions at all).
* **ready** is false for ``failed``/``stalled``/``unready``; decisions are not
  published while not ready (the plane refuses at the same predicates).
* **stalled** is progress-based, not heartbeat-based: work is queued and no item
  has been processed for ``health.stall_after_s`` of *monotonic* time.
* Dependency flapping (≥ 4 breaker transitions inside ``health.flap_window_s``)
  is reported as ``degraded`` rather than toggling readiness.

Evaluation reads in-memory state only; it never calls a dependency, so it
cannot block on one.
"""
from __future__ import annotations

ORDER = ("healthy", "degraded", "unready", "stalled", "failed")


def evaluate(plane) -> dict:
    cfg = plane.config.active
    mono = plane.mono()
    now = plane._now()  # also runs the clock-discontinuity detector
    blockers: list[str] = []
    degraded: list[str] = []
    deps: dict[str, str] = {}

    # security dependencies
    active_keys = [k for k in plane.ring._keys.values() if k.active(now)]
    deps["keyring"] = "up" if active_keys else "down"
    if not active_keys:
        blockers.append("R_NO_ACTIVE_KEY")
    deps["trusted_time"] = "down" if plane.time_fault else "up"
    if plane.time_fault:
        blockers.append("R_TIME_FAULT")
    deps["audit_sink"] = "up" if plane.audit.sink_available else "down"
    if plane.audit.pressure >= 1.0:
        blockers.append("R_AUDIT_BUFFER_FULL")
    elif not plane.audit.sink_available:
        degraded.append("R_AUDIT_SINK_DOWN")
    # coordination and sink via breakers
    for name, br in plane.breakers.items():
        deps.setdefault(name, "up" if br.state == "closed" else br.state)
        recent = [t for t, _ in br.transitions if now - t <= cfg.get("health.flap_window_s")]
        if len(recent) >= 4:
            degraded.append(f"R_FLAPPING_{name.upper()}")
    deps["coordination"] = "up" if plane.leases.available and plane.breakers["coordination"].state == "closed" else "down"
    if deps["coordination"] == "down":
        degraded.append("R_COORDINATION_DOWN")
    if plane.state_errors:
        blockers.append("R_STATE_CORRUPT")
    if plane.draining:
        blockers.append("R_DRAINING")
    for s in plane.scopes.values():
        if s.mode in ("stale", "degraded"):
            degraded.append(f"R_SCOPE_{s.mode.upper()}")
            break

    state = "healthy"
    if degraded:
        state = "degraded"
    if blockers:
        state = "unready"
    queued = len(plane.admission)
    if queued and mono - plane.last_progress_mono > cfg.get("health.stall_after_s"):
        state = "stalled"
        blockers.append("R_STALLED")
    if not plane.config.active.checksum:
        state = "failed"
    return {"live": state != "failed", "ready": state in ("healthy", "degraded"), "state": state,
            "blockers": sorted(set(blockers)), "degraded": sorted(set(degraded)),
            "dependencies": deps, "queue_depth": queued, "processed": plane.processed}
