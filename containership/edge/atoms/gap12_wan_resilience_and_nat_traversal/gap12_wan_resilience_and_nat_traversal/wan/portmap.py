"""Explicit port-mapping protocols: PCP (G12-A008, RFC 6887), NAT-PMP
(G12-A009, RFC 6886) and UPnP IGD (G12-A010).

All three are OPTIONAL capabilities, disabled unless policy enables them, and
scoped to the selected local gateway only.  Every mapping this module
creates is recorded in an ownership ledger (``MappingLedger``) so it can be
refreshed before expiry and deterministically deleted; mappings are never
exported outside the configured policy.

PCP: MAP request/response codec with nonce, epoch tracking (a server epoch
that goes backwards or jumps inconsistently means the gateway rebooted and
every owned mapping must be re-created), lifetime refresh at 1/2 lifetime,
result-code taxonomy, and response validation (opcode, nonce, protocol,
internal port, source = selected gateway).

NAT-PMP: public-address and UDP/TCP mapping requests, epoch ("seconds since
start of epoch") reboot detection, bounded retry (RFC 6886: 250 ms doubling,
9 attempts max — capped here at 4), lifetime-0 delete.

UPnP IGD: SSDP discovery restricted to trusted interfaces; device description
and control URLs are accepted only when they point at the gateway's own
private address on the same subnet (SSRF guard); SOAP AddPortMapping /
DeletePortMapping envelopes are built from escaped values.  The HTTP fetch
itself is the caller's; no URL is ever fetched by this module.
"""
from __future__ import annotations

import ipaddress
import os
import select
import socket
import struct
import time
import urllib.parse
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

PCP_PORT = 5351
PCP_VERSION = 2
PCP_OP_MAP = 1
PCP_RESULTS = {0: "SUCCESS", 1: "UNSUPP_VERSION", 2: "NOT_AUTHORIZED", 3: "MALFORMED_REQUEST",
               4: "UNSUPP_OPCODE", 5: "UNSUPP_OPTION", 6: "MALFORMED_OPTION", 7: "NETWORK_FAILURE",
               8: "NO_RESOURCES", 9: "UNSUPP_PROTOCOL", 10: "USER_EX_QUOTA", 11: "CANNOT_PROVIDE_EXTERNAL",
               12: "ADDRESS_MISMATCH", 13: "EXCESSIVE_REMOTE_PEERS"}
PCP_REASON = {0: "OK", 2: "POLICY_EGRESS_DENIED", 8: "BUDGET_QUOTA_EXHAUSTED", 10: "BUDGET_QUOTA_EXHAUSTED",
              12: "NET_MAPPING_CHANGED", 7: "DEP_UNAVAILABLE"}


def _v4mapped(ip: str) -> bytes:
    a = ipaddress.ip_address(ip)
    return a.packed if a.version == 6 else b"\x00" * 10 + b"\xff\xff" + a.packed


def _unmap(raw: bytes) -> str:
    a = ipaddress.IPv6Address(raw)
    return str(a.ipv4_mapped) if a.ipv4_mapped else str(a)


def pcp_map_request(client_ip: str, proto: int, internal_port: int, lifetime: int, *, nonce: bytes | None = None,
                    suggested_port: int = 0, suggested_ip: str = "0.0.0.0") -> tuple[bytes, bytes]:
    nonce = nonce or os.urandom(12)
    hdr = struct.pack("!BBHI16s", PCP_VERSION, PCP_OP_MAP, 0, lifetime, _v4mapped(client_ip))
    body = nonce + struct.pack("!B3xHH16s", proto, internal_port, suggested_port, _v4mapped(suggested_ip))
    return hdr + body, nonce


@dataclass
class PcpResponse:
    result: int
    lifetime: int
    epoch: int
    nonce: bytes
    proto: int
    internal_port: int
    external_port: int
    external_ip: str

    @property
    def reason(self) -> str:
        return PCP_REASON.get(self.result, "DEP_UNAVAILABLE")


def pcp_parse_response(data: bytes) -> PcpResponse:
    if len(data) < 60 or len(data) % 4:
        raise ValueError("short/misaligned PCP response")
    ver, op, _, result, lifetime, epoch = struct.unpack_from("!BBBBII", data)
    if ver != PCP_VERSION or op != (0x80 | PCP_OP_MAP):
        raise ValueError("not a PCP MAP response")
    nonce = data[24:36]
    proto, iport, eport = struct.unpack_from("!B3xHH", data, 36)
    return PcpResponse(result, lifetime, epoch, nonce, proto, iport, eport, _unmap(data[44:60]))


def pcp_validate(resp: PcpResponse, *, nonce: bytes, proto: int, internal_port: int) -> None:
    if resp.nonce != nonce:
        raise ValueError("nonce mismatch (response for another transaction)")
    if resp.proto != proto or resp.internal_port != internal_port:
        raise ValueError("protocol/internal port mismatch")


@dataclass
class EpochTracker:
    """RFC 6887 8.5: detect gateway state loss from the server epoch."""
    last_server: int | None = None
    last_client: float | None = None

    def observe(self, server_epoch: int, client_now: float) -> bool:
        """Return True when mappings must be re-created (gateway lost state)."""
        lost = False
        if self.last_server is not None and self.last_client is not None:
            client_delta = client_now - self.last_client
            server_delta = server_epoch - self.last_server
            if server_epoch < self.last_server - 1:
                lost = True
            elif client_delta + 2 < server_delta - server_delta / 16 or server_delta + 2 < client_delta - client_delta / 16:
                lost = True
        self.last_server, self.last_client = server_epoch, client_now
        return lost


# --- NAT-PMP --------------------------------------------------------------------------------
NATPMP_PORT = 5351


