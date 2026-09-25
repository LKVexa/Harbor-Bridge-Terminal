"""Authentication, capability authorization, replay defence, key rotation and a
tamper-evident audit log (INV-37-C023, C024, C042, C044, C048, C049).

Mechanism (stdlib only): HMAC-SHA256 signed capability tokens.  This is a
*local* trust mechanism suitable for a single trust domain where the control
plane (the token minter) and the data plane share a key ring delivered as a
file.  It is not mTLS/SPIFFE and not attestation; those remain external
integrations tracked in MISSING_COMPONENTS.md.

Token wire form: ``v1.<kid>.<b64url(json claims)>.<b64url(hmac)>``
Claims: sub, tenant, node, actions[], scope (transfer id or "*"), iat, exp,
nonce, once (bool - single use).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .errors import CodedError, SecurityRejected

DATA_ACTIONS = frozenset({"create-transfer", "attach-buffer", "write-chunk", "read-progress", "resume",
                          "finalize", "cancel"})
ADMIN_ACTIONS = frozenset({"quarantine", "release", "inspect", "administer", "freeze"})
ALL_ACTIONS = DATA_ACTIONS | ADMIN_ACTIONS
TOKEN_VERSION = "v1"


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class KeyRing:
    """kid -> secret.  One active signing key; older keys verify until retired."""

    def __init__(self, keys: Mapping[str, bytes], active: str) -> None:
        if active not in keys:
            raise CodedError("invalid_config", "active key id not in key ring")
        for kid, k in keys.items():
            if len(k) < 32:
                raise CodedError("invalid_config", "keys must be >= 32 bytes", kid=kid)
        self._keys = dict(keys)
        self.active = active
        self.revoked: set[str] = set()
        self._lock = threading.Lock()

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> "KeyRing":
        p = Path(path)
        if os.name == "posix" and p.stat().st_mode & 0o077:
            raise CodedError("invalid_config", "key file must be mode 0600 or stricter")
        raw = json.loads(p.read_text(encoding="utf-8"))
        keys = {kid: bytes.fromhex(v) for kid, v in raw["keys"].items()}
        ring = cls(keys, raw["active"])
        ring.revoked = set(raw.get("revoked", []))
        return ring

    def rotate(self, kid: str, secret: bytes) -> None:
        with self._lock:
            if len(secret) < 32:
                raise CodedError("invalid_config", "keys must be >= 32 bytes")
            self._keys[kid] = secret
            self.active = kid

    def revoke(self, kid: str) -> None:
        with self._lock:
            if kid == self.active:
                raise CodedError("invalid_config", "cannot revoke the active key; rotate first")
            self.revoked.add(kid)

    def get(self, kid: str) -> bytes | None:
        with self._lock:
            if kid in self.revoked:
                return None
            return self._keys.get(kid)

    def signing(self) -> tuple[str, bytes]:
        with self._lock:
            return self.active, self._keys[self.active]


@dataclass(frozen=True)
class Principal:
    sub: str
    tenant: str
    node: str
    actions: frozenset[str]
    scope: str
    exp: float
    kid: str
    once: bool


def mint(ring: KeyRing, *, sub: str, tenant: str, actions: Iterable[str], scope: str = "*", node: str = "*",
         ttl: float = 900.0, once: bool = False, now: float | None = None) -> str:
    acts = sorted(set(actions))
    bad = set(acts) - ALL_ACTIONS
    if bad:
        raise CodedError("invalid_config", "unknown actions", actions=sorted(bad))
    if set(acts) & ADMIN_ACTIONS and set(acts) & DATA_ACTIONS:
        # Least privilege: administrative capabilities are never mixed with data-plane ones.
        raise CodedError("invalid_config", "admin and data-plane actions must be minted separately")
    now = time.time() if now is None else now
    claims = {"sub": sub, "tenant": tenant, "node": node, "actions": acts, "scope": scope,
              "iat": now, "exp": now + ttl, "nonce": secrets.token_hex(12), "once": once}
    kid, key = ring.signing()
    body = _b64e(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
    signing_input = f"{TOKEN_VERSION}.{kid}.{body}".encode()
    return f"{TOKEN_VERSION}.{kid}.{body}.{_b64e(hmac.new(key, signing_input, hashlib.sha256).digest())}"


class Authenticator:
    def __init__(self, ring: KeyRing, *, clock: Callable[[], float] = time.time, clock_skew: float = 30.0,
                 node: str = "*", replay_cache: int = 100_000, audit: "AuditLog | None" = None) -> None:
        self.ring = ring
        self.clock = clock
        self.skew = clock_skew
        self.node = node
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._cap = replay_cache
        self._lock = threading.Lock()
        self.revoked_subjects: set[str] = set()
        self.audit = audit

    def _fail(self, reason: str, code: str = "authentication_failed") -> SecurityRejected:
        if self.audit:
            self.audit.append("authn.denied", {"reason": reason})
        # Caller-visible message is generic (no oracle); reason is audit-only.
        return SecurityRejected(code, "authentication failed" if code == "authentication_failed" else code)

    def verify(self, token: Any) -> Principal:
        try:
            now = self.clock()
        except Exception:  # noqa: BLE001 - time service failure => fail closed
            raise SecurityRejected("security_service_unavailable", "time source unavailable") from None
        if not isinstance(token, str) or token.count(".") != 3:
            raise self._fail("malformed")
        ver, kid, body, sig = token.split(".")
        if ver != TOKEN_VERSION:
            raise self._fail("version")
        key = self.ring.get(kid)
        if key is None:
            raise self._fail("unknown_or_revoked_kid")
        expect = hmac.new(key, f"{ver}.{kid}.{body}".encode(), hashlib.sha256).digest()
        try:
            given = _b64d(sig)
        except (ValueError, TypeError):
            raise self._fail("sig_encoding") from None
        if not hmac.compare_digest(expect, given):
            raise self._fail("bad_signature")
        try:
            c = json.loads(_b64d(body))
        except (ValueError, TypeError):
            raise self._fail("claims_encoding") from None
        if not _claims_ok(c):
            raise self._fail("claims_shape")
        if c.get("iat", 0) > now + self.skew:
            raise self._fail("not_yet_valid")
        if c.get("exp", 0) < now - self.skew:
            raise self._fail("expired")
        if c.get("sub") in self.revoked_subjects:
            raise self._fail("revoked_subject")
        if self.node != "*" and c.get("node") not in ("*", self.node):
            raise self._fail("wrong_node")
        if c.get("once"):
            with self._lock:
                if c["nonce"] in self._seen:
                    if self.audit:
                        self.audit.append("authn.replay", {"sub": c.get("sub")})
                    raise SecurityRejected("replay_detected", "token already used")
                if len(self._seen) >= self._cap:
                    # Evict only nonces whose tokens can no longer verify; never
                    # forget a live nonce (that would re-enable replay).
                    horizon = now - self.skew
                    for n in [n for n, exp in self._seen.items() if exp < horizon]:
                        del self._seen[n]
                    if len(self._seen) >= self._cap:
                        if self.audit:
                            self.audit.append("authn.replay_cache_full", {"sub": c.get("sub")})
                        raise SecurityRejected("security_service_unavailable", "replay cache full")
                self._seen[c["nonce"]] = c["exp"]
        return Principal(c["sub"], c["tenant"], c.get("node", "*"), frozenset(c["actions"]), c.get("scope", "*"),
                         float(c["exp"]), kid, bool(c.get("once")))


def _claims_ok(c: Any) -> bool:
    if not isinstance(c, dict):
        return False
    str_fields = ("sub", "tenant", "nonce")
    if any(not isinstance(c.get(f), str) or not c.get(f) for f in str_fields):
        return False
    if not isinstance(c.get("actions"), list) or not all(isinstance(a, str) for a in c["actions"]):
        return False
    for f in ("iat", "exp"):
        if not isinstance(c.get(f), (int, float)) or isinstance(c.get(f), bool):
            return False
    return isinstance(c.get("scope", "*"), str) and isinstance(c.get("node", "*"), str) and isinstance(c.get("once", False), bool)


NODE_SCOPED_ACTIONS = frozenset({"freeze", "administer"})


class Authorizer:
    """Deny-by-default capability check performed on *every* boundary crossing."""

    def __init__(self, audit: "AuditLog | None" = None) -> None:
        self.audit = audit

    def check(self, p: Principal, action: str, *, tenant: str, transfer_id: str | None = None) -> None:
        reason = None
        if action not in ALL_ACTIONS:
            reason = "unknown_action"
        elif action not in p.actions:
            reason = "missing_capability"
        elif action in NODE_SCOPED_ACTIONS and p.tenant != "*":
            reason = "node_scope_requires_global_admin"
        elif p.tenant != tenant and not (action in ADMIN_ACTIONS and p.tenant == "*"):
            reason = "cross_tenant"
        elif p.scope != "*" and transfer_id is not None and p.scope != transfer_id:
            reason = "out_of_scope"
        if reason:
            if self.audit:
                self.audit.append("authz.denied", {"sub": p.sub, "action": action, "tenant": tenant,
                                                   "transfer_id": transfer_id, "reason": reason})
            raise SecurityRejected("authorization_denied", "not authorized", action=action)
        if action in ADMIN_ACTIONS and self.audit:
            self.audit.append("authz.admin_granted", {"sub": p.sub, "action": action, "tenant": tenant,
                                                      "transfer_id": transfer_id})


class AuditLog:
    """Append-only hash-chained JSONL.  Each record carries ``prev`` and ``mac``
    (HMAC over canonical record) so deletion, reordering or edits are detected
    by ``verify``.  Records never contain payload bytes or tokens."""

    GENESIS = "0" * 64

    def __init__(self, path: str | os.PathLike[str] | None, key: bytes, *, fsync: bool = False) -> None:
        self.path = Path(path) if path else None
        self._key = key
        self._fsync = fsync
        self._lock = threading.Lock()
        self._prev = self.GENESIS
        self.records: list[dict[str, Any]] = []
        if self.path and self.path.exists():
            ok, last, _ = verify_audit(self.path, key)
            if not ok:
                raise CodedError("checkpoint_corrupt", "existing audit log fails verification")
            self._prev = last

    def append(self, event: str, data: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            rec = {"ts": time.time(), "event": event, "data": dict(data), "prev": self._prev}
            blob = json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()
            rec["mac"] = hmac.new(self._key, blob, hashlib.sha256).hexdigest()
            self._prev = hashlib.sha256(blob + rec["mac"].encode()).hexdigest()
            self.records.append(rec)
            if len(self.records) > 10_000:
                del self.records[:-10_000]
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
                    if self._fsync:
                        fh.flush()
                        os.fsync(fh.fileno())
            return rec


def verify_audit(path: str | os.PathLike[str], key: bytes) -> tuple[bool, str, int]:
    prev = AuditLog.GENESIS
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            mac = rec.pop("mac", "")
            if rec.get("prev") != prev:
                return False, prev, n
            blob = json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()
            if not hmac.compare_digest(mac, hmac.new(key, blob, hashlib.sha256).hexdigest()):
                return False, prev, n
            prev = hashlib.sha256(blob + mac.encode()).hexdigest()
            n += 1
    return True, prev, n


# --- encryption at rest / in transit -----------------------------------------
# The standard library has no authenticated cipher.  No encryption dependency is
# approved or pinned for this repository, so the provider registry is empty and
# any configuration requiring encryption fails closed (C047 stays open).
_ENCRYPTION_PROVIDERS: dict[str, Any] = {}


def register_encryption_provider(name: str, provider: Any) -> None:
    """Hook for an approved, pinned AEAD provider (must expose seal/open)."""
    if not (hasattr(provider, "seal") and hasattr(provider, "open")):
        raise CodedError("invalid_config", "provider must expose seal/open")
    _ENCRYPTION_PROVIDERS[name] = provider


def encryption_provider_available() -> bool:
    return bool(_ENCRYPTION_PROVIDERS)


def require_encryption() -> Any:
    if not _ENCRYPTION_PROVIDERS:
        raise CodedError("encryption_unavailable", "no approved encryption provider installed")
    return next(iter(_ENCRYPTION_PROVIDERS.values()))


def check_residency(region: str, allowed: Iterable[str], tenant_regions: Iterable[str] | None = None) -> None:
    allowed = list(allowed)
    tr = list(tenant_regions or [])
    if (allowed and region not in allowed) or (tr and region not in tr):
        raise CodedError("residency_violation", "region not permitted", region=region)

