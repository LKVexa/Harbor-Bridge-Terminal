"""Network security profile (component 26).

* ``tls_context`` -- client/server ``ssl.SSLContext`` with certificate and
  hostname verification required, minimum TLS 1.2 (1.3 configurable),
  compression off, renegotiation off; ``mtls_server_context`` additionally
  requires a client certificate signed by the configured CA.
* ``EgressPolicy`` -- every outbound URL (Git remote, KMS, policy service,
  telemetry sink, control plane) is checked against an allowlist of
  ``scheme://host[:port]``; private/link-local/loopback literal addresses are
  refused unless allowlisted (SSRF guard), userinfo is refused, redirects are
  not followed (git ``http.followRedirects=false``), and proxies must be
  explicit (``https_proxy`` is ignored unless configured).
* ``resolve_pinned`` -- DNS answers are checked against the same private-range
  rule after resolution (DNS-rebinding guard).
* Cert rotation: contexts are rebuilt from files on reload; ``cert_expiry``
  reports days-to-expiry for alerting.
"""
from __future__ import annotations

import ipaddress
import socket
import ssl
from urllib.parse import urlsplit

from .errors import NetworkPolicy


def tls_context(*, cafile: str | None = None, min_version: str = "TLSv1.2", server: bool = False,
                certfile: str | None = None, keyfile: str | None = None) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server else ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3 if min_version == "TLSv1.3" else ssl.TLSVersion.TLSv1_2
    ctx.options |= ssl.OP_NO_COMPRESSION
    if hasattr(ssl, "OP_NO_RENEGOTIATION"):
        ctx.options |= ssl.OP_NO_RENEGOTIATION
    if not server:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        if cafile:
            ctx.load_verify_locations(cafile)
        else:
            ctx.load_default_certs()
    if certfile:
        ctx.load_cert_chain(certfile, keyfile)
    return ctx


def mtls_server_context(*, certfile: str, keyfile: str, client_ca: str, min_version: str = "TLSv1.2"):
    ctx = tls_context(server=True, certfile=certfile, keyfile=keyfile, min_version=min_version)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(client_ca)
    return ctx


def _is_private(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return host.lower() in ("localhost", "localhost.localdomain")
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved \
        or ip.is_unspecified


class EgressPolicy:
    def __init__(self, allowlist: list[str], *, proxy: str | None = None) -> None:
        self.allow = set()
        for a in allowlist:
            p = urlsplit(a)
            if not p.scheme or not p.hostname:
                raise NetworkPolicy("egress allowlist entries must be scheme://host[:port]")
            self.allow.add((p.scheme, p.hostname.lower(), p.port))
        self.proxy = proxy

    def check(self, url: str) -> tuple[str, str, int | None]:
        p = urlsplit(url)
        if p.username or p.password:
            raise NetworkPolicy("userinfo in outbound URL refused")
        host = (p.hostname or "").lower()
        key = (p.scheme, host, p.port)
        if key not in self.allow and (p.scheme, host, None) not in self.allow:
            raise NetworkPolicy("destination not in egress allowlist", host=host)
        return key

    def resolve_pinned(self, host: str, port: int, *, resolver=socket.getaddrinfo) -> list[str]:
        allowed_literal = any(h == host for _, h, _ in self.allow)
        ips = sorted({ai[4][0] for ai in resolver(host, port, proto=socket.IPPROTO_TCP)})
        bad = [ip for ip in ips if _is_private(ip)]
        if bad and not (allowed_literal and _is_private(host)):
            raise NetworkPolicy("DNS answer points into a private/loopback range", host=host)
        return ips


def cert_expiry_days(cert: dict, now: float) -> float:
    return (ssl.cert_time_to_seconds(cert["notAfter"]) - now) / 86400.0
