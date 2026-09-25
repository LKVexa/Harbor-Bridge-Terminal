"""Lifecycle state machines (MC-007) and degraded-operation modes (MC-046).

Every transition not listed is illegal and raises; transitions are recorded
with a reason so operators can reconstruct why an entity is in its state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, TypeVar

S = TypeVar("S", bound=Enum)


class IllegalTransition(ValueError):
    pass


class NodeState(str, Enum):
    DISCOVERED = "discovered"
    ACTIVE = "active"
    DRAINING = "draining"
    QUARANTINED = "quarantined"
    RETIRED = "retired"


class LinkState(str, Enum):
    UNKNOWN = "unknown"
    UP = "up"
    SUSPECT = "suspect"
    DOWN = "down"
    STALE = "stale"
    FLAPPING = "flapping"


class SiteState(str, Enum):
    CONNECTED = "connected"
    SUSPECT = "suspect"
    PARTITIONED = "partitioned"
    RECOVERING = "recovering"


class CoordinatorState(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


NODE_TRANSITIONS = {
    NodeState.DISCOVERED: {NodeState.ACTIVE, NodeState.QUARANTINED, NodeState.RETIRED},
    NodeState.ACTIVE: {NodeState.DRAINING, NodeState.QUARANTINED},
    NodeState.DRAINING: {NodeState.RETIRED, NodeState.QUARANTINED, NodeState.ACTIVE},
    NodeState.QUARANTINED: {NodeState.ACTIVE, NodeState.RETIRED},
    NodeState.RETIRED: set(),
}
LINK_TRANSITIONS = {
    LinkState.UNKNOWN: {LinkState.UP, LinkState.DOWN, LinkState.STALE},
    LinkState.UP: {LinkState.SUSPECT, LinkState.DOWN, LinkState.STALE, LinkState.FLAPPING},
    LinkState.SUSPECT: {LinkState.UP, LinkState.DOWN, LinkState.STALE, LinkState.FLAPPING},
    LinkState.DOWN: {LinkState.UP, LinkState.STALE, LinkState.FLAPPING},
    LinkState.STALE: {LinkState.UP, LinkState.DOWN, LinkState.SUSPECT},
    LinkState.FLAPPING: {LinkState.DOWN, LinkState.UP, LinkState.STALE},
}
SITE_TRANSITIONS = {
    SiteState.CONNECTED: {SiteState.SUSPECT, SiteState.PARTITIONED},
    SiteState.SUSPECT: {SiteState.CONNECTED, SiteState.PARTITIONED},
    SiteState.PARTITIONED: {SiteState.RECOVERING},
    SiteState.RECOVERING: {SiteState.CONNECTED, SiteState.PARTITIONED},
}
COORDINATOR_TRANSITIONS = {
    CoordinatorState.FOLLOWER: {CoordinatorState.CANDIDATE},
    CoordinatorState.CANDIDATE: {CoordinatorState.LEADER, CoordinatorState.FOLLOWER},
    CoordinatorState.LEADER: {CoordinatorState.FOLLOWER},
}


@dataclass
class Machine(Generic[S]):
    state: S
    table: dict
    history: list[tuple[str, str, str]] = field(default_factory=list)
    max_history: int = 64

    def can(self, target: S) -> bool:
        return target == self.state or target in self.table[self.state]

    def to(self, target: S, reason: str) -> bool:
        """Transition; returns True if the state changed.  Self-transitions are no-ops."""
        if target == self.state:
            return False
        if target not in self.table[self.state]:
            raise IllegalTransition(f"{self.state.value} -> {target.value} is not a legal transition")
        self.history.append((self.state.value, target.value, reason))
        del self.history[:-self.max_history]
        self.state = target
        return True


class Mode(str, Enum):
    NORMAL = "normal"
    PARTITIONED_LOCAL = "partitioned_local"   # site cannot reach its cloud: on-site answers only
    STALE_DATA = "stale_data"                 # some latency data older than stale_after_s
    FROZEN = "frozen"                         # operator froze automated decisions
    NOT_READY = "not_ready"                   # no active configuration


#: Allowed operations per mode (MC-046).  "resolve" in STALE_DATA answers with
#: outcome=degraded; FROZEN blocks automated state changes but keeps reads.
ALLOWED: dict[Mode, frozenset[str]] = {
    Mode.NORMAL: frozenset({"graph.apply", "graph.get", "nearest.resolve", "partition.status", "partition.acquire",
                            "partition.renew", "partition.validate_token"}),
    Mode.PARTITIONED_LOCAL: frozenset({"graph.apply", "graph.get", "nearest.resolve", "partition.status",
                                       "partition.acquire", "partition.renew", "partition.validate_token"}),
    Mode.STALE_DATA: frozenset({"graph.apply", "graph.get", "nearest.resolve", "partition.status", "partition.acquire",
                                "partition.renew", "partition.validate_token"}),
    Mode.FROZEN: frozenset({"graph.get", "nearest.resolve", "partition.status", "partition.renew",
                            "partition.validate_token"}),
    Mode.NOT_READY: frozenset(),
}
