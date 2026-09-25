"""Reference adapters for the adjacent architectural layers named in the
contract (MC-019, MC-020, MC-072).  They are thin, deterministic translators
used by the integration suite and as starting points for real integrations:

* GAP-02 Hardware capability discovery  -> :class:`HardwareDiscoveryFeed`
* GAP-12 WAN resilience / NAT traversal  -> :class:`WanHealthFeed`
* GAP-03 Topology-aware scheduler        -> :class:`SchedulerAdapter`
* GAP-04 Disconnected operation controller -> :class:`DisconnectedController`
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from collections.abc import Iterable

from . import errors
from .client import Client


@dataclass
class HardwareDiscoveryFeed:
    """Accepts GAP-02 inventory records ``{"id","tier","site","parent","caps","residency"}``."""

    client: Client
    known: set[str] = field(default_factory=set)

    def sync(self, inventory: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
        muts = []
        order = {"cloud": 0, "region": 1, "site": 2, "device": 3}
        for rec in sorted(inventory, key=lambda r: (order[r["tier"]], r["id"])):
            if rec["id"] in self.known:
                continue
            m = {"kind": "add_node", "node": rec["id"], "tier": rec["tier"], "caps": sorted(rec.get("caps", []))}
            for k in ("site", "parent", "residency"):
                if rec.get(k):
                    m[k] = rec[k]
            muts.append(m)
        if not muts:
            return None
        resp = self.client.apply(muts)
        self.known.update(m["node"] for m in muts)
        return resp


@dataclass
class WanHealthFeed:
    """Forwards GAP-12 probe results; hysteresis is applied server-side."""

    client: Client

    def links(self, links: Iterable[tuple[str, str, float]], at: float) -> dict[str, Any]:
        return self.client.apply([{"kind": "connect", "a": a, "b": b, "latency_ms": l, "measured_at": at}
                                  for a, b, l in links])

    def probes(self, results: Iterable[tuple[str, str, bool, float | None]], at: float) -> dict[str, Any]:
        muts = []
        for a, b, ok, latency in results:
            m: dict[str, Any] = {"kind": "probe", "a": a, "b": b, "ok": ok, "at": at}
            if ok and latency is not None:
                m["latency_ms"] = latency
            muts.append(m)
        return self.client.apply(muts)


@dataclass
class SchedulerAdapter:
    """GAP-03 placement query: returns (node, latency, degraded_mode) or None."""

    client: Client

    def place(self, origin: str, capability: str, **constraints: Any) -> tuple[str, float, str | None] | None:
        try:
            r = self.client.resolve(origin, capability, **constraints)
        except errors.TopoError as exc:
            if exc.code == errors.NO_CAPABLE_NODE.code:
                return None
            raise
        return r["result"]["node"], r["result"]["latency_ms"], r.get("degraded_mode")


@dataclass
class DisconnectedController:
    """GAP-04: when the site is partitioned, campaign for the site lease and
    keep renewing it; every local action is fenced by the returned token."""

    client: Client
    site: str
    me: str
    token: int | None = None

    def tick(self) -> dict[str, Any]:
        status = self.client.status(self.site)["result"]
        if not status["partitioned"]:
            self.token = None
            return {"action": "follow-cloud", "status": status}
        if self.token is not None:
            try:
                self.client.renew(self.site, self.me, self.token)
                return {"action": "renewed", "token": self.token}
            except errors.TopoError as exc:
                if exc.code not in (errors.CONFLICT.code, errors.STALE_LEADER.code):
                    raise
                self.token = None
        try:
            lease = self.client.acquire(self.site, self.me)["result"]
            self.token = lease["fencing_token"]
            return {"action": "leader", "token": self.token}
        except errors.TopoError as exc:
            if exc.code in (errors.CONFLICT.code, errors.FORBIDDEN.code):
                return {"action": "follower", "reason": exc.message}
            raise
