"""Snapshot confidentiality envelope and key service port (C047, X006, X009, X010).

Envelope ``AES-256-GCM-CHUNKED/1``:

* one fresh 256-bit data-encryption key (DEK) per snapshot, wrapped by a
  key-encryption key (KEK) held by a :class:`KeyService` (envelope encryption);
  the DEK wrap is itself AES-256-GCM with the snapshot's security context as
  associated data, so a wrapped DEK cannot be moved to another snapshot;
* the memory/device image is split into fixed-size chunks; chunk *i* uses the
  96-bit nonce ``i (8 bytes, big-endian) || 0x00000000``. Nonces are unique
  because the DEK is never reused across snapshots;
* each chunk's AAD binds ``{aad_schema, snapshot_id, tenant, workload,
  environment, site, fingerprint, generation, index, total, final}`` in
  canonical encoding, so truncation, reordering, duplication, a dropped final
  chunk, or a chunk transplanted from another snapshot fails authentication;
* :func:`open_envelope` authenticates **every** chunk before returning any
  plaintext (no unauthenticated streaming into the hypervisor).

Crypto-erase (X010): destroying a snapshot's DEK is done by deleting the
wrapped DEK from metadata *and* the blob; disabling/destroying a KEK version
makes every DEK wrapped under it permanently unrecoverable.

Requires the ``cryptography`` package (pinned in ``requirements.lock``). If it
is absent, :func:`require_crypto` raises and the service refuses to start in
any profile other than ``reference`` — there is no plaintext fallback.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import threading
from dataclasses import dataclass, field

from .errors import SnapshotServiceError
from .schema import canonical_bytes

try:  # pragma: no cover - import guard
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAVE_CRYPTO = True
except ImportError:  # pragma: no cover
    AESGCM = None  # type: ignore
    InvalidTag = Exception  # type: ignore
    HAVE_CRYPTO = False

ENVELOPE_ALG = "AES-256-GCM-CHUNKED/1"
AAD_SCHEMA = "PK_SNAPSHOT_AAD/1"
DEFAULT_CHUNK = 1024 * 1024


def require_crypto() -> None:
    if not HAVE_CRYPTO:
        raise SnapshotServiceError("SNAP_DEPENDENCY_UNAVAILABLE", "cryptography package not installed")


def _nonce(index: int) -> bytes:
    return index.to_bytes(8, "big") + b"\x00\x00\x00\x00"


def _aad(ctx: dict, index: int, total: int) -> bytes:
    return canonical_bytes({"aad_schema": AAD_SCHEMA, **ctx, "index": index, "total": total,
                            "final": index == total - 1})


# --------------------------------------------------------------------- KMS port
class KeyService:
    """Port: wrap/unwrap DEKs under a named KEK. Production = cloud KMS/HSM adapter."""

    def wrap(self, key_id: str, dek: bytes, context: dict) -> tuple[int, str]:  # pragma: no cover
        raise NotImplementedError

    def unwrap(self, key_id: str, version: int, wrapped: str, context: dict) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def health(self) -> bool:  # pragma: no cover
        raise NotImplementedError


@dataclass
class _KeyVersion:
    material: bytes
    state: str = "enabled"  # enabled | decrypt_only | disabled | destroyed


@dataclass
class LocalKeyService(KeyService):
    """In-process KEK store for tests, reference profile and edge drills.

    Not a production KMS: KEKs live in process memory. It implements the
    same semantics a managed KMS adapter must honour — versioned keys,
    rotation (new version encrypts, old versions decrypt-only), disable,
    destroy (crypto-erase), availability outage injection, and a call counter
    used by the quota/fairness tests.
    """

    keys: dict[str, list[_KeyVersion]] = field(default_factory=dict)
    available: bool = True
    calls: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def create(self, key_id: str) -> int:
        with self._lock:
            self.keys.setdefault(key_id, []).append(_KeyVersion(secrets.token_bytes(32)))
            return len(self.keys[key_id])

    def rotate(self, key_id: str) -> int:
        with self._lock:
            for v in self.keys.get(key_id, []):
                if v.state == "enabled":
                    v.state = "decrypt_only"
        return self.create(key_id)

    def set_state(self, key_id: str, version: int, state: str) -> None:
        if state not in ("enabled", "decrypt_only", "disabled", "destroyed"):
            raise ValueError(state)
        with self._lock:
            kv = self.keys[key_id][version - 1]
            if kv.state == "destroyed":
                raise ValueError("destroyed key versions cannot be revived")
            kv.state = state
            if state == "destroyed":
                kv.material = b""

    def health(self) -> bool:
        return self.available

    def _check(self) -> None:
        self.calls += 1
        if not self.available:
            raise SnapshotServiceError("SNAP_KMS_UNAVAILABLE", "key service unreachable")
        require_crypto()

    def wrap(self, key_id: str, dek: bytes, context: dict) -> tuple[int, str]:
        self._check()
        with self._lock:
            versions = self.keys.get(key_id)
            if not versions:
                raise SnapshotServiceError("SNAP_KEY_REVOKED", f"no such key {key_id}")
            idx = max((i for i, v in enumerate(versions) if v.state == "enabled"), default=None)
            if idx is None:
                raise SnapshotServiceError("SNAP_KEY_REVOKED", f"{key_id}: no enabled version")
            kek = versions[idx].material
        nonce = secrets.token_bytes(12)
        ct = AESGCM(kek).encrypt(nonce, dek, canonical_bytes({"purpose": "dek-wrap", **context}))
        return idx + 1, base64.b64encode(nonce + ct).decode()

    def unwrap(self, key_id: str, version: int, wrapped: str, context: dict) -> bytes:
        self._check()
        with self._lock:
            versions = self.keys.get(key_id) or []
            if not 1 <= version <= len(versions):
                raise SnapshotServiceError("SNAP_KEY_REVOKED", f"{key_id} v{version} unknown")
            kv = versions[version - 1]
            if kv.state in ("disabled", "destroyed"):
                raise SnapshotServiceError("SNAP_KEY_REVOKED", f"{key_id} v{version} {kv.state}")
            kek = kv.material
        try:
            raw = base64.b64decode(wrapped, validate=True)
            return AESGCM(kek).decrypt(raw[:12], raw[12:],
                                       canonical_bytes({"purpose": "dek-wrap", **context}))
        except (InvalidTag, ValueError) as exc:
            raise SnapshotServiceError("SNAP_CIPHERTEXT_INVALID", "DEK unwrap failed (wrong context/key)") from exc

    def rewrap(self, key_id: str, version: int, wrapped: str, context: dict) -> tuple[int, str]:
        """Re-wrap a DEK under the current KEK version (rotation without re-encrypting the blob)."""
        dek = self.unwrap(key_id, version, wrapped, context)
        try:
            return self.wrap(key_id, dek, context)
        finally:
            dek = b""  # noqa: F841 - best-effort drop of the reference


# ------------------------------------------------------------------- envelope
def seal_envelope(plaintext: bytes, *, ctx: dict, kms: KeyService, key_id: str,
                  chunk_size: int = DEFAULT_CHUNK) -> tuple[dict, bytes]:
    """Encrypt *plaintext*; return (envelope-manifest-fields, ciphertext blob)."""
    require_crypto()
    if chunk_size < 4096:
        raise ValueError("chunk_size too small")
    dek = bytearray(secrets.token_bytes(32))
    try:
        key_version, wrapped = kms.wrap(key_id, bytes(dek), ctx)
        aead = AESGCM(bytes(dek))
        total = max(1, -(-len(plaintext) // chunk_size))
        parts = []
        for i in range(total):
            chunk = plaintext[i * chunk_size:(i + 1) * chunk_size]
            parts.append(aead.encrypt(_nonce(i), chunk, _aad(ctx, i, total)))
        blob = b"".join(parts)
    finally:
        for i in range(len(dek)):  # zeroize our copy (the AESGCM object holds its own)
            dek[i] = 0
    env = {"alg": ENVELOPE_ALG, "key_id": key_id, "key_version": key_version, "wrapped_dek": wrapped,
           "chunk_size": chunk_size, "chunks": total, "ciphertext_sha256": hashlib.sha256(blob).hexdigest(),
           "plaintext_bytes": len(plaintext), "aad_schema": AAD_SCHEMA}
    return env, blob


def open_envelope(blob: bytes, *, env: dict, ctx: dict, kms: KeyService, verify_digest: bool = False) -> bytes:
    """Authenticate every chunk, then return plaintext; any mismatch -> integrity rejection.

    The per-chunk GCM tags (with index/total/final and the security context in
    the AAD) already authenticate every byte, so the whole-blob SHA-256 is not
    needed for integrity on the restore hot path; it is checked when
    ``verify_digest=True`` (capture read-back and the storage scrub) to tell
    storage corruption apart from tampering. Measured effect: -49 ms of a
    ~78 ms decrypt at 16 MiB on the build host (BENCHMARKS.md, C066).
    """
    require_crypto()
    if not isinstance(env, dict) or env.get("alg") != ENVELOPE_ALG or env.get("aad_schema") != AAD_SCHEMA:
        raise SnapshotServiceError("SNAP_UNSUPPORTED_VERSION", "unsupported envelope")
    from .schema import SCHEMAS, _walk
    errs: list[str] = []
    _walk(env, SCHEMAS["PK_SNAPSHOT_MANIFEST/1"]["properties"]["envelope"], "$.envelope", errs, 0)
    if errs:
        raise SnapshotServiceError("SNAP_STORAGE_CORRUPT", "envelope metadata invalid: " + "; ".join(errs[:5]))
    total, size = env["chunks"], env["chunk_size"]
    if total != max(1, -(-env["plaintext_bytes"] // size)):
        raise SnapshotServiceError("SNAP_CIPHERTEXT_INVALID", "chunk count inconsistent with length")
    if len(blob) != env["plaintext_bytes"] + 16 * total:
        raise SnapshotServiceError("SNAP_CIPHERTEXT_INVALID", "ciphertext length mismatch")
    if verify_digest and hashlib.sha256(blob).hexdigest() != env["ciphertext_sha256"]:
        raise SnapshotServiceError("SNAP_STORAGE_CORRUPT", "ciphertext digest mismatch")
    dek = kms.unwrap(env["key_id"], env["key_version"], env["wrapped_dek"], ctx)
    aead = AESGCM(dek)
    mv = memoryview(blob)
    parts: list[bytes] = []
    pos = 0
    try:
        for i in range(total):
            clen = min(size, env["plaintext_bytes"] - i * size) + 16
            try:
                parts.append(aead.decrypt(_nonce(i), mv[pos:pos + clen], _aad(ctx, i, total)))
            except InvalidTag:
                parts.clear()
                raise SnapshotServiceError("SNAP_CIPHERTEXT_INVALID", f"chunk {i} failed authentication") from None
            pos += clen
    finally:
        dek = b""  # noqa: F841
    return b"".join(parts)
