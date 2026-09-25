"""M17/M36/M39 - principals, enrolment, signed short-lived credentials.

A trust domain has an issuer key (Ed25519). Principals (host, workload, provider,
operator, automation, control) are enrolled once with a one-time enrolment code
(no shared default credential), receive a public key binding, and then present
short-lived signed tokens bound to audience + nonce + session. Validation checks
signature, issuer, audience, subject kind, not-before/expiry with bounded clock
skew, revocation, replay and clone (same identity from an unexpected endpoint).
Dependency failure (issuer/revocation source unavailable) fails CLOSED.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass, field

from . import ed25519
from .errors import FabricError

KINDS = ("host", "workload", "provider", "operator", "automation", "control")
MAX_CLOCK_SKEW_S = 30.0
MAX_TOKEN_TTL_S = 900.0


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    """Strict, canonical decode: rejects non-alphabet characters and non-canonical
    trailing bits so one credential has exactly one accepted encoding (no malleability)."""
    if not isinstance(s, str) or not s or any(c not in _B64_ALPHABET for c in s):
        raise ValueError("non-canonical base64")
    raw = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    if _b64(raw) != s:
        raise ValueError("non-canonical base64")
    return raw


_B64_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


@dataclass
class Principal:
    id: str                 # spiffe-like: spiffe://<domain>/<kind>/<name>
    kind: str
    tenant: str
    public_key: bytes
    attestation: dict = field(default_factory=dict)
    endpoint: str | None = None

    def public(self) -> dict:
        """Non-sensitive identity metadata for diagnostics (M36)."""
        return {"id": self.id, "kind": self.kind, "tenant": self.tenant,
                "key_fingerprint": hashlib.sha256(self.public_key).hexdigest()[:16],
                "attested": bool(self.attestation.get("verified"))}


class TrustDomain:
    def __init__(self, name: str, issuer_seed: bytes | None = None, *, clock=time.time,
                 require_attestation_for=("host",)) -> None:
        self.name = name
        self._issuer_seed = issuer_seed or os.urandom(32)
        self.issuer_public = ed25519.public_key(self._issuer_seed)
        self.clock = clock
        self.principals: dict[str, Principal] = {}
        self.revoked: set[str] = set()
        self._enrol_codes: dict[str, tuple[str, str, str]] = {}
        self._seen_nonces: dict[str, float] = {}
        self._nonce_lock = threading.Lock()  # replay check+record must be atomic
        self.require_attestation_for = set(require_attestation_for)
        self.revocation_source_available = True
        self.issuer_available = True

    # -- enrolment (M17 bootstrap, M36 issuance) --------------------
    def issue_enrolment_code(self, kind: str, name: str, tenant: str) -> str:
        if kind not in KINDS:
            raise FabricError("INVALID_ARGUMENT", f"unknown principal kind {kind!r}")
        code = _b64(os.urandom(18))
        self._enrol_codes[hashlib.sha256(code.encode()).hexdigest()] = (kind, name, tenant)
        return code

    def enrol(self, code: str, public_key: bytes, *, attestation: dict | None = None,
              endpoint: str | None = None) -> Principal:
        key = hashlib.sha256(code.encode()).hexdigest()
        if key not in self._enrol_codes:
            raise FabricError("UNAUTHENTICATED", "enrolment code unknown or already used")
        kind, name, tenant = self._enrol_codes.pop(key)  # single use
        att = dict(attestation or {})
        if kind in self.require_attestation_for:
            if not self._verify_attestation(att, public_key):
                raise FabricError("UNAUTHENTICATED", f"{kind} enrolment requires valid attestation")
        pid = f"spiffe://{self.name}/{kind}/{name}"
        for p in self.principals.values():
            if p.public_key == public_key:
                raise FabricError("ALREADY_EXISTS", "public key already bound to another identity (clone)")
        if pid in self.principals and pid not in self.revoked:
            raise FabricError("ALREADY_EXISTS", f"{pid} already enrolled")
        self.revoked.discard(pid)
        pr = Principal(pid, kind, tenant, bytes(public_key), att, endpoint)
        self.principals[pid] = pr
        return pr

    @staticmethod
    def _verify_attestation(att: dict, public_key: bytes) -> bool:
        """Reference attestation: a quote binding the public key to a measured boot digest.

        Real deployments bind TPM/TEE quotes here; the reference form is
        {"measurement": hex, "quote": sha256(measurement||pubkey)}. Marked verified on success.
        """
        m, q = att.get("measurement"), att.get("quote")
        if not (isinstance(m, str) and isinstance(q, str)):
            return False
        ok = hmac.compare_digest(q, hashlib.sha256(bytes.fromhex(m) + public_key).hexdigest())
        att["verified"] = ok
        return ok

    def revoke(self, principal_id: str) -> None:
        self.revoked.add(principal_id)

    # -- tokens -----------------------------------------------------
    def mint_token(self, principal_id: str, subject_seed: bytes, audience: str, *,
                   ttl_s: float = 300.0, session: str = "", nonce: str | None = None) -> str:
        """Holder-signed request token: the subject proves key possession; the fabric
        validates against the enrolled key. ttl is capped (short-lived credentials)."""
        if principal_id not in self.principals:
            raise FabricError("UNAUTHENTICATED", "unknown principal")
        now = self.clock()
        claims = {"iss": self.name, "sub": principal_id, "aud": audience,
                  "nbf": now, "exp": now + min(ttl_s, MAX_TOKEN_TTL_S),
                  "nonce": nonce or _b64(os.urandom(12)), "sid": session}
        body = canonical(claims)
        sig = ed25519.sign(subject_seed, body)
        return _b64(body) + "." + _b64(sig)

    def authenticate(self, token: str, audience: str, *, session: str = "",
                     endpoint: str | None = None) -> Principal:
        if not self.revocation_source_available or not self.issuer_available:
            raise FabricError("UNAVAILABLE", "identity dependency unavailable; failing closed")
        try:
            body_s, sig_s = token.split(".")
            body, sig = _unb64(body_s), _unb64(sig_s)
            claims = json.loads(body)
        except Exception:
            raise FabricError("UNAUTHENTICATED", "malformed credential") from None
        sub = claims.get("sub")
        pr = self.principals.get(sub)
        if pr is None:
            raise FabricError("UNAUTHENTICATED", "unknown principal")
        if not ed25519.verify(pr.public_key, body, sig):
            raise FabricError("UNAUTHENTICATED", "signature invalid")
        if claims.get("iss") != self.name:
            raise FabricError("UNAUTHENTICATED", "wrong issuer / trust domain")
        if claims.get("aud") != audience:
            raise FabricError("UNAUTHENTICATED", "wrong audience")
        now = self.clock()
        if now + MAX_CLOCK_SKEW_S < claims.get("nbf", 0):
            raise FabricError("UNAUTHENTICATED", "credential not yet valid (clock skew)")
        if now - MAX_CLOCK_SKEW_S > claims.get("exp", 0):
            raise FabricError("UNAUTHENTICATED", "credential expired")
        if claims.get("exp", 0) - claims.get("nbf", 0) > MAX_TOKEN_TTL_S + 1e-6:
            raise FabricError("UNAUTHENTICATED", "credential lifetime exceeds policy")
        if sub in self.revoked:
            raise FabricError("UNAUTHENTICATED", "principal revoked")
        if claims.get("sid", "") != session:
            raise FabricError("UNAUTHENTICATED", "credential not bound to this session")
        if pr.kind in self.require_attestation_for and not pr.attestation.get("verified"):
            raise FabricError("UNAUTHENTICATED", "principal not attested")
        if endpoint and pr.endpoint and endpoint != pr.endpoint:
            raise FabricError("UNAUTHENTICATED", "identity presented from unexpected endpoint (clone)")
        nonce = claims.get("nonce")
        with self._nonce_lock:
            self._gc_nonces(now)
            if nonce in self._seen_nonces:
                raise FabricError("REPLAY_DETECTED", "credential nonce replayed")
            self._seen_nonces[nonce] = claims["exp"]
        return pr

    def _gc_nonces(self, now: float) -> None:
        for n in [n for n, exp in self._seen_nonces.items() if exp + MAX_CLOCK_SKEW_S < now]:
            del self._seen_nonces[n]


def new_keypair() -> tuple[bytes, bytes]:
    seed = os.urandom(32)
    return seed, ed25519.public_key(seed)


def reference_attestation(public_key: bytes, measurement: bytes | None = None) -> dict:
    m = measurement or hashlib.sha256(b"reference-measured-boot").digest()
    return {"measurement": m.hex(), "quote": hashlib.sha256(m + public_key).hexdigest()}
