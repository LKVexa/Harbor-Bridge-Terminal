"""Authentication layer (component 07).

Principals are typed (``user``, ``service``, ``producer``, ``node``,
``automation``, ``breakglass``) and each type has its own issuer and maximum
token lifetime — no shared credential class (MC-07-01). Tokens are short-lived
Ed25519-signed canonical JSON (``GAP15-TOKEN/1``), verified for issuer,
audience, subject type, exp/nbf with bounded skew, single-use nonce and
optional channel binding (e.g. the mTLS peer certificate digest) (MC-07-03).
Revocation is checked against a revocation set whose age is bounded; a stale
set fails closed (MC-07-04). Node tokens are only accepted together with a
verified attestation binding (MC-07-06). Break-glass tokens are time-limited,
need an incident reference and an approver, and are flagged for review
(MC-07-07). Delegation chains carry the original actor (MC-07-08).
"""
from __future__ import annotations

import hmac
import threading
from dataclasses import dataclass, field
from typing import Optional

from .canonical import CanonicalError, canonical_bytes, parse
from .signing import KeyProvider, TrustStore, b64d, b64e, verify_payload

TOKEN_SCHEMA = "GAP15-TOKEN/1"
PRINCIPAL_TYPES = {"user": 3600, "service": 900, "producer": 900, "node": 900, "automation": 600, "breakglass": 1800}
MAX_SKEW_S = 30
MAX_REVOCATION_AGE_S = 300
MAX_TOKEN_BYTES = 4096


class AuthError(PermissionError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)  # detail is deliberately not in str(): no enumeration oracle
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Principal:
    subject: str
    ptype: str
    issuer: str
    scopes: frozenset
    partitions: frozenset
    token_id: str
    delegated_by: tuple = ()
    breakglass: Optional[dict] = None
    attestation_digest: Optional[str] = None

    def as_audit(self) -> dict:
        return {"subject": self.subject, "type": self.ptype, "issuer": self.issuer, "token_id": self.token_id,
                "delegated_by": list(self.delegated_by), "breakglass": bool(self.breakglass)}


def issue_token(provider: KeyProvider, key_id: str, *, issuer: str, subject: str, ptype: str, audience: str,
                now: int, ttl_s: int, scopes: list, partitions: list, nonce: str,
                cnf: Optional[str] = None, delegated_by: tuple = (), breakglass: Optional[dict] = None,
                attestation_digest: Optional[str] = None) -> str:
    if ptype not in PRINCIPAL_TYPES:
        raise AuthError("E_AUTH_PTYPE", ptype)
    claims = {"schema": TOKEN_SCHEMA, "iss": issuer, "sub": subject, "typ": ptype, "aud": audience,
              "iat": now, "nbf": now, "exp": now + min(ttl_s, PRINCIPAL_TYPES[ptype]), "jti": nonce,
              "scp": sorted(scopes), "prt": sorted(partitions), "dlg": list(delegated_by)}
    if cnf:
        claims["cnf"] = cnf
    if breakglass:
        claims["bg"] = breakglass
    if attestation_digest:
        claims["att"] = attestation_digest
    from .signing import sign_payload
    sig = sign_payload(provider, key_id, message_type="token", environment=audience, payload=claims, signed_at=now)
    return b64e(canonical_bytes(claims)) + "." + b64e(canonical_bytes(sig))


