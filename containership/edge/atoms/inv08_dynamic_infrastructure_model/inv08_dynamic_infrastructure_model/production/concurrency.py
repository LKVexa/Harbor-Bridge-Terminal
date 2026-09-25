"""Component 58 - concurrency primitives and race-test targets.

``model.Pool`` is NOT thread-safe: ``tick`` copies ``nodes``, computes, then
commits the copy, so a ``set_busy`` that lands between copy and commit is lost
(demonstrated deterministically in the tests).  Contract: Pool is single-writer.

* ``LockedPool`` - RLock-serialized wrapper exposing tick/set_busy/snapshot.
* ``LeaseTable`` - in-memory lease store double with compare-and-swap on a
  per-lease revision and monotonically increasing fencing tokens per lease and
  leader epochs.  A write carrying a stale fencing token or stale epoch is
  rejected (dual-leader / stale-writer protection).  Real distributed store is
  BLOCKED (component 10 technology selection).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from ..model import Pool
from .core import Inv08Error, Outcome


class LockedPool:
    def __init__(self, pool: Pool) -> None:
        self._pool = pool
        self._lock = threading.RLock()

    def tick(self, now, demand, **kw):
        with self._lock:
            return self._pool.tick(now, demand, **kw)

    def set_busy(self, node_id: str, busy: bool = True) -> None:
        with self._lock:
            self._pool.set_busy(node_id, busy)

    def snapshot(self) -> dict:
        with self._lock:
            return self._pool.snapshot()

    def check_invariants(self) -> list[str]:
        with self._lock:
            p = self._pool
            out = []
            if len(p.nodes) > p.max_nodes:
                out.append("size > max_nodes")
            if len(set(p.nodes)) != len(p.nodes):
                out.append("duplicate ids")
            return out


def _conflict(name: str, msg: str, **d) -> Inv08Error:
    return Inv08Error(code=f"INV08.LEASE.{name}", message=msg, outcome=Outcome.RETRYABLE_FAILURE
                      if name == "CAS_CONFLICT" else Outcome.TERMINAL_FAILURE, details=d)


@dataclass
class Lease:
    node_id: str
    holder: str
    expires: float
    busy: bool
    revision: int
    fence: int


class LeaseTable:
    """Per-tenant lease table double with CAS + fencing; all ops are atomic under a lock."""

    def __init__(self, tenant: str) -> None:
        self.tenant = tenant
        self._lock = threading.Lock()
        self._leases: dict[str, Lease] = {}
        self._fence = 0
        self._epoch = 0
        self.leader: str | None = None

    # -- leader election (epoch-fenced)
    def elect(self, candidate: str) -> int:
        with self._lock:
            self._epoch += 1
            self.leader = candidate
            return self._epoch

    def _check_epoch(self, epoch: int) -> None:
        if epoch != self._epoch:
            raise _conflict("STALE_EPOCH", f"epoch {epoch} is stale (current {self._epoch})",
                            epoch=epoch, current=self._epoch)

    def acquire(self, node_id: str, holder: str, now: float, ttl: float, *, epoch: int) -> Lease:
        with self._lock:
            self._check_epoch(epoch)
            cur = self._leases.get(node_id)
            if cur is not None and cur.expires > now:
                raise _conflict("HELD", f"{node_id} held by {cur.holder}", holder=cur.holder)
            self._fence += 1
            lease = Lease(node_id, holder, now + ttl, False, (cur.revision + 1) if cur else 1, self._fence)
            self._leases[node_id] = lease
            return Lease(**lease.__dict__)

    def cas(self, node_id: str, expected_revision: int, fence: int, *, epoch: int, **changes) -> Lease:
        with self._lock:
            self._check_epoch(epoch)
            cur = self._leases.get(node_id)
            if cur is None:
                raise _conflict("ABSENT", f"{node_id} not leased")
            if fence != cur.fence:
                raise _conflict("STALE_FENCE", f"fence {fence} != {cur.fence}", fence=fence)
            if expected_revision != cur.revision:
                raise _conflict("CAS_CONFLICT", f"revision {expected_revision} != {cur.revision}")
            for k, v in changes.items():
                if k not in {"expires", "busy"}:
                    raise ValueError(f"field {k} not mutable")
                setattr(cur, k, v)
            cur.revision += 1
            return Lease(**cur.__dict__)

    def reclaim_expired(self, now: float, *, epoch: int) -> list[str]:
        """Reclaim idle leases whose expiry passed; busy leases are never reclaimed."""
        with self._lock:
            self._check_epoch(epoch)
            gone = sorted(n for n, lz in self._leases.items() if not lz.busy and lz.expires <= now)
            for n in gone:
                del self._leases[n]
            return gone

    def get(self, node_id: str) -> Lease | None:
        with self._lock:
            lz = self._leases.get(node_id)
            return Lease(**lz.__dict__) if lz else None

    def all(self) -> dict[str, Lease]:
        with self._lock:
            return {k: Lease(**v.__dict__) for k, v in self._leases.items()}