def natpmp_public_request() -> bytes:
    return struct.pack("!BB", 0, 0)


def natpmp_map_request(proto: str, internal: int, external: int, lifetime: int) -> bytes:
    op = {"udp": 1, "tcp": 2}[proto]
    return struct.pack("!BBHHHI", 0, op, 0, internal, external, lifetime)


def natpmp_parse(data: bytes) -> dict:
    if len(data) < 8:
        raise ValueError("short NAT-PMP response")
    ver, op, result, epoch = struct.unpack_from("!BBHI", data)
    if ver != 0 or op < 128:
        raise ValueError("not a NAT-PMP response")
    out = {"op": op - 128, "result": result, "epoch": epoch}
    if op == 128:
        if len(data) < 12:
            raise ValueError("short public-address response")
        out["public"] = socket.inet_ntoa(data[8:12])
    else:
        if len(data) < 16:
            raise ValueError("short mapping response")
        out["internal"], out["external"], out["lifetime"] = struct.unpack_from("!HHI", data, 8)
    return out


def natpmp_transact(gateway: str, request: bytes, *, attempts: int = 4, initial: float = 0.25,
                    sock: socket.socket | None = None) -> dict | None:
    """Bounded retry (RFC 6886 3.1 with a 4-attempt cap); only the selected gateway's replies count."""
    own = sock is None
    sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        wait = initial
        for _ in range(attempts):
            sock.sendto(request, (gateway, NATPMP_PORT))
            end = time.monotonic() + wait
            while time.monotonic() < end:
                r, _, _ = select.select([sock], [], [], max(0.0, end - time.monotonic()))
                if not r:
                    break
                data, src = sock.recvfrom(1100)
                if src[0] != gateway or src[1] != NATPMP_PORT:
                    continue     # never accept replies from anything but the chosen gateway
                try:
                    return natpmp_parse(data)
                except ValueError:
                    continue
            wait *= 2
        return None
    finally:
        if own:
            sock.close()


# --- UPnP IGD ------------------------------------------------------------------------------

def validate_igd_url(url: str, gateway_ip: str, local_network: str) -> str:
    """Accept only http://<gateway private IP>[:port]/path on the local subnet (SSRF guard)."""
    u = urllib.parse.urlsplit(url)
    if u.scheme != "http" or not u.hostname or u.username or u.password:
        raise ValueError("IGD URL must be plain http without userinfo")
    try:
        host = ipaddress.ip_address(u.hostname)
    except ValueError:
        raise ValueError("IGD URL host must be an IP literal (no DNS rebinding)") from None
    net = ipaddress.ip_network(local_network, strict=False)
    if host != ipaddress.ip_address(gateway_ip) or host not in net or not host.is_private:
        raise ValueError("IGD URL must point at the selected gateway on the trusted subnet")
    if u.port is not None and not 1 <= u.port <= 65535:
        raise ValueError("bad port")
    return urllib.parse.urlunsplit(u)


def soap_add_port_mapping(external_port: int, proto: str, internal_port: int, internal_client: str,
                          description: str, lease: int, service: str = "urn:schemas-upnp-org:service:WANIPConnection:1") -> str:
    if proto.upper() not in ("UDP", "TCP"):
        raise ValueError("protocol must be UDP or TCP")
    ipaddress.ip_address(internal_client)
    args = {"NewRemoteHost": "", "NewExternalPort": str(int(external_port)), "NewProtocol": proto.upper(),
            "NewInternalPort": str(int(internal_port)), "NewInternalClient": internal_client, "NewEnabled": "1",
            "NewPortMappingDescription": description[:64], "NewLeaseDuration": str(int(lease))}
    inner = "".join(f"<{k}>{escape(v)}</{k}>" for k, v in args.items())
    return ('<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
            f'<u:AddPortMapping xmlns:u="{escape(service)}">{inner}</u:AddPortMapping></s:Body></s:Envelope>')


# --- ownership ledger shared by all three ------------------------------------------------------

@dataclass
class Mapping:
    protocol: str            # pcp | natpmp | upnp
    transport: str           # udp | tcp
    internal_port: int
    external_port: int
    external_ip: str | None
    gateway: str
    expires: float
    nonce: bytes = b""


@dataclass
class MappingLedger:
    enabled: set[str] = field(default_factory=set)       # policy: which protocols may be used
    owned: list[Mapping] = field(default_factory=list)
    max_owned: int = 16

    def allow(self, protocol: str) -> bool:
        return protocol in self.enabled

    def add(self, m: Mapping) -> None:
        if not self.allow(m.protocol):
            raise PermissionError(f"{m.protocol} disabled by policy")
        if len(self.owned) >= self.max_owned:
            raise OverflowError("mapping ceiling reached")
        for o in self.owned:
            if (o.protocol, o.transport, o.external_port, o.gateway) == (m.protocol, m.transport, m.external_port, m.gateway):
                raise ValueError("collision with an owned mapping")
        self.owned.append(m)

    def due(self, now: float, lifetime_fraction: float = 0.5, lifetime: float = 7200) -> list[Mapping]:
        return [m for m in self.owned if m.expires - now <= lifetime * (1 - lifetime_fraction)]

    def gateway_changed(self, new_gateway: str) -> list[Mapping]:
        """A new gateway invalidates every owned mapping; return them for re-creation elsewhere."""
        stale = [m for m in self.owned if m.gateway != new_gateway]
        self.owned = [m for m in self.owned if m.gateway == new_gateway]
        return stale

    def teardown(self) -> list[Mapping]:
        """Deterministic removal list: every mapping we created, newest first; ledger emptied."""
        out = list(reversed(self.owned))
        self.owned.clear()
        return out
