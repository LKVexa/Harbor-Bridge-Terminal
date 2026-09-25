"""Key custody, epochs, rotation and revocation (MC-05).

Long-lived keys (identity signing keys, quarantine/audit signing keys) are
obtained through a :class:`KeyProvider` behind a ``secretref://`` handle, never
from configuration values (MC-05.003/.006, MC-08.005).  Traffic keys are never
long-lived: every session derives them from an ephemeral handshake, so key
rotation never re-keys live traffic in place - it forces re-establishment.

Production providers (cloud KMS, HSM/PKCS#11, Vault) are adapters over this
interface and are **not** shipped here; :class:`InMemoryKeyProvider` is the
reference/test provider and refuses to serve the ``prod`` namespace unless
explicitly constructed for it.
"""
from __future__ import annotations

import enum
import random
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

from .errors import ErrorCode, Inv36Error

SECRET_REF_RE = re.compile(r"secretref://(?P<ns>dev|test|stage|prod)/(?P<name>[a-z0-9][a-z0-9._/-]{0,127})\Z")
NAMESPACES = ("dev", "test", "stage", "prod")


class KeyError_(Inv36Error, RuntimeError):
    code = ErrorCode.KEY_UNAVAILABLE


class KeyUnavailable(KeyError_):
    code = ErrorCode.KEY_UNAVAILABLE


class KeyPermissionDenied(KeyError_):
    code = ErrorCode.KEY_PERMISSION


class KeyIntegrityError(KeyError_):
    code = ErrorCode.KEY_INTEGRITY


class KeyEpochError(KeyError_):
    code = ErrorCode.KEY_EPOCH


class KeyRevoked(KeyError_):
    code = ErrorCode.KEY_REVOKED


class KeyThrottled(KeyError_):
    code = ErrorCode.KEY_THROTTLED


class KeyState(str, enum.Enum):
    ACTIVE = "active"
    GRACE = "grace"          # still accepted for verification, not for new signatures
    RETIRED = "retired"
    REVOKED = "revoked"


class KeyClass(str, enum.Enum):
    TRUST_ANCHOR = "trust_anchor"
    IDENTITY = "identity"
    QUARANTINE_AUTHORITY = "quarantine_authority"
    AUDIT_SIGNING = "audit_signing"
    RELEASE_SIGNING = "release_signing"
    TRAFFIC = "traffic"           # ephemeral; never stored by a provider
    TEST = "test"


@dataclass(frozen=True)
class SecretRef:
    namespace: str
    name: str

    @classmethod
    def parse(cls, ref: str) -> "SecretRef":
        m = SECRET_REF_RE.match(ref or "")
        if not m:
            raise KeyPermissionDenied("invalid secret reference", detail={"ref_prefix": (ref or "")[:12]})
        return cls(m["ns"], m["name"])

    def __str__(self) -> str:
        return f"secretref://{self.namespace}/{self.name}"


@dataclass(frozen=True)
class KeyMetadata:
    key_id: str
    key_class: KeyClass
    algorithm: str
    epoch: int
    state: KeyState
    namespace: str
    not_after: float

    def safe(self) -> dict:
        """Loggable identifiers only - never key bytes (MC-05.005/.026)."""
        return {"key_id": self.key_id, "class": self.key_class.value, "alg": self.algorithm,
                "epoch": self.epoch, "state": self.state.value, "ns": self.namespace}


class SigningKey:
    """Opaque handle; the private key object is never exposed through repr/str/pickle."""

    __slots__ = ("meta", "_priv")

    def __init__(self, meta: KeyMetadata, priv: Ed25519PrivateKey) -> None:
        self.meta = meta
        self._priv = priv

    def sign(self, data: bytes) -> bytes:
        if self._priv is None:
            raise KeyUnavailable("key handle destroyed")
        if self.meta.state is not KeyState.ACTIVE:
            raise KeyEpochError("key not active for signing", detail=self.meta.safe())
        return self._priv.sign(data)

    def public_bytes(self) -> bytes:
        if self._priv is None:
            raise KeyUnavailable("key handle destroyed")
        return self._priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    def destroy(self) -> None:
        # Reference minimisation; CPython cannot guarantee physical zeroisation (MC-05.011).
        self._priv = None

    def __repr__(self) -> str:
        return f"SigningKey({self.meta.key_id!r}, epoch={self.meta.epoch}, state={self.meta.state.value})"

    __str__ = __repr__

    def __reduce__(self):  # refuse pickling of private material
        raise TypeError("SigningKey is not serializable")


class KeyProvider(Protocol):
    def get_signing_key(self, ref: SecretRef) -> SigningKey: ...

    def metadata(self, ref: SecretRef) -> KeyMetadata: ...


_ALLOWED_ALGS = {"ed25519"}


