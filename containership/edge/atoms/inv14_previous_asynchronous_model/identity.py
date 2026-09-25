"""Authenticated component identity / capability tokens (component P1-07).

v4.2.0 compared ``owner`` strings.  v4.3.0 binds an owner to a principal
``tenant/component/instance`` through an HMAC-SHA256 capability token minted by a
trusted issuer key.  A poll is admitted only when the presented token verifies,
is unexpired, grants ``poll``, and its principal equals the PollSet owner.

What this is NOT: runtime attestation.  The issuer key is supplied by the host;
binding it to a hardware/runtime attestation is an INV-13/GAP-15 obligation and
is recorded as BLOCKED in the checklist status (no attestation service exists in
this archive).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time

try:
    from .errors import Inv14Error
except ImportError:
    from errors import Inv14Error

TOKEN_SCHEMA = "PK_POLL_CAPABILITY/1"
_SEG = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,62}$")
MAX_TOKEN_BYTES = 2048
MAX_TTL_SECONDS = 3600
MIN_KEY_BYTES = 32


class IdentityError(Inv14Error):
    default_code = "PK_POLL_IDENTITY_REFUSED"


def principal(tenant: str, component: str, instance: str) -> str:
    for label, seg in (("tenant", tenant), ("component", component), ("instance", instance)):
        if not isinstance(seg, str) or not _SEG.match(seg):
            raise IdentityError(f"invalid {label} segment", code="PK_POLL_INVALID_PRINCIPAL")
    return f"{tenant}/{component}/{instance}"


def tenant_of(owner: str) -> str:
    parts = owner.split("/") if isinstance(owner, str) else []
    if len(parts) != 3:
        raise IdentityError("owner is not a tenant-namespaced principal", code="PK_POLL_INVALID_PRINCIPAL")
    principal(*parts)
    return parts[0]


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Issuer:
    def __init__(self, key: bytes, key_id: str, *, clock=time.time):
        if not isinstance(key, (bytes, bytearray)) or len(key) < MIN_KEY_BYTES:
            raise IdentityError("issuer key must be >= 32 bytes", code="PK_POLL_WEAK_KEY")
        if not isinstance(key_id, str) or not _SEG.match(key_id):
            raise IdentityError("invalid key id", code="PK_POLL_INVALID_KEY_ID")
        self._key, self.key_id, self._clock = bytes(key), key_id, clock

    def mint(self, owner: str, *, ttl_seconds: int = 300, rights=("poll",)) -> str:
        tenant_of(owner)
        if not isinstance(ttl_seconds, int) or not 0 < ttl_seconds <= MAX_TTL_SECONDS:
            raise IdentityError("ttl out of range", code="PK_POLL_TOKEN_TTL")
        now = int(self._clock())
        body = {"schema": TOKEN_SCHEMA, "sub": owner, "kid": self.key_id,
                "iat": now, "exp": now + ttl_seconds, "rights": sorted(set(rights))}
        payload = _b64(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
        sig = _b64(hmac.new(self._key, payload.encode(), hashlib.sha256).digest())
        return f"{payload}.{sig}"


class Verifier:
    """Verifies tokens against a set of trusted issuer keys (key rotation safe)."""

    def __init__(self, trusted: dict, *, clock=time.time, leeway_seconds: int = 5):
        if not trusted:
            raise IdentityError("no trusted issuer keys configured", code="PK_POLL_NO_TRUST_ROOT")
        self._trusted = {k: bytes(v) for k, v in trusted.items()}
        self._clock, self._leeway = clock, leeway_seconds

    def verify(self, token: object, *, owner: str, right: str = "poll") -> dict:
        if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_BYTES or token.count(".") != 1:
            raise IdentityError("malformed capability token", code="PK_POLL_TOKEN_MALFORMED")
        payload, sig = token.split(".")
        try:
            body = json.loads(_unb64(payload))
            sig_b = _unb64(sig)
        except Exception:
            raise IdentityError("malformed capability token", code="PK_POLL_TOKEN_MALFORMED") from None
        if not isinstance(body, dict) or body.get("schema") != TOKEN_SCHEMA:
            raise IdentityError("wrong token schema", code="PK_POLL_TOKEN_MALFORMED")
        key = self._trusted.get(body.get("kid"))
        if key is None:
            raise IdentityError("untrusted issuer", code="PK_POLL_TOKEN_UNTRUSTED")
        if not hmac.compare_digest(hmac.new(key, payload.encode(), hashlib.sha256).digest(), sig_b):
            raise IdentityError("bad token signature", code="PK_POLL_TOKEN_SIGNATURE")
        now = self._clock()
        if not isinstance(body.get("exp"), int) or now > body["exp"] + self._leeway:
            raise IdentityError("token expired", code="PK_POLL_TOKEN_EXPIRED")
        if not isinstance(body.get("iat"), int) or body["iat"] > now + self._leeway:
            raise IdentityError("token not yet valid", code="PK_POLL_TOKEN_NOT_YET_VALID")
        if right not in (body.get("rights") or []):
            raise IdentityError("token lacks right", code="PK_POLL_TOKEN_RIGHT", details={"right": right})
        if body.get("sub") != owner:
            # Do not disclose the other principal's identity.
            raise IdentityError("token principal does not own this poll set", code="PK_POLL_TOKEN_SUBJECT")
        return {"sub": body["sub"], "tenant": tenant_of(body["sub"]), "kid": body["kid"], "exp": body["exp"]}
