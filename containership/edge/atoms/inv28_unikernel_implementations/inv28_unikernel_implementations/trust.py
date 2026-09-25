"""Keyed integrity for every document INV-28 loads or emits (MC-030, MC-036, MC-097, MC-098).

Stdlib only, so the primitive is HMAC-SHA256 over canonical JSON with a named key id.  A
:class:`KeyRing` holds trusted keys per *purpose* (``registry``, ``gap15``, ``advisory``,
``ticket``); a key trusted for one purpose never verifies another, so a leaked advisory key cannot
forge a certification.  Verification is constant-time and fails closed on unknown key ids,
missing signatures and any payload change.

Residual risk (THREAT_MODEL T-09, waiver W-002): HMAC is symmetric - every verifier can also sign.
Production deployment must supply keys from a KMS and should move to asymmetric signatures; the
``KeyRing`` interface is the seam for that.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field

from .errors import Inv28Error, Reason
from .model import canonical

PURPOSES = ("registry", "gap15", "advisory", "ticket", "policy")


@dataclass
class KeyRing:
    keys: dict = field(default_factory=dict)   # (purpose, key_id) -> bytes

    def add(self, purpose: str, key_id: str, secret: bytes) -> None:
        if purpose not in PURPOSES:
            raise ValueError(f"unknown key purpose {purpose!r}")
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("keys must be at least 32 bytes")
        self.keys[(purpose, key_id)] = secret

    @classmethod
    def ephemeral(cls, *purposes: str) -> KeyRing:
        ring = cls()
        for p in purposes or PURPOSES:
            ring.add(p, f"{p}-ephemeral", secrets.token_bytes(32))
        return ring

    def default_key_id(self, purpose: str) -> str:
        ids = sorted(k for p, k in self.keys if p == purpose)
        if not ids:
            raise Inv28Error(Reason.DEPENDENCY_UNAVAILABLE, f"no {purpose} signing key configured")
        return ids[0]

    def sign(self, purpose: str, payload: dict, key_id: str | None = None) -> dict:
        key_id = key_id or self.default_key_id(purpose)
        secret = self.keys.get((purpose, key_id))
        if secret is None:
            raise Inv28Error(Reason.DEPENDENCY_UNAVAILABLE, f"no {purpose} key {key_id}")
        mac = hmac.new(secret, canonical(payload), hashlib.sha256).hexdigest()
        return {"alg": "HMAC-SHA256", "purpose": purpose, "key_id": key_id, "mac": mac}

    def verify(self, purpose: str, payload: dict, signature) -> bool:
        if not isinstance(signature, dict) or signature.get("alg") != "HMAC-SHA256" \
                or signature.get("purpose") != purpose:
            return False
        secret = self.keys.get((purpose, signature.get("key_id")))
        mac = signature.get("mac")
        if secret is None or not isinstance(mac, str):
            return False
        return hmac.compare_digest(hmac.new(secret, canonical(payload), hashlib.sha256).hexdigest(), mac)
