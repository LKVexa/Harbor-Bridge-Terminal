"""Identity, capability, replay, key-rotation and audit primitives.

Covers INV-35-C023/C044 (boundary authentication of control-plane peers),
C024/C042 (least-privilege capability model), C043 (no ambient authority: every
privileged call must present a capability), C047 (key rotation), C048 (fail
closed when key/time services fail) and C049 (tamper-evident audit chain).

Cryptography is stdlib HMAC-SHA-256 with keys held in a :class:`KeyRing`.  This
is a reference implementation of the *policy*; a production deployment binds the
same interfaces to an HSM/KMS and attestation service (see
docs/security/CRYPTO_AND_KEY_POLICY.md).
"""
from __future__ import annotations

import base64
from collections import OrderedDict
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import secrets as _secrets
from threading import RLock
import time
from typing import Callable

from .errors import Inv35Error

ACTIONS = frozenset({"submit", "complete", "register_memory", "lifecycle", "configure", "quarantine", "read_status"})


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


class KeyRing:
    """Versioned signing keys: one active key, older keys verify-only until retired."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._keys: dict[str, bytes] = {}
        self._active: str | None = None
        self._retired: set[str] = set()
        self._lock = RLock()
        self.available = True  # flipped to model KMS outage (C048)
        self.on_retire: list[Callable[[], None]] = []
        self.clock = clock

    def add(self, key_id: str, material: bytes, *, activate: bool = True) -> None:
        if len(material) < 32:
            raise Inv35Error("INV35-E500", "signing keys must be at least 256 bits")
        with self._lock:
            self._keys[key_id] = bytes(material)
            if activate:
                self._active = key_id

    def rotate(self, key_id: str | None = None) -> str:
        key_id = key_id or f"k{len(self._keys) + 1}"
        self.add(key_id, _secrets.token_bytes(32), activate=True)
        return key_id

    def retire(self, key_id: str) -> None:
        with self._lock:
            if key_id == self._active:
                raise Inv35Error("INV35-E500", "cannot retire the active key")
            self._retired.add(key_id)
            for listener in list(self.on_retire):
                listener()

    def sign(self, payload: bytes) -> tuple[str, bytes]:
        with self._lock:
            if not self.available or self._active is None:
                raise Inv35Error("INV35-E306", "key service unavailable")
            return self._active, hmac.new(self._keys[self._active], payload, hashlib.sha256).digest()

    def verify(self, key_id: str, payload: bytes, mac: bytes) -> bool:
        with self._lock:
            if not self.available:
                raise Inv35Error("INV35-E306", "key service unavailable")
            key = self._keys.get(key_id)
            if key is None or key_id in self._retired:
                return False
            return hmac.compare_digest(hmac.new(key, payload, hashlib.sha256).digest(), mac)


@dataclass(frozen=True, slots=True)
class Capability:
    subject: str          # authenticated principal (VMM process, controller, operator)
    tenant: str
    queues: frozenset[str]
    actions: frozenset[str]
    not_before: float
    not_after: float
    nonce: str
    key_id: str = ""
    mac: str = ""

    def claims(self) -> dict[str, object]:
        return {
            "sub": self.subject, "tenant": self.tenant, "queues": sorted(self.queues),
            "actions": sorted(self.actions), "nbf": self.not_before, "exp": self.not_after,
            "nonce": self.nonce,
        }

    def encode(self) -> str:
        return f"{_b64(canonical(self.claims()))}.{self.key_id}.{self.mac}"


class Authority:
    """Mints and verifies capabilities; enforces replay and validity windows."""

    MAX_TTL = 3600.0
    CLOCK_SKEW = 5.0

    def __init__(self, keyring: KeyRing, *, replay_window: int = 65536) -> None:
        self.keyring = keyring
        keyring.on_retire.append(self.flush)
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._replay_window = replay_window
        self._lock = RLock()
        self.time_trusted = True  # model loss of trusted time (C048)
        # Measured optimisation (C066): cache the *cryptographic* verification of a
        # reusable token.  Validity window, tenant, action and queue are still
        # checked on every call; single-use tokens never use the cache; retiring a
        # key or losing the key service flushes it.
        self._verified: OrderedDict[str, tuple[str, dict]] = OrderedDict()
        self.cache_capacity = 1024

    def mint(self, subject: str, tenant: str, queues: set[str], actions: set[str], ttl: float = 300.0) -> str:
        unknown = set(actions) - ACTIONS
        if unknown:
            raise Inv35Error("INV35-E303", f"unknown actions {sorted(unknown)}")
        if not (0 < ttl <= self.MAX_TTL):
            raise Inv35Error("INV35-E302", "ttl out of policy")
        now = self.keyring.clock()
        cap = Capability(subject, tenant, frozenset(queues), frozenset(actions), now, now + ttl,
                         _secrets.token_hex(16))
        key_id, mac = self.keyring.sign(canonical(cap.claims()))
        return Capability(**{**{k: getattr(cap, k) for k in cap.__slots__}, "key_id": key_id, "mac": _b64(mac)}).encode()

    def authorize(self, token: object, *, action: str, tenant: str, queue: str, single_use: bool = False) -> Capability:
        if not self.time_trusted:
            raise Inv35Error("INV35-E306", "trusted time unavailable")
        if not isinstance(token, str) or token.count(".") != 2:
            raise Inv35Error("INV35-E300")
        if not self.keyring.available:
            self._verified.clear()
            raise Inv35Error("INV35-E306", "key service unavailable")
        cached = None if single_use else self._verified.get(token)
        if cached is not None and cached[0] not in self.keyring._retired:
            return self._check_claims(cached[1], action=action, tenant=tenant, queue=queue, key_id=cached[0], mac="")
        body, key_id, mac = token.split(".")
        try:
            raw = _unb64(body)
            claims = json.loads(raw)
            mac_bytes = _unb64(mac)
        except Exception as exc:  # malformed input is a terminal refusal, never a crash
            raise Inv35Error("INV35-E300", "undecodable capability") from exc
        if not isinstance(claims, dict) or canonical(claims) != raw:
            raise Inv35Error("INV35-E300", "non-canonical capability")
        if not self.keyring.verify(key_id, raw, mac_bytes):
            raise Inv35Error("INV35-E301")
        for field_name, typ in (("sub", str), ("tenant", str), ("queues", list), ("actions", list),
                                ("nbf", (int, float)), ("exp", (int, float)), ("nonce", str)):
            if not isinstance(claims.get(field_name), typ):
                raise Inv35Error("INV35-E300", f"claim {field_name} malformed")
        if single_use:
            cap = self._check_claims(claims, action=action, tenant=tenant, queue=queue, key_id=key_id, mac=mac)
            with self._lock:
                if claims["nonce"] in self._seen:
                    raise Inv35Error("INV35-E304")
                self._seen[claims["nonce"]] = claims["exp"]
                while len(self._seen) > self._replay_window:
                    self._seen.popitem(last=False)
            return cap
        cap = self._check_claims(claims, action=action, tenant=tenant, queue=queue, key_id=key_id, mac=mac)
        with self._lock:
            self._verified[token] = (key_id, claims)
            while len(self._verified) > self.cache_capacity:
                self._verified.popitem(last=False)
        return cap

    def flush(self) -> None:
        with self._lock:
            self._verified.clear()

    def _check_claims(self, claims: dict, *, action: str, tenant: str, queue: str, key_id: str, mac: str) -> Capability:
        now = self.keyring.clock()
        if not (claims["nbf"] - self.CLOCK_SKEW <= now <= claims["exp"]):
            raise Inv35Error("INV35-E302")
        if claims["tenant"] != tenant:
            raise Inv35Error("INV35-E305", f"capability tenant {claims['tenant']!r} != {tenant!r}")
        if action not in claims["actions"] or queue not in claims["queues"]:
            raise Inv35Error("INV35-E303", f"{action} on {queue}")
        return Capability(claims["sub"], claims["tenant"], frozenset(claims["queues"]),
                          frozenset(claims["actions"]), claims["nbf"], claims["exp"], claims["nonce"], key_id, mac)


# ---------------------------------------------------------------------------
# Tamper-evident audit chain (C049)
# ---------------------------------------------------------------------------

GENESIS = "0" * 64


@dataclass
class AuditLog:
    keyring: KeyRing
    entries: list[dict[str, object]] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def append(self, event: str, **fields: object) -> dict[str, object]:
        with self._lock:
            prev = self.entries[-1]["hash"] if self.entries else GENESIS
            body = {"seq": len(self.entries), "event": event, "at": self.keyring.clock(),
                    "prev": prev, "fields": redact(fields)}
            digest = hashlib.sha256(canonical(body)).hexdigest()
            key_id, mac = self.keyring.sign(digest.encode("ascii"))
            entry = {**body, "hash": digest, "key_id": key_id, "mac": _b64(mac)}
            self.entries.append(entry)
            return entry

    def verify(self) -> bool:
        prev = GENESIS
        for i, entry in enumerate(self.entries):
            body = {k: entry[k] for k in ("seq", "event", "at", "prev", "fields")}
            digest = hashlib.sha256(canonical(body)).hexdigest()
            if entry["seq"] != i or entry["prev"] != prev or entry["hash"] != digest:
                return False
            if not self.keyring.verify(entry["key_id"], digest.encode("ascii"), _unb64(entry["mac"])):
                return False
            prev = digest
        return True

    def require_intact(self) -> None:
        if not self.verify():
            raise Inv35Error("INV35-E505")


# ---------------------------------------------------------------------------
# Secret redaction (C039, C075)
# ---------------------------------------------------------------------------

SECRET_WORDS = frozenset({"secret", "secrets", "password", "passwd", "token", "tokens", "credential",
                          "credentials", "mac", "apikey"})
SECRET_PHRASES = ("key_material", "private_key", "api_key", "signing_key")


def is_secret_key(name: str) -> bool:
    """Field-name heuristic: whole underscore/dash-separated words or known phrases."""
    lowered = str(name).lower().replace("-", "_")
    return bool(SECRET_WORDS & set(lowered.split("_"))) or any(p in lowered for p in SECRET_PHRASES)


def redact(value: object, _depth: int = 0) -> object:
    if _depth > 8:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if is_secret_key(str(k)) else redact(v, _depth + 1)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v, _depth + 1) for v in value]
    if isinstance(value, bytes):
        return f"[{len(value)} bytes]"
    return value
