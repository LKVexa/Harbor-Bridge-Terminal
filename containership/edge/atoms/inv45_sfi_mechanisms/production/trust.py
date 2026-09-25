"""Trust material: secret references, keyrings, artifact signatures, sealed descriptors.

C044/C045 (artifact identity, signatures, provenance, anti-rollback), C039 (secrets
as references), C047/C048 (key handling and behaviour when trust services are
unavailable or stale).

* **Secrets are references.**  Configuration carries ``SecretRef`` strings such as
  ``env:INV45_SEAL_KEY_2026A`` or ``file:/run/secrets/seal``; values are resolved at
  use time, never logged, never serialized, and never placed in errors.
* **Artifact signatures** (submitter/CI -> verifier) are Ed25519 over the canonical
  statement ``{artifact_sha256, workload, version, issuer}``.  Public trust roots
  are pinned by key id; revoked or expired keys are refused.  Ed25519 needs the
  ``cryptography`` package (pinned in ``constraints.txt``); when it is absent,
  signature verification fails closed with ``SFI_DEPENDENCY_UNAVAILABLE``.
* **Sealed descriptors** (verifier -> trusted loader, same trust domain) are
  HMAC-SHA256 over canonical JSON binding artifact digest, profile digest,
  proof digest, config digest, tenant, workload, version, nonce and expiry.
* **Freshness.**  A keyring older than ``max_age_seconds`` (revocation freshness)
  is ``SFI_TRUST_STALE``: no new trust is granted from stale material; already
  running instances are unaffected (documented in docs/requirements/SPEC.md S-OFF-*).
"""
from __future__ import annotations

import base64
import hmac
import os
import secrets as _secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .errors import SfiError
from .sfi import canonical_json, sha256_hex

DESCRIPTOR_SCHEMA = "PK_SFI_SEALED_DESCRIPTOR/1"
STATEMENT_SCHEMA = "PK_SFI_ARTIFACT_STATEMENT/1"


# ------------------------------------------------------------------------------ secrets

@dataclass(frozen=True)
class SecretRef:
    ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.ref, str) or not self.ref.startswith(("env:", "file:")):
            raise SfiError("SFI_CONFIG_INVALID", "secret must be a reference (env:NAME or file:PATH)",
                           field="secret_ref")

    def resolve(self) -> bytes:
        kind, _, loc = self.ref.partition(":")
        try:
            if kind == "env":
                val = os.environ[loc].encode("utf-8")
            else:
                val = Path(loc).read_bytes().strip()
        except (KeyError, OSError):
            raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "secret reference could not be resolved",
                           dependency="secret-store", field="secret_ref") from None
        if len(val) < 32:
            raise SfiError("SFI_CONFIG_INVALID", "resolved secret is shorter than 32 bytes",
                           field="secret_ref")
        return val

    def __repr__(self) -> str:  # never print resolved material
        return f"SecretRef({self.ref!r})"


# ------------------------------------------------------------------------------ keyring

@dataclass
class HmacKey:
    key_id: str
    secret: SecretRef
    not_before: float = 0.0
    not_after: float = float("inf")
    revoked: bool = False


@dataclass
class KeyRing:
    """HMAC sealing keys with rotation (one active signer, several verifiers)."""

    keys: dict[str, HmacKey] = field(default_factory=dict)
    active: Optional[str] = None
    loaded_at: float = field(default_factory=time.time)
    max_age_seconds: float = 3600.0
    clock: Callable[[], float] = time.time

    def add(self, key: HmacKey, *, activate: bool = False) -> None:
        self.keys[key.key_id] = key
        if activate:
            self.active = key.key_id

    def revoke(self, key_id: str) -> None:
        if key_id in self.keys:
            self.keys[key_id].revoked = True
        if self.active == key_id:
            self.active = None

    def refresh(self) -> None:
        self.loaded_at = self.clock()

    def _fresh(self) -> None:
        if self.clock() - self.loaded_at > self.max_age_seconds:
            raise SfiError("SFI_TRUST_STALE", "keyring/revocation data is stale", dependency="key-service")

    def _usable(self, key_id: str) -> HmacKey:
        k = self.keys.get(key_id)
        now = self.clock()
        if k is None or k.revoked or not (k.not_before <= now <= k.not_after):
            raise SfiError("SFI_SIGNATURE_INVALID", "sealing key unknown, revoked or outside validity",
                           key_id=key_id)
        return k

    def sign(self, payload: bytes) -> tuple[str, str]:
        self._fresh()
        if self.active is None:
            raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "no active sealing key", dependency="key-service")
        k = self._usable(self.active)
        mac = hmac.new(k.secret.resolve(), payload, "sha256").hexdigest()
        return k.key_id, mac

    def verify(self, key_id: str, payload: bytes, mac: str) -> None:
        self._fresh()
        k = self._usable(key_id)
        expect = hmac.new(k.secret.resolve(), payload, "sha256").hexdigest()
        if not isinstance(mac, str) or not hmac.compare_digest(expect, mac):
            raise SfiError("SFI_SIGNATURE_INVALID", "descriptor MAC does not verify", key_id=key_id)


