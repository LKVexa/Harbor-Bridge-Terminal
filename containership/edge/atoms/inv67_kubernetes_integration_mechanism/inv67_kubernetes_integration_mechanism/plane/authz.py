"""Authentication and least-privilege authorization (items 24, 25).

* Callers of the plane (the Kubernetes watch path, the operator API, the
  downstream callback) present a ``Principal`` established by a verifier —
  a ServiceAccount token reviewed via TokenReview in-cluster, or an mTLS
  peer identity. No trust is inherited from network location or namespace.
* Authorization is deny-by-default: each principal holds explicit
  (verb, resource, namespace) grants; wildcard namespace grants are allowed
  only for the controller's own ServiceAccount and are audited.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field

from .lifecycle import PlaneError


@dataclass(frozen=True)
class Principal:
    subject: str               # e.g. system:serviceaccount:inv67-system:inv67-controller
    groups: tuple[str, ...] = ()
    method: str = "none"       # tokenreview | mtls | test


@dataclass(frozen=True)
class Grant:
    verb: str
    resource: str
    namespace: str             # "*" = all


@dataclass
class Policy:
    grants: dict[str, set[Grant]] = field(default_factory=dict)

    def allow(self, subject: str, *grants: Grant) -> None:
        self.grants.setdefault(subject, set()).update(grants)

    def check(self, p: Principal, verb: str, resource: str, namespace: str) -> None:
        if p.method == "none":
            raise PlaneError("INV67_UNAUTHORIZED", "unauthenticated principal")
        for g in self.grants.get(p.subject, ()):
            if g.verb in (verb, "*") and g.resource == resource and g.namespace in (namespace, "*"):
                return
        raise PlaneError("INV67_UNAUTHORIZED", f"{p.subject} may not {verb} {resource} in {namespace}",
                         subject=p.subject, verb=verb, resource=resource, namespace=namespace)


CONTROLLER_SA = "system:serviceaccount:inv67-system:inv67-controller"


def default_policy() -> Policy:
    """Least-privilege policy mirroring deploy/base/rbac.yaml."""
    pol = Policy()
    pol.allow(CONTROLLER_SA,
              Grant("get", "wasmworkloads", "*"), Grant("list", "wasmworkloads", "*"),
              Grant("watch", "wasmworkloads", "*"), Grant("update", "wasmworkloads", "*"),
              Grant("update", "wasmworkloads/status", "*"), Grant("create", "events", "*"),
              Grant("get", "leases", "inv67-system"), Grant("update", "leases", "inv67-system"),
              Grant("create", "leases", "inv67-system"))
    return pol


class TokenVerifier:
    """Verifies HMAC-signed bearer tokens ``subject|expiry|sig`` issued by a
    local test/bootstrap authority. In-cluster, the equivalent is a TokenReview
    call (see kube.HttpKubeClient.token_review). Expired, malformed or
    mis-signed tokens fail closed."""

    def __init__(self, key: bytes, clock=time.time):
        if len(key) < 32:
            raise ValueError("verifier key must be >= 32 bytes")
        self.key, self.clock = key, clock

    def issue(self, subject: str, ttl: float = 300) -> str:
        exp = int(self.clock() + ttl)
        msg = f"{subject}|{exp}".encode()
        return f"{subject}|{exp}|{hmac.new(self.key, msg, hashlib.sha256).hexdigest()}"

    def verify(self, token: str) -> Principal:
        try:
            subject, exp, sig = token.rsplit("|", 2)
            exp_i = int(exp)
        except (ValueError, AttributeError):
            raise PlaneError("INV67_UNAUTHORIZED", "malformed token") from None
        want = hmac.new(self.key, f"{subject}|{exp}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, sig):
            raise PlaneError("INV67_UNAUTHORIZED", "bad token signature")
        if exp_i < self.clock():
            raise PlaneError("INV67_UNAUTHORIZED", "token expired")
        return Principal(subject, (), "test")


def principal_from_mtls(peer_cert_sans: list[str], trusted_spiffe_prefix: str) -> Principal:
    """Map a verified mTLS peer's URI SANs to a principal. The TLS layer must
    already have verified the chain; this only refuses untrusted trust domains."""
    for san in peer_cert_sans:
        if san.startswith(trusted_spiffe_prefix):
            return Principal(san, (), "mtls")
    raise PlaneError("INV67_UNAUTHORIZED", "peer identity outside trusted trust domain")
