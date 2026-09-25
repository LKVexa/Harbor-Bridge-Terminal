"""Link, interface and routing awareness (G12-B017..B022, B024..B027).

* ``snapshot()`` builds an immutable local-network snapshot from Linux
  /sys and /proc (interfaces, link state, MTU, IPv4 addresses via SIOCGIFADDR,
  IPv6 from /proc/net/if_inet6 when the kernel has IPv6, routes with metrics
  and gateways, resolv.conf nameservers, tunnel/VPN/virtual detection).
* ``RouteWatcher`` reconciles change events with periodic full snapshots so a
  missed or coalesced event cannot leave stale state indefinitely; changes are
  coalesced and must be stable for ``min_stable`` before they are published.
* ``Debounce`` is the link-flap hysteresis primitive (hold-down + minimum
  stability), ``UplinkManager`` the multi-WAN policy (priority, metered/cost
  constraints, policy exclusion, deterministic tie-break), ``should_migrate``
  the connection-migration rule, ``pinned_socket`` source-address pinning.
* ``captive_verdict`` classifies a connectivity-check probe; ``diagnose_firewall``
  explains blocked ingress/egress from observations only and never mutates
  host policy (observation is separated from mutation by construction: this
  module contains no code path that writes firewall, route or DNS state).
* ``Plpmtud`` is an RFC 8899 search with black-hole detection, ``mss_for`` the
  MSS/MTU clamp policy for tunnel/relay encapsulation.

Unsupported (explicit): OS change notifications other than Linux rtnetlink
polling; Windows/macOS interface enumeration; Wi-Fi/cellular metering is read
from policy, not discovered.
"""
from __future__ import annotations

import fcntl
import hashlib
import ipaddress
import json
import os
import socket
import struct
import time
from dataclasses import dataclass, field

SIOCGIFADDR, SIOCGIFNETMASK = 0x8915, 0x891B


def _read(path: str, default: str = "") -> str:
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return default


def _ifaddr(name: str, req: int) -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        res = fcntl.ioctl(s.fileno(), req, struct.pack("256s", name[:15].encode()))
        return socket.inet_ntoa(res[20:24])
    except OSError:
        return None
    finally:
        s.close()


def _kind(name: str) -> str:
    base = f"/sys/class/net/{name}"
    if name == "lo":
        return "loopback"
    if os.path.exists(f"{base}/wireless") or os.path.exists(f"{base}/phy80211"):
        return "wifi"
    if name.startswith(("wwan", "rmnet", "ccmni")):
        return "cellular"
    if name.startswith(("tun", "tap", "wg", "ppp", "ipsec", "vpn")) or _read(f"{base}/type") in ("65534", "512"):
        return "tunnel"
    if name.startswith(("veth", "docker", "br", "virbr", "vnet")) or not os.path.exists(f"{base}/device"):
        return "virtual"
    return "ethernet"


@dataclass(frozen=True)
class Interface:
    name: str
    index: int
    kind: str
    up: bool
    mtu: int
    ipv4: tuple[str, ...]
    ipv6: tuple[tuple[str, str], ...]      # (address, scope)
    metered: bool = False


@dataclass(frozen=True)
class Route:
    interface: str
    destination: str
    gateway: str | None
    metric: int


