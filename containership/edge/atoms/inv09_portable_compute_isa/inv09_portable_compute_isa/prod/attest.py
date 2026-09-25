"""M08 - validation-result attestation (Ed25519), also used for M22 bundle signing.

An attestation binds a verdict to *everything that affected it*: module digest,
profile id, policy-bundle revision + epoch, host-contract revision, engine id,
validator id/version, limits revision, byte-derived features, issue/expiry
time and a nonce.  The signed payload is canonical JSON.  Verification is
fail-closed: unknown key id, bad signature, schema drift, expiry, or any
binding mismatch -> ``ATTESTATION_INVALID``.

Requires the ``cryptography`` package; without it signing/verifying raises
``ATTESTATION_INVALID`` (there is no unsigned fallback).
"""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Mapping

from .errors import Code, InvalidModule
from .registry import canonical_json

SCHEMA = "PK_VALIDATION_ATTESTATION/1"
BUNDLE_SIG_SCHEMA = "PK_SIGNED_BUNDLE/1"
FIELDS = {"schema", "module_digest", "profile", "bundle_revision", "epoch", "host_contract_revision",
          "engine", "validator", "limits_revision", "verdict", "features", "deterministic",
          "issued_at", "expires_at", "nonce", "key_id"}


def _crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (Ed25519PrivateKey,
                                                                       Ed25519PublicKey)
        from cryptography.exceptions import InvalidSignature
        return Ed25519PrivateKey, Ed25519PublicKey, InvalidSignature
    except ImportError:  # pragma: no cover - environment dependent
        raise InvalidModule(Code.ATTESTATION_INVALID, "cryptography (Ed25519) unavailable") from None


class Signer:
    """Holds a private key.  In production this wraps an HSM/KMS handle; the
    in-memory form exists for tests and air-gapped reference deployments."""

    def __init__(self, key_id: str, private_key=None):
        priv_cls, _, _ = _crypto()
        self.key_id = key_id
        self._key = private_key or priv_cls.generate()

    def public_raw(self) -> bytes:
        from cryptography.hazmat.primitives import serialization as s
        return self._key.public_key().public_bytes(s.Encoding.Raw, s.PublicFormat.Raw)

    def sign(self, payload: bytes) -> str:
        return base64.b64encode(self._key.sign(payload)).decode()


class Verifier:
    def __init__(self, trusted: Mapping[str, bytes], clock=time.time, max_skew: float = 30.0):
        _, pub_cls, _ = _crypto()
        self._keys = {k: pub_cls.from_public_bytes(v) for k, v in trusted.items()}
        self._revoked: set[str] = set()
        self.clock = clock
        self.max_skew = max_skew

    def revoke(self, key_id: str) -> None:
        self._revoked.add(key_id)

    def check(self, payload: bytes, key_id: str, sig_b64: str) -> None:
        _, _, invalid = _crypto()
        if key_id in self._revoked or key_id not in self._keys:
            raise InvalidModule(Code.ATTESTATION_INVALID, "untrusted or revoked key id")
        try:
            sig = base64.b64decode(sig_b64, validate=True)
            self._keys[key_id].verify(sig, payload)
        except (invalid, ValueError, TypeError):
            raise InvalidModule(Code.ATTESTATION_INVALID, "signature verification failed") from None


@dataclass(frozen=True)
class Attestation:
    payload: bytes   # canonical JSON
    signature: str

    @property
    def claims(self) -> dict[str, Any]:
        return json.loads(self.payload)

    def to_json(self) -> str:
        return json.dumps({"payload": self.payload.decode(), "signature": self.signature})


def issue(signer: Signer, *, ttl: float = 3600.0, clock=time.time, **claims: Any) -> Attestation:
    now = int(clock())
    body = dict(claims, schema=SCHEMA, issued_at=now, expires_at=now + int(ttl),
                nonce=base64.b16encode(os.urandom(12)).decode().lower(), key_id=signer.key_id)
    if set(body) != FIELDS:
        raise InvalidModule(Code.INTERNAL_ERROR, f"attestation fields {sorted(set(body) ^ FIELDS)}")
    payload = canonical_json(body)
    return Attestation(payload, signer.sign(payload))


def verify(att: Attestation, verifier: Verifier, *, expect: Mapping[str, Any]) -> dict[str, Any]:
    try:
        claims = json.loads(att.payload.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raise InvalidModule(Code.ATTESTATION_INVALID, "payload is not canonical JSON") from None
    if not isinstance(claims, dict) or set(claims) != FIELDS or claims.get("schema") != SCHEMA:
        raise InvalidModule(Code.ATTESTATION_INVALID, "attestation schema mismatch")
    if canonical_json(claims) != att.payload:
        raise InvalidModule(Code.ATTESTATION_INVALID, "payload not canonical")
    verifier.check(att.payload, claims["key_id"], att.signature)
    now = verifier.clock()
    if not (claims["issued_at"] - verifier.max_skew <= now < claims["expires_at"]):
        raise InvalidModule(Code.ATTESTATION_INVALID, "attestation expired or not yet valid")
    for k, v in expect.items():
        if claims.get(k) != v:
            raise InvalidModule(Code.ATTESTATION_INVALID, f"attestation {k} does not match")
    return claims


# ---- M22 signed policy-bundle distribution --------------------------------
def sign_bundle(signer: Signer, bundle_raw: bytes) -> str:
    return json.dumps({"schema": BUNDLE_SIG_SCHEMA, "key_id": signer.key_id,
                       "bundle": base64.b64encode(bundle_raw).decode(),
                       "signature": signer.sign(bundle_raw)}, sort_keys=True)


def open_signed_bundle(envelope: str, verifier: Verifier) -> bytes:
    try:
        e = json.loads(envelope)
    except ValueError:
        e = None
    if not isinstance(e, dict) or set(e) != {"schema", "key_id", "bundle", "signature"} \
            or e["schema"] != BUNDLE_SIG_SCHEMA or not isinstance(e["bundle"], str):
        raise InvalidModule(Code.REGISTRY_INVALID, "signed bundle envelope malformed")
    try:
        raw = base64.b64decode(e["bundle"], validate=True)
    except ValueError:
        raise InvalidModule(Code.REGISTRY_INVALID, "signed bundle envelope malformed") from None
    verifier.check(raw, e["key_id"], e["signature"])
    return raw
