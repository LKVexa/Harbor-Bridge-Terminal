"""Key management boundary (MC-024).

``Keyring`` holds versioned symmetric keys supplied by a ``KeyProvider``
(KMS/HSM adapter in production; ``EnvKeyProvider``/``StaticKeyProvider`` for
tests).  Keys are never logged; missing key material fails closed with
``KEY_UNAVAILABLE``.  Rotation keeps the previous key for verification only
during an explicit grace window.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import threading
import time
from dataclasses import dataclass
from typing import Protocol

from ..errors import Inv24Error

MIN_KEY_BYTES = 32


class KeyProvider(Protocol):
    def fetch(self, key_id: str) -> bytes: ...


class StaticKeyProvider:
    def __init__(self, keys: dict[str, bytes]) -> None:
        self._keys = dict(keys)

    def fetch(self, key_id: str) -> bytes:
        try:
            return self._keys[key_id]
        except KeyError:
            raise Inv24Error("KEY_UNAVAILABLE", f"key {key_id} not provisioned") from None


class EnvKeyProvider:
    """Reads base64 keys from ``INV24_KEY_<ID>``; for bootstrap only, never production."""

    def fetch(self, key_id: str) -> bytes:
        raw = os.environ.get(f"INV24_KEY_{key_id.upper().replace('-', '_')}")
        if not raw:
            raise Inv24Error("KEY_UNAVAILABLE", f"key {key_id} not provisioned")
        try:
            return base64.b64decode(raw, validate=True)
        except ValueError:
            raise Inv24Error("KEY_UNAVAILABLE", f"key {key_id} malformed") from None


@dataclass(frozen=True, slots=True)
class _Slot:
    key_id: str
    material: bytes
    activated: float
    retire_after: float | None


class Keyring:
    def __init__(self, provider: KeyProvider, active_id: str, *, grace_s: float = 3600.0,
                 clock=time.time) -> None:
        self.provider, self.grace_s, self.clock = provider, grace_s, clock
        self._lock = threading.Lock()
        self._slots: dict[str, _Slot] = {}
        self._active = self._load(active_id, None).key_id

    def _load(self, key_id: str, retire_after: float | None) -> _Slot:
        material = self.provider.fetch(key_id)
        if not isinstance(material, (bytes, bytearray)) or len(material) < MIN_KEY_BYTES:
            raise Inv24Error("KEY_UNAVAILABLE", f"key {key_id} shorter than {MIN_KEY_BYTES} bytes")
        slot = _Slot(key_id, bytes(material), self.clock(), retire_after)
        self._slots[key_id] = slot
        return slot

    @property
    def active_id(self) -> str:
        return self._active

    def rotate(self, new_id: str) -> None:
        with self._lock:
            old = self._slots[self._active]
            self._slots[old.key_id] = _Slot(old.key_id, old.material, old.activated, self.clock() + self.grace_s)
            self._load(new_id, None)
            self._active = new_id

    def sign(self, data: bytes) -> tuple[str, str]:
        with self._lock:
            slot = self._slots[self._active]
        return slot.key_id, hmac.new(slot.material, data, hashlib.sha256).hexdigest()

    def verify(self, key_id: str, data: bytes, mac: str) -> bool:
        with self._lock:
            slot = self._slots.get(key_id)
        if slot is None:
            return False
        if slot.retire_after is not None and self.clock() > slot.retire_after:
            return False
        if not isinstance(mac, str):
            return False
        expected = hmac.new(slot.material, data, hashlib.sha256).hexdigest().encode()
        return hmac.compare_digest(expected, mac.encode("utf-8", "surrogatepass"))

    def fingerprint(self) -> str:
        """Non-secret identifier safe for logs."""
        return f"{self._active}:{hashlib.sha256(self._slots[self._active].material).hexdigest()[:8]}"
