"""Secret/key management integration (component 11).

The v4.2.0 model passed signing secrets around as ordinary ``bytes``.  Here:

* **The controller never needs a private key.**  Commit, provenance and token
  verification use *public* keys from the trust roots; private keys belong to
  signers (developers, CI builder, IdP).  That removes the largest secret from
  the controller's memory entirely.
* The remaining secrets (Git transport credential, metrics bearer) are only
  ever **references** (``env:NAME`` / ``file:/path``) resolved at use time by
  ``SecretResolver`` -- never stored in config, argv, logs or evidence.
* ``file:`` secrets must not be group/world-readable (POSIX) and are size
  bounded; missing secrets raise ``SecretUnavailable`` (retryable).
* ``SecretBytes`` holds material in a ``bytearray`` that is overwritten on
  ``wipe()``/context exit (best-effort zeroisation -- CPython may have made
  copies; documented, not claimed).
* ``KeyRing`` tracks versions, activation and revocation for rotation and
  exposes only public material and fingerprints.

A managed KMS/HSM/Vault provider is an adapter slot (``provider=``) and is
BLOCKED: none is present in this environment.
"""
from __future__ import annotations

import hashlib
import os
import stat
from typing import Callable

from . import ed25519
from .errors import ConfigRejected, Revoked, SecretUnavailable


class SecretBytes:
    def __init__(self, data: bytes) -> None:
        self._b = bytearray(data)

    def reveal(self) -> bytes:
        if not self._b:
            raise SecretUnavailable("secret already wiped")
        return bytes(self._b)

    def wipe(self) -> None:
        for i in range(len(self._b)):
            self._b[i] = 0
        self._b = bytearray()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.wipe()

    def __repr__(self) -> str:
        return "SecretBytes(<redacted>)"

    __str__ = __repr__


class SecretResolver:
    def __init__(self, *, environ: dict | None = None, provider: Callable[[str], bytes] | None = None,
                 max_bytes: int = 64 << 10) -> None:
        self.env = os.environ if environ is None else environ
        self.provider, self.max_bytes = provider, max_bytes

    def resolve(self, ref: str) -> SecretBytes:
        if ref.startswith("env:"):
            v = self.env.get(ref[4:])
            if v is None:
                raise SecretUnavailable("secret reference not set", ref=ref[:4] + "<name>")
            return SecretBytes(v.encode())
        if ref.startswith("file:"):
            p = ref[5:]
            try:
                st = os.stat(p)
            except OSError:
                raise SecretUnavailable("secret file unavailable") from None
            if os.name == "posix" and st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise ConfigRejected("secret file permissions too open (must be 0600 or stricter)")
            if st.st_size > self.max_bytes:
                raise ConfigRejected("secret file too large")
            with open(p, "rb") as fh:
                return SecretBytes(fh.read().strip())
        if ref.startswith("kms:"):
            if self.provider is None:
                raise SecretUnavailable("KMS provider not configured")
            return SecretBytes(self.provider(ref[4:]))
        raise ConfigRejected("unsupported secret reference scheme")


def fingerprint(public: bytes) -> str:
    return hashlib.sha256(public).hexdigest()[:32]


class KeyRing:
    """Versioned public verification keys with rotation and revocation."""

    def __init__(self) -> None:
        self._keys: dict[str, dict] = {}

    def add(self, key_id: str, public: bytes, *, activated_at: int, purpose: str) -> dict:
        if len(public) != 32:
            raise ConfigRejected("ed25519 public key must be 32 bytes")
        if key_id in self._keys:
            raise ConfigRejected("key id already present; rotation must use a new id")
        rec = {"key_id": key_id, "public": public, "fingerprint": fingerprint(public), "purpose": purpose,
               "activated_at": activated_at, "revoked_at": None, "version": len(self._keys) + 1}
        self._keys[key_id] = rec
        return {k: v for k, v in rec.items() if k != "public"}

    def rotate(self, old: str, new_id: str, public: bytes, *, at: int, overlap: int = 0) -> dict:
        rec = self.add(new_id, public, activated_at=at, purpose=self._keys[old]["purpose"])
        self._keys[old]["revoked_at"] = at + overlap
        return rec

    def revoke(self, key_id: str, *, at: int) -> None:
        self._keys[key_id]["revoked_at"] = at

    def public(self, key_id: str, *, now: int) -> bytes:
        rec = self._keys.get(key_id)
        if rec is None:
            raise Revoked("unknown key")
        if rec["revoked_at"] is not None and now >= rec["revoked_at"]:
            raise Revoked("key revoked", key_id=key_id)
        return rec["public"]

    def listing(self) -> list[dict]:
        return [{k: v for k, v in r.items() if k != "public"} for r in self._keys.values()]


def generate_keypair(seed: bytes | None = None) -> tuple[bytes, bytes]:
    """Fixture/test helper (signers only).  Pure-Python Ed25519 is not
    constant-time: production signing keys belong in an HSM/KMS (waiver W-002)."""
    sk = seed if seed is not None else os.urandom(32)
    return sk, ed25519.public_key(sk)
