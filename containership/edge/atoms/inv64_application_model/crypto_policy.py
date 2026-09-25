"""Transport/storage encryption policy, managed key rotation, trust-service outage rules (MC-17; C047-C048).

* :func:`tls_context` — TLS 1.2 minimum (1.3 preferred), AEAD-only suites,
  compression and renegotiation off, peer certificate required (mTLS) for
  service-to-service boundaries, hostname verification on for clients.
* :class:`KeyRing` + :func:`seal` / :func:`open_sealed` — envelope encryption
  for persisted sensitive state/evidence: a fresh 256-bit DEK per object under
  AES-256-GCM, the DEK wrapped by a KEK fetched *by key ID* from a managed
  :class:`KeyProvider` (KMS/HSM) — key material never appears in configuration.
  Object metadata records ``kid``, algorithm and nonce, never key bytes.
  Key states: ``active`` (encrypt+decrypt), ``decrypt_only`` (rotation window),
  ``retired`` (refused: ``crypto.key_retired``), ``revoked`` (refused).
  :func:`rewrap` migrates objects to the active key during rotation.
  Without the optional ``cryptography`` backend every call refuses with
  ``crypto.unavailable`` — plaintext persistence is never the fallback.
* :data:`OUTAGE_RULES` / :func:`outage_decision` — explicit fail-closed /
  cached-trust behaviour for identity, attestation, policy, key and trusted-time
  service outages (SPECIFICATION.md §9).
"""
from __future__ import annotations

import base64
import os
import ssl
import threading
from dataclasses import dataclass
from typing import Callable, Mapping

from .errors import Inv64Error

AEAD_ALG = "AES-256-GCM"
TLS12_CIPHERS = "ECDHE+AESGCM:ECDHE+CHACHA20"


def tls_context(*, server: bool, cafile: str | None = None, certfile: str | None = None,
                keyfile: str | None = None, require_client_cert: bool = True) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server else ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers(TLS12_CIPHERS)
    ctx.options |= ssl.OP_NO_COMPRESSION
    if hasattr(ssl, "OP_NO_RENEGOTIATION"):
        ctx.options |= ssl.OP_NO_RENEGOTIATION
    if server:
        ctx.verify_mode = ssl.CERT_REQUIRED if require_client_cert else ssl.CERT_NONE
    else:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    if cafile:
        ctx.load_verify_locations(cafile)
    if certfile:
        ctx.load_cert_chain(certfile, keyfile)
    return ctx


def _aead():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise Inv64Error("crypto.unavailable", details={"reason": "cryptography backend not installed"})
    return AESGCM


class KeyProvider:
    """Managed key source: ``get(kid) -> bytes`` (32-byte KEK). Implementations wrap KMS/HSM."""

    def __init__(self, fetch: Callable[[str], bytes]):
        self._fetch = fetch

    def get(self, kid: str) -> bytes:
        try:
            k = self._fetch(kid)
        except Exception:
            raise Inv64Error("crypto.unavailable", details={"kid": kid})
        if not isinstance(k, (bytes, bytearray)) or len(k) != 32:
            raise Inv64Error("crypto.unavailable", details={"kid": kid, "reason": "bad key material"})
        return bytes(k)


@dataclass
class KeyRing:
    provider: KeyProvider
    states: dict  # kid -> "active" | "decrypt_only" | "retired" | "revoked"

    def __post_init__(self):
        self._lock = threading.Lock()
        actives = [k for k, s in self.states.items() if s == "active"]
        if len(actives) != 1:
            raise ValueError("exactly one active key is required")

    @property
    def active(self) -> str:
        return next(k for k, s in self.states.items() if s == "active")

    def rotate(self, new_kid: str) -> None:
        with self._lock:
            old = self.active
            self.states[old] = "decrypt_only"
            self.states[new_kid] = "active"

    def retire(self, kid: str) -> None:
        with self._lock:
            if self.states.get(kid) == "active":
                raise ValueError("cannot retire the active key")
            self.states[kid] = "retired"

    def usable_for_decrypt(self, kid: str) -> None:
        st = self.states.get(kid)
        if st in ("active", "decrypt_only"):
            return
        if st == "revoked":
            raise Inv64Error("crypto.key_retired", details={"kid": kid, "state": "revoked"})
        raise Inv64Error("crypto.key_retired", details={"kid": kid, "state": st or "unknown"})


