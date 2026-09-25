"""MC-006 - Distributed coordination / leader fencing (GAP03-LEASE/1).

Model: single elected leader per environment.  Leadership is a lease granted by
a *majority* of lease replicas, each keeping its own durable term record and
using its OWN clock (server time).  Every grant carries a strictly increasing
fencing token (term).  The holder treats leadership as lost at
``acquired_local + ttl - safety_margin`` (skew budget), i.e. before any
replica could grant it to someone else.  Loss of the lease flips the replica
to read-only/not-ready *before* returning control.

Only the leader may: prepare/commit/abort/release claims, mutate topology,
write entitlements.  Any replica may score/explain (read-only).

``LeaseReplica`` is a local reference implementation used for deterministic
tests; a production deployment backs it with a consensus store (etcd/ZK/Raft)
- that integration is a blocked certification item.
"""
from __future__ import annotations

import os
import threading
import time

from . import canonical
from .canonical import readb
from .durable import atomic_write
from .errors import SchedulerError

LEADER_OPS = frozenset({"placement.prepare", "placement.commit", "placement.abort", "placement.release",
                        "topology.mutate", "entitlement.write", "ledger.write"})
READ_OPS = frozenset({"score", "explain", "health"})


class LeaseReplica:
    def __init__(self, path: str, *, clock=time.time):
        self.path, self.clock = path, clock
        self.reachable = {}  # client_id -> bool (partition injection)
        self._lock = threading.Lock()
        if os.path.exists(path):
            self.rec = canonical.loads(readb(path))
        else:
            self.rec = {"term": 0, "holder": None, "expires": 0.0}

    def _persist(self):
        atomic_write(self.path, canonical.dumps({k: (int(v * 1000) / 1000 if isinstance(v, float) else v) for k, v in self.rec.items()}))

    def request(self, client: str, term: int, ttl: float, *, renew: bool) -> dict | None:
        if not self.reachable.get(client, True):
            raise ConnectionError("partitioned")
        with self._lock:
            now = self.clock()
            free = self.rec["holder"] is None or now >= self.rec["expires"]
            if renew:
                if self.rec["holder"] != client or self.rec["term"] != term or now >= self.rec["expires"]:
                    return None
            elif not free or term <= self.rec["term"]:
                return {"denied": True, "term": self.rec["term"]}
            self.rec = {"term": term, "holder": client, "expires": now + ttl}
            self._persist()
            return {"granted": True, "term": term}

    def release(self, client: str, term: int):
        with self._lock:
            if self.rec["holder"] == client and self.rec["term"] == term:
                self.rec = {"term": term, "holder": None, "expires": 0.0}
                self._persist()


class Coordinator:
    def __init__(self, node_id: str, replicas: list[LeaseReplica], *, ttl: float = 10.0, safety_margin: float = 2.0,
                 clock=time.monotonic, on_loss=None, metrics=None, max_attempts: int = 3):
        if safety_margin >= ttl:
            raise ValueError("safety margin must be < ttl")
        self.node_id, self.replicas, self.ttl, self.margin = node_id, replicas, ttl, safety_margin
        self.clock, self.on_loss, self.metrics, self.max_attempts = clock, on_loss, metrics, max_attempts
        self.term, self.deadline, self.role = 0, 0.0, "follower"
        self.draining = False
        self._lock = threading.RLock()

    @property
    def quorum(self) -> int:
        return len(self.replicas) // 2 + 1

    def _ask(self, term, renew):
        oks, seen = 0, 0
        for r in self.replicas:
            try:
                res = r.request(self.node_id, term, self.ttl, renew=renew)
            except ConnectionError:
                continue
            if res and res.get("granted"):
                oks += 1
            elif res and "term" in res:
                seen = max(seen, res["term"])
        return oks, seen

    def acquire(self) -> bool:
        with self._lock:
            if self.draining:
                return False
            start = self.clock()
            seen_max = self.term
            for _ in range(self.max_attempts):  # bounded attempts; no retry storm
                term = seen_max + 1
                oks, seen = self._ask(term, renew=False)
                if oks >= self.quorum:
                    self.term, self.role = term, "leader"
                    self.deadline = start + self.ttl - self.margin
                    self._metric()
                    return True
                for r in self.replicas:  # undo minority grants so they expire harmlessly
                    try:
                        r.release(self.node_id, term)
                    except Exception:
                        pass
                seen_max = max(seen_max, seen, term)
            self._metric()
            return False

    def renew(self) -> bool:
        with self._lock:
            if self.role != "leader":
                return False
            start = self.clock()
            if start >= self.deadline:
                self._lose("expired_before_renew")
                return False
            oks, _ = self._ask(self.term, renew=True)
            if oks >= self.quorum:
                self.deadline = start + self.ttl - self.margin
                return True
            self._lose("renew_quorum_lost")
            return False

    def _lose(self, reason):
        self.role = "follower"
        self.deadline = 0.0
        self._metric()
        if self.on_loss:
            self.on_loss(reason)

    def is_leader(self) -> bool:
        with self._lock:
            if self.role == "leader" and self.clock() >= self.deadline:
                self._lose("lease_expired")
            return self.role == "leader"

    def fence(self) -> int:
        """Fencing token for a protected write; raises NOT_LEADER when lease is not held."""
        if not self.is_leader():
            raise SchedulerError("NOT_LEADER", "lease not held")
        return self.term

    def authorize(self, op: str) -> int | None:
        if op in READ_OPS:
            return None
        if op in LEADER_OPS:
            return self.fence()
        raise SchedulerError("INVALID_ARGUMENT", f"unknown coordinated op {op}")

    def drain(self):
        """Graceful handover: stop acquiring, release the lease (term never reused)."""
        with self._lock:
            self.draining = True
            if self.role == "leader":
                for r in self.replicas:
                    try:
                        r.release(self.node_id, self.term)
                    except Exception:
                        pass
                self._lose("drained")

    def status(self) -> dict:
        leader = self.is_leader()
        return {"node": self.node_id, "role": "leader" if leader else "follower", "term": self.term,
                "fencing_token": self.term if leader else None,
                "lease_remaining_s": max(0.0, round(self.deadline - self.clock(), 3)) if leader else 0.0,
                "quorum": self.quorum, "replicas": len(self.replicas), "draining": self.draining}

    def _metric(self):
        if self.metrics:
            self.metrics.set("gap03_coordination_is_leader", 1 if self.role == "leader" else 0)
            self.metrics.set("gap03_coordination_term", self.term)
