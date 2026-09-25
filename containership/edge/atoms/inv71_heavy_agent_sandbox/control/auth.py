"""Authentication and capability authorization reference (C023, C024, C042, C044, C048).

Tokens are compact ``base64url(payload).base64url(HMAC-SHA256)`` capabilities
bound to issuer, audience, principal, role, tenant, site, allowed actions,
expiry and a single-use nonce.  HMAC with a shared key is a *reference* for the
semantics (audience, expiry, replay, revocation, tenant binding, skew); the
production design (docs/AUTH.md) requires mTLS workload identities from a PKI
with per-node keys, which this repository cannot supply.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Callable, Iterable

from .errors import ControlError

MAX_TOKEN_BYTES = 4096
DEFAULT_SKEW_S = 30.0
MAX_TTL_S = 900.0

# Capability model (C024-IMP-01).  Default deny; no wildcard; no admin inheritance.
ACTIONS = frozenset({
    "session.create", "session.inspect", "session.exec", "session.attach", "session.stop",
    "session.teardown", "egress.policy.update", "session.freeze", "session.quarantine",
    "node.quarantine", "artifact.promote", "config.activate", "emergency.disable",
    "emergency.enable", "diagnostics.read", "rollback.execute",
})
# Host-level capabilities are held only by the node helper identity (C024-IMP-04).
HOST_ACTIONS = frozenset({"host.kvm.open", "host.tap.create", "host.cgroup.write", "host.overlay.mount"})

ROLES: dict[str, frozenset[str]] = {
    "workload": frozenset({"session.create", "session.inspect", "session.exec", "session.stop", "session.teardown"}),
    "scheduler": frozenset({"session.create", "session.stop", "session.teardown", "session.inspect"}),
    "operator-read": frozenset({"session.inspect", "diagnostics.read"}),
    "operator-contain": frozenset({"session.freeze", "session.quarantine", "node.quarantine", "emergency.disable", "session.inspect"}),
    "policy-editor": frozenset({"egress.policy.update", "config.activate"}),
    "release-manager": frozenset({"artifact.promote", "rollback.execute"}),
    "break-glass": frozenset({"emergency.disable", "emergency.enable", "node.quarantine", "rollback.execute"}),
    "node-helper": HOST_ACTIONS,
}
# Separation of duties (C009-IMP-02, C042-IMP-04): these actions need a second,
# distinct approver principal holding an approving role.
TWO_PERSON = frozenset({"artifact.promote", "emergency.enable", "rollback.execute", "egress.policy.update", "config.activate"})
# Actions whose target tenant must equal the caller's tenant.
TENANT_SCOPED = frozenset({"session.create", "session.inspect", "session.exec", "session.attach",
                           "session.stop", "session.teardown"})


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass(frozen=True)
class Claims:
    iss: str
    aud: str
    sub: str
    role: str
    tenant: str
    site: str
    actions: tuple[str, ...]
    iat: float
    exp: float
    nonce: str
    policy_version: str


class TokenAuthority:
    """Issues and verifies capability tokens; tracks replay and revocation."""

    def __init__(self, key: bytes, issuer: str, *, clock: Callable[[], float],
                 skew_s: float = DEFAULT_SKEW_S, replay_capacity: int = 100_000) -> None:
        if len(key) < 32:
            raise ValueError("token key must be at least 32 bytes")
        self._key, self.issuer, self._clock, self.skew = key, issuer, clock, skew_s
        self._seen: dict[str, float] = {}
        self._revoked_subjects: set[str] = set()
        self._revoked_nonces: set[str] = set()
        self._cap = replay_capacity
        self._lock = threading.Lock()

    def issue(self, *, aud: str, sub: str, role: str, tenant: str, site: str,
              actions: Iterable[str], ttl_s: float, nonce: str, policy_version: str = "1") -> str:
        acts = tuple(sorted(set(actions)))
        if role not in ROLES:
            raise ValueError("unknown role")
        if not set(acts) <= ROLES[role]:
            raise ValueError("requested actions exceed role")
        if not 0 < ttl_s <= MAX_TTL_S:
            raise ValueError("ttl out of range")
        now = self._clock()
        payload = json.dumps({"iss": self.issuer, "aud": aud, "sub": sub, "role": role, "tenant": tenant,
                              "site": site, "actions": acts, "iat": now, "exp": now + ttl_s,
                              "nonce": nonce, "pv": policy_version},
                             sort_keys=True, separators=(",", ":")).encode()
        sig = hmac.new(self._key, payload, hashlib.sha256).digest()
        return f"{_b64(payload)}.{_b64(sig)}"

    def sweep(self) -> int:
        """Forget nonces whose tokens can no longer verify (expired beyond skew)."""
        with self._lock:
            now = self._clock()
            dead = [k for k, e in self._seen.items() if e + self.skew < now]
            for k in dead:
                del self._seen[k]
            return len(dead)

    def revoke_subject(self, sub: str) -> None:
        with self._lock:
            self._revoked_subjects.add(sub)

    def verify(self, token: str | None, *, aud: str, consume: bool = True) -> Claims:
        if not token:
            raise ControlError("AUTHN.MISSING_CREDENTIAL")
        if not isinstance(token, str) or len(token) > MAX_TOKEN_BYTES or token.count(".") != 1:
            raise ControlError("AUTHN.INVALID_CREDENTIAL", "shape")
        p64, s64 = token.split(".")
        try:
            payload, sig = _unb64(p64), _unb64(s64)
        except Exception:
            raise ControlError("AUTHN.INVALID_CREDENTIAL", "encoding") from None
        if not hmac.compare_digest(sig, hmac.new(self._key, payload, hashlib.sha256).digest()):
            raise ControlError("AUTHN.INVALID_CREDENTIAL", "signature")
        try:
            d = json.loads(payload)
            c = Claims(d["iss"], d["aud"], d["sub"], d["role"], d["tenant"], d["site"],
                       tuple(d["actions"]), float(d["iat"]), float(d["exp"]), d["nonce"], d["pv"])
        except Exception:
            raise ControlError("AUTHN.INVALID_CREDENTIAL", "claims") from None
        now = self._clock()
        if c.iss != self.issuer:
            raise ControlError("AUTHN.INVALID_CREDENTIAL", "issuer")
        if c.aud != aud:
            raise ControlError("AUTHN.WRONG_AUDIENCE")
        if c.iat > now + self.skew:
            raise ControlError("AUTHN.INVALID_CREDENTIAL", "issued in future beyond skew")
        if now > c.exp + self.skew:
            raise ControlError("AUTHN.EXPIRED")
        with self._lock:
            if c.sub in self._revoked_subjects or c.nonce in self._revoked_nonces:
                raise ControlError("AUTHN.REVOKED")
            if consume:
                if c.nonce in self._seen:
                    raise ControlError("AUTHN.REPLAYED")
                if len(self._seen) >= self._cap:
                    # Bounded, but never by forgetting a nonce whose token can still verify:
                    # evicting a live nonce would let an attacker flood the cache and then
                    # replay (found by the v4.3.0 adversarial review).  Refuse instead.
                    for k in [k for k, e in self._seen.items() if e + self.skew < now]:
                        del self._seen[k]
                    if len(self._seen) >= self._cap:
                        raise ControlError("CAPACITY.ADMISSION_REJECTED", "replay cache full of live nonces")
                self._seen[c.nonce] = c.exp
                self._n = getattr(self, "_n", 0) + 1
        if consume and self._n % 256 == 0:
            self.sweep()
        return c


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    action: str
    principal: str
    policy_version: str


def authorize(claims: Claims, action: str, *, tenant: str, site: str,
              approver: Claims | None = None) -> Decision:
    """Default-deny, reason-coded capability check (C024-IMP-02/03/05)."""
    def deny(reason: str) -> Decision:
        return Decision(False, reason, action, claims.sub, claims.policy_version)
    if action not in ACTIONS and action not in HOST_ACTIONS:
        return deny("AUTHZ.UNKNOWN_ACTION")
    if action in HOST_ACTIONS and claims.role != "node-helper":
        return deny("AUTHZ.HOST_CAPABILITY_REQUIRES_NODE_HELPER")
    if action not in ROLES.get(claims.role, frozenset()):
        return deny("AUTHZ.ROLE_LACKS_ACTION")
    if action not in claims.actions:
        return deny("AUTHZ.TOKEN_LACKS_ACTION")
    if claims.site != site:
        return deny("AUTHZ.SITE_MISMATCH")
    if action in TENANT_SCOPED and claims.tenant != tenant:
        return deny("AUTHZ.TENANT_MISMATCH")
    if action in TWO_PERSON:
        if approver is None:
            return deny("AUTHZ.SECOND_APPROVER_REQUIRED")
        if approver.sub == claims.sub:
            return deny("AUTHZ.SELF_APPROVAL")
        if action not in approver.actions or approver.site != site:
            return deny("AUTHZ.APPROVER_LACKS_ACTION")
    return Decision(True, "AUTHZ.ALLOWED", action, claims.sub, claims.policy_version)
