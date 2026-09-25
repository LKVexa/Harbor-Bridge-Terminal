"""Component 28 - secret/key isolation model.

Identities hold capability-scoped keys. A key can only sign/verify for the
capabilities and scopes (node/site globs) it was granted; nothing reads keys
from ambient process state. Rotation keeps the previous key verify-only for a
bounded overlap; revocation is immediate.

Signatures use HMAC-SHA256 from the standard library. HMAC is a shared-secret
MAC; deployments that need non-repudiation should back ``KeyRing`` with an
asymmetric signer/HSM behind the same interface (see ADR-0004).
"""
from __future__ import annotations

import fnmatch
import hashlib
import hmac
import json
from dataclasses import dataclass, field

from .errors import ErrorCode, Gap10Error

CAPABILITIES = frozenset({
    "telemetry.publish",      # GAP-09 reporter
    "policy.author",          # may author policy (cannot raise limits alone)
    "policy.approve-relax",   # second party required to relax any limit
    "control.operate",        # quarantine/freeze/disable
    "control.release",        # release quarantine/freeze/disable
    "controller.lead",        # may hold a GAP-10 leadership lease
    "release.sign",           # artifact signing
})


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@dataclass
class KeyEntry:
    key_id: str
    identity: str
    secret: bytes
    capabilities: frozenset[str]
    scopes: tuple[str, ...] = ("*",)
    state: str = "active"  # active | verify-only | revoked
    not_after: float | None = None


@dataclass
class KeyRing:
    _keys: dict[str, KeyEntry] = field(default_factory=dict)

    def add(self, key_id: str, identity: str, secret: bytes, capabilities, scopes=("*",), not_after=None) -> KeyEntry:
        caps = frozenset(capabilities)
        unknown = caps - CAPABILITIES
        if unknown:
            raise ValueError(f"unknown capabilities {sorted(unknown)}")
        if len(secret) < 32:
            raise ValueError("secret must be at least 32 bytes")
        entry = KeyEntry(key_id, identity, bytes(secret), caps, tuple(scopes), "active", not_after)
        self._keys[key_id] = entry
        return entry

    def rotate(self, old_key_id: str, new_key_id: str, new_secret: bytes, overlap_until: float) -> KeyEntry:
        old = self._require(old_key_id)
        new = self.add(new_key_id, old.identity, new_secret, old.capabilities, old.scopes)
        old.state = "verify-only"
        old.not_after = overlap_until
        return new

    def revoke(self, key_id: str) -> None:
        self._require(key_id).state = "revoked"

    def _require(self, key_id: str) -> KeyEntry:
        entry = self._keys.get(key_id)
        if entry is None:
            raise Gap10Error(ErrorCode.KEY_UNKNOWN, key_id)
        return entry

    def sign(self, key_id: str, capability: str, scope: str, payload) -> str:
        entry = self._require(key_id)
        if entry.state != "active":
            raise Gap10Error(ErrorCode.KEY_REVOKED, f"{key_id} is {entry.state}")
        self._check(entry, capability, scope)
        return hmac.new(entry.secret, canonical([capability, scope, payload]), hashlib.sha256).hexdigest()

    def verify(self, key_id: str, capability: str, scope: str, payload, signature: str, now: float | None = None) -> str:
        """Return the authenticated identity or raise a Gap10Error."""
        entry = self._keys.get(key_id)
        if entry is None:
            raise Gap10Error(ErrorCode.KEY_UNKNOWN, key_id)
        if entry.state == "revoked":
            raise Gap10Error(ErrorCode.KEY_REVOKED, key_id)
        if entry.not_after is not None and now is not None and now > entry.not_after:
            raise Gap10Error(ErrorCode.KEY_REVOKED, f"{key_id} expired")
        self._check(entry, capability, scope)
        expected = hmac.new(entry.secret, canonical([capability, scope, payload]), hashlib.sha256).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            raise Gap10Error(ErrorCode.TELEMETRY_BAD_SIGNATURE, f"bad signature for {key_id}")
        return entry.identity

    @staticmethod
    def _check(entry: KeyEntry, capability: str, scope: str) -> None:
        if capability not in entry.capabilities:
            raise Gap10Error(ErrorCode.KEY_SCOPE_DENIED, f"{entry.key_id} lacks {capability}")
        if not any(fnmatch.fnmatchcase(scope, pat) for pat in entry.scopes):
            raise Gap10Error(ErrorCode.KEY_SCOPE_DENIED, f"{entry.key_id} not scoped for {scope}")

    def identity_of(self, key_id: str) -> str:
        return self._require(key_id).identity

    def describe(self) -> list[dict]:
        """Inventory without secrets (safe to log)."""
        return [
            {"key_id": k.key_id, "identity": k.identity, "capabilities": sorted(k.capabilities),
             "scopes": list(k.scopes), "state": k.state, "fingerprint": hashlib.sha256(k.secret).hexdigest()[:16]}
            for k in self._keys.values()
        ]
