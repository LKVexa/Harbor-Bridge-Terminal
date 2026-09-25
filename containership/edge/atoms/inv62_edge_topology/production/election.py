"""Fenced site-coordinator leases (MC-048).

Safety properties (tested in tests/test_election.py and the fault suite):

* **Monotonic terms.**  Every grant to a *new* holder increments the site's
  term; the term high-water mark is persisted before the grant is returned,
  so a restart can never reissue an old term.
* **Single holder.**  While a lease is unexpired only its holder may renew;
  any other candidate is refused with the current holder and expiry.
* **Fencing.**  The fencing token is the term.  Downstream actors must call
  ``validate_token``; a token lower than the current term is STALE_LEADER.
* **Quorum.**  A candidate must be coordinator-eligible, not quarantined, and
  able to reach a strict majority of the site's eligible voters over live
  links (itself included).  A minority side of an intra-site split therefore
  cannot acquire even if the lease authority were replicated to it.
* **Deterministic preference.**  Among quorum-capable candidates the
  lexicographically lowest wins an *expired* lease; a lower-ranked candidate
  is refused while a preferred one is reachable, so concurrent campaigns
  converge.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from collections.abc import Callable

from . import errors
from ..topology import Topology


@dataclass(frozen=True)
class Lease:
    site: str
    holder: str
    term: int
    expires_at: float

    def as_dict(self) -> dict:
        return {"site": self.site, "holder": self.holder, "term": self.term, "fencing_token": self.term,
                "expires_at": self.expires_at}


class LeaseAuthority:
    def __init__(self, *, ttl_s: float, persist_term: Callable[[str, int], None] | None = None,
                 terms: dict[str, int] | None = None):
        self.ttl_s = ttl_s
        self._persist = persist_term
        self._terms: dict[str, int] = dict(terms or {})
        self._leases: dict[str, Lease] = {}
        self._lock = threading.Lock()

    def current(self, site: str, now: float) -> Lease | None:
        lease = self._leases.get(site)
        return lease if lease and lease.expires_at > now else None

    def term(self, site: str) -> int:
        return self._terms.get(site, 0)

    @staticmethod
    def quorum(topo: Topology, site: str, capability: str, excluded: set[str]) -> tuple[list[str], dict[str, bool]]:
        voters = [m for m in topo.site_members(site) if capability in topo.nodes[m].caps and m not in excluded]
        need = len(voters) // 2 + 1
        ok: dict[str, bool] = {}
        for v in voters:
            reach = topo.distances(v)
            ok[v] = sum(1 for other in voters if other in reach) >= need
        return voters, ok

    def acquire(self, topo: Topology, key: str, site: str, candidate: str, now: float, *, capability: str,
                excluded: set[str]) -> Lease:
        """Grant/renew the lease stored under ``key`` for a member of ``site``."""
        with self._lock:
            node = topo.nodes.get(candidate)
            if node is None or node.site != site:
                raise errors.TopoError(errors.INVALID_TOPOLOGY, "candidate is not a member of the site")
            if candidate in excluded:
                raise errors.TopoError(errors.QUARANTINED, "candidate is quarantined")
            if capability not in node.caps:
                raise errors.TopoError(errors.NO_COORDINATOR, "candidate lacks coordinator capability")
            cur = self.current(key, now)
            if cur and cur.holder != candidate:
                raise errors.TopoError(errors.CONFLICT, "site lease held by another node",
                                       {"holder": cur.holder, "term": cur.term, "expires_at": cur.expires_at})
            voters, ok = self.quorum(topo, site, capability, excluded)
            if not ok.get(candidate):
                raise errors.TopoError(errors.FORBIDDEN, "candidate cannot reach a quorum of eligible voters",
                                       {"voters": len(voters)})
            if cur is None:
                preferred = min(v for v, good in ok.items() if good)
                if preferred != candidate:
                    raise errors.TopoError(errors.CONFLICT, "a preferred eligible candidate is available",
                                           {"preferred": preferred})
                term = self._terms.get(key, 0) + 1
                if self._persist:
                    self._persist(key, term)  # durable before grant
                self._terms[key] = term
            else:
                term = cur.term
            lease = Lease(key, candidate, term, now + self.ttl_s)
            self._leases[key] = lease
            return lease

    def renew(self, site: str, candidate: str, token: int, now: float) -> Lease:
        with self._lock:
            cur = self.current(site, now)
            if cur is None or cur.holder != candidate or cur.term != token:
                self._check_token(site, token)
                raise errors.TopoError(errors.CONFLICT, "lease not held by caller or expired")
            lease = Lease(site, candidate, cur.term, now + self.ttl_s)
            self._leases[site] = lease
            return lease

    def validate_token(self, site: str, token: int, now: float) -> Lease:
        with self._lock:
            self._check_token(site, token)
            cur = self.current(site, now)
            if cur is None or cur.term != token:
                raise errors.TopoError(errors.STALE_LEADER, "no live lease for this fencing token")
            return cur

    def _check_token(self, site: str, token: int) -> None:
        if token < self._terms.get(site, 0):
            raise errors.TopoError(errors.STALE_LEADER, "fencing token superseded",
                                   {"current_term": self._terms.get(site, 0)})

    def revoke(self, site: str) -> None:
        with self._lock:
            self._leases.pop(site, None)
