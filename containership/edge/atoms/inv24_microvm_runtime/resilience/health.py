"""Liveness/readiness, VMM heartbeat and guest stall detection (MC-027)."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ProbeResult:
    name: str
    ok: bool
    detail: str = ""
    latency_ms: float = 0.0


@dataclass
class HealthReport:
    live: bool
    ready: bool
    probes: list[ProbeResult]
    stalled: list[str] = field(default_factory=list)
    mode: str = "normal"

    def to_dict(self) -> dict:
        return {"schema": "PK_MICROVM_HEALTH/1", "live": self.live, "ready": self.ready, "mode": self.mode,
                "stalled": self.stalled[:100],
                "probes": [{"name": p.name, "ok": p.ok, "detail": p.detail[:200], "latency_ms": round(p.latency_ms, 2)}
                           for p in self.probes]}


class HealthMonitor:
    """Readiness = all *required* dependency probes pass and not quarantined/frozen.

    Heartbeats: each supervised VMM/guest agent calls ``beat(instance)``; an
    instance whose last beat is older than ``stall_after_s`` is reported stalled.
    """

    def __init__(self, *, stall_after_s: float = 5.0, probe_timeout_s: float = 1.0, clock=time.monotonic) -> None:
        self.stall_after_s, self.probe_timeout_s, self.clock = stall_after_s, probe_timeout_s, clock
        self._probes: dict[str, tuple[Callable[[], bool], bool]] = {}
        self._beats: dict[str, float] = {}
        self._lock = threading.Lock()
        self.mode_fn: Callable[[], str] = lambda: "normal"

    def register(self, name: str, fn: Callable[[], bool], *, required: bool = True) -> None:
        self._probes[name] = (fn, required)

    def beat(self, instance: str) -> None:
        with self._lock:
            self._beats[instance] = self.clock()

    def forget(self, instance: str) -> None:
        with self._lock:
            self._beats.pop(instance, None)

    def stalled(self) -> list[str]:
        now = self.clock()
        with self._lock:
            return sorted(i for i, t in self._beats.items() if now - t > self.stall_after_s)

    def _run(self, name: str, fn: Callable[[], bool]) -> ProbeResult:
        box: list = []
        start = time.monotonic()
        t = threading.Thread(target=lambda: box.append(_safe(fn)), daemon=True)
        t.start()
        t.join(self.probe_timeout_s)
        lat = (time.monotonic() - start) * 1000
        if not box:
            return ProbeResult(name, False, "probe timed out", lat)
        ok, detail = box[0]
        return ProbeResult(name, ok, detail, lat)

    def report(self) -> HealthReport:
        results = [self._run(n, fn) for n, (fn, _) in sorted(self._probes.items())]
        required_ok = all(r.ok for r in results if self._probes[r.name][1])
        mode = self.mode_fn()
        return HealthReport(True, required_ok and mode == "normal", results, self.stalled(), mode)


def _safe(fn) -> tuple[bool, str]:
    try:
        return bool(fn()), ""
    except Exception as exc:  # a probe crash is a failed probe, never a crashed monitor
        return False, f"{type(exc).__name__}: {getattr(exc, 'code', exc)}"
