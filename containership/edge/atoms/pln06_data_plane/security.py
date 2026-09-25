"""Wave 1 security primitives for PLN-06 (work packages #10-#12, #18-#24).

Everything here is standard-library only.  Cryptography is HMAC-SHA256 over a
managed key ring; confidentiality in transit is delegated to ``ssl`` contexts
supplied to the network adapters (see :mod:`transports`).  These primitives
are *reference implementations of the enforcement points*; production key
custody (KMS/HSM) plugs in through :class:`KeyProvider`.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .data_plane import _StructuredError

# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class AuthenticationFailed(_StructuredError, PermissionError):
    code = "PK_AUTHN_FAILED"


class AuthorizationDenied(_StructuredError, PermissionError):
    code = "PK_AUTHZ_DENIED"


class KeyUnavailable(_StructuredError, RuntimeError):
    """Key service outage or unknown/revoked key: security decisions fail closed."""

    code = "PK_KEY_UNAVAILABLE"
    retryable = True


class LabelInvalid(_StructuredError, PermissionError):
    code = "PK_CLASSIFICATION_LABEL_INVALID"


class AuditTampered(_StructuredError, RuntimeError):
    code = "PK_AUDIT_CHAIN_BROKEN"


def canonical(obj: object) -> bytes:
    """Deterministic JSON encoding used for every MAC/digest in this package."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


# --------------------------------------------------------------------------
# #23 Managed key lifecycle
# --------------------------------------------------------------------------

KEY_STATES = ("active", "verify_only", "revoked")


class KeyProvider:
    """SPI for KMS/HSM integration.  ``fetch`` may raise to signal an outage."""

    def fetch(self, key_id: str) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class _Key:
    key_id: str
    material: bytes
    state: str
    created: float
    not_after: float | None


class KeyRing:
    """Rotatable HMAC key ring with verify-only grace and hard revocation.

    * exactly one ``active`` signing key per purpose;
    * rotated keys become ``verify_only`` until ``retire``/expiry;
    * ``revoked`` keys never verify;
    * an attached :class:`KeyProvider` outage raises :class:`KeyUnavailable`
      (fail closed) instead of falling back to cached material.
    """

    def __init__(self, *, provider: KeyProvider | None = None, clock: Callable[[], float] = time.time):
        self._keys: dict[str, _Key] = {}
        self._active: str | None = None
        self._provider = provider
        self._clock = clock
        self._lock = threading.RLock()
        self._provider_down = False

    def add(self, key_id: str, material: bytes | None = None, *, activate: bool = True,
            ttl_seconds: float | None = None) -> str:
        if not key_id or not isinstance(key_id, str):
            raise KeyUnavailable("key_id must be a non-empty string")
        material = material if material is not None else secrets.token_bytes(32)
        if len(material) < 16:
            raise KeyUnavailable("key material must be >= 128 bits", key_id=key_id)
        with self._lock:
            if key_id in self._keys:
                raise KeyUnavailable("duplicate key_id", key_id=key_id)
            now = self._clock()
            self._keys[key_id] = _Key(key_id, material, "verify_only", now,
                                      None if ttl_seconds is None else now + ttl_seconds)
            if activate:
                self._activate(key_id)
        return key_id

    def _activate(self, key_id: str) -> None:
        if self._active and self._active in self._keys:
            self._keys[self._active].state = "verify_only"
        self._keys[key_id].state = "active"
        self._active = key_id

    def rotate(self, new_key_id: str, material: bytes | None = None) -> str:
        return self.add(new_key_id, material, activate=True)

    def retire(self, key_id: str) -> None:
        with self._lock:
            key = self._keys.get(key_id)
            if key is None or key.state == "active":
                raise KeyUnavailable("cannot retire unknown or active key", key_id=key_id)
            del self._keys[key_id]

    def revoke(self, key_id: str) -> None:
        with self._lock:
            key = self._keys.get(key_id)
            if key is None:
                raise KeyUnavailable("unknown key", key_id=key_id)
            key.state = "revoked"
            if self._active == key_id:
                self._active = None

    def set_provider_outage(self, down: bool) -> None:
        """Fault-injection hook representing a KMS/HSM outage."""
        self._provider_down = bool(down)

    def _material(self, key_id: str, *, signing: bool) -> bytes:
        if self._provider_down:
            raise KeyUnavailable("key service unavailable", key_id=key_id)
        with self._lock:
            key = self._keys.get(key_id)
            if key is None:
                raise KeyUnavailable("unknown key", key_id=key_id)
            if key.state == "revoked":
                raise KeyUnavailable("key revoked", key_id=key_id)
            if key.not_after is not None and self._clock() > key.not_after:
                raise KeyUnavailable("key expired", key_id=key_id)
            if signing and key.state != "active":
                raise KeyUnavailable("key is not the active signing key", key_id=key_id)
            if self._provider is not None:
                return self._provider.fetch(key_id)
            return key.material

    @property
    def active_key_id(self) -> str:
        with self._lock:
            if self._active is None:
                raise KeyUnavailable("no active signing key")
            return self._active

    def sign(self, payload: bytes) -> tuple[str, str]:
        kid = self.active_key_id
        return kid, hmac.new(self._material(kid, signing=True), payload, hashlib.sha256).hexdigest()

    def verify(self, key_id: str, payload: bytes, mac: str) -> bool:
        expected = hmac.new(self._material(key_id, signing=False), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, str(mac))

    def inventory(self) -> list[dict[str, object]]:
        """Key metadata only - material is never exported."""
        with self._lock:
            return [{"key_id": k.key_id, "state": k.state, "created": k.created,
                     "not_after": k.not_after} for k in self._keys.values()]


