"""Component 43 - lease-based leader election with monotonic fencing tokens.

Contract ``PK_DYN_LEADER/1``:
* Leadership == holding the ``LEADER_KEY`` lease in ``LeaseStore`` with
  ``expires > now``.  ``ttl`` bounds failover time; a leader must renew at
  intervals < ttl/2 and MUST stop acting once ``now >= expires - safety``.
* The fencing token is the lease ``epoch``: strictly increasing across tenures.
  Every side effect (store write, provider call) carries it; receivers reject
  tokens lower than the highest seen (``FenceGate``) or not equal to the
  current lease epoch (``LeaseStore.check_fence``).
* A second controller cannot acquire while the lease is valid (duplicate
  prevention).  ``detect_split_brain`` resolves concurrent claims: the claim
  matching the store's current epoch wins; every other claimant must step down.
Clock skew is bounded by using a single clock source (the store's ``now``);
multi-node clock-skew bounds are PARTIAL (need the replicated store).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .core import Inv08Error, Outcome
from .leasestore import LeaseStore

LEADER_KEY = "controller/leader"


@dataclass(frozen=True)
class Leadership:
    identity: str
    epoch: int
    expires: float


class LeaderElector:
    def __init__(self, store: LeaseStore, identity: str, *, clock: Callable[[], float],
                 ttl: float = 15.0, safety: float = 1.0, key: str = LEADER_KEY) -> None:
        if not identity:
            raise ValueError("identity required")
        if not 0 <= safety < ttl:
            raise ValueError("need 0 <= safety < ttl")
        self.store, self.identity, self.clock = store, identity, clock
        self.ttl, self.safety, self.key = ttl, safety, key
        self.leadership: Leadership | None = None

    def try_acquire(self) -> Leadership | None:
        now = self.clock()
        rec = self.store.acquire(self.key, self.identity, now=now, ttl=self.ttl)
        if rec is None:
            self.leadership = None
            return None
        self.leadership = Leadership(self.identity, rec.epoch, rec.expires)
        return self.leadership

    def is_leader(self) -> bool:
        lead = self.leadership
        return lead is not None and self.clock() < lead.expires - self.safety

    def require(self) -> Leadership:
        if not self.is_leader():
            raise Inv08Error("INV08.LEADER.NOT_LEADER", f"{self.identity} is not the leader",
                             outcome=Outcome.RETRYABLE_FAILURE, severity="warning",
                             remediation="standby controller; do not act",
                             details={"identity": self.identity})
        return self.leadership  # type: ignore[return-value]

    def step_down(self) -> None:
        if self.leadership is not None:
            self.store.release(self.key, self.identity, self.leadership.epoch, now=self.clock())
        self.leadership = None


class FenceGate:
    """Receiver-side stale-writer guard: remembers the highest token seen and
    rejects anything lower."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.highest = 0
        self.rejected = 0

    def admit(self, token: int) -> None:
        if isinstance(token, bool) or not isinstance(token, int) or token < 1:
            raise Inv08Error("INV08.FENCE.MISSING", f"{self.name}: fencing token required",
                             outcome=Outcome.TERMINAL_FAILURE, details={"token": repr(token)})
        if token < self.highest:
            self.rejected += 1
            raise Inv08Error("INV08.FENCE.STALE", f"{self.name}: stale token {token} < {self.highest}",
                             outcome=Outcome.TERMINAL_FAILURE, severity="critical",
                             remediation="writer has been superseded; it must stop",
                             details={"token": token, "highest": self.highest})
        self.highest = token


def detect_split_brain(store: LeaseStore, claims: list[Leadership], *,
                       key: str = LEADER_KEY) -> dict:
    cur = store.get(key)
    winner = None
    losers = []
    for c in claims:
        if cur is not None and c.identity == cur.holder and c.epoch == cur.epoch:
            winner = c.identity
        else:
            losers.append(c.identity)
    return {"split_brain": len(claims) > 1, "winner": winner, "must_step_down": sorted(losers),
            "current_epoch": cur.epoch if cur else None}
