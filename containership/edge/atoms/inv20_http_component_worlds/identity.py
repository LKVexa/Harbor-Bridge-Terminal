"""Workload identity, explicit egress capabilities, and authorisation (checklist components 6 and 10).

* ``Principal`` — typed, stable identifiers (tenant / workload / component instance / node /
  operator / peer).
* ``IdentityVerifier`` — pluggable attestation check (production: mTLS/SPIFFE-equivalent SVID
  verification at the adjacent layer; reference: HMAC-attested identity documents). If
  identity cannot be verified the result is *deny*.
* ``EgressCapability`` — an unforgeable handle (HMAC-SHA256 over a canonical body) bound to
  tenant, workload, environment, the destination-policy digest, an expiry and a version.
  Delegation can only *attenuate* (subset of authorities, earlier expiry, child workload of
  the same tenant). Revocation is by capability id and takes effect on the next check.
* ``CapabilityStore`` — per-tenant namespace; a handle minted for tenant A is not
  resolvable from tenant B's store even if the bytes are replayed.
* ``Authorizer`` — policy decision point wrapper that fails closed when the policy service is
  unavailable, with an optional bounded cached-decision window.

Key material lives behind ``KeyProvider`` (secret reference), never in configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Callable, Dict, FrozenSet, Optional, Set, Tuple

from .errors import Inv20Error

CAP_SCHEMA = "INV20_CAP/1"
CLOCK_SKEW_S = 30


class Unauthenticated(Inv20Error):
    code = "E_UNAUTHENTICATED"


class CapabilityInvalid(Inv20Error):
    code = "E_CAPABILITY_INVALID"


class PolicyUnavailable(Inv20Error):
    code = "E_POLICY_UNAVAILABLE"


class Quarantined(Inv20Error):
    code = "E_QUARANTINED"


class PrincipalKind(str, Enum):
    TENANT = "tenant"
    WORKLOAD = "workload"
    INSTANCE = "component_instance"
    NODE = "node"
    OPERATOR = "operator"
    PEER = "external_peer"


@dataclass(frozen=True)
class Principal:
    kind: PrincipalKind
    tenant: str
    workload: str
    instance: str = ""
    artifact_digest: str = ""          # binds runtime identity to the attested artifact

    def __post_init__(self) -> None:
        for v in (self.tenant, self.workload):
            if not v or not all(c.isalnum() or c in "-_." for c in v) or len(v) > 64:
                raise Unauthenticated("malformed principal identifier")

    @property
    def id(self) -> str:
        return f"{self.kind.value}:{self.tenant}/{self.workload}" + (f"#{self.instance}" if self.instance else "")


class KeyProvider:
    """Secret boundary. Holds keys by id; rotation keeps old keys verifiable until retired."""

    def __init__(self) -> None:
        self._keys: Dict[str, bytes] = {}
        self.active: Optional[str] = None

    def rotate(self, key_id: Optional[str] = None, key: Optional[bytes] = None) -> str:
        kid = key_id or f"k{len(self._keys) + 1}"
        self._keys[kid] = key or secrets.token_bytes(32)
        self.active = kid
        return kid

    def retire(self, key_id: str) -> None:
        self._keys.pop(key_id, None)

    def get(self, key_id: str) -> bytes:
        k = self._keys.get(key_id)
        if k is None:
            raise CapabilityInvalid("unknown key id")
        return k

    def __repr__(self) -> str:  # never print key material
        return f"KeyProvider(keys={sorted(self._keys)}, active={self.active})"


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class IdentityVerifier:
    """Reference verifier for HMAC-attested identity documents (stand-in for SVID checks)."""

    def __init__(self, keys: KeyProvider, clock: Callable[[], float] = time.time) -> None:
        self.keys, self.clock = keys, clock
        self.available = True

    def issue(self, p: Principal, ttl: int = 300) -> str:
        body = {"kind": p.kind.value, "tenant": p.tenant, "workload": p.workload, "instance": p.instance,
                "artifact": p.artifact_digest, "exp": int(self.clock()) + ttl, "kid": self.keys.active}
        mac = hmac.new(self.keys.get(self.keys.active), _canon(body), hashlib.sha256).digest()
        return _b64(_canon(body)) + "." + _b64(mac)

    def verify(self, doc: str, expected_artifact: Optional[str] = None) -> Principal:
        if not self.available:
            raise PolicyUnavailable("identity service unavailable")
        try:
            b, m = doc.split(".")
            raw = _unb64(b)
            body = json.loads(raw)
            key = self.keys.get(body["kid"])
        except (ValueError, KeyError, TypeError, CapabilityInvalid):
            raise Unauthenticated("undecodable identity document") from None
        if not hmac.compare_digest(hmac.new(key, raw, hashlib.sha256).digest(), _unb64(m)):
            raise Unauthenticated("identity signature invalid")
        if body["exp"] + CLOCK_SKEW_S < self.clock():
            raise Unauthenticated("identity expired")
        if expected_artifact is not None and body["artifact"] != expected_artifact:
            raise Unauthenticated("artifact identity mismatch")
        return Principal(PrincipalKind(body["kind"]), body["tenant"], body["workload"], body["instance"],
                         body["artifact"])


@dataclass(frozen=True)
class EgressCapability:
    cap_id: str
    tenant: str
    workload: str
    environment: str
    authorities: FrozenSet[Tuple[str, int]]
    policy_digest: str
    not_before: int
    expires: int
    version: int
    parent: str
    token: str

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.token.encode()).hexdigest()[:16]


class CapabilityStore:
    """Mints, delegates, revokes and resolves capabilities inside one tenant namespace each."""

    def __init__(self, keys: KeyProvider, environment: str, clock: Callable[[], float] = time.time) -> None:
        self.keys, self.environment, self.clock = keys, environment, clock
        self._revoked: Set[str] = set()
        self._quarantined: Set[Tuple[str, str]] = set()
        self.version = 1

    def _sign(self, body: dict) -> str:
        kid = self.keys.active
        body = dict(body, kid=kid, schema=CAP_SCHEMA)
        raw = _canon(body)
        return _b64(raw) + "." + _b64(hmac.new(self.keys.get(kid), raw, hashlib.sha256).digest())

    def mint(self, principal: Principal, authorities, policy_digest: str, ttl: int = 600,
             parent: str = "") -> EgressCapability:
        if principal.kind not in (PrincipalKind.WORKLOAD, PrincipalKind.INSTANCE):
            raise CapabilityInvalid("only workloads hold egress capabilities")
        now = int(self.clock())
        auths = frozenset((h, int(p)) for h, p in authorities)
        body = {"id": secrets.token_hex(8), "tenant": principal.tenant, "workload": principal.workload,
                "env": self.environment, "auth": sorted([list(a) for a in auths]), "pol": policy_digest,
                "nbf": now, "exp": now + ttl, "ver": self.version, "parent": parent}
        tok = self._sign(body)
        return EgressCapability(body["id"], principal.tenant, principal.workload, self.environment, auths,
                                policy_digest, now, now + ttl, self.version, parent, tok)

    def delegate(self, cap: EgressCapability, child: Principal, authorities=None, ttl: Optional[int] = None) -> EgressCapability:
        self.resolve(cap.token, Principal(PrincipalKind.WORKLOAD, cap.tenant, cap.workload))
        if child.tenant != cap.tenant:
            raise CapabilityInvalid("cross-tenant delegation prohibited")
        if not child.workload.startswith(cap.workload + "."):
            raise CapabilityInvalid("delegation only to a child workload")
        want = frozenset(authorities) if authorities is not None else cap.authorities
        if not want <= cap.authorities:
            raise CapabilityInvalid("delegation cannot amplify authority")
        remaining = cap.expires - int(self.clock())
        new_ttl = min(ttl if ttl is not None else remaining, remaining)
        return self.mint(child, want, cap.policy_digest, new_ttl, parent=cap.cap_id)

    def revoke(self, cap_id: str) -> None:
        self._revoked.add(cap_id)

    def revoke_all(self) -> None:
        """Emergency disable of outgoing HTTP: bump version; every earlier capability dies."""
        self.version += 1

    def quarantine(self, tenant: str, workload: str = "*") -> None:
        self._quarantined.add((tenant, workload))

    def release(self, tenant: str, workload: str = "*") -> None:
        self._quarantined.discard((tenant, workload))

    def is_quarantined(self, tenant: str, workload: str) -> bool:
        return (tenant, "*") in self._quarantined or (tenant, workload) in self._quarantined

    def resolve(self, token: str, holder: Principal) -> EgressCapability:
        try:
            b, m = token.split(".")
            raw = _unb64(b)
            body = json.loads(raw)
            key = self.keys.get(body["kid"])
            if body.get("schema") != CAP_SCHEMA:
                raise ValueError
        except (ValueError, KeyError, TypeError, AttributeError):
            raise CapabilityInvalid("undecodable capability") from None
        if not hmac.compare_digest(hmac.new(key, raw, hashlib.sha256).digest(), _unb64(m)):
            raise CapabilityInvalid("forged capability")
        now = self.clock()
        if body["id"] in self._revoked or body["parent"] in self._revoked:
            raise CapabilityInvalid("revoked")
        if body["ver"] != self.version:
            raise CapabilityInvalid("capability epoch superseded")
        if now > body["exp"] or now + CLOCK_SKEW_S < body["nbf"]:
            raise CapabilityInvalid("expired or not yet valid")
        if body["env"] != self.environment:
            raise CapabilityInvalid("wrong environment")
        if body["tenant"] != holder.tenant or body["workload"] != holder.workload:
            raise CapabilityInvalid("capability not bound to this workload")
        if self.is_quarantined(holder.tenant, holder.workload):
            raise Quarantined(holder.id)
        return EgressCapability(body["id"], body["tenant"], body["workload"], body["env"],
                                frozenset((h, int(p)) for h, p in body["auth"]), body["pol"], body["nbf"],
                                body["exp"], body["ver"], body["parent"], token)


@dataclass
class Authorizer:
    """PDP client wrapper: fail closed, with an optional bounded cached-decision window."""

    decide: Callable[[Principal, str, str], bool]
    cache_seconds: float = 0.0
    clock: Callable[[], float] = time.monotonic
    _cache: Dict[Tuple[str, str, str], Tuple[float, bool]] = field(default_factory=dict)

    def check(self, principal: Principal, action: str, target: str) -> bool:
        key = (principal.id, action, target)
        try:
            verdict = bool(self.decide(principal, action, target))
        except Exception:
            hit = self._cache.get(key)
            if hit and self.clock() - hit[0] <= self.cache_seconds and hit[1]:
                return True
            raise PolicyUnavailable("policy decision point unavailable") from None
        self._cache[key] = (self.clock(), verdict)
        return verdict
