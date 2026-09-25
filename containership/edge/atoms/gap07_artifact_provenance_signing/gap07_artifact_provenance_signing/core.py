"""Dependency-free signing/provenance core for GAP-07.

The production component wrapper depends on ``pk_core``; this module intentionally
uses only the Python standard library so its security-critical behavior remains
testable in isolation.

HMAC is retained only as a deterministic reference backend. Production estates
should provide asymmetric signing/verification through a KMS/HSM or a Sigstore-
compatible backend; see ``MISSING_COMPONENTS.md``.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol, Sequence

SIGNATURE_SCHEMA = "PK_SIGNATURE/2"
VERIFICATION_SCHEMA = "PK_VERIFICATION/2"
PROVENANCE_SCHEMA = "PK_PROVENANCE/2"
PROVENANCE_LINK_SCHEMA = "PK_PROVENANCE_LINK/2"
AUDIT_SCHEMA = "PK_AUDIT_EVENT/1"
ALGORITHM = "HMAC-SHA256-REF-v2"

ROLE_FOR_KIND = {
    "code": "release",
    "policy": "policy",
    "grant": "authority",
    "label": "data",
    "attestation": "authority",
    "bundle": "release",
}
_ALLOWED_ROLES = frozenset(ROLE_FOR_KIND.values())
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class VerificationError(PermissionError):
    """Base class for machine-readable verification refusals."""

    code = "VERIFICATION_FAILED"

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class Unsigned(VerificationError):
    code = "UNSIGNED"


class SignatureInvalid(VerificationError):
    code = "SIGNATURE_INVALID"


class SignerUntrusted(VerificationError):
    code = "SIGNER_UNTRUSTED"


class ProvenanceInvalid(ValueError):
    code = "PROVENANCE_INVALID"


class KeyProvider(Protocol):
    """External key-custody boundary used by the reference verifier."""

    def get_key(self, key_id: str) -> bytes:
        """Return key bytes for ``key_id`` or raise ``KeyError``."""


class InMemoryKeyProvider:
    """Test/development key provider; never use as production key custody."""

    def __init__(self, keys: Mapping[str, bytes] | None = None):
        self.__keys: dict[str, bytes] = {}
        for key_id, key in (keys or {}).items():
            self.put(key_id, key)

    def __repr__(self) -> str:  # avoid accidentally logging key material
        return f"{type(self).__name__}(key_count={len(self.__keys)})"

    def put(self, key_id: str, key: bytes) -> None:
        _validate_token(key_id, "key_id")
        if not isinstance(key, bytes) or len(key) < 16:
            raise ValueError("reference HMAC keys must be bytes and at least 16 bytes")
        self.__keys[key_id] = key

    def get_key(self, key_id: str) -> bytes:
        return self.__keys[key_id]


def _validate_token(value: str, field_name: str, *, max_len: int = 128) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    value = value.strip()
    if len(value) > max_len:
        raise ValueError(f"{field_name} exceeds {max_len} characters")
    if any(ord(ch) < 0x20 for ch in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def _validate_now(now: int) -> int:
    if isinstance(now, bool) or not isinstance(now, int) or now < 0:
        raise ValueError("time values must be non-negative integer seconds")
    return now


def _payload_bytes(payload: bytes | bytearray | memoryview) -> bytes:
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        raise TypeError("artifact payload must be bytes-like")
    return bytes(payload)


def canonical_json(value: Mapping[str, Any]) -> bytes:
    """Return a deterministic UTF-8 JSON representation."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(payload: bytes | bytearray | memoryview) -> str:
    return hashlib.sha256(_payload_bytes(payload)).hexdigest()


def digest_chunks(chunks: Iterable[bytes | bytearray | memoryview]) -> str:
    """Hash a stream without materializing the whole artifact in memory."""
    hasher = hashlib.sha256()
    for chunk in chunks:
        hasher.update(_payload_bytes(chunk))
    return hasher.hexdigest()


@dataclass(frozen=True)
class Signature:
    schema: str
    algorithm: str
    environment: str
    kind: str
    signer: str
    key_id: str
    digest: str
    issued_at: int
    mac: str

    def unsigned_fields(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "algorithm": self.algorithm,
            "environment": self.environment,
            "kind": self.kind,
            "signer": self.signer,
            "key_id": self.key_id,
            "digest": self.digest,
            "issued_at": self.issued_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_fields(), "mac": self.mac}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Signature":
        if not isinstance(data, Mapping):
            raise SignatureInvalid("signature must be an object", details={"field": "signature"})
        required = {"schema", "algorithm", "environment", "kind", "signer", "key_id", "digest", "issued_at", "mac"}
        missing = sorted(required - set(data))
        extra = sorted(set(data) - required)
        if missing or extra:
            raise SignatureInvalid(
                "signature fields do not match PK_SIGNATURE/2",
                details={"missing": missing, "extra": extra},
            )
        sig = cls(**{k: data[k] for k in required})
        _validate_signature_shape(sig)
        return sig


