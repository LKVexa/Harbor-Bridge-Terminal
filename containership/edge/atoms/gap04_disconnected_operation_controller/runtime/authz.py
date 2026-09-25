"""Authentication and authorization for every external boundary (GAP04-C14).

Identity comes from the transport: an mTLS peer certificate carrying a
SPIFFE-style URI SAN (``spiffe://<trust-domain>/<path>``). ``server_tls_context``
builds a TLS 1.3, client-cert-required context. ``Authorizer`` is deny-by-
default: each boundary lists the identities and capabilities allowed; anything
unlisted, from a foreign trust domain, or unauthenticated is refused (E0104).
"""
from __future__ import annotations

import re
import ssl
from dataclasses import dataclass, field

from .errors import Unauthorized

SPIFFE = re.compile(r"^spiffe://([a-z0-9.-]+)/([A-Za-z0-9._/-]+)$")
BOUNDARIES = frozenset({"lease.install", "policy.install", "trust.install", "decide", "reconcile", "health.read",
                        "metrics.read", "override.request", "override.approve", "quarantine", "quarantine.release",
                        "config.activate", "backup", "restore"})


@dataclass(frozen=True)
class Principal:
    spiffe_id: str
    trust_domain: str
    authenticated: bool = True


def principal_from_peercert(cert: dict | None) -> Principal:
    if not cert:
        raise Unauthorized("no authenticated peer certificate")
    uris = [v for (k, v) in cert.get("subjectAltName", ()) if k == "URI"]
    ids = [u for u in uris if SPIFFE.match(u)]
    if len(ids) != 1:
        raise Unauthorized("peer certificate must carry exactly one SPIFFE URI SAN")
    return Principal(ids[0], SPIFFE.match(ids[0]).group(1))


def server_tls_context(cert_file: str, key_file: str, ca_file: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(cert_file, key_file)
    ctx.load_verify_locations(ca_file)
    return ctx


def client_tls_context(cert_file: str, key_file: str, ca_file: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(cert_file, key_file)
    ctx.load_verify_locations(ca_file)
    return ctx


@dataclass
class Authorizer:
    trust_domain: str
    rules: dict[str, set[str]] = field(default_factory=dict)  # boundary -> allowed spiffe ids

    def allow(self, boundary: str, spiffe_id: str) -> None:
        if boundary not in BOUNDARIES:
            raise ValueError(f"unknown boundary {boundary}")
        self.rules.setdefault(boundary, set()).add(spiffe_id)

    def check(self, boundary: str, principal: Principal | None) -> Principal:
        if principal is None or not principal.authenticated:
            raise Unauthorized("unauthenticated caller", details={"boundary": boundary})
        if boundary not in BOUNDARIES:
            raise Unauthorized("unknown boundary", details={"boundary": boundary})
        if principal.trust_domain != self.trust_domain:
            raise Unauthorized("foreign trust domain", details={"boundary": boundary})
        if principal.spiffe_id not in self.rules.get(boundary, ()):
            raise Unauthorized("principal not allowed at boundary", details={"boundary": boundary, "principal": principal.spiffe_id})
        return principal
