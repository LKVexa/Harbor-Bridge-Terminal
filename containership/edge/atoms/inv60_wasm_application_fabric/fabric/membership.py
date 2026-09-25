"""M13/M42/M48 - failure detection, partitions, leases and fencing.

Heartbeat failure detector: a host is *suspect* after ``suspect_after_s`` with no
heartbeat and *lost* after ``lost_after_s``. Authority to place/fail over is held
by a lease with a monotonically increasing epoch (fencing token); writes carrying
an older epoch are rejected (FENCED). A minority partition cannot acquire the
lease (quorum of voters required), so two sides never both grant authority.
Isolated hosts may keep serving existing workloads for ``isolated_serving_s``
(bounded), but never accept new placements or links. Stalls (a host sending
heartbeats but making no progress) are detected by a progress counter.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .errors import FabricError


@dataclass
class HostHealth:
    last_heartbeat: float
    progress: int = 0
    last_progress_change: float = 0.0


class FailureDetector:
    def __init__(self, suspect_after_s=3.0, lost_after_s=8.0, stall_after_s=10.0, clock=time.monotonic):
        if not 0 < suspect_after_s < lost_after_s:
            raise FabricError("INVALID_ARGUMENT", "require 0 < suspect_after < lost_after")
        self.suspect_after_s, self.lost_after_s, self.stall_after_s = suspect_after_s, lost_after_s, stall_after_s
        self.clock = clock
        self.hosts: dict[str, HostHealth] = {}

    def heartbeat(self, host: str, progress: int | None = None) -> None:
        now = self.clock()
        h = self.hosts.get(host)
        if h is None:
            self.hosts[host] = HostHealth(now, progress or 0, now)
            return
        h.last_heartbeat = now
        if progress is not None and progress != h.progress:
            h.progress, h.last_progress_change = progress, now

    def status(self, host: str) -> str:
        h = self.hosts.get(host)
        if h is None:
            return "unknown"
        age = self.clock() - h.last_heartbeat
        if age >= self.lost_after_s:
            return "lost"
        if age >= self.suspect_after_s:
            return "suspect"
        if self.clock() - h.last_progress_change >= self.stall_after_s:
            return "stalled"
        return "healthy"

    def sweep(self) -> dict[str, str]:
        return {h: self.status(h) for h in sorted(self.hosts)}


@dataclass
class Lease:
    holder: str
    epoch: int
    expires_at: float


class LeaseManager:
    """Quorum lease with fencing tokens across a fixed voter set."""

    def __init__(self, voters: list[str], ttl_s: float = 10.0, clock=time.monotonic):
        if not voters:
            raise FabricError("INVALID_ARGUMENT", "need at least one voter")
        self.voters, self.ttl_s, self.clock = list(voters), ttl_s, clock
        self.lease: Lease | None = None
        self.epoch = 0
        self.highest_seen_epoch = 0

    def acquire(self, candidate: str, reachable_voters: list[str]) -> Lease:
        reach = set(reachable_voters) & set(self.voters)
        if len(reach) * 2 <= len(self.voters):
            raise FabricError("PARTITIONED", "no quorum; authority not granted",
                              detail={"reachable": len(reach), "voters": len(self.voters)})
        now = self.clock()
        if self.lease and self.lease.expires_at > now and self.lease.holder != candidate:
            raise FabricError("FENCED", f"lease held by {self.lease.holder} until expiry")
        if self.lease and self.lease.holder == candidate and self.lease.expires_at > now:
            self.lease.expires_at = now + self.ttl_s
            return self.lease
        self.epoch += 1
        self.lease = Lease(candidate, self.epoch, now + self.ttl_s)
        return self.lease

    def check_fence(self, epoch: int) -> None:
        if self.lease is None or epoch != self.lease.epoch or self.lease.expires_at <= self.clock():
            raise FabricError("FENCED", f"write with epoch {epoch} rejected (current "
                              f"{self.lease.epoch if self.lease else None})")


@dataclass
class PartitionState:
    connected_to_control: bool = True
    isolated_since: float | None = None
    isolated_serving_s: float = 300.0
    clock: object = time.monotonic

    def isolate(self) -> None:
        if self.connected_to_control:
            self.connected_to_control, self.isolated_since = False, self.clock()

    def heal(self) -> None:
        self.connected_to_control, self.isolated_since = True, None

    def mode(self) -> str:
        if self.connected_to_control:
            return "connected"
        if self.clock() - self.isolated_since <= self.isolated_serving_s:
            return "isolated_serving"
        return "isolated_expired"

    def require_new_authority(self) -> None:
        if self.mode() != "connected":
            raise FabricError("PARTITIONED", f"mode {self.mode()}: no new placements or links while isolated")

    def may_serve_existing(self) -> bool:
        return self.mode() in ("connected", "isolated_serving")
