"""MC12 encryption and managed key rotation; MC02 signed/attested write provenance.

Encryption at rest / in transit payloads: AES-256-GCM envelopes with a 96-bit random
nonce and associated data binding the ciphertext to (tenant, environment, purpose), so a
ciphertext cannot be replayed into another namespace.  ``Keyring`` supports rotation
(new active key, old keys decrypt-only), re-wrapping, and retirement that refuses to
drop a key while any tracked ciphertext still references it.  The keyring material
itself would come from a KMS/HSM in production; this module is the envelope and
lifecycle logic that a KMS adapter plugs into (a KMS integration is a BLOCKED
external dependency, recorded in the checklist evidence).

Provenance: a write document is signed with the author replica's Ed25519 key over
``signable_view`` (every semantic field: tenant, environment, key, value, site,
vector, epoch, schema, deleted, value_type).  Verification uses the key registered for
the *author* in the membership configuration - never a key named by the document - so
a relaying peer cannot re-attribute or alter a write.
"""
from __future__ import annotations

import os
import threading

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .errors import ConfigError, IntegrityError, ProvenanceError, SecurityError
from .identity import b64, fingerprint, unb64
from .schemas import canonical_bytes, signable_view

ENVELOPE = "GAP05_AEAD/1"
SIG_ALG = "ed25519"


class Keyring:
    def __init__(self):
        self._keys: dict[str, bytes] = {}
        self._active: str | None = None
        self._retired: set[str] = set()
        self._refs: dict[str, int] = {}
        self._lock = threading.Lock()

    @property
    def active_key_id(self) -> str:
        if self._active is None:
            raise ConfigError("keyring has no active key")
        return self._active

    def rotate(self, material: bytes | None = None) -> str:
        material = material or AESGCM.generate_key(bit_length=256)
        if len(material) != 32:
            raise ConfigError("AES-256 key must be 32 bytes")
        kid = os.urandom(6).hex()
        with self._lock:
            self._keys[kid] = material
            self._active = kid
        return kid

    def encrypt(self, plaintext: bytes, *, tenant: str, environment: str, purpose: str) -> dict:
        kid = self.active_key_id
        nonce = os.urandom(12)
        aad = canonical_bytes({"t": tenant, "e": environment, "p": purpose, "k": kid, "f": ENVELOPE})
        ct = AESGCM(self._keys[kid]).encrypt(nonce, plaintext, aad)
        with self._lock:
            self._refs[kid] = self._refs.get(kid, 0) + 1
        return {"format": ENVELOPE, "kid": kid, "nonce": b64(nonce), "ct": b64(ct)}

    def decrypt(self, env: dict, *, tenant: str, environment: str, purpose: str) -> bytes:
        if env.get("format") != ENVELOPE:
            raise IntegrityError("unknown envelope format", code="CORR_ENVELOPE_FORMAT")
        kid = env.get("kid")
        if kid in self._retired or kid not in self._keys:
            raise SecurityError(f"key {kid} unavailable", code="SEC_KEY_UNAVAILABLE")
        aad = canonical_bytes({"t": tenant, "e": environment, "p": purpose, "k": kid, "f": ENVELOPE})
        try:
            return AESGCM(self._keys[kid]).decrypt(unb64(env["nonce"]), unb64(env["ct"]), aad)
        except InvalidTag as exc:
            raise IntegrityError("ciphertext failed authentication", code="CORR_AEAD_TAG") from exc

    def rewrap(self, env: dict, **ctx) -> dict:
        plain = self.decrypt(env, **ctx)
        new = self.encrypt(plain, **ctx)
        with self._lock:
            self._refs[env["kid"]] = max(0, self._refs.get(env["kid"], 0) - 1)
        return new

    def retire(self, kid: str) -> None:
        with self._lock:
            if kid == self._active:
                raise ConfigError("cannot retire the active key; rotate first")
            if self._refs.get(kid, 0) > 0:
                raise ConfigError(f"key {kid} still protects {self._refs[kid]} envelopes; rewrap first",
                                  code="CORR_KEY_IN_USE")
            self._retired.add(kid)
            self._keys.pop(kid, None)


def sign_write(doc: dict, key: Ed25519PrivateKey) -> dict:
    out = dict(doc)
    out.pop("provenance", None)
    sig = key.sign(canonical_bytes({"ctx": "GAP05-WRITE/1", "w": signable_view(out)}))
    out["provenance"] = {"alg": SIG_ALG, "key_id": fingerprint(key.public_key()), "sig": b64(sig)}
    return out


def verify_write(doc: dict, membership) -> None:
    prov = doc.get("provenance")
    if not prov:
        raise ProvenanceError("write is unsigned", code="SEC_UNSIGNED")
    if prov.get("alg") != SIG_ALG:
        raise ProvenanceError("unsupported signature algorithm", code="SEC_BAD_ALG")
    rec = membership.current.replicas.get(doc["site"])
    if rec is None:
        raise ProvenanceError("author is not a known replica", code="SEC_UNKNOWN_AUTHOR")
    if prov["key_id"] not in rec.key_fingerprints:
        raise ProvenanceError("signing key not registered for the author", code="SEC_KEY_NOT_REGISTERED")
    idx = rec.key_fingerprints.index(prov["key_id"])
    if idx >= len(rec.public_keys):
        raise ProvenanceError("author public key not provisioned", code="SEC_KEY_NOT_PROVISIONED")
    pub = Ed25519PublicKey.from_public_bytes(unb64(rec.public_keys[idx]))
    try:
        pub.verify(unb64(prov["sig"]), canonical_bytes({"ctx": "GAP05-WRITE/1", "w": signable_view(doc)}))
    except InvalidSignature as exc:
        raise ProvenanceError("write signature invalid", code="SEC_BAD_SIGNATURE") from exc
