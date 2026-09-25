"""Host-side egress policy with DNS-to-destination binding (INV71-X007, C018, C043).

The guest never supplies DNS answers.  A trusted ``Resolver`` (supplied by the
node; the tests use a scripted fake) returns CNAME chains and A/AAAA records
with TTLs.  A connect is allowed only when:

* the requested name canonicalizes and is on the allowlist (or a literal IP is
  explicitly allowlisted),
* every CNAME hop and the final name are themselves allowlisted, chain <= 8,
* every resolved address is outside the blocked ranges (loopback, private,
  link-local incl. cloud metadata, multicast, reserved, unspecified, ULA,
  IPv4-mapped/NAT64 forms of those),
* the port/protocol is allowed for that destination,

and it returns a ``DestinationCapability`` naming the exact ip:port the
enforcement point (nftables/proxy) may open.  Re-resolution is forced after the
bounded TTL so a rebinding answer is re-checked; resolver failure fails closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import ipaddress
import json
from typing import Callable, Iterable, Mapping, Protocol

from ..sandbox import canonicalize_host
from .errors import ControlError

MAX_CNAME_CHAIN = 8
MAX_TTL_S = 300
MIN_TTL_S = 1
CAPABILITY_MAX_S = 30
METADATA_ADDRS = frozenset({ipaddress.ip_address("169.254.169.254"), ipaddress.ip_address("fd00:ec2::254"),
                            ipaddress.ip_address("100.100.100.200")})


class ResolverError(Exception):
    pass


@dataclass(frozen=True)
class Answer:
    cnames: tuple[str, ...]
    addresses: tuple[str, ...]
    ttl: int


class Resolver(Protocol):
    def resolve(self, name: str) -> Answer: ...


def blocked_address(addr: str) -> str | None:
    """Return a reason if the address must never be reachable, else None."""
    ip = ipaddress.ip_address(addr)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return blocked_address(str(ip.ipv4_mapped)) or None
        if ip in ipaddress.ip_network("64:ff9b::/96"):
            return blocked_address(str(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))) or None
        if ip.scope_id:
            return "zone_id"
    if ip in METADATA_ADDRS:
        return "metadata"
    for attr in ("is_loopback", "is_private", "is_link_local", "is_multicast", "is_reserved",
                 "is_unspecified", "is_site_local"):
        if getattr(ip, attr, False):
            return attr[3:]
    if isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"):
        return "cgnat"
    return None


@dataclass(frozen=True)
class Rule:
    host: str
    ports: frozenset[int]
    protocols: frozenset[str] = frozenset({"tcp"})


@dataclass(frozen=True)
class DestinationCapability:
    sid: str
    requested: str
    canonical: str
    address: str
    port: int
    protocol: str
    policy_version: str
    expires_at: float
    mac: str

    def body(self) -> bytes:
        d = {k: getattr(self, k) for k in ("sid", "requested", "canonical", "address", "port",
                                          "protocol", "policy_version", "expires_at")}
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


@dataclass
class EgressPolicy:
    version: str
    rules: Mapping[str, Rule]
    key: bytes
    resolver: Resolver
    clock: Callable[[], float]
    allow_private: frozenset[str] = frozenset()  # explicit, reviewed exceptions only
    _cache: dict[str, tuple[Answer, float]] = field(default_factory=dict)
    decisions: list[dict] = field(default_factory=list)
    decision_limit: int = 1024

    @classmethod
    def build(cls, version: str, rules: Iterable[tuple[str, Iterable[int]]], *, key: bytes,
              resolver: Resolver, clock: Callable[[], float]) -> "EgressPolicy":
        rs = {}
        for host, ports in rules:
            c = canonicalize_host(host)
            ps = frozenset(int(p) for p in ports)
            if not ps or any(not 0 < p < 65536 for p in ps):
                raise ValueError("ports must be 1..65535 and non-empty")
            rs[c] = Rule(c, ps)
        return cls(version, rs, key, resolver, clock)

    def _log(self, sid: str, requested: str, canonical: str, addrs, chosen, allowed: bool, reason: str) -> None:
        if len(self.decisions) >= self.decision_limit:
            del self.decisions[0]
        self.decisions.append({"schema": "PK_HEAVYBOX_EGRESS/2", "sid": sid, "requested": requested,
                               "canonical": canonical, "resolved": list(addrs), "selected": chosen,
                               "policy_version": self.version, "decision": "allow" if allowed else "deny",
                               "reason": reason})

    def _resolve(self, name: str) -> Answer:
        now = self.clock()
        hit = self._cache.get(name)
        if hit and hit[1] > now:
            return hit[0]
        try:
            ans = self.resolver.resolve(name)
        except ResolverError as exc:
            self._cache.pop(name, None)  # never serve stale answers for new decisions
            raise ControlError("POLICY.DESTINATION_UNVERIFIED", "resolver unavailable") from exc
        ttl = min(max(int(ans.ttl), MIN_TTL_S), MAX_TTL_S)
        self._cache[name] = (ans, now + ttl)
        return ans

    def decide(self, sid: str, requested: str, port: int, protocol: str = "tcp") -> DestinationCapability:
        try:
            canonical = canonicalize_host(requested)
        except ValueError:
            self._log(sid, requested[:253], "", (), None, False, "malformed_host")
            raise ControlError("POLICY.EGRESS_DENIED", "malformed host") from None
        rule = self.rules.get(canonical)
        if rule is None:
            self._log(sid, requested, canonical, (), None, False, "not_allowlisted")
            raise ControlError("POLICY.EGRESS_DENIED", "not allowlisted")
        if port not in rule.ports or protocol not in rule.protocols:
            self._log(sid, requested, canonical, (), None, False, "port_or_protocol")
            raise ControlError("POLICY.EGRESS_DENIED", "port/protocol")
        try:
            literal = ipaddress.ip_address(canonical)
        except ValueError:
            literal = None
        if literal is not None:
            addrs: tuple[str, ...] = (literal.compressed,)
        else:
            ans = self._resolve(canonical)
            if len(ans.cnames) > MAX_CNAME_CHAIN:
                self._log(sid, requested, canonical, (), None, False, "cname_chain_too_long")
                raise ControlError("POLICY.EGRESS_DENIED", "cname chain")
            for hop in ans.cnames:
                try:
                    hop_c = canonicalize_host(hop)
                except ValueError:
                    hop_c = ""
                if hop_c not in self.rules:
                    self._log(sid, requested, canonical, (), None, False, "cname_not_allowlisted")
                    raise ControlError("POLICY.EGRESS_DENIED", "cname hop not allowlisted")
            addrs = tuple(ipaddress.ip_address(a).compressed for a in ans.addresses)
            if not addrs:
                self._log(sid, requested, canonical, (), None, False, "no_addresses")
                raise ControlError("POLICY.DESTINATION_UNVERIFIED", "no addresses")
        for a in addrs:
            why = blocked_address(a)
            if why and canonical not in self.allow_private:
                self._log(sid, requested, canonical, addrs, None, False, f"blocked_range:{why}")
                raise ControlError("POLICY.EGRESS_DENIED", f"resolved to blocked range {why}")
        chosen = sorted(addrs, key=lambda a: (ipaddress.ip_address(a).version != 6, a))[0]
        # A capability never outlives the DNS answer it was bound from (max 30 s).
        cached = self._cache.get(canonical)
        exp = min(self.clock() + CAPABILITY_MAX_S, cached[1] if (literal is None and cached) else self.clock() + CAPABILITY_MAX_S)
        cap = DestinationCapability(sid, requested, canonical, chosen, port, protocol, self.version, exp, "")
        mac = hmac.new(self.key, cap.body(), hashlib.sha256).hexdigest()
        cap = DestinationCapability(**{**cap.__dict__, "mac": mac})
        self._log(sid, requested, canonical, addrs, chosen, True, "allowlisted_and_bound")
        return cap


def enforce(cap: DestinationCapability, *, key: bytes, sid: str, address: str, port: int,
            protocol: str, now: float) -> None:
    """The enforcement point: only the exact capability-bound tuple may connect (TOCTOU)."""
    good = hmac.compare_digest(cap.mac, hmac.new(key, cap.body(), hashlib.sha256).hexdigest())
    if not good or cap.sid != sid or cap.address != ipaddress.ip_address(address).compressed \
            or cap.port != port or cap.protocol != protocol or now > cap.expires_at:
        raise ControlError("POLICY.EGRESS_DENIED", "capability mismatch")
