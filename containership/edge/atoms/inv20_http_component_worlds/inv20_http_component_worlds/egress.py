"""DNS and destination-identity enforcement (checklist component 5).

Policy is *combined*: an authority (host + port + scheme) must be allow-listed, AND every
address it resolves to must pass the address-class policy, AND the transport is handed the
exact validated address to connect to (``Destination.connect_ip``) so there is no second
resolution between check and connect (TOCTOU). Redirects are re-authorised hop by hop.

The resolver is injected (``Resolver`` protocol), so tests drive rebinding, mixed answer
sets and CNAME chains deterministically; production wiring uses ``SystemResolver`` or the
platform resolver named in configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import socket
import time
from typing import Callable, Dict, FrozenSet, Iterable, List, Optional, Protocol, Sequence, Tuple

from .errors import Inv20Error
from .protocol import Authority, parse_authority

POLICY_VERSION = "INV20_DEST_POLICY/1"

IPAddr = ipaddress.IPv4Address | ipaddress.IPv6Address


class EgressPolicyDenied(Inv20Error):
    code = "E_EGRESS_DENIED"


class DnsDenied(Inv20Error):
    code = "E_DNS_DENIED"


class DnsFailure(Inv20Error):
    code = "E_DNS_FAILURE"


class RedirectLimit(Inv20Error):
    code = "E_REDIRECT_LIMIT"


# Stable reason codes (bounded label set for metrics).
REASONS = ("allowed", "not_allowlisted", "scheme", "port", "loopback", "private", "link_local",
           "multicast", "unspecified", "reserved", "metadata", "mapped_denied", "mixed_answer",
           "cname_denied", "empty_answer", "resolver_error", "redirect_limit", "redirect_loop",
           "ip_literal_denied", "proxy_ignored")

METADATA_ADDRESSES = frozenset({ipaddress.ip_address("169.254.169.254"),
                                ipaddress.ip_address("fd00:ec2::254"),
                                ipaddress.ip_address("100.100.100.200")})


def classify(ip: IPAddr) -> str:
    """Return the address class; an IPv4-mapped/compat IPv6 is classified by its IPv4 form."""
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped or (ip.sixtofour if ip.sixtofour else None)
        if mapped is not None:
            inner = classify(mapped)
            return "mapped_denied" if inner != "public" else "public"
        if ip in ipaddress.ip_network("64:ff9b::/96"):  # NAT64 well-known prefix
            inner = classify(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
            return "mapped_denied" if inner != "public" else "public"
    if ip in METADATA_ADDRESSES:
        return "metadata"
    if ip.is_unspecified:
        return "unspecified"
    if ip.is_loopback:
        return "loopback"
    if ip.is_link_local:
        return "link_local"
    if ip.is_multicast:
        return "multicast"
    if ip.is_private:
        return "private"
    if ip.is_reserved or not ip.is_global:
        return "reserved"
    return "public"


@dataclass(frozen=True)
class Answer:
    addresses: Tuple[str, ...]
    cname_chain: Tuple[str, ...] = ()
    ttl: int = 30


class Resolver(Protocol):
    def resolve(self, host: str) -> Answer: ...


class SystemResolver:
    """getaddrinfo-backed resolver (no CNAME visibility; policy relies on address checks)."""

    def resolve(self, host: str) -> Answer:
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except OSError as exc:
            raise DnsFailure(type(exc).__name__) from None
        return Answer(tuple(sorted({i[4][0] for i in infos})))


@dataclass(frozen=True)
class Destination:
    authority: Authority
    connect_ip: str          # the only address the transport may dial
    sni: Optional[str]       # expected TLS SNI / certificate identity (None for IP literal)
    reason: str
    policy_version: str = POLICY_VERSION


@dataclass
class DestinationPolicy:
    allowed_authorities: FrozenSet[Tuple[str, int]] = frozenset()   # (canonical host, port)
    allowed_schemes: FrozenSet[str] = frozenset({"https"})
    allowed_address_classes: FrozenSet[str] = frozenset({"public"})
    allowed_cidrs: Tuple[str, ...] = ()        # explicit exceptions, e.g. a service mesh range
    allow_ip_literals: bool = False
    denied_cname_suffixes: Tuple[str, ...] = ()
    max_redirects: int = 5
    cache_ttl_cap: int = 60
    resolver: Resolver = field(default_factory=SystemResolver)
    clock: Callable[[], float] = time.monotonic
    on_decision: Optional[Callable[[str, str], None]] = None   # (reason, safe_dest)
    _cache: Dict[str, Tuple[float, Answer]] = field(default_factory=dict)

    @classmethod
    def from_hosts(cls, hosts: Iterable[str], port: int = 443, **kw) -> "DestinationPolicy":
        auths = set()
        for h in hosts:
            a = parse_authority(h if (h.startswith("[") or h.count(":") == 1) else
                                (f"[{h}]:{port}" if ":" in h else f"{h}:{port}"))
            auths.add((a.host, a.port))
        return cls(allowed_authorities=frozenset(auths), **kw)

    # -- internals --------------------------------------------------------
    def _emit(self, reason: str, auth: Optional[Authority]) -> None:
        if self.on_decision:
            self.on_decision(reason, auth.render() if auth else "-")

    def _deny(self, exc_cls, reason: str, auth: Optional[Authority]):
        if auth is not None:
            self._cache.pop(auth.host, None)   # never cache an answer that produced a denial
        self._emit(reason, auth)
        return exc_cls(reason)

    def _address_ok(self, ip: IPAddr) -> Tuple[bool, str]:
        for c in self.allowed_cidrs:
            net = ipaddress.ip_network(c)
            if ip.version == net.version and ip in net:
                return True, "allowed"
        cls_ = classify(ip)
        return cls_ in self.allowed_address_classes, cls_

    def _lookup(self, host: str) -> Answer:
        now = self.clock()
        hit = self._cache.get(host)
        if hit and hit[0] > now:
            return hit[1]
        try:
            ans = self.resolver.resolve(host)
        except DnsFailure:
            raise
        except Exception as exc:  # any resolver defect fails closed
            raise DnsFailure(type(exc).__name__) from None
        ttl = max(0, min(int(ans.ttl), self.cache_ttl_cap))
        if ttl:
            self._cache[host] = (now + ttl, ans)
        else:
            self._cache.pop(host, None)
        return ans

    def invalidate(self, host: Optional[str] = None) -> None:
        """Called on reconnect: forces revalidation against a fresh answer."""
        if host is None:
            self._cache.clear()
        else:
            self._cache.pop(host, None)

    # -- public API -------------------------------------------------------
    def authorize(self, scheme: str, authority: str) -> Destination:
        if scheme not in self.allowed_schemes:
            raise self._deny(EgressPolicyDenied, "scheme", None)
        auth = parse_authority(authority, scheme)
        if (auth.host, auth.port) not in self.allowed_authorities:
            raise self._deny(EgressPolicyDenied, "not_allowlisted", auth)
        if auth.is_ip:
            if not self.allow_ip_literals:
                raise self._deny(EgressPolicyDenied, "ip_literal_denied", auth)
            ok, why = self._address_ok(ipaddress.ip_address(auth.host))
            if not ok:
                raise self._deny(DnsDenied, why, auth)
            self._emit("allowed", auth)
            return Destination(auth, auth.host, None, "allowed")
        ans = self._lookup(auth.host)
        for name in ans.cname_chain:
            if any(name.rstrip(".").lower().endswith(s) for s in self.denied_cname_suffixes):
                raise self._deny(DnsDenied, "cname_denied", auth)
        if not ans.addresses:
            raise self._deny(DnsDenied, "empty_answer", auth)
        verdicts = []
        for a in ans.addresses:
            try:
                ip = ipaddress.ip_address(a)
            except ValueError:
                raise self._deny(DnsDenied, "reserved", auth) from None
            verdicts.append((ip, *self._address_ok(ip)))
        bad = [v for v in verdicts if not v[1]]
        if bad:
            # Mixed answer sets are rejected outright: no "pick the good one" selection.
            reason = "mixed_answer" if len(bad) < len(verdicts) else bad[0][2]
            raise self._deny(DnsDenied, reason, auth)
        chosen = sorted(v[0] for v in verdicts if v[0].version == 4) or sorted(v[0] for v in verdicts)
        self._emit("allowed", auth)
        return Destination(auth, chosen[0].compressed, auth.host, "allowed")

    def follow_redirects(self, scheme: str, authority: str,
                         next_hop: Callable[[Destination], Optional[Tuple[str, str]]]) -> Destination:
        """Authorise the initial destination and every redirect target; cap depth; detect loops."""
        seen = set()
        dest = self.authorize(scheme, authority)
        for _ in range(self.max_redirects + 1):
            key = (scheme, dest.authority)
            if key in seen:
                raise self._deny(RedirectLimit, "redirect_loop", dest.authority)
            seen.add(key)
            nxt = next_hop(dest)
            if nxt is None:
                return dest
            scheme, authority = nxt
            dest = self.authorize(scheme, authority)
        raise self._deny(RedirectLimit, "redirect_limit", dest.authority)


def check_identity_coherence(dest: Destination, host_header: Optional[str], tls_peer_names: Sequence[str]) -> None:
    """Adjacent-transport hook: requested authority == Host == SNI == certificate name."""
    if host_header is not None and parse_authority(host_header, "https").host != dest.authority.host:
        raise EgressPolicyDenied("host_header_mismatch")
    if dest.sni is not None:
        names = {n.lower().rstrip(".") for n in tls_peer_names}
        wildcard = "*." + dest.sni.split(".", 1)[1] if "." in dest.sni else None
        if dest.sni not in names and (wildcard is None or wildcard not in names):
            raise EgressPolicyDenied("tls_identity_mismatch")


def proxy_environment_ignored(env: Dict[str, str]) -> List[str]:
    """INV-20 never honours ambient proxy variables; returns the ones it ignored (for evidence)."""
    return sorted(k for k in env if k.lower() in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"})