@dataclass(frozen=True)
class SignerRecord:
    role: str
    active_key_id: str
    verify_key_ids: frozenset[str]


@dataclass
class AuditLedger:
    """Local hash-chained security-event ledger.

    This makes deletion/reordering/modification detectable inside an exported
    ledger. Durable external anchoring remains an estate integration concern.
    """

    events: list[dict[str, Any]] = field(default_factory=list)
    head: str | None = None
    _lock: Any = field(default_factory=threading.Lock, repr=False, compare=False)

    def append(self, event: str, details: Mapping[str, Any] | None = None, *, now: int = 0, actor: str | None = None) -> dict[str, Any]:
        event = _validate_token(event, "event")
        now = _validate_now(now)
        details = dict(details or {})
        details.setdefault("event_id", str(uuid.uuid4()))
        if actor is not None:
            details["actor"] = actor
        with self._lock:
            return self._append_locked(event, details, now)

    def _append_locked(self, event: str, details: dict[str, Any], now: int) -> dict[str, Any]:
        body = {
            "schema": AUDIT_SCHEMA,
            "sequence": len(self.events),
            "event": event,
            "time": now,
            "details": details,
            "previous": self.head,
        }
        event_hash = hashlib.sha256(canonical_json(body)).hexdigest()
        record = {**body, "hash": event_hash}
        self.events.append(record)
        self.head = event_hash
        return dict(record)

    def verify(self) -> bool:
        previous = None
        for sequence, record in enumerate(self.events):
            if not isinstance(record, dict):
                return False
            body = {k: record.get(k) for k in ("schema", "sequence", "event", "time", "details", "previous")}
            if body["schema"] != AUDIT_SCHEMA or body["sequence"] != sequence or body["previous"] != previous:
                return False
            computed = hashlib.sha256(canonical_json(body)).hexdigest()
            if not hmac.compare_digest(str(record.get("hash", "")), computed):
                return False
            previous = computed
        return previous == self.head

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "PK_AUDIT_LEDGER/1", "events": [dict(e) for e in self.events], "head": self.head}


