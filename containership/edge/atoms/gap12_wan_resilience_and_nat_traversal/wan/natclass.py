"""NAT behaviour classification (G12-A006), CGNAT indicators (G12-A007) and
NAT64/DNS64 prefix handling (G12-A012) — RFC 4787 / RFC 5780 / RFC 6598 /
RFC 6052 / RFC 7050.

Mapping and filtering are classified independently from controlled
multi-address / multi-port observations.  When the server cannot supply the
observations a label needs (no OTHER-ADDRESS, CHANGE-REQUEST ignored, too few
servers) the result is ``undetermined`` with the missing evidence named — a
label is never forced.  Classifications carry the network fingerprint they
were measured under and expire when it changes or after ``TTL`` seconds.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import time
from dataclasses import dataclass, field

from . import stun

TTL = 600.0
CGNAT_NET = ipaddress.ip_network("100.64.0.0/10")
WKP_NAT64 = ipaddress.ip_network("64:ff9b::/96")
IPV4ONLY_ARPA = ("192.0.0.170", "192.0.0.171")


@dataclass
class Classification:
    mapping: str            # endpoint-independent | address-dependent | address-and-port-dependent | undetermined | none
    filtering: str          # endpoint-independent | address-dependent | address-and-port-dependent | undetermined
    evidence: dict
    fingerprint: str
    measured_at: float
    missing: list[str] = field(default_factory=list)

    def valid(self, fingerprint: str, now: float) -> bool:
        return fingerprint == self.fingerprint and 0 <= now - self.measured_at <= TTL

    def label(self) -> str:
        """Legacy label only when both halves are determined; otherwise 'undetermined'."""
        m, f = self.mapping, self.filtering
        if "undetermined" in (m, f):
            return "undetermined"
        if m == "none":
            return "open-internet"
        if m != "endpoint-independent":
            return "symmetric"
        return {"endpoint-independent": "full-cone", "address-dependent": "restricted-cone",
                "address-and-port-dependent": "port-restricted-cone"}[f]


def network_fingerprint(snapshot: dict) -> str:
    """Stable digest of the inputs a classification depends on (interface, gateway, public address)."""
    keys = {k: snapshot.get(k) for k in ("interface", "gateway", "local_address", "public_address")}
    return hashlib.sha256(json.dumps(keys, sort_keys=True).encode()).hexdigest()[:16]


def classify(server: tuple[str, int], *, bind: tuple[str, int] = ("0.0.0.0", 0), fingerprint: str = "",
             rto: float = 0.1, rc: int = 3, rm: int = 3, clock=time.monotonic) -> Classification:
    """RFC 5780 section 4.3 (mapping) and 4.4 (filtering) tests from one socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ev: dict = {}
    missing: list[str] = []
    try:
        sock.bind(bind)
        kw = dict(rto=rto, rc=rc, rm=rm)
        t1 = stun.binding(sock, server, **kw)
        ev["test1"] = _ev(t1)
        if not t1.ok:
            return Classification("undetermined", "undetermined", ev, fingerprint, clock(),
                                  [f"test I failed: {t1.reason}"])
        local = sock.getsockname()
        if t1.mapped == tuple(local) or (t1.mapped[1] == local[1] and _is_local(t1.mapped[0])):
            mapping = "none"
        elif t1.other is None:
            mapping = "undetermined"
            missing.append("server supplied no OTHER-ADDRESS")
        else:
            t2 = stun.binding(sock, (t1.other[0], server[1]), **kw)
            ev["test2"] = _ev(t2)
            if not t2.ok:
                mapping = "undetermined"
                missing.append(f"test II failed: {t2.reason}")
            elif t2.mapped == t1.mapped:
                mapping = "endpoint-independent"
            else:
                t3 = stun.binding(sock, (t1.other[0], t1.other[1]), **kw)
                ev["test3"] = _ev(t3)
                if not t3.ok:
                    mapping = "undetermined"
                    missing.append(f"test III failed: {t3.reason}")
                else:
                    mapping = "address-dependent" if t3.mapped == t2.mapped else "address-and-port-dependent"
        # filtering: ask the server to answer from the other IP+port, then other port only
        f2 = stun.binding(sock, server, change_ip=True, change_port=True, **kw)
        ev["filter2"] = _ev(f2)
        if f2.ok:
            if f2.origin is not None and f2.origin[0] == server[0]:
                filtering = "undetermined"
                missing.append("server ignored CHANGE-REQUEST (response origin unchanged)")
            else:
                filtering = "endpoint-independent"
        else:
            f3 = stun.binding(sock, server, change_port=True, **kw)
            ev["filter3"] = _ev(f3)
            if f3.ok and f3.origin is not None and f3.origin[1] == server[1]:
                filtering = "undetermined"
                missing.append("server ignored CHANGE-REQUEST port change")
            else:
                filtering = "address-dependent" if f3.ok else "address-and-port-dependent"
            if t1.other is None:
                filtering = "undetermined"
                missing.append("filtering tests need an RFC 5780 server with OTHER-ADDRESS")
        return Classification(mapping, filtering, ev, fingerprint, clock(), missing)
    finally:
        sock.close()