# --------------------------------------------------------------------------
# #11 Boundary authentication and #12 capability authorization
# --------------------------------------------------------------------------

CAPABILITIES = frozenset({
    "transfer.submit",        # admit
    "transfer.complete",      # complete/cancel own transfers
    "transfer.complete.any",  # complete/cancel other principals' transfers
    "policy.update",          # replace residency / config
    "policy.rollback",
    "control.freeze",         # freeze/quarantine/drain/emergency-disable
    "transport.use.inline",
    "transport.use.local",
    "transport.use.bulk",
    "diagnostics.read",       # metrics/health/explain
    "audit.read",
})

PRINCIPAL_KINDS = frozenset({"workload", "node", "peer", "operator", "control_plane", "provider"})


@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str
    tenant: str | None
    capabilities: frozenset[str]
    token_id: str


class Authenticator:
    """Issues and verifies MAC-bound, expiring, replay-protected credentials.

    Credentials bind subject, kind, tenant, capabilities, audience, expiry and a
    nonce.  Verification enforces audience, expiry with bounded clock skew, key
    state, and one-time nonce use when ``single_use`` is set (replay defence).
    """

    def __init__(self, keyring: KeyRing, *, audience: str = "pln06", max_skew: float = 30.0,
                 clock: Callable[[], float] = time.time, replay_cache_limit: int = 100_000):
        self._keys = keyring
        self._aud = audience
        self._skew = max_skew
        self._clock = clock
        self._seen: dict[str, float] = {}
        self._seen_limit = replay_cache_limit
        self._lock = threading.Lock()
        self._revoked_tokens: set[str] = set()

    def issue(self, subject: str, kind: str, capabilities: Iterable[str], *, tenant: str | None = None,
              ttl: float = 300.0, single_use: bool = False) -> dict[str, object]:
        caps = sorted(set(capabilities))
        unknown = set(caps) - CAPABILITIES
        if unknown:
            raise AuthorizationDenied("unknown capabilities requested", unknown=sorted(unknown))
        if kind not in PRINCIPAL_KINDS:
            raise AuthenticationFailed("unknown principal kind", kind=kind)
        now = self._clock()
        body = {"sub": subject, "kind": kind, "tenant": tenant, "caps": caps, "aud": self._aud,
                "iat": now, "exp": now + ttl, "jti": secrets.token_hex(16), "once": bool(single_use)}
        kid, mac = self._keys.sign(canonical(body))
        return {"body": body, "kid": kid, "mac": mac}

    def revoke_token(self, token_id: str) -> None:
        with self._lock:
            self._revoked_tokens.add(token_id)

    def authenticate(self, credential: Mapping[str, object]) -> Principal:
        try:
            body = dict(credential["body"])  # type: ignore[arg-type, call-overload]
            kid = str(credential["kid"])
            mac = str(credential["mac"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationFailed("malformed credential") from exc
        if not self._keys.verify(kid, canonical(body), mac):
            raise AuthenticationFailed("credential MAC mismatch")
        now = self._clock()
        if body.get("aud") != self._aud:
            raise AuthenticationFailed("audience mismatch (possible cross-service replay)")
        if not isinstance(body.get("exp"), (int, float)) or now > float(body["exp"]) + self._skew:
            raise AuthenticationFailed("credential expired")
        if float(body.get("iat", 0)) > now + self._skew:
            raise AuthenticationFailed("credential issued in the future")
        jti = str(body.get("jti"))
        with self._lock:
            if jti in self._revoked_tokens:
                raise AuthenticationFailed("credential revoked")
            if body.get("once"):
                if jti in self._seen:
                    raise AuthenticationFailed("credential replay detected")
                if len(self._seen) >= self._seen_limit:
                    # bounded state: evict expired entries, then fail closed if still full
                    for k in [k for k, exp in self._seen.items() if exp < now]:
                        del self._seen[k]
                    if len(self._seen) >= self._seen_limit:
                        raise AuthenticationFailed("replay cache saturated; failing closed")
                self._seen[jti] = float(body["exp"])
        caps = frozenset(body.get("caps") or ())
        if not caps <= CAPABILITIES:
            raise AuthenticationFailed("credential carries unknown capabilities")
        return Principal(str(body["sub"]), str(body["kind"]), body.get("tenant"), caps, jti)


class Authorizer:
    """Deny-by-default capability checks with tenant scoping."""

    @staticmethod
    def require(principal: Principal, capability: str, *, tenant: str | None = None) -> None:
        if capability not in CAPABILITIES:
            raise AuthorizationDenied("unknown capability", capability=capability)
        if capability not in principal.capabilities:
            raise AuthorizationDenied("missing capability", capability=capability, subject=principal.subject)
        if tenant is not None and principal.kind == "workload" and principal.tenant != tenant:
            raise AuthorizationDenied("cross-tenant action refused", subject=principal.subject,
                                      principal_tenant=principal.tenant, target_tenant=tenant)


# --------------------------------------------------------------------------
# #20 Signed classification / provenance (GAP-07 equivalent)
# --------------------------------------------------------------------------


class LabelAuthority:
    """Issues and verifies signed classification labels bound to a payload digest.

    Trust roots are key IDs in a :class:`KeyRing`; rotation is the key ring's
    rotate/verify_only/revoke cycle.  If the key service is down, verification
    raises :class:`KeyUnavailable` and admission fails closed.
    """

    def __init__(self, keyring: KeyRing, *, issuer: str = "gap07-reference", clock: Callable[[], float] = time.time):
        self._keys = keyring
        self._issuer = issuer
        self._clock = clock

    def issue(self, *, classification: str, digest: str, tenant: str, ttl: float = 3600.0,
              provenance: Mapping[str, object] | None = None) -> dict[str, object]:
        now = self._clock()
        body = {"iss": self._issuer, "classification": classification, "digest": digest, "tenant": tenant,
                "iat": now, "exp": now + ttl, "provenance": dict(provenance or {})}
        kid, mac = self._keys.sign(canonical(body))
        return {"body": body, "kid": kid, "mac": mac}

    def verify(self, label: Mapping[str, object], *, classification: str, digest: str | None,
               tenant: str) -> dict[str, object]:
        try:
            body = dict(label["body"])  # type: ignore[arg-type, call-overload]
            ok = self._keys.verify(str(label["kid"]), canonical(body), str(label["mac"]))
        except KeyUnavailable:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise LabelInvalid("malformed classification label") from exc
        if not ok:
            raise LabelInvalid("classification label signature mismatch")
        if body.get("iss") != self._issuer:
            raise LabelInvalid("untrusted label issuer", issuer=body.get("iss"))
        if self._clock() > float(body.get("exp", 0)):
            raise LabelInvalid("classification label expired")
        if body.get("classification") != classification:
            raise LabelInvalid("claimed classification differs from signed label")
        if body.get("tenant") != tenant:
            raise LabelInvalid("label tenant mismatch")
        if digest is None or body.get("digest") != digest:
            raise LabelInvalid("label is not bound to this payload digest")
        return body


# --------------------------------------------------------------------------
# #24 Tamper-evident audit ledger
# --------------------------------------------------------------------------

AUDIT_EVENTS = frozenset({
    "admit", "refuse", "complete", "cancel", "fail", "quarantine_payload", "policy_update",
    "policy_rollback", "freeze", "unfreeze", "quarantine", "unquarantine", "drain", "emergency_disable",
    "authn_failure", "authz_denied", "key_rotate", "key_revoke", "failover", "restore",
})


class AuditLedger:
    """Append-only, hash-chained, MAC-sealed security event log.

    Each record carries ``prev`` (SHA-256 of the previous record) and a MAC
    over the record by the active audit key.  Appends are fsync'd when a file
    path is configured.  :meth:`verify` detects deletion, reordering,
    insertion and in-place edits.  Payload bytes and secrets are never logged.
    """

    GENESIS = "0" * 64

    def __init__(self, keyring: KeyRing, path: str | os.PathLike[str] | None = None, *,
                 clock: Callable[[], float] = time.time):
        self._keys = keyring
        self._path = Path(path) if path else None
        self._clock = clock
        self._lock = threading.Lock()
        self._records: list[dict[str, object]] = []
        self._head = self.GENESIS
        if self._path and self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._records.append(json.loads(line))
            self.verify()
            if self._records:
                self._head = self._digest(self._records[-1])

    @staticmethod
    def _digest(record: Mapping[str, object]) -> str:
        return hashlib.sha256(canonical(record)).hexdigest()

    def append(self, event: str, **fields: object) -> dict[str, object]:
        if event not in AUDIT_EVENTS:
            raise AuditTampered("unknown audit event type", event=event)
        with self._lock:
            body = {"seq": len(self._records), "ts": self._clock(), "event": event,
                    "fields": fields, "prev": self._head}
            kid, mac = self._keys.sign(canonical(body))
            record = {**body, "kid": kid, "mac": mac}
            if self._path:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            self._records.append(record)
            self._head = self._digest(record)
            return dict(record)

    def verify(self) -> int:
        prev = self.GENESIS
        for index, record in enumerate(self._records):
            body = {k: record[k] for k in ("seq", "ts", "event", "fields", "prev")}
            if record["seq"] != index or record["prev"] != prev:
                raise AuditTampered("audit chain broken", at=index)
            if not self._keys.verify(str(record["kid"]), canonical(body), str(record["mac"])):
                raise AuditTampered("audit record MAC mismatch", at=index)
            prev = self._digest(record)
        return len(self._records)

    @property
    def head(self) -> str:
        return self._head

    def records(self) -> list[dict[str, object]]:
        with self._lock:
            return [dict(r) for r in self._records]


# --------------------------------------------------------------------------
# #19 Ambient-authority sandbox and #22 tenant isolation helpers
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Grant:
    """Explicit authority a transport adapter may exercise."""

    network: bool = False
    filesystem_paths: tuple[str, ...] = ()
    shared_memory: bool = False
    devices: tuple[str, ...] = ()
    secrets: tuple[str, ...] = ()


class SandboxViolation(_StructuredError, PermissionError):
    code = "PK_SANDBOX_VIOLATION"


@dataclass
class AuthorityGuard:
    """Checks every privileged action an adapter performs against its grant.

    Adapters call :meth:`check` before opening sockets, files, shared memory,
    devices, or secrets.  Violations raise and are recorded; the process-level
    enforcement (seccomp/landlock/containers) is a deployment control listed in
    ``docs/THREAT_MODEL.md`` and ``WAIVERS.json``.
    """

    grant: Grant
    violations: list[dict[str, object]] = field(default_factory=list)

    def check(self, action: str, target: str = "") -> None:
        g = self.grant
        allowed = {
            "network": g.network,
            "shared_memory": g.shared_memory,
            "filesystem": any(target == p or target.startswith(p.rstrip("/") + "/") for p in g.filesystem_paths),
            "device": target in g.devices,
            "secret": target in g.secrets,
        }.get(action, False)
        if not allowed:
            record = {"action": action, "target": target}
            self.violations.append(record)  # type: ignore[arg-type]  # JSON-shaped mapping
            raise SandboxViolation("adapter attempted ungranted authority", **record)  # type: ignore[arg-type]  # JSON-shaped mapping


def tenant_namespace(tenant: str, name: str) -> str:
    """Deterministic, collision-resistant per-tenant resource name (shm segments etc.)."""
    h = hashlib.sha256(f"{tenant}\x00{name}".encode()).hexdigest()[:24]
    return f"pk06_{h}"
