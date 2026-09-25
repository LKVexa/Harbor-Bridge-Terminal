"""Atomic file primitives and managed keys (GAP04-C15, C18, C41).

``atomic_write`` = write temp file in same directory -> fsync -> rename ->
fsync directory, so a crash leaves either the old or the new file, never a
torn one. ``Keyring`` holds AES-256 data keys by key id with one active key;
rotation adds a new active key while older keys stay available for decryption
until re-encryption completes. ``KeyProvider`` is the seam for TPM/HSM/secure
element integration; ``FileKeyProvider`` is the reference (0600 file) provider.
"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from . import crypto
from .errors import Gap04Error
from .faults import crashpoint


def fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:  # pragma: no cover - platforms without directory fds
        return
    try:
        os.fsync(fd)
    except OSError:  # pragma: no cover
        pass
    finally:
        os.close(fd)


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path = Path(path)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    crashpoint("atomic.before_rename")
    os.replace(tmp, path)
    fsync_dir(path.parent)


class KeyProvider(Protocol):
    def load(self) -> dict: ...
    def store(self, doc: dict) -> None: ...


@dataclass
class FileKeyProvider:
    path: Path

    def load(self) -> dict:
        p = Path(self.path)
        if not p.exists():
            return {}
        st = p.stat()
        if os.name == "posix" and st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise Gap04Error("key file permissions too open", code="GAP04-E0403", details={"path": str(p)})
        return json.loads(p.read_text())

    def store(self, doc: dict) -> None:
        atomic_write(Path(self.path), json.dumps(doc, sort_keys=True).encode(), 0o600)


@dataclass
class Keyring:
    provider: KeyProvider
    active: str = ""
    keys: dict[str, bytearray] = field(default_factory=dict, repr=False)
    audit_key: bytearray = field(default_factory=bytearray, repr=False)

    @classmethod
    def open(cls, provider: KeyProvider) -> "Keyring":
        doc = provider.load()
        kr = cls(provider)
        if not doc:
            kr.keys["k1"] = bytearray(os.urandom(32))
            kr.active = "k1"
            kr.audit_key = bytearray(os.urandom(32))
            kr._persist()
        else:
            kr.active = doc["active"]
            kr.keys = {k: bytearray(crypto.b64d(v)) for k, v in doc["keys"].items()}
            kr.audit_key = bytearray(crypto.b64d(doc["audit_key"]))
        return kr

    def _persist(self) -> None:
        self.provider.store({"version": "PK_KEYRING/1", "active": self.active,
                             "keys": {k: crypto.b64e(bytes(v)) for k, v in self.keys.items()},
                             "audit_key": crypto.b64e(bytes(self.audit_key))})

    def rotate(self) -> str:
        n = max(int(k[1:]) for k in self.keys) + 1
        kid = f"k{n}"
        self.keys[kid] = bytearray(os.urandom(32))
        self.active = kid
        self._persist()
        return kid

    def retire(self, kid: str) -> None:
        if kid == self.active:
            raise ValueError("cannot retire the active key")
        buf = self.keys.pop(kid)
        crypto.zeroize(buf)
        self._persist()

    def encrypt(self, plaintext: bytes, aad: bytes) -> dict:
        blob = crypto.aead_encrypt(bytes(self.keys[self.active]), plaintext, aad + self.active.encode())
        return {"kid": self.active, "ct": crypto.b64e(blob)}

    def decrypt(self, env: dict, aad: bytes) -> bytes:
        kid = env.get("kid")
        if kid not in self.keys:
            raise Gap04Error("unknown data key", code="GAP04-E0403", details={"kid": kid})
        return crypto.aead_decrypt(bytes(self.keys[kid]), crypto.b64d(env["ct"]), aad + kid.encode())

    def close(self) -> None:
        for v in self.keys.values():
            crypto.zeroize(v)
        crypto.zeroize(self.audit_key)
        self.keys.clear()
