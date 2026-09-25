"""Automated link health: probe cadence, failure/success thresholds with
hysteresis, staleness and flap suppression (MC-042).

The tracker is fed by the WAN-resilience layer (GAP-12) and only ever
*downgrades* optimistically: a link becomes UP again only after
``up_after_successes`` consecutive good probes and never while flapping.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .lifecycle import LINK_TRANSITIONS, LinkState, Machine


@dataclass(frozen=True)
class HealthPolicy:
    probe_interval_s: float = 5.0
    suspect_after_s: float = 10.0
    stale_after_s: float = 30.0
    down_after_failures: int = 3
    up_after_successes: int = 2
    flap_window_s: float = 60.0
    max_flaps: int = 4

    @classmethod
    def from_config(cls, cfg: dict) -> HealthPolicy:
        return cls(**{k: cfg[k] for k in cls.__dataclass_fields__ if k in cfg})


@dataclass
class LinkHealth:
    policy: HealthPolicy
    machine: Machine = field(default_factory=lambda: Machine(LinkState.UNKNOWN, LINK_TRANSITIONS))
    last_probe_at: float | None = None
    last_latency_ms: float | None = None
    failures: int = 0
    successes: int = 0
    flips: deque = field(default_factory=lambda: deque(maxlen=64))

    @property
    def state(self) -> LinkState:
        return self.machine.state

    def routable(self) -> bool:
        return self.state is LinkState.UP or self.state is LinkState.SUSPECT

    def _move(self, target: LinkState, reason: str, at: float) -> None:
        before_routable = self.routable()
        if self.machine.to(target, reason) and before_routable != self.routable():
            self.flips.append(at)
            while self.flips and at - self.flips[0] > self.policy.flap_window_s:
                self.flips.popleft()
            if len(self.flips) >= self.policy.max_flaps and self.machine.can(LinkState.FLAPPING):
                self.machine.to(LinkState.FLAPPING, f"{len(self.flips)} availability flips in {self.policy.flap_window_s}s")

    def probe(self, ok: bool, at: float, latency_ms: float | None = None) -> LinkState:
        self.last_probe_at = at
        if ok:
            self.last_latency_ms = latency_ms
            self.successes += 1
            self.failures = 0
            if self.state is LinkState.FLAPPING:
                while self.flips and at - self.flips[0] > self.policy.flap_window_s:
                    self.flips.popleft()
                if len(self.flips) < self.policy.max_flaps and self.successes >= self.policy.up_after_successes:
                    self.machine.to(LinkState.UP, "flap window cleared")
            elif self.state in (LinkState.UNKNOWN, LinkState.SUSPECT, LinkState.STALE):
                self._move(LinkState.UP, "probe ok", at)
            elif self.state is LinkState.DOWN and self.successes >= self.policy.up_after_successes:
                self._move(LinkState.UP, f"{self.successes} consecutive good probes", at)
        else:
            self.failures += 1
            self.successes = 0
            if self.state is LinkState.FLAPPING:
                pass
            elif self.failures >= self.policy.down_after_failures or self.state is LinkState.UNKNOWN:
                self._move(LinkState.DOWN, f"{self.failures} consecutive failed probes", at)
            elif self.state in (LinkState.UP, LinkState.STALE):
                self._move(LinkState.SUSPECT, "probe failed", at)
        return self.state

    def to_dict(self) -> dict:
        return {"state": self.state.value, "last_probe_at": self.last_probe_at, "last_latency_ms": self.last_latency_ms,
                "failures": self.failures, "successes": self.successes, "flips": list(self.flips)}

    @classmethod
    def from_dict(cls, policy: HealthPolicy, data: dict) -> LinkHealth:
        lh = cls(policy)
        lh.machine.state = LinkState(data["state"])
        lh.last_probe_at, lh.last_latency_ms = data.get("last_probe_at"), data.get("last_latency_ms")
        lh.failures, lh.successes = int(data.get("failures", 0)), int(data.get("successes", 0))
        lh.flips.extend(float(x) for x in data.get("flips", []))
        return lh

    def copy(self) -> LinkHealth:
        return LinkHealth.from_dict(self.policy, self.to_dict())

    def evaluate(self, now: float) -> LinkState:
        """Apply time-based rules: missed probes -> SUSPECT; no data -> STALE."""
        if self.last_probe_at is None:
            return self.state
        age = now - self.last_probe_at
        if age >= self.policy.stale_after_s and self.machine.can(LinkState.STALE):
            self.machine.to(LinkState.STALE, f"no probe for {age:.1f}s")
        elif age >= self.policy.suspect_after_s and self.state is LinkState.UP:
            self.machine.to(LinkState.SUSPECT, f"no probe for {age:.1f}s")
        return self.state
