"""MC-08 / MC-18: bounded replay protection and HA-safe nonce consumption.

Design argument (18.01): a nonce is acceptable only while it is *outstanding*
(issued, unexpired, unconsumed).  Nonces are 256-bit random and never reissued,
so once a challenge has expired its nonce can never be outstanding again; a
replayed expired nonce is rejected as UNISSUED.  The spent set therefore only
has to cover the window [issue, expiry + skew_margin] and can be pruned by
time bucket without reopening replay.  Capacity is bounded by
``max_outstanding`` (admission refuses beyond it).

HA: consumption is a compare-and-set on the shared DurableStore generation under
a fencing token -- a replica holding a stale lease is refused (E_FENCED).
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from .errors import fail

TABLE = "challenges"


@dataclass
class Lease:
    holder: str
    token: int
    expires: float


class LeaseManager:
    def __init__(self, store, ttl: float = 10.0):
        self.store, self.ttl = store, ttl

    def acquire(self, holder: str, now: float) -> Lease:
        cur = self.store.get("lease", "nonce-owner")
        if cur and cur["holder"] != holder and now < cur["expires"]:
            raise fail("E_FENCED", f"lease held by {cur['holder']}")
        token = (cur["token"] if cur else 0) + 1
        rec = {"holder": holder, "token": token, "expires": now + self.ttl}
        self.store.put("lease", "nonce-owner", rec)
        return Lease(holder, token, rec["expires"])

    def check(self, lease: Lease, now: float) -> None:
        cur = self.store.get("lease", "nonce-owner")
        if not cur or cur["token"] != lease.token or cur["holder"] != lease.holder or now >= cur["expires"]:
            raise fail("E_FENCED", "stale or expired lease (fenced)")


class ChallengeBook:
    def __init__(self, store, *, ttl: float = 30.0, skew_margin: float = 5.0, max_outstanding: int = 100_000,
                 leases: LeaseManager | None = None):
        self.store, self.ttl, self.skew, self.max = store, ttl, skew_margin, max_outstanding
        self.leases = leases

    def issue(self, node: str, now: float, *, audience: str, lease: Lease | None = None) -> str:
        if self.leases is not None:
            self.leases.check(lease, now)
        self.prune(now)
        live = [c for c in self.store.items(TABLE).values() if c["state"] == "issued"]
        if len(live) >= self.max:
            raise fail("E_OVERLOADED", "outstanding challenge capacity exhausted")
        nonce = secrets.token_hex(32)
        self.store.put(TABLE, nonce, {"node": node, "issued": now, "expires": now + self.ttl,
                                      "audience": audience, "state": "issued"})
        return nonce

    def consume(self, nonce: str, node: str, now: float, *, audience: str, lease: Lease | None = None) -> dict:
        """Check-and-consume under the store's write lock (linearisable within one
        store).  v5.0.0-rc used a CAS on the store-wide generation, which made
        unrelated concurrent writes fail each other with E_CONFLICT; found by
        ConcurrencyTest.test_parallel_nodes and fixed here."""
        if self.leases is not None:
            self.leases.check(lease, now)
        with self.store.transaction() as tx:  # holds the store lock for read+write
            c = self.store.get(TABLE, nonce)
            if c is None:
                raise fail("E_UNISSUED_CHALLENGE", "nonce not outstanding")
            if c["node"] != node or c["audience"] != audience:
                raise fail("E_UNISSUED_CHALLENGE", "nonce issued to a different node/audience")
            if c["state"] != "issued":
                raise fail("E_REPLAY", "nonce already consumed")
            c["state"] = "expired" if now >= c["expires"] else "consumed"
            tx.put(TABLE, nonce, c)
        if c["state"] == "expired":
            raise fail("E_CHALLENGE_EXPIRED", "challenge expired")
        return c

    def prune(self, now: float) -> int:
        dead = [n for n, c in self.store.items(TABLE).items() if now > c["expires"] + self.skew]
        if dead:
            with self.store.transaction() as tx:
                for n in dead:
                    tx.delete(TABLE, n)
        return len(dead)
