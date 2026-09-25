"""Key/certificate lifecycle registry (component 04) and the Ed25519
signature/provenance verifier (component 02).

The registry is the single place key state lives: each key has an id, owner
reporter, algorithm, validity window, scope and status.  Rotation adds a new
key with an overlap window; revocation is immediate and permanent; expiry is
evaluated at the verification instant with a half-open window
``not_before <= now < not_after``.  Every mutation is written to the audit
ledger when one is attached.
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from ..runtime import MAX_TEXT, ReporterAuthority, ReporterUntrusted
from . import ed25519
from .canonical import PROFILE_ID, canonical_bytes
from .errors import Expired, Malformed, Revoked, Unverifiable

ALLOWED_ALGORITHMS = frozenset({"ed25519"})
DEPRECATED_ALGORITHMS = frozenset({"hmac-sha256-fixture"})
STATUSES = ("active", "retiring", "revoked")
VERIFIER_BUILD = "gap09-components/5.1.0"


@dataclass(frozen=True)
class KeyRecord:
    key_id: str
    reporter: str
    algorithm: str
    public_key: bytes
    not_before: int
    not_after: int
    tenants: frozenset
    environments: frozenset = frozenset({"*"})
    sites: frozenset = frozenset({"*"})
    workloads: frozenset = frozenset({"*"})
    attested_level: str = "software"
    status: str = "active"
    provenance: str = ""

    def __post_init__(self) -> None:
        for name in ("key_id", "reporter"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v or len(v) > MAX_TEXT or v != v.strip():
                raise Malformed(f"{name} invalid")
        if self.algorithm not in ALLOWED_ALGORITHMS:
            raise Malformed("algorithm not approved", algorithm=self.algorithm)
        if len(self.public_key) != 32:
            raise Malformed("ed25519 public key must be 32 bytes")
        if not (0 <= self.not_before < self.not_after < 2**63):
            raise Malformed("validity window invalid")
        if self.status not in STATUSES:
            raise Malformed("status invalid")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.public_key).hexdigest()


class KeyRegistry:
    def __init__(self, audit=None, max_keys: int = 10_000) -> None:
        self._keys: dict[str, KeyRecord] = {}
        self._lock = threading.RLock()
        self._audit = audit
        self._max = max_keys

    def _log(self, action: str, rec: KeyRecord, actor: str) -> None:
        if self._audit is not None:
            self._audit.append("key_lifecycle", {"action": action, "key_id": rec.key_id,
                                                 "reporter": rec.reporter, "fingerprint": rec.fingerprint,
                                                 "status": rec.status}, actor=actor)

    def add(self, rec: KeyRecord, *, actor: str) -> None:
        with self._lock:
            if rec.key_id in self._keys:
                raise Malformed("key id already registered; key ids are never reused", key_id=rec.key_id)
            if len(self._keys) >= self._max:
                raise Malformed("key registry full")
            self._keys[rec.key_id] = rec
            self._log("add", rec, actor)

    def rotate(self, old_id: str, new: KeyRecord, *, overlap_until: int, actor: str) -> None:
        with self._lock:
            old = self._keys.get(old_id)
            if old is None or old.status == "revoked":
                raise Malformed("cannot rotate from unknown or revoked key")
            if new.reporter != old.reporter:
                raise Malformed("rotation may not change key owner")
            self.add(new, actor=actor)
            retiring = replace(old, status="retiring", not_after=min(old.not_after, overlap_until))
            self._keys[old_id] = retiring
            self._log("retire", retiring, actor)

    def revoke(self, key_id: str, *, actor: str, reason: str) -> None:
        with self._lock:
            rec = self._keys.get(key_id)
            if rec is None:
                raise Malformed("unknown key id")
            rec = replace(rec, status="revoked", provenance=rec.provenance + f";revoked:{reason[:64]}")
            self._keys[key_id] = rec
            self._log("revoke", rec, actor)

    def get(self, key_id: str) -> KeyRecord | None:
        with self._lock:
            return self._keys.get(key_id)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [{"key_id": r.key_id, "reporter": r.reporter, "algorithm": r.algorithm,
                     "fingerprint": r.fingerprint, "status": r.status,
                     "not_before": r.not_before, "not_after": r.not_after}
                    for r in sorted(self._keys.values(), key=lambda r: r.key_id)]


class Ed25519Verifier:
    """TrustVerifier implementation over GAP09-CSP/1 envelopes.

    ``attestation`` must carry ``key_id`` and ``profile``.  The signature is
    over ``canonical_bytes(envelope)`` -- the store's own legacy payload bytes
    are NOT what is signed, so ``payload`` is re-derived by the caller via
    :func:`sign_submission`/``verify_submission``.  To stay a drop-in
    ``TrustVerifier`` the ``payload`` argument is accepted and the signature
    is checked over it; callers wiring CSP/1 pass the CSP/1 bytes
    (see ``ingest.VerifiedIngest``).
    """

    def __init__(self, registry: KeyRegistry, *, attestation_verifier=None, transcripts=None) -> None:
        self.registry = registry
        self.attestation_verifier = attestation_verifier
        self.transcripts = transcripts if transcripts is not None else []

    def verify(self, *, reporter: str, payload: bytes, signature, attestation: Mapping[str, Any], now: int) -> ReporterAuthority:
        key_id = attestation.get("key_id")
        decision = {"reporter": reporter, "key_id": key_id if isinstance(key_id, str) else None,
                    "envelope_sha256": hashlib.sha256(payload).hexdigest(), "profile": attestation.get("profile"),
                    "verifier_build": VERIFIER_BUILD, "at": now}
        try:
            if attestation.get("profile") != PROFILE_ID:
                raise Unverifiable("unsupported or missing signing profile")
            if not isinstance(key_id, str) or not key_id or len(key_id) > MAX_TEXT:
                raise Unverifiable("key_id missing or malformed")
            rec = self.registry.get(key_id)
            if rec is None:
                raise Unverifiable("unknown key id")
            decision["algorithm"] = rec.algorithm
            decision["fingerprint"] = rec.fingerprint
            if rec.reporter != reporter:
                raise Unverifiable("key/reporter mismatch")
            if rec.status == "revoked":
                raise Revoked("key revoked")
            if now < rec.not_before:
                raise Expired("key not yet valid")
            if now >= rec.not_after:
                raise Expired("key expired")
            sig = _decode_sig(signature)
            if not ed25519.verify(rec.public_key, payload, sig):
                raise Unverifiable("signature verification failed")
            level = rec.attested_level
            if self.attestation_verifier is not None:
                att = self.attestation_verifier.verify_evidence(attestation.get("evidence"), reporter=reporter, now=now)
                level = att.level
                decision["attestation"] = att.as_dict()
            authority = ReporterAuthority(reporter=reporter, attested_level=level, tenants=rec.tenants,
                                          environments=rec.environments, sites=rec.sites,
                                          workloads=rec.workloads, expires_at=rec.not_after)
            decision["outcome"] = "accept"
            return authority
        except (Unverifiable, Revoked, Expired) as exc:
            decision["outcome"] = "reject"
            decision["reason"] = exc.code
            raise ReporterUntrusted(f"{reporter}: {exc}", reason=exc.code) from exc
        finally:
            self.transcripts.append(decision)
            if len(self.transcripts) > 10_000:
                del self.transcripts[:1000]


def _decode_sig(signature) -> bytes:
    if isinstance(signature, bytes):
        try:
            signature = signature.decode("ascii")
        except UnicodeDecodeError as exc:
            raise Unverifiable("signature not ascii hex") from exc
    if not isinstance(signature, str) or len(signature) != 128:
        raise Unverifiable("ed25519 signature must be 128 hex characters")
    if signature != signature.lower():
        raise Unverifiable("signature hex must be lowercase (single encoding)")
    try:
        return bytes.fromhex(signature)
    except ValueError as exc:
        raise Unverifiable("signature not hex") from exc


def sign_envelope(secret: bytes, envelope: dict) -> str:
    return ed25519.sign(secret, canonical_bytes(envelope)).hex()