@dataclass
class TrustStore:
    """Accepted signer metadata with externalized key custody and revocation."""

    environment: str
    key_provider: KeyProvider
    signers: dict[str, SignerRecord] = field(default_factory=dict)
    revoked: set[str] = field(default_factory=set)
    updated_at: int = 0
    audit: AuditLedger | None = None

    def __post_init__(self) -> None:
        self.environment = _validate_token(self.environment, "environment")
        if not hasattr(self.key_provider, "get_key"):
            raise TypeError("key_provider must implement get_key(key_id)")

    def _event(self, event: str, details: Mapping[str, Any], *, now: int = 0) -> None:
        if self.audit is not None:
            self.audit.append(event, {"environment": self.environment, **dict(details)}, now=now)

    def _touch(self, now: int) -> None:
        self.updated_at = max(self.updated_at, _validate_now(now))

    def add(self, signer: str, role: str, key_id: str, now: int = 0) -> None:
        signer = _validate_token(signer, "signer")
        role = _validate_token(role, "role")
        key_id = _validate_token(key_id, "key_id")
        if role not in _ALLOWED_ROLES:
            raise ValueError(f"{signer}: unknown signer role {role!r}")
        # Resolve once so typos/missing keys cannot activate a broken signer.
        _get_provider_key(self.key_provider, key_id)
        record = SignerRecord(role, key_id, frozenset({key_id}))
        existing = self.signers.get(signer)
        if existing is not None and existing != record:
            raise ValueError(f"{signer}: signer already exists; use rotate() for key changes")
        self.signers[signer] = record
        self._touch(now)
        self._event("trust.add", {"signer": signer, "role": role, "key_id": key_id}, now=now)

    def rotate(self, signer: str, new_key_id: str, *, retain_previous: bool = True, now: int = 0) -> None:
        signer = _validate_token(signer, "signer")
        new_key_id = _validate_token(new_key_id, "new_key_id")
        if signer in self.revoked:
            raise SignerUntrusted(f"{signer} is revoked", details={"signer": signer, "reason": "revoked"})
        old = self.signers.get(signer)
        if old is None:
            raise SignerUntrusted(f"{signer} is not trusted", details={"signer": signer, "reason": "absent"})
        _get_provider_key(self.key_provider, new_key_id)
        keys = set(old.verify_key_ids) if retain_previous else set()
        keys.add(new_key_id)
        self.signers[signer] = SignerRecord(old.role, new_key_id, frozenset(keys))
        self._touch(now)
        self._event(
            "trust.rotate",
            {"signer": signer, "old_key_id": old.active_key_id, "new_key_id": new_key_id, "retain_previous": retain_previous},
            now=now,
        )

    def retire_key(self, signer: str, key_id: str, *, now: int = 0) -> None:
        signer = _validate_token(signer, "signer")
        key_id = _validate_token(key_id, "key_id")
        record = self.signers.get(signer)
        if record is None:
            raise SignerUntrusted(f"{signer} is not trusted", details={"signer": signer, "reason": "absent"})
        if key_id == record.active_key_id:
            raise ValueError("cannot retire the active signer key; rotate first")
        if key_id not in record.verify_key_ids:
            raise ValueError(f"{signer}: key {key_id!r} is not an accepted verification key")
        keys = set(record.verify_key_ids)
        keys.remove(key_id)
        self.signers[signer] = SignerRecord(record.role, record.active_key_id, frozenset(keys))
        self._touch(now)
        self._event("trust.retire_key", {"signer": signer, "key_id": key_id}, now=now)

    def revoke(self, signer: str, now: int = 0) -> None:
        signer = _validate_token(signer, "signer")
        if signer not in self.signers:
            raise ValueError(f"{signer}: cannot revoke an unknown signer")
        self.revoked.add(signer)
        self._touch(now)
        self._event("trust.revoke", {"signer": signer}, now=now)

    def snapshot(self) -> dict[str, Any]:
        """Return secret-free PK_TRUST_STORE/2 metadata for export/inspection."""
        return {
            "schema": "PK_TRUST_STORE/2",
            "environment": self.environment,
            "updated_at": self.updated_at,
            "signers": {
                signer: {
                    "role": record.role,
                    "active_key_id": record.active_key_id,
                    "verify_key_ids": sorted(record.verify_key_ids),
                }
                for signer, record in sorted(self.signers.items())
            },
            "revoked": sorted(self.revoked),
        }

    def role_of(self, signer: str) -> str:
        signer = _validate_token(signer, "signer")
        if signer not in self.signers or signer in self.revoked:
            reason = "revoked" if signer in self.revoked else "absent"
            raise SignerUntrusted(
                f"{signer} is not a trusted signer in {self.environment}",
                details={"signer": signer, "environment": self.environment, "reason": reason},
            )
        return self.signers[signer].role

    def _record(self, signer: str) -> SignerRecord:
        self.role_of(signer)
        return self.signers[signer]

    def sign(self, signer: str, payload: bytes | bytearray | memoryview, kind: str, *, now: int = 0) -> Signature:
        signer = _validate_token(signer, "signer")
        kind = _validate_kind(kind)
        now = _validate_now(now)
        record = self._record(signer)
        required = ROLE_FOR_KIND[kind]
        if record.role != required:
            raise SignerUntrusted(
                f"{signer} holds role {record.role!r}; {kind!r} requires {required!r}",
                details={"signer": signer, "role": record.role, "kind": kind, "required_role": required},
            )
        artifact_digest = digest(payload)
        fields = {
            "schema": SIGNATURE_SCHEMA,
            "algorithm": ALGORITHM,
            "environment": self.environment,
            "kind": kind,
            "signer": signer,
            "key_id": record.active_key_id,
            "digest": artifact_digest,
            "issued_at": now,
        }
        key = _get_provider_key(self.key_provider, record.active_key_id)
        mac = hmac.new(key, canonical_json(fields), hashlib.sha256).hexdigest()
        signature = Signature(**fields, mac=mac)
        self._event("artifact.sign", {"signer": signer, "kind": kind, "key_id": record.active_key_id, "digest": artifact_digest}, now=now)
        return signature

    def verify(
        self,
        signature: Signature | Mapping[str, Any] | None,
        payload: bytes | bytearray | memoryview,
        kind: str,
        *,
        now: int | None = None,
        max_age_seconds: int | None = None,
    ) -> dict[str, Any]:
        kind = _validate_kind(kind)
        if signature is None:
            self._event("artifact.verify_refused", {"kind": kind, "code": Unsigned.code}, now=0 if now is None else _validate_now(now))
            raise Unsigned(f"{kind} artifacts require a signature", details={"kind": kind})
        sig = signature if isinstance(signature, Signature) else Signature.from_dict(signature)
        _validate_signature_shape(sig)
        event_now = sig.issued_at if now is None else _validate_now(now)

        def refuse(exc: VerificationError) -> None:
            self._event(
                "artifact.verify_refused",
                {"kind": kind, "signer": sig.signer, "key_id": sig.key_id, "digest": sig.digest, "code": exc.code},
                now=event_now,
            )
            raise exc

        if sig.schema != SIGNATURE_SCHEMA or sig.algorithm != ALGORITHM:
            refuse(SignatureInvalid("unsupported signature schema or algorithm", details={"schema": sig.schema, "algorithm": sig.algorithm}))
        if sig.environment != self.environment:
            refuse(SignatureInvalid("signature environment does not match trust store", details={"signature_environment": sig.environment, "environment": self.environment}))
        if sig.kind != kind:
            refuse(SignatureInvalid("signature is bound to a different artifact kind", details={"signature_kind": sig.kind, "requested_kind": kind}))

        try:
            record = self._record(sig.signer)
        except SignerUntrusted as exc:
            refuse(exc)
        required = ROLE_FOR_KIND[kind]
        if record.role != required:
            refuse(SignerUntrusted(
                f"{sig.signer} holds role {record.role!r}; {kind!r} requires {required!r}",
                details={"signer": sig.signer, "role": record.role, "kind": kind, "required_role": required},
            ))
        if sig.key_id not in record.verify_key_ids:
            refuse(SignerUntrusted(
                f"{sig.signer}: key {sig.key_id!r} is not accepted",
                details={"signer": sig.signer, "key_id": sig.key_id, "reason": "key_not_accepted"},
            ))

        actual = digest(payload)
        if not hmac.compare_digest(actual, sig.digest):
            refuse(SignatureInvalid("digest mismatch", details={"signed_digest": sig.digest, "actual_digest": actual}))

        if max_age_seconds is not None:
            if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds < 0:
                raise ValueError("max_age_seconds must be a non-negative integer")
            if now is None:
                raise ValueError("now is required when max_age_seconds is used")
            if sig.issued_at > now:
                refuse(SignatureInvalid("signature issuance time is in the future", details={"issued_at": sig.issued_at, "now": now}))
            if now - sig.issued_at > max_age_seconds:
                refuse(SignatureInvalid("signature exceeds the configured maximum age", details={"issued_at": sig.issued_at, "now": now, "max_age_seconds": max_age_seconds}))

        try:
            key = _get_provider_key(self.key_provider, sig.key_id)
        except ValueError as exc:
            refuse(SignerUntrusted(str(exc), details={"signer": sig.signer, "key_id": sig.key_id, "reason": "key_unavailable"}))
        expected = hmac.new(key, canonical_json(sig.unsigned_fields()), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig.mac):
            refuse(SignatureInvalid("signature authentication tag does not verify", details={"signer": sig.signer, "key_id": sig.key_id}))

        result = {
            "schema": VERIFICATION_SCHEMA,
            "signature_schema": sig.schema,
            "algorithm": sig.algorithm,
            "environment": self.environment,
            "kind": kind,
            "signer": sig.signer,
            "role": record.role,
            "key_id": sig.key_id,
            "digest": actual,
            "issued_at": sig.issued_at,
            "verified": True,
        }
        self._event("artifact.verify", {"kind": kind, "signer": sig.signer, "key_id": sig.key_id, "digest": actual}, now=event_now)
        return result


