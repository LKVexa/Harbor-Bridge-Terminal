"""Health signal registry and aggregation policy (9).

Signals are declared, not discovered: an unregistered signal is rejected
(anti-spoofing).  Each signal has a required/optional flag, its own staleness
bound, and a set of callers allowed to report it (trust provenance).  The
aggregate is ``healthy`` only when every required signal is fresh and passing
and the optional quorum is met.  Missing evidence is never health.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import SupervisorError


@dataclass(frozen=True)
class SignalSpec:
    name: str
    required: bool = True
    staleness_s: int = 30
    reporters: frozenset[str] = frozenset()  # empty = any authenticated reporter


@dataclass
class Observation:
    ok: bool
    at: int
    reporter: str


@dataclass
class HealthRegistry:
    max_signals: int = 64
    optional_quorum: float = 0.5
    specs: dict[str, SignalSpec] = field(default_factory=dict)
    observations: dict[str, Observation] = field(default_factory=dict)

    def register(self, spec: SignalSpec) -> None:
        if not spec.name or len(spec.name) > 128:
            raise SupervisorError("E_BAD_REQUEST", "signal name must be 1..128 chars")
        if spec.name not in self.specs and len(self.specs) >= self.max_signals:
            raise SupervisorError("E_CAPACITY", "health signal ceiling reached")
        if spec.staleness_s <= 0:
            raise SupervisorError("E_CONFIG", "staleness must be positive")
        self.specs[spec.name] = spec

    def report(self, name: str, ok: bool, at: int, reporter: str) -> None:
        spec = self.specs.get(name)
        if spec is None:
            raise SupervisorError("E_BAD_REQUEST", f"unregistered signal {name!r}")
        if spec.reporters and reporter not in spec.reporters:
            raise SupervisorError("E_FORBIDDEN", f"{reporter} may not report {name}")
        if not isinstance(ok, bool):
            raise SupervisorError("E_BAD_REQUEST", "ok must be boolean")
        prev = self.observations.get(name)
        if prev is not None and at < prev.at:
            raise SupervisorError("E_STALE_REQUEST", f"{name} observation regressed")
        self.observations[name] = Observation(ok, at, reporter)

    def evaluate(self, now: int) -> dict:
        contributing: list[dict] = []
        failing: list[str] = []
        stale: list[str] = []
        missing: list[str] = []
        opt_total = opt_ok = 0
        for name, spec in sorted(self.specs.items()):
            obs = self.observations.get(name)
            if obs is None:
                state = "missing"
            elif obs.at > now or now - obs.at > spec.staleness_s:
                state = "stale"
            elif not obs.ok:
                state = "failing"
            else:
                state = "ok"
            contributing.append({"signal": name, "required": spec.required, "state": state,
                                 "at": obs.at if obs else None,
                                 "reporter": obs.reporter if obs else None})
            if spec.required:
                {"missing": missing, "stale": stale, "failing": failing}.get(state, []).append(name)
            else:
                opt_total += 1
                opt_ok += state == "ok"
        quorum_ok = opt_total == 0 or (opt_ok / opt_total) >= self.optional_quorum
        required_present = any(s.required for s in self.specs.values())
        healthy = required_present and not (missing or stale or failing) and quorum_ok
        return {
            "schema": "PK_NODE_HEALTH/1",
            "healthy": healthy,
            "evaluated_at": now,
            "reasons": ([] if healthy else
                        [*(f"missing:{n}" for n in missing), *(f"stale:{n}" for n in stale),
                         *(f"failing:{n}" for n in failing)]
                        + ([] if quorum_ok else ["optional-quorum"])
                        + ([] if required_present else ["no-required-signals"])),
            "signals": contributing,
        }