def validate_metadata(meta: KeyMetadata, *, expected_ns: str, expected_class: KeyClass, now: float,
                      min_epoch: int = 0) -> None:
    """MC-05.008: validate key metadata, algorithm, state and version before use."""
    if meta.algorithm not in _ALLOWED_ALGS:
        raise KeyIntegrityError("unexpected key algorithm", detail=meta.safe())
    if meta.namespace != expected_ns:
        raise KeyPermissionDenied("key namespace does not match environment", detail=meta.safe())
    if meta.key_class is not expected_class:
        raise KeyPermissionDenied("key class mismatch", detail=meta.safe())
    if meta.state is KeyState.REVOKED:
        raise KeyRevoked("key revoked", detail=meta.safe())
    if meta.state is KeyState.RETIRED:
        raise KeyEpochError("key retired", detail=meta.safe())
    if meta.epoch < min_epoch:
        raise KeyEpochError("key epoch below minimum (rollback refused)", detail=meta.safe())
    if now >= meta.not_after:
        raise KeyEpochError("key expired", detail=meta.safe())


class InMemoryKeyProvider:
    """Reference provider with failure injection for tests (MC-05.019)."""

    def __init__(self, namespace: str = "test", *, allow_prod: bool = False,
                 clock: Callable[[], float] = time.time) -> None:
        if namespace not in NAMESPACES:
            raise ValueError("unknown namespace")
        if namespace == "prod" and not allow_prod:
            raise KeyPermissionDenied("in-memory provider may not serve prod keys")
        self.namespace = namespace
        self.clock = clock
        self._keys: dict[str, tuple[KeyMetadata, Ed25519PrivateKey]] = {}
        self.fail_mode: str | None = None  # unavailable|permission|throttled|corrupt|stale
        self.calls = 0

    def create(self, name: str, key_class: KeyClass, *, epoch: int = 1, ttl_s: float = 86400.0,
               state: KeyState = KeyState.ACTIVE) -> SecretRef:
        ref = SecretRef(self.namespace, name)
        priv = Ed25519PrivateKey.generate()
        meta = KeyMetadata(f"{self.namespace}:{name}#{epoch}", key_class, "ed25519", epoch, state,
                           self.namespace, self.clock() + ttl_s)
        self._keys[str(ref)] = (meta, priv)
        return ref

    def set_state(self, ref: SecretRef, state: KeyState) -> None:
        meta, priv = self._keys[str(ref)]
        self._keys[str(ref)] = (KeyMetadata(meta.key_id, meta.key_class, meta.algorithm, meta.epoch, state,
                                            meta.namespace, meta.not_after), priv)

    def _lookup(self, ref: SecretRef) -> tuple[KeyMetadata, Ed25519PrivateKey]:
        self.calls += 1
        if ref.namespace != self.namespace:
            raise KeyPermissionDenied("cross-namespace key request refused")
        mode = self.fail_mode
        if mode == "unavailable":
            raise KeyUnavailable("key service unavailable")
        if mode == "permission":
            raise KeyPermissionDenied("permission denied")
        if mode == "throttled":
            raise KeyThrottled("throttled", retry_after_s=0.01)
        try:
            meta, priv = self._keys[str(ref)]
        except KeyError as exc:
            raise KeyUnavailable("no such key") from exc
        if mode == "corrupt":
            meta = KeyMetadata(meta.key_id, meta.key_class, "rsa1024", meta.epoch, meta.state,
                               meta.namespace, meta.not_after)
        if mode == "stale":
            meta = KeyMetadata(meta.key_id, meta.key_class, meta.algorithm, max(meta.epoch - 1, 0),
                               meta.state, meta.namespace, meta.not_after)
        return meta, priv

    def metadata(self, ref: SecretRef) -> KeyMetadata:
        return self._lookup(ref)[0]

    def get_signing_key(self, ref: SecretRef) -> SigningKey:
        meta, priv = self._lookup(ref)
        return SigningKey(meta, priv)


def retry_call(fn: Callable[[], object], *, attempts: int = 4, base_s: float = 0.02, cap_s: float = 0.5,
               rng: random.Random | None = None, sleep: Callable[[float], None] = time.sleep,
               retry_on: tuple[type[BaseException], ...] = (KeyUnavailable, KeyThrottled)):
    """Bounded retries with full jitter for transient key-service faults (MC-05.020)."""
    r = rng or random.Random()
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as exc:  # noqa: PERF203
            last = exc
            if i == attempts - 1:
                break
            hint = getattr(exc, "retry_after_s", None) or 0.0
            sleep(max(hint, r.uniform(0, min(cap_s, base_s * (2 ** i)))))
    if last is None:  # pragma: no cover - attempts >= 1 always sets last
        raise KeyUnavailable("retry loop ended without a result")
    raise last


