"""MC-007 -- explicit socket / address / DNS authority.

No socket is created unless a ``NetPolicy`` explicitly allows the (operation,
family, protocol, address, port) tuple.  Address checks run on the *numeric*
address actually used (after DNS), so a hostname cannot launder a denied IP.
DNS itself is a separate authority with a name allowlist.  Per-instance
quotas bound open sockets.
"""
from __future__ import annotations

import ipaddress
import socket
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import ErrorCode, Inv13Error, from_os_error

_FAMILIES = {"inet": socket.AF_INET, "inet6": socket.AF_INET6}
_PROTOS = {"tcp": socket.SOCK_STREAM, "udp": socket.SOCK_DGRAM}


@dataclass(frozen=True)
class NetRule:
    op: str                    # connect | bind | listen
    proto: str                 # tcp | udp
    cidr: str
    ports: tuple[int, int]     # inclusive range

    def matches(self, op: str, proto: str, ip: ipaddress._BaseAddress, port: int) -> bool:
        net = ipaddress.ip_network(self.cidr, strict=False)
        return (self.op == op and self.proto == proto and ip.version == net.version
                and ip in net and self.ports[0] <= port <= self.ports[1])


@dataclass
class NetPolicy:
    rules: list[NetRule] = field(default_factory=list)
    dns_names: frozenset[str] = frozenset()
    families: frozenset[str] = frozenset({"inet"})
    max_sockets: int = 16

    def allows(self, op: str, proto: str, ip: str, port: int) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        fam = "inet" if addr.version == 4 else "inet6"
        if fam not in self.families or not (0 <= port <= 65535):
            return False
        return any(r.matches(op, proto, addr, port) for r in self.rules)


class SocketProvider:
    """Hands out real sockets only through policy. Guests never see ``socket``."""

    def __init__(self, policy: NetPolicy, resolver: Callable[[str], list[str]] | None = None) -> None:
        self.policy = policy
        self._resolver = resolver or (lambda host: sorted({ai[4][0] for ai in socket.getaddrinfo(host, None)}))
        self._open: set[socket.socket] = set()
        self._lock = threading.Lock()

    def _admit(self) -> None:
        with self._lock:
            self._open = {s for s in self._open if s.fileno() != -1}
            if len(self._open) >= self.policy.max_sockets:
                raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, "sockets")

    def resolve(self, name: str) -> list[str]:
        if not isinstance(name, str) or len(name) > 253:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT)
        n = name.lower().rstrip(".")
        if not any(n == a or (a.startswith("*.") and n.endswith(a[1:])) for a in self.policy.dns_names):
            raise Inv13Error(ErrorCode.DESTINATION_DENIED, "dns")
        try:
            return self._resolver(n)
        except OSError as exc:
            raise from_os_error(exc) from None

    def _new(self, ip: str, proto: str) -> socket.socket:
        self._admit()
        fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
        s = socket.socket(fam, _PROTOS[proto])
        with self._lock:
            self._open.add(s)
        return s

    def connect(self, ip: str, port: int, proto: str = "tcp", timeout: float = 5.0) -> socket.socket:
        if proto not in _PROTOS or not self.policy.allows("connect", proto, ip, port):
            raise Inv13Error(ErrorCode.DESTINATION_DENIED, (ip, port, proto))
        s = self._new(ip, proto)
        s.settimeout(timeout)
        try:
            s.connect((ip, port))
        except OSError as exc:
            s.close()
            raise from_os_error(exc) from None
        return s

    def listen(self, ip: str, port: int, backlog: int = 16) -> socket.socket:
        if not (self.policy.allows("bind", "tcp", ip, port) and self.policy.allows("listen", "tcp", ip, port)):
            raise Inv13Error(ErrorCode.DESTINATION_DENIED, (ip, port))
        s = self._new(ip, "tcp")
        try:
            s.bind((ip, port))
            s.listen(min(backlog, 128))
        except OSError as exc:
            s.close()
            raise from_os_error(exc) from None
        return s

    def open_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._open if s.fileno() != -1)