# ------------------------------------------------------------------------------ artifact signatures

def _ed25519():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except ImportError:  # pragma: no cover - environment dependent
        raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "Ed25519 provider (cryptography) not installed",
                       dependency="cryptography") from None
    return Ed25519PrivateKey, Ed25519PublicKey, InvalidSignature


@dataclass
class TrustRoot:
    key_id: str
    public_key_b64: str
    issuer: str
    not_before: float = 0.0
    not_after: float = float("inf")
    revoked: bool = False


@dataclass
class ArtifactTrustStore:
    roots: dict[str, TrustRoot] = field(default_factory=dict)
    clock: Callable[[], float] = time.time

    def add(self, root: TrustRoot) -> None:
        self.roots[root.key_id] = root

    def revoke(self, key_id: str) -> None:
        if key_id in self.roots:
            self.roots[key_id].revoked = True

    def verify_statement(self, artifact: bytes, signed: dict[str, Any]) -> dict[str, Any]:
        """Verify a signed artifact statement against the exact ``artifact`` bytes."""
        _, Pub, Invalid = _ed25519()
        if not isinstance(signed, dict) or set(signed) != {"statement", "key_id", "signature"}:
            raise SfiError("SFI_SIGNATURE_INVALID", "signed statement envelope malformed")
        if type(signed["key_id"]) is not str or type(signed["signature"]) is not str:
            raise SfiError("SFI_SIGNATURE_INVALID", "signed statement envelope malformed")
        st = signed["statement"]
        if not isinstance(st, dict) or st.get("schema") != STATEMENT_SCHEMA:
            raise SfiError("SFI_UNSUPPORTED_VERSION", "unknown artifact statement schema",
                           expected_version=STATEMENT_SCHEMA)
        root = self.roots.get(signed["key_id"])
        now = self.clock()
        if root is None or root.revoked or not (root.not_before <= now <= root.not_after):
            raise SfiError("SFI_SIGNATURE_INVALID", "artifact signer unknown, revoked or expired",
                           key_id=signed.get("key_id"))
        if st.get("issuer") != root.issuer:
            raise SfiError("SFI_SIGNATURE_INVALID", "statement issuer does not match trust root",
                           key_id=root.key_id)
        try:
            pub = Pub.from_public_bytes(base64.b64decode(root.public_key_b64))
            pub.verify(base64.b64decode(signed["signature"]), canonical_json(st))
        except (Invalid, ValueError, TypeError):
            raise SfiError("SFI_SIGNATURE_INVALID", "artifact signature does not verify",
                           key_id=root.key_id) from None
        digest = sha256_hex(artifact)
        if st.get("artifact_sha256") != digest:
            raise SfiError("SFI_DIGEST_MISMATCH", "signed digest does not match artifact bytes",
                           artifact_sha256=digest, expected_sha256=st.get("artifact_sha256"))
        return st


def sign_statement(private_key: Any, key_id: str, artifact: bytes, *, workload: str, version: int,
                   issuer: str) -> dict[str, Any]:
    """CI/submitter side: produce a signed statement (used by tests and release tooling)."""
    st = {"schema": STATEMENT_SCHEMA, "artifact_sha256": sha256_hex(artifact), "workload": workload,
          "version": int(version), "issuer": issuer}
    sig = private_key.sign(canonical_json(st))
    return {"statement": st, "key_id": key_id, "signature": base64.b64encode(sig).decode()}


