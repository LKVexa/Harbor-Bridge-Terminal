"""Authentication, authorization, admission, tenant isolation, quota/fairness
and secret handling (components 27, 28, 30, 31, 32, 43).

Authentication here verifies HMAC-SHA256 signed bearer tokens (JWT HS256
compact form) with issuer, audience, expiry, not-before and clock-skew checks,
keyed by ``kid`` so keys rotate without downtime.  Production deployments may
instead front the service with Kubernetes TokenReview or an mTLS proxy
(component 29); both yield the same ``Principal`` to the authorizer.
Secrets are only ever referenced (``SecretRef``) and resolved through a
provider; ``repr`` never reveals values.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping

from .errors import AdmissionDenied, Forbidden, QuotaExceeded, Unauthenticated


# ------------------------------------------------------------ secrets (43)


class Secret:
    """Opaque secret value: never printed, never serialised."""

    __slots__ = ("_v",)

    def __init__(self, value: bytes):
        self._v = value

    def reveal(self) -> bytes:
        return self._v

    def __repr__(self) -> str:
        return "Secret([REDACTED])"

    __str__ = __repr__

    def __reduce__(self):  # prevent pickling secrets into dumps
        raise TypeError("Secret values cannot be serialised")


@dataclass(frozen=True)
class SecretRef:
    provider: str  # env | file
    name: str


class SecretResolver:
    """Resolves SecretRefs (env var / mounted file); re-reads on ``rotate``."""

    def __init__(self, *, env: Mapping[str, str] | None = None, root: str = "/var/run/secrets/inv04"):
        self.env = env if env is not None else os.environ
        self.root = root
        self._cache: dict[SecretRef, Secret] = {}
        self._lock = threading.Lock()

    def resolve(self, ref: SecretRef) -> Secret:
        with self._lock:
            if ref in self._cache:
                return self._cache[ref]
            if ref.provider == "env":
                val = self.env.get(ref.name)
                if val is None:
                    raise Unauthenticated(f"secret reference env:{ref.name} is not set")
                s = Secret(val.encode())
            elif ref.provider == "file":
                path = os.path.join(self.root, os.path.basename(ref.name))
                with open(path, "rb") as fh:
                    s = Secret(fh.read().strip())
            else:
                raise ValueError(f"unknown secret provider {ref.provider!r}")
            self._cache[ref] = s
            return s

    def rotate(self) -> None:
        with self._lock:
            self._cache.clear()


# ------------------------------------------------------ authentication (27)


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    groups: tuple[str, ...] = ()
    site: str = ""
    method: str = "token"


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def mint_token(claims: dict, key: Secret, kid: str) -> str:
    """Test/bootstrap helper; production tokens come from the identity provider."""
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT", "kid": kid}, separators=(",", ":")).encode())
    body = _b64e(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    sig = hmac.new(key.reveal(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64e(sig)}"


class TokenAuthenticator:
    def __init__(self, keys: Mapping[str, Secret], *, issuer: str, audience: str, skew: float = 30.0,
                 clock: Callable[[], float] = time.time, max_ttl: float = 3600.0):
        self.keys, self.issuer, self.audience, self.skew, self.clock, self.max_ttl = dict(keys), issuer, audience, skew, clock, max_ttl

    def authenticate(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise Unauthenticated("missing bearer credential")
        token = authorization[7:].strip()
        parts = token.split(".")
        if len(parts) != 3 or len(token) > 8192:
            raise Unauthenticated("malformed credential")
        try:
            header = json.loads(_b64d(parts[0]))
            claims = json.loads(_b64d(parts[1]))
            sig = _b64d(parts[2])
        except (ValueError, json.JSONDecodeError):
            raise Unauthenticated("malformed credential") from None
        if header.get("alg") != "HS256":
            raise Unauthenticated("unsupported credential algorithm")
        key = self.keys.get(header.get("kid", ""))
        if key is None:
            raise Unauthenticated("unknown signing key")
        expect = hmac.new(key.reveal(), f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expect, sig):
            raise Unauthenticated("credential signature invalid")
        now = self.clock()
        if claims.get("iss") != self.issuer:
            raise Unauthenticated("credential issuer rejected")
        aud = claims.get("aud")
        if self.audience not in (aud if isinstance(aud, list) else [aud]):
            raise Unauthenticated("credential audience rejected")
        exp, nbf, iat = claims.get("exp"), claims.get("nbf", 0), claims.get("iat", now)
        if not isinstance(exp, (int, float)) or now > exp + self.skew:
            raise Unauthenticated("credential expired")
        if now + self.skew < nbf:
            raise Unauthenticated("credential not yet valid")
        if exp - iat > self.max_ttl:
            raise Unauthenticated("credential lifetime exceeds policy")
        sub, tenant = claims.get("sub"), claims.get("tenant")
        if not isinstance(sub, str) or not sub or not isinstance(tenant, str) or not tenant:
            raise Unauthenticated("credential lacks subject or tenant")
        return Principal(sub, tenant, tuple(sorted(claims.get("groups", []))), str(claims.get("site", "")))


# ------------------------------------------------------- authorization (28)

VERBS = ("reconcile", "drain", "inventory", "handoff", "configure", "read")


@dataclass(frozen=True)
class Rule:
    groups: tuple[str, ...]
    verbs: tuple[str, ...]
    tenants: tuple[str, ...] = ("$own",)  # "$own" = principal's tenant; "*" = any (platform admins only)
    sites: tuple[str, ...] = ("*",)


@dataclass
class Authorizer:
    """Deny-by-default RBAC. Cross-tenant access needs an explicit '*' rule."""

    rules: list[Rule] = field(default_factory=list)

    def authorize(self, p: Principal, verb: str, *, tenant: str, site: str = "") -> None:
        if verb not in VERBS:
            raise Forbidden(f"unknown verb {verb!r}")
        for r in self.rules:
            if not set(r.groups) & set(p.groups) or verb not in r.verbs:
                continue
            tenant_ok = "*" in r.tenants or tenant in r.tenants or ("$own" in r.tenants and tenant == p.tenant)
            site_ok = "*" in r.sites or site in r.sites
            if tenant_ok and site_ok:
                return
        raise Forbidden(f"{p.subject} may not {verb} in tenant scope", details={"verb": verb})


DEFAULT_RULES = [
    Rule(("inv04:operators",), ("reconcile", "inventory", "read")),
    # Node drains are cluster/site-scoped (a node hosts many tenants), so they are
    # never granted through the per-tenant "$own" rule.
    Rule(("inv04:site-operators",), ("drain",), tenants=("*",)),
    Rule(("inv04:readers",), ("inventory", "read")),
    Rule(("inv04:successor",), ("inventory", "handoff", "read")),
    Rule(("inv04:platform-admins",), VERBS, tenants=("*",)),
]


# -------------------------------------------------- tenant isolation (31)


def tenant_of(namespace: str, mapping: Mapping[str, str]) -> str:
    """Namespace -> tenant; unmapped namespaces belong to no tenant and are invisible."""
    return mapping.get(namespace, "")


def scope_filter(items, tenant: str, mapping: Mapping[str, str], ns_of: Callable = lambda x: x.meta.namespace):
    return [x for x in items if tenant and tenant_of(ns_of(x), mapping) == tenant]


# --------------------------------------------------------- admission (30)


@dataclass
class MaintenanceWindow:
    start: float
    end: float
    sites: tuple[str, ...] = ("*",)


class AdmissionPolicy:
    """Pre-mutation policy: drains only inside maintenance windows (unless
    emergency with a reason), frozen tenants cannot be mutated, and at most
    ``max_concurrent_drains`` per site."""

    def __init__(self, *, windows: list[MaintenanceWindow] | None = None, frozen_tenants: set[str] | None = None,
                 max_concurrent_drains: int = 1, clock: Callable[[], float] = time.time):
        self.windows = windows
        self.frozen = frozen_tenants or set()
        self.max_concurrent = max_concurrent_drains
        self.active: dict[str, int] = {}
        self.clock = clock

    def admit(self, verb: str, p: Principal, *, tenant: str, site: str = "", emergency_reason: str = "") -> None:
        if verb in ("reconcile", "drain") and tenant in self.frozen:
            raise AdmissionDenied(f"tenant is frozen for {verb}", details={"verb": verb})
        if verb == "drain":
            if self.windows is not None and not emergency_reason:
                now = self.clock()
                if not any(w.start <= now < w.end and ("*" in w.sites or site in w.sites) for w in self.windows):
                    raise AdmissionDenied("drain outside maintenance window", details={"site": site})
            if self.active.get(site, 0) >= self.max_concurrent:
                raise AdmissionDenied("concurrent drain limit reached for site", details={"site": site})

    def begin(self, site: str) -> None:
        self.active[site] = self.active.get(site, 0) + 1

    def end(self, site: str) -> None:
        self.active[site] = max(0, self.active.get(site, 0) - 1)


# ---------------------------------------------------- quota/fairness (32)


class FairQueue:
    """Per-tenant in-flight quota with round-robin dispatch (no starvation)."""

    def __init__(self, *, per_tenant_inflight: int = 4, per_tenant_queued: int = 100):
        self.limit, self.qlimit = per_tenant_inflight, per_tenant_queued
        self.inflight: dict[str, int] = {}
        self.queues: dict[str, list] = {}
        self.order: list[str] = []
        self._lock = threading.Lock()

    def submit(self, tenant: str, item) -> None:
        with self._lock:
            q = self.queues.setdefault(tenant, [])
            if len(q) >= self.qlimit:
                raise QuotaExceeded("tenant queue full", details={"limit": self.qlimit})
            q.append(item)
            if tenant not in self.order:
                self.order.append(tenant)

    def next(self):
        with self._lock:
            for _ in range(len(self.order)):
                t = self.order.pop(0)
                self.order.append(t)
                if self.queues.get(t) and self.inflight.get(t, 0) < self.limit:
                    self.inflight[t] = self.inflight.get(t, 0) + 1
                    return t, self.queues[t].pop(0)
            return None

    def complete(self, tenant: str) -> None:
        with self._lock:
            self.inflight[tenant] = max(0, self.inflight.get(tenant, 0) - 1)