def _ev(r: stun.BindingResult) -> dict:
    return {"ok": r.ok, "reason": r.reason, "mapped": r.mapped, "other": r.other, "origin": r.origin,
            "sends": r.sends}


def _is_local(ip: str) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((ip, 0))
        s.close()
        return True
    except OSError:
        return False


# --- CGNAT -------------------------------------------------------------------------------

@dataclass
class CgnatAssessment:
    verdict: str                  # likely | possible | unlikely | undetermined
    indicators: list[str]
    evidence: dict
    note: str = ("diagnostic/policy signal only: never proof of peer identity or of exact carrier topology")


def assess_cgnat(*, local_address: str, mapped_address: str | None, traceroute_hops: list[str] | None = None,
                 mapping_behaviour: str | None = None, gateway_wan_address: str | None = None) -> CgnatAssessment:
    """Combine independent indicators; a single heuristic never yields 'likely'."""
    ind: list[str] = []
    ev = {"local_address": local_address, "mapped_address": mapped_address, "gateway_wan_address": gateway_wan_address,
          "hops": traceroute_hops, "mapping": mapping_behaviour}
    if mapped_address is None:
        return CgnatAssessment("undetermined", [], ev)
    if _in(local_address, CGNAT_NET):
        ind.append("local address inside 100.64.0.0/10 (RFC 6598 shared space)")
    if gateway_wan_address and _in(gateway_wan_address, CGNAT_NET):
        ind.append("home gateway WAN address inside 100.64.0.0/10")
    if gateway_wan_address and mapped_address and gateway_wan_address != mapped_address:
        ind.append("gateway WAN address differs from the STUN-mapped public address (another NAT layer upstream)")
    if traceroute_hops and any(_in(h, CGNAT_NET) for h in traceroute_hops):
        ind.append("a 100.64.0.0/10 hop on the upstream path")
    if mapping_behaviour == "address-and-port-dependent":
        ind.append("address-and-port-dependent mapping (common on carrier NAT, not specific to it)")
    strong = [i for i in ind if "100.64" in i or "another NAT layer" in i]
    if len(strong) >= 2 or (strong and len(ind) >= 2):
        verdict = "likely"
    elif ind:
        verdict = "possible"
    else:
        verdict = "unlikely"
    return CgnatAssessment(verdict, ind, ev)


def _in(ip: str | None, net) -> bool:
    try:
        return ip is not None and ipaddress.ip_address(ip) in net
    except ValueError:
        return False


# --- NAT64 / DNS64 ------------------------------------------------------------------------

def discover_nat64_prefixes(ipv4only_aaaa: list[str]) -> list[str]:
    """RFC 7050: derive Pref64::/n from the AAAA answers for ipv4only.arpa."""
    found = []
    for a in ipv4only_aaaa:
        ip = ipaddress.IPv6Address(a)
        raw = ip.packed
        for plen, pos in ((96, 12), (64, 9), (56, 7), (48, 6), (40, 5), (32, 4)):
            v4 = _extract_v4(raw, plen)
            if v4 in IPV4ONLY_ARPA:
                prefix = ipaddress.IPv6Network((int(ip) >> (128 - plen) << (128 - plen), plen))
                if str(prefix) not in found:
                    found.append(str(prefix))
                break
    return found


def _extract_v4(raw: bytes, plen: int) -> str:
    b = bytearray(raw)
    if plen == 96:
        v4 = b[12:16]
    else:
        bits = b[:8] + b[9:]            # RFC 6052: skip octet 8 (bits 64-71 are zero)
        start = plen // 8
        v4 = bits[start:start + 4]
    return str(ipaddress.IPv4Address(bytes(v4)))


def synthesize(prefix: str, v4: str) -> str:
    net = ipaddress.IPv6Network(prefix)
    plen = net.prefixlen
    if plen not in (32, 40, 48, 56, 64, 96):
        raise ValueError("RFC 6052 prefix length must be 32/40/48/56/64/96")
    v4b = ipaddress.IPv4Address(v4).packed
    base = bytearray(net.network_address.packed)
    if plen == 96:
        base[12:16] = v4b
    else:
        seq = bytearray(base[:8] + base[9:])
        start = plen // 8
        seq[start:start + 4] = v4b
        base = seq[:8] + bytearray([0]) + seq[8:]
    return str(ipaddress.IPv6Address(bytes(base)))


def is_synthesized(v6: str, prefixes: list[str]) -> bool:
    """Keeps translated candidates separate from native IPv6 ones."""
    ip = ipaddress.IPv6Address(v6)
    return any(ip in ipaddress.IPv6Network(p) for p in prefixes)