@dataclass(frozen=True)
class Snapshot:
    taken_at: float
    interfaces: tuple[Interface, ...]
    routes: tuple[Route, ...]
    nameservers: tuple[str, ...]
    ipv6_kernel: bool

    def default_routes(self) -> list[Route]:
        return sorted((r for r in self.routes if r.destination == "0.0.0.0/0"), key=lambda r: (r.metric, r.interface))

    def fingerprint(self) -> str:
        body = json.dumps({"i": [(i.name, i.up, i.mtu, i.ipv4, i.ipv6) for i in self.interfaces],
                           "r": [(r.interface, r.destination, r.gateway, r.metric) for r in self.routes],
                           "d": self.nameservers}, sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()[:16]


def snapshot(metered: set[str] | None = None, clock=time.monotonic) -> Snapshot:
    metered = metered or set()
    v6: dict[str, list[tuple[str, str]]] = {}
    raw6 = _read("/proc/net/if_inet6")
    for line in raw6.splitlines():
        parts = line.split()
        if len(parts) >= 6:
            addr = str(ipaddress.IPv6Address(bytes.fromhex(parts[0])))
            scope = {"00": "global", "20": "link", "10": "host", "40": "site"}.get(parts[3], parts[3])
            v6.setdefault(parts[5], []).append((addr, scope))
    ifs = []
    for idx, name in sorted(socket.if_nameindex()):
        base = f"/sys/class/net/{name}"
        oper = _read(f"{base}/operstate", "unknown")
        flags = int(_read(f"{base}/flags", "0x0"), 16)
        ip4 = _ifaddr(name, SIOCGIFADDR)
        mask = _ifaddr(name, SIOCGIFNETMASK)
        cidr = (f"{ip4}/{ipaddress.IPv4Network(f'0.0.0.0/{mask}').prefixlen}",) if ip4 and mask else ()
        ifs.append(Interface(name, idx, _kind(name), bool(flags & 1) and oper in ("up", "unknown"),
                             int(_read(f"{base}/mtu", "0") or 0), cidr, tuple(v6.get(name, ())), name in metered))
    routes = []
    for line in _read("/proc/net/route").splitlines()[1:]:
        f = line.split()
        if len(f) < 11:
            continue
        dst = socket.inet_ntoa(struct.pack("<I", int(f[1], 16)))
        gw = socket.inet_ntoa(struct.pack("<I", int(f[2], 16)))
        mask = socket.inet_ntoa(struct.pack("<I", int(f[7], 16)))
        plen = ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
        routes.append(Route(f[0], f"{dst}/{plen}", None if gw == "0.0.0.0" else gw, int(f[6])))
    ns = tuple(l.split()[1] for l in _read("/etc/resolv.conf").splitlines() if l.startswith("nameserver") and len(l.split()) > 1)
    return Snapshot(clock(), tuple(ifs), tuple(routes), ns, os.path.exists("/proc/net/if_inet6"))


def eligible_ipv6(iface: Interface, *, allow_temporary: bool = True) -> list[str]:
    """Policy-eligible IPv6 candidates: global scope only; link-local needs a scope id and is excluded."""
    out = []
    for addr, scope in iface.ipv6:
        ip = ipaddress.IPv6Address(addr)
        if scope != "global" or ip.is_link_local or ip.is_loopback or ip.is_multicast:
            continue
        out.append(addr)
    return out


# --- change detection ----------------------------------------------------------------------

@dataclass
class Debounce:
    """Publish a new value only after it has been stable for ``min_stable`` seconds,
    and never more often than once per ``hold_down`` seconds (flap guard)."""
    min_stable: float = 2.0
    hold_down: float = 5.0
    value: object = None
    candidate: object = None
    candidate_since: float | None = None
    last_publish: float | None = None
    suppressed: int = 0

    def feed(self, value, now: float) -> bool:
        if value == self.value:
            self.candidate, self.candidate_since = None, None
            return False
        if value != self.candidate:
            if self.candidate is not None:
                self.suppressed += 1
            self.candidate, self.candidate_since = value, now
            return False
        if now - self.candidate_since < self.min_stable:
            return False
        if self.last_publish is not None and now - self.last_publish < self.hold_down:
            return False
        self.value, self.last_publish = value, now
        self.candidate, self.candidate_since = None, None
        return True


@dataclass
class RouteWatcher:
    """Event + periodic reconciliation; ``sample`` is snapshot() or a test double."""
    sample: object = snapshot
    full_interval: float = 30.0
    debounce: Debounce = field(default_factory=Debounce)
    last_full: float | None = None
    published: Snapshot | None = None
    events: int = 0
    reconciles: int = 0

    def on_event(self, now: float) -> Snapshot | None:
        self.events += 1
        return self._consider(self.sample(), now)

    def tick(self, now: float) -> Snapshot | None:
        if self.last_full is None or now - self.last_full >= self.full_interval:
            self.last_full = now
            self.reconciles += 1
            return self._consider(self.sample(), now)
        if self.debounce.candidate is not None:   # re-check a pending candidate
            return self._consider(self.sample(), now)
        return None

    def _consider(self, snap: Snapshot, now: float) -> Snapshot | None:
        if self.debounce.feed(snap.fingerprint(), now):
            self.published = snap
            return snap
        if self.published is None and self.debounce.value is None:
            self.debounce.value = snap.fingerprint()
            self.published = snap
            return snap
        return None


@dataclass(frozen=True)
class Uplink:
    name: str
    priority: int                  # lower is preferred
    healthy: bool
    metered: bool = False
    cost_per_gb: float = 0.0
    policy_allowed: bool = True


def select_uplink(uplinks: list[Uplink], *, allow_metered: bool = False, current: str | None = None,
                  max_cost_per_gb: float | None = None) -> tuple[Uplink | None, str]:
    """Deterministic multi-WAN choice; the current uplink wins ties (stickiness)."""
    cands = [u for u in uplinks if u.healthy and u.policy_allowed and (allow_metered or not u.metered)
             and (max_cost_per_gb is None or u.cost_per_gb <= max_cost_per_gb)]
    if not cands:
        if any(u.healthy and u.metered for u in uplinks) and not allow_metered:
            return None, "POLICY_MECHANISM_DISABLED"
        return None, "NET_UNREACHABLE"
    cands.sort(key=lambda u: (u.priority, u.name != current, u.cost_per_gb, u.name))
    return cands[0], "OK"


def should_migrate(current_score: float, candidate_score: float, *, current_healthy: bool,
                   margin: float = 0.15, session_active: bool = True) -> bool:
    """Migrate only when the current path failed or the candidate is better by a hysteresis margin.
    Healthy active sessions are not discarded for a marginal gain."""
    if not current_healthy:
        return candidate_score > 0
    if not session_active:
        return candidate_score > current_score
    return candidate_score >= current_score * (1 + margin)


def pinned_socket(source_ip: str, *, kind=socket.SOCK_DGRAM, interface: str | None = None) -> socket.socket:
    """Create a socket pinned to a source address (and optionally SO_BINDTODEVICE)."""
    fam = socket.AF_INET6 if ":" in source_ip else socket.AF_INET
    s = socket.socket(fam, kind)
    try:
        if interface and hasattr(socket, "SO_BINDTODEVICE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode())
        s.bind((source_ip, 0))
    except OSError:
        s.close()
        raise
    return s


def verify_pinning(s: socket.socket, expected_ip: str) -> bool:
    return s.getsockname()[0] == expected_ip


# --- captive portal / firewall diagnostics -------------------------------------------------------

def captive_verdict(status: int | None, body: bytes | None, *, expected_status: int = 204,
                    expected_body: bytes = b"", redirected_to: str | None = None) -> str:
    """Classify a connectivity-check probe: open | captive | blocked | unknown."""
    if status is None:
        return "blocked"
    if redirected_to or status in (301, 302, 303, 307, 308, 511):
        return "captive"
    if status == expected_status and (body or b"") == expected_body:
        return "open"
    if status == 200 and body and body != expected_body:
        return "captive"          # walled garden answering with its own page
    return "unknown"


def diagnose_firewall(obs: dict) -> dict:
    """Explain reachability from observations; returns an explanation, never an action."""
    findings = []
    if obs.get("local_send_errno") in (1, 13):
        findings.append(("NET_FILTERED", "local host policy refused the send (EPERM/EACCES)"))
    if obs.get("udp_ok") is False and obs.get("tcp_ok") is True:
        findings.append(("NET_UDP_BLOCKED", "UDP egress blocked upstream while TCP works"))
    if obs.get("stun_ok") and obs.get("inbound_ok") is False:
        findings.append(("NET_FILTERED", "egress works but unsolicited ingress is filtered (NAT/firewall)"))
    if obs.get("dns_ok") is False and obs.get("ip_literal_ok") is True:
        findings.append(("DNS_TIMEOUT", "DNS is failing while IP-literal connectivity works"))
    if not findings:
        findings.append(("OK" if obs.get("tcp_ok") or obs.get("udp_ok") else "NET_UNREACHABLE",
                         "no blocking condition inferred from the observations"))
    return {"findings": findings, "mutations": [], "note": "diagnostic only; host/network policy untouched"}


# --- PMTU ------------------------------------------------------------------------------------

@dataclass
class Plpmtud:
    """RFC 8899 style search: probe sizes between BASE and MAX; a size that fails
    ``max_probes`` times while smaller ones succeed is a black hole, not loss."""
    base: int = 1200
    max_size: int = 9000
    max_probes: int = 3
    ttl: float = 600.0
    low: int = 1200
    high: int = 9000
    failures: dict[int, int] = field(default_factory=dict)
    confirmed_at: float | None = None
    blackhole: bool = False

    def next_probe(self) -> int | None:
        if self.high - self.low <= 8:
            return None
        return (self.low + self.high + 1) // 2

    def result(self, size: int, ok: bool, now: float) -> None:
        if ok:
            self.low = max(self.low, size)
            self.failures.pop(size, None)
            self.confirmed_at = now
            return
        self.failures[size] = self.failures.get(size, 0) + 1
        if self.failures[size] >= self.max_probes:
            self.high = min(self.high, size - 1)
            self.blackhole = True

    def pmtu(self, now: float) -> int:
        if self.confirmed_at is None or now - self.confirmed_at > self.ttl:
            return self.base              # expired: fall back to the safe base, re-search
        return self.low

    def search(self, probe, now: float = 0.0) -> int:
        while (size := self.next_probe()) is not None:
            ok = False
            for _ in range(self.max_probes):
                if probe(size):
                    ok = True
                    break
                self.result(size, False, now)
                if self.high < size:
                    break
            if ok:
                self.result(size, True, now)
        return self.pmtu(now)


ENCAP_OVERHEAD = {"none": 0, "wireguard": 80, "ipsec": 73, "vxlan": 50, "gre": 24, "turn_channel": 4,
                  "turn_send": 36, "ipip": 20}


def usable_mtu(link_mtu: int, encapsulations: list[str], path_mtu: int | None = None) -> int:
    """Never assume the physical MTU is the end-to-end MTU."""
    m = min(link_mtu, path_mtu or link_mtu)
    for e in encapsulations:
        m -= ENCAP_OVERHEAD[e]
    if m < 576:
        raise ValueError("encapsulation leaves less than the IPv4 minimum")
    return m


def mss_for(mtu: int, *, ipv6: bool = False) -> int:
    return mtu - (60 if ipv6 else 40)
