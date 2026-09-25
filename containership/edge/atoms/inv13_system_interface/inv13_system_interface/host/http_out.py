"""MC-018 -- outgoing HTTP adapter with SSRF defences.

Destination policy is evaluated on the *resolved* IP of every hop (initial and
each redirect), connections are pinned to that vetted IP (no second DNS
lookup -> no DNS-rebinding window), TLS uses the platform default context with
hostname verification (downgrade is impossible: ``https`` only unless the
policy explicitly lists an ``http`` origin), redirects are bounded and may not
cross to a denied destination or downgrade scheme, and request/response sizes
and timeouts are capped.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urljoin, urlsplit

from .errors import ErrorCode, Inv13Error, from_os_error

_ALWAYS_DENIED = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
    "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15", "224.0.0.0/4", "240.0.0.0/4",
    "::/128", "::1/128", "fc00::/7", "fe80::/10", "ff00::/8", "::ffff:0:0/96", "64:ff9b::/96")]


@dataclass
class HttpPolicy:
    allowed_hosts: frozenset[str]
    allow_http_hosts: frozenset[str] = frozenset()
    allow_private: frozenset[str] = frozenset()      # CIDRs explicitly permitted (e.g. test loopback)
    methods: frozenset[str] = frozenset({"GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"})
    max_redirects: int = 3
    max_request_bytes: int = 1 << 20
    max_response_bytes: int = 8 << 20
    timeout: float = 10.0
    ports: frozenset[int] = frozenset({443, 80})


@dataclass
class Response:
    status: int
    headers: list[tuple[str, str]]
    body: bytes
    url: str
    hops: list[str] = field(default_factory=list)


class HttpOutgoing:
    def __init__(self, policy: HttpPolicy, resolver: Callable[[str], list[str]] | None = None,
                 ssl_context: ssl.SSLContext | None = None) -> None:
        self.policy = policy
        self._resolve = resolver or (lambda h: [ai[4][0] for ai in socket.getaddrinfo(h, None, proto=socket.IPPROTO_TCP)])
        self._ctx = ssl_context or ssl.create_default_context()
        if self._ctx.verify_mode != ssl.CERT_REQUIRED or not self._ctx.check_hostname:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "TLS verification must stay enabled")

    def vet(self, url: str) -> tuple[str, str, int, str, str]:
        if not isinstance(url, str) or len(url) > 8192:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT)
        u = urlsplit(url)
        host = (u.hostname or "").lower()
        if u.username or u.password or not host:
            raise Inv13Error(ErrorCode.DESTINATION_DENIED, "userinfo/host")
        if u.scheme == "https":
            pass
        elif u.scheme == "http" and host in self.policy.allow_http_hosts:
            pass
        else:
            raise Inv13Error(ErrorCode.DESTINATION_DENIED, "scheme")
        if host not in self.policy.allowed_hosts:
            raise Inv13Error(ErrorCode.DESTINATION_DENIED, "host")
        port = u.port or (443 if u.scheme == "https" else 80)
        if port not in self.policy.ports:
            raise Inv13Error(ErrorCode.DESTINATION_DENIED, "port")
        try:
            ips = self._resolve(host)
        except OSError as exc:
            raise from_os_error(exc) from None
        if not ips:
            raise Inv13Error(ErrorCode.NOT_FOUND, "dns")
        for ip in ips:  # every answer must be acceptable, else rebinding games are possible
            addr = ipaddress.ip_address(ip)
            if any(addr in n for n in _ALWAYS_DENIED) and not any(
                    addr in ipaddress.ip_network(c) for c in self.policy.allow_private):
                raise Inv13Error(ErrorCode.DESTINATION_DENIED, "private address")
        path = (u.path or "/") + (f"?{u.query}" if u.query else "")
        return u.scheme, host, port, ips[0], path

    def request(self, method: str, url: str, body: bytes = b"", headers: dict[str, str] | None = None) -> Response:
        if method not in self.policy.methods:
            raise Inv13Error(ErrorCode.POLICY_DENIED, "method")
        if len(body) > self.policy.max_request_bytes:
            raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, "request body")
        hops: list[str] = []
        prev_scheme = None
        for _ in range(self.policy.max_redirects + 1):
            scheme, host, port, ip, path = self.vet(url)
            if prev_scheme == "https" and scheme == "http":
                raise Inv13Error(ErrorCode.DESTINATION_DENIED, "downgrade")
            prev_scheme = scheme
            hops.append(url)
            resp = self._send(scheme, host, port, ip, method, path, body, headers or {})
            if resp.status in (301, 302, 303, 307, 308):
                loc = dict((k.lower(), v) for k, v in resp.headers).get("location")
                if not loc:
                    return resp
                url = urljoin(url, loc)
                if resp.status == 303 or (resp.status in (301, 302) and method == "POST"):
                    method, body = "GET", b""
                continue
            resp.hops = hops
            return resp
        raise Inv13Error(ErrorCode.POLICY_DENIED, "too many redirects")

    def _send(self, scheme, host, port, ip, method, path, body, headers) -> Response:
        try:
            raw = socket.create_connection((ip, port), timeout=self.policy.timeout)  # pinned IP
            if scheme == "https":
                raw = self._ctx.wrap_socket(raw, server_hostname=host)
            conn = http.client.HTTPConnection(host, port, timeout=self.policy.timeout)
            conn.sock = raw
            hdrs = {k: v for k, v in headers.items() if k.lower() not in ("host", "content-length")}
            conn.request(method, path, body=body or None, headers=hdrs)
            r = conn.getresponse()
            data = r.read(self.policy.max_response_bytes + 1)
            if len(data) > self.policy.max_response_bytes:
                raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, "response body")
            out = Response(r.status, r.getheaders(), data, f"{scheme}://{host}:{port}{path}")
            conn.close()
            return out
        except ssl.SSLError as exc:
            raise Inv13Error(ErrorCode.DESTINATION_DENIED, f"tls: {exc.reason}") from None
        except socket.timeout:
            raise Inv13Error(ErrorCode.TIMED_OUT) from None
        except OSError as exc:
            raise from_os_error(exc) from None