def seal(plaintext: bytes, ring: KeyRing, *, aad: bytes = b"") -> dict:
    AESGCM = _aead()
    kid = ring.active
    kek = ring.provider.get(kid)
    dek = AESGCM.generate_key(bit_length=256)
    n1, n2 = os.urandom(12), os.urandom(12)
    wrapped = AESGCM(kek).encrypt(n1, dek, kid.encode())
    ct = AESGCM(dek).encrypt(n2, plaintext, aad)
    return {"format": "PK_APP_SEALED/1", "alg": AEAD_ALG, "kid": kid,
            "wrap_nonce": base64.b64encode(n1).decode(), "wrapped_dek": base64.b64encode(wrapped).decode(),
            "nonce": base64.b64encode(n2).decode(), "ciphertext": base64.b64encode(ct).decode()}


def open_sealed(obj: Mapping, ring: KeyRing, *, aad: bytes = b"") -> bytes:
    AESGCM = _aead()
    if obj.get("format") != "PK_APP_SEALED/1" or obj.get("alg") != AEAD_ALG:
        raise Inv64Error("crypto.unavailable", details={"reason": "unknown sealed format"})
    kid = obj["kid"]
    ring.usable_for_decrypt(kid)
    kek = ring.provider.get(kid)
    try:
        from cryptography.exceptions import InvalidTag
        dek = AESGCM(kek).decrypt(base64.b64decode(obj["wrap_nonce"]), base64.b64decode(obj["wrapped_dek"]),
                                  kid.encode())
        return AESGCM(dek).decrypt(base64.b64decode(obj["nonce"]), base64.b64decode(obj["ciphertext"]), aad)
    except (InvalidTag, ValueError, KeyError):
        raise Inv64Error("crypto.unavailable", details={"reason": "authentication failed"})


def rewrap(obj: Mapping, ring: KeyRing, *, aad: bytes = b"") -> dict:
    if obj.get("kid") == ring.active:
        return dict(obj)
    return seal(open_sealed(obj, ring, aad=aad), ring, aad=aad)


# service -> (behaviour when unreachable, cached-trust window seconds, rationale)
OUTAGE_RULES: dict[str, tuple[str, int, str]] = {
    "identity": ("cached-then-closed", 300, "tokens verifiable with cached keys stay valid for the cache TTL; no new issuers/keys"),
    "attestation": ("closed", 0, "no new node/peer trust without fresh attestation"),
    "policy": ("last-verified", 3600, "keep enforcing the last verified authz policy; never fall back to allow"),
    "key": ("closed-for-write", 0, "no new sealed writes; decrypt only with already-fetched keys in process"),
    "trusted-time": ("closed-if-uncertain", 0, "if clock uncertainty exceeds token skew, refuse expiry-sensitive decisions"),
    "provenance": ("cached-verification", 86_400, "previously verified digests remain valid; new artifacts refused"),
    "audit-sink": ("bounded-buffer", 0, "buffer up to limit; critical operations fail closed; drops counted and chained"),
}


def outage_decision(service: str, *, cached_age_s: float | None, new_trust: bool) -> str:
    """Return ``allow-cached`` or raise; unknown services fail closed."""
    rule = OUTAGE_RULES.get(service)
    if rule is None:
        raise Inv64Error("auth.trust_unavailable", details={"service": service})
    mode, window, _ = rule
    if new_trust or cached_age_s is None or cached_age_s > window or mode.startswith("closed"):
        raise Inv64Error("auth.trust_unavailable", details={"service": service, "mode": mode})
    return "allow-cached"
