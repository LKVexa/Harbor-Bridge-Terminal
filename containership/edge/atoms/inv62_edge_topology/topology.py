"""Core edge-topology graph and routing primitives for INV-62.

This module deliberately has no dependency on ``pk_core`` so the production
logic can be unit-tested and embedded independently of the conformance harness.

Concurrency contract (MC-075): a :class:`Topology` instance is *not* internally
synchronised.  Concurrent use must go through
:class:`inv62_edge_topology.production.service.TopologyService`, which serialises
mutations behind a lock and publishes immutable copy-on-write generations to
readers.  Direct embedders must provide equivalent exclusion.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from collections.abc import Callable, Iterable, Iterator


TIER_PARENT: dict[str, str | None] = {
    "cloud": None,
    "region": "cloud",
    "site": "region",
    "device": "site",
}

#: Identifier grammar shared with the wire schemas (MC-012/MC-018).
MAX_IDENTIFIER_LEN = 128
_IDENT_ALLOWED = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")


class TopologyError(ValueError):
    """Base class for invalid topology mutations."""


class CapacityExceeded(TopologyError):
    """Raised when a mutation would exceed a declared resource bound (MC-057)."""


class UnknownNode(LookupError):
    """Raised when a referenced node is not present in the graph."""


class UnknownSite(LookupError):
    """Raised when a referenced site has no registered members."""


class NoCoordinatorCandidate(LookupError):
    """Raised when a site has no node eligible for coordinator election."""


@dataclass(frozen=True, slots=True)
class TopologyLimits:
    """Hard resource bounds for one topology graph (MC-009/MC-018/MC-057)."""

    max_nodes: int = 10_000
    max_links: int = 50_000
    max_degree: int = 1_024
    max_caps_per_node: int = 64

    def __post_init__(self) -> None:
        for name in ("max_nodes", "max_links", "max_degree", "max_caps_per_node"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise TopologyError(f"{name} must be a positive integer, got {value!r}")


@dataclass(frozen=True, slots=True)
class Node:
    name: str
    tier: str
    site: str | None
    parent: str | None
    caps: frozenset[str] = field(default_factory=frozenset)
    residency: str | None = None


@dataclass(frozen=True, slots=True)
class Link:
    latency_ms: float
    up: bool = True
    measured_at: float | None = None


def validate_identifier(value: object, label: str) -> str:
    """Return a canonical identifier or raise :class:`TopologyError`.

    Identifiers are bounded, printable ASCII from a conservative alphabet so
    they are safe in logs, metric labels, file names and wire payloads.
    """
    if not isinstance(value, str) or not value.strip():
        raise TopologyError(f"{label} must be a non-empty string")
    if value != value.strip():
        # 4.2.0 silently stripped, so "x" and "x\n" aliased one node.
        raise TopologyError(f"{label} must not have leading/trailing whitespace")
    if len(value) > MAX_IDENTIFIER_LEN:
        raise TopologyError(f"{label} exceeds {MAX_IDENTIFIER_LEN} characters")
    if not set(value) <= _IDENT_ALLOWED:
        raise TopologyError(f"{label} contains characters outside [A-Za-z0-9-_.:]")
    return value


@dataclass
class Topology:
    """Validated undirected topology graph.

    Node hierarchy is constrained to cloud -> region -> site -> device.  A
    non-cloud parent may be omitted only when there is exactly one unambiguous
    valid parent already registered; the resolved parent is always stored.
    """

    nodes: dict[str, Node] = field(default_factory=dict)
    links: dict[frozenset[str], Link] = field(default_factory=dict)
    limits: TopologyLimits = field(default_factory=TopologyLimits)
    revision: int = 0
    _adj: dict[str, dict[str, Link]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        # Rebuild adjacency if constructed with pre-populated dictionaries.
        if self.links and not self._adj:
            for pair, link in self.links.items():
                a, b = sorted(pair)
                self._adj.setdefault(a, {})[b] = link
                self._adj.setdefault(b, {})[a] = link

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _identifier(value: object, label: str) -> str:
        return validate_identifier(value, label)

    def _capabilities(self, caps: Iterable[str]) -> frozenset[str]:
        if isinstance(caps, (str, bytes)):
            raise TopologyError("caps must be an iterable of capability names, not a string")
        try:
            values = frozenset(self._identifier(cap, "capability") for cap in caps)
        except TypeError as exc:
            raise TopologyError("caps must be an iterable of capability names") from exc
        if len(values) > self.limits.max_caps_per_node:
            raise CapacityExceeded(
                f"node advertises {len(values)} capabilities; limit is {self.limits.max_caps_per_node}"
            )
        return values

    def _bump(self) -> None:
        self.revision += 1

    def _infer_parent(self, tier: str, site: str | None) -> str | None:
        expected = TIER_PARENT[tier]
        if expected is None:
            return None
        candidates = [
            node.name
            for node in self.nodes.values()
            if node.tier == expected
            and (tier != "device" or node.site == site)
        ]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise TopologyError(f"{tier!r} node requires a registered {expected!r} parent")
        raise TopologyError(
            f"{tier!r} node has ambiguous parent; specify one of {sorted(candidates)!r}"
        )

    # ---------------------------------------------------------------- mutation
    def add(
        self,
        node: str,
        tier: str,
        site: str | None = None,
        caps: Iterable[str] = (),
        *,
        parent: str | None = None,
        residency: str | None = None,
    ) -> None:
        """Register a node after validating hierarchy and capability metadata."""
        node = self._identifier(node, "node")
        tier = self._identifier(tier, "tier")
        if tier not in TIER_PARENT:
            raise TopologyError(f"unsupported tier {tier!r}; expected one of {sorted(TIER_PARENT)}")
        if node in self.nodes:
            raise TopologyError(f"node {node!r} is already registered")
        if len(self.nodes) >= self.limits.max_nodes:
            raise CapacityExceeded(f"topology already holds the maximum {self.limits.max_nodes} nodes")

        if tier in {"site", "device"} or site is not None:
            site = self._identifier(site, "site")
        if residency is not None:
            residency = self._identifier(residency, "residency")

        if tier == "cloud":
            if parent is not None:
                raise TopologyError("cloud nodes cannot have a parent")
            parent = None
        else:
            parent = self._infer_parent(tier, site) if parent is None else self._identifier(parent, "parent")
            if parent is None:  # pragma: no cover - _infer_parent never returns None for non-cloud tiers
                raise TopologyError(f"{tier!r} node requires a parent")
            parent_node = self.nodes.get(parent)
            if parent_node is None:
                raise UnknownNode(f"unknown parent node {parent!r}")
            expected_tier = TIER_PARENT[tier]
            if parent_node.tier != expected_tier:
                raise TopologyError(
                    f"{tier!r} node requires a {expected_tier!r} parent; {parent!r} is {parent_node.tier!r}"
                )
            if tier == "device" and parent_node.site != site:
                raise TopologyError(
                    f"device site {site!r} does not match parent site {parent_node.site!r}"
                )

        self.nodes[node] = Node(node, tier, site, parent, self._capabilities(caps), residency)
        self._bump()

    def remove(self, node: str) -> None:
        """Retire a leaf node and every link touching it.

        Removing a node that still parents other nodes is refused so the
        hierarchy invariant can never be broken by a partial delete.
        """
        node = self._identifier(node, "node")
        if node not in self.nodes:
            raise UnknownNode(f"unknown node {node!r}")
        children = sorted(n.name for n in self.nodes.values() if n.parent == node)
        if children:
            raise TopologyError(f"node {node!r} still parents {children!r}; remove them first")
        for other in list(self._adj.get(node, {})):
            self._drop_link(node, other)
        self._adj.pop(node, None)
        del self.nodes[node]
        self._bump()

    def _drop_link(self, a: str, b: str) -> None:
        self.links.pop(frozenset((a, b)), None)
        self._adj.get(a, {}).pop(b, None)
        self._adj.get(b, {}).pop(a, None)

    def connect(
        self,
        a: str,
        b: str,
        latency: float,
        up: bool = True,
        *,
        measured_at: float | None = None,
    ) -> None:
        """Create or replace a validated link between two registered nodes."""
        a = self._identifier(a, "link endpoint")
        b = self._identifier(b, "link endpoint")
        if a == b:
            raise TopologyError(f"cannot link {a!r} to itself")
        missing = [name for name in (a, b) if name not in self.nodes]
        if missing:
            raise UnknownNode(f"cannot link unregistered node(s): {', '.join(repr(x) for x in missing)}")
        latency = self._latency(latency)
        if not isinstance(up, bool):
            raise TopologyError(f"link state must be bool, got {up!r}")
        if measured_at is not None:
            measured_at = self._timestamp(measured_at)
        key = frozenset((a, b))
        if key not in self.links:
            if len(self.links) >= self.limits.max_links:
                raise CapacityExceeded(f"topology already holds the maximum {self.limits.max_links} links")
            for end in (a, b):
                if len(self._adj.get(end, {})) >= self.limits.max_degree:
                    raise CapacityExceeded(f"node {end!r} already has the maximum {self.limits.max_degree} links")
        link = Link(latency, up, measured_at)
        self.links[key] = link
        self._adj.setdefault(a, {})[b] = link
        self._adj.setdefault(b, {})[a] = link
        self._bump()

    @staticmethod
    def _latency(latency: object) -> float:
        if isinstance(latency, bool) or not isinstance(latency, (int, float)):
            raise TopologyError(f"latency must be a finite non-negative number, got {latency!r}")
        value = float(latency)
        if not math.isfinite(value) or value < 0:
            raise TopologyError(f"latency must be a finite non-negative number, got {latency!r}")
        return value

    @staticmethod
    def _timestamp(value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
            raise TopologyError(f"measured_at must be a finite non-negative timestamp, got {value!r}")
        return float(value)

    def set_link_state(self, a: str, b: str, up: bool, *, measured_at: float | None = None) -> None:
        """Change link health without silently changing its measured latency."""
        if not isinstance(up, bool):
            raise TopologyError(f"link state must be bool, got {up!r}")
        key = frozenset((a, b))
        link = self.links.get(key)
        if link is None:
            raise TopologyError(f"link {a!r}<->{b!r} is not registered")
        stamp = link.measured_at if measured_at is None else self._timestamp(measured_at)
        new = Link(link.latency_ms, up, stamp)
        self.links[key] = new
        self._adj[a][b] = new
        self._adj[b][a] = new
        self._bump()

    def disconnect(self, a: str, b: str) -> None:
        key = frozenset((a, b))
        if key not in self.links:
            raise TopologyError(f"link {a!r}<->{b!r} is not registered")
        self._drop_link(a, b)
        self._bump()

    # ------------------------------------------------------------------ query
    def _neighbours(
        self,
        node: str,
        link_ok: Callable[[Link], bool] | None = None,
    ) -> Iterator[tuple[str, float]]:
        for other, link in self._adj.get(node, {}).items():
            if link.up and (link_ok is None or link_ok(link)):
                yield other, link.latency_ms

    def _require(self, name: object, label: str) -> str:
        name = self._identifier(name, label)
        if name not in self.nodes:
            raise UnknownNode(f"unknown node {name!r}")
        return name

    def distances(
        self,
        origin: str,
        *,
        link_ok: Callable[[Link], bool] | None = None,
    ) -> dict[str, float]:
        """Shortest live-link latency from ``origin`` to every reachable node."""
        origin = self._require(origin, "origin")
        best: dict[str, float] = {origin: 0.0}
        done: set[str] = set()
        heap: list[tuple[float, str]] = [(0.0, origin)]
        while heap:
            dist, node = heapq.heappop(heap)
            if node in done:
                continue
            done.add(node)
            for other, latency in self._neighbours(node, link_ok):
                candidate = dist + latency
                if candidate < best.get(other, math.inf):
                    best[other] = candidate
                    heapq.heappush(heap, (candidate, other))
        return {name: best[name] for name in done}

    def iter_by_distance(
        self,
        origin: str,
        *,
        link_ok: Callable[[Link], bool] | None = None,
    ) -> Iterator[tuple[float, str]]:
        """Lazily yield ``(latency, node)`` in non-decreasing latency order,
        ties by node name.  Callers stop early, so a query touches only the
        part of the graph it needs (MC-056)."""
        origin = self._require(origin, "origin")
        best: dict[str, float] = {origin: 0.0}
        done: set[str] = set()
        heap: list[tuple[float, str]] = [(0.0, origin)]
        while heap:
            dist, node = heapq.heappop(heap)
            if node in done:
                continue
            done.add(node)
            yield dist, node
            for other, latency in self._neighbours(node, link_ok):
                candidate = dist + latency
                if other not in done and candidate < best.get(other, math.inf):
                    best[other] = candidate
                    heapq.heappush(heap, (candidate, other))

    def distance(
        self,
        origin: str,
        target: str,
        *,
        link_ok: Callable[[Link], bool] | None = None,
    ) -> float | None:
        """Return shortest live-link latency, or ``None`` if target is unreachable."""
        target = self._require(target, "target")
        for dist, node in self.iter_by_distance(origin, link_ok=link_ok):
            if node == target:
                return dist
        return None

    def nearest(
        self,
        origin: str,
        cap: str,
        *,
        eligible: Callable[[Node], bool] | None = None,
        link_ok: Callable[[Link], bool] | None = None,
    ) -> tuple[str | None, float | None]:
        """Resolve the lowest-latency reachable node advertising ``cap``.

        Ties are broken by lowest node name, so the result is deterministic.
        ``eligible`` filters candidates (policy); ``link_ok`` filters links
        (e.g. staleness).  Neither can make a down link traversable.
        """
        cap = self._identifier(cap, "capability")
        for dist, node in self.iter_by_distance(origin, link_ok=link_ok):
            meta = self.nodes[node]
            if cap in meta.caps and (eligible is None or eligible(meta)):
                return node, dist
        return None, None

    def candidates(
        self,
        origin: str,
        cap: str,
        *,
        link_ok: Callable[[Link], bool] | None = None,
        limit: int = 16,
    ) -> list[tuple[str, float]]:
        """Reachable nodes advertising ``cap`` ordered by (latency, name)."""
        cap = self._identifier(cap, "capability")
        dist = self.distances(origin, link_ok=link_ok)
        ranked = sorted((d, n) for n, d in dist.items() if cap in self.nodes[n].caps)
        return [(n, d) for d, n in ranked[: max(0, limit)]]

    def site_members(self, site: str) -> tuple[str, ...]:
        site = self._identifier(site, "site")
        members = tuple(sorted(node.name for node in self.nodes.values() if node.site == site))
        if not members:
            raise UnknownSite(f"no nodes on site {site!r}")
        return members

    def sites(self) -> tuple[str, ...]:
        return tuple(sorted({n.site for n in self.nodes.values() if n.site is not None}))

    def partitioned(self, site: str, cloud: str = "cloud") -> bool:
        """Return true when no member of ``site`` can reach the designated cloud node."""
        cloud = self._identifier(cloud, "cloud")
        cloud_node = self.nodes.get(cloud)
        if cloud_node is None:
            raise UnknownNode(f"unknown cloud node {cloud!r}")
        if cloud_node.tier != "cloud":
            raise TopologyError(f"partition target {cloud!r} is not a cloud-tier node")
        members = self.site_members(site)
        reach = self.distances(cloud)
        return all(member not in reach for member in members)

    def elect(self, site: str, capability: str = "coordinator") -> str:
        """Deterministically select the lexicographically-lowest eligible candidate.

        This is *candidate selection* only.  Distributed safety (terms, leases,
        fencing, stale-leader rejection) is provided by
        :mod:`inv62_edge_topology.production.election` (MC-048).
        """
        capability = self._identifier(capability, "coordinator capability")
        candidates = [
            member
            for member in self.site_members(site)
            if capability in self.nodes[member].caps
        ]
        if not candidates:
            raise NoCoordinatorCandidate(
                f"site {site!r} has no node with capability {capability!r}"
            )
        return min(candidates)

    # --------------------------------------------------------------- snapshot
    def clone(self) -> Topology:
        """Return an independent copy (nodes/links are immutable values)."""
        copy = Topology(dict(self.nodes), dict(self.links), self.limits, self.revision)
        return copy

    def snapshot(self) -> dict[str, object]:
        """Return a deterministic, JSON-serializable diagnostic snapshot."""
        nodes = {
            name: {
                "tier": node.tier,
                "site": node.site,
                "parent": node.parent,
                "caps": sorted(node.caps),
                **({"residency": node.residency} if node.residency is not None else {}),
            }
            for name, node in sorted(self.nodes.items())
        }
        links = []
        for pair, link in self.links.items():
            a, b = sorted(pair)
            item: dict[str, object] = {"a": a, "b": b, "latency_ms": link.latency_ms, "up": link.up}
            if link.measured_at is not None:
                item["measured_at"] = link.measured_at
            links.append(item)
        links.sort(key=lambda item: (item["a"], item["b"]))
        return {"nodes": nodes, "links": links}

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, object],
        *,
        limits: TopologyLimits | None = None,
    ) -> Topology:
        """Rebuild a topology from :meth:`snapshot` output with full validation."""
        if not isinstance(snapshot, dict) or set(snapshot) - {"nodes", "links", "revision"}:
            raise TopologyError("snapshot must be an object with 'nodes' and 'links'")
        nodes = snapshot.get("nodes")
        links = snapshot.get("links")
        if not isinstance(nodes, dict) or not isinstance(links, list):
            raise TopologyError("snapshot 'nodes' must be an object and 'links' a list")
        topo = cls(limits=limits or TopologyLimits())
        order = {tier: i for i, tier in enumerate(TIER_PARENT)}
        pending = []
        for name, meta in nodes.items():
            if not isinstance(meta, dict):
                raise TopologyError(f"node {name!r} metadata must be an object")
            tier = meta.get("tier")
            if tier not in order:
                raise TopologyError(f"node {name!r} has unsupported tier {tier!r}")
            pending.append((order[tier], str(name), meta))
        for _, name, meta in sorted(pending):
            unknown = set(meta) - {"tier", "site", "parent", "caps", "residency"}
            if unknown:
                raise TopologyError(f"node {name!r} has unknown fields {sorted(unknown)!r}")
            caps = meta.get("caps", [])
            if not isinstance(caps, list):
                raise TopologyError(f"node {name!r} caps must be a list")
            topo.add(
                name,
                meta["tier"],
                meta.get("site"),
                caps,
                parent=meta.get("parent"),
                residency=meta.get("residency"),
            )
        for item in links:
            if not isinstance(item, dict) or set(item) - {"a", "b", "latency_ms", "up", "measured_at"}:
                raise TopologyError(f"invalid link record {item!r}")
            topo.connect(  # every argument is re-validated by connect()
                item.get("a"),  # type: ignore[arg-type]
                item.get("b"),  # type: ignore[arg-type]
                item.get("latency_ms"),  # type: ignore[arg-type]
                item.get("up", True),
                measured_at=item.get("measured_at"),
            )
        return topo
