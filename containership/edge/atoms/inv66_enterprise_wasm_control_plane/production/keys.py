"""Key material, envelope encryption and rotation (MC-027 secrets, MC-034 at-rest crypto).

* ``SecretProvider`` resolves *secret references* (``env:NAME``, ``file:/path``) so no
  secret value ever appears in configuration, logs or error envelopes.  A KMS/Vault
  provider plugs in behind the same interface; none is bundled (OPEN_EXTERNAL).
* ``Keyring`` holds versioned 256-bit data-encryption keys; ``seal``/``open`` use
  AES-256-GCM with the key id and a caller-supplied context bound as AAD, so a
  ciphertext moved to another record/tenant fails authentication.  ``rotate`` adds
  a new active key; old keys stay decrypt-only until ``retire``.
* ``Signer``/``verify_sig`` wrap Ed25519 for audit anchors and release manifests.
"""
from __future__ import annotations

import base64
import os
import threading
from pathlib import Path
from typing import Protocol

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization

from .errors import EcpError


class SecretProvider(Protocol):
    def resolve(self, ref: str) -> bytes: ...


class LocalSecretProvider:
    """Resolves ``env:NAME`` and ``file:PATH`` references. Values are never logged."""

    def __init__(self, environ: dict[str, str] | None = None, allowed_dirs: tuple[str, ...] = ()):
        self._env = os.environ if environ is None else environ
        self._dirs = tuple(str(Path(d).resolve()) for d in allowed_dirs)

    def resolve(self, ref: str) -> bytes:
        if not isinstance(ref, str) or ":" not in ref:
            raise EcpError("ECP_CONFIG_INVALID", "secret reference must be scheme:value", field="secret_ref")
        scheme, _, val = ref.partition(":")
        if scheme == "env":
            if val not in self._env:
                raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "secret not present", dependency="secrets")
            return self._env[val].encode()
        if scheme == "file":
            p = Path(val).resolve()
            if self._dirs and not any(str(p).startswith(d + os.sep) for d in self._dirs):
                raise EcpError("ECP_CONFIG_INVALID", "secret file outside allowed directories", field="secret_ref")
            try:
                return p.read_bytes().strip()
            except OSError:
                raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "secret file unreadable", dependency="secrets") from None
        raise EcpError("ECP_CONFIG_INVALID", "unsupported secret scheme", field="secret_ref", observed=scheme)


class Keyring:
    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}
        self._retired: set[str] = set()
        self.active: str | None = None
        self._lock = threading.Lock()

    def add(self, key_id: str, key: bytes, *, activate: bool = True) -> None:
        if len(key) != 32:
            raise EcpError("ECP_CONFIG_INVALID", "data key must be 32 bytes", field="key", key_id=key_id)
        with self._lock:
            self._keys[key_id] = bytes(key)
            if activate:
                self.active = key_id

    def rotate(self, key_id: str | None = None) -> str:
        kid = key_id or f"dek-{len(self._keys) + 1}"
        self.add(kid, AESGCM.generate_key(bit_length=256))
        return kid

    def retire(self, key_id: str) -> None:
        with self._lock:
            if key_id == self.active:
                raise EcpError("ECP_CONFIG_INVALID", "cannot retire the active key", key_id=key_id)
            self._retired.add(key_id)

    def key_ids(self) -> list[str]:
        return sorted(self._keys)

    def seal(self, plaintext: bytes, context: bytes) -> dict[str, str]:
        if self.active is None:
            raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "no active data key", dependency="keyring")
        kid = self.active
        nonce = os.urandom(12)
        ct = AESGCM(self._keys[kid]).encrypt(nonce, plaintext, kid.encode() + b"\0" + context)
        return {"alg": "AES-256-GCM", "kid": kid, "n": base64.b64encode(nonce).decode(),
                "ct": base64.b64encode(ct).decode()}

    def open(self, env: dict[str, str], context: bytes) -> bytes:
        kid = env.get("kid")
        if kid not in self._keys or kid in self._retired:
            raise EcpError("ECP_STORE_CORRUPT", "unknown or retired data key", key_id=str(kid)[:64])
        try:
            return AESGCM(self._keys[kid]).decrypt(base64.b64decode(env["n"]), base64.b64decode(env["ct"]),
                                                   kid.encode() + b"\0" + context)
        except (InvalidTag, KeyError, ValueError):
            raise EcpError("ECP_STORE_CORRUPT", "ciphertext failed authentication", key_id=kid) from None


class Signer:
    def __init__(self, key_id: str, private: Ed25519PrivateKey | None = None):
        self.key_id = key_id
        self._sk = private or Ed25519PrivateKey.generate()

    def sign(self, data: bytes) -> str:
        return base64.b64encode(self._sk.sign(data)).decode()

    def public_b64(self) -> str:
        raw = self._sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return base64.b64encode(raw).decode()


def public_key(b64: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(b64))


def verify_sig(public_b64: str, signature_b64: str, data: bytes) -> bool:
    try:
        public_key(public_b64).verify(base64.b64decode(signature_b64), data)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
