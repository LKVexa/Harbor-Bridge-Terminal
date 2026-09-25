"""Boundary authentication, key rotation, replay protection and the
capability/authorization model (MC-013, MC-014, MC-033, MC-034, MC-036,
MC-037 (signing-key rotation), MC-038).

Credential profile ``PKT1`` (HMAC-SHA256 bearer, audience-bound, short-lived):

    PKT1.<kid>.<base64url(canonical JSON claims)>.<base64url(HMAC-SHA256)>

Claims: ``sub`` (principal id), ``role``, ``tenants`` (explicit list, no
wildcards), ``aud`` (must be ``inv62``), ``iat``/``exp`` (unix seconds, max
lifetime enforced), ``nonce`` (single-use for mutating operations) and optional
``node`` (binds a node-agent credential to exactly one topology node).

Transport confidentiality is the lattice/NATS mTLS layer (see
``docs/SECURITY.md``); this layer provides *message-level* authenticity so a
compromised transport hop cannot forge topology mutations.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from collections.abc import Callable, Iterable

from . import errors

AUDIENCE = "inv62"
MAX_LIFETIME_S = 900
CLOCK_SKEW_S = 30
MIN_KEY_BYTES = 32

# ------------------------------------------------------------ permissions
READ_GRAPH = "topo.graph.read"
WRITE_GRAPH = "topo.graph.write"
RESOLVE = "topo.nearest.resolve"
READ_PARTITION = "topo.partition.read"
LEASE = "topo.partition.lease"
ADMIN_FREEZE = "topo.admin.freeze"
ADMIN_QUARANTINE = "topo.admin.quarantine"
CONFIG_ACTIVATE = "topo.config.activate"
DIAG_SENSITIVE = "topo.diag.sensitive"
AUDIT_READ = "topo.audit.read"

#: Identity-to-permission matrix (least privilege, MC-033).  No role holds
#: every permission; no role implies another.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "topology-feed": frozenset({WRITE_GRAPH, READ_GRAPH}),              # GAP-02/GAP-12 adapters
    "scheduler": frozenset({RESOLVE, READ_GRAPH, READ_PARTITION}),      # GAP-03
    "node-agent": frozenset({READ_PARTITION, LEASE}),                   # site coordinator candidates
    "disconnected-controller": frozenset({READ_PARTITION, RESOLVE}),    # GAP-04
    "operator": frozenset({READ_GRAPH, READ_PARTITION, ADMIN_FREEZE, ADMIN_QUARANTINE, CONFIG_ACTIVATE}),
    "auditor": frozenset({AUDIT_READ, READ_GRAPH, DIAG_SENSITIVE}),
}

#: (family, op) -> required permission.  Anything not listed is denied.
OPERATION_PERMISSION: dict[tuple[str, str], str] = {
    ("PK_TOPO_GRAPH", "apply"): WRITE_GRAPH,
    ("PK_TOPO_GRAPH", "get"): READ_GRAPH,
    ("PK_TOPO_NEAREST", "resolve"): RESOLVE,
    ("PK_TOPO_PARTITION", "status"): READ_PARTITION,
    ("PK_TOPO_PARTITION", "acquire"): LEASE,
    ("PK_TOPO_PARTITION", "renew"): LEASE,
    ("PK_TOPO_PARTITION", "validate_token"): READ_PARTITION,
}

MUTATING = frozenset({("PK_TOPO_GRAPH", "apply"), ("PK_TOPO_PARTITION", "acquire"), ("PK_TOPO_PARTITION", "renew")})


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


_B64URL = re.compile(r"[A-Za-z0-9_-]{1,8192}")


def _b64d(text: str) -> bytes:
    if not _B64URL.fullmatch(text):
        raise ValueError("bad base64url")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class Clock:
    """Time source with an explicit health signal (MC-038)."""

    def __init__(self, now: Callable[[], float] = time.time):
        self._now = now
        self.healthy = True

    def now(self) -> float:
        if not self.healthy:
            raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "trusted time source unavailable",
                                   {"dependency": "time"})
        return self._now()


@dataclass
class _Key:
    secret: bytes
    state: str  # active | verify_only | revoked


class KeyRing:
    """HMAC key ring with rotation: exactly one active signing key, any
    number of verify-only keys during overlap, and revoked keys that fail."""

    def __init__(self) -> None:
        self._keys: dict[str, _Key] = {}
        self._lock = threading.Lock()
        self.available = True

    def add(self, kid: str, secret: bytes, *, activate: bool = False) -> None:
        if not isinstance(secret, (bytes, bytearray)) or len(secret) < MIN_KEY_BYTES:
            raise ValueError(f"key {kid!r} must be at least {MIN_KEY_BYTES} bytes")
        if not kid or len(kid) > 64 or not all(c.isalnum() or c in "-_" for c in kid):
            raise ValueError("kid must be 1-64 chars of [A-Za-z0-9-_]")
        with self._lock:
            if kid in self._keys:
                raise ValueError(f"kid {kid!r} already present; keys are never overwritten")
            self._keys[kid] = _Key(bytes(secret), "verify_only")
        if activate:
            self.rotate_to(kid)

    def rotate_to(self, kid: str) -> None:
        with self._lock:
            if kid not in self._keys or self._keys[kid].state == "revoked":
                raise ValueError(f"cannot activate unknown/revoked kid {kid!r}")
            for k in self._keys.values():
                if k.state == "active":
                    k.state = "verify_only"
            self._keys[kid].state = "active"

    def revoke(self, kid: str) -> None:
        with self._lock:
            if kid not in self._keys:
                raise ValueError(f"unknown kid {kid!r}")
            self._keys[kid].state = "revoked"

    def retire_verify_only(self) -> list[str]:
        """End a rotation overlap window: revoke every verify-only key."""
        with self._lock:
            gone = [kid for kid, k in self._keys.items() if k.state == "verify_only"]
            for kid in gone:
                self._keys[kid].state = "revoked"
        return gone

    def active(self) -> tuple[str, bytes]:
        self._check()
        with self._lock:
            for kid, k in self._keys.items():
                if k.state == "active":
                    return kid, k.secret
        raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "no active signing key", {"dependency": "keys"})

    def verifier(self, kid: str) -> bytes | None:
        self._check()
        with self._lock:
            k = self._keys.get(kid)
            return None if k is None or k.state == "revoked" else k.secret

    def states(self) -> dict[str, str]:
        with self._lock:
            return {kid: k.state for kid, k in sorted(self._keys.items())}

    def _check(self) -> None:
        if not self.available:
            raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "key service unavailable", {"dependency": "keys"})


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str
    tenants: frozenset[str]
    permissions: frozenset[str]
    node: str | None = None
    nonce: str = ""
    expires_at: float = 0.0
    kid: str = ""
    issued_at: int = 0


class ReplayCache:
    """Bounded single-use nonce cache.  When full it fails *closed*: new
    mutating requests are refused rather than evicting unexpired nonces."""

    def __init__(self, capacity: int = 100_000):
        self.capacity = capacity
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def spend(self, nonce: str, expires_at: float, now: float) -> None:
        with self._lock:
            while self._seen:
                _oldest, oldest_exp = next(iter(self._seen.items()))
                if oldest_exp + CLOCK_SKEW_S < now:
                    self._seen.popitem(last=False)
                else:
                    break
            if nonce in self._seen:
                raise errors.TopoError(errors.REPLAYED, "credential nonce already used")
            if len(self._seen) >= self.capacity:
                raise errors.TopoError(errors.OVERLOADED, "replay cache saturated; refusing mutating request",
                                       retry_after_ms=1000)
            self._seen[nonce] = expires_at

    def forget(self, nonce: str) -> None:
        with self._lock:
            self._seen.pop(nonce, None)

    def restore(self, entries: Iterable[tuple[str, float]], now: float) -> None:
        """Reload persisted spends (recovery); expired entries are dropped."""
        with self._lock:
            for nonce, exp in sorted(entries, key=lambda e: e[1]):
                if exp + CLOCK_SKEW_S >= now:
                    self._seen[nonce] = exp

    def prune(self, now: float) -> None:
        with self._lock:
            for k in [k for k, exp in self._seen.items() if exp + CLOCK_SKEW_S < now]:
                del self._seen[k]

    def entries(self) -> list[tuple[str, float]]:
        with self._lock:
            return list(self._seen.items())

    def __len__(self) -> int:
        return len(self._seen)


class Authenticator:
    def __init__(self, keyring: KeyRing, clock: Clock | None = None, replay: ReplayCache | None = None,
                 revoked_subjects: Iterable[str] = ()):
        self.keyring = keyring
        self.clock = clock or Clock()
        self.replay = replay or ReplayCache()
        self.revoked_subjects = set(revoked_subjects)
        #: called with (key, expires_at) *before* a nonce is accepted; used to persist spends (restart-safe replay protection)
        self.on_spend: Callable[[str, float], None] | None = None

    def issue(self, subject: str, role: str, tenants: Iterable[str], *, lifetime_s: int = 300,
              node: str | None = None, nonce: str | None = None) -> str:
        """Mint a credential (used by tests, bootstrap and the issuing sidecar)."""
        if role not in ROLE_PERMISSIONS:
            raise ValueError(f"unknown role {role!r}")
        tenants = sorted(set(tenants))
        if not tenants or "*" in tenants:
            raise ValueError("credentials must name explicit tenants")
        if not 0 < lifetime_s <= MAX_LIFETIME_S:
            raise ValueError(f"lifetime must be 1..{MAX_LIFETIME_S}s")
        kid, secret = self.keyring.active()
        now = int(self.clock.now())
        claims = {"sub": subject, "role": role, "tenants": tenants, "aud": AUDIENCE, "iat": now,
                  "exp": now + lifetime_s, "nonce": nonce or secrets.token_urlsafe(12)}
        if node is not None:
            claims["node"] = node
        body = _b64e(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        sig = _b64e(hmac.new(secret, f"PKT1.{kid}.{body}".encode(), hashlib.sha256).digest())
        return f"PKT1.{kid}.{body}.{sig}"

    def authenticate(self, credential: object, *, mutating: bool) -> Principal:
        fail = errors.TopoError(errors.UNAUTHENTICATED, "credential rejected")
        if not isinstance(credential, str) or credential.count(".") != 3:
            raise fail
        scheme, kid, body, sig = credential.split(".")
        if scheme != "PKT1":
            raise fail
        secret = self.keyring.verifier(kid)  # raises DEPENDENCY_UNAVAILABLE when key service is down
        if secret is None:
            raise fail
        try:
            expected = hmac.new(secret, f"PKT1.{kid}.{body}".encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64d(sig)):
                raise fail
            claims = json.loads(_b64d(body))
        except errors.TopoError:
            raise
        except Exception:
            raise fail from None
        now = self.clock.now()
        try:
            sub, role, tenants = claims["sub"], claims["role"], claims["tenants"]
            iat, exp, nonce = claims["iat"], claims["exp"], claims["nonce"]
            ok = (claims.get("aud") == AUDIENCE and isinstance(sub, str) and role in ROLE_PERMISSIONS
                  and isinstance(tenants, list) and tenants and all(isinstance(t, str) and t != "*" for t in tenants)
                  and isinstance(iat, int) and isinstance(exp, int) and 0 < exp - iat <= MAX_LIFETIME_S
                  and iat - CLOCK_SKEW_S <= now < exp + CLOCK_SKEW_S and isinstance(nonce, str) and 8 <= len(nonce) <= 64)
        except (KeyError, TypeError):
            ok = False
        if not ok or sub in self.revoked_subjects:
            raise fail
        node = claims.get("node")
        principal = Principal(sub, role, frozenset(tenants), ROLE_PERMISSIONS[role],
                              node if isinstance(node, str) else None, nonce, float(exp), kid, iat)
        if mutating:
            self.spend(principal)
        return principal

    def spend(self, principal: Principal) -> None:
        """Consume the credential nonce (single use for mutating operations)."""
        key = f"{principal.kid}:{principal.nonce}"
        self.replay.spend(key, principal.expires_at, self.clock.now())
        if self.on_spend is not None:
            try:
                self.on_spend(key, principal.expires_at)
            except Exception:
                self.replay.forget(key)
                raise


@dataclass
class Authorizer:
    """Default-deny policy decision point (MC-014, MC-036)."""

    available: bool = True
    denials: list[dict[str, str]] = field(default_factory=list)

    def authorize(self, principal: Principal, family: str, op: str, tenant: str,
                  *, target_node: str | None = None) -> None:
        if not self.available:
            raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "policy service unavailable; failing closed",
                                   {"dependency": "policy"})
        needed = OPERATION_PERMISSION.get((family, op))
        reason = None
        if needed is None:
            reason = "operation not mapped to a permission"
        elif needed not in principal.permissions:
            reason = f"role {principal.role} lacks {needed}"
        elif tenant not in principal.tenants:
            reason = "tenant not granted"
        elif needed == LEASE and (principal.node is None or principal.node != target_node):
            reason = "node-agent may only lease for its own bound node"
        if reason:
            self.denials.append({"subject": principal.subject, "op": f"{family}.{op}", "tenant": tenant, "reason": reason})
            del self.denials[:-1000]
            raise errors.TopoError(errors.FORBIDDEN, "operation not permitted", {"required": needed or "none"})

    def require(self, principal: Principal, permission: str, tenant: str | None = None) -> None:
        if not self.available:
            raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "policy service unavailable; failing closed",
                                   {"dependency": "policy"})
        if permission not in principal.permissions or (tenant is not None and tenant not in principal.tenants):
            raise errors.TopoError(errors.FORBIDDEN, "operation not permitted", {"required": permission})