@dataclass
class Authenticator:
    trust: TrustStore
    audience: str
    issuers: dict  # issuer -> set(ptype) it may mint
    revoked_token_ids: set = field(default_factory=set)
    revoked_subjects: set = field(default_factory=set)
    revocation_list_at: int = 0
    _seen_nonces: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    failures: dict = field(default_factory=dict)  # (issuer, subject) -> count (throttling)

    def update_revocations(self, token_ids: set, subjects: set, at: int) -> None:
        self.revoked_token_ids |= set(token_ids)
        self.revoked_subjects |= set(subjects)
        self.revocation_list_at = at

    def authenticate(self, token: object, *, now: int, channel_binding: Optional[str] = None,
                     attestation_verified: Optional[str] = None) -> Principal:
        if not isinstance(token, str) or len(token) > MAX_TOKEN_BYTES or token.count(".") != 1:
            raise AuthError("E_AUTH_MALFORMED")
        try:
            claims = parse(b64d_long(token.split(".")[0]), max_bytes=MAX_TOKEN_BYTES)
            sig = parse(b64d_long(token.split(".")[1]), max_bytes=MAX_TOKEN_BYTES)
        except (CanonicalError, ValueError):
            raise AuthError("E_AUTH_MALFORMED") from None
        if not isinstance(claims, dict) or claims.get("schema") != TOKEN_SCHEMA:
            raise AuthError("E_AUTH_MALFORMED")
        iss, ptype, sub = claims.get("iss"), claims.get("typ"), claims.get("sub")
        key = (iss, sub)
        if self.failures.get(key, 0) >= 5:
            raise AuthError("E_AUTH_THROTTLED")
        try:
            return self._check(claims, sig, now, channel_binding, attestation_verified)
        except AuthError:
            self.failures[key] = self.failures.get(key, 0) + 1
            raise

    def _check(self, claims, sig, now, channel_binding, attestation_verified) -> Principal:
        iss, ptype, sub = claims.get("iss"), claims.get("typ"), claims.get("sub")
        if claims.get("aud") != self.audience:
            raise AuthError("E_AUTH_AUDIENCE")
        if iss not in self.issuers or ptype not in self.issuers[iss]:
            raise AuthError("E_AUTH_ISSUER")
        result = verify_payload(self.trust, sig, message_type="token", environment=self.audience, payload=claims,
                                required_scope=f"token:issue:{ptype}")
        if not result.ok or result.signer != iss:
            raise AuthError("E_AUTH_SIGNATURE", result.code)
        for f in ("iat", "nbf", "exp"):
            if isinstance(claims.get(f), bool) or not isinstance(claims.get(f), int):
                raise AuthError("E_AUTH_MALFORMED")
        if claims["exp"] - claims["iat"] > PRINCIPAL_TYPES[ptype]:
            raise AuthError("E_AUTH_LIFETIME")
        if now + MAX_SKEW_S < claims["nbf"]:
            raise AuthError("E_AUTH_NOT_YET_VALID")
        if now - MAX_SKEW_S >= claims["exp"]:
            raise AuthError("E_AUTH_EXPIRED")
        if now - self.revocation_list_at > MAX_REVOCATION_AGE_S:
            raise AuthError("E_AUTH_REVOCATION_STALE")
        if claims["jti"] in self.revoked_token_ids or sub in self.revoked_subjects:
            raise AuthError("E_AUTH_REVOKED")
        if "cnf" in claims:
            if channel_binding is None or not hmac.compare_digest(claims["cnf"], channel_binding):
                raise AuthError("E_AUTH_BINDING")
        if ptype == "node":
            if not claims.get("att") or attestation_verified != claims.get("att"):
                raise AuthError("E_AUTH_ATTESTATION_REQUIRED")
        if ptype == "breakglass":
            bg = claims.get("bg") or {}
            if not bg.get("incident") or not bg.get("approver") or bg.get("approver") == sub:
                raise AuthError("E_AUTH_BREAKGLASS")
        with self._lock:
            for n, exp in list(self._seen_nonces.items()):
                if exp < now - MAX_SKEW_S:
                    del self._seen_nonces[n]
            if claims["jti"] in self._seen_nonces:
                raise AuthError("E_AUTH_REPLAY")
            self._seen_nonces[claims["jti"]] = claims["exp"]
        return Principal(sub, ptype, iss, frozenset(claims["scp"]), frozenset(claims["prt"]), claims["jti"],
                         tuple(claims.get("dlg", ())), claims.get("bg"), claims.get("att"))


def b64d_long(text: str) -> bytes:
    if len(text) > MAX_TOKEN_BYTES:
        raise ValueError("too long")
    import base64
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
