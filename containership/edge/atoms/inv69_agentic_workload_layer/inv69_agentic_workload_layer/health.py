"""Watchdog / stall detection (C052) and the status report (C071).

Health is multi-dimensional; readiness is per work class (``new_runs``,
``side_effect_tools``, ``readonly_tools``, ``approvals``) with stable reason
codes, never one boolean.  Watchdog actions are advisory records plus the
admission switch; the watchdog never re-executes work, so it cannot duplicate
side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import os
import platform
import threading
import time

HEALTH_DIMENSIONS = ("liveness", "worker_progress", "queue_age", "run_progress", "dependency", "audit_writer",
                     "sandbox_startup", "approval_response")
ACTIONS = {"warning": "alert_only", "critical_run_stall": "cancel_run", "critical_queue_age": "reject_new_work",
           "critical_audit_writer": "reject_new_work", "critical_dependency": "reject_new_work"}
REASON_CODES = {
    "HLT-OK": "healthy",
    "HLT-STALL-WARN": "a run has made no progress for longer than stall_warning_s",
    "HLT-STALL-CRIT": "a run has made no progress for longer than stall_critical_s",
    "HLT-QUEUE-WARN": "oldest admission wait exceeds queue_age_warning_s",
    "HLT-QUEUE-CRIT": "oldest admission wait exceeds queue_age_critical_s",
    "HLT-DEP-DOWN": "a critical dependency is down or stale",
    "HLT-AUDIT-STALL": "audit writer has not progressed",
    "HLT-OFFLINE": "connectivity offline; online-only capabilities blocked",
    "HLT-CONTAINED": "operator containment active (new runs disabled)",
    "HLT-SEALED": "an agent audit stream is sealed",
}


@dataclass
class Beat:
    run_id: str
    last_progress: float
    expected_max_s: float | None      # per-tool expectation for legitimately long tools
    label: str = ""


class Watchdog:
    def __init__(self, *, warning_s: float, critical_s: float, queue_warn_s: float, queue_crit_s: float,
                 clock=time.monotonic):
        self.warning_s, self.critical_s = warning_s, critical_s
        self.queue_warn_s, self.queue_crit_s = queue_warn_s, queue_crit_s
        self._clock = clock
        self._beats: dict[str, Beat] = {}
        self._lock = threading.Lock()
        self.last_audit_progress = clock()

    def heartbeat(self, run_id: str, *, expected_max_s: float | None = None, label: str = "") -> None:
        with self._lock:
            self._beats[run_id] = Beat(run_id, self._clock(), expected_max_s, label)

    def done(self, run_id: str) -> None:
        with self._lock:
            self._beats.pop(run_id, None)

    def audit_progress(self) -> None:
        self.last_audit_progress = self._clock()

    def evaluate(self, queue_age_s: float = 0.0) -> list[dict[str, Any]]:
        now = self._clock()
        findings = []
        with self._lock:
            beats = list(self._beats.values())
        for b in beats:
            idle = now - b.last_progress
            crit = max(self.critical_s, b.expected_max_s or 0.0)
            warn = max(self.warning_s, (b.expected_max_s or 0.0) * 0.8)
            if idle >= crit:
                findings.append({"code": "HLT-STALL-CRIT", "run_id": b.run_id, "idle_s": round(idle, 3),
                                 "action": ACTIONS["critical_run_stall"]})
            elif idle >= warn:
                findings.append({"code": "HLT-STALL-WARN", "run_id": b.run_id, "idle_s": round(idle, 3),
                                 "action": ACTIONS["warning"]})
        if queue_age_s >= self.queue_crit_s:
            findings.append({"code": "HLT-QUEUE-CRIT", "age_s": queue_age_s, "action": ACTIONS["critical_queue_age"]})
        elif queue_age_s >= self.queue_warn_s:
            findings.append({"code": "HLT-QUEUE-WARN", "age_s": queue_age_s, "action": ACTIONS["warning"]})
        return findings

    def thresholds(self) -> dict[str, float]:
        return {"stall_warning_s": self.warning_s, "stall_critical_s": self.critical_s,
                "queue_age_warning_s": self.queue_warn_s, "queue_age_critical_s": self.queue_crit_s}


def build_status(*, version: str, build_id: str, config, trust_snapshot: Mapping[str, Any], admission: Mapping[str, Any],
                 findings: list[dict], contained: bool, sealed_agents: int, telemetry_ids: Mapping[str, Any],
                 lineage: Mapping[str, Any], audience: str = "operator", trust_probe=None, peers=None) -> dict[str, Any]:
    """Assemble PK_AGENT_STATUS/1.  ``audience='public'`` returns only liveness/readiness/version."""
    reasons = sorted({f["code"] for f in findings})
    deps = trust_snapshot["dependencies"]
    from .trust import DEPENDENCY_MATRIX
    crit_down = [n for n, d in deps.items() if DEPENDENCY_MATRIX[n]["critical"] and d["health"] != "up"]
    if crit_down:
        reasons.append("HLT-DEP-DOWN")
    if trust_snapshot["connectivity"] != "online":
        reasons.append("HLT-OFFLINE")
    if contained:
        reasons.append("HLT-CONTAINED")
    if sealed_agents:
        reasons.append("HLT-SEALED")
    probe = trust_probe or (lambda phase: (True, ""))
    online = trust_snapshot["connectivity"] == "online"
    reject_new = contained or any(f["action"] == "reject_new_work" for f in findings)
    readiness = {
        "new_runs": not reject_new and probe("admission")[0],
        "readonly_tools": not contained and probe("tool_execution")[0],
        "side_effect_tools": not reject_new and online and probe("tool_execution")[0] and probe("approval")[0],
        "approvals": online and probe("approval")[0],
    }
    status = {
        "schema": "PK_AGENT_STATUS/1",
        "live": True,
        "ready": readiness,
        "version": version,
        "reasons": sorted(set(reasons)) or ["HLT-OK"],
    }
    if audience == "public":
        return status
    status.update({
        "build_id": build_id,
        "profile": config.profile["context"],
        "config": {"digest": config.digest, "layers": [list(l) for l in config.layers]},
        "capabilities": sorted(config.capabilities() - set(trust_snapshot["blocked_capabilities"])),
        "blocked_capabilities": trust_snapshot["blocked_capabilities"],
        "dependencies": deps,
        "connectivity": trust_snapshot["connectivity"],
        "admission": dict(admission),
        "health_findings": findings,
        "thresholds_source": "effective configuration (health.*)",
        "telemetry": dict(telemetry_ids),
        "lineage": dict(lineage),
        "peers": dict(peers or {}),
        "runtime": {"python": platform.python_version(), "machine": platform.machine(), "pid": os.getpid()},
    })
    return status