def new_ed25519() -> tuple[Any, str]:
    Priv, _, _ = _ed25519()
    from cryptography.hazmat.primitives import serialization
    k = Priv.generate()
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return k, base64.b64encode(pub).decode()


# ------------------------------------------------------------------------------ sealed descriptors

DESCRIPTOR_FIELDS = frozenset({
    "schema", "artifact_sha256", "profile_id", "profile_sha256", "proof_sha256", "config_sha256",
    "tenant", "workload", "artifact_version", "verifier_version", "issued_at", "expires_at", "nonce",
    "key_id", "mac",
})


def seal(keyring: KeyRing, *, proof: dict[str, Any], proof_sha256: str, config_sha256: str, tenant: str,
         workload: str, artifact_version: int, ttl_seconds: float = 900.0) -> dict[str, Any]:
    now = keyring.clock()
    body = {
        "schema": DESCRIPTOR_SCHEMA,
        "artifact_sha256": proof["artifact_sha256"],
        "profile_id": proof["profile_id"],
        "profile_sha256": proof["profile_sha256"],
        "proof_sha256": proof_sha256,
        "config_sha256": config_sha256,
        "tenant": tenant,
        "workload": workload,
        "artifact_version": int(artifact_version),
        "verifier_version": proof["verifier_version"],
        "issued_at": now,
        "expires_at": now + ttl_seconds,
        "nonce": _secrets.token_hex(16),
    }
    key_id, mac = keyring.sign(canonical_json(body))
    return body | {"key_id": key_id, "mac": mac}


_HEX64 = frozenset("0123456789abcdef")
_STR_FIELDS = ("schema", "profile_id", "tenant", "workload", "verifier_version", "nonce", "key_id")
_HEX_FIELDS = ("artifact_sha256", "profile_sha256", "proof_sha256", "config_sha256", "mac")


def _check_descriptor_types(desc: dict[str, Any]) -> None:
    """Strict typing before any semantic use (fuzz-found: type confusion must not escape as TypeError)."""
    for k in _STR_FIELDS:
        v = desc[k]
        if type(v) is not str or not v or len(v) > 256:
            raise SfiError("SFI_SEAL_MISMATCH", "descriptor field has wrong type", field=k)
    for k in _HEX_FIELDS:
        v = desc[k]
        if type(v) is not str or len(v) != 64 or not set(v) <= _HEX64:
            raise SfiError("SFI_SEAL_MISMATCH", "descriptor digest field malformed", field=k)
    if type(desc["artifact_version"]) is not int or not 0 <= desc["artifact_version"] < 2**32:
        raise SfiError("SFI_SEAL_MISMATCH", "descriptor field has wrong type", field="artifact_version")
    for k in ("issued_at", "expires_at"):
        v = desc[k]
        if type(v) not in (int, float) or v != v or v in (float("inf"), float("-inf")):
            raise SfiError("SFI_SEAL_MISMATCH", "descriptor field has wrong type", field=k)


def open_descriptor(keyring: KeyRing, desc: Any) -> dict[str, Any]:
    """Authenticate a descriptor.  Returns the body; raises on any defect (fail closed)."""
    if not isinstance(desc, dict) or set(desc) != DESCRIPTOR_FIELDS:
        raise SfiError("SFI_SEAL_MISMATCH", "descriptor fields missing or unexpected")
    _check_descriptor_types(desc)
    if desc["schema"] != DESCRIPTOR_SCHEMA:
        raise SfiError("SFI_UNSUPPORTED_VERSION", "unsupported descriptor schema",
                       expected_version=DESCRIPTOR_SCHEMA, observed_version=str(desc["schema"])[:64])
    body = {k: v for k, v in desc.items() if k not in ("key_id", "mac")}
    keyring.verify(desc["key_id"], canonical_json(body), desc["mac"])
    if keyring.clock() > desc["expires_at"]:
        raise SfiError("SFI_SEAL_MISMATCH", "descriptor expired", reason="expired")
    return body