def _get_provider_key(provider: KeyProvider, key_id: str) -> bytes:
    try:
        key = provider.get_key(key_id)
    except KeyError as exc:
        raise ValueError(f"key provider has no key {key_id!r}") from exc
    if not isinstance(key, bytes) or len(key) < 16:
        raise ValueError(f"key provider returned invalid key material for {key_id!r}")
    return key


def _validate_kind(kind: str) -> str:
    kind = _validate_token(kind, "kind")
    if kind not in ROLE_FOR_KIND:
        raise SignerUntrusted(
            f"{kind!r} is not a known artifact kind; no signer role may vouch for it",
            details={"kind": kind, "reason": "unknown_kind"},
        )
    return kind


def _validate_signature_shape(sig: Signature) -> None:
    for field_name in ("schema", "algorithm", "environment", "kind", "signer", "key_id"):
        try:
            _validate_token(getattr(sig, field_name), field_name)
        except (TypeError, ValueError) as exc:
            raise SignatureInvalid(f"invalid signature field {field_name!r}", details={"field": field_name}) from exc
    if not isinstance(sig.issued_at, int) or isinstance(sig.issued_at, bool) or sig.issued_at < 0:
        raise SignatureInvalid("issued_at must be a non-negative integer", details={"field": "issued_at"})
    if not isinstance(sig.digest, str) or _HEX_64.fullmatch(sig.digest) is None:
        raise SignatureInvalid("digest must be a lowercase SHA-256 hex value", details={"field": "digest"})
    if not isinstance(sig.mac, str) or _HEX_64.fullmatch(sig.mac) is None:
        raise SignatureInvalid("mac must be a lowercase SHA-256 hex value", details={"field": "mac"})


