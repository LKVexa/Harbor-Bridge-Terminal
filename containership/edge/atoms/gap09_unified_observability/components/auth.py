"""Authorization-policy integration (07), authenticated query principals (08),
secret/KMS integration (06) and authenticated transport (05).

07 -- ``PolicyBundle``: capability scopes come from a policy document signed
      (Ed25519, CSP/1) by the authoritative policy service's key, with a
      version, issue time and hard expiry.  A stale/unsigned/downgraded
      bundle fails closed.  The *real* policy service is not in this archive.
08 -- ``QueryAuthenticator``: a query gateway presents a signed principal
      token; tenant/env/site/workload scope is derived from the token plus the
      policy bundle -- a client's self-declared tenant is never identity.
06 -- ``SecretProvider`` protocol + ``EnvelopeGuard``: persistence of any
      sensitive buffer requires a provider; with none configured the guard
      refuses rather than writing plaintext.  No AES exists in the stdlib, so
      no cipher is shipped: a real KMS/AEAD provider is BLOCKED.
05 -- ``server_tls_context``/``client_tls_context``: TLS1.2+ with mandatory
      client certificates (mTLS); principal derived from the verified peer
      certificate subject.
"""
from __future__ import annotations

import ssl
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from . import ed25519
from .canonical import canonical_bytes
from .errors import DependencyUnavailable, Expired, Malformed, Unauthenticated, Unauthorized, Unverifiable

# ------------------------------------------------------------------ 07


@dataclass(frozen=True)
class Scope:
    tenants: frozenset
    environments: frozenset
    sites: frozenset
    workloads: frozenset

    def permits(self, tenant: str, environment: str, site: str, workload: str) -> bool:
        def ok(allowed, v):
            return "*" in allowed or v in allowed
        return ok(self.tenants, tenant) and ok(self.environments, environment) and ok(self.sites, site) and ok(self.workloads, workload)


class PolicyBundle:
    FORMAT = "GAP09-POLICY/1"

    def __init__(self, *, signer_key: bytes) -> None:
        self._key = signer_key
        self._doc: dict | None = None
        self._lock = threading.Lock()

    def load(self, doc: Mapping[str, Any], signature_hex: str, *, now: int) -> None:
        if doc.get("format") != self.FORMAT:
            raise Malformed("unknown policy format")
        try:
            sig = bytes.fromhex(signature_hex)
        except (ValueError, TypeError) as exc:
            raise Unverifiable("policy signature malformed") from exc
        if not ed25519.verify(self._key, canonical_bytes(dict(doc)), sig):
            raise Unverifiable("policy bundle signature invalid")
        if not (doc["issued_at"] <= now < doc["expires_at"]):
            raise Expired("policy bundle outside its validity window")
        with self._lock:
            if self._doc and doc["version"] <= self._doc["version"]:
                raise Unverifiable("policy downgrade/replay refused")
            self._doc = dict(doc)

    def scope_for(self, principal: str, *, now: int) -> Scope:
        with self._lock:
            doc = self._doc
        if doc is None:
            raise DependencyUnavailable("no policy bundle loaded; refusing")
        if now >= doc["expires_at"]:
            raise Expired("policy bundle expired; refusing rather than using stale grants")
        g = doc["grants"].get(principal)
        if g is None:
            raise Unauthorized("principal has no grant")
        return Scope(frozenset(g["tenants"]), frozenset(g.get("environments", ["*"])),
                     frozenset(g.get("sites", ["*"])), frozenset(g.get("workloads", ["*"])))

    @property
    def version(self) -> int | None:
        return self._doc["version"] if self._doc else None


# ------------------------------------------------------------------ 08


class QueryAuthenticator:
    """Verifies ``GAP09-QTOKEN/1`` principal tokens issued by the gateway.

    token = {format, principal, audience, issued_at, expires_at, nonce}
    signed by one of ``issuer_keys`` (kid -> ed25519 public key).
    """

    FORMAT = "GAP09-QTOKEN/1"
    MAX_LIFETIME = 900

    def __init__(self, *, issuer_keys: Mapping[str, bytes], audience: str, policy: PolicyBundle) -> None:
        self.issuer_keys = dict(issuer_keys)
        self.audience = audience
        self.policy = policy

    def authenticate(self, token: Mapping[str, Any], kid: str, signature_hex: str, *, now: int) -> tuple[str, Scope]:
        key = self.issuer_keys.get(kid)
        if key is None:
            raise Unauthenticated("unknown token issuer key")
        if not isinstance(token, Mapping) or token.get("format") != self.FORMAT:
            raise Unauthenticated("malformed token")
        try:
            sig = bytes.fromhex(signature_hex)
        except (ValueError, TypeError) as exc:
            raise Unauthenticated("token signature malformed") from exc
        if not ed25519.verify(key, canonical_bytes(dict(token)), sig):
            raise Unauthenticated("token signature invalid")
        if token.get("audience") != self.audience:
            raise Unauthenticated("token audience mismatch")
        ia, ea = token.get("issued_at"), token.get("expires_at")
        if not isinstance(ia, int) or not isinstance(ea, int) or ea - ia > self.MAX_LIFETIME or not (ia <= now < ea):
            raise Expired("token outside validity window")
        principal = token.get("principal")
        if not isinstance(principal, str) or not principal:
            raise Unauthenticated("token has no principal")
        return principal, self.policy.scope_for(principal, now=now)

    @staticmethod
    def authorize(scope: Scope, *, tenant: str, environment: str, site: str, workload: str) -> None:
        if not scope.permits(tenant, environment, site, workload):
            raise Unauthorized("principal scope does not cover the requested series")


# ------------------------------------------------------------------ 06


class SecretProvider(Protocol):
    def wrap(self, plaintext: bytes, *, purpose: str) -> bytes: ...
    def unwrap(self, blob: bytes, *, purpose: str) -> bytes: ...
    def key_id(self, purpose: str) -> str: ...


class EnvelopeGuard:
    SENSITIVE = frozenset({"wal", "audit_export", "config_secrets", "backup"})

    def __init__(self, provider: SecretProvider | None) -> None:
        self.provider = provider

    def seal(self, data: bytes, *, purpose: str) -> bytes:
        if purpose in self.SENSITIVE:
            if self.provider is None:
                raise DependencyUnavailable("no KMS/secret provider configured; refusing plaintext persistence",
                                            purpose=purpose)
            return self.provider.wrap(data, purpose=purpose)
        return data


# ------------------------------------------------------------------ 05


def server_tls_context(certfile: str, keyfile: str, client_ca: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(certfile, keyfile)
    ctx.load_verify_locations(client_ca)
    ctx.options |= ssl.OP_NO_COMPRESSION
    return ctx


def client_tls_context(certfile: str, keyfile: str, server_ca: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile, keyfile)
    ctx.load_verify_locations(server_ca)
    return ctx


def principal_from_peercert(cert: Mapping[str, Any] | None) -> str:
    if not cert:
        raise Unauthenticated("no verified client certificate")
    for rdn in cert.get("subject", ()):
        for k, v in rdn:
            if k == "commonName" and v:
                return v
    raise Unauthenticated("client certificate has no commonName")