class KeyCache:
    """Bounded-duration cache with explicit invalidation (MC-05.009)."""

    def __init__(self, provider: KeyProvider, *, namespace: str, ttl_s: float = 300.0, max_entries: int = 16,
                 clock: Callable[[], float] = time.monotonic, wall: Callable[[], float] = time.time,
                 min_epoch: Callable[[SecretRef], int] | None = None) -> None:
        self.provider = provider
        self.namespace = namespace
        self.ttl_s = ttl_s
        self.max_entries = max_entries
        self.clock = clock
        self.wall = wall
        self.min_epoch = min_epoch or (lambda ref: 0)
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[float, SigningKey]] = {}

    def get(self, ref: SecretRef, key_class: KeyClass, **retry_kw) -> SigningKey:
        now = self.clock()
        with self._lock:
            hit = self._entries.get(str(ref))
            if hit and now - hit[0] < self.ttl_s:
                return hit[1]
        key = retry_call(lambda: self.provider.get_signing_key(ref), **retry_kw)
        validate_metadata(key.meta, expected_ns=self.namespace, expected_class=key_class, now=self.wall(),
                          min_epoch=self.min_epoch(ref))
        with self._lock:
            if len(self._entries) >= self.max_entries:
                oldest = min(self._entries, key=lambda k: self._entries[k][0])
                self._entries.pop(oldest)[1].destroy()
            self._entries[str(ref)] = (now, key)
        return key

    def invalidate(self, ref: SecretRef | None = None) -> None:
        with self._lock:
            keys = [str(ref)] if ref else list(self._entries)
            for k in keys:
                ent = self._entries.pop(k, None)
                if ent:
                    ent[1].destroy()


@dataclass
class EpochPolicy:
    """Accepted identity-key epochs for one key family (MC-05.012-.017).

    * ``current`` is the epoch new credentials must carry.
    * ``previous`` stays acceptable until ``grace_until`` (wall clock).
    * Epochs never decrease; :meth:`rollback` requires an explicit recovery
      authorization token and is audited.
    * ``revoked`` epochs are refused immediately.
    """

    current: int = 1
    previous: int | None = None
    grace_until: float = 0.0
    revoked: set[int] = field(default_factory=set)
    clock: Callable[[], float] = time.time
    listeners: list[Callable[[str, dict], None]] = field(default_factory=list)

    def _emit(self, event: str, **data) -> None:
        for fn in list(self.listeners):
            fn(event, data)

    def accepts(self, epoch: int) -> bool:
        if epoch in self.revoked:
            return False
        if epoch == self.current:
            return True
        return self.previous is not None and epoch == self.previous and self.clock() < self.grace_until

    def check(self, epoch: int) -> None:
        if epoch in self.revoked:
            raise KeyRevoked("key epoch revoked", detail={"epoch": epoch})
        if not self.accepts(epoch):
            raise KeyEpochError("key epoch not accepted", detail={"epoch": epoch, "current": self.current})

    def rotate(self, new_epoch: int, *, grace_s: float) -> None:
        if new_epoch <= self.current:
            raise KeyEpochError("epochs must increase", detail={"current": self.current, "new": new_epoch})
        if grace_s < 0:
            raise ValueError("grace must be >= 0")
        self.previous, self.current = self.current, new_epoch
        self.grace_until = self.clock() + grace_s
        self._emit("key.rotate", epoch=new_epoch, previous=self.previous, grace_s=grace_s)

    def revoke(self, epoch: int, *, reason: str) -> None:
        self.revoked.add(epoch)
        if self.previous == epoch:
            self.previous = None
        self._emit("key.revoke", epoch=epoch, reason=reason[:128])

    def rollback(self, epoch: int, *, recovery_authorization: str | None) -> None:
        """Deny unless an explicit recovery authorization is supplied (MC-05.017)."""
        if not recovery_authorization:
            self._emit("key.rollback_denied", epoch=epoch)
            raise KeyEpochError("rollback to an older epoch requires recovery authorization")
        if epoch in self.revoked:
            self._emit("key.rollback_denied", epoch=epoch)
            raise KeyRevoked("cannot roll back to a revoked epoch")
        self.previous, self.current = None, epoch
        self._emit("key.rollback", epoch=epoch, authorization=recovery_authorization[:64])


def public_key_from_bytes(raw: bytes) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(raw)


KEY_INVENTORY: tuple[dict, ...] = (
    {"class": "trust_anchor", "purpose": "issue identity credentials", "storage": "HSM/KMS (offline root preferred)",
     "rotation": "yearly + on compromise", "consumers": ["handshake verifier (public only)"]},
    {"class": "identity", "purpose": "sign handshake transcripts", "storage": "KMS/HSM via workload identity",
     "rotation": "30 days, 7-day grace", "consumers": ["handshake"]},
    {"class": "traffic", "purpose": "PK_CTRL_FRAME/2 AEAD", "storage": "process memory only, per session",
     "rotation": "per session; rekey at max age/frames", "consumers": ["transport.Session"]},
    {"class": "quarantine_authority", "purpose": "sign quarantine directives", "storage": "HSM, break-glass",
     "rotation": "yearly + on compromise", "consumers": ["quarantine registry (public only)"]},
    {"class": "audit_signing", "purpose": "sign audit-log checkpoints", "storage": "KMS",
     "rotation": "90 days", "consumers": ["audit log"]},
    {"class": "release_signing", "purpose": "sign release artifacts", "storage": "CI OIDC-bound signer",
     "rotation": "per release identity policy", "consumers": ["tools/release.py verify"]},
    {"class": "test", "purpose": "tests and fixtures only", "storage": "generated per test run (test namespace)",
     "rotation": "per run", "consumers": ["tests"]},
)


def inventory_classes() -> Iterable[str]:
    return (k["class"] for k in KEY_INVENTORY)
