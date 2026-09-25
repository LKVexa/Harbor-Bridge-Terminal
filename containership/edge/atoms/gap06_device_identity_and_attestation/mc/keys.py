"""MC-14: key custody behind a KMS-shaped interface.

``SoftwareKeyStore`` is the only backend shipped: Ed25519 keys held in process
memory, never exported in private form, with rotation, versioned key ids, access
control per principal and best-effort zeroization (Python cannot guarantee
memory wiping -- recorded as a limitation).  HSM/cloud-KMS backends are BLOCKED
(no device or service available); the interface is what they must implement.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .errors import fail


class KeyStore:  # interface
    def sign(self, key_id: str, message: bytes, *, principal: str) -> bytes: ...
    def public_key_pem(self, key_id: str) -> bytes: ...
    def rotate(self, name: str, *, principal: str) -> str: ...
    def destroy(self, key_id: str, *, principal: str) -> None: ...


@dataclass
class SoftwareKeyStore(KeyStore):
    acl: dict = field(default_factory=dict)  # key name -> {principal: {"sign","rotate","destroy"}}
    _keys: dict = field(default_factory=dict, repr=False)
    _versions: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _allowed(self, name, principal, op):
        if op not in self.acl.get(name, {}).get(principal, set()):
            raise fail("E_FORBIDDEN", f"{principal} may not {op} {name}")

    def create(self, name: str) -> str:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        with self._lock:
            v = self._versions.get(name, 0) + 1
            self._versions[name] = v
            kid = f"{name}/v{v}"
            self._keys[kid] = ed25519.Ed25519PrivateKey.generate()
            return kid

    def current(self, name: str) -> str:
        return f"{name}/v{self._versions[name]}"

    def sign(self, key_id, message, *, principal):
        self._allowed(key_id.split("/")[0], principal, "sign")
        k = self._keys.get(key_id)
        if k is None:
            raise fail("E_UNKNOWN_KEY", f"{key_id} unknown or destroyed")
        if key_id != self.current(key_id.split("/")[0]):
            raise fail("E_FORBIDDEN", "signing with a retired key version")
        return k.sign(message)

    def public_key_pem(self, key_id):
        from cryptography.hazmat.primitives import serialization
        k = self._keys.get(key_id)
        if k is None:
            raise fail("E_UNKNOWN_KEY", key_id)
        return k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def rotate(self, name, *, principal):
        self._allowed(name, principal, "rotate")
        return self.create(name)

    def destroy(self, key_id, *, principal):
        self._allowed(key_id.split("/")[0], principal, "destroy")
        with self._lock:
            self._keys.pop(key_id, None)  # zeroization is best-effort in CPython

    def __repr__(self):  # never print key material
        return f"SoftwareKeyStore(keys={sorted(self._keys)})"
