"""MC-15 identity/capabilities and MC-17 sensitive-data handling.

* Identity is minted only by an :class:`Authority` holding a key reference;
  callers cannot spoof it because every :class:`Capability` is an HMAC-SHA256
  token over (tenant, workload, actions, resource scope, expiry, serial).
* Authorization runs before any resource reservation or native call.
* Revocation is by serial; expiry is monotonic-clock based.
* Keys are held by reference in a :class:`KeyProvider`; rotation keeps the
  previous key for verification only; a revoked key fails closed.
* :func:`redact` is the single central redaction point used by logs,
  snapshots, audit and error messages.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

ACTIONS = frozenset({"arm", "submit", "reap", "cancel", "inspect", "configure", "admin"})


class Unauthorized(PermissionError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class KeyUnavailable(RuntimeError):
    pass


@dataclass
class KeyProvider:
    """Key-reference provider. Real deployments back this with a KMS; the
    in-process implementation keeps raw bytes private and never exposes them."""
    _keys: dict[str, bytes] = field(default_factory=dict, repr=False)
    _revoked: set[str] = field(default_factory=set)
    _expiry: dict[str, float] = field(default_factory=dict)
    active: str | None = None
    available: bool = True
    clock: Any = time.monotonic

    def create(self, ref: str, ttl: float | None = None) -> str:
        self._keys[ref] = os.urandom(32)
        if ttl is not None:
            self._expiry[ref] = self.clock() + ttl
        self.active = ref
        return ref

    def rotate(self, new_ref: str, ttl: float | None = None) -> str:
        return self.create(new_ref, ttl)

    def revoke(self, ref: str) -> None:
        self._revoked.add(ref)
        if self.active == ref:
            self.active = None

    def key(self, ref: str) -> bytes:
        if not self.available:
            raise KeyUnavailable("key service unavailable")  # fail closed
        if ref in self._revoked:
            raise KeyUnavailable(f"key {ref} revoked")
        if ref in self._expiry and self.clock() >= self._expiry[ref]:
            raise KeyUnavailable(f"key {ref} expired")
        if ref not in self._keys:
            raise KeyUnavailable(f"unknown key {ref}")
        return self._keys[ref]

    def __repr__(self) -> str:  # never print key material
        return f"KeyProvider(active={self.active!r}, refs={sorted(self._keys)})"


@dataclass(frozen=True)
class Capability:
    tenant: str
    workload: str
    actions: frozenset
    resource: str          # e.g. "fd:*" or "fd:12" or "op:*"
    expires: float
    serial: int
    key_ref: str
    mac: str = field(repr=False, default="")

    def body(self) -> bytes:
        return "|".join([self.tenant, self.workload, ",".join(sorted(self.actions)),
                         self.resource, repr(self.expires), str(self.serial), self.key_ref]).encode()


_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


class Authority:
    def __init__(self, keys: KeyProvider, clock=time.monotonic) -> None:
        self.keys = keys
        self.clock = clock
        self._serial = 0
        self._revoked: set[int] = set()
        self._lock = threading.Lock()
        self.denials: list[dict] = []

    def mint(self, tenant: str, workload: str, actions: Iterable[str], resource: str = "fd:*",
             ttl: float = 3600.0) -> Capability:
        acts = frozenset(actions)
        if not acts <= ACTIONS:
            raise ValueError(f"unknown actions {sorted(acts - ACTIONS)}")
        for v in (tenant, workload):
            if not _ID_RE.match(v):
                raise ValueError("identity must match [A-Za-z0-9_.:-]{1,64}")
        ref = self.keys.active
        if ref is None:
            raise KeyUnavailable("no active key")
        with self._lock:
            self._serial += 1
            serial = self._serial
        cap = Capability(tenant, workload, acts, resource, self.clock() + ttl, serial, ref)
        mac = hmac.new(self.keys.key(ref), cap.body(), hashlib.sha256).hexdigest()
        return Capability(**{**cap.__dict__, "mac": mac})

    def revoke(self, cap: Capability) -> None:
        with self._lock:
            self._revoked.add(cap.serial)

    def check(self, cap: object, action: str, *, fd: int | None = None,
              owner: tuple[str, str] | None = None) -> Capability:
        """Authorize; raises Unauthorized. Called before any allocation."""
        try:
            if not isinstance(cap, Capability):
                raise Unauthorized("NO_CAPABILITY")
            try:
                key = self.keys.key(cap.key_ref)
            except KeyUnavailable as exc:
                raise Unauthorized(f"KEY_UNAVAILABLE:{exc}") from None
            want = hmac.new(key, cap.body(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(want, cap.mac):
                raise Unauthorized("FORGED_CAPABILITY")
            if cap.serial in self._revoked:
                raise Unauthorized("REVOKED")
            if self.clock() >= cap.expires:
                raise Unauthorized("EXPIRED")
            if action not in cap.actions:
                raise Unauthorized(f"ACTION_NOT_GRANTED:{action}")
            if fd is not None and cap.resource not in ("fd:*", f"fd:{fd}"):
                raise Unauthorized("RESOURCE_OUT_OF_SCOPE")
            if owner is not None and owner != (cap.tenant, cap.workload) and "admin" not in cap.actions:
                raise Unauthorized("CROSS_TENANT" if owner[0] != cap.tenant else "CROSS_WORKLOAD")
            return cap
        except Unauthorized as exc:
            self.denials.append({"action": action, "reason": exc.reason})
            del self.denials[:-1024]
            raise


# ---------------------------------------------------------------- MC-17 redaction
DATA_CLASSIFICATION = {
    "backend": "public", "semantics": "public", "code": "public", "op_kind": "public",
    "counts": "public", "tenant": "tenant-sensitive (pseudonymise)",
    "workload": "tenant-sensitive (pseudonymise)", "fd": "internal (never a metric label)",
    "op_id": "internal", "payload": "prohibited", "buffer": "prohibited",
    "key": "secret (prohibited)", "token": "secret (prohibited)", "mac": "secret (prohibited)",
    "password": "secret (prohibited)", "authorization": "secret (prohibited)",
}
PERMITTED_LOG_FIELDS = frozenset({"event", "severity", "backend", "semantics", "code", "op_kind",
                                  "corr", "tenant_ps", "workload_ps", "reason", "config_digest",
                                  "release", "ts", "trace_id", "span_id", "count", "state"})
_SECRET_KEYS = re.compile(r"(secret|passw|token|mac|key|authori[sz]ation|credential|cookie|payload|buffer)", re.I)
_SECRET_VALUES = re.compile(r"(?i)(bearer\s+[A-Za-z0-9._~+/-]+=*|[A-Fa-f0-9]{40,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]+-----)")
REDACTED = "[REDACTED]"
_MAX_STR = 256


def pseudonym(value: str, salt: bytes = b"inv19-ps-v1") -> str:
    return "ps_" + hashlib.sha256(salt + value.encode()).hexdigest()[:12]


def redact(obj: Any, _depth: int = 0) -> Any:
    """Recursively redact secrets; bound depth and string length; strip controls."""
    if _depth > 8:
        return "[DEPTH]"
    if isinstance(obj, dict):
        return {str(k)[:64]: (REDACTED if _SECRET_KEYS.search(str(k)) else redact(v, _depth + 1))
                for k, v in list(obj.items())[:128]}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [redact(v, _depth + 1) for v in list(obj)[:128]]
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return REDACTED
    if isinstance(obj, Capability):
        return {"tenant": obj.tenant, "workload": obj.workload, "serial": obj.serial, "mac": REDACTED}
    if isinstance(obj, str):
        s = _SECRET_VALUES.sub(REDACTED, obj)
        s = "".join(ch if ch.isprintable() else "\\x%02x" % ord(ch) for ch in s)  # log-injection
        return s[:_MAX_STR] + ("…" if len(s) > _MAX_STR else "")
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    return redact(repr(obj), _depth + 1)


def safe_exception(exc: BaseException) -> dict:
    """Traceback-free, redacted exception summary for diagnostics."""
    return {"type": type(exc).__name__, "message": redact(str(exc))}


# Outage policy (MC-17 dependency outage behaviour) - explicit fail-open/closed.
OUTAGE_POLICY = {
    "identity_service": "fail-closed: no new capabilities minted; existing ones verify until expiry",
    "key_service": "fail-closed: capability verification refuses (KEY_UNAVAILABLE)",
    "time_service": "fail-closed for expiry: monotonic clock only; wall clock used for display only",
    "audit_sink": "fail-closed after bounded buffer: security-relevant actions refused when the audit buffer is full",
    "telemetry_sink": "fail-open: metrics dropped and counted; I/O continues",
}
