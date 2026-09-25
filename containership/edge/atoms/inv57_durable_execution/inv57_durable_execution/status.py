"""Health / readiness / version / config / dependency / capability status (MC-47).

Liveness answers "can this process make progress"; readiness additionally
requires config, the history backend and time source.  Dependency probes are
cached for ``probe_ttl`` seconds so a slow dependency cannot be hammered by
probes.  Nothing tenant-identifying or secret is included.
"""
from __future__ import annotations

import time
from typing import Any, Callable

STATUS_SCHEMA = "INV57_STATUS/1"

CAPABILITIES = (
    "replay", "hash_chained_history", "in_doubt_halt", "sqlite_backend", "lease_fencing",
    "conditional_append", "lifecycle_controls", "effect_protocol", "config_ledger",
    "admission_control", "circuit_breaker", "structured_telemetry",
)
# Declared dependencies; probe callables return (ok: bool, reason_code: str).
REQUIRED_FOR_READY = ("config", "history_backend", "time_source")


class StatusSurface:
    def __init__(self, *, version: str, config_digest: str, config_generation: int,
                 environment: str, site: str, probes: dict[str, Callable[[], tuple[bool, str]]],
                 probe_ttl: float = 5.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.version, self.config_digest, self.config_generation = version, config_digest, config_generation
        self.environment, self.site = environment, site
        self.probes, self.ttl, self.clock = probes, probe_ttl, clock
        self._cache: dict[str, tuple[float, bool, str]] = {}
        self.frozen_reason: str | None = None

    def _probe(self, name: str) -> tuple[bool, str]:
        now = self.clock()
        hit = self._cache.get(name)
        if hit and now - hit[0] < self.ttl:
            return hit[1], hit[2]
        try:
            ok, code = self.probes[name]()
        except Exception as exc:  # a probe that raises is a failed probe, never a crash
            ok, code = False, f"probe_error:{type(exc).__name__}"
        self._cache[name] = (now, ok, code)
        return ok, code

    def liveness(self) -> dict[str, Any]:
        return {"live": True}

    def readiness(self) -> dict[str, Any]:
        reasons = []
        for name in REQUIRED_FOR_READY:
            if name not in self.probes:
                reasons.append(f"{name}:not_configured")
                continue
            ok, code = self._probe(name)
            if not ok:
                reasons.append(f"{name}:{code}")
        if self.frozen_reason:
            reasons.append(f"frozen:{self.frozen_reason}")
        return {"ready": not reasons, "reasons": reasons}

    def document(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        deps = {n: dict(zip(("ok", "code"), self._probe(n))) for n in sorted(self.probes)}
        ready = self.readiness()
        mode = "frozen" if self.frozen_reason else ("ready" if ready["ready"] else "degraded")
        return {
            "schema": STATUS_SCHEMA, "version": self.version, "mode": mode,
            "ready": ready, "live": self.liveness()["live"],
            "config": {"digest": self.config_digest, "generation": self.config_generation},
            "environment": self.environment, "site": self.site,
            "history_schema": "PK_WF_HISTORY_EVENT/2",
            "capabilities": list(CAPABILITIES), "dependencies": deps, **(extra or {}),
        }
