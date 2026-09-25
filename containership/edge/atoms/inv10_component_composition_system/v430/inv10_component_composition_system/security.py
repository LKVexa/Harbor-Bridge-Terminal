"""MC-21..MC-23: key management, actor authentication, tamper-evident audit.

* :class:`KeyProvider` — versioned keys with rotation, retirement and a
  fail-closed ``unavailable`` state (degraded mode refuses signing/verifying).
* :class:`Authenticator` — HMAC bearer tokens binding actor, role, expiry.
* :class:`AuditTrail` — append-only JSONL hash chain; ``verify()`` detects any
  edit, deletion or reorder. Secrets are never written to the trail.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import pathlib
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from .errors import DependencyUnavailable, IntegrityError, Unauthenticated

REDACT_KEYS = {"token", "secret", "key", "password", "signature"}


class KeyProvider:
    """In-process key ring. Production: back with a KMS/HSM via the same API."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._keys: dict[str, dict[str, Any]] = {}
        self._active: str | None = None
        self._lock = threading.Lock()
        self.available = True
        self.clock = clock

    @classmethod
    def from_env(cls, var: str = "INV10_SIGNING_KEY", key_id: str = "env-1") -> "KeyProvider":
        kp = cls()
        raw = os.environ.get(var)
        if not raw:
            raise DependencyUnavailable("signing key environment variable unset", variable=var)
        kp.add(key_id, raw.encode(), activate=True)
        return kp

    def add(self, key_id: str, material: bytes, *, activate: bool = False) -> None:
        if len(material) < 16:
            raise ValueError("key material must be >= 16 bytes")
        with self._lock:
            self._keys[key_id] = {"material": bytes(material), "created": self.clock(), "retired": None}
            if activate:
                self._active = key_id

    def generate(self, key_id: str | None = None, *, activate: bool = True) -> str:
        key_id = key_id or f"k-{secrets.token_hex(4)}"
        self.add(key_id, secrets.token_bytes(32), activate=activate)
        return key_id

    def rotate(self) -> str:
        with self._lock:
            old = self._active
        new = self.generate(activate=True)
        if old:
            with self._lock:
                self._keys[old]["retired"] = self.clock()  # still verifies, never signs
        return new

    def revoke(self, key_id: str) -> None:
        with self._lock:
            self._keys.pop(key_id, None)
            if self._active == key_id:
                self._active = None

    def _check(self) -> None:
        if not self.available:
            raise DependencyUnavailable("key service unavailable", dependency="keys")

    def signing_key(self) -> tuple[str, bytes]:
        self._check()
        with self._lock:
            if self._active is None:
                raise DependencyUnavailable("no active signing key", dependency="keys")
            return self._active, self._keys[self._active]["material"]

    def verification_key(self, key_id: str) -> bytes:
        self._check()
        with self._lock:
            if key_id not in self._keys:
                raise Unauthenticated("unknown or revoked key", key_id=key_id)
            return self._keys[key_id]["material"]

    def sign(self, message: bytes) -> tuple[str, str]:
        kid, key = self.signing_key()
        return kid, hmac.new(key, message, "sha256").hexdigest()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {"available": self.available, "active": self._active,
                    "keys": sorted(self._keys), "retired": sorted(k for k, v in self._keys.items() if v["retired"])}


@dataclass(frozen=True)
class Principal:
    actor: str
    role: str  # submitter | publisher | operator | admin


ROLE_PERMISSIONS = {
    "submitter": {"compose", "explain", "diff"},
    "publisher": {"compose", "explain", "diff", "publish"},
    "operator": {"compose", "explain", "diff", "publish", "activate", "rollback", "quarantine", "freeze"},
    "admin": {"*"},
}


class Authenticator:
    def __init__(self, keys: KeyProvider, clock: Callable[[], float] = time.time) -> None:
        self.keys, self.clock = keys, clock

    def issue(self, actor: str, role: str, ttl: float = 900.0) -> str:
        if role not in ROLE_PERMISSIONS:
            raise ValueError("unknown role")
        body = json.dumps({"a": actor, "r": role, "e": self.clock() + ttl}, sort_keys=True).encode()
        kid, sig = self.keys.sign(body)
        return ".".join([base64.urlsafe_b64encode(body).decode(), kid, sig])

    def authenticate(self, token: str) -> Principal:
        try:
            b64, kid, sig = token.split(".")
            body = base64.urlsafe_b64decode(b64.encode())
        except Exception:
            raise Unauthenticated("malformed token") from None
        expected = hmac.new(self.keys.verification_key(kid), body, "sha256").hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise Unauthenticated("bad token signature")
        claims = json.loads(body)
        if claims["e"] < self.clock():
            raise Unauthenticated("token expired", actor=claims["a"])
        return Principal(claims["a"], claims["r"])

    @staticmethod
    def authorize(principal: Principal, action: str) -> None:
        perms = ROLE_PERMISSIONS.get(principal.role, set())
        if "*" not in perms and action not in perms:
            raise Unauthenticated("actor not permitted", actor=principal.actor, action=action, role=principal.role)


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if k.lower() in REDACT_KEYS else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


GENESIS = "0" * 64


class AuditTrail:
    """Append-only, hash-chained JSONL audit log (optionally file-backed)."""

    def __init__(self, path: str | os.PathLike | None = None, clock: Callable[[], float] = time.time) -> None:
        self.path = pathlib.Path(path) if path else None
        self.clock = clock
        self._lock = threading.Lock()
        self.records: list[dict[str, Any]] = []
        if self.path and self.path.exists():
            self.records = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
            self.verify()

    @staticmethod
    def _hash(record: dict[str, Any]) -> str:
        body = {k: v for k, v in record.items() if k != "hash"}
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def append(self, event: str, actor: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            prev = self.records[-1]["hash"] if self.records else GENESIS
            rec = {"seq": len(self.records), "ts": self.clock(), "event": event, "actor": actor,
                   "fields": redact(fields), "prev": prev}
            rec["hash"] = self._hash(rec)
            self.records.append(rec)
            if self.path:
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return rec

    def verify(self) -> int:
        prev = GENESIS
        for i, rec in enumerate(self.records):
            if rec.get("seq") != i or rec.get("prev") != prev or self._hash(rec) != rec.get("hash"):
                raise IntegrityError("audit chain broken", seq=i)
            prev = rec["hash"]
        return len(self.records)

    def head(self) -> str:
        return self.records[-1]["hash"] if self.records else GENESIS
