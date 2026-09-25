"""Replication, leader election by lease, and epoch fencing (components 49, 50, 55, 60).

Reference model (single process, pluggable transport): a :class:`FencingAuthority`
issues strictly increasing epochs with a lease.  A :class:`ReplicaNode` accepts writes
only while it holds the current epoch; followers reject any replicate/append carrying an
epoch lower than the highest they have seen, so a partitioned stale leader cannot corrupt
the log after failover (split-brain protection).  Commit = acknowledged by a quorum
(``min_insync``); a write that cannot reach quorum is reported RETRYABLE and is not
exposed to consumers (high-watermark semantics).

Residency: each node carries a ``site``; ``failover()`` refuses candidates outside the
partition's allowed sites (component 55) and prefers the most caught-up in-sync replica.
Real network transport and cross-host clock behaviour are UNVERIFIED (see evidence).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable

from .errors import FENCED, INVALID_ARGUMENT, NOT_LEADER, PARTITION_UNAVAILABLE, BrokerError


@dataclass
class Lease:
    holder: str
    epoch: int
    expires_at: float


class FencingAuthority:
    def __init__(self, lease_s: float = 10.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.lease_s, self.clock = lease_s, clock
        self._epoch = 0
        self._lease: Lease | None = None
        self._lock = RLock()

    def acquire(self, node: str) -> Lease:
        with self._lock:
            now = self.clock()
            if self._lease and self._lease.holder != node and self._lease.expires_at > now:
                raise BrokerError(NOT_LEADER, "lease held by another node", holder=self._lease.holder)
            if self._lease and self._lease.holder == node and self._lease.expires_at > now:
                self._lease.expires_at = now + self.lease_s
                return self._lease
            self._epoch += 1
            self._lease = Lease(node, self._epoch, now + self.lease_s)
            return self._lease

    def revoke(self) -> None:
        with self._lock:
            self._lease = None

    @property
    def epoch(self) -> int:
        return self._epoch


@dataclass
class ReplicaNode:
    name: str
    site: str
    log: list[tuple[int, str, Any]] = field(default_factory=list)  # (epoch, key, value)
    seen_epoch: int = 0
    up: bool = True

    def replicate(self, epoch: int, offset: int, key: str, value: Any) -> None:
        if not self.up:
            raise BrokerError(PARTITION_UNAVAILABLE, "replica down", node=self.name)
        if epoch < self.seen_epoch:
            raise BrokerError(FENCED, epoch=epoch, seen=self.seen_epoch, node=self.name)
        self.seen_epoch = epoch
        if offset < len(self.log):          # divergent suffix from a deposed leader: truncate
            del self.log[offset:]
        if offset != len(self.log):
            raise BrokerError(PARTITION_UNAVAILABLE, "replica gap; needs catch-up", node=self.name)
        self.log.append((epoch, key, value))


class ReplicatedPartition:
    def __init__(self, nodes: list[ReplicaNode], authority: FencingAuthority, *, min_insync: int = 2,
                 allowed_sites: set[str] | None = None) -> None:
        if not (1 <= min_insync <= len(nodes)):
            raise BrokerError(INVALID_ARGUMENT, "min_insync must be 1..len(nodes)")
        self.nodes = {n.name: n for n in nodes}
        self.authority = authority
        self.min_insync = min_insync
        self.allowed_sites = allowed_sites
        self.leader: str | None = None
        self.epoch = 0
        self.high_watermark = 0
        self._lock = RLock()

    def elect(self, name: str) -> int:
        node = self.nodes[name]
        if self.allowed_sites is not None and node.site not in self.allowed_sites:
            raise BrokerError(INVALID_ARGUMENT, "candidate violates residency policy", site=node.site)
        lease = self.authority.acquire(name)
        with self._lock:
            self.leader, self.epoch = name, lease.epoch
            node.seen_epoch = max(node.seen_epoch, lease.epoch)
            # new leader's log is authoritative up to its length; HW cannot exceed it
            self.high_watermark = min(self.high_watermark, len(node.log))
        return lease.epoch

    def append(self, key: str, value: Any, *, as_node: str | None = None, epoch: int | None = None) -> int:
        """Append through ``as_node`` using ``epoch`` (defaults: current leader/epoch).

        Passing an old ``epoch`` simulates a deposed leader that still believes it leads.
        """
        with self._lock:
            leader = as_node or self.leader
            ep = self.epoch if epoch is None else epoch
            if leader is None:
                raise BrokerError(NOT_LEADER, "no leader elected")
            lnode = self.nodes[leader]
            if ep < lnode.seen_epoch or ep < self.authority.epoch:
                raise BrokerError(FENCED, epoch=ep, current=self.authority.epoch, node=leader)
            offset = len(lnode.log)
            lnode.replicate(ep, offset, key, value)
            acks = 1
            for n in self.nodes.values():
                if n.name == leader:
                    continue
                try:
                    n.replicate(ep, offset, key, value)
                    acks += 1
                except BrokerError as e:
                    if e.code is FENCED:
                        raise
            if acks < self.min_insync:
                raise BrokerError(PARTITION_UNAVAILABLE, "insufficient in-sync replicas", acks=acks,
                                  required=self.min_insync)
            self.high_watermark = offset + 1
            return offset

    def read_committed(self, node: str | None = None) -> list[tuple[str, Any]]:
        n = self.nodes[node or self.leader]  # type: ignore[index]
        return [(k, v) for _, k, v in n.log[: self.high_watermark]]

    def failover(self) -> str:
        """Promote the most caught-up live replica in an allowed site."""
        self.authority.revoke()
        candidates = [n for n in self.nodes.values() if n.up and n.name != self.leader and
                      (self.allowed_sites is None or n.site in self.allowed_sites)]
        if not candidates:
            raise BrokerError(PARTITION_UNAVAILABLE, "no eligible failover candidate")
        best = max(candidates, key=lambda n: (len(n.log), n.name))
        self.elect(best.name)
        return best.name
