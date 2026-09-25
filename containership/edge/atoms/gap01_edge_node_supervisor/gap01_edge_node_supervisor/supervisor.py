"""Dependency-free runtime model for GAP-01 Edge Node Supervisor.

This module deliberately depends only on the Python standard library so local
lifecycle/drain logic can be tested even when the wider ``pk_core`` framework
is not installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterable, Mapping

TRANSITIONS: Mapping[str, frozenset[str]] = {
    "joining": frozenset({"ready", "stopped"}),
    "ready": frozenset({"cordoned", "draining", "stopped"}),
    "cordoned": frozenset({"ready", "draining", "stopped"}),
    "draining": frozenset({"stopped", "cordoned"}),
    "stopped": frozenset(),
}
DRAIN_ORDER = ("hostile", "untrusted", "third-party", "first-party", "trusted")
HEALTH_STALENESS_BOUND = 30


class IllegalTransition(ValueError):
    """Raised when a lifecycle transition is not in the state machine."""


class DrainIncomplete(RuntimeError):
    """Raised when a transition would stop a node with resident workloads."""


def _non_negative_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer tick")
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


@dataclass
class NodeSupervisor:
    """Local lifecycle authority for one node.

    The model is deliberately fail-closed: invalid states, time regressions,
    duplicate workload identities, missing health, and stale/future health
    evidence cannot make a node placement-ready.
    """

    node: str
    state: str = "joining"
    workloads: dict[str, str] = field(default_factory=dict)
    health: dict[str, int] = field(default_factory=dict)
    last_reason: str = "initial"
    breaches: list[dict] = field(default_factory=list)
    clock: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.node, str) or not self.node.strip():
            raise ValueError("node name must be non-empty")
        if self.state not in TRANSITIONS:
            raise ValueError(f"{self.node}: invalid initial state {self.state!r}")
        _non_negative_int(self.clock, "clock")
        if any(not isinstance(name, str) or not name for name in self.workloads):
            raise ValueError(f"{self.node}: workload names must be non-empty strings")
        unknown = sorted({v for v in self.workloads.values() if v not in DRAIN_ORDER})
        if unknown:
            raise ValueError(f"{self.node}: unknown trust classes {unknown!r}")
        for signal, seen in self.health.items():
            if not isinstance(signal, str) or not signal:
                raise ValueError(f"{self.node}: health signal names must be non-empty strings")
            _non_negative_int(seen, f"health[{signal!r}]")
            if seen > self.clock:
                self.clock = seen

    def transition(self, to: str, *, reason: str = "") -> str:
        if not isinstance(to, str) or to not in TRANSITIONS:
            raise IllegalTransition(f"{self.node}: unknown target state {to!r}")
        if to not in TRANSITIONS[self.state]:
            raise IllegalTransition(f"{self.node}: {self.state} -> {to} is not a legal transition")
        if to == "stopped" and self.workloads:
            raise DrainIncomplete(
                f"{self.node}: cannot stop with {len(self.workloads)} resident workload(s)"
            )
        self.state = to
        self.last_reason = reason.strip() if isinstance(reason, str) and reason.strip() else to
        return self.state

    @property
    def accepts_placement(self) -> bool:
        return self.state == "ready" and self.healthy_at(self.clock)

    def healthy_at(self, now: int) -> bool:
        now = _non_negative_int(now, "now")
        if not self.health:
            return False
        # Future-dated evidence is invalid, not "extra fresh".
        return all(0 <= now - seen <= HEALTH_STALENESS_BOUND for seen in self.health.values())

    def report_health(self, signal: str, now: int) -> None:
        if not isinstance(signal, str) or not signal.strip():
            raise ValueError(f"{self.node}: health signal name must be non-empty")
        now = _non_negative_int(now, "now")
        if now < self.clock:
            raise ValueError(f"{self.node}: health timestamp regressed from {self.clock} to {now}")
        self.health[signal.strip()] = now
        self.clock = now

    def admit(self, workload: str, trust_class: str) -> None:
        if not isinstance(workload, str) or not workload.strip():
            raise ValueError(f"{self.node}: workload name must be non-empty")
        workload = workload.strip()
        if trust_class not in DRAIN_ORDER:
            raise ValueError(f"{self.node}: unknown trust class {trust_class!r}")
        if workload in self.workloads:
            raise ValueError(f"{self.node}: workload {workload!r} already admitted")
        if not self.accepts_placement:
            raise IllegalTransition(f"{self.node}: does not accept placement while {self.state}")
        self.workloads[workload] = trust_class

    def drain_order(self) -> list[str]:
        return sorted(self.workloads, key=lambda w: (DRAIN_ORDER.index(self.workloads[w]), w))

    def drain(self, *, now: int, deadline: int, stubborn: Iterable[str] = ()) -> dict:
        """Drain resident workloads in trust order and fail closed at deadline."""
        now = _non_negative_int(now, "now")
        deadline = _non_negative_int(deadline, "deadline")
        if now < self.clock:
            raise ValueError(f"{self.node}: drain timestamp regressed from {self.clock} to {now}")
        self.clock = now
        if self.state == "stopped":
            raise IllegalTransition(f"{self.node}: cannot drain a stopped node")
        if self.state != "draining":
            self.transition("draining", reason="drain requested")

        stubborn_set = set(stubborn)
        released: list[str] = []
        remaining: list[str] = []
        for workload in self.drain_order():
            if workload in stubborn_set:
                remaining.append(workload)
                continue
            released.append(workload)
            del self.workloads[workload]

        result = {
            "schema": "PK_DRAIN/1",
            "node": self.node,
            "complete": False,
            "released": released,
            "remaining": remaining,
            "deadline": deadline,
            "observed_at": now,
            "escalation": None,
        }
        if remaining:
            if now > deadline:
                breach = {"at": now, "deadline": deadline, "workloads": list(remaining)}
                # Avoid duplicate breach records when a caller polls repeatedly at the same tick.
                if not self.breaches or self.breaches[-1] != breach:
                    self.breaches.append(breach)
                result["escalation"] = "drain deadline exceeded; node held in draining"
            return result

        self.transition("stopped", reason="drain complete")
        result["complete"] = True
        return result