def provenance(chain: Sequence[tuple[str, bytes | bytearray | memoryview]]) -> dict[str, Any]:
    """Create a metadata-bound provenance hash chain.

    Each link hash commits to its index, step name, artifact digest, and previous
    link hash. Editing/reordering any of those fields changes the final head.
    """
    if not isinstance(chain, Sequence) or isinstance(chain, (str, bytes, bytearray, memoryview)):
        raise TypeError("provenance chain must be a sequence of (step, payload) pairs")
    if not chain:
        raise ValueError("a provenance chain needs at least one step")
    if len(chain) > 4096:
        raise ValueError("provenance chain exceeds 4096 links")
    links: list[dict[str, Any]] = []
    previous = None
    for index, item in enumerate(chain):
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"provenance link {index} must be a (step, payload) pair")
        step, payload = item
        step = _validate_token(step, f"step[{index}]", max_len=256)
        artifact_digest = digest(payload)
        body = {
            "schema": PROVENANCE_LINK_SCHEMA,
            "index": index,
            "step": step,
            "artifact_digest": artifact_digest,
            "previous": previous,
        }
        link_digest = hashlib.sha256(canonical_json(body)).hexdigest()
        links.append({**body, "link_digest": link_digest})
        previous = link_digest
    return {"schema": PROVENANCE_SCHEMA, "links": links, "head": previous}


def verify_provenance(
    record: Mapping[str, Any],
    payloads: Sequence[bytes | bytearray | memoryview] | None = None,
) -> dict[str, Any]:
    """Verify provenance structure/hash chain and optionally the linked payloads."""
    if not isinstance(record, Mapping):
        raise ProvenanceInvalid("provenance record must be an object")
    if record.get("schema") != PROVENANCE_SCHEMA:
        raise ProvenanceInvalid("unsupported provenance schema")
    links = record.get("links")
    if not isinstance(links, list) or not links or len(links) > 4096:
        raise ProvenanceInvalid("provenance links must contain 1..4096 entries")
    if payloads is not None and len(payloads) != len(links):
        raise ProvenanceInvalid("payload count does not match provenance link count")

    previous = None
    for index, link in enumerate(links):
        if not isinstance(link, Mapping):
            raise ProvenanceInvalid(f"link {index} is not an object")
        body = {
            "schema": link.get("schema"),
            "index": link.get("index"),
            "step": link.get("step"),
            "artifact_digest": link.get("artifact_digest"),
            "previous": link.get("previous"),
        }
        if body["schema"] != PROVENANCE_LINK_SCHEMA or body["index"] != index or body["previous"] != previous:
            raise ProvenanceInvalid(f"link {index} breaks provenance ordering")
        try:
            _validate_token(body["step"], f"step[{index}]", max_len=256)
        except (TypeError, ValueError) as exc:
            raise ProvenanceInvalid(f"link {index} has an invalid step name") from exc
        if not isinstance(body["artifact_digest"], str) or _HEX_64.fullmatch(body["artifact_digest"]) is None:
            raise ProvenanceInvalid(f"link {index} has an invalid artifact digest")
        computed = hashlib.sha256(canonical_json(body)).hexdigest()
        if not isinstance(link.get("link_digest"), str) or not hmac.compare_digest(link["link_digest"], computed):
            raise ProvenanceInvalid(f"link {index} digest does not verify")
        if payloads is not None and not hmac.compare_digest(body["artifact_digest"], digest(payloads[index])):
            raise ProvenanceInvalid(f"link {index} payload digest does not verify")
        previous = computed

    head = record.get("head")
    if not isinstance(head, str) or not hmac.compare_digest(head, previous or ""):
        raise ProvenanceInvalid("provenance head does not match the final link")
    return {"schema": "PK_PROVENANCE_VERIFICATION/1", "verified": True, "link_count": len(links), "head": head}
